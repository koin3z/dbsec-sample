from pathlib import Path

import pytest

from deepsec_demo.config import ConfigError, load_app_mediated_config, load_config


PHASE2_ENV_NAMES = [
    "APP_DB_AUTH_MODE",
    "APP_DB_USERNAME",
    "APP_DB_PASSWORD",
    "APP_SECURITY_CONTEXT_MODE",
    "APP_CONTEXT_ATTRIBUTES_JSON",
    "IDENTITY_DOMAIN_URL",
    "DEMO_APP_TOKEN_URL",
    "DEMO_APP_CLIENT_ID",
    "DEMO_APP_CLIENT_SECRET",
    "DEMO_APP_DATABASE_SCOPE",
    "APP_END_USER_CONTEXT_KEY",
    "APP_DATA_ROLES",
    "APP_TOKEN_REQUEST_TIMEOUT",
    "PHASE2_APP_DIRECTORY_DATA_ROLE",
    "PHASE2_APP_SENSITIVE_DATA_ROLE",
]


def _clear_phase2_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in PHASE2_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_load_config_defaults_to_thin_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in [
        "ORACLE_DRIVER_MODE",
        "ORACLE_CLIENT_LIB_DIR",
        "ORACLE_CLIENT_CONFIG_DIR",
        "ORACLE_WALLET_LOCATION",
    ]:
        monkeypatch.delenv(name, raising=False)

    config = load_config(env_file=None)

    assert config.driver_mode == "thin"
    assert config.client_lib_dir is None
    assert config.client_config_dir is None


def test_load_config_accepts_thick_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORACLE_DRIVER_MODE", "thick")
    monkeypatch.setenv("ORACLE_CLIENT_LIB_DIR", "/opt/oracle/instantclient")
    monkeypatch.setenv("ORACLE_CLIENT_CONFIG_DIR", "/opt/oracle/network/admin")

    config = load_config(env_file=None)

    assert config.driver_mode == "thick"
    assert config.client_lib_dir == "/opt/oracle/instantclient"
    assert config.client_config_dir == "/opt/oracle/network/admin"


def test_wallet_location_defaults_client_config_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORACLE_DRIVER_MODE", "thick")
    monkeypatch.setenv("ORACLE_WALLET_LOCATION", "/opt/oracle/wallet")
    monkeypatch.delenv("ORACLE_CLIENT_CONFIG_DIR", raising=False)

    config = load_config(env_file=None)

    assert config.wallet_location == "/opt/oracle/wallet"
    assert config.client_config_dir == "/opt/oracle/wallet"


def test_invalid_driver_mode_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORACLE_DRIVER_MODE", "oci")

    with pytest.raises(ConfigError, match="ORACLE_DRIVER_MODE"):
        load_config(env_file=None)


def test_env_example_documents_thick_mode() -> None:
    env_example = Path(".env.example").read_text(encoding="utf-8")
    assert "ORACLE_DRIVER_MODE=thin" in env_example
    assert "ORACLE_CLIENT_LIB_DIR=" in env_example
    assert "ORACLE_CLIENT_CONFIG_DIR=" in env_example


def test_load_app_mediated_config_reads_password_local_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_phase2_env(monkeypatch)
    monkeypatch.setenv("ORACLE_DRIVER_MODE", "thin")
    monkeypatch.setenv("APP_DB_AUTH_MODE", "password")
    monkeypatch.setenv("APP_DB_USERNAME", "DEEPSEC_APP")
    monkeypatch.setenv("APP_DB_PASSWORD", "app_password")
    monkeypatch.setenv("APP_SECURITY_CONTEXT_MODE", "local")
    monkeypatch.setenv(
        "APP_CONTEXT_ATTRIBUTES_JSON",
        '{"purpose":"demo","enabled":true}',
    )

    _, app_config = load_app_mediated_config(env_file=None)

    assert app_config.app_username == "DEEPSEC_APP"
    assert app_config.app_password == "app_password"
    assert app_config.app_auth_mode == "password"
    assert app_config.security_context_mode == "local"
    assert app_config.context_attributes == {"purpose": "demo", "enabled": True}


