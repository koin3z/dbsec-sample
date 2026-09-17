import sys
import types
from typing import Any

import pytest

from deepsec_demo import app_mediated
from deepsec_demo.app_mediated import (
    build_end_user_context_provider,
    build_identity_domain_token_client,
    connect_as_app,
    create_end_user_context,
    query_as_end_user_via_app,
    query_on_connection_with_context,
    validate_app_context_config,
)
from deepsec_demo.config import AppMediatedConfig, ConfigError, DemoConfig
from deepsec_demo.context_providers.client_credentials import (
    IdentityDomainClientCredentialsProvider,
)
from deepsec_demo.context_providers.token_free import TokenFreeEndUserContextProvider
from deepsec_demo.personas import PERSONAS


def _demo_config(driver_mode: str = "thin", protocol: str = "tcp") -> DemoConfig:
    return DemoConfig(
        host="localhost",
        port=1521,
        service_name="FREEPDB1",
        protocol=protocol,
        wallet_location=None,
        demo_schema="DEMO_HR",
        default_password="change_me",
        driver_mode=driver_mode,
    )


def _app_config(**overrides: Any) -> AppMediatedConfig:
    values = {
        "app_username": "DEEPSEC_APP",
        "app_password": "change_me",
        "app_auth_mode": "password",
        "security_context_mode": "local",
        "context_attributes": {},
    }
    values.update(overrides)
    return AppMediatedConfig(**values)


def _identity_app_config(**overrides: Any) -> AppMediatedConfig:
    values = {
        "app_username": "DEEPSEC_APP",
        "app_password": "",
        "app_auth_mode": "client_credentials",
        "security_context_mode": "identity_domain_client_credentials",
        "identity_domain_url": "https://idcs.example.com:443",
        "demo_app_client_id": "demo-client",
        "demo_app_client_secret": "demo-secret",
        "demo_app_database_scope": "db-scope",
        "end_user_context_key": "lookup-key",
        "application_data_roles": (
            "APP_DIRECTORY_LOOKUP_ROLE",
            "APP_SENSITIVE_LOOKUP_ROLE",
        ),
        "context_attributes": {"purpose": "demo"},
    }
    values.update(overrides)
    return AppMediatedConfig(**values)


class FakeCursor:
    description = (("EMPLOYEE_ID",), ("DISPLAY_NAME",))

    def __init__(self, connection: "FakeConnection") -> None:
        self.connection = connection

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.connection.cursor_closed = True

    def execute(self, sql: str) -> None:
        self.connection.executed_sql = sql
        if self.connection.execute_error is not None:
            raise self.connection.execute_error

    def fetchall(self) -> list[tuple[int, str]]:
        return [(1001, "Tokyo Staff")]


class FakeConnection:
    def __init__(self, execute_error: Exception | None = None) -> None:
        self.calls: list[str] = []
        self.cursor_closed = False
        self.execute_error = execute_error
        self.executed_sql = ""
        self.call_timeout = None
        self.closed = False

    def set_end_user_security_context(self, context: object) -> None:
        self.calls.append("set")
        self.context = context

    def clear_end_user_security_context(self) -> None:
        self.calls.append("clear")

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def close(self) -> None:
        self.closed = True


def test_query_with_context_attaches_executes_and_clears() -> None:
    connection = FakeConnection()

    result = query_on_connection_with_context(
        connection,
        context=object(),
        sql="SELECT employee_id, display_name FROM demo_hr.employees",
        shared_db_user="DEEPSEC_APP",
        end_user="staff_tokyo",
    )

    assert connection.calls == ["set", "clear"]
    assert connection.cursor_closed is True
    assert connection.executed_sql.startswith("SELECT")
    assert result.columns == ("employee_id", "display_name")
    assert result.rows == ((1001, "Tokyo Staff"),)
    assert result.shared_db_user == "DEEPSEC_APP"
    assert result.end_user == "staff_tokyo"
    assert result.context_attached is True
    assert result.context_cleared is True


def test_query_with_context_clears_when_query_raises() -> None:
    connection = FakeConnection(execute_error=RuntimeError("db failed"))

    with pytest.raises(RuntimeError, match="db failed"):
        query_on_connection_with_context(
            connection,
            context=object(),
            sql="SELECT employee_id FROM demo_hr.employees",
            shared_db_user="DEEPSEC_APP",
            end_user="staff_tokyo",
        )

    assert connection.calls == ["set", "clear"]
    assert connection.cursor_closed is True


def test_validate_app_context_config_accepts_non_token_connection_settings() -> None:
    validate_app_context_config(_demo_config(driver_mode="thick"), _app_config())


def test_validate_app_context_config_accepts_identity_domain_client_credentials() -> None:
    validate_app_context_config(_demo_config(driver_mode="thin", protocol="tcps"), _identity_app_config())


def test_validate_app_context_config_rejects_identity_domain_without_tcps() -> None:
    with pytest.raises(ConfigError, match="ORACLE_PROTOCOL=tcps"):
        validate_app_context_config(_demo_config(driver_mode="thin"), _identity_app_config())

