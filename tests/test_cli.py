from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from wikix import __version__
from wikix.api import XApiError
from wikix.auth import (
    CredentialCorruptError,
    CredentialStore,
    CredentialUnavailableError,
    OAuthTokenError,
    OAuthTokens,
)
from wikix.cli import app, cost_summary, run_with_token_refresh
from wikix.config import CollectionConfig, bind_account, collection_paths, load_config
from wikix.reconcile import ReconcileConflict, ReconcileResult
from wikix.state import load_state, save_state
from wikix.sync import SyncResult

runner = CliRunner()


def test_version_option_does_not_require_a_collection() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout == f"Wikix {__version__}\n"


class EmptyBackend:
    def get_password(self, service: str, username: str) -> str | None:
        return None

    def set_password(self, service: str, username: str, password: str) -> None:
        raise AssertionError("unexpected credential write")

    def delete_password(self, service: str, username: str) -> None:
        return None


class MemoryStore:
    def __init__(self, tokens: OAuthTokens | None = None) -> None:
        self.tokens = tokens
        self.saved: list[OAuthTokens] = []
        self.deleted = False

    def load(self, collection_id: str) -> OAuthTokens | None:
        return self.tokens

    def save(self, collection_id: str, tokens: OAuthTokens) -> None:
        self.tokens = tokens
        self.saved.append(tokens)

    def delete(self, collection_id: str) -> None:
        self.deleted = True


def patch_login_dependencies(monkeypatch, store: MemoryStore, *, account_id: str) -> None:
    class FakeCallback:
        def __init__(self, port: int, *, expected_state: str) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def wait_for_code(self) -> str:
            return "code"

    class FakeHttpClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

    class FakeOAuth:
        def __init__(self, client: object) -> None:
            pass

        def exchange_code(
            self,
            config: CollectionConfig,
            *,
            code: str,
            code_verifier: str,
        ) -> OAuthTokens:
            return OAuthTokens(access_token="access", refresh_token="refresh")

    class FakeApi:
        def get_me(self, access_token: str) -> str:
            return account_id

    monkeypatch.setattr("wikix.cli.OAuthCallbackServer", FakeCallback)
    monkeypatch.setattr("wikix.cli.httpx.Client", FakeHttpClient)
    monkeypatch.setattr("wikix.cli.OAuthClient", FakeOAuth)
    monkeypatch.setattr("wikix.cli.default_api_client", lambda client: FakeApi())
    monkeypatch.setattr("wikix.cli.default_credential_store", lambda: store)
    monkeypatch.setattr("wikix.cli.webbrowser.open", lambda url: True)


def patch_sync_dependencies(
    monkeypatch,
    store: MemoryStore,
    outcome: SyncResult | Exception,
) -> None:
    class FakeHttpClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

    class FakeEngine:
        def __init__(self, api: object, *, now) -> None:
            pass

        def run(self, *args: object, **kwargs: object) -> SyncResult:
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr("wikix.cli.httpx.Client", FakeHttpClient)
    monkeypatch.setattr("wikix.cli.OAuthClient", lambda client: object())
    monkeypatch.setattr("wikix.cli.default_api_client", lambda client: object())
    monkeypatch.setattr("wikix.cli.SyncEngine", FakeEngine)
    monkeypatch.setattr("wikix.cli.default_credential_store", lambda: store)


def test_init_and_status_commands(tmp_path: Path) -> None:
    collection = tmp_path / "Wikix"

    initialized = runner.invoke(
        app,
        ["init", str(collection), "--client-id", "client-1"],
    )
    status = runner.invoke(app, ["--collection", str(collection), "status"])

    assert initialized.exit_code == 0
    assert "Initialized Wikix collection" in initialized.output
    assert load_config(collection).client_id == "client-1"
    assert status.exit_code == 0
    assert "Records: 0" in status.output
    assert "Account: not authenticated" in status.output


def test_init_command_reports_existing_collection(tmp_path: Path) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])

    repeated = runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])

    assert repeated.exit_code == 1
    assert "collection already exists" in repeated.output


def test_status_discovers_collection_from_current_directory(tmp_path: Path, monkeypatch) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])
    monkeypatch.chdir(collection / "bookmarks")

    status = runner.invoke(app, ["status"])

    assert status.exit_code == 0
    assert f"Collection: {collection.resolve()}" in status.output


