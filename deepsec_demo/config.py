"""Configuration loading for the direct-logon demo."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(ValueError):
    """Raised when required demo configuration is missing or invalid."""


@dataclass(frozen=True)
class DemoConfig:
    host: str
    port: int
    service_name: str
    protocol: str
    wallet_location: str | None
    demo_schema: str
    default_password: str = field(repr=False)
    connect_timeout: int = 5
    mode: str = "live"
    driver_mode: str = "thin"
    client_lib_dir: str | None = None
    client_config_dir: str | None = None

    @property
    def dsn(self) -> str:
        if self.protocol == "tcp":
            return f"{self.host}:{self.port}/{self.service_name}"
        return f"{self.protocol}://{self.host}:{self.port}/{self.service_name}"

    @property
    def schema_sql_name(self) -> str:
        return self.demo_schema.upper()


@dataclass(frozen=True)
class AdminConfig:
    user: str
    password: str = field(repr=False)
    mode: str = "sysdba"


@dataclass(frozen=True)
class AppMediatedConfig:
    app_username: str
    app_password: str = field(default="", repr=False)
    app_auth_mode: str = "password"
    security_context_mode: str = "local"
    context_attributes: dict[str, object] = field(default_factory=dict)
    identity_domain_url: str | None = None
    demo_app_token_url: str | None = None
    demo_app_client_id: str | None = None
    demo_app_client_secret: str | None = field(default=None, repr=False)
    demo_app_database_scope: str | None = None
    end_user_context_key: str | None = field(default=None, repr=False)
    application_data_roles: tuple[str, ...] = ()
    token_request_timeout: int = 10


def _load_dotenv(env_file: str | Path | None) -> None:
    if env_file is None:
        return
    path = Path(env_file)
    if path.exists():
        load_dotenv(path, override=False)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    value = _env(name, str(default))
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer.") from exc


def _env_csv(name: str) -> tuple[str, ...]:
    value = _env(name)
    if not value:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def load_config(env_file: str | Path | None = ".env") -> DemoConfig:
    """Load non-admin demo configuration from environment and optional .env."""
    _load_dotenv(env_file)

    protocol = _env("ORACLE_PROTOCOL", "tcp").lower()
    if protocol not in {"tcp", "tcps"}:
        raise ConfigError("ORACLE_PROTOCOL must be either tcp or tcps.")

    mode = _env("DEMO_MODE", "live").lower()
    if mode not in {"live", "mock"}:
        raise ConfigError("DEMO_MODE must be either live or mock.")

    driver_mode = _env("ORACLE_DRIVER_MODE", "thin").lower()
    if driver_mode not in {"thin", "thick"}:
        raise ConfigError("ORACLE_DRIVER_MODE must be either thin or thick.")

    wallet_location = _env("ORACLE_WALLET_LOCATION") or None
    client_config_dir = _env("ORACLE_CLIENT_CONFIG_DIR") or wallet_location

    config = DemoConfig(
        host=_env("ORACLE_HOST", "localhost"),
        port=_env_int("ORACLE_PORT", 1521),
        service_name=_env("ORACLE_SERVICE_NAME", "FREEPDB1"),
        protocol=protocol,
        wallet_location=wallet_location,
        demo_schema=_env("DEMO_SCHEMA", "DEMO_HR"),
        default_password=_env("DEMO_DEFAULT_PASSWORD", "change_me"),
        connect_timeout=_env_int("DEMO_CONNECT_TIMEOUT", 5),
        mode=mode,
        driver_mode=driver_mode,
        client_lib_dir=_env("ORACLE_CLIENT_LIB_DIR") or None,
        client_config_dir=client_config_dir or None,
    )

    missing = [
        name
        for name, value in {
            "ORACLE_HOST": config.host,
            "ORACLE_SERVICE_NAME": config.service_name,
            "DEMO_SCHEMA": config.demo_schema,
            "DEMO_DEFAULT_PASSWORD": config.default_password,
        }.items()
        if not value
    ]
    if missing:
        raise ConfigError(f"Missing required environment values: {', '.join(missing)}")

    return config


def _env_json_object(name: str) -> dict[str, object]:
    value = _env(name)
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{name} must be a JSON object.") from exc
    if not isinstance(parsed, dict):
        raise ConfigError(f"{name} must be a JSON object.")
    return parsed


def _normalized_context_mode() -> str:
    mode = _env("APP_SECURITY_CONTEXT_MODE", "local").lower()
    if mode == "client_credentials":
        return "identity_domain_client_credentials"
    if mode not in {"local", "identity_domain_client_credentials"}:
        raise ConfigError(
            "APP_SECURITY_CONTEXT_MODE must be local or "
            "identity_domain_client_credentials."
        )
    return mode


def _application_data_roles_from_env() -> tuple[str, ...]:
    explicit_roles = _env_csv("APP_DATA_ROLES")
    if explicit_roles:
        return explicit_roles
    return tuple(
        role
        for role in (
            _env("PHASE2_APP_DIRECTORY_DATA_ROLE", "APP_DIRECTORY_LOOKUP_ROLE"),
            _env("PHASE2_APP_SENSITIVE_DATA_ROLE", "APP_SENSITIVE_LOOKUP_ROLE"),
        )
        if role
    )


def load_app_mediated_config(
    env_file: str | Path | None = ".env",
) -> tuple[DemoConfig, AppMediatedConfig]:
    """Load Phase 2 application-mediated connection settings."""
    demo_config = load_config(env_file)

    app_auth_mode = _env("APP_DB_AUTH_MODE", "password").lower()
    if app_auth_mode not in {"password", "client_credentials"}:
        raise ConfigError("APP_DB_AUTH_MODE must be password or client_credentials.")

    security_context_mode = _normalized_context_mode()
    app_username = _env("APP_DB_USERNAME", "DEEPSEC_APP")
    app_password = _env("APP_DB_PASSWORD", "change_me" if app_auth_mode == "password" else "")
    if not app_username:
        raise ConfigError("APP_DB_USERNAME is required for Phase 2.")
    if app_auth_mode == "password" and not app_password:
        raise ConfigError("APP_DB_PASSWORD is required when APP_DB_AUTH_MODE=password.")

    identity_domain_url = _env("IDENTITY_DOMAIN_URL") or None
    token_url = _env("DEMO_APP_TOKEN_URL") or None
    demo_app_client_id = _env("DEMO_APP_CLIENT_ID") or None
    demo_app_client_secret = _env("DEMO_APP_CLIENT_SECRET") or None
    demo_app_database_scope = _env("DEMO_APP_DATABASE_SCOPE") or None
    end_user_context_key = _env("APP_END_USER_CONTEXT_KEY") or None

    uses_identity_domain_token = (
        app_auth_mode == "client_credentials"
        or security_context_mode == "identity_domain_client_credentials"
    )
    if uses_identity_domain_token:
        missing = [
            name
            for name, value in {
                "IDENTITY_DOMAIN_URL or DEMO_APP_TOKEN_URL": identity_domain_url or token_url,
                "DEMO_APP_CLIENT_ID": demo_app_client_id,
                "DEMO_APP_CLIENT_SECRET": demo_app_client_secret,
                "DEMO_APP_DATABASE_SCOPE": demo_app_database_scope,
            }.items()
            if not value
        ]
        if missing:
            raise ConfigError(
                "Missing Identity Domain client-credentials settings: "
                + ", ".join(missing)
            )
    if security_context_mode == "identity_domain_client_credentials" and not end_user_context_key:
        raise ConfigError("APP_END_USER_CONTEXT_KEY is required for Phase 2 DDS context.")

    return demo_config, AppMediatedConfig(
        app_username=app_username,
        app_password=app_password,
        app_auth_mode=app_auth_mode,
        security_context_mode=security_context_mode,
        context_attributes=_env_json_object("APP_CONTEXT_ATTRIBUTES_JSON"),
        identity_domain_url=identity_domain_url,
        demo_app_token_url=token_url,
        demo_app_client_id=demo_app_client_id,
        demo_app_client_secret=demo_app_client_secret,
        demo_app_database_scope=demo_app_database_scope,
        end_user_context_key=end_user_context_key,
        application_data_roles=_application_data_roles_from_env(),
        token_request_timeout=_env_int("APP_TOKEN_REQUEST_TIMEOUT", 10),
    )


def load_admin_config(
    env_file: str | Path | None = ".env",
) -> tuple[DemoConfig, AdminConfig]:
    """Load admin connection settings for SQL setup scripts."""
    demo_config = load_config(env_file)
    admin_user = _env("ORACLE_ADMIN_USER", "sys")
    admin_password = _env("ORACLE_ADMIN_PASSWORD")
    admin_mode = _env("ORACLE_ADMIN_MODE", "sysdba").lower()

    if not admin_user:
        raise ConfigError("ORACLE_ADMIN_USER is required for admin SQL execution.")
    if not admin_password:
        raise ConfigError("ORACLE_ADMIN_PASSWORD is required for admin SQL execution.")
    if admin_mode not in {"default", "sysdba", "sysoper"}:
        raise ConfigError("ORACLE_ADMIN_MODE must be default, sysdba, or sysoper.")

    return demo_config, AdminConfig(
        user=admin_user,
        password=admin_password,
        mode=admin_mode,
    )
