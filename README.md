# Wikix

Wikix is an Apache-2.0, local-first Python CLI that exports one X account's complete bookmark
collection to Obsidian-ready Markdown and versioned JSONL.

Wikix uses the official X API. You provide your own approved X developer app and pay its API
charges. Wikix has no hosted service, shared credentials, browser scraper, telemetry, or plaintext
token fallback.

> [!CAUTION]
> A sync fully enumerates the remote bookmark collection. Review the estimate Wikix displays,
> understand X's current pricing, and configure a spending limit in the X Developer Console before
> continuing. Bundled pricing and policy metadata was last reviewed on July 28, 2026 and can become
> stale.

## Install

Wikix requires Python 3.12 or newer:

```shell
pipx install wikix
```

or:

```shell
uv tool install wikix
```

## Set up an export

First [create and configure your own X developer app](docs/x-app-setup.md). Then initialize a
collection:

```shell
wikix init ~/Documents/MyVault/X-Bookmarks --client-id YOUR_CLIENT_ID
cd ~/Documents/MyVault/X-Bookmarks
wikix auth login
wikix sync
```

The default sync is lean. Rich author/media/reference metadata and X bookmark-folder membership are
independent opt-ins:

```shell
wikix sync --rich
wikix sync --folders
wikix sync --rich --folders
```

Use `--yes` only after you have reviewed the cost warning. Use `--collection PATH` before any
command to operate outside the collection directory:

```shell
wikix --collection ~/Documents/MyVault/X-Bookmarks status
```

Headless environments may inject `WIKIX_ACCESS_TOKEN` and, optionally, `WIKIX_REFRESH_TOKEN`.
Environment values override the OS credential store and are never persisted by Wikix.

## Output

```text
X-Bookmarks/
├── bookmarks/
│   └── <post-id>.md
├── bookmarks.jsonl
├── _review/
└── .wikix/
    ├── config.toml
    └── state.json
```

Each bookmark note has deterministic YAML frontmatter, Markdown-safe post content, and a personal
notes region:

```markdown
## Personal notes
<!-- wikix:notes:start -->

<!-- wikix:notes:end -->
```

Only text between those markers is user-owned. Wikix leaves files untouched when markers are
malformed or the generated region was edited. It exits nonzero and reports the conflict.

`bookmarks.jsonl` is the machine-readable current collection. It preserves exact post text, is
sorted by post creation time and ID, and contains no removed post bodies. See the
[schema contract](docs/schema.md).

When a remote bookmark disappears, Wikix deletes an unannotated note. For an annotated note, it
moves only the post ID, source URL, removal time, and personal annotation to `_review/`. If the
bookmark returns, the annotation is restored.

## Operational behavior

- Every sync is a complete remote scan; "incremental" applies only to local file writes.
- Successful API pages are checkpointed so an interrupted scan can resume.
- Output changes are committed only after the complete remote snapshot succeeds.
- A collection lock prevents concurrent syncs.
- HTTP 429 responses wait for the server reset; transient network and 5xx failures retry.
- Authentication, credit, malformed-response, and unresolved partial-error failures do not alter
  existing exports.
- Access and refresh tokens use the operating system credential store. `wikix auth logout` removes
  them.
- `wikix status` reports the account, counts, profile, recovery/conflict state, and metadata
  freshness.

## Scope and responsible use

Wikix supports private personal retrieval, search, summarization, classification, synthesis, and
citation. It is designed to help users comply with X's terms; it is not legal certification.

Version 1 explicitly excludes browser scraping, public dataset redistribution, profiling or
surveillance, model training, media downloads, external-page extraction, thread crawling,
background scheduling, hosted OAuth, and MCP or API servers. Read [privacy](PRIVACY.md) and
[compliance and scope](docs/compliance.md) before use.

## Development

```shell
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=wikix
```

The test suite uses synthetic X responses only. See [CONTRIBUTING.md](CONTRIBUTING.md), the
[security policy](SECURITY.md), and the [release checklist](docs/release-checklist.md).
