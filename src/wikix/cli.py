"""Wikix command-line interface."""

import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Never

import httpx
import portalocker
import typer

from wikix import __version__
from wikix.api import XApiError, default_api_client
from wikix.auth import (
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
from wikix.config import (
    AccountMismatchError,
    CollectionConfig,
    CollectionNotFoundError,
    CollectionPaths,
    bind_account,
    collection_paths,
    discover_collection,
    init_collection,
    load_config,
)
from wikix.state import load_state
from wikix.sync import SyncEngine

app = typer.Typer(no_args_is_help=True)
auth_app = typer.Typer(no_args_is_help=True)
app.add_typer(auth_app, name="auth")

PRICING_REVIEWED_AT = "2026-07-28"
POLICY_REVIEWED_AT = "2026-07-28"


@dataclass
class CliSettings:
    collection: Path | None


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"Wikix {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show the installed Wikix version and exit.",
        ),
    ] = False,
    collection: Annotated[
        Path | None,
        typer.Option(
            "--collection",
            help="Wikix collection path. Defaults to discovery from the current directory.",
        ),
    ] = None,
) -> None:
    ctx.obj = CliSettings(collection=collection)


def cost_summary(
    record_count: int,
    *,
    has_previous_sync: bool,
    rich: bool,
    folders: bool,
) -> str:
    if has_previous_sync:
        base = (
            f"Estimated bookmark reads from the previous count: "
            f"{record_count:,} × $0.001 = ${record_count * 0.001:,.2f}."
        )
    else:
        base = "First-sync bookmark read cost is unknown because no prior record count exists."
    additions = []
    if rich:
        additions.append("rich expansion costs are additional and not predictable")
    if folders:
        additions.append("folder costs are additional and not predictable")
    extra = f" {'; '.join(additions)}." if additions else ""
    return (
        f"{base}{extra} Rates last reviewed {PRICING_REVIEWED_AT}; "
        "verify current rates and set a spending limit in the X Developer Console."
    )


def run_with_token_refresh[T](
    operation: Callable[[str], T],
    tokens: OAuthTokens,
    *,
    oauth: OAuthClient,
    config: CollectionConfig,
    store: CredentialStore,
) -> T:
    source = tokens.source
    refreshed_once = False

    def refresh() -> OAuthTokens:
        nonlocal refreshed_once
        if refreshed_once or not tokens.refresh_token:
            raise XApiError(
                "X authorization expired; run `wikix auth login` again",
                status_code=401,
            )
        refreshed_once = True
        refreshed = oauth.refresh(config, tokens.refresh_token)
        refreshed = refreshed.model_copy(
            update={
                "refresh_token": refreshed.refresh_token or tokens.refresh_token,
                "scope": refreshed.scope or tokens.scope,
                "source": source,
            }
        )
        if source != "environment":
            store.save(config.collection_id, refreshed)
        return refreshed

    if tokens.expires_at is not None and tokens.expires_at <= datetime.now(UTC) + timedelta(
        seconds=60
    ):
        tokens = refresh()
    try:
        return operation(tokens.access_token)
    except XApiError as error:
        if error.status_code != 401:
            raise
        tokens = refresh()
        return operation(tokens.access_token)


@app.command("init")
def init_command(
    path: Path,
    client_id: str = typer.Option(..., "--client-id"),
    callback_port: int = typer.Option(8765, "--callback-port"),
) -> None:
    try:
        paths = init_collection(path, client_id=client_id, callback_port=callback_port)
    except Exception as error:
        _fail(str(error))
    typer.echo(f"Initialized Wikix collection at {paths.root}")


@app.command()
def status(ctx: typer.Context) -> None:
    paths = _resolve_paths(ctx)
    config = load_config(paths.root)
    state = load_state(paths)
    pending = (paths.metadata / "staging").exists() or (
        paths.metadata / "reconcile-journal.json"
    ).exists()
    typer.echo(f"Collection: {paths.root}")
    typer.echo(f"Account: {config.account_id or 'not authenticated'}")
    typer.echo(f"Records: {state.record_count}")
    typer.echo(f"Last sync: {state.last_sync or 'never'}")
    typer.echo(f"Last profile: {state.last_profile or 'none'}")
    typer.echo(f"Pending recovery: {'yes' if pending else 'no'}")
    typer.echo(f"Conflicts: {len(state.conflicts)}")
    reviewed = min(
        date.fromisoformat(state.pricing_reviewed_at),
        date.fromisoformat(state.policy_reviewed_at),
    )
    if (date.today() - reviewed).days > 90:
        typer.echo("Warning: bundled X pricing or policy guidance is over 90 days old.")