def test_status_reports_missing_explicit_and_discovered_collections(
    tmp_path: Path, monkeypatch
) -> None:
    explicit = runner.invoke(app, ["--collection", str(tmp_path / "missing"), "status"])
    monkeypatch.chdir(tmp_path)
    discovered = runner.invoke(app, ["status"])

    assert explicit.exit_code == 1
    assert "no Wikix collection found at" in explicit.output
    assert discovered.exit_code == 1
    assert "no Wikix collection found from" in discovered.output


def test_status_warns_when_pricing_or_policy_metadata_is_stale(tmp_path: Path) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])

    paths = collection_paths(collection)
    state = load_state(paths)
    state.pricing_reviewed_at = "2020-01-01"
    save_state(paths, state)

    status = runner.invoke(app, ["--collection", str(collection), "status"])

    assert status.exit_code == 0
    assert "over 90 days old" in status.output


def test_sync_without_credentials_has_actionable_error(tmp_path: Path, monkeypatch) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])
    store = CredentialStore(backend=EmptyBackend(), environ={})
    monkeypatch.setattr("wikix.cli.default_credential_store", lambda: store)

    result = runner.invoke(
        app,
        ["--collection", str(collection), "sync", "--yes"],
    )

    assert result.exit_code == 1
    assert "wikix auth login" in result.output


def test_sync_can_be_cancelled_before_credentials_or_api_calls(tmp_path: Path) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])

    result = runner.invoke(
        app,
        ["--collection", str(collection), "sync"],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "Continue with a complete X API scan?" in result.output


def test_sync_reports_secure_credential_backend_failure(tmp_path: Path, monkeypatch) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])

    class FailingLoadStore(MemoryStore):
        def load(self, collection_id: str) -> OAuthTokens | None:
            raise CredentialUnavailableError("secure backend unavailable")

    monkeypatch.setattr("wikix.cli.default_credential_store", FailingLoadStore)

    result = runner.invoke(
        app,
        ["--collection", str(collection), "sync", "--yes"],
    )

    assert result.exit_code == 1
    assert "secure backend unavailable" in result.output


def test_sync_reports_corrupt_stored_credentials(tmp_path: Path, monkeypatch) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])

    class CorruptLoadStore(MemoryStore):
        def load(self, collection_id: str) -> OAuthTokens | None:
            raise CredentialCorruptError("stored X credentials are invalid")

    monkeypatch.setattr("wikix.cli.default_credential_store", CorruptLoadStore)

    result = runner.invoke(
        app,
        ["--collection", str(collection), "sync", "--yes"],
    )

    assert result.exit_code == 1
    assert "stored X credentials are invalid" in result.output


@pytest.mark.parametrize("proactive_refresh", [True, False])
def test_sync_reports_malformed_token_refresh(
    tmp_path: Path,
    monkeypatch,
    proactive_refresh: bool,
) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])
    expires_at = datetime.now(UTC) if proactive_refresh else datetime.now(UTC) + timedelta(hours=1)
    store = MemoryStore(
        OAuthTokens(
            access_token="access",
            refresh_token="refresh",
            expires_at=expires_at,
        )
    )
    patch_sync_dependencies(
        monkeypatch,
        store,
        XApiError("unauthorized", status_code=401),
    )

    class FailingRefreshOAuth:
        def refresh(
            self,
            config: CollectionConfig,
            refresh_token: str,
        ) -> OAuthTokens:
            raise OAuthTokenError("X returned a malformed OAuth token response")

    monkeypatch.setattr("wikix.cli.OAuthClient", lambda client: FailingRefreshOAuth())

    result = runner.invoke(
        app,
        ["--collection", str(collection), "sync", "--yes"],
    )

    assert result.exit_code == 1
    assert "malformed OAuth token response" in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    "command",
    [["status"], ["sync", "--yes"], ["auth", "login"], ["auth", "logout"]],
)
def test_commands_report_corrupt_config_without_traceback(
    tmp_path: Path,
    command: list[str],
) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])
    collection_paths(collection).config.write_text("not = [toml", encoding="utf-8")

    result = runner.invoke(
        app,
        ["--collection", str(collection), *command],
    )

    assert result.exit_code == 1
    assert result.output.startswith("Error:")
    assert "configuration" in result.output
    assert "Traceback" not in result.output
    assert "ValidationError" not in result.output


@pytest.mark.parametrize("command", [["status"], ["sync", "--yes"]])
def test_commands_report_corrupt_state_without_traceback(
    tmp_path: Path,
    command: list[str],
) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])
    collection_paths(collection).state.write_text(
        '{"schema_version": 2}',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["--collection", str(collection), *command],
    )

    assert result.exit_code == 1
    assert result.output.startswith("Error:")
    assert "state" in result.output
    assert "Traceback" not in result.output
    assert "ValidationError" not in result.output


