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
    app_password: str = field(repr=False)
    security_context_mode: str = "local"
    database_access_token: str | None = field(default=None, repr=False)
    end_user_context_key: str | None = field(default=None, repr=False)
    context_attributes: dict[str, object] = field(default_factory=dict)


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


def load_app_mediated_config(
    env_file: str | Path | None = ".env",
) -> tuple[DemoConfig, AppMediatedConfig]:
    """Load Phase 2 application-mediated connection settings."""
    demo_config = load_config(env_file)
    security_context_mode = _env("APP_SECURITY_CONTEXT_MODE", "local").lower()
    if security_context_mode != "local":
        raise ConfigError("APP_SECURITY_CONTEXT_MODE currently supports only local.")

    app_username = _env("APP_DB_USERNAME", "DEEPSEC_APP")
    app_password = _env("APP_DB_PASSWORD", "change_me")
    if not app_username:
        raise ConfigError("APP_DB_USERNAME is required for Phase 2.")
    if not app_password:
        raise ConfigError("APP_DB_PASSWORD is required for Phase 2.")

    return demo_config, AppMediatedConfig(
        app_username=app_username,
        app_password=app_password,
        security_context_mode=security_context_mode,
        database_access_token=_env("APP_DATABASE_ACCESS_TOKEN") or None,
        end_user_context_key=_env("APP_END_USER_CONTEXT_KEY") or None,
        context_attributes=_env_json_object("APP_CONTEXT_ATTRIBUTES_JSON"),
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