@app.command()
def sync(
    ctx: typer.Context,
    rich: bool = typer.Option(False, "--rich"),
    folders: bool = typer.Option(False, "--folders"),
    yes: bool = typer.Option(False, "--yes"),
) -> None:
    paths = _resolve_paths(ctx)
    config = load_config(paths.root)
    state = load_state(paths)
    typer.echo(
        cost_summary(
            state.record_count,
            has_previous_sync=state.last_sync is not None,
            rich=rich,
            folders=folders,
        )
    )
    if not yes and not typer.confirm("Continue with a complete X API scan?"):
        raise typer.Exit(0)

    try:
        store = default_credential_store()
        tokens = store.load(config.collection_id)
    except CredentialUnavailableError as error:
        _fail(str(error))
    if tokens is None:
        _fail("No X credentials found. Run `wikix auth login` first.")

    try:
        with httpx.Client(timeout=30) as client:
            oauth = OAuthClient(client)
            engine = SyncEngine(default_api_client(client), now=lambda: datetime.now(UTC))
            result = run_with_token_refresh(
                lambda access_token: engine.run(
                    paths,
                    access_token=access_token,
                    rich=rich,
                    folders=folders,
                ),
                tokens,
                oauth=oauth,
                config=config,
                store=store,
            )
    except (XApiError, httpx.HTTPError, portalocker.LockException, ValueError) as error:
        _fail(str(error))

    typer.echo(
        f"Synced {result.record_count} bookmarks "
        f"({result.reconcile.added} added, {result.reconcile.updated} updated, "
        f"{result.reconcile.removed} removed, {result.reconcile.unchanged} unchanged)."
    )
    if result.reconcile.conflicts:
        for conflict in result.reconcile.conflicts:
            typer.echo(f"Conflict {conflict.post_id}: {conflict.reason}", err=True)
        raise typer.Exit(2)


@auth_app.command("login")
def auth_login(ctx: typer.Context) -> None:
    paths = _resolve_paths(ctx)
    config = load_config(paths.root)
    request = build_authorization_request(config)
    try:
        with OAuthCallbackServer(
            config.callback_port,
            expected_state=request.state,
        ) as callback:
            typer.echo("Opening X authorization in your browser.")
            typer.echo(request.url)
            webbrowser.open(request.url)
            code = callback.wait_for_code()
        with httpx.Client(timeout=30) as client:
            oauth = OAuthClient(client)
            tokens = oauth.exchange_code(
                config,
                code=code,
                code_verifier=request.code_verifier,
            )
            account_id = default_api_client(client).get_me(tokens.access_token)
        if config.account_id is not None and config.account_id != account_id:
            raise AccountMismatchError(
                f"collection belongs to X account {config.account_id}, not {account_id}"
            )
        store = default_credential_store()
        store.save(config.collection_id, tokens)
        if config.account_id is None:
            try:
                bind_account(paths.root, account_id)
            except Exception:
                try:
                    store.delete(config.collection_id)
                except CredentialUnavailableError as rollback_error:
                    raise CredentialUnavailableError(
                        "account binding failed and saved credentials could not be removed"
                    ) from rollback_error
                raise
    except (
        AccountMismatchError,
        OSError,
        OAuthCallbackError,
        OAuthTokenError,
        CredentialUnavailableError,
        XApiError,
        httpx.HTTPError,
    ) as error:
        _fail(str(error))
    typer.echo(f"Authenticated X account {account_id}.")


@auth_app.command("logout")
def auth_logout(ctx: typer.Context) -> None:
    paths = _resolve_paths(ctx)
    config = load_config(paths.root)
    try:
        default_credential_store().delete(config.collection_id)
    except CredentialUnavailableError as error:
        _fail(str(error))
    typer.echo("Removed Wikix credentials from secure storage.")


def _resolve_paths(ctx: typer.Context) -> CollectionPaths:
    settings = ctx.ensure_object(CliSettings)
    if settings.collection is not None:
        paths = collection_paths(settings.collection)
        if not paths.config.exists():
            _fail(f"no Wikix collection found at {paths.root}")
        return paths
    try:
        return discover_collection(Path.cwd())
    except CollectionNotFoundError as error:
        _fail(str(error))


def _fail(message: str) -> Never:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(1)
