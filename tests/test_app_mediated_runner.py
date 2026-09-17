import pytest

from deepsec_demo.app_mediated_runner import (
    DDS_USERNAME_QUERY,
    run_as_persona_with_shared_user,
    verify_current_end_user_context,
)
from deepsec_demo.context_providers.base import ContextAttachResult
from deepsec_demo.context_providers.token_free import TokenFreeEndUserContextProvider


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.description = None
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.connection.cursor_closed += 1

    def execute(self, sql):
        self.connection.executed_sql.append(sql)
        if sql == DDS_USERNAME_QUERY:
            self.description = (("USERNAME",),)
            self._rows = [(self.connection.ora_username,)]
            return
        if self.connection.query_error is not None:
            raise self.connection.query_error
        self.description = (("EMPLOYEE_ID",), ("DISPLAY_NAME",))
        self._rows = [(1001, "Tokyo Staff")]

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class FakeConnection:
    def __init__(self, ora_username="staff_tokyo", query_error=None):
        self.ora_username = ora_username
        self.query_error = query_error
        self.executed_sql = []
        self.cursor_closed = 0

    def cursor(self):
        return FakeCursor(self)


class FakePool:
    def __init__(self, connection=None):
        self.connection = connection or FakeConnection()
        self.acquired = 0
        self.released = 0

    def acquire(self):
        self.acquired += 1
        return self.connection

    def release(self, connection):
        assert connection is self.connection
        self.released += 1


class SupportedProvider:
    mode = "verified_test_provider"
    supports_real_dds_context = True

    def __init__(self):
        self.attached = []
        self.cleared = 0

    def attach(self, connection, persona):
        self.attached.append(persona)
        return ContextAttachResult(
            mode=self.mode,
            persona=persona,
            verified_username=persona,
            verified_roles=["employee_role"],
            attached=True,
        )

    def clear(self, connection):
        self.cleared += 1


def test_token_free_provider_is_disabled_placeholder():
    provider = TokenFreeEndUserContextProvider()

    assert provider.supports_real_dds_context is False
    with pytest.raises(NotImplementedError, match="No token-free"):
        provider.attach(object(), "staff_tokyo")
    assert provider.clear(object()) is None


def test_runner_fails_closed_before_acquiring_connection_for_disabled_provider():
    pool = FakePool()

    with pytest.raises(RuntimeError, match="Protected queries are disabled"):
        run_as_persona_with_shared_user(
            pool,
            TokenFreeEndUserContextProvider(),
            persona="staff_tokyo",
            sql="SELECT employee_id FROM demo_hr.employees",
            shared_db_user="DEEPSEC_APP",
        )

    assert pool.acquired == 0
    assert pool.connection.executed_sql == []


def test_runner_verifies_ora_end_user_context_before_protected_query():
    provider = SupportedProvider()
    pool = FakePool(FakeConnection(ora_username="staff_tokyo"))

    result = run_as_persona_with_shared_user(
        pool,
        provider,
        persona="staff_tokyo",
        sql="SELECT employee_id, display_name FROM demo_hr.employees",
        shared_db_user="DEEPSEC_APP",
        expected_roles=("employee_role",),
    )

    assert pool.connection.executed_sql == [
        DDS_USERNAME_QUERY,
        "SELECT employee_id, display_name FROM demo_hr.employees",
    ]
    assert result.shared_db_user == "DEEPSEC_APP"
    assert result.end_user == "staff_tokyo"
    assert result.provider_mode == "verified_test_provider"
    assert result.verified_username == "staff_tokyo"
    assert result.verified_roles == ("employee_role",)
    assert result.context_attached is True
    assert result.context_cleared is True
    assert result.rows == ((1001, "Tokyo Staff"),)
    assert provider.cleared == 1
    assert pool.released == 1


def test_runner_refuses_when_database_context_verification_fails():
    provider = SupportedProvider()
    pool = FakePool(FakeConnection(ora_username="manager_tokyo"))

    with pytest.raises(RuntimeError, match="verification failed"):
        run_as_persona_with_shared_user(
            pool,
            provider,
            persona="staff_tokyo",
            sql="SELECT employee_id FROM demo_hr.employees",
            shared_db_user="DEEPSEC_APP",
        )

    assert pool.connection.executed_sql == [DDS_USERNAME_QUERY]
    assert provider.cleared == 1
    assert pool.released == 1


def test_runner_refuses_when_verified_roles_do_not_match_persona():
    provider = SupportedProvider()
    pool = FakePool(FakeConnection(ora_username="staff_tokyo"))

    with pytest.raises(RuntimeError, match="data role verification failed"):
        run_as_persona_with_shared_user(
            pool,
            provider,
            persona="staff_tokyo",
            sql="SELECT employee_id FROM demo_hr.employees",
            shared_db_user="DEEPSEC_APP",
            expected_roles=("manager_role",),
        )

    assert pool.connection.executed_sql == [DDS_USERNAME_QUERY]
    assert provider.cleared == 1
    assert pool.released == 1


def test_runner_clears_and_releases_when_protected_query_raises():
    provider = SupportedProvider()
    pool = FakePool(FakeConnection(query_error=RuntimeError("db failed")))

    with pytest.raises(RuntimeError, match="db failed"):
        run_as_persona_with_shared_user(
            pool,
            provider,
            persona="staff_tokyo",
            sql="SELECT employee_id FROM demo_hr.employees",
            shared_db_user="DEEPSEC_APP",
        )

    assert provider.cleared == 1
    assert pool.released == 1


def test_verify_current_end_user_context_returns_verified_username():
    connection = FakeConnection(ora_username="ai_assistant")

    assert verify_current_end_user_context(connection, "ai_assistant") == "ai_assistant"
