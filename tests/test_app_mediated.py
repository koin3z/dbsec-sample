import sys
import types
from typing import Any

import pytest

from deepsec_demo.app_mediated import (
    create_end_user_context,
    query_on_connection_with_context,
    validate_app_context_config,
)
from deepsec_demo.config import AppMediatedConfig, ConfigError, DemoConfig
from deepsec_demo.personas import PERSONAS


def _demo_config(driver_mode: str = "thin") -> DemoConfig:
    return DemoConfig(
        host="localhost",
        port=1521,
        service_name="FREEPDB1",
        protocol="tcp",
        wallet_location=None,
        demo_schema="DEMO_HR",
        default_password="change_me",
        driver_mode=driver_mode,
    )


def _app_config(**overrides: Any) -> AppMediatedConfig:
    values = {
        "app_username": "DEEPSEC_APP",
        "app_password": "change_me",
        "security_context_mode": "local",
        "database_access_token": "token",
        "end_user_context_key": "context-key",
        "context_attributes": {},
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

    def set_end_user_security_context(self, context: object) -> None:
        self.calls.append("set")
        self.context = context

    def clear_end_user_security_context(self) -> None:
        self.calls.append("clear")

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)


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


def test_validate_app_context_config_requires_thin_mode() -> None:
    with pytest.raises(ConfigError, match="Thin mode"):
        validate_app_context_config(_demo_config(driver_mode="thick"), _app_config())


def test_validate_app_context_config_requires_token_and_key() -> None:
    with pytest.raises(ConfigError, match="APP_DATABASE_ACCESS_TOKEN"):
        validate_app_context_config(
            _demo_config(),
            _app_config(database_access_token=None),
        )

    with pytest.raises(ConfigError, match="APP_END_USER_CONTEXT_KEY"):
        validate_app_context_config(
            _demo_config(),
            _app_config(end_user_context_key=None),
        )


def test_create_end_user_context_uses_local_end_user_identity_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_oracledb = types.SimpleNamespace(
        create_end_user_security_context=lambda **kwargs: kwargs
    )
    monkeypatch.setitem(sys.modules, "oracledb", fake_oracledb)

    payload = create_end_user_context(
        _demo_config(),
        _app_config(context_attributes={"purpose": "demo"}),
        PERSONAS["staff_tokyo"],
    )

    assert payload["end_user_identity"] == ("staff_tokyo", "context-key")
    assert payload["database_access_token"] == "token"
    assert payload["attributes"] == {"purpose": "demo"}
    assert "data_roles" not in payload
