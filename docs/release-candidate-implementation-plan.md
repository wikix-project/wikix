# Wikix 1.0 Release-Candidate Preparation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce independently reviewable launch-readiness pull requests and a fully verified,
unpushed Wikix 1.0 release candidate without merging, publishing, deploying, changing external
settings, or deleting user work.

**Architecture:** Execute one issue-sized stream at a time from the then-current `origin/main`.
Keep confidential remediation inside a private advisory, keep public branches independent of it,
and combine the verified stream heads only in a disposable local RC worktree. Any integration fix
returns to the stream that owns the behavior.

**Tech Stack:** Python 3.12-3.14, uv, Typer, HTTPX, Pydantic, PyYAML, pytest, Ruff, mypy, static
HTML/CSS, Vercel preview hosting, GitHub Actions, GitHub Security Advisories, and PyPI Trusted
Publishing.

**Spec:** `docs/release-candidate-preparation.md`

## Global Constraints

- Freeze product behavior at authentication, lean/rich/folder sync, resume, deterministic
  Markdown/JSONL, reconciliation, and status.
- Use only the official X API; do not add scraping, hosted credentials, scheduling, servers, or
  other product features.
- Keep confidential reproduction, impact, source mapping, and patch details out of public issues,
  branches, logs, commits, and documents.
- Treat every existing branch, worktree, uncommitted change, and untracked file as user-owned.
- Start every implementation branch from a freshly fetched current `origin/main`.
- Search live issues, pull requests, and branches before creating each issue.
- Implement one confirmed public issue at a time and reconcile its branch, PR, review, and CI state
  before starting the next public issue.
- Use issue-linked branch names such as `fix/123-description`, `docs/124-description`, and
  `build/125-description`.
- Use tests first for behavioral changes. Apply source tests, confirm the intended failure, then
  apply the smallest implementation diff.
- Preserve the macOS, Windows, and Linux onboarding guides and current `uv tool install` source
  instructions until PyPI publication is actually verified.
- Keep public branches independent of confidential code.
- Do not merge, close, withdraw, force-push, tag, publish, deploy to production, change external
  repository/package/hosting settings, or delete branches/worktrees without separate approval.
- Use `git add -- path1 path2` with only the task's listed paths; never stage the entire worktree.
- The target final package version is `1.0.0`, but its metadata PR remains draft until all
  launch-critical verification gates are green.

## Execution Paths and Plan Boundaries

- Main checkout: `/Users/atharvafulay/Documents/Wikix`
- Planning worktree: `/Users/atharvafulay/Documents/Wikix/.worktrees/issue-3-release-candidate-plan`
- Run Task 1 from the planning worktree.
- Begin every later task with `cd /Users/atharvafulay/Documents/Wikix` before resolving or creating
  worktrees.
- Execute each task in one persistent terminal session so its task-specific `WIKIX_*` variables and
  current worktree persist across steps. If a session restarts, rederive the issue number from the
  exact issue title before running another mutating command.
- This is one coordination plan, but every public implementation task is a separately rejectable,
  independently testable subproject with its own issue, branch, commit, and PR. Task 3's technical
  plan exists only in the private advisory.

## Source Inventory

These fingerprints are the inputs observed while this plan was written. Task 2 must recheck them
before any migration. A mismatch means the source work changed and the plan must be refreshed; it
does not authorize overwriting the newer work.

| Public stream | Source | Observed fingerprint |
| --- | --- | --- |
| Live and staged page validation | Commit plus uncommitted hardening | `b489c1b486dd1ef4f2f9d31068e6a762c723634b`; patch SHA-256 `1327bcc006312bf73666c0b03acd9f26bfa11068f898c1c519e021cbef0acffd` |
| Markdown rendering safety | Two file-scoped commit diffs | `988cd99d05375c2364e76ed8f78b119be64262e3`; records-only portion of `2fe8b76dad8b7f0243fb7c9dac36eda7d54069b5` |
| Local metadata and CLI failures | Three file-scoped commit diffs | `3be0505ddbf1e5c7111c87b0b1d9edd4c20d909c`; `14081b0022d543dbf2968edfc4efa3d9a97fb7ce`; CLI/state portion of `2fe8b76dad8b7f0243fb7c9dac36eda7d54069b5` |
| Bounded rate-limit waiting | Commit | `f23cc00118ada9fcc86a5801e739b159fdfe6832` |
| Website and setup pages | Branch diff against the observed main | `26acd91270917895be7bcc01470c214cfcb452a4`; patch SHA-256 `02e70f73fd51dfc0c5914be8f4e50173ee14c24d83eba8ed8e9bcbc961ddf957` |
| Confidential remediation | Private ledger only | Intentionally omitted from this public plan |

---

### Task 0: Verify the local launch toolchain

**Files:**
- No repository changes.

**Interfaces:**
- Consumes: the maintainer's local macOS development environment.
- Produces: verified Git, GitHub CLI, Python, uv, and authentication prerequisites for every later
  task.

- [ ] **Step 1: Inspect the required tools without installing anything**

```bash
cd /Users/atharvafulay/Documents/Wikix
git --version
gh --version
gh auth status
python3 --version
command -v uv
uv --version
```

Expected: Git and GitHub CLI are authenticated for `wikix-project/wikix`, Python is 3.12 or newer,
and `uv` resolves to an executable. The restarted Codex environment did not have `uv` at plan-writing
time, so do not assume this gate is already green.

- [ ] **Step 2: If uv is absent, stop for installation approval**

After explicit approval, install uv with the maintainer's package manager:

```bash
brew install uv
uv --version
```

Expected: uv reports an installed version. Do not modify project files to work around a missing
machine-level tool. The existing `.venv` may verify current Python tests, but it cannot replace uv
for lockfile, clean-sync, and package-build gates.

- [ ] **Step 3: Verify a frozen clean setup on current main**

```bash
git fetch --prune origin
uv sync --extra dev --frozen
uv run pytest -q
```

Expected: the current main baseline passes before any issue branch is created. If it fails, stop and
classify the failure as product, dependency, or environment before continuing.

### Task 1: Publish the approved planning documents for review

**Files:**
- Modify: `docs/release-candidate-preparation.md`
- Create: `docs/release-candidate-implementation-plan.md`

