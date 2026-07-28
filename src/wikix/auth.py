"""OAuth PKCE and secure credential storage."""

import base64
import hashlib
import os
import secrets
import time
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Protocol
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
import keyring
from pydantic import BaseModel

from wikix.config import CollectionConfig


class PasswordBackend(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...

    def set_password(self, service: str, username: str, password: str) -> None: ...

    def delete_password(self, service: str, username: str) -> None: ...


class CredentialUnavailableError(RuntimeError):
    """Raised when the operating system has no usable secure credential backend."""


class OAuthCallbackError(RuntimeError):
    """Raised when the localhost OAuth callback is invalid or times out."""


class OAuthTokenError(RuntimeError):
    """Raised when X returns an unusable OAuth token response."""


REQUIRED_SCOPES = ("bookmark.read", "tweet.read", "users.read", "offline.access")


class OAuthTokens(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    scope: str = ""
    source: str = "keyring"


class AuthorizationRequest(BaseModel):
    url: str
    state: str
    code_verifier: str


class CredentialStore:
    def __init__(self, *, backend: PasswordBackend, environ: Mapping[str, str]) -> None:
        self._backend = backend
        self._environ = environ

    def load(self, collection_id: str) -> OAuthTokens | None:
        access_token = self._environ.get("WIKIX_ACCESS_TOKEN")
        if access_token:
            return OAuthTokens(
                access_token=access_token,
                refresh_token=self._environ.get("WIKIX_REFRESH_TOKEN"),
                source="environment",
            )
        try:
            stored = self._backend.get_password("wikix", collection_id)
        except Exception as error:
            raise CredentialUnavailableError(
                "no usable secure credential backend is available"
            ) from error
        if stored is None:
            return None
        return OAuthTokens.model_validate_json(stored)

    def save(self, collection_id: str, tokens: OAuthTokens) -> None:
        try:
            self._backend.set_password("wikix", collection_id, tokens.model_dump_json())
        except Exception as error:
            raise CredentialUnavailableError(
                "no usable secure credential backend is available"
            ) from error

    def delete(self, collection_id: str) -> None:
        try:
            if self._backend.get_password("wikix", collection_id) is None:
                return
            self._backend.delete_password("wikix", collection_id)
        except Exception as error:
            raise CredentialUnavailableError(
                "could not delete credentials from secure storage"
            ) from error


def default_credential_store() -> CredentialStore:
    return CredentialStore(backend=keyring, environ=os.environ)


def build_authorization_request(config: CollectionConfig) -> AuthorizationRequest:
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )
    query = urlencode(
        {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": f"http://127.0.0.1:{config.callback_port}/callback",
            "scope": " ".join(REQUIRED_SCOPES),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return AuthorizationRequest(
        url=f"https://x.com/i/oauth2/authorize?{query}",
        state=state,
        code_verifier=code_verifier,
    )


class OAuthClient:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def exchange_code(
        self, config: CollectionConfig, *, code: str, code_verifier: str
    ) -> OAuthTokens:
        return self._request_token(
            {
                "grant_type": "authorization_code",
                "client_id": config.client_id,
                "code": code,
                "redirect_uri": f"http://127.0.0.1:{config.callback_port}/callback",
                "code_verifier": code_verifier,
            },
            require_scopes=True,
            require_refresh_token=True,
        )

    def refresh(self, config: CollectionConfig, refresh_token: str) -> OAuthTokens:
        return self._request_token(
            {
                "grant_type": "refresh_token",
                "client_id": config.client_id,
                "refresh_token": refresh_token,
            },
            require_scopes=False,
            require_refresh_token=False,
        )

    def _request_token(
        self,
        form: dict[str, str],
        *,
        require_scopes: bool,
        require_refresh_token: bool,
    ) -> OAuthTokens:
        response = self._client.post(
            "https://api.x.com/2/oauth2/token",
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        payload: Any = response.json()
        if not isinstance(payload, dict):
            raise OAuthTokenError("X returned a malformed OAuth token response")
        access_token = payload.get("access_token")
        token_type = payload.get("token_type")
        scope = payload.get("scope", "")
        if (
            not isinstance(access_token, str)
            or not access_token
            or not isinstance(token_type, str)
            or token_type.lower() != "bearer"
            or not isinstance(scope, str)
        ):
            raise OAuthTokenError("X returned a malformed OAuth token response")
        granted_scopes = set(scope.split())
        if require_scopes and not set(REQUIRED_SCOPES).issubset(granted_scopes):
            raise OAuthTokenError("X did not grant all required scopes")
        try:
            expires_in = int(payload.get("expires_in", 7200))
        except (TypeError, ValueError) as error:
            raise OAuthTokenError("X returned a malformed OAuth token response") from error
        if expires_in <= 0:
            raise OAuthTokenError("X returned a malformed OAuth token response")
        refresh_token = payload.get("refresh_token")
        if refresh_token is not None and not isinstance(refresh_token, str):
            raise OAuthTokenError("X returned a malformed OAuth token response")
        if require_refresh_token and not refresh_token:
            raise OAuthTokenError("X did not return the required refresh token")
        return OAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
            scope=scope,
        )


class _CallbackHttpServer(HTTPServer):
    expected_state: str
    authorization_code: str | None
    callback_error: str | None


class _CallbackHandler(BaseHTTPRequestHandler):
    server: _CallbackHttpServer

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_error(404)
            return
        query = parse_qs(parsed.query)
        state = query.get("state", [None])[0]
        code = query.get("code", [None])[0]
        oauth_error = query.get("error_description", query.get("error", [None]))[0]
        if oauth_error:
            self.server.callback_error = f"X authorization failed: {oauth_error}"
        elif state != self.server.expected_state:
            self.server.callback_error = "OAuth callback state did not match"
        elif not code:
            self.server.callback_error = "OAuth callback did not include a code"
        else:
            self.server.authorization_code = code

        success = self.server.callback_error is None
        body = (
            "<h1>Authorization complete</h1><p>You can close this window.</p>"
            if success
            else "<h1>Authorization failed</h1><p>Return to Wikix for details.</p>"
        )
        encoded = body.encode()
        self.send_response(200 if success else 400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


class OAuthCallbackServer:
    """Single-purpose localhost callback server for OAuth authorization."""

    def __init__(self, port: int, *, expected_state: str, timeout: float = 180) -> None:
        self._server = _CallbackHttpServer(("127.0.0.1", port), _CallbackHandler)
        self._server.expected_state = expected_state
        self._server.authorization_code = None
        self._server.callback_error = None
        self._timeout = timeout

    @property
    def port(self) -> int:
        return int(self._server.server_port)

    def wait_for_code(self) -> str:
        deadline = time.monotonic() + self._timeout
        while (
            self._server.authorization_code is None
            and self._server.callback_error is None
            and time.monotonic() < deadline
        ):
            self._server.timeout = min(0.25, max(deadline - time.monotonic(), 0.01))
            self._server.handle_request()
        if self._server.callback_error is not None:
            raise OAuthCallbackError(self._server.callback_error)
        if self._server.authorization_code is None:
            raise OAuthCallbackError("OAuth callback timed out")
        return self._server.authorization_code

    def close(self) -> None:
        self._server.server_close()

    def __enter__(self) -> "OAuthCallbackServer":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
