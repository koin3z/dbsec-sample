"""Run a SQL setup file against the configured admin connection."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deepsec_demo.config import ConfigError, DemoConfig, load_admin_config, load_config
from deepsec_demo.db import connect_as_admin


_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_PASSWORD_RE = re.compile(
    r"(identified\s+by)\s+(\"(?:\"\"|[^\"])*\"|\S+)",
    flags=re.IGNORECASE,
)


def _sql_identifier(value: str) -> str:
    if not _IDENTIFIER_RE.match(value):
        raise ConfigError(f"Unsafe SQL identifier in configuration: {value!r}")
    return value.upper()


def _quoted_password(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def render_template(sql_text: str, config: DemoConfig) -> str:
    """Render non-secret SQL placeholders from validated configuration."""
    schema = _sql_identifier(config.demo_schema)
    return (
        sql_text.replace("{{DEMO_SCHEMA}}", schema)
        .replace("{{DEMO_SCHEMA_LOWER}}", schema.lower())
        .replace("{{DEMO_DEFAULT_PASSWORD}}", _quoted_password(config.default_password))
    )


def iter_statements(sql_text: str) -> Iterable[str]:
    """Yield SQL statements split on semicolons and SQL*Plus-style slash lines."""
    buffer: list[str] = []
    in_plsql = False

    for raw_line in sql_text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("--"):
            continue

        if stripped == "/":
            statement = "\n".join(buffer).strip()
            if statement:
                yield statement
            buffer.clear()
            in_plsql = False
            continue

        if not buffer and re.match(r"^(begin|declare)\b", stripped, re.IGNORECASE):
            in_plsql = True

        buffer.append(raw_line)

        if not in_plsql and stripped.endswith(";"):
            statement = "\n".join(buffer).strip()
            yield statement[:-1].rstrip()
            buffer.clear()

    statement = "\n".join(buffer).strip()
    if statement:
        if statement.endswith(";"):
            statement = statement[:-1].rstrip()
        yield statement


def _redact(statement: str) -> str:
    first_line = statement.strip().splitlines()[0]
    return _PASSWORD_RE.sub(r"\1 <redacted>", first_line)


def run_file(
    path: Path,
    *,
    continue_on_error: bool,
    dry_run: bool,
    env_file: str | Path | None,
) -> int:
    raw_sql_text = path.read_text(encoding="utf-8")
    raw_statements = list(iter_statements(raw_sql_text))
    if not raw_statements:
        print(f"No executable statements in {path}")
        return 0

    if dry_run:
        demo_config = load_config(env_file)
        sql_text = render_template(raw_sql_text, demo_config)
        statements = list(iter_statements(sql_text))
        print(f"DRY RUN {path}: {len(statements)} statement(s)")
        for index, statement in enumerate(statements, start=1):
            print(f"{index:02d}: {_redact(statement)}")
        return 0

    demo_config, admin_config = load_admin_config(env_file)
    sql_text = render_template(raw_sql_text, demo_config)
    statements = list(iter_statements(sql_text))

    with connect_as_admin(demo_config, admin_config) as connection:
        with connection.cursor() as cursor:
            for index, statement in enumerate(statements, start=1):
                try:
                    cursor.execute(statement)
                    if cursor.description:
                        columns = [column[0] for column in cursor.description]
                        print(" | ".join(columns))
                        for row in cursor.fetchall():
                            print(" | ".join("" if value is None else str(value) for value in row))
                    print(f"OK {index}/{len(statements)}: {_redact(statement)}")
                except Exception as exc:
                    print(f"ERROR {index}/{len(statements)}: {_redact(statement)}")
                    print(f"{type(exc).__name__}: {exc}")
                    if not continue_on_error:
                        return 1
            connection.commit()
    return 0


def _connection_hint(exc: Exception) -> str | None:
    message = str(exc)
    if "DPY-3001" in message:
        return (
            "DPY-3001: 接続先が Native Network Encryption または Data Integrity "
            "を要求しています。.env で ORACLE_DRIVER_MODE=thick を設定し、"
            "Oracle Client libraries を利用できる状態にしてください。"
        )
    if "DPI-1047" in message:
        return (
            "DPI-1047: Oracle Client libraries を読み込めません。"
            "ORACLE_CLIENT_LIB_DIR、LD_LIBRARY_PATH、ldconfig、Instant Client の"
            "インストール状態を確認してください。"
        )
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one SQL setup file with placeholders rendered from .env."
    )
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render and list statements without connecting to Oracle Database.",
    )
    args = parser.parse_args()

    try:
        return run_file(
            args.file,
            continue_on_error=args.continue_on_error,
            dry_run=args.dry_run,
            env_file=args.env_file,
        )
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        return 2
    except Exception as exc:
        print(f"SQL execution failed: {type(exc).__name__}: {exc}")
        hint = _connection_hint(exc)
        if hint:
            print(f"Hint: {hint}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