**Interfaces:**
- Consumes: approved issue [#3](https://github.com/wikix-project/wikix/issues/3) and branch
  `docs/3-release-candidate-plan`.
- Produces: a draft documentation PR that is the public release-train reference; no product code.

- [ ] **Step 1: Verify the isolated planning branch**

```bash
git fetch --prune origin
git status --short --branch
git diff --check origin/main...HEAD
git diff --name-status origin/main...HEAD
```

Expected: branch `docs/3-release-candidate-plan`, no uncommitted files, and only the two planning
documents differ from `origin/main`.

- [ ] **Step 2: Run the final planning-branch quality gate**

```bash
uv sync --extra dev --frozen
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=wikix
```

Expected: 150 tests pass on the current baseline and coverage remains at least 90%. If test count
has legitimately changed on a newer main, record the new complete count instead of forcing 150.

- [ ] **Step 3: Push only the planning branch**

```bash
git push -u origin docs/3-release-candidate-plan
```

- [ ] **Step 4: Open a draft PR linked to issue #3**

```bash
gh pr create --repo wikix-project/wikix --draft --base main \
  --head docs/3-release-candidate-plan \
  --title "Document the Wikix 1.0 release-candidate preparation plan" \
  --body "## Summary

- define isolated public and confidential launch-readiness streams
- define migration, verification, handoff, and cleanup gates
- add the issue-first execution plan

## Verification

- uv run ruff check .
- uv run ruff format --check .
- uv run mypy src
- uv run pytest --cov=wikix

Fixes #3"
```

- [ ] **Step 5: Verify the live PR and stop short of merge**

```bash
gh pr view --repo wikix-project/wikix --json url,isDraft,baseRefName,headRefName,files,commits
gh pr checks --repo wikix-project/wikix --watch
```

Expected: base `main`, head `docs/3-release-candidate-plan`, only the planning documents changed,
and required checks pass. Leave the PR open and unmerged.

### Task 2: Refresh the migration ledger and live competition state

**Files:**
- No tracked repository changes.
- Private output: the draft advisory ledger.
- Public output: a redacted issue #3 comment recording refreshed source fingerprints and statuses.

**Interfaces:**
- Consumes: the Source Inventory table and all existing Wikix worktrees.
- Produces: authoritative public and private ledgers used by Tasks 3-12.

- [ ] **Step 1: Recheck the remote and public work**

```bash
cd /Users/atharvafulay/Documents/Wikix
git fetch --prune origin
gh issue list --repo wikix-project/wikix --state all --limit 100
gh pr list --repo wikix-project/wikix --state all --limit 100
gh api repos/wikix-project/wikix/branches --paginate --jq '.[].name'
git worktree list --porcelain
```

Expected: record current main, issues, PRs, branches, and every local worktree before migration.

- [ ] **Step 2: Verify the uncommitted hardening fingerprint without changing it**

```bash
git -C .worktrees/foundational-hardening diff --binary \
  --output=/tmp/wikix-foundational-hardening.patch
shasum -a 256 /tmp/wikix-foundational-hardening.patch
git -C .worktrees/foundational-hardening status --short
```

Expected SHA-256:
`1327bcc006312bf73666c0b03acd9f26bfa11068f898c1c519e021cbef0acffd`.

- [ ] **Step 3: Verify the website-source fingerprint without changing it**

```bash
git -C .worktrees/wikix-site-polish diff --binary origin/main...HEAD \
  --output=/tmp/wikix-site-polish.patch
shasum -a 256 /tmp/wikix-site-polish.patch
git -C .worktrees/wikix-site-polish status --short
```

Expected SHA-256 at the observed main:
`02e70f73fd51dfc0c5914be8f4e50173ee14c24d83eba8ed8e9bcbc961ddf957`.
If `origin/main` advanced, recompute and review the semantic diff rather than expecting the old hash.

- [ ] **Step 4: Prove the integrated onboarding worktree has no unique tree content**

```bash
git -C .worktrees/integrate-beginner-onboarding rev-parse HEAD^{tree}
git rev-parse origin/main^{tree}
git -C .worktrees/integrate-beginner-onboarding status --short
```

Expected: equal tree IDs and a clean worktree. Record this as cleanup evidence only; do not remove
the worktree.

- [ ] **Step 5: Post the redacted public ledger**

```bash
gh issue comment 3 --repo wikix-project/wikix --body "Migration ledger refreshed.

- live/staged validation: source verified; migration pending
- Markdown rendering safety: source verified; migration pending
- local metadata and CLI failures: source verified; migration pending
- bounded rate-limit waiting: source verified; migration pending
- website/setup pages: source verified; additive port pending
- confidential remediation: tracked privately
- existing branches and worktrees: preserved

No merge, release, deployment, setting change, or cleanup action has been performed."
```

### Task 3: Prepare confidential remediation through a draft security advisory

**Files:**
- Public files: none.
- Private files and branch: created only through the GitHub Security Advisory private process.

**Interfaces:**
- Consumes: the confidential source ledger and current `origin/main`.
- Produces: a tested confidential commit/branch and private advisory status for the local RC.

The technical patch plan is intentionally excluded from this public document. Before editing code,
the private advisory must contain the exact affected boundary, reproduction, impact, test names,
source fingerprints, minimal remediation, rollback, and disclosure notes.

- [ ] **Step 1: Verify advisory capability and current security settings**

```bash
gh api repos/wikix-project/wikix --jq \
  '{private_vulnerability_reporting:.security_and_analysis.private_vulnerability_reporting,
    secret_scanning:.security_and_analysis.secret_scanning,
    push_protection:.security_and_analysis.secret_scanning_push_protection}'
```

Expected: capture current values. Do not change them in this task.

- [ ] **Step 2: Create a draft private advisory**

Use GitHub's Security Advisories interface as a repository administrator. Populate all private
fields from the confidential ledger. Do not create a public issue, public branch, or public comment.

Expected: the advisory remains draft and visible only to authorized collaborators.

- [ ] **Step 3: Create the confidential branch from current main**

Create the branch through the advisory's private temporary fork or other GitHub-provided private
remediation mechanism. Confirm its base commit equals current `origin/main` before applying code,
and create the local-only alias `security/wikix-1.0-private` for the tested private head. Never push
that alias to the public repository.

- [ ] **Step 4: Follow the private red-green plan**

Apply only the private regression tests first, run them to observe the documented failure, then
apply the smallest remediation from the private ledger. Technical commands and output stay in the
advisory record.

- [ ] **Step 5: Run the complete confidential-branch quality gate**

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=wikix
```

Expected: all checks pass with no real credentials or private bookmark content in fixtures or logs.

- [ ] **Step 6: Record the private head and leave the advisory unpublished**

Record the exact private head commit in the advisory ledger. Do not merge to public main, publish
the advisory, or expose the private head in a public artifact.

### Task 4: Unify validation for live and recovered API pages

**Files:**
- Modify: `src/wikix/api.py`
- Modify: `src/wikix/staging.py`
- Modify: `src/wikix/sync.py`
- Test: `tests/test_api.py`
- Test: `tests/test_staging.py`
- Test: `tests/test_sync.py`

**Interfaces:**
- Consumes: `XApiClient`, `ApiPage`, and `SnapshotStager`.
- Produces: one normalized page validator used by live API normalization and staged-page recovery;
  invalid live or staged data raises or causes safe refetch before reconciliation.

- [ ] **Step 1: Create the public issue after a live duplicate check**

```bash
gh issue list --repo wikix-project/wikix --state open --search \
  'validation staged API pages in:title,body'
WIKIX_API_ISSUE_URL=$(gh issue create --repo wikix-project/wikix --label bug \
  --title "Validate live and recovered API pages consistently" \
  --body "## Problem

Live API pages and recovered staging pages do not enforce one complete record contract. Malformed
folder, membership, include, or nested record data can survive one boundary and fail later.

## Expected behavior

Use one validator for normalized live and staged pages. Invalid live data fails before a snapshot is
accepted; invalid staged data is discarded so the next sync safely refetches it.

## Acceptance criteria

- validate bookmark, folder, and membership records and post includes
- validate non-empty ASCII-decimal identifiers and pagination tokens
- reject malformed nested post, user, media, entity, attachment, and reference fields
- discard incompatible staged pages without replacing the last good export
- preserve complete-snapshot and resume behavior

## Non-goals

- changing the exported schema
- adding endpoints or import sources
- exposing confidential remediation details")
WIKIX_API_ISSUE_NUMBER=${WIKIX_API_ISSUE_URL##*/}
```

- [ ] **Step 2: Create an isolated issue branch from current main**

```bash
cd /Users/atharvafulay/Documents/Wikix
git fetch --prune origin
git worktree add ".worktrees/issue-${WIKIX_API_ISSUE_NUMBER}-api-validation" \
  -b "fix/${WIKIX_API_ISSUE_NUMBER}-api-page-validation" origin/main
cd ".worktrees/issue-${WIKIX_API_ISSUE_NUMBER}-api-validation"
uv sync --extra dev --frozen
```

- [ ] **Step 3: Apply only the existing regression tests**

```bash
git diff b489c1b^ b489c1b -- tests/test_api.py tests/test_staging.py tests/test_sync.py \
  | git apply --3way
git -C ../foundational-hardening diff -- tests/test_api.py tests/test_staging.py \
  tests/test_sync.py | git apply --3way
```

Retain these named contracts: `test_api_rejects_non_object_json`,
`test_get_me_rejects_non_ascii_decimal_account_ids`,
`test_api_rejects_nested_data_normalization_cannot_consume`,
`test_folder_page_rejects_a_supplied_mismatched_result_count`,
`test_recovered_bookmark_pages_enforce_live_api_validation`, and
`test_corrupt_nested_staging_restarts_full_scan`.

- [ ] **Step 4: Run the focused tests and observe the intended failure**

```bash
uv run pytest tests/test_api.py tests/test_staging.py tests/test_sync.py -q
```

Expected: the new malformed-record and recovered-page tests fail because current main validates
live and staged pages differently. Existing unrelated tests must remain green.

- [ ] **Step 5: Apply the minimal implementation diff**

```bash
git diff b489c1b^ b489c1b -- src/wikix/api.py src/wikix/staging.py src/wikix/sync.py \
  | git apply --3way
git -C ../foundational-hardening diff -- src/wikix/api.py src/wikix/staging.py \
  | git apply --3way
```

Keep `validate_normalized_page(payload: object, *, item_kind: PageKind) -> None` as the shared
boundary. Do not copy confidential changes or unrelated retry behavior from the source worktree.

- [ ] **Step 6: Run focused and full verification**

```bash
uv run pytest tests/test_api.py tests/test_staging.py tests/test_sync.py -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=wikix
```

Expected: all checks pass and coverage remains at least 90%.

- [ ] **Step 7: Commit only owned files**

```bash
git add -- src/wikix/api.py src/wikix/staging.py src/wikix/sync.py \
  tests/test_api.py tests/test_staging.py tests/test_sync.py
git commit -m "fix: validate live and staged API pages"
```

- [ ] **Step 8: Push and open a draft PR**

```bash
git push -u origin "fix/${WIKIX_API_ISSUE_NUMBER}-api-page-validation"
gh pr create --repo wikix-project/wikix --draft --base main \
  --head "fix/${WIKIX_API_ISSUE_NUMBER}-api-page-validation" \
  --title "Validate live and recovered API pages consistently" \
  --body "## Summary

- share the normalized-page contract between live API and staging recovery
- reject malformed nested records before reconciliation
- discard invalid staged data for safe refetch

## Verification

- uv run ruff check .
- uv run ruff format --check .
- uv run mypy src
- uv run pytest --cov=wikix

Fixes #${WIKIX_API_ISSUE_NUMBER}"
```

- [ ] **Step 9: Verify CI, review state, and final source mapping**

```bash
gh pr checks --repo wikix-project/wikix --watch
gh pr view --repo wikix-project/wikix --json url,isDraft,mergeable,files,commits
```

Record the destination commit in the ledger. Mark ready only when checks pass and the diff contains
no confidential or unrelated change. Do not merge.

### Task 5: Keep remote Markdown metadata inert

**Files:**
- Modify: `src/wikix/records.py`
- Test: `tests/test_records.py`

**Interfaces:**
- Consumes: `BookmarkRecordV1` and `render_markdown`.
- Produces: escaped labels, HTTP(S)-only links, control-character rejection, and fenced referenced
  text without mutating the machine-readable record.

- [ ] **Step 1: Create the issue and branch**

```bash
gh issue list --repo wikix-project/wikix --state open --search \
  'Markdown remote metadata inert in:title,body'
WIKIX_MARKDOWN_ISSUE_URL=$(gh issue create --repo wikix-project/wikix --label bug \
  --title "Keep remote metadata inert in exported Markdown" \
  --body "## Problem

Remote labels, URLs, and referenced text can be interpreted as active Markdown instead of literal
bookmark metadata.

## Expected behavior

Render remote metadata as inert text. Only valid HTTP(S) URLs become links, labels are escaped, and
referenced post text is fenced safely while JSONL retains the original values.

## Acceptance criteria

- escape Markdown label characters
- reject non-HTTP(S), relative, hostname-free, or control-character URLs
- fence referenced text with a collision-safe fence
- preserve original normalized record values

## Non-goals

- sanitizing user-owned personal notes
- rewriting JSONL source values")
WIKIX_MARKDOWN_ISSUE_NUMBER=${WIKIX_MARKDOWN_ISSUE_URL##*/}
cd /Users/atharvafulay/Documents/Wikix
git fetch --prune origin
git worktree add ".worktrees/issue-${WIKIX_MARKDOWN_ISSUE_NUMBER}-markdown-safety" \
  -b "fix/${WIKIX_MARKDOWN_ISSUE_NUMBER}-markdown-safety" origin/main
cd ".worktrees/issue-${WIKIX_MARKDOWN_ISSUE_NUMBER}-markdown-safety"
uv sync --extra dev --frozen
```

- [ ] **Step 2: Apply and run the existing regression tests first**

```bash
git diff 988cd99^ 988cd99 -- tests/test_records.py | git apply --3way
git diff 2fe8b76^ 2fe8b76 -- tests/test_records.py | git apply --3way
uv run pytest tests/test_records.py::test_render_markdown_keeps_remote_metadata_inert \
  tests/test_records.py::test_render_markdown_does_not_link_urls_with_control_characters -q
```

Expected: FAIL because current main still emits remote labels and URLs using active Markdown forms.

- [ ] **Step 3: Apply the minimal renderer changes**

```bash
git diff 988cd99^ 988cd99 -- src/wikix/records.py | git apply --3way
git diff 2fe8b76^ 2fe8b76 -- src/wikix/records.py | git apply --3way
```

Keep `_escape_markdown_label`, `_safe_http_url`, `_render_link`, and collision-safe fence selection
private to `records.py`; do not change the JSONL schema.

- [ ] **Step 4: Verify, commit, and publish the draft PR**

```bash
uv run pytest tests/test_records.py -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=wikix
git add -- src/wikix/records.py tests/test_records.py
git commit -m "fix: render remote Markdown metadata safely"
git push -u origin "fix/${WIKIX_MARKDOWN_ISSUE_NUMBER}-markdown-safety"
gh pr create --repo wikix-project/wikix --draft --base main \
  --head "fix/${WIKIX_MARKDOWN_ISSUE_NUMBER}-markdown-safety" \
  --title "Keep remote metadata inert in exported Markdown" \
  --body "Safely renders remote labels, URLs, and referenced text without changing JSONL values.

Verification: Ruff, Ruff format, strict mypy, and full pytest with coverage.

Fixes #${WIKIX_MARKDOWN_ISSUE_NUMBER}"
gh pr checks --repo wikix-project/wikix --watch
```

Expected: checks pass. Record the destination commit, inspect the live diff, and do not merge.

### Task 6: Reject malformed local metadata with clean CLI failures

**Files:**
- Modify: `src/wikix/auth.py`
- Modify: `src/wikix/cli.py`
- Modify: `src/wikix/config.py`
- Modify: `src/wikix/state.py`
- Modify: `src/wikix/reconcile.py`
- Test: `tests/test_auth.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_config.py`
- Test: `tests/test_reconcile.py`

**Interfaces:**
- Consumes: `CollectionConfig`, `CollectionState`, `CredentialStore`, and CLI command loaders.
- Produces: strict persisted metadata validation and concise `Error:` output without partial
  collection creation, export mutation, validation tracebacks, or credential contents.

- [ ] **Step 1: Create the issue and isolated branch**

```bash
gh issue list --repo wikix-project/wikix --state open --search \
  'malformed local metadata CLI in:title,body'
WIKIX_LOCAL_DATA_ISSUE_URL=$(gh issue create --repo wikix-project/wikix --label bug \
  --title "Reject malformed local metadata with clean CLI errors" \
  --body "## Problem

Unsupported collection metadata, corrupt stored credential JSON, and malformed OAuth responses can
surface as validation tracebacks or fail after partial local work.

## Expected behavior

Validate persisted non-secret metadata before mutation and report malformed local or OAuth data as
concise CLI errors without exposing credential content.

## Acceptance criteria

- forbid unsupported schema versions and unknown metadata fields
- validate IDs, callback ports, and review dates
- avoid partial collection creation for invalid initialization
- preserve the last good export when state is invalid
- report configuration, state, stored-credential, and OAuth parse failures without tracebacks

## Non-goals

- changing the collection schema version
- persisting credentials outside the operating-system store")
WIKIX_LOCAL_DATA_ISSUE_NUMBER=${WIKIX_LOCAL_DATA_ISSUE_URL##*/}
cd /Users/atharvafulay/Documents/Wikix
git fetch --prune origin
git worktree add ".worktrees/issue-${WIKIX_LOCAL_DATA_ISSUE_NUMBER}-local-data" \
  -b "fix/${WIKIX_LOCAL_DATA_ISSUE_NUMBER}-local-data-errors" origin/main
cd ".worktrees/issue-${WIKIX_LOCAL_DATA_ISSUE_NUMBER}-local-data"
uv sync --extra dev --frozen
```

- [ ] **Step 2: Apply the public regression tests only**

```bash
git diff 3be0505^ 3be0505 -- tests/test_config.py tests/test_reconcile.py | git apply --3way
git diff 14081b0^ 14081b0 -- tests/test_auth.py tests/test_cli.py | git apply --3way
git diff 2fe8b76^ 2fe8b76 -- tests/test_cli.py | git apply --3way
```

Retain tests for invalid config/state values, no partial initialization, no reconciliation mutation,
corrupt stored JSON, non-JSON OAuth responses, and traceback-free CLI output. Do not copy private
credential-boundary tests from the confidential ledger.

- [ ] **Step 3: Run focused tests and confirm the failures**

```bash
uv run pytest tests/test_auth.py tests/test_cli.py tests/test_config.py \
  tests/test_reconcile.py -q
```

Expected: new invalid-metadata and clean-error tests fail while unrelated existing tests pass.

- [ ] **Step 4: Apply only the public implementation hunks**

```bash
git diff 3be0505^ 3be0505 -- src/wikix/config.py src/wikix/state.py \
  src/wikix/reconcile.py | git apply --3way
git diff 14081b0^ 14081b0 -- src/wikix/auth.py src/wikix/cli.py | git apply --3way
git diff 2fe8b76^ 2fe8b76 -- src/wikix/cli.py src/wikix/state.py | git apply --3way
```

Keep strict metadata models and CLI error translation. If a hunk overlaps confidential work, leave
the public branch on current-main behavior and resolve the overlap later inside the private branch.

- [ ] **Step 5: Verify, commit, and open the draft PR**

```bash
uv run pytest tests/test_auth.py tests/test_cli.py tests/test_config.py \
  tests/test_reconcile.py -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=wikix
git add -- src/wikix/auth.py src/wikix/cli.py src/wikix/config.py src/wikix/state.py \
  src/wikix/reconcile.py tests/test_auth.py tests/test_cli.py tests/test_config.py \
  tests/test_reconcile.py
git commit -m "fix: report invalid local metadata safely"
git push -u origin "fix/${WIKIX_LOCAL_DATA_ISSUE_NUMBER}-local-data-errors"
gh pr create --repo wikix-project/wikix --draft --base main \
  --head "fix/${WIKIX_LOCAL_DATA_ISSUE_NUMBER}-local-data-errors" \
  --title "Reject malformed local metadata with clean CLI errors" \
  --body "Validates persisted collection metadata before mutation and reports malformed local data
without tracebacks or credential contents.

Verification: Ruff, Ruff format, strict mypy, and full pytest with coverage.

Fixes #${WIKIX_LOCAL_DATA_ISSUE_NUMBER}"
gh pr checks --repo wikix-project/wikix --watch
```

Expected: checks pass, the live PR contains public handling only, and no confidential test or hunk
is present. Record the commit and do not merge.

### Task 7: Bound persistent rate-limit waiting

**Files:**
- Modify: `src/wikix/api.py`
- Modify: `README.md`
- Modify: `docs/getting-started.md` or the retained platform guides that own troubleshooting copy
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `XApiClient._request_json`, injected clock, and injected sleep function.
- Produces: at most three rate-limit waits and at most 900 cumulative wait seconds per request;
  exhaustion raises `XApiError` with status 429 while resumable staging protects prior output.

- [ ] **Step 1: Create the issue and branch**

```bash
gh issue list --repo wikix-project/wikix --state open --search \
  'rate-limit wait budget in:title,body'
WIKIX_RATE_ISSUE_URL=$(gh issue create --repo wikix-project/wikix --label bug \
  --title "Bound persistent X rate-limit waiting" \
  --body "## Problem

Repeated HTTP 429 responses can keep one request waiting indefinitely.

## Expected behavior

Use a dedicated response-count and cumulative-time budget for rate-limit waits. Exhaustion exits
cleanly with status 429 so the staged scan can resume later without replacing the prior export.

## Acceptance criteria

- allow at most three rate-limit waits per request
- allow at most 900 cumulative wait seconds per request
- use a 60-second default for missing, invalid, or non-finite reset values
- keep rate-limit and transient-failure budgets independent
- document the bounded behavior

## Non-goals

- background scheduling
- changing transient retry counts")
WIKIX_RATE_ISSUE_NUMBER=${WIKIX_RATE_ISSUE_URL##*/}
cd /Users/atharvafulay/Documents/Wikix
git fetch --prune origin
git worktree add ".worktrees/issue-${WIKIX_RATE_ISSUE_NUMBER}-rate-limit" \
  -b "fix/${WIKIX_RATE_ISSUE_NUMBER}-rate-limit-budget" origin/main
cd ".worktrees/issue-${WIKIX_RATE_ISSUE_NUMBER}-rate-limit"
uv sync --extra dev --frozen
```

- [ ] **Step 2: Apply and run the rate-limit tests first**

```bash
git diff f23cc00^ f23cc00 -- tests/test_api.py | git apply --3way
uv run pytest tests/test_api.py -k 'persistent_rate_limit or cumulative_budget or \
invalid_rate_limit or past_rate_limit or independent_budgets' -q
```

Expected: FAIL because current main has no rate-limit count or cumulative wait budget.

- [ ] **Step 3: Apply the implementation and adapt documentation to current main**

```bash
git diff f23cc00^ f23cc00 -- src/wikix/api.py README.md | git apply --3way
```

Add the same 3-response/900-second/60-second contract to the troubleshooting sections of each
current platform guide that mentions HTTP 429. Do not replace the platform chooser with the older
single getting-started document from the source commit.

- [ ] **Step 4: Verify, commit, and open the draft PR**

```bash
uv run pytest tests/test_api.py -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=wikix
git add -- src/wikix/api.py tests/test_api.py README.md docs/getting-started-macos.md \
  docs/getting-started-windows.md docs/getting-started-linux.md
git commit -m "fix: bound X rate-limit waiting"
git push -u origin "fix/${WIKIX_RATE_ISSUE_NUMBER}-rate-limit-budget"
gh pr create --repo wikix-project/wikix --draft --base main \
  --head "fix/${WIKIX_RATE_ISSUE_NUMBER}-rate-limit-budget" \
  --title "Bound persistent X rate-limit waiting" \
  --body "Bounds repeated 429 waits while preserving independent transient retries and resumable
staging.

Verification: Ruff, Ruff format, strict mypy, and full pytest with coverage.

Fixes #${WIKIX_RATE_ISSUE_NUMBER}"
gh pr checks --repo wikix-project/wikix --watch
```

Expected: checks pass. Confirm docs state exact limits, record the destination commit, and do not
merge.

### Task 8: Port the polished website without replacing platform onboarding

**Files:**
- Modify: `.vercelignore`
- Modify: `index.html`
- Modify: `styles.css`
- Modify: `docs/getting-started.md`
- Create: `guide.html`
- Create: `quick-setup.html`
- Create: `docs/quick-setup.md`
- Modify: `tests/test_landing_page.py`
- Create: `tests/test_guide_page.py`
- Create: `tests/test_quick_setup_page.py`
- Preserve unchanged: `docs/getting-started-macos.md`
- Preserve unchanged: `docs/getting-started-windows.md`
- Preserve unchanged: `docs/getting-started-linux.md`
- Preserve unchanged: `tests/test_onboarding_docs.py`

**Interfaces:**
- Consumes: the current static landing page, current `uv` source install contract, and existing OS
  chooser/guides.
- Produces: `/guide.html` and `/quick-setup.html` as static, responsive routes plus matching concise
  documentation, while the existing platform guides remain complete.

- [ ] **Step 1: Create the issue and branch**

```bash
gh issue list --repo wikix-project/wikix --state open --search \
  'Quick Setup Step-by-Step website in:title,body'
WIKIX_SITE_ISSUE_URL=$(gh issue create --repo wikix-project/wikix --label documentation \
  --label enhancement --title "Add separate Quick Setup and Step-by-Step website pages" \
  --body "## Problem

The landing page sends every prospective user into the same documentation path, while a polished
short setup page and a detailed website guide exist only in an unintegrated local branch.

## Expected behavior

Add separate static Quick Setup and Step-by-Step pages using the current visual system. Preserve the
merged macOS, Windows, and Linux onboarding and current source-only uv installation claims.

## Acceptance criteria

- add static semantic guide and quick-setup routes with no client JavaScript
- link both routes from the landing page and footer
- retain the OS chooser and all three platform guides
- keep all commands aligned with uv source installation
- include only required static assets in Vercel previews
- verify responsive layouts and reduced-motion behavior

## Non-goals

- publishing to PyPI
- production deployment
- replacing the platform-specific onboarding")
WIKIX_SITE_ISSUE_NUMBER=${WIKIX_SITE_ISSUE_URL##*/}
cd /Users/atharvafulay/Documents/Wikix
git fetch --prune origin
git worktree add ".worktrees/issue-${WIKIX_SITE_ISSUE_NUMBER}-setup-pages" \
  -b "docs/${WIKIX_SITE_ISSUE_NUMBER}-setup-pages" origin/main
cd ".worktrees/issue-${WIKIX_SITE_ISSUE_NUMBER}-setup-pages"
uv sync --extra dev --frozen
```

- [ ] **Step 2: Apply the page-contract tests without accepting stale install copy**

```bash
git diff origin/main...codex/wikix-site-polish -- tests/test_guide_page.py \
  tests/test_landing_page.py tests/test_quick_setup_page.py | git apply --3way
```

In the new tests, use this exact source command:

```python
SOURCE_INSTALL = "uv tool install --python 3.12 git+https://github.com/wikix-project/wikix.git"
```

Replace the older detailed-document assumptions with this retained-onboarding contract:

```python
def test_getting_started_preserves_platform_chooser_and_links_quick_setup() -> None:
    content = (ROOT / "docs/getting-started.md").read_text(encoding="utf-8")

    assert "[Quick setup](quick-setup.md)" in content
    assert "[macOS](getting-started-macos.md)" in content
    assert "[Windows](getting-started-windows.md)" in content
    assert "[Linux](getting-started-linux.md)" in content
```

Remove only source-branch tests that require replacing the OS chooser with numbered detailed
headings. Keep semantic HTML, route, command, navigation, and Vercel allowlist assertions.

- [ ] **Step 3: Run the new contracts and observe the missing-page failures**

```bash
uv run pytest tests/test_landing_page.py tests/test_guide_page.py \
  tests/test_quick_setup_page.py tests/test_onboarding_docs.py -q
```

Expected: FAIL because `guide.html`, `quick-setup.html`, and `docs/quick-setup.md` do not exist and
the landing page does not link them.

- [ ] **Step 4: Port only the additive website files**

```bash
git diff origin/main...codex/wikix-site-polish -- .vercelignore docs/quick-setup.md \
  guide.html index.html quick-setup.html styles.css | git apply --3way
```

Replace every older `pipx install git+https://github.com/wikix-project/wikix.git` occurrence in the
ported files with the exact `uv tool install --python 3.12` source command. Add
`[Quick setup](quick-setup.md)` to the current OS chooser without replacing its platform links or
introductory cost warning.

- [ ] **Step 5: Verify content contracts and stale-copy exclusions**

```bash
uv run pytest tests/test_landing_page.py tests/test_guide_page.py \
  tests/test_quick_setup_page.py tests/test_onboarding_docs.py -q
rg -n 'pipx install wikix|pipx install git\+' README.md docs index.html guide.html quick-setup.html
git diff --exit-code origin/main -- docs/getting-started-macos.md \
  docs/getting-started-windows.md docs/getting-started-linux.md
```

Expected: tests pass, the `rg` search returns no match, and all three OS guides remain byte-for-byte
unchanged in this issue.

- [ ] **Step 6: Run the full quality gate and browser verification**

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=wikix
python3 -m http.server 4173
```

Inspect `/`, `/guide.html`, and `/quick-setup.html` at desktop and mobile widths in light and dark
appearance. Verify keyboard navigation, visible focus, command wrapping, no horizontal scrolling,
no script requests, local font loading, and reduced-motion behavior. Stop the local server after
inspection.

- [ ] **Step 7: Commit, push, and open the draft PR**

```bash
git add -- .vercelignore docs/getting-started.md docs/quick-setup.md guide.html index.html \
  quick-setup.html styles.css tests/test_guide_page.py tests/test_landing_page.py \
  tests/test_quick_setup_page.py
git commit -m "docs: add separate website setup pages"
git push -u origin "docs/${WIKIX_SITE_ISSUE_NUMBER}-setup-pages"
gh pr create --repo wikix-project/wikix --draft --base main \
  --head "docs/${WIKIX_SITE_ISSUE_NUMBER}-setup-pages" \
  --title "Add separate Quick Setup and Step-by-Step website pages" \
  --body "Adds two static setup paths while preserving the merged platform onboarding and current
uv source-install contract.

Verification: focused page/onboarding tests, Ruff, Ruff format, strict mypy, full pytest, and local
responsive browser checks.

Fixes #${WIKIX_SITE_ISSUE_NUMBER}"
gh pr checks --repo wikix-project/wikix --watch
```

Expected: checks pass and the live diff contains no deletion of platform guides. Do not deploy or
merge.

### Task 9: Prepare coherent Wikix 1.0 package metadata

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `src/wikix/__init__.py`
- Modify: `tests/test_package.py`

**Interfaces:**
- Consumes: Hatchling metadata and the public `wikix.__version__` CLI contract.
- Produces: version `1.0.0`, synchronized runtime/package versions, stable classifier metadata, and
  no unused direct `platformdirs` dependency.

- [ ] **Step 1: Create the package-metadata issue and draft branch**

```bash
gh issue list --repo wikix-project/wikix --state open --search \
  '1.0 package metadata platformdirs in:title,body'
WIKIX_PACKAGE_ISSUE_URL=$(gh issue create --repo wikix-project/wikix --label enhancement \
  --title "Prepare coherent Wikix 1.0 package metadata" \
  --body "## Problem

The release candidate still reports 0.1.0 alpha metadata and declares an unused direct runtime
dependency.

## Expected behavior

Prepare synchronized 1.0.0 package and CLI metadata, use a stable development-status classifier,
and remove the unused direct dependency without changing runtime behavior.

## Acceptance criteria

- pyproject and wikix.__version__ both report 1.0.0
- package tests enforce version synchronization
- metadata uses Development Status :: 5 - Production/Stable
- platformdirs is not a direct project dependency
- the lockfile is regenerated and frozen sync succeeds
- clean wheel and sdist install and report Wikix 1.0.0

## Non-goals

- tagging or publishing the package
- changing command behavior")
WIKIX_PACKAGE_ISSUE_NUMBER=${WIKIX_PACKAGE_ISSUE_URL##*/}
cd /Users/atharvafulay/Documents/Wikix
git fetch --prune origin
git worktree add ".worktrees/issue-${WIKIX_PACKAGE_ISSUE_NUMBER}-package-metadata" \
  -b "build/${WIKIX_PACKAGE_ISSUE_NUMBER}-package-metadata" origin/main
cd ".worktrees/issue-${WIKIX_PACKAGE_ISSUE_NUMBER}-package-metadata"
uv sync --extra dev --frozen
```

- [ ] **Step 2: Strengthen the metadata test and observe the intended failure**

Add this assertion to `tests/test_package.py`:

```python
def test_package_metadata_matches_the_1_0_release_contract() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert project["version"] == "1.0.0"
    assert wikix.__version__ == "1.0.0"
    assert "Development Status :: 5 - Production/Stable" in project["classifiers"]
    assert not any(dependency.startswith("platformdirs") for dependency in project["dependencies"])
```

```bash
uv run pytest tests/test_package.py -q
```

Expected: FAIL on current version, classifier, and direct dependency.

- [ ] **Step 3: Make the minimal metadata changes**

In `pyproject.toml`, set `version = "1.0.0"`, replace the Alpha classifier with
`Development Status :: 5 - Production/Stable`, and remove `platformdirs>=4.3` from direct
dependencies. In `src/wikix/__init__.py`, set `__version__ = "1.0.0"`.

```bash
uv lock
uv sync --extra dev --frozen
```

- [ ] **Step 4: Verify package metadata and clean installation**

```bash
uv run pytest tests/test_package.py tests/test_cli.py::test_version_command -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=wikix
uv build
python3 -m venv /tmp/wikix-package-smoke
/tmp/wikix-package-smoke/bin/pip install dist/*.whl
/tmp/wikix-package-smoke/bin/wikix --version
/tmp/wikix-package-smoke/bin/pip uninstall -y wikix
```

Expected: the wheel installs, reports `Wikix 1.0.0`, and uninstalls cleanly. Inspect wheel/sdist
contents and METADATA to confirm repository URLs, Python requirement, license, classifiers, and
direct dependencies.

- [ ] **Step 5: Commit and open a draft PR only**

```bash
git add -- pyproject.toml uv.lock src/wikix/__init__.py tests/test_package.py
git commit -m "build: prepare Wikix 1.0 package metadata"
git push -u origin "build/${WIKIX_PACKAGE_ISSUE_NUMBER}-package-metadata"
gh pr create --repo wikix-project/wikix --draft --base main \
  --head "build/${WIKIX_PACKAGE_ISSUE_NUMBER}-package-metadata" \
  --title "Prepare coherent Wikix 1.0 package metadata" \
  --body "Synchronizes 1.0.0 metadata, removes one unused direct dependency, and verifies clean
artifacts without tagging or publishing.

Verification: full quality gate, clean build, wheel install/version/uninstall smoke.

Fixes #${WIKIX_PACKAGE_ISSUE_NUMBER}"
gh pr checks --repo wikix-project/wikix --watch
```

Leave this PR draft until every launch-critical gate, including the live X smoke test, is green.

### Task 10: Pin release actions and test package construction in CI

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/release.yml`
- Create: `tests/test_workflows.py`

**Interfaces:**
- Consumes: GitHub Actions workflows and Hatchling build configuration.
- Produces: immutable third-party action references, least-privilege workflow permissions, and a CI
  package-smoke job that builds and installs artifacts without publishing.

- [ ] **Step 1: Create the workflow-hardening issue and branch**

```bash
gh issue list --repo wikix-project/wikix --state open --search \
  'immutable action package smoke in:title,body'
WIKIX_WORKFLOW_ISSUE_URL=$(gh issue create --repo wikix-project/wikix --label enhancement \
  --title "Pin release actions and verify package construction in CI" \
  --body "## Problem

Several CI and release steps use mutable action tags, and ordinary pull requests do not build and
install the package artifact that the tag workflow would publish.

## Expected behavior

Pin every third-party action to a reviewed 40-character commit and add a non-publishing package
smoke job to CI.

## Acceptance criteria

- every uses reference is an immutable 40-character commit with a readable version comment
- workflow permissions remain least privilege
- CI builds wheel and sdist, installs the wheel, verifies the version, and uninstalls
- release artifact and approval boundaries remain unchanged
- no manual or pull-request event can publish to PyPI

## Non-goals

- configuring external environments or Trusted Publishing
- tagging or publishing a release")
WIKIX_WORKFLOW_ISSUE_NUMBER=${WIKIX_WORKFLOW_ISSUE_URL##*/}
cd /Users/atharvafulay/Documents/Wikix
git fetch --prune origin
git worktree add ".worktrees/issue-${WIKIX_WORKFLOW_ISSUE_NUMBER}-workflows" \
  -b "build/${WIKIX_WORKFLOW_ISSUE_NUMBER}-workflow-hardening" origin/main
cd ".worktrees/issue-${WIKIX_WORKFLOW_ISSUE_NUMBER}-workflows"
uv sync --extra dev --frozen
```

- [ ] **Step 2: Add a failing immutable-reference test**

Create `tests/test_workflows.py`:

```python
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
WORKFLOWS = [ROOT / ".github/workflows/ci.yml", ROOT / ".github/workflows/release.yml"]
USES = re.compile(r"^\s*-?\s*uses:\s*[^@\s]+@([^\s#]+)", re.MULTILINE)


def test_workflow_actions_are_pinned_to_full_commits() -> None:
    references = [
        match
        for workflow in WORKFLOWS
        for match in USES.findall(workflow.read_text(encoding="utf-8"))
    ]

    assert references
    assert all(re.fullmatch(r"[0-9a-f]{40}", reference) for reference in references)


def test_release_publication_remains_tag_only_and_environment_gated() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert 'tags: ["v*"]' in workflow
    assert "environment:" in workflow
    assert "name: pypi" in workflow
    assert "id-token: write" in workflow
```

```bash
uv run pytest tests/test_workflows.py -q
```

Expected: FAIL because current workflows contain mutable version tags.

- [ ] **Step 3: Resolve and record immutable action commits**

Re-resolve these selections through each official GitHub repository and compare them with the
reviewed commits recorded on 2026-08-20:

| Action | Selected release/reference | Reviewed commit |
| --- | --- | --- |
| `actions/checkout` | `v6.1.0` | `d23441a48e516b6c34aea4fa41551a30e30af803` |
| `actions/setup-python` | `v6.3.0` | `ece7cb06caefa5fff74198d8649806c4678c61a1` |
| `astral-sh/setup-uv` | existing reviewed pin | `c771a70e6277c0a99b617c7a806ffedaca235ff9` |
| `anchore/sbom-action` | `v0.24.0` | `e22c389904149dbc22b58101806040fa8d37a610` |
| `actions/upload-artifact` | `v7.0.1` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` |
| `actions/download-artifact` | `v8.0.1` | `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c` |
| `pypa/gh-action-pypi-publish` | `release/v1` head | `dc37677b2e1c63e2034f94d8a5b11f265b73ba33` |
| `actions/attest` | `v4.2.2` | `1e69f48acb82d1966a394da916b4c1698aa569d6` |

If a selected reference moved, review its release notes and source diff before accepting the new
commit. Record the reviewed choice in the issue. Do not substitute a broad major tag.

- [ ] **Step 4: Add the non-publishing package-smoke job**

Add a `package-smoke` job to `.github/workflows/ci.yml` that:

```yaml
package-smoke:
  runs-on: ubuntu-latest
  permissions:
    contents: read
  steps:
    - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0
    - uses: astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9 # reviewed 2026-08-20
    - run: uv build
    - run: uv venv package-smoke
    - run: uv pip install --python package-smoke dist/*.whl
    - run: package-smoke/bin/wikix --version
    - run: uv pip uninstall --python package-smoke wikix
```

Do not add a publish step or broader token permission.

- [ ] **Step 5: Verify workflows, commit, and open the draft PR**

```bash
uv run pytest tests/test_workflows.py -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=wikix
git diff --check
git add -- .github/workflows/ci.yml .github/workflows/release.yml tests/test_workflows.py
git commit -m "build: harden release workflow references"
git push -u origin "build/${WIKIX_WORKFLOW_ISSUE_NUMBER}-workflow-hardening"
gh pr create --repo wikix-project/wikix --draft --base main \
  --head "build/${WIKIX_WORKFLOW_ISSUE_NUMBER}-workflow-hardening" \
  --title "Pin release actions and verify package construction in CI" \
  --body "Pins action dependencies and adds a non-publishing package smoke job while preserving the
tag-only PyPI gate.

Verification: workflow contract tests and the full local quality gate.

Fixes #${WIKIX_WORKFLOW_ISSUE_NUMBER}"
gh pr checks --repo wikix-project/wikix --watch
```

Expected: all matrix, onboarding, quality, workflow-contract, and package-smoke checks pass. Verify
the live PR permissions and action SHAs. Do not merge or configure the `pypi` environment.

### Task 11: Assemble and verify the unpushed local release candidate

**Files:**
- Local-only RC worktree under `.worktrees/`.
- Local-only verification artifacts under `/tmp/wikix-1.0-rc-verification/`.
- No public branch or tracked file changes.

**Interfaces:**
- Consumes: exact private head and all green public stream heads from Tasks 3-10.
- Produces: an unpushed RC commit, artifact checksums, automated evidence, browser evidence, and a
  private/public-safe readiness summary.

- [ ] **Step 1: Record exact component heads and verify every public PR**

```bash
cd /Users/atharvafulay/Documents/Wikix
git fetch --prune origin
gh pr list --repo wikix-project/wikix --state open --json url,headRefName,headRefOid,isDraft
for WIKIX_PR_NUMBER in $(gh pr list --repo wikix-project/wikix --state open \
  --json number --jq '.[].number'); do
  gh pr checks "$WIKIX_PR_NUMBER" --repo wikix-project/wikix --watch
done
```

Expected: every selected public PR is based on main, has a recorded immutable head, and has green
required checks. Record the private head only in the private ledger.

- [ ] **Step 2: Create a disposable local integration branch from current main**

```bash
git worktree add .worktrees/wikix-1.0-rc -b rc/wikix-1.0-local origin/main
cd .worktrees/wikix-1.0-rc
```

Do not push `rc/wikix-1.0-local`.

- [ ] **Step 3: Integrate stream heads in the recorded order**

Apply the confidential head first, then API/staging validation, Markdown safety, local-data errors,
rate-limit handling, website/setup pages, package metadata, and workflow hardening. Use exact commit
IDs resolved immediately before this step:

```bash
WIKIX_CONFIDENTIAL_HEAD=$(git rev-parse security/wikix-1.0-private)
WIKIX_API_VALIDATION_HEAD=$(gh pr list --repo wikix-project/wikix --state open \
  --search '"Validate live and recovered API pages consistently" in:title' \
  --json headRefOid --jq '.[0].headRefOid')
WIKIX_MARKDOWN_SAFETY_HEAD=$(gh pr list --repo wikix-project/wikix --state open \
  --search '"Keep remote metadata inert in exported Markdown" in:title' \
  --json headRefOid --jq '.[0].headRefOid')
WIKIX_LOCAL_DATA_HEAD=$(gh pr list --repo wikix-project/wikix --state open \
  --search '"Reject malformed local metadata with clean CLI errors" in:title' \
  --json headRefOid --jq '.[0].headRefOid')
WIKIX_RATE_LIMIT_HEAD=$(gh pr list --repo wikix-project/wikix --state open \
  --search '"Bound persistent X rate-limit waiting" in:title' \
  --json headRefOid --jq '.[0].headRefOid')
WIKIX_WEBSITE_HEAD=$(gh pr list --repo wikix-project/wikix --state open \
  --search '"Add separate Quick Setup and Step-by-Step website pages" in:title' \
  --json headRefOid --jq '.[0].headRefOid')
WIKIX_PACKAGE_METADATA_HEAD=$(gh pr list --repo wikix-project/wikix --state open \
  --search '"Prepare coherent Wikix 1.0 package metadata" in:title' \
  --json headRefOid --jq '.[0].headRefOid')
WIKIX_WORKFLOW_HARDENING_HEAD=$(gh pr list --repo wikix-project/wikix --state open \
  --search '"Pin release actions and verify package construction in CI" in:title' \
  --json headRefOid --jq '.[0].headRefOid')
git cherry-pick "$WIKIX_CONFIDENTIAL_HEAD"
git cherry-pick "$WIKIX_API_VALIDATION_HEAD"
git cherry-pick "$WIKIX_MARKDOWN_SAFETY_HEAD"
git cherry-pick "$WIKIX_LOCAL_DATA_HEAD"
git cherry-pick "$WIKIX_RATE_LIMIT_HEAD"
git cherry-pick "$WIKIX_WEBSITE_HEAD"
git cherry-pick "$WIKIX_PACKAGE_METADATA_HEAD"
git cherry-pick "$WIKIX_WORKFLOW_HARDENING_HEAD"
```

Before cherry-picking, verify every resolved value is a 40-character commit and matches the ledger.
If a conflict occurs, abort the cherry-pick, correct the owning source branch, rerun its tests,
update its head, recreate the RC worktree, and restart integration.

- [ ] **Step 4: Run the complete automated quality gate**

```bash
uv sync --extra dev --frozen
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=wikix --cov-report=term-missing
uv run pytest tests/test_scale.py -q
```

Expected: the complete suite passes once without targeted-rerun substitution and core coverage is
at least 90%.

- [ ] **Step 5: Build and inspect release artifacts**

```bash
mkdir -p /tmp/wikix-1.0-rc-verification
uv build --out-dir /tmp/wikix-1.0-rc-verification/dist
python3 -m zipfile -l /tmp/wikix-1.0-rc-verification/dist/*.whl
tar -tzf /tmp/wikix-1.0-rc-verification/dist/*.tar.gz
shasum -a 256 /tmp/wikix-1.0-rc-verification/dist/*
python3 -m venv /tmp/wikix-1.0-rc-verification/venv
/tmp/wikix-1.0-rc-verification/venv/bin/pip install \
  /tmp/wikix-1.0-rc-verification/dist/*.whl
/tmp/wikix-1.0-rc-verification/venv/bin/wikix --version
/tmp/wikix-1.0-rc-verification/venv/bin/pip uninstall -y wikix
```

Expected: only intended package files are present, version is `Wikix 1.0.0`, hashes are recorded,
and install/uninstall succeeds.

- [ ] **Step 6: Verify the complete static website locally**

```bash
python3 -m http.server 4173
```

Inspect `/`, `/guide.html`, and `/quick-setup.html` at desktop and mobile widths. Verify local assets,
navigation, visible focus, light/dark appearance, reduced motion, wrapping, no horizontal overflow,
and no JavaScript. Stop the server when finished.

- [ ] **Step 7: Create a preview deployment only if needed for hosting verification**

Create a Vercel preview, not a production deployment. Verify response headers, all three routes,
asset loading, and that `.vercelignore` excludes source, tests, private documentation, and local
artifacts. Record the preview URL privately until public review is appropriate.

- [ ] **Step 8: Mark the credentialed live smoke test explicitly**

Do not request, print, copy, or store the maintainer's credentials. Prepare the exact checklist for
login, lean sync, unchanged repeat sync, rich sync, folder sync, removal/restoration, interruption
and resume, logout, and wheel uninstall. Until the maintainer runs it successfully, mark this gate
yellow and publication-blocking.

- [ ] **Step 9: Keep the RC unpushed**

```bash
git status --short --branch
git log --oneline --decorate origin/main..HEAD
git branch -r --contains HEAD
```

Expected: clean local RC, documented component order, and no remote branch contains the RC head.

### Task 12: Publish the redacted readiness report and stop at approval gates

**Files:**
- Create: `docs/release-readiness.md`
- No modification to product or workflow files.

**Interfaces:**
- Consumes: Tasks 2-11 ledgers and verification evidence.
- Produces: a public-safe readiness PR plus a private handoff containing confidential and RC-only
  identifiers.

- [ ] **Step 1: Create the readiness-report issue and branch**

```bash
gh issue list --repo wikix-project/wikix --state open --search \
  'release readiness report in:title,body'
WIKIX_REPORT_ISSUE_URL=$(gh issue create --repo wikix-project/wikix --label documentation \
  --title "Record Wikix 1.0 release readiness" \
  --body "## Goal

Record the evidence for the prepared Wikix 1.0 candidate without publishing confidential details
or performing launch actions.

## Acceptance criteria

- list public stream PRs and tested dependency order
- report automated gates as green, yellow, or red
- list manual and external publication blockers
- include a redacted cleanup manifest
- include no private advisory details, credentials, private bookmark content, or private head IDs

## Non-goals

- merging, tagging, publishing, deploying, configuring external settings, or deleting work")
WIKIX_REPORT_ISSUE_NUMBER=${WIKIX_REPORT_ISSUE_URL##*/}
cd /Users/atharvafulay/Documents/Wikix
git fetch --prune origin
git worktree add ".worktrees/issue-${WIKIX_REPORT_ISSUE_NUMBER}-readiness" \
  -b "docs/${WIKIX_REPORT_ISSUE_NUMBER}-release-readiness" origin/main
cd ".worktrees/issue-${WIKIX_REPORT_ISSUE_NUMBER}-readiness"
```

- [ ] **Step 2: Write the public-safe readiness matrix**

Create `docs/release-readiness.md` with these sections and actual evidence from Task 11:

```markdown
# Wikix 1.0 Release Readiness

## Candidate scope
## Public pull requests and tested order
## Automated verification
## Package artifact inspection
## Website verification
## Confidential stream status
## Manual X smoke test
## Repository, PyPI, and hosting gates
## Launch sequence and rollback points
## Redacted cleanup manifest
## Stop boundary
```

Use Green, Yellow, or Red for every gate. Do not use an unverified green status. Keep private head
IDs, reproduction details, and the unpushed RC ID in the private handoff only.

- [ ] **Step 3: Record exact yellow external gates without applying them**

The public report must list the observed status of:

- private vulnerability reporting;
- secret scanning and push protection;
- Dependabot security updates;
- branch protection required checks and conversation resolution;
- the protected `pypi` environment and reviewer;
- PyPI project ownership and Trusted Publisher configuration;
- current X agreement, policy, pricing, scopes, rate limits, and endpoint review;
- credentialed live smoke test;
- the untracked `AGENTS.md` public-content decision and any separately approved governance issue;
- production Vercel domain and promotion;
- PR merges, signed tag, PyPI publication, GitHub Release, advisory publication, and cleanup.

Keep each incomplete launch-critical item yellow. Do not change it to green by preparing
instructions alone.

- [ ] **Step 4: Verify and commit only the report**

```bash
git diff --check
rg -n 'access_token|refresh_token|client_secret|private key|security/wikix-1.0-private' \
  docs/release-readiness.md
git add -- docs/release-readiness.md
git commit -m "docs: record Wikix 1.0 release readiness"
```

Expected: the secret-pattern search returns no match and the commit contains only the report.

- [ ] **Step 5: Push and open the draft readiness PR**

```bash
git push -u origin "docs/${WIKIX_REPORT_ISSUE_NUMBER}-release-readiness"
gh pr create --repo wikix-project/wikix --draft --base main \
  --head "docs/${WIKIX_REPORT_ISSUE_NUMBER}-release-readiness" \
  --title "Record Wikix 1.0 release readiness" \
  --body "Records verified candidate evidence, remaining manual/external gates, and the redacted
cleanup manifest without performing launch actions.

Fixes #${WIKIX_REPORT_ISSUE_NUMBER}"
gh pr checks --repo wikix-project/wikix --watch
```

- [ ] **Step 6: Deliver the private handoff and stop**

Provide the user with:

- public issue and PR links;
- the private advisory status;
- exact private and RC commit IDs through a private channel only;
- automated verification commands and results;
- artifact hashes;
- preview verification result;
- the credentialed smoke checklist;
- exact external-setting changes awaiting approval;
- exact merge/tag/publish/deploy sequence and rollback points;
- the cleanup candidates and evidence, with no deletion performed.

Stop. Do not merge, publish the advisory, apply settings, tag, publish to PyPI, create a GitHub
Release, promote Vercel, or delete any branch/worktree until the user authorizes each next phase.