def test_validate_app_context_config_rejects_identity_domain_in_thick_mode() -> None:
    with pytest.raises(ConfigError, match="ORACLE_DRIVER_MODE=thin"):
        validate_app_context_config(_demo_config(driver_mode="thick"), _identity_app_config())


def test_build_identity_domain_token_client_derives_token_url() -> None:
    client = build_identity_domain_token_client(_identity_app_config())

    assert client.token_url == "https://idcs.example.com:443/oauth2/v1/token"
    assert client.client_id == "demo-client"
    assert client.scope == "db-scope"


def test_build_end_user_context_provider_uses_identity_domain_config() -> None:
    provider = build_end_user_context_provider(_identity_app_config())

    assert isinstance(provider, IdentityDomainClientCredentialsProvider)
    assert provider.supports_real_dds_context is True
    assert provider.data_roles == (
        "APP_DIRECTORY_LOOKUP_ROLE",
        "APP_SENSITIVE_LOOKUP_ROLE",
    )
    assert provider.attributes == {"purpose": "demo"}


def test_build_end_user_context_provider_keeps_local_fail_closed() -> None:
    provider = build_end_user_context_provider(_app_config())

    assert isinstance(provider, TokenFreeEndUserContextProvider)
    assert provider.supports_real_dds_context is False


def test_create_end_user_context_rejects_local_disabled_provider() -> None:
    with pytest.raises(ConfigError, match="database-access token"):
        create_end_user_context(
            _demo_config(),
            _app_config(context_attributes={"purpose": "demo"}),
            PERSONAS["staff_tokyo"],
        )


def test_create_end_user_context_uses_identity_domain_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = {}

    def create_end_user_security_context(**kwargs):
        created.update(kwargs)
        return {"payload": kwargs}

    monkeypatch.setitem(
        sys.modules,
        "oracledb",
        types.SimpleNamespace(
            create_end_user_security_context=create_end_user_security_context
        ),
    )

    class FakeTokenClient:
        is_configured = True

        def require_configured(self):
            return None

        def get_access_token(self):
            return "db-token"

    monkeypatch.setattr(
        app_mediated,
        "build_identity_domain_token_client",
        lambda app_config: FakeTokenClient(),
    )

    context = create_end_user_context(
        _demo_config(protocol="tcps"),
        _identity_app_config(app_auth_mode="password", app_password="change_me"),
        PERSONAS["staff_tokyo"],
    )

    assert context == {"payload": created}
    assert created == {
        "end_user_identity": ("staff_tokyo", "lookup-key"),
        "database_access_token": "db-token",
        "data_roles": ["APP_DIRECTORY_LOOKUP_ROLE", "APP_SENSITIVE_LOOKUP_ROLE"],
        "attributes": {"purpose": "demo"},
    }


def test_connect_as_app_uses_password_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    fake_connection = FakeConnection()

    def connect(**kwargs):
        calls.append(kwargs)
        return fake_connection

    monkeypatch.setitem(sys.modules, "oracledb", types.SimpleNamespace(connect=connect))

    connection = connect_as_app(_demo_config(), _app_config())

    assert connection is fake_connection
    assert calls == [
        {
            "dsn": "localhost:1521/FREEPDB1",
            "user": "DEEPSEC_APP",
            "password": "change_me",
        }
    ]
    assert fake_connection.call_timeout == 5000


def test_connect_as_app_rejects_client_credentials_without_tcps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_mediated,
        "build_identity_domain_token_client",
        lambda app_config: (_ for _ in ()).throw(AssertionError("token requested")),
    )

    with pytest.raises(ConfigError, match="ORACLE_PROTOCOL=tcps"):
        connect_as_app(_demo_config(), _identity_app_config())


def test_connect_as_app_uses_client_credentials_access_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    fake_connection = FakeConnection()

    def connect(**kwargs):
        calls.append(kwargs)
        return fake_connection

    class FakeTokenClient:
        def get_access_token(self):
            return "db-token"

    monkeypatch.setitem(sys.modules, "oracledb", types.SimpleNamespace(connect=connect))
    monkeypatch.setattr(
        app_mediated,
        "build_identity_domain_token_client",
        lambda app_config: FakeTokenClient(),
    )

    connection = connect_as_app(_demo_config(protocol="tcps"), _identity_app_config())

    assert connection is fake_connection
    assert calls == [{"dsn": "tcps://localhost:1521/FREEPDB1", "access_token": "db-token"}]
    assert fake_connection.call_timeout == 5000


def test_query_as_end_user_via_app_default_provider_fails_before_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_connect(*args: object, **kwargs: object) -> object:
        raise AssertionError("connect_as_app should not be called")

    monkeypatch.setattr(app_mediated, "connect_as_app", fail_connect)

    with pytest.raises(RuntimeError, match="Protected queries are disabled"):
        query_as_end_user_via_app(
            _demo_config(),
            _app_config(),
            PERSONAS["staff_tokyo"],
            "SELECT employee_id FROM demo_hr.employees",
        )
