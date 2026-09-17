"""Status checks for the Phase 2 shared application DB user."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from deepsec_demo.app_mediated import connect_as_app
from deepsec_demo.app_mediated_runner import DDS_USERNAME_QUERY
from deepsec_demo.config import AppMediatedConfig, DemoConfig

SESSION_USER_QUERY = "SELECT SYS_CONTEXT('USERENV', 'SESSION_USER') FROM dual"
CURRENT_USER_QUERY = "SELECT SYS_CONTEXT('USERENV', 'CURRENT_USER') FROM dual"


@dataclass(frozen=True)
class SharedAppConnectionStatus:
    shared_db_user: str
    session_user: str | None
    current_user: str | None
    dds_username: str | None
    dds_query_error: str | None = None

    @property
    def connected_as_expected(self) -> bool:
        return (self.session_user or "").upper() == self.shared_db_user.upper()

    @property
    def has_active_dds_context(self) -> bool:
        return self.dds_username is not None


def _fetch_scalar(connection: Any, sql: str) -> Any:
    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
    return None if row is None else row[0]


def check_shared_app_connection(
    config: DemoConfig,
    app_config: AppMediatedConfig,
    *,
    connection_factory: Callable[[DemoConfig, AppMediatedConfig], Any] = connect_as_app,
) -> SharedAppConnectionStatus:
    """Connect as the shared app user without running protected table queries."""
    with connection_factory(config, app_config) as connection:
        session_user = _fetch_scalar(connection, SESSION_USER_QUERY)
        current_user = _fetch_scalar(connection, CURRENT_USER_QUERY)
        dds_username = None
        dds_query_error = None
        try:
            dds_username = _fetch_scalar(connection, DDS_USERNAME_QUERY)
        except Exception as exc:  # pragma: no cover - driver/database-specific detail
            dds_query_error = f"{type(exc).__name__}: {exc}"

    return SharedAppConnectionStatus(
        shared_db_user=app_config.app_username,
        session_user=None if session_user is None else str(session_user),
        current_user=None if current_user is None else str(current_user),
        dds_username=None if dds_username is None else str(dds_username),
        dds_query_error=dds_query_error,
    )
