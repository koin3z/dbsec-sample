"""Oracle Database access helpers for direct-logon personas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from deepsec_demo.config import AdminConfig, DemoConfig
from deepsec_demo.personas import Persona
from deepsec_demo.sql_safety import normalize_select_sql


@dataclass(frozen=True)
class QueryResult:
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]


def _quoted_identifier(value: str) -> str:
    if not value:
        raise ValueError("Oracle identifier must not be empty.")
    return '"' + value.replace('"', '""') + '"'


def direct_logon_username(persona: Persona) -> str:
    """Return the connection username for a quoted lowercase local end user."""
    # The SQL setup creates local end users as quoted lowercase names,
    # e.g. CREATE END USER "manager_tokyo". Pass the same quoted name
    # to python-oracledb so Oracle does not fold it to MANAGER_TOKYO.
    return _quoted_identifier(persona.db_username)


def _connect_kwargs(config: DemoConfig, user: str, password: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "user": user,
        "password": password,
        "dsn": config.dsn,
    }
    if config.wallet_location:
        kwargs["config_dir"] = config.wallet_location
        kwargs["wallet_location"] = config.wallet_location
    return kwargs


def ensure_oracle_driver_mode(config: DemoConfig) -> None:
    """Enable the configured python-oracledb mode before opening a connection."""
    import oracledb

    if config.driver_mode == "thin":
        return

    kwargs: dict[str, str] = {}
    if config.client_lib_dir:
        kwargs["lib_dir"] = config.client_lib_dir
    if config.client_config_dir:
        kwargs["config_dir"] = config.client_config_dir
    oracledb.init_oracle_client(**kwargs)


def oracle_driver_mode() -> str:
    """Return the currently active python-oracledb mode."""
    import oracledb

    return "thin" if oracledb.is_thin_mode() else "thick"


def connect_as_persona(config: DemoConfig, persona: Persona):
    """Open a direct-logon connection for a local demo end user."""
    import oracledb

    ensure_oracle_driver_mode(config)
    # This is the key Phase 1 behavior: open a new DB session as the
    # selected local end user. No shared application user is used here.
    connection = oracledb.connect(
        **_connect_kwargs(config, direct_logon_username(persona), config.default_password)
    )
    connection.call_timeout = config.connect_timeout * 1000
    return connection


def _admin_auth_mode(oracledb_module: Any, mode: str) -> Any | None:
    if mode == "default":
        return None
    if mode == "sysdba":
        return getattr(oracledb_module, "AUTH_MODE_SYSDBA")
    if mode == "sysoper":
        return getattr(oracledb_module, "AUTH_MODE_SYSOPER")
    raise ValueError(f"Unsupported admin mode: {mode}")


def connect_as_admin(config: DemoConfig, admin: AdminConfig):
    """Open the admin connection used by setup scripts."""
    import oracledb

    ensure_oracle_driver_mode(config)
    kwargs = _connect_kwargs(config, admin.user, admin.password)
    mode = _admin_auth_mode(oracledb, admin.mode)
    if mode is not None:
        kwargs["mode"] = mode
    connection = oracledb.connect(**kwargs)
    connection.call_timeout = config.connect_timeout * 1000
    return connection


def query_as_persona(config: DemoConfig, persona: Persona, sql: str) -> QueryResult:
    """Run a SELECT-only query as the selected direct-logon persona."""
    # Validate only the shape of the SQL. Access control remains Database-side DDS.
    normalized_sql = normalize_select_sql(sql)
    with connect_as_persona(config, persona) as connection:
        with connection.cursor() as cursor:
            cursor.execute(normalized_sql)
            columns = tuple(column[0].lower() for column in (cursor.description or ()))
            rows = tuple(tuple(row) for row in cursor.fetchall())
    return QueryResult(columns=columns, rows=rows)
