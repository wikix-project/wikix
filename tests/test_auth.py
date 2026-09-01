import base64
import hashlib
import json
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from wikix.auth import (
    CredentialCorruptError,
    CredentialStore,
    CredentialUnavailableError,
    OAuthCallbackError,
    OAuthCallbackServer,
    OAuthClient,
    OAuthTokenError,
    OAuthTokens,
    build_authorization_request,
    default_credential_store,
)
from wikix.config import CollectionConfig


class FakePasswordBackend:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.values[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self.values.pop((service, username), None)


class BrokenPasswordBackend(FakePasswordBackend):
    def set_password(self, service: str, username: str, password: str) -> None:
        raise RuntimeError("no secure backend")


class BrokenDeleteBackend(FakePasswordBackend):
    def delete_password(self, service: str, username: str) -> None:
        raise RuntimeError("credential remains")


class BrokenReadBackend(FakePasswordBackend):
    def get_password(self, service: str, username: str) -> str | None:
        raise RuntimeError("backend unavailable")


def config() -> CollectionConfig:
    return CollectionConfig(
        collection_id="collection-1",
        client_id="client-1",
        callback_port=8765,
    )


def token_set() -> OAuthTokens:
    return OAuthTokens(
        access_token="access",
        refresh_token="refresh",
        expires_at=datetime.now(UTC) + timedelta(hours=2),
        scope="bookmark.read tweet.read users.read offline.access",
    )


def test_credential_store_prefers_environment_tokens() -> None:
    backend = FakePasswordBackend()
    backend.set_password("wikix", "collection-1", token_set().model_dump_json())
    environment: Mapping[str, str] = {
        "WIKIX_ACCESS_TOKEN": "environment-access",
        "WIKIX_REFRESH_TOKEN": "environment-refresh",
    }

    tokens = CredentialStore(backend=backend, environ=environment).load("collection-1")

    assert tokens is not None
    assert tokens.access_token == "environment-access"
    assert tokens.refresh_token == "environment-refresh"
    assert tokens.source == "environment"


def test_credential_store_round_trips_and_deletes_keyring_tokens() -> None:
    backend = FakePasswordBackend()
    store = CredentialStore(backend=backend, environ={})

    store.save("collection-1", token_set())
    loaded = store.load("collection-1")
    store.delete("collection-1")

    assert loaded is not None
    assert loaded.access_token == "access"
    assert loaded.refresh_token == "refresh"
    assert store.load("collection-1") is None
    store.delete("collection-1")


@pytest.mark.parametrize("stored", ["not-json", '{"access_token": 42}'])
def test_credential_store_reports_corrupt_stored_tokens(stored: str) -> None:
    backend = FakePasswordBackend()
    backend.set_password("wikix", "collection-1", stored)
    store = CredentialStore(backend=backend, environ={})

    with pytest.raises(CredentialCorruptError, match="invalid"):
        store.load("collection-1")


def test_default_credential_store_reads_injected_environment_token(monkeypatch) -> None:
    monkeypatch.setenv("WIKIX_ACCESS_TOKEN", "environment-access")
    monkeypatch.setenv("WIKIX_REFRESH_TOKEN", "environment-refresh")

    tokens = default_credential_store().load("collection-1")

    assert tokens is not None
    assert tokens.access_token == "environment-access"
    assert tokens.refresh_token == "environment-refresh"


def test_credential_store_reports_unavailable_secure_backend() -> None:
    store = CredentialStore(backend=BrokenPasswordBackend(), environ={})

    with pytest.raises(CredentialUnavailableError, match="secure credential"):
        store.save("collection-1", token_set())

    with pytest.raises(CredentialUnavailableError, match="secure credential"):
        CredentialStore(backend=BrokenReadBackend(), environ={}).load("collection-1")


def test_credential_store_reports_failed_logout_instead_of_claiming_success() -> None:
    backend = BrokenDeleteBackend()
    backend.set_password("wikix", "collection-1", token_set().model_dump_json())
    store = CredentialStore(backend=backend, environ={})

    with pytest.raises(CredentialUnavailableError, match="delete credentials"):
        store.delete("collection-1")


def test_authorization_request_uses_pkce_and_minimum_scopes() -> None:
    request = build_authorization_request(config())
    query = parse_qs(urlparse(request.url).query)
    expected_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(request.code_verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )

    assert query["client_id"] == ["client-1"]
    assert query["redirect_uri"] == ["http://127.0.0.1:8765/callback"]
    assert query["state"] == [request.state]
    assert query["code_challenge"] == [expected_challenge]
    assert query["code_challenge_method"] == ["S256"]
    assert set(query["scope"][0].split()) == {
        "bookmark.read",
        "tweet.read",
        "users.read",
        "offline.access",
    }


def test_oauth_client_exchanges_code_and_refreshes_token() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = {
            "token_type": "bearer",
            "access_token": f"access-{len(requests)}",
            "refresh_token": f"refresh-{len(requests)}",
            "expires_in": 7200,
            "scope": "bookmark.read tweet.read users.read offline.access",
        }
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        oauth = OAuthClient(client)
        first = oauth.exchange_code(config(), code="auth-code", code_verifier="verifier")
        second = oauth.refresh(config(), first.refresh_token or "")

    first_form = parse_qs(requests[0].content.decode())
    second_form = parse_qs(requests[1].content.decode())
    assert first.access_token == "access-1"
    assert first.expires_at > datetime.now(UTC)
    assert first_form["grant_type"] == ["authorization_code"]
    assert first_form["code_verifier"] == ["verifier"]
    assert second.access_token == "access-2"
    assert second_form["grant_type"] == ["refresh_token"]
    assert second_form["refresh_token"] == ["refresh-1"]
    assert json.loads(second.model_dump_json())["source"] == "keyring"


def test_oauth_client_rejects_malformed_or_reduced_scope_token_responses() -> None:
    responses = [
        httpx.Response(200, json=["not", "an", "object"]),
        httpx.Response(
            200,
            json={
                "token_type": "bearer",
                "access_token": "access",
                "scope": "bookmark.read tweet.read",
            },
        ),
        httpx.Response(
            200,
            json={
                "token_type": "bearer",
                "access_token": "access",
                "scope": "bookmark.read tweet.read users.read offline.access",
            },
        ),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        oauth = OAuthClient(client)
        with pytest.raises(OAuthTokenError, match="malformed"):
            oauth.exchange_code(config(), code="code", code_verifier="verifier")
        with pytest.raises(OAuthTokenError, match="required scopes"):
            oauth.exchange_code(config(), code="code", code_verifier="verifier")
        with pytest.raises(OAuthTokenError, match="refresh token"):
            oauth.exchange_code(config(), code="code", code_verifier="verifier")


def test_oauth_client_rejects_non_json_token_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>not json</html>")

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(OAuthTokenError, match="malformed"),
    ):
        OAuthClient(client).refresh(config(), "refresh-token")


@pytest.mark.parametrize(
    "payload",
    [
        {
            "token_type": "not-bearer",
            "access_token": "access",
            "scope": "bookmark.read tweet.read users.read offline.access",
            "refresh_token": "refresh",
        },
        {
            "token_type": "bearer",
            "access_token": "access",
            "scope": "bookmark.read tweet.read users.read offline.access",
            "refresh_token": "refresh",
            "expires_in": "not-a-number",
        },
        {
            "token_type": "bearer",
            "access_token": "access",
            "scope": "bookmark.read tweet.read users.read offline.access",
            "refresh_token": "refresh",
            "expires_in": 0,
        },
        {
            "token_type": "bearer",
            "access_token": "access",
            "scope": "bookmark.read tweet.read users.read offline.access",
            "refresh_token": 42,
        },
    ],
)
def test_oauth_client_rejects_invalid_token_fields(payload: object) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(OAuthTokenError, match="malformed"),
    ):
        OAuthClient(client).exchange_code(config(), code="code", code_verifier="verifier")


