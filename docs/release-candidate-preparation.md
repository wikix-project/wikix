# Wikix 1.0 Release-Candidate Preparation Design

**Date:** 2026-08-20
**Issue:** [#3](https://github.com/wikix-project/wikix/issues/3)
**Status:** Approved

## Summary

Prepare the existing Wikix 1.0 CLI for launch through isolated, issue-first work streams and an
unpushed local release-candidate integration branch. Preserve all current user work, keep
confidential security details private, and stop before merges, tags, package publication,
production deployment, repository-setting changes, or branch deletion.

This document coordinates the release train. It does not authorize a single broad implementation
issue. Each public implementation change must have its own coherent issue, branch, tests, and pull
request. Confidential remediation uses the repository's private security process instead.

## Context

The public default branch already contains the complete Wikix 1.0 product surface and beginner
onboarding. Additional audited hardening and website work exists across local branches, commits,
and uncommitted worktrees. Some of that work is useful, some is stale, and some is confidential.
Merging any existing branch wholesale would risk carrying obsolete documentation, unrelated
deletions, or hidden dependencies into the release candidate.

The design branch started from `origin/main` at `9a08ef4`. Before any follow-up issue begins, its
branch must be created from the then-current remote default branch rather than assuming this commit
is still current.

The clean baseline passed Ruff lint and formatting, strict mypy, all 150 tests, the 25,000-record
bounded-memory test, and 100% measured core coverage. This is baseline evidence, not proof that
future integration or production behavior is correct.

## Product scope

The 1.0 feature set is frozen at the existing CLI capabilities:

- OAuth authentication and logout;
- lean, rich, and folder bookmark synchronization through the official X API;
- interrupted-scan staging and resume;
- deterministic Markdown and JSONL output;
- reconciliation, review-note preservation, and restoration;
- local status and operational reporting.

Release preparation may change security, reliability, documentation, the website, packaging,
workflows, and repository readiness. It must not add new product features.

## Goals

- Migrate only accepted, traceable changes from the scattered local work.
- Keep confidential remediation out of public issues, branches, logs, and specifications.
- Produce small public pull requests that can be reviewed independently.
- Preserve the merged macOS, Windows, and Linux onboarding while adding the approved polished site
  and separate Quick Setup and Step-by-Step pages.
- Create a combined local candidate that proves the streams work together before any merge.
- Produce an evidence-backed launch handoff with explicit remaining human and external gates.
- Preserve all existing branches and worktrees until cleanup is separately authorized.

## Non-goals

- New import sources, scraping, hosted credentials, scheduling, servers, or other new features.
- Publishing confidential vulnerability details.
- Treating preview hosting, synthetic tests, or local checks as proof of production behavior.
- Merging pull requests, publishing a security advisory, tagging, publishing to PyPI, creating a
  GitHub Release, or deploying the production website.
- Applying repository, PyPI, or hosting settings without separate approval.
- Deleting or rewriting branches, worktrees, or user-owned uncommitted changes.

## Chosen approach

Use parallel, isolated release streams plus an unpushed local integration candidate. This preserves
reviewability while allowing the complete candidate to be tested before merges. A sequential merge
train cannot produce the complete candidate under the stop-before-merge boundary. One large launch
pull request would be harder to review and would violate the repository's coherent-change rule.

## Work-stream architecture

### 1. Confidential security remediation

- Use a draft private security advisory and confidential remediation branch.
- Keep reproduction, impact, affected paths, and patch details in the private process only.
- Run focused and broad checks without copying sensitive diagnostics into public artifacts.
- Do not create a public issue for this stream.

### 2. Public reliability and data integrity

- Decompose accepted hardening into coherent issue-sized patches.
- Separate independent concerns rather than creating a general cleanup issue.
- Give each behavioral fix a regression test and the relevant broader checks.
- Ensure public branches do not depend on unreleased confidential code.

### 3. Website and onboarding

- Retain the merged platform-specific walkthroughs and their tests.
- Port the polished website additively rather than merging a stale site branch.
- Add separate Quick Setup and Step-by-Step routes without duplicating or contradicting the full
  platform guides.
- Keep installation and availability claims aligned with actual source, PyPI, and hosting state.

### 4. Release engineering and repository readiness

- Harden release workflow references, permissions, artifact flow, approval gates, checksums, SBOM,
  and attestations.
- Reconcile package version sources, metadata, repository URLs, and dependencies.
- Track only intentionally public repository guidance through its own coherent governance change.
- Prepare exact setting changes for package publishing, vulnerability reporting, security scanning,
  and branch protection, but leave them unapplied until separately approved.

### 5. Local release-candidate integration

- Create an unpushed local branch from a clean, freshly fetched `origin/main`.
- Apply the private remediation and public stream heads in the documented order.
- Use the branch only for integration, packaging, website, and smoke-test evidence.
- Treat stream branches as the sources of truth; the RC must contain no unique fixes.

## Change ledger and migration rules

Create a ledger before implementation. Each accepted public change records:

| Field | Purpose |
| --- | --- |
| Source reference | Original branch, commit, or uncommitted worktree |
| Fingerprint | Commit ID or diff hash proving which source was assessed |
| Destination | Owning issue and release stream |
| Files | Exact paths expected to migrate |
| Method | Clean cherry-pick or surgical reapplication |
| Verification | Focused tests and required shared checks |
| Status | Pending, migrated, superseded, excluded, or blocked |
| Evidence | Destination commit and comparison result |

Confidential source mapping stays in the private advisory. The public ledger contains only a
redacted confidential-stream status.

Migration follows these rules:

1. Fetch the remote and confirm the current default branch before each issue.
2. Search current issues, pull requests, and branches for duplicates or competing work.
3. Create one coherent issue with evidence, acceptance criteria, verification, and non-goals.
4. Branch from the current `origin/main` using the repository's issue-linked naming convention.
5. Cherry-pick only when a commit is isolated and still correct against current main.
6. Reapply entangled work surgically with its tests; never merge a stale source branch wholesale.
7. Exclude unrelated formatting, stale deletions, temporary artifacts, and superseded content.
8. Record the destination commit and verify that no accepted source hunk was stranded.

Existing source branches and worktrees remain unchanged throughout migration.

## Issue and branch ownership

Public work uses names such as `fix/123-description`, `docs/124-description`, and
`build/125-description`. Each issue owns its behavior, tests, documentation, and corrections found
during integration. Pull requests link their issue with the appropriate closing or reference syntax.

If the RC exposes a conflict or regression, fix and retest the owning stream branch, then rebuild
the RC. Never fix only the integration branch.

## Sequence

1. Record the refreshed repository and worktree inventory.
2. Build the public change ledger and the confidential equivalent.
3. Prepare confidential remediation.
4. Prepare independent public reliability and data-integrity issues and pull requests.
5. Prepare the website and onboarding issue and pull request.
6. Prepare release-engineering and repository-readiness issues and pull requests.
7. Assemble the unpushed local RC in a documented commit order.
8. Run the complete verification contract and produce the readiness report.
9. Stop for merge, external-setting, smoke-test, tag, publication, deployment, and cleanup approvals.

Only one confirmed public issue is implemented at a time. Issue, branch, pull request, review, and
CI state must be reconciled before starting dependent work.

## Verification contract

### Per stream

- Add focused regression tests for behavior changes before implementing the fix.
- Run Ruff lint and formatting checks for changed Python work.
- Run strict mypy for changed typed code.
- Run focused tests plus the relevant broader suite.
- Run documentation and route tests for website or onboarding changes.
- Inspect workflow syntax, permissions, immutable references, and artifact boundaries for release
  changes.

### Combined RC

The combined candidate must pass:

- `ruff check` and `ruff format --check`;
- strict mypy;
- the complete test suite with at least 90% core coverage;
- the 25,000-record bounded-memory test;
- clean sdist and wheel builds with metadata and contents inspected;
- fresh-environment install, CLI execution, version verification, uninstall, and reinstall;
- website route, navigation, link, responsive-layout, and content-consistency checks;
- release-workflow review covering permissions, immutable action references, artifact continuity,
  approval gates, checksums, SBOM, and attestations.

### Live and external verification

The maintainer's own approved X app must be used for the final live smoke test:

- login and logout;
- lean sync and unchanged repeat sync;
- rich sync;
- folder sync;
- removal and annotated-note restoration;
- interruption and resume;
- clean wheel installation and uninstall.

Immediately before release, recheck the current X agreement, policy, pricing, endpoint behavior,
OAuth scopes, rate limits, offline-content requirements, and redistribution or AI-use restrictions.
Preview hosting verifies a preview build only. Synthetic tests do not replace the live smoke test.

## Readiness and failure handling

Every gate receives one status:

- **Green:** verified with current evidence.
- **Yellow:** requires a credentialed smoke test, external setting, merge, or publication approval.
- **Red:** failed, contradictory, or missing required internal evidence.

Any red gate blocks the RC. Launch-critical yellow gates block publication but may remain in the
handoff for an otherwise complete candidate. Environmental failures must be reproduced and
distinguished from product failures; a targeted rerun does not silently convert an incomplete full
run into a fully verified suite.

## Authorized preparation and stop boundary

After follow-up implementation plans are separately approved, preparation may create:

- follow-up public issues, branches, commits, pushes, and draft or ready pull requests within
  approved scope;
- a draft private advisory and confidential remediation work;
- local worktrees and an unpushed combined RC;
- local package artifacts and preview hosting needed for verification;
- the launch-readiness report, final runbook, and cleanup manifest.

Preparation stops before:

- merging or closing public work;
- publishing the advisory;
- applying repository, PyPI, or hosting settings;
- deleting branches or worktrees;
- creating or pushing a release tag;
- publishing to PyPI or creating a GitHub Release;
- promoting the website to production or assigning a production domain.

Each stopped action requires separate user approval and a fresh live-state check.

## Handoff package

The release-candidate handoff contains:

- public issue and pull-request links with tested dependency order;
- private advisory status without confidential details;
- exact component and RC commit IDs;
- automated, manual, and external verification evidence;
- the green/yellow/red readiness matrix;
- the remaining maintainer smoke-test checklist;
- final launch instructions with rollback points;
- a cleanup manifest for redundant branches and worktrees.

## Cleanup safety

Cleanup is a separate destructive phase. A branch or worktree is eligible only when:

- its accepted work is mapped to a destination commit or explicitly excluded;
- comparison proves it contains no unique committed change that should survive;
- it has no unique uncommitted or untracked user work;
- related issue, pull-request, and review state has been reconciled;
- the user explicitly approves that exact deletion.

After authorized merges, rebuild and reverify the candidate from the resulting main branch before
requesting approval for any tag or publication. Do not reuse the pre-merge RC as release evidence.

## Acceptance criteria

This design is successfully implemented when:

- every accepted source change is traceably migrated or explicitly excluded;
- confidential work remains private;
- public pull requests are coherent, independently reviewable, and green;
- the combined local RC satisfies all internal verification gates;
- all remaining live, external, merge, publication, deployment, and cleanup gates are explicit;
- no irreversible or separately approval-gated action has occurred.
