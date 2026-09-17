"""Guarded runner for Phase 2 application-mediated DDS demos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from deepsec_demo.context_providers.base import (
    ContextAttachResult,
    EndUserContextProvider,
)
from deepsec_demo.db import QueryResult
from deepsec_demo.sql_safety import normalize_select_sql

DDS_USERNAME_QUERY = "SELECT ORA_END_USER_CONTEXT.username FROM dual"


class SharedConnectionPool(Protocol):
    def acquire(self) -> Any:
        """Return a shared application DB connection."""

    def release(self, connection: Any) -> None:
        """Return or close the shared application DB connection."""


@dataclass(frozen=True)
class AppMediatedRunResult(QueryResult):
    shared_db_user: str
    end_user: str
    provider_mode: str
    verified_username: str
    verified_roles: tuple[str, ...]
    context_attached: bool
    context_cleared: bool


def _query_on_connection(connection: Any, sql: str) -> QueryResult:
    with connection.cursor() as cursor:
        cursor.execute(sql)
        columns = tuple(column[0].lower() for column in (cursor.description or ()))
        rows = tuple(tuple(row) for row in cursor.fetchall())
    return QueryResult(columns=columns, rows=rows)


def verify_current_end_user_context(connection: Any, expected_persona: str) -> str:
    """Verify the real DDS username before running protected SQL."""
    with connection.cursor() as cursor:
        cursor.execute(DDS_USERNAME_QUERY)
        row = cursor.fetchone()

    verified_username = None if row is None else row[0]
    if verified_username != expected_persona:
        raise RuntimeError(
            "DDS end-user context verification failed: "
            f"expected {expected_persona!r}, got {verified_username!r}."
        )
    return verified_username


def run_as_persona_with_shared_user(
    pool: SharedConnectionPool,
    provider: EndUserContextProvider,
    *,
    persona: str,
    sql: str,
    shared_db_user: str,
    expected_roles: tuple[str, ...] | None = None,
) -> AppMediatedRunResult:
    """Run protected SQL only after a provider proves real DDS context."""
    if not provider.supports_real_dds_context:
        raise RuntimeError(
            "The selected provider cannot attach a verified Oracle DDS "
            "end-user security context. Protected queries are disabled."
        )

    normalized_sql = normalize_select_sql(sql)
    connection = pool.acquire()
    attach_result: ContextAttachResult | None = None
    query_result: QueryResult | None = None
    verified_username: str | None = None
    context_cleared = False

    try:
        attach_result = provider.attach(connection, persona)
        if not attach_result.attached:
            raise RuntimeError("DDS end-user context provider did not attach context.")

        verified_username = verify_current_end_user_context(connection, persona)
        if attach_result.verified_username not in {None, verified_username}:
            raise RuntimeError(
                "DDS provider verification disagrees with database verification."
            )
        if expected_roles is not None and set(attach_result.verified_roles) != set(expected_roles):
            raise RuntimeError(
                "DDS data role verification failed: "
                f"expected {sorted(expected_roles)!r}, "
                f"got {sorted(attach_result.verified_roles)!r}."
            )

        query_result = _query_on_connection(connection, normalized_sql)
    finally:
        try:
            provider.clear(connection)
            context_cleared = True
        finally:
            pool.release(connection)

    if attach_result is None or query_result is None or verified_username is None:
        raise RuntimeError("Protected query did not produce a verified result.")

    return AppMediatedRunResult(
        columns=query_result.columns,
        rows=query_result.rows,
        shared_db_user=shared_db_user,
        end_user=persona,
        provider_mode=attach_result.mode,
        verified_username=verified_username,
        verified_roles=tuple(attach_result.verified_roles),
        context_attached=attach_result.attached,
        context_cleared=context_cleared,
    )