def test_callback_server_returns_code_and_rejects_wrong_state() -> None:
    with (
        OAuthCallbackServer(0, expected_state="expected", timeout=2) as server,
        ThreadPoolExecutor(max_workers=1) as executor,
    ):
        future = executor.submit(server.wait_for_code)
        response = httpx.get(f"http://127.0.0.1:{server.port}/not-the-callback")
        assert response.status_code == 404
        valid_response = httpx.get(
            f"http://127.0.0.1:{server.port}/callback",
            params={"code": "authorization-code", "state": "expected"},
        )
        assert future.result(timeout=2) == "authorization-code"
        assert "Authorization complete" in valid_response.text

    with (
        OAuthCallbackServer(0, expected_state="expected", timeout=2) as server,
        ThreadPoolExecutor(max_workers=1) as executor,
    ):
        future = executor.submit(server.wait_for_code)
        response = httpx.get(
            f"http://127.0.0.1:{server.port}/callback",
            params={"code": "authorization-code", "state": "expected"},
        )
        assert future.result(timeout=2) == "authorization-code"
        assert "Authorization complete" in response.text

    with (
        OAuthCallbackServer(0, expected_state="expected", timeout=2) as server,
        ThreadPoolExecutor(max_workers=1) as executor,
    ):
        future = executor.submit(server.wait_for_code)
        httpx.get(
            f"http://127.0.0.1:{server.port}/callback",
            params={"code": "authorization-code", "state": "wrong"},
        )
        with pytest.raises(OAuthCallbackError, match="state"):
            future.result(timeout=2)

    with (
        OAuthCallbackServer(0, expected_state="expected", timeout=2) as server,
        ThreadPoolExecutor(max_workers=1) as executor,
    ):
        future = executor.submit(server.wait_for_code)
        response = httpx.get(
            f"http://127.0.0.1:{server.port}/callback",
            params={"error_description": "user denied", "state": "expected"},
        )
        assert response.status_code == 400
        with pytest.raises(OAuthCallbackError, match="user denied"):
            future.result(timeout=2)

    with (
        OAuthCallbackServer(0, expected_state="expected", timeout=2) as server,
        ThreadPoolExecutor(max_workers=1) as executor,
    ):
        future = executor.submit(server.wait_for_code)
        httpx.get(
            f"http://127.0.0.1:{server.port}/callback",
            params={"state": "expected"},
        )
        with pytest.raises(OAuthCallbackError, match="include a code"):
            future.result(timeout=2)

    with (
        OAuthCallbackServer(0, expected_state="expected", timeout=0) as server,
        pytest.raises(OAuthCallbackError, match="timed out"),
    ):
        server.wait_for_code()
