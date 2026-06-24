from pathlib import Path

import pytest

from deepsec_demo.config import ConfigError, load_app_mediated_config, load_config


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

def test_load_app_mediated_config_reads_phase2_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORACLE_DRIVER_MODE", "thin")
    monkeypatch.setenv("APP_DB_USERNAME", "DEEPSEC_APP")
    monkeypatch.setenv("APP_DB_PASSWORD", "app_password")
    monkeypatch.setenv("APP_SECURITY_CONTEXT_MODE", "local")
    monkeypatch.setenv("APP_DATABASE_ACCESS_TOKEN", "token")
    monkeypatch.setenv("APP_END_USER_CONTEXT_KEY", "context-key")
    monkeypatch.setenv(
        "APP_CONTEXT_ATTRIBUTES_JSON",
        '{"purpose":"demo","enabled":true}',
    )

    _, app_config = load_app_mediated_config(env_file=None)

    assert app_config.app_username == "DEEPSEC_APP"
    assert app_config.app_password == "app_password"
    assert app_config.security_context_mode == "local"
    assert app_config.database_access_token == "token"
    assert app_config.end_user_context_key == "context-key"
    assert app_config.context_attributes == {"purpose": "demo", "enabled": True}


def test_load_app_mediated_config_rejects_unknown_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_SECURITY_CONTEXT_MODE", "iam")

    with pytest.raises(ConfigError, match="APP_SECURITY_CONTEXT_MODE"):
        load_app_mediated_config(env_file=None)


def test_load_app_mediated_config_rejects_non_object_attributes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_SECURITY_CONTEXT_MODE", "local")
    monkeypatch.setenv("APP_CONTEXT_ATTRIBUTES_JSON", "[]")

    with pytest.raises(ConfigError, match="APP_CONTEXT_ATTRIBUTES_JSON"):
        load_app_mediated_config(env_file=None)

