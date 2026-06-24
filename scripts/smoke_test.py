"""Live DB smoke test for the direct-logon demo."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deepsec_demo.config import ConfigError, load_config
from deepsec_demo.db import QueryResult, direct_logon_username, query_as_persona
from deepsec_demo.personas import PERSONAS, get_persona
from deepsec_demo.queries import EXAMPLE_QUERIES

SENSITIVE_COLUMNS = ("salary_amount", "personal_id", "phone_number")


@dataclass(frozen=True)
class CheckResult:
    summary: list[str]
    failures: list[str]
    warnings: list[str]


def _employee_ids(result: QueryResult) -> set[int]:
    if "employee_id" not in result.columns:
        return set()
    index = result.columns.index("employee_id")
    return {int(row[index]) for row in result.rows if row[index] is not None}


def _row_by_employee_id(result: QueryResult) -> dict[int, tuple[object, ...]]:
    if "employee_id" not in result.columns:
        return {}
    index = result.columns.index("employee_id")
    return {int(row[index]): row for row in result.rows if row[index] is not None}


def _cell(result: QueryResult, employee_id: int, column: str) -> object | None:
    rows = _row_by_employee_id(result)
    if employee_id not in rows or column not in result.columns:
        return None
    return rows[employee_id][result.columns.index(column)]


def _all_null(result: QueryResult, column: str, employee_ids: set[int] | None = None) -> bool:
    if column not in result.columns:
        return True
    rows = _row_by_employee_id(result)
    target_ids = employee_ids if employee_ids is not None else set(rows)
    return all(_cell(result, employee_id, column) is None for employee_id in target_ids)


def _validate_canonical(persona_id: str, result: QueryResult) -> CheckResult:
    ids = _employee_ids(result)
    summary = [f"rows={len(result.rows)}", f"employee_ids={sorted(ids)}"]
    failures: list[str] = []
    warnings: list[str] = []

    if "employee_id" not in result.columns:
        failures.append("employee_id column is missing from the result")
        return CheckResult(summary, failures, warnings)

    if persona_id == "staff_tokyo":
        if ids != {1001}:
            failures.append("expected only employee_id 1001")
        for column in SENSITIVE_COLUMNS:
            if column not in result.columns:
                warnings.append(f"{column} column is unavailable; target DDS behavior may hide columns")

    elif persona_id == "manager_tokyo":
        expected = {1001, 1002, 1003}
        if ids != expected:
            failures.append(f"expected employee_ids {sorted(expected)}")
        if "personal_id" not in result.columns:
            warnings.append("personal_id column is unavailable; expected NULL cells for direct reports")
        else:
            if not _all_null(result, "personal_id", {1001, 1002}):
                failures.append("expected personal_id to be NULL for direct reports 1001 and 1002")
            if _cell(result, 1003, "personal_id") is None:
                failures.append("expected manager own-row personal_id for employee_id 1003 to be visible")

    elif persona_id == "manager_japan":
        expected_subset = {1001, 1002, 1003, 1004, 1005}
        if not expected_subset.issubset(ids):
            failures.append(f"expected at least Japan Sales employee_ids {sorted(expected_subset)}")
        for column in SENSITIVE_COLUMNS:
            if column not in result.columns:
                warnings.append(f"{column} column is unavailable; target DDS behavior may hide columns")
        if "personal_id" in result.columns:
            non_own = ids - {1005}
            if not _all_null(result, "personal_id", non_own):
                failures.append("expected non-own country-scope personal_id values to be NULL")

    elif persona_id == "ai_assistant":
        if not ids:
            failures.append("expected active directory rows for ai_assistant")
        for column in SENSITIVE_COLUMNS:
            if column in result.columns and not _all_null(result, column):
                failures.append(f"expected {column} to be NULL for ai_assistant")
            elif column not in result.columns:
                warnings.append(f"{column} column is unavailable; this is acceptable for a narrow DDS projection")

    return CheckResult(summary, failures, warnings)


def _summarize_without_validation(result: QueryResult) -> CheckResult:
    ids = _employee_ids(result)
    return CheckResult(
        summary=[f"rows={len(result.rows)}", f"employee_ids={sorted(ids)}"],
        failures=[],
        warnings=["validation is only implemented for --sql canonical"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run live direct-logon smoke checks against Oracle Database."
    )
    parser.add_argument("--persona", choices=sorted(PERSONAS))
    parser.add_argument("--all-personas", action="store_true")
    parser.add_argument("--sql", choices=sorted(EXAMPLE_QUERIES), default="canonical")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Print validation failures but return success if the DB query itself ran.",
    )
    args = parser.parse_args()

    persona_ids = sorted(PERSONAS) if args.all_personas else [args.persona or "staff_tokyo"]
    sql = EXAMPLE_QUERIES[args.sql]
    any_failures = False

    current_persona_id: str | None = None
    current_direct_username: str | None = None

    try:
        config = load_config(args.env_file)
        print(
            "Connection target: "
            f"{config.host}:{config.port}/{config.service_name} "
            f"schema={config.demo_schema} mode={config.mode} driver={config.driver_mode}"
        )
        for persona_id in persona_ids:
            persona = get_persona(persona_id)
            current_persona_id = persona_id
            current_direct_username = direct_logon_username(persona)
            print(f"{persona_id}: connecting as {current_direct_username}")
            result = query_as_persona(config, persona, sql)
            check = (
                _validate_canonical(persona_id, result)
                if args.sql == "canonical"
                else _summarize_without_validation(result)
            )
            print(f"{persona_id}: " + "; ".join(check.summary))
            for warning in check.warnings:
                print(f"  WARN: {warning}")
            for failure in check.failures:
                print(f"  FAIL: {failure}")
            any_failures = any_failures or bool(check.failures)
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        return 2
    except Exception as exc:
        print(f"Smoke test failed: {type(exc).__name__}: {exc}")
        message = str(exc)
        if "ORA-01017" in message:
            if current_persona_id and current_direct_username:
                print(
                    "Hint: direct logon attempted "
                    f"persona={current_persona_id} user={current_direct_username}."
                )
            print(
                "Hint: quoted lowercase local end users require an exact password "
                "match. Confirm .env DEMO_DEFAULT_PASSWORD is the same value used "
                "when sql/03_create_end_users.sql was run. If unsure, rerun the "
                "setup from sql/00_reset.sql through sql/06_validate.sql."
            )
            print(
                "Hint: if the password is correct, confirm sql/04_create_data_roles.sql "
                "completed so the local end user inherits CREATE SESSION through "
                "deepsec_demo_session_role."
            )
        if "DPY-3001" in message:
            print(
                "Hint: .env で ORACLE_DRIVER_MODE=thick を設定し、Oracle Client "
                "libraries を利用できる状態にしてください。"
            )
        if "DPI-1047" in message:
            print(
                "Hint: Oracle Client libraries を読み込めません。ORACLE_CLIENT_LIB_DIR、"
                "LD_LIBRARY_PATH、ldconfig、Instant Client のインストール状態を確認してください。"
            )
        return 1

    if any_failures and not args.warn_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
