# Wikix

Wikix is an Apache-2.0, local-first Python CLI that exports one X account's complete bookmark
collection to Obsidian-ready Markdown and versioned JSONL.

Wikix reads bookmarks only through the official X API. Each user supplies an approved developer app
and API credits. Manual imports, X account-archive imports, browser scraping, hosted credentials,
telemetry, and plaintext token storage are unsupported.

## Cost and API boundaries

The lean complete-scan estimate is `bookmark count × $0.001`. These examples are non-binding:
verify current pricing in the X Developer Console before relying on them. Pricing was reviewed on
July 29, 2026; policy guidance was reviewed on July 28, 2026. X pricing may change, and the
Developer Console is authoritative. The first sync cannot estimate a count; later estimates use the
previous successful collection count.

| Current bookmarks | Estimated owned-read cost |
| ---: | ---: |
| 100 | $0.10 |
| 1,000 | $1.00 |
| 5,000 | $5.00 |
| 10,000 | $10.00 |
| 25,000 | $25.00 |

Each sync scans the full collection. Rich and folder modes may incur additional, unpredictable
resource charges. X's same-day deduplication is not a guaranteed discount.

## Get started

Wikix currently installs from its GitHub source. It is not yet published on PyPI.

Follow the [getting started guide](docs/getting-started.md), then choose the complete walkthrough
for macOS, Windows, or Linux. Each walkthrough covers X developer access, API credits, OAuth
configuration, Git and Wikix installation, authentication, your first export, and troubleshooting.

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

Only text between those markers is user-owned. Unchanged notes are not rewritten. Wikix leaves
files untouched when markers are malformed or managed content was edited; it exits nonzero and
reports the conflict.

`bookmarks.jsonl` is the machine-readable current collection. It preserves exact post text, is
sorted by post creation time and ID, and contains no removed post bodies. See the
[schema contract](docs/schema.md).

When a remote bookmark disappears, Wikix deletes an unannotated note. For an annotated note, it
moves only the post ID, source URL, removal time, and personal annotation to `_review/`. If the
bookmark returns, the annotation is restored.

## Operational behavior

- Every sync is a complete remote scan; "incremental" applies only to local file writes.
- Successful API pages are checkpointed so an interrupted scan can resume from compatible staging.
- Incomplete API snapshots never replace an existing export; output changes are committed only after
  the complete remote snapshot succeeds.
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
