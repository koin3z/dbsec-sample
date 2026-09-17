from deepsec_demo.app_mediated_status import (
    CURRENT_USER_QUERY,
    DDS_USERNAME_QUERY,
    SESSION_USER_QUERY,
    check_shared_app_connection,
)
from deepsec_demo.config import AppMediatedConfig, DemoConfig


def _demo_config() -> DemoConfig:
    return DemoConfig(
        host="localhost",
        port=1521,
        service_name="FREEPDB1",
        protocol="tcp",
        wallet_location=None,
        demo_schema="DEMO_HR",
        default_password="change_me",
    )


def _app_config() -> AppMediatedConfig:
    return AppMediatedConfig(
        app_username="DEEPSEC_APP",
        app_password="change_me",
    )


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self._row = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.connection.closed_cursors += 1

    def execute(self, sql):
        self.connection.executed_sql.append(sql)
        if sql == SESSION_USER_QUERY:
            self._row = (self.connection.session_user,)
        elif sql == CURRENT_USER_QUERY:
            self._row = (self.connection.current_user,)
        elif sql == DDS_USERNAME_QUERY:
            if self.connection.dds_error is not None:
                raise self.connection.dds_error
            self._row = (self.connection.dds_username,)
        else:
            raise AssertionError(f"unexpected SQL: {sql}")

    def fetchone(self):
        return self._row


class FakeConnection:
    def __init__(
        self,
        *,
        session_user="DEEPSEC_APP",
        current_user="DEEPSEC_APP",
        dds_username=None,
        dds_error=None,
    ):
        self.session_user = session_user
        self.current_user = current_user
        self.dds_username = dds_username
        self.dds_error = dds_error
        self.executed_sql = []
        self.closed_cursors = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.closed = True

    def cursor(self):
        return FakeCursor(self)


def test_check_shared_app_connection_reads_user_context_without_protected_query():
    connection = FakeConnection(dds_username=None)

    status = check_shared_app_connection(
        _demo_config(),
        _app_config(),
        connection_factory=lambda config, app_config: connection,
    )

    assert status.shared_db_user == "DEEPSEC_APP"
    assert status.session_user == "DEEPSEC_APP"
    assert status.current_user == "DEEPSEC_APP"
    assert status.dds_username is None
    assert status.dds_query_error is None
    assert status.connected_as_expected is True
    assert status.has_active_dds_context is False
    assert connection.executed_sql == [
        SESSION_USER_QUERY,
        CURRENT_USER_QUERY,
        DDS_USERNAME_QUERY,
    ]
    assert connection.closed is True


def test_check_shared_app_connection_reports_dds_query_error():
    connection = FakeConnection(dds_error=RuntimeError("not available"))

    status = check_shared_app_connection(
        _demo_config(),
        _app_config(),
        connection_factory=lambda config, app_config: connection,
    )

    assert status.dds_username is None
    assert "RuntimeError" in status.dds_query_error
    assert status.connected_as_expected is True


def test_check_shared_app_connection_flags_unexpected_session_user():
    connection = FakeConnection(session_user="OTHER_USER")

    status = check_shared_app_connection(
        _demo_config(),
        _app_config(),
        connection_factory=lambda config, app_config: connection,
    )

    assert status.connected_as_expected is False
