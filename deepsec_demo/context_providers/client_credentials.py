"""Identity Domain client-credentials DDS context provider."""

from __future__ import annotations

from dataclasses import dataclass, field
import base64
import json
import time
from typing import Any, Callable
import urllib.error
import urllib.parse
import urllib.request

from deepsec_demo.config import ConfigError
from deepsec_demo.context_providers.base import ContextAttachResult

TokenRequester = Callable[[urllib.request.Request, float], bytes]


@dataclass
class OAuthClientCredentialsTokenClient:
    """Fetch and cache an Identity Domain OAuth client-credentials token."""

    token_url: str | None
    client_id: str | None
    client_secret: str | None = field(default=None, repr=False)
    scope: str | None = None
    timeout: int = 10
    requester: TokenRequester | None = field(default=None, repr=False, compare=False)

    _cached_token: str | None = field(default=None, init=False, repr=False, compare=False)
    _expires_at: float = field(default=0.0, init=False, repr=False, compare=False)

    @property
    def is_configured(self) -> bool:
        return all([self.token_url, self.client_id, self.client_secret, self.scope])

    def require_configured(self) -> None:
        missing = []
        if not self.token_url:
            missing.append("DEMO_APP_TOKEN_URL or IDENTITY_DOMAIN_URL")
        if not self.client_id:
            missing.append("DEMO_APP_CLIENT_ID")
        if not self.client_secret:
            missing.append("DEMO_APP_CLIENT_SECRET")
        if not self.scope:
            missing.append("DEMO_APP_DATABASE_SCOPE")
        if missing:
            raise ConfigError(
                "Missing Identity Domain client-credentials settings: "
                + ", ".join(missing)
            )

    def get_access_token(self) -> str:
        self.require_configured()
        now = time.time()
        if self._cached_token and now < self._expires_at - 60:
            return self._cached_token

        token, expires_in = self._request_access_token()
        if not token:
            raise RuntimeError("Identity Domain token response did not include access_token.")

        ttl_seconds = 300 if expires_in is None else max(0, int(expires_in))
        self._cached_token = token
        self._expires_at = now + ttl_seconds
        return token

    def _request_access_token(self) -> tuple[str, int | None]:
        assert self.token_url is not None
        assert self.client_id is not None
        assert self.client_secret is not None
        assert self.scope is not None

        form_body = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "scope": self.scope,
            }
        ).encode("utf-8")
        basic_value = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode("utf-8")
        ).decode("ascii")
        request = urllib.request.Request(
            self.token_url,
            data=form_body,
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {basic_value}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )

        requester = self.requester or _urlopen_bytes
        try:
            body = requester(request, float(self.timeout))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"Identity Domain token request failed with HTTP {exc.code}."
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("Identity Domain token request failed.") from exc

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Identity Domain token response was not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("Identity Domain token response was not a JSON object.")

        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise RuntimeError("Identity Domain token response did not include access_token.")

        expires_in = payload.get("expires_in")
        if expires_in is None:
            return access_token, None
        try:
            return access_token, int(expires_in)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Identity Domain token response had invalid expires_in.") from exc


def _urlopen_bytes(request: urllib.request.Request, timeout: float) -> bytes:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


@dataclass
class IdentityDomainClientCredentialsProvider:
    """Attach a real DDS end-user context using an Identity Domain token."""

    token_client: OAuthClientCredentialsTokenClient
    end_user_context_key: str | None = field(default=None, repr=False)
    data_roles: tuple[str, ...] = ()
    attributes: dict[str, object] = field(default_factory=dict)

    mode: str = "identity_domain_client_credentials"
    disabled_reason: str = (
        "Identity Domain client-credentials DDS context is not fully configured. "
        "Set DEMO_APP_CLIENT_ID, DEMO_APP_CLIENT_SECRET, DEMO_APP_DATABASE_SCOPE, "
        "IDENTITY_DOMAIN_URL or DEMO_APP_TOKEN_URL, and APP_END_USER_CONTEXT_KEY."
    )

    @property
    def supports_real_dds_context(self) -> bool:
        return self.token_client.is_configured and bool(self.end_user_context_key)

    def require_configured(self) -> None:
        self.token_client.require_configured()
        if not self.end_user_context_key:
            raise ConfigError("APP_END_USER_CONTEXT_KEY is required for Phase 2 DDS context.")

    def create_context(self, persona: str) -> Any:
        self.require_configured()
        import oracledb

        create_context = getattr(oracledb, "create_end_user_security_context", None)
        if create_context is None:
            raise ConfigError(
                "python-oracledb does not expose create_end_user_security_context."
            )

        token = self.token_client.get_access_token()
        return create_context(
            end_user_identity=(persona, self.end_user_context_key),
            database_access_token=token,
            data_roles=list(self.data_roles) or None,
            attributes=self.attributes or None,
        )

    def attach(self, connection: Any, persona: str) -> ContextAttachResult:
        context = self.create_context(persona)
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


def derive_token_url(identity_domain_url: str | None, explicit_token_url: str | None) -> str | None:
    """Return the OAuth token endpoint for the demo application."""
    if explicit_token_url:
        return explicit_token_url
    if not identity_domain_url:
        return None
    return identity_domain_url.rstrip("/") + "/oauth2/v1/token"