@pytest.mark.parametrize("field", ["pricing_reviewed_at", "policy_reviewed_at"])
def test_status_reports_invalid_persisted_review_dates(
    tmp_path: Path,
    field: str,
) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])
    collection_paths(collection).state.write_text(
        f'{{"schema_version": 1, "{field}": "not-a-date"}}',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["--collection", str(collection), "status"],
    )

    assert result.exit_code == 1
    assert result.output.startswith("Error:")
    assert "state" in result.output
    assert "Traceback" not in result.output
    assert "ValueError" not in result.output


def test_cost_summary_distinguishes_known_base_and_unknown_expansion_costs() -> None:
    message = cost_summary(5_000, has_previous_sync=True, rich=True, folders=True)

    assert "$5.00" in message
    assert "rich expansion costs are additional and not predictable" in message
    assert "folder costs are additional and not predictable" in message


def test_cost_summary_distinguishes_first_sync_from_known_empty_collection() -> None:
    first = cost_summary(0, has_previous_sync=False, rich=False, folders=False)
    known_empty = cost_summary(0, has_previous_sync=True, rich=False, folders=False)

    assert "unknown" in first
    assert "0 × $0.001 = $0.00" in known_empty


def test_run_with_token_refresh_retries_one_unauthorized_operation() -> None:
    backend = EmptyBackend()
    store = CredentialStore(backend=backend, environ={})
    saved: list[OAuthTokens] = []
    store.save = lambda collection_id, tokens: saved.append(tokens)  # type: ignore[method-assign]
    initial = OAuthTokens(
        access_token="expired",
        refresh_token="refresh",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )

    class FakeOAuth:
        def refresh(self, config: CollectionConfig, refresh_token: str) -> OAuthTokens:
            return OAuthTokens(access_token="fresh", refresh_token="rotated")

    attempts: list[str] = []

    def operation(access_token: str) -> str:
        attempts.append(access_token)
        if len(attempts) == 1:
            raise XApiError("unauthorized", status_code=401)
        return "done"

    result = run_with_token_refresh(
        operation,
        initial,
        oauth=FakeOAuth(),  # type: ignore[arg-type]
        config=CollectionConfig(collection_id="c1", client_id="client"),
        store=store,
    )

    assert result == "done"
    assert attempts == ["expired", "fresh"]
    assert saved[0].access_token == "fresh"


def test_run_with_token_refresh_proactively_refreshes_environment_token_without_saving() -> None:
    store = MemoryStore()
    initial = OAuthTokens(
        access_token="expiring",
        refresh_token="refresh",
        expires_at=datetime.now(UTC),
        source="environment",
    )

    class FakeOAuth:
        def refresh(self, config: CollectionConfig, refresh_token: str) -> OAuthTokens:
            return OAuthTokens(access_token="fresh", refresh_token="rotated")

    result = run_with_token_refresh(
        lambda access_token: access_token,
        initial,
        oauth=FakeOAuth(),  # type: ignore[arg-type]
        config=CollectionConfig(collection_id="c1", client_id="client"),
        store=store,  # type: ignore[arg-type]
    )

    assert result == "fresh"
    assert store.saved == []


def test_token_refresh_preserves_existing_refresh_token_when_x_does_not_rotate_it() -> None:
    store = MemoryStore()
    initial = OAuthTokens(
        access_token="expired",
        refresh_token="keep-me",
        expires_at=datetime.now(UTC),
    )

    class FakeOAuth:
        def refresh(self, config: CollectionConfig, refresh_token: str) -> OAuthTokens:
            return OAuthTokens(access_token="fresh")

    result = run_with_token_refresh(
        lambda access_token: access_token,
        initial,
        oauth=FakeOAuth(),  # type: ignore[arg-type]
        config=CollectionConfig(collection_id="c1", client_id="client"),
        store=store,  # type: ignore[arg-type]
    )

    assert result == "fresh"
    assert store.saved[0].refresh_token == "keep-me"


def test_run_with_token_refresh_does_not_retry_non_authentication_failures() -> None:
    tokens = OAuthTokens(access_token="access", refresh_token="refresh")

    def operation(access_token: str) -> str:
        raise XApiError("no credits", status_code=403)

    with pytest.raises(XApiError, match="no credits"):
        run_with_token_refresh(
            operation,
            tokens,
            oauth=object(),  # type: ignore[arg-type]
            config=CollectionConfig(collection_id="c1", client_id="client"),
            store=MemoryStore(),  # type: ignore[arg-type]
        )


