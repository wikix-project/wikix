# API-only onboarding documentation design

## Objective

Make Wikix's official-X-API-only workflow, prerequisites, costs, setup process, and runtime
behavior clear before a user installs or runs the tool.

## Documentation structure

### README

The README remains the project overview and fast path. It will contain:

1. A prominent statement that the official X API is the only supported ingestion method.
2. An explicit statement that account-archive import, manual bookmark import, and browser scraping
   are not supported.
3. A before-you-start checklist covering Python, an approved X developer app, OAuth 2.0 PKCE,
   API credits, a spending limit, a local browser, secure credential storage, and one collection
   directory per X account.
4. A cost table for complete lean scans using X's documented owned-read price of $0.001 per
   bookmark, with examples from 100 through 25,000 bookmarks.
5. Warnings that pricing can change, the first-sync count is unknown, every sync is a complete
   scan, and rich or folder resources may add costs that Wikix cannot predict.
6. A short quickstart containing installation, collection initialization, authentication, lean
   synchronization, and status commands.
7. A prominent link to the complete getting-started guide.
8. A concise explanation of authentication, confirmation prompts, generated files,
   reconciliation, personal-note ownership, conflicts, retries, resumability, and secure token
   storage.

### Getting-started guide

Rename `docs/x-app-setup.md` to `docs/getting-started.md` and expand it into the complete
walkthrough:

1. Requirements and cost expectations.
2. X developer-account, project, app, and API-credit preparation.
3. OAuth 2.0 Authorization Code with PKCE configuration.
4. Exact callback URI and required scopes.
5. Spending-limit configuration.
6. Wikix installation.
7. Collection initialization.
8. Browser authentication and account binding.
9. First lean synchronization and interactive cost confirmation.
10. Optional rich and folder synchronization.
11. Output layout and user-editable personal notes.
12. Subsequent synchronization, removals, conflicts, retries, and recovery.
13. Status and logout commands.
14. Headless token injection and credential-security rules.
15. Troubleshooting for missing credentials, OAuth failures, insufficient credits, rate limits,
    concurrent syncs, and reconciliation conflicts.

The guide will use placeholders rather than real credentials or X content.

## Source-of-truth and maintenance rules

- Current prices, scopes, callback requirements, and endpoint behavior must link to official X
  documentation and carry a last-reviewed date.
- The README cost table is an estimate, not a billing guarantee.
- Cost examples cover only the lean owned-bookmark read. Rich and folder costs remain explicitly
  unquantified.
- The README and guide must describe actual implemented CLI commands and behavior.
- `docs/getting-started.md` is the detailed setup source of truth; the README avoids duplicating
  the entire walkthrough.
- Existing references to `docs/x-app-setup.md` will be updated.

## Verification

1. Check every documented command against Typer's generated help and implemented options.
2. Verify every internal Markdown link resolves.
3. Scan for stale references to `docs/x-app-setup.md`.
4. Run formatting, linting, strict type checking, and the full test suite.
5. Build the package so the README and documentation metadata are validated in the release
   artifact.
