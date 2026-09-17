"""Disabled token-free provider placeholder for Phase 2."""

from __future__ import annotations

from typing import Any


TOKEN_FREE_DISABLED_REASON = (
    "No token-free application-mediated Deep Data Security context provider "
    "is configured. The official driver path uses an EndUserSecurityContext "
    "payload with a database-access token. Do not emulate "
    "ORA_END_USER_CONTEXT in Python, CLIENT_IDENTIFIER, MODULE, ACTION, "
    "or DBMS_SESSION.SET_CONTEXT."
)


class TokenFreeEndUserContextProvider:
    mode = "app_mediated_token_free"
    supports_real_dds_context = False
    disabled_reason = TOKEN_FREE_DISABLED_REASON

    def attach(self, connection: Any, persona: str):
        _ = connection, persona
        raise NotImplementedError(self.disabled_reason)

    def clear(self, connection: Any) -> None:
        _ = connection
        return None