def test_run_with_token_refresh_requires_login_without_refresh_token() -> None:
    tokens = OAuthTokens(access_token="expired", expires_at=datetime.now(UTC))

    with pytest.raises(XApiError, match="auth login"):
        run_with_token_refresh(
            lambda access_token: access_token,
            tokens,
            oauth=object(),  # type: ignore[arg-type]
            config=CollectionConfig(collection_id="c1", client_id="client"),
            store=MemoryStore(),  # type: ignore[arg-type]
        )


def test_auth_login_and_logout_commands_bind_account_and_use_secure_store(
    tmp_path: Path, monkeypatch
) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])
    store = MemoryStore()

    class FakeCallback:
        def __init__(self, port: int, *, expected_state: str) -> None:
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def wait_for_code(self) -> str:
            return "code"

    class FakeHttpClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

    class FakeOAuth:
        def __init__(self, client: object) -> None:
            pass

        def exchange_code(
            self,
            config: CollectionConfig,
            *,
            code: str,
            code_verifier: str,
        ) -> OAuthTokens:
            return OAuthTokens(access_token="access", refresh_token="refresh")

    class FakeApi:
        def get_me(self, access_token: str) -> str:
            return "42"

    monkeypatch.setattr("wikix.cli.OAuthCallbackServer", FakeCallback)
    monkeypatch.setattr("wikix.cli.httpx.Client", FakeHttpClient)
    monkeypatch.setattr("wikix.cli.OAuthClient", FakeOAuth)
    monkeypatch.setattr("wikix.cli.default_api_client", lambda client: FakeApi())
    monkeypatch.setattr("wikix.cli.default_credential_store", lambda: store)
    monkeypatch.setattr("wikix.cli.webbrowser.open", lambda url: True)

    logged_in = runner.invoke(
        app,
        ["--collection", str(collection), "auth", "login"],
    )
    logged_out = runner.invoke(
        app,
        ["--collection", str(collection), "auth", "logout"],
    )

    assert logged_in.exit_code == 0
    assert "Authenticated X account 42" in logged_in.output
    assert load_config(collection).account_id == "42"
    assert store.saved[0].access_token == "access"
    assert logged_out.exit_code == 0
    assert store.deleted is True


def test_auth_login_rejects_a_different_account_for_bound_collection(
    tmp_path: Path, monkeypatch
) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])
    bind_account(collection, "99")
    store = MemoryStore()
    patch_login_dependencies(monkeypatch, store, account_id="42")

    result = runner.invoke(app, ["--collection", str(collection), "auth", "login"])

    assert result.exit_code == 1
    assert "collection belongs to X account 99" in result.output
    assert store.saved == []


def test_auth_login_reuses_matching_collection_binding(tmp_path: Path, monkeypatch) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])
    bind_account(collection, "42")
    store = MemoryStore()
    patch_login_dependencies(monkeypatch, store, account_id="42")

    result = runner.invoke(app, ["--collection", str(collection), "auth", "login"])

    assert result.exit_code == 0
    assert "Authenticated X account 42" in result.output
    assert store.saved[0].access_token == "access"


def test_auth_login_removes_saved_token_when_account_binding_fails(
    tmp_path: Path, monkeypatch
) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])
    store = MemoryStore()
    patch_login_dependencies(monkeypatch, store, account_id="42")
    monkeypatch.setattr(
        "wikix.cli.bind_account",
        lambda root, account_id: (_ for _ in ()).throw(OSError("binding failed")),
    )

    result = runner.invoke(app, ["--collection", str(collection), "auth", "login"])

    assert result.exit_code == 1
    assert "binding failed" in result.output
    assert store.deleted is True


def test_auth_login_reports_when_binding_and_credential_rollback_both_fail(
    tmp_path: Path, monkeypatch
) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])

    class FailingRollbackStore(MemoryStore):
        def delete(self, collection_id: str) -> None:
            raise CredentialUnavailableError("rollback failed")

    store = FailingRollbackStore()
    patch_login_dependencies(monkeypatch, store, account_id="42")
    monkeypatch.setattr(
        "wikix.cli.bind_account",
        lambda root, account_id: (_ for _ in ()).throw(OSError("binding failed")),
    )

    result = runner.invoke(app, ["--collection", str(collection), "auth", "login"])

    assert result.exit_code == 1
    assert "saved credentials could not be removed" in result.output


