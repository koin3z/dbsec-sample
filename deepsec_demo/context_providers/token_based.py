"""Policy-disabled official token-based DDS context provider scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from deepsec_demo.config import ConfigError
from deepsec_demo.context_providers.base import ContextAttachResult

TOKEN_BASED_DISABLED_REASON = (
    "The official application-mediated Deep Data Security driver path "
    "requires an end-user security context payload containing a database-access "
    "token. The current project phase excludes token-based context APIs, so "
    "this provider is not enabled."
)


@dataclass(frozen=True)
class TokenBasedEndUserContextProvider:
    database_access_token: str | None = field(default=None, repr=False)
    end_user_context_key: str | None = field(default=None, repr=False)
    data_roles: tuple[str, ...] = ()
    attributes: dict[str, object] = field(default_factory=dict)
    allow_token_api: bool = False

    mode: str = "app_mediated_token"
    disabled_reason: str = TOKEN_BASED_DISABLED_REASON

    @property
    def supports_real_dds_context(self) -> bool:
        return (
            self.allow_token_api
            and bool(self.database_access_token)
            and bool(self.end_user_context_key)
        )

    def attach(self, connection: Any, persona: str) -> ContextAttachResult:
        if not self.allow_token_api:
            raise NotImplementedError(self.disabled_reason)
        if not self.database_access_token:
            raise ConfigError(
                "database_access_token is required for token-based DDS context."
            )
        if not self.end_user_context_key:
            raise ConfigError(
                "end_user_context_key is required for local database users."
            )

        import oracledb

        context = oracledb.create_end_user_security_context(
            end_user_identity=(persona, self.end_user_context_key),
            database_access_token=self.database_access_token,
            data_roles=list(self.data_roles) or None,
            attributes=self.attributes or None,
        )
        connection.set_end_user_security_context(context)
        return ContextAttachResult(
            mode=self.mode,
            persona=persona,
            verified_username=None,
            verified_roles=list(self.data_roles),
            attached=True,
        )

    def clear(self, connection: Any) -> None:
        connection.clear_end_user_security_context()
