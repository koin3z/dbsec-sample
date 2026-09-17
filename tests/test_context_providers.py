import base64
import json
import sys
import types
import urllib.parse

import pytest

from deepsec_demo.config import ConfigError
from deepsec_demo.context_providers.client_credentials import (
    IdentityDomainClientCredentialsProvider,
    OAuthClientCredentialsTokenClient,
    derive_token_url,
)
from deepsec_demo.context_providers.token_based import TokenBasedEndUserContextProvider
from deepsec_demo.context_providers.token_free import TokenFreeEndUserContextProvider


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.context = None

    def set_end_user_security_context(self, context):
        self.calls.append("set")
        self.context = context

    def clear_end_user_security_context(self):
        self.calls.append("clear")


def test_token_free_provider_explains_official_path_is_token_based():
    provider = TokenFreeEndUserContextProvider()

    assert provider.supports_real_dds_context is False
    assert "database-access token" in provider.disabled_reason
    with pytest.raises(NotImplementedError, match="No token-free"):
        provider.attach(FakeConnection(), "staff_tokyo")


def test_token_based_provider_is_policy_disabled_by_default():
    provider = TokenBasedEndUserContextProvider(
        database_access_token="token",
        end_user_context_key="lookup-key",
    )

    assert provider.supports_real_dds_context is False
    with pytest.raises(NotImplementedError, match="requires an end-user security context payload"):
        provider.attach(FakeConnection(), "staff_tokyo")


def test_token_based_provider_requires_token_and_key_when_policy_allows():
    with pytest.raises(ConfigError, match="database_access_token"):
        TokenBasedEndUserContextProvider(allow_token_api=True).attach(
            FakeConnection(),
            "staff_tokyo",
        )

    with pytest.raises(ConfigError, match="end_user_context_key"):
        TokenBasedEndUserContextProvider(
            allow_token_api=True,
            database_access_token="token",
        ).attach(FakeConnection(), "staff_tokyo")


def test_token_based_provider_uses_oracledb_payload_api_when_explicitly_allowed(
    monkeypatch: pytest.MonkeyPatch,
):
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
    connection = FakeConnection()
    provider = TokenBasedEndUserContextProvider(
        allow_token_api=True,
        database_access_token="token",
        end_user_context_key="lookup-key",
        data_roles=("employee_role",),
        attributes={"purpose": "demo"},
    )

    result = provider.attach(connection, "staff_tokyo")
    provider.clear(connection)

    assert created == {
        "end_user_identity": ("staff_tokyo", "lookup-key"),
        "database_access_token": "token",
        "data_roles": ["employee_role"],
        "attributes": {"purpose": "demo"},
    }
    assert connection.calls == ["set", "clear"]
    assert result.attached is True
    assert result.verified_roles == ["employee_role"]


def test_derive_token_url_uses_explicit_override_first():
    assert (
        derive_token_url("https://idcs.example.com:443", "https://override/token")
        == "https://override/token"
    )
    assert (
        derive_token_url("https://idcs.example.com:443/", None)
        == "https://idcs.example.com:443/oauth2/v1/token"
    )
    assert derive_token_url(None, None) is None


def test_oauth_client_credentials_token_client_posts_expected_request():
    calls = []

    def requester(request, timeout):
        calls.append((request, timeout))
        assert timeout == 7.0
        assert request.full_url == "https://idcs.example.com/oauth2/v1/token"
        assert request.get_method() == "POST"
        assert request.get_header("Content-type") == "application/x-www-form-urlencoded"
        auth = request.get_header("Authorization")
        assert auth == "Basic " + base64.b64encode(b"client-id:client-secret").decode("ascii")
        parsed = urllib.parse.parse_qs(request.data.decode("utf-8"))
        assert parsed == {
            "grant_type": ["client_credentials"],
            "scope": ["db-scope"],
        }
        return json.dumps({"access_token": "db-token", "expires_in": 3600}).encode("utf-8")

    client = OAuthClientCredentialsTokenClient(
        token_url="https://idcs.example.com/oauth2/v1/token",
        client_id="client-id",
        client_secret="client-secret",
        scope="db-scope",
        timeout=7,
        requester=requester,
    )

    assert client.get_access_token() == "db-token"
    assert client.get_access_token() == "db-token"
    assert len(calls) == 1


def test_oauth_client_credentials_token_client_requires_settings():
    client = OAuthClientCredentialsTokenClient(
        token_url=None,
        client_id="client-id",
        client_secret="client-secret",
        scope="db-scope",
    )

    with pytest.raises(ConfigError, match="IDENTITY_DOMAIN_URL"):
        client.get_access_token()


def test_identity_domain_client_credentials_provider_uses_oracledb_payload_api(
    monkeypatch: pytest.MonkeyPatch,
):
    created = {}

    def requester(request, timeout):
        return json.dumps({"access_token": "db-token", "expires_in": 3600}).encode("utf-8")

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
    connection = FakeConnection()
    provider = IdentityDomainClientCredentialsProvider(
        token_client=OAuthClientCredentialsTokenClient(
            token_url="https://idcs.example.com/oauth2/v1/token",
            client_id="client-id",
            client_secret="client-secret",
            scope="db-scope",
            requester=requester,
        ),
        end_user_context_key="lookup-key",
        data_roles=("APP_DIRECTORY_LOOKUP_ROLE", "APP_SENSITIVE_LOOKUP_ROLE"),
        attributes={"purpose": "demo"},
    )

    result = provider.attach(connection, "staff_tokyo")
    provider.clear(connection)

    assert provider.supports_real_dds_context is True
    assert created == {
        "end_user_identity": ("staff_tokyo", "lookup-key"),
        "database_access_token": "db-token",
        "data_roles": ["APP_DIRECTORY_LOOKUP_ROLE", "APP_SENSITIVE_LOOKUP_ROLE"],
        "attributes": {"purpose": "demo"},
    }
    assert connection.calls == ["set", "clear"]
    assert result.attached is True
    assert result.verified_roles == [
        "APP_DIRECTORY_LOOKUP_ROLE",
        "APP_SENSITIVE_LOOKUP_ROLE",
    ]


def test_identity_domain_provider_requires_end_user_context_key():
    provider = IdentityDomainClientCredentialsProvider(
        token_client=OAuthClientCredentialsTokenClient(
            token_url="https://idcs.example.com/oauth2/v1/token",
            client_id="client-id",
            client_secret="client-secret",
            scope="db-scope",
        )
    )

    assert provider.supports_real_dds_context is False
    with pytest.raises(ConfigError, match="APP_END_USER_CONTEXT_KEY"):
        provider.attach(FakeConnection(), "staff_tokyo")
