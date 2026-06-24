"""Application-mediated Deep Data Security helpers for Phase 2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from deepsec_demo.config import AppMediatedConfig, ConfigError, DemoConfig
from deepsec_demo.db import QueryResult, ensure_oracle_driver_mode
from deepsec_demo.personas import Persona
from deepsec_demo.sql_safety import normalize_select_sql


@dataclass(frozen=True)
class AppMediatedQueryResult(QueryResult):
    shared_db_user: str
    end_user: str
    context_attached: bool
    context_cleared: bool


def connect_as_app(config: DemoConfig, app_config: AppMediatedConfig):
    """Open the shared application database connection for Phase 2."""
    import oracledb

    ensure_oracle_driver_mode(config)
    kwargs: dict[str, Any] = {
        "user": app_config.app_username,
        "password": app_config.app_password,
        "dsn": config.dsn,
    }
    if config.wallet_location:
        kwargs["config_dir"] = config.wallet_location
        kwargs["wallet_location"] = config.wallet_location
    connection = oracledb.connect(**kwargs)
    connection.call_timeout = config.connect_timeout * 1000
    return connection


def validate_app_context_config(config: DemoConfig, app_config: AppMediatedConfig) -> None:
    """Validate Phase 2 settings before creating a security context payload."""
    if config.driver_mode != "thin":
        raise ConfigError(
            "Phase 2 end-user security context APIs are documented for "
            "python-oracledb Thin mode. Set ORACLE_DRIVER_MODE=thin for "
            "demo_app_mediated.py."
        )
    if app_config.security_context_mode != "local":
        raise ConfigError("Only APP_SECURITY_CONTEXT_MODE=local is implemented.")
    if not app_config.database_access_token:
        raise ConfigError("APP_DATABASE_ACCESS_TOKEN is required for Phase 2.")
    if not app_config.end_user_context_key:
        raise ConfigError("APP_END_USER_CONTEXT_KEY is required for local end users.")


def create_end_user_context(
    config: DemoConfig,
    app_config: AppMediatedConfig,
    persona: Persona,
):
    """Create an oracledb EndUserSecurityContext for a selected local end user."""
    import oracledb

    validate_app_context_config(config, app_config)
    return oracledb.create_end_user_security_context(
        end_user_identity=(persona.db_username, app_config.end_user_context_key),
        database_access_token=app_config.database_access_token,
        attributes=app_config.context_attributes or None,
    )


def _query_on_connection(connection: Any, sql: str) -> QueryResult:
    with connection.cursor() as cursor:
        cursor.execute(sql)
        columns = tuple(column[0].lower() for column in (cursor.description or ()))
        rows = tuple(tuple(row) for row in cursor.fetchall())
    return QueryResult(columns=columns, rows=rows)


def query_on_connection_with_context(
    connection: Any,
    *,
    context: Any,
    sql: str,
    shared_db_user: str,
    end_user: str,
) -> AppMediatedQueryResult:
    """Attach context, execute a SELECT, and always clear context afterwards."""
    normalized_sql = normalize_select_sql(sql)
    context_attached = False
    context_cleared = False
    query_result: QueryResult | None = None

    try:
        connection.set_end_user_security_context(context)
        context_attached = True
        query_result = _query_on_connection(connection, normalized_sql)
    finally:
        if context_attached:
            connection.clear_end_user_security_context()
            context_cleared = True

    if query_result is None:
        raise RuntimeError("Query did not produce a result.")

    return AppMediatedQueryResult(
        columns=query_result.columns,
        rows=query_result.rows,
        shared_db_user=shared_db_user,
        end_user=end_user,
        context_attached=context_attached,
        context_cleared=context_cleared,
    )


def query_as_end_user_via_app(
    config: DemoConfig,
    app_config: AppMediatedConfig,
    persona: Persona,
    sql: str,
) -> AppMediatedQueryResult:
    """Run a SELECT through the shared app DB user with end-user context."""
    context = create_end_user_context(config, app_config, persona)
    with connect_as_app(config, app_config) as connection:
        return query_on_connection_with_context(
            connection,
            context=context,
            sql=sql,
            shared_db_user=app_config.app_username,
            end_user=persona.db_username,
        )