def test_auth_logout_reports_secure_storage_failure(tmp_path: Path, monkeypatch) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])

    class FailingLogoutStore(MemoryStore):
        def delete(self, collection_id: str) -> None:
            raise CredentialUnavailableError("logout failed")

    monkeypatch.setattr("wikix.cli.default_credential_store", FailingLogoutStore)

    result = runner.invoke(app, ["--collection", str(collection), "auth", "logout"])

    assert result.exit_code == 1
    assert "logout failed" in result.output


def test_sync_command_reports_completed_counts(tmp_path: Path, monkeypatch) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])
    bind_account(collection, "42")
    store = MemoryStore(
        OAuthTokens(
            access_token="access",
            refresh_token="refresh",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )

    class FakeHttpClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

    class FakeEngine:
        def __init__(self, api: object, *, now) -> None:
            pass

        def run(self, *args: object, **kwargs: object) -> SyncResult:
            return SyncResult(
                record_count=3,
                profile="rich",
                folders=True,
                reconcile=ReconcileResult(added=2, updated=1),
            )

    monkeypatch.setattr("wikix.cli.httpx.Client", FakeHttpClient)
    monkeypatch.setattr("wikix.cli.OAuthClient", lambda client: object())
    monkeypatch.setattr("wikix.cli.default_api_client", lambda client: object())
    monkeypatch.setattr("wikix.cli.SyncEngine", FakeEngine)
    monkeypatch.setattr("wikix.cli.default_credential_store", lambda: store)

    result = runner.invoke(
        app,
        [
            "--collection",
            str(collection),
            "sync",
            "--rich",
            "--folders",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    assert "Synced 3 bookmarks (2 added, 1 updated, 0 removed, 0 unchanged)" in result.output


def test_sync_command_reports_api_failure(tmp_path: Path, monkeypatch) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])
    bind_account(collection, "42")
    store = MemoryStore(OAuthTokens(access_token="access", refresh_token="refresh"))
    patch_sync_dependencies(monkeypatch, store, XApiError("credits exhausted"))

    result = runner.invoke(app, ["--collection", str(collection), "sync", "--yes"])

    assert result.exit_code == 1
    assert "credits exhausted" in result.output


def test_sync_command_reports_conflicts_and_exits_two(tmp_path: Path, monkeypatch) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])
    bind_account(collection, "42")
    store = MemoryStore(OAuthTokens(access_token="access", refresh_token="refresh"))
    outcome = SyncResult(
        record_count=1,
        profile="lean",
        folders=False,
        reconcile=ReconcileResult(
            conflicts=[
                ReconcileConflict(
                    post_id="100",
                    reason="Wikix-managed content was edited",
                )
            ]
        ),
    )
    patch_sync_dependencies(monkeypatch, store, outcome)

    result = runner.invoke(app, ["--collection", str(collection), "sync", "--yes"])

    assert result.exit_code == 2
    assert "Conflict 100: Wikix-managed content was edited" in result.output


def test_auth_login_does_not_bind_collection_when_secure_token_save_fails(
    tmp_path: Path, monkeypatch
) -> None:
    collection = tmp_path / "Wikix"
    runner.invoke(app, ["init", str(collection), "--client-id", "client-1"])

    class FailingStore(MemoryStore):
        def save(self, collection_id: str, tokens: OAuthTokens) -> None:
            raise CredentialUnavailableError("secure storage failed")

    class FakeCallback:
        def __init__(self, port: int, *, expected_state: str) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def wait_for_code(self) -> str:
            return "code"

    class FakeHttpClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

    class FakeOAuth:
        def __init__(self, client: object) -> None:
            pass

        def exchange_code(
            self,
            config: CollectionConfig,
            *,
            code: str,
            code_verifier: str,
        ) -> OAuthTokens:
            return OAuthTokens(access_token="access", refresh_token="refresh")

    class FakeApi:
        def get_me(self, access_token: str) -> str:
            return "42"

    monkeypatch.setattr("wikix.cli.OAuthCallbackServer", FakeCallback)
    monkeypatch.setattr("wikix.cli.httpx.Client", FakeHttpClient)
    monkeypatch.setattr("wikix.cli.OAuthClient", FakeOAuth)
    monkeypatch.setattr("wikix.cli.default_api_client", lambda client: FakeApi())
    monkeypatch.setattr("wikix.cli.default_credential_store", lambda: FailingStore())
    monkeypatch.setattr("wikix.cli.webbrowser.open", lambda url: True)

    result = runner.invoke(
        app,
        ["--collection", str(collection), "auth", "login"],
    )

    assert result.exit_code == 1
    assert "secure storage failed" in result.output
    assert load_config(collection).account_id is None
