# API-only Onboarding Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give prospective Wikix users an accurate API-only quickstart, upfront cost expectations,
and a complete step-by-step setup guide.

**Architecture:** Keep `README.md` as the concise project overview and fast path. Rename the
narrow X-app page to `docs/getting-started.md` and make it the detailed onboarding source of truth,
so the README can link to details without duplicating the full walkthrough.

**Tech Stack:** Markdown, Typer CLI commands, official X developer documentation, Hatchling package
metadata.

## Global Constraints

- The official X API is the only supported bookmark-ingestion method.
- Account-archive import, manual bookmark import, and browser scraping are not supported.
- Cost examples use the X owned-read price last reviewed July 28, 2026: `$0.001` per bookmark.
- Every estimate must be labeled as non-binding and direct users to verify current Developer
  Console pricing.
- Lean estimates must not imply that rich author/media/reference resources or folder reads are
  included.
- Every sync is a complete remote scan; local writes alone are incremental.
- Documentation must use placeholder credentials and synthetic paths, never real tokens or X
  content.
- The documented CLI must match Wikix 0.1.0 exactly.

---

### Task 1: Rewrite API-only onboarding

**Files:**

- Modify: `README.md`
- Move and modify: `docs/x-app-setup.md` → `docs/getting-started.md`

**Interfaces:**

- Consumes: `wikix init PATH --client-id ID [--callback-port PORT]`
- Consumes: `wikix auth login`
- Consumes: `wikix sync [--rich] [--folders] [--yes]`
- Consumes: `wikix status`
- Consumes: `wikix auth logout`
- Consumes: global `wikix --collection PATH`
- Produces: one concise quickstart in `README.md`
- Produces: one end-to-end setup source of truth in `docs/getting-started.md`

- [ ] **Step 1: Rewrite the README opening and prerequisites**

  Preserve the project description and Apache-2.0/local-first positioning. Immediately state:

  - Wikix reads bookmarks only through the official X API.
  - Each user supplies an approved developer app and API credits.
  - Manual imports, X account-archive imports, browser scraping, hosted credentials, telemetry, and
    plaintext token storage are unsupported.

  Add a `Before you start` checklist containing:

  - Python 3.12 or newer;
  - `pipx` or `uv`;
  - an X account and approved X developer project/app;
  - OAuth 2.0 Authorization Code with PKCE access;
  - sufficient API credits and a configured spending limit;
  - a local browser able to reach `127.0.0.1`;
  - an OS credential store supported by keyring;
  - a separate collection directory for each X account.

- [ ] **Step 2: Add the README cost table and boundaries**

  Add this lean complete-scan estimate table:

  | Current bookmarks | Estimated owned-read cost |
  | ---: | ---: |
  | 100 | $0.10 |
  | 1,000 | $1.00 |
  | 5,000 | $5.00 |
  | 10,000 | $10.00 |
  | 25,000 | $25.00 |

  Surround the table with the following constraints:

  - The calculation is `bookmark count × $0.001`.
  - The price and policy review date is July 28, 2026.
  - X pricing may change and the Developer Console is authoritative.
  - The first sync cannot estimate a count.
  - Later estimates use the previous successful collection count.
  - Each sync scans the full collection.
  - Rich and folder modes may incur additional, unpredictable resource charges.
  - X's same-day deduplication must not be presented as a guaranteed discount.

- [ ] **Step 3: Add the README quickstart**

  Link prominently to `docs/getting-started.md`, then show:

  ```shell
  pipx install wikix
  wikix init ~/Documents/MyVault/X-Bookmarks --client-id YOUR_CLIENT_ID
  cd ~/Documents/MyVault/X-Bookmarks
  wikix auth login
  wikix sync
  wikix status
  ```

  Explain that `wikix auth login` opens X in the system browser, tokens go to the OS credential
  store, and `wikix sync` displays cost assumptions and asks for confirmation before making API
  calls.

- [ ] **Step 4: Clarify README runtime expectations**

  Retain and organize the existing output tree, personal-note markers, JSONL description,
  reconciliation behavior, and operational guarantees. Explicitly explain:

  - the default profile is lean;
  - `--rich` and `--folders` are independent opt-ins;
  - `--yes` skips confirmation but not billing;
  - unchanged notes are not rewritten;
  - removed unannotated notes are deleted;
  - removed annotated notes move to `_review/`;
  - malformed markers or managed-content edits create conflicts and leave files untouched;
  - incomplete API snapshots never replace an existing export;
  - interrupted scans resume from compatible staging;
  - status code 429 waits for X's reset time;
  - `wikix auth logout` removes stored credentials.

- [ ] **Step 5: Rename and expand the detailed guide**

  Move `docs/x-app-setup.md` to `docs/getting-started.md`. Use this section order:

  1. `What this guide covers`
  2. `Requirements`
  3. `Understand the cost before continuing`
  4. `Create or select an X developer project and app`
  5. `Configure OAuth 2.0 PKCE`
  6. `Buy API credits and set a spending limit`
  7. `Install Wikix`
  8. `Initialize a collection`
  9. `Authenticate the collection`
  10. `Run the first lean sync`
  11. `Inspect the export`
  12. `Run later or expanded syncs`
  13. `Check status and log out`
  14. `Headless environments`
  15. `Troubleshooting`

  The OAuth section must specify:

  ```text
  App type: public native/desktop client
  Flow: OAuth 2.0 Authorization Code with PKCE
  Callback: http://127.0.0.1:8765/callback
  Scopes: bookmark.read tweet.read users.read offline.access
  Client secret: not used by Wikix
  ```

  The troubleshooting section must give an actionable next step for:

  - no credentials;
  - callback URI mismatch or occupied callback port;
  - rejected or incomplete scopes;
  - insufficient credits or HTTP 403;
  - HTTP 429 waiting;
  - a concurrent collection lock;
  - managed Markdown conflicts;
  - interrupted scans and pending recovery;
  - stale pricing/policy metadata warnings.

- [ ] **Step 6: Update references and verify documentation consistency**

  Run:

  ```shell
  rg -n "docs/x-app-setup\.md|x-app-setup\.md" .
  ```

  Expected: no matches outside Git history.

  Verify the new guide and every repository-relative README link exist:

  ```shell
  test -f docs/getting-started.md
  test -f docs/schema.md
  test -f docs/compliance.md
  test -f docs/release-checklist.md
  test -f PRIVACY.md
  test -f CONTRIBUTING.md
  test -f SECURITY.md
  ```

  Inspect CLI help against the documented commands:

  ```shell
  .venv/bin/wikix --help
  .venv/bin/wikix init --help
  .venv/bin/wikix sync --help
  .venv/bin/wikix auth --help
  ```

- [ ] **Step 7: Run the repository verification gates**

  Run:

  ```shell
  .venv/bin/ruff check .
  .venv/bin/ruff format --check .
  .venv/bin/mypy src
  .venv/bin/pytest --cov=wikix --cov-branch --cov-report=term-missing --cov-fail-under=100
  .venv/bin/uv build
  git diff --check
  ```

  Expected:

  - Ruff reports no lint or formatting failures.
  - mypy reports no issues.
  - All tests pass with 100% statement and branch coverage.
  - The source archive and wheel build successfully.
  - Git reports no whitespace errors.

- [ ] **Step 8: Review and commit the documentation change**

  Review:

  ```shell
  git diff -- README.md docs/x-app-setup.md docs/getting-started.md
  git status --short
  ```

  Confirm that only the approved onboarding documentation changed, then commit:

  ```shell
  git add README.md docs/x-app-setup.md docs/getting-started.md
  git commit -m "Improve API-only onboarding documentation"
  ```
