# Getting started

## What this guide covers

Wikix exports one X account's bookmarks to a local, Obsidian-ready collection using only the official X API. This guide covers creating your own X app, funding its API use, authenticating one collection, and running and maintaining that collection. Wikix does not support manual or account-archive imports, browser scraping, hosted credentials, telemetry, or plaintext token storage.

## Requirements

- Python 3.12 or newer and either `pipx` or `uv`.
- An X account plus an approved X developer project and app.
- OAuth 2.0 Authorization Code with PKCE access, sufficient API credits, and a spending limit.
- A local browser that can reach `127.0.0.1` and an OS credential store supported by keyring.
- A separate collection directory for each X account.

## Understand the cost before continuing

Wikix estimates an owned-read cost of `bookmark count × $0.001` for a complete scan. These examples are non-binding: verify current pricing in the X Developer Console before relying on them. The price and policy metadata was reviewed on July 28, 2026; X pricing may change, and the Developer Console is authoritative. The first sync cannot estimate a count. Later estimates use the previous successful collection count.

Every sync scans the full collection. `--rich` and `--folders` can add unpredictable resource charges. X's same-day deduplication is not a guaranteed discount. Set a spending limit before you continue.

| Current bookmarks | Estimated owned-read cost |
| ---: | ---: |
| 100 | $0.10 |
| 1,000 | $1.00 |
| 5,000 | $5.00 |
| 10,000 | $10.00 |
| 25,000 | $25.00 |

## Create or select an X developer project and app

In the [X Developer Console](https://developer.x.com/en/portal/dashboard), create or select a project and app approved for your account. Ensure it can use the bookmark endpoint. Console labels, prices, and policy terms can change, so check the current [X OAuth documentation](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code) and [bookmark endpoint documentation](https://docs.x.com/x-api/users/get-bookmarks).

## Configure OAuth 2.0 PKCE

Configure the app exactly as follows (unless you choose a different callback port during initialization):

```text
App type: public native/desktop client
Flow: OAuth 2.0 Authorization Code with PKCE
Callback: http://127.0.0.1:8765/callback
Scopes: bookmark.read tweet.read users.read offline.access
Client secret: not used by Wikix
```

Copy the OAuth 2.0 client ID. Do not put a client secret into Wikix.

## Buy API credits and set a spending limit

Buy sufficient API credits in the Developer Console and configure a spending limit before the first sync. The Console's current pricing and policy are authoritative; do not rely on a prior estimate.

## Install Wikix

```shell
pipx install wikix
```

Or install with `uv`:

```shell
uv tool install wikix
```

## Initialize a collection

Create one empty local collection for one X account. The default callback port is `8765`:

```shell
wikix init ~/Documents/MyVault/X-Bookmarks --client-id YOUR_CLIENT_ID
```

If that port is unavailable, choose a port and register its exact callback URI in the X app first:

```shell
wikix init ~/Documents/MyVault/X-Bookmarks --client-id YOUR_CLIENT_ID --callback-port PORT
```

## Authenticate the collection

Change to the collection, then start login:

```shell
cd ~/Documents/MyVault/X-Bookmarks
wikix auth login
```

Wikix opens X in the system browser, validates the OAuth state, receives the localhost callback, and binds the collection to the authenticated account. Access and refresh tokens are stored in the OS credential store.

## Run the first lean sync

```shell
wikix sync
```

The default profile is lean. Before making API calls, Wikix displays its cost assumptions and asks for confirmation. The first sync has no prior collection count, so it cannot estimate a count.

## Inspect the export

The collection contains `bookmarks/` Markdown notes, `bookmarks.jsonl`, `_review/`, and `.wikix/` configuration and state. Each note has deterministic generated content and a personal-notes region; only text inside that region is user-owned. See the [schema contract](schema.md) for JSONL details.

## Run later or expanded syncs

Run later scans from the collection directory, or select it explicitly from elsewhere:

```shell
wikix sync
wikix sync --rich
wikix sync --folders
wikix sync --rich --folders
wikix --collection ~/Documents/MyVault/X-Bookmarks sync
```

`--rich` and `--folders` are independent opt-ins and may create additional charges. `--yes` skips the confirmation prompt, not billing:

```shell
wikix sync --yes
```

## Check status and log out

```shell
wikix status
wikix auth logout
```

`status` reports account, counts, profile, recovery/conflict state, and metadata freshness. `auth logout` removes the stored credentials.

## Headless environments

The interactive login needs a local browser and callback port. A headless process may securely inject user-context tokens instead:

```shell
export WIKIX_ACCESS_TOKEN=...
export WIKIX_REFRESH_TOKEN=...
wikix --collection PATH sync
```

Environment values override the OS credential store and are never persisted by Wikix. Do not put tokens in shell history, `.env` files, collection configuration, CI logs, or source control.

## Troubleshooting

- **No credentials:** run `wikix auth login` from the collection directory, or provide secure headless environment tokens for that command.
- **Callback URI mismatch or occupied callback port:** register the exact `http://127.0.0.1:PORT/callback` URI in the X app, then rerun `wikix init` with `--callback-port PORT` and log in again.
- **Rejected or incomplete scopes:** update the app to request `bookmark.read`, `tweet.read`, `users.read`, and `offline.access`, then log in again.
- **Insufficient credits or HTTP 403:** check app approval, endpoint access, credits, and the spending limit in the Developer Console before retrying.
- **HTTP 429 waiting:** Wikix waits for X's reset time; let it wait or retry after that reset.
- **Concurrent collection lock:** let the active Wikix command finish, then retry; do not delete a lock while a sync may still be running.
- **Managed Markdown conflicts:** restore the generated region and valid personal-note markers, or resolve the reported conflict manually; Wikix leaves conflicting files untouched.
- **Interrupted scans and pending recovery:** rerun a compatible sync so Wikix can resume staging; incomplete API snapshots never replace an existing export.
- **Stale pricing or policy metadata warnings:** review the current Developer Console pricing and policy, confirm your spending limit, and then decide whether to continue.
