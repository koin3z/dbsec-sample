"""Application-mediated Deep Data Security helpers for Phase 2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from deepsec_demo.app_mediated_runner import (
    AppMediatedRunResult,
    run_as_persona_with_shared_user,
)
from deepsec_demo.config import AppMediatedConfig, ConfigError, DemoConfig
from deepsec_demo.context_providers.base import EndUserContextProvider
from deepsec_demo.context_providers.client_credentials import (
    IdentityDomainClientCredentialsProvider,
    OAuthClientCredentialsTokenClient,
    derive_token_url,
)
from deepsec_demo.context_providers.token_free import TokenFreeEndUserContextProvider
from deepsec_demo.db import QueryResult, ensure_oracle_driver_mode
from deepsec_demo.personas import Persona
from deepsec_demo.sql_safety import normalize_select_sql


@dataclass(frozen=True)
class AppMediatedQueryResult(QueryResult):
    shared_db_user: str
    end_user: str
    context_attached: bool
    context_cleared: bool


def build_identity_domain_token_client(
    app_config: AppMediatedConfig,
) -> OAuthClientCredentialsTokenClient:
    """Build the Identity Domain token client from Phase 2 config."""
    return OAuthClientCredentialsTokenClient(
        token_url=derive_token_url(
            app_config.identity_domain_url,
            app_config.demo_app_token_url,
        ),
        client_id=app_config.demo_app_client_id,
        client_secret=app_config.demo_app_client_secret,
        scope=app_config.demo_app_database_scope,
        timeout=app_config.token_request_timeout,
    )


def build_end_user_context_provider(
    app_config: AppMediatedConfig,
) -> EndUserContextProvider:
    """Select the Phase 2 end-user context provider from configuration."""
    if app_config.security_context_mode == "local":
        return TokenFreeEndUserContextProvider()
    if app_config.security_context_mode == "identity_domain_client_credentials":
        return IdentityDomainClientCredentialsProvider(
            token_client=build_identity_domain_token_client(app_config),
            end_user_context_key=app_config.end_user_context_key,
            data_roles=app_config.application_data_roles,
            attributes=app_config.context_attributes,
        )
    raise ConfigError(
        "APP_SECURITY_CONTEXT_MODE must be local or "
        "identity_domain_client_credentials."
    )


def _require_tcps(config: DemoConfig, setting: str) -> None:
    if config.protocol != "tcps":
        raise ConfigError(
            f"{setting} requires ORACLE_PROTOCOL=tcps. "
            "Use the database TCPS listener/port and configure wallet or "
            "server certificate settings as required by the target database."
        )


def connect_as_app(config: DemoConfig, app_config: AppMediatedConfig):
    """Open the shared application database connection for Phase 2."""
    import oracledb

    ensure_oracle_driver_mode(config)
    kwargs: dict[str, Any] = {"dsn": config.dsn}
    if app_config.app_auth_mode == "password":
        if not app_config.app_password:
            raise ConfigError("APP_DB_PASSWORD is required when APP_DB_AUTH_MODE=password.")
        kwargs["user"] = app_config.app_username
        kwargs["password"] = app_config.app_password
    elif app_config.app_auth_mode == "client_credentials":
        if config.driver_mode != "thin":
            raise ConfigError(
                "APP_DB_AUTH_MODE=client_credentials requires ORACLE_DRIVER_MODE=thin."
            )
        _require_tcps(config, "APP_DB_AUTH_MODE=client_credentials")
        token = build_identity_domain_token_client(app_config).get_access_token()
        kwargs["access_token"] = token
    else:
        raise ConfigError("APP_DB_AUTH_MODE must be password or client_credentials.")

    if config.wallet_location:
        kwargs["config_dir"] = config.wallet_location
        kwargs["wallet_location"] = config.wallet_location
    connection = oracledb.connect(**kwargs)
    connection.call_timeout = config.connect_timeout * 1000
    return connection


def validate_app_context_config(config: DemoConfig, app_config: AppMediatedConfig) -> None:
    """Validate Phase 2 settings before creating a security context payload."""
    if app_config.app_auth_mode == "client_credentials" and config.driver_mode != "thin":
        raise ConfigError(
            "APP_DB_AUTH_MODE=client_credentials requires ORACLE_DRIVER_MODE=thin."
        )
    if app_config.security_context_mode == "local":
        return
    if app_config.security_context_mode != "identity_domain_client_credentials":
        raise ConfigError(
            "APP_SECURITY_CONTEXT_MODE must be local or "
            "identity_domain_client_credentials."
        )
    if config.driver_mode != "thin":
        raise ConfigError(
            "APP_SECURITY_CONTEXT_MODE=identity_domain_client_credentials "
            "requires ORACLE_DRIVER_MODE=thin."
        )
    _require_tcps(config, "APP_SECURITY_CONTEXT_MODE=identity_domain_client_credentials")
    provider = build_end_user_context_provider(app_config)
    if not isinstance(provider, IdentityDomainClientCredentialsProvider):
        raise ConfigError("Identity Domain provider was not selected.")
    provider.require_configured()


def create_end_user_context(
    config: DemoConfig,
    app_config: AppMediatedConfig,
    persona: Persona,
):
    """Create an official python-oracledb DDS end-user context payload."""
    validate_app_context_config(config, app_config)
    provider = build_end_user_context_provider(app_config)
    create_context = getattr(provider, "create_context", None)
    if create_context is None or not provider.supports_real_dds_context:
        raise ConfigError(getattr(provider, "disabled_reason", "DDS context provider is disabled."))
    return create_context(persona.db_username)


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


class _SingleAppConnectionPool:
    def __init__(self, config: DemoConfig, app_config: AppMediatedConfig) -> None:
        self.config = config
        self.app_config = app_config

    def acquire(self):
        return connect_as_app(self.config, self.app_config)

    def release(self, connection) -> None:
        connection.close()


def query_as_end_user_via_app(
    config: DemoConfig,
    app_config: AppMediatedConfig,
    persona: Persona,
    sql: str,
    provider: EndUserContextProvider | None = None,
) -> AppMediatedRunResult:
    """Run a SELECT through the shared app DB user with end-user context.

    The default local provider is intentionally disabled and fails closed.
    With APP_SECURITY_CONTEXT_MODE=identity_domain_client_credentials, this
    uses the official python-oracledb DDS payload API and verifies
    ORA_END_USER_CONTEXT.username before executing protected SQL.
    """
    if provider is None:
        validate_app_context_config(config, app_config)
    selected_provider = provider or build_end_user_context_provider(app_config)
    provider_roles = getattr(selected_provider, "data_roles", None)
    expected_roles = tuple(provider_roles) if provider_roles is not None else persona.data_roles
    pool = _SingleAppConnectionPool(config, app_config)
    return run_as_persona_with_shared_user(
        pool,
        selected_provider,
        persona=persona.db_username,
        sql=sql,
        shared_db_user=app_config.app_username,
        expected_roles=expected_roles,
    )