def test_load_app_mediated_config_reads_identity_domain_client_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_phase2_env(monkeypatch)
    monkeypatch.setenv("ORACLE_DRIVER_MODE", "thin")
    monkeypatch.setenv("APP_DB_AUTH_MODE", "client_credentials")
    monkeypatch.setenv("APP_DB_USERNAME", "DEEPSEC_APP")
    monkeypatch.setenv("APP_SECURITY_CONTEXT_MODE", "identity_domain_client_credentials")
    monkeypatch.setenv("IDENTITY_DOMAIN_URL", "https://idcs.example.com:443")
    monkeypatch.setenv("DEMO_APP_CLIENT_ID", "demo-client")
    monkeypatch.setenv("DEMO_APP_CLIENT_SECRET", "demo-secret")
    monkeypatch.setenv("DEMO_APP_DATABASE_SCOPE", "db-scope")
    monkeypatch.setenv("APP_END_USER_CONTEXT_KEY", "lookup-key")
    monkeypatch.setenv("APP_DATA_ROLES", "APP_DIRECTORY_LOOKUP_ROLE, APP_SENSITIVE_LOOKUP_ROLE")
    monkeypatch.setenv("APP_TOKEN_REQUEST_TIMEOUT", "7")

    _, app_config = load_app_mediated_config(env_file=None)

    assert app_config.app_auth_mode == "client_credentials"
    assert app_config.app_password == ""
    assert app_config.security_context_mode == "identity_domain_client_credentials"
    assert app_config.identity_domain_url == "https://idcs.example.com:443"
    assert app_config.demo_app_token_url is None
    assert app_config.demo_app_client_id == "demo-client"
    assert app_config.demo_app_client_secret == "demo-secret"
    assert app_config.demo_app_database_scope == "db-scope"
    assert app_config.end_user_context_key == "lookup-key"
    assert app_config.application_data_roles == (
        "APP_DIRECTORY_LOOKUP_ROLE",
        "APP_SENSITIVE_LOOKUP_ROLE",
    )
    assert app_config.token_request_timeout == 7


def test_load_app_mediated_config_accepts_context_mode_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_phase2_env(monkeypatch)
    monkeypatch.setenv("APP_SECURITY_CONTEXT_MODE", "client_credentials")
    monkeypatch.setenv("IDENTITY_DOMAIN_URL", "https://idcs.example.com")
    monkeypatch.setenv("DEMO_APP_CLIENT_ID", "demo-client")
    monkeypatch.setenv("DEMO_APP_CLIENT_SECRET", "demo-secret")
    monkeypatch.setenv("DEMO_APP_DATABASE_SCOPE", "db-scope")
    monkeypatch.setenv("APP_END_USER_CONTEXT_KEY", "lookup-key")

    _, app_config = load_app_mediated_config(env_file=None)

    assert app_config.security_context_mode == "identity_domain_client_credentials"


def test_load_app_mediated_config_rejects_unknown_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_phase2_env(monkeypatch)
    monkeypatch.setenv("APP_SECURITY_CONTEXT_MODE", "iam")

    with pytest.raises(ConfigError, match="APP_SECURITY_CONTEXT_MODE"):
        load_app_mediated_config(env_file=None)


def test_load_app_mediated_config_rejects_missing_identity_domain_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_phase2_env(monkeypatch)
    monkeypatch.setenv("APP_DB_AUTH_MODE", "client_credentials")
    monkeypatch.setenv("DEMO_APP_CLIENT_ID", "demo-client")

    with pytest.raises(ConfigError, match="Missing Identity Domain"):
        load_app_mediated_config(env_file=None)


def test_load_app_mediated_config_rejects_missing_end_user_context_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_phase2_env(monkeypatch)
    monkeypatch.setenv("APP_SECURITY_CONTEXT_MODE", "identity_domain_client_credentials")
    monkeypatch.setenv("IDENTITY_DOMAIN_URL", "https://idcs.example.com")
    monkeypatch.setenv("DEMO_APP_CLIENT_ID", "demo-client")
    monkeypatch.setenv("DEMO_APP_CLIENT_SECRET", "demo-secret")
    monkeypatch.setenv("DEMO_APP_DATABASE_SCOPE", "db-scope")

    with pytest.raises(ConfigError, match="APP_END_USER_CONTEXT_KEY"):
        load_app_mediated_config(env_file=None)


def test_load_app_mediated_config_rejects_non_object_attributes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_phase2_env(monkeypatch)
    monkeypatch.setenv("APP_SECURITY_CONTEXT_MODE", "local")
    monkeypatch.setenv("APP_CONTEXT_ATTRIBUTES_JSON", "[]")

    with pytest.raises(ConfigError, match="APP_CONTEXT_ATTRIBUTES_JSON"):
        load_app_mediated_config(env_file=None)
