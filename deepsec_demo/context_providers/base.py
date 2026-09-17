"""Provider interface for real DDS end-user context attachment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ContextAttachResult:
    mode: str
    persona: str
    verified_username: str | None
    verified_roles: list[str] = field(default_factory=list)
    attached: bool = False


class EndUserContextProvider(Protocol):
    mode: str
    supports_real_dds_context: bool

    def attach(self, connection: Any, persona: str) -> ContextAttachResult:
        """Attach a real DDS end-user context to the current connection.

        Implementations must fail closed if ORA_END_USER_CONTEXT.username
        cannot be verified against the selected persona.
        """

    def clear(self, connection: Any) -> None:
        """Clear or detach the context before connection reuse."""
