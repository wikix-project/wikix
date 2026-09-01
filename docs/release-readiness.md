# Wikix 1.0 Release Readiness

Observed on September 1, 2026. This report records the prepared candidate without publishing it.
Green means verified, Yellow means incomplete or awaiting a maintainer-controlled gate, and Red means
a known failure. The overall release status is **Yellow: publication blocked**.

## Candidate scope

| Gate | Status | Evidence |
| --- | --- | --- |
| Coherent 1.0 candidate | Green | A disposable local candidate was assembled from current `main`, the confidential remediation, and the seven public streams below. It remains unpushed. |
| Scope review | Green | Independent whole-candidate review found no Critical, Important, or Minor findings. |
| Public integration | Yellow | All source PRs remain open drafts. No merge, tag, package publication, release, advisory publication, or production deployment has occurred. |
| Final installation guidance | Yellow | Launch-facing documentation still accurately says Wikix is not on PyPI and installs from GitHub source. A separate issue and PR must choose and document the final installation path before PyPI publication makes that text stale. |

The candidate is Apache-2.0, Python 3.12+, local-first, read-only with respect to X, and scoped to
one user's own bookmark export. It does not add hosted credentials, telemetry, scraping, background
scheduling, model training, or public dataset redistribution.

## Public pull requests and tested order

The local candidate used this dependency order. The confidential stream is intentionally named only
by role; its identifiers and vulnerability details are not public-release evidence.

| Order | Stream | Status |
| ---: | --- | --- |
| 1 | Confidential remediation | Green: verified and independently reviewed in the private security workflow; coordinated public integration is still Yellow. |
| 2 | [#6 Validate live and recovered API pages consistently](https://github.com/wikix-project/wikix/pull/6) | Green: draft PR checks passed. |
| 3 | [#8 Keep remote metadata inert in exported Markdown](https://github.com/wikix-project/wikix/pull/8) | Green: draft PR checks passed. |
| 4 | [#10 Reject malformed local metadata with clean CLI errors](https://github.com/wikix-project/wikix/pull/10) | Green: draft PR checks passed. |
| 5 | [#12 Bound persistent X rate-limit waiting](https://github.com/wikix-project/wikix/pull/12) | Green: draft PR checks passed. |
| 6 | [#14 Add separate Quick Setup and Step-by-Step website pages](https://github.com/wikix-project/wikix/pull/14) | Green: draft PR checks passed, including a successful rerun of one isolated unchanged OAuth test timeout. |
| 7 | [#16 Prepare coherent Wikix 1.0 package metadata](https://github.com/wikix-project/wikix/pull/16) | Green: draft PR checks passed. |
| 8 | [#18 Pin release actions and verify package construction in CI](https://github.com/wikix-project/wikix/pull/18) | Green: all fourteen draft PR checks, including package smoke, passed. |

The planning-only [draft PR #4](https://github.com/wikix-project/wikix/pull/4) is not part of the
candidate's product source.

## Automated verification

| Gate | Status | Evidence |
| --- | --- | --- |
| Ruff lint | Green | `uv run ruff check .` passed. |
| Formatting | Green | `uv run ruff format --check .` passed. |
| Static typing | Green | `uv run mypy src` passed in strict mode. |
| Full tests and coverage | Green | 243 tests passed in one complete run with 99.13% core coverage. |
| Scale test | Green | The separate 25,000-record bounded-memory test passed. |
| Patch hygiene | Green | `git diff --check` and conflict-marker scans passed. |
| Source PR CI | Green | Every selected public source head had a complete successful GitHub Actions matrix when observed. |

## Package artifact inspection

| Gate | Status | Evidence |
| --- | --- | --- |
| Wheel | Green | `wikix-1.0.0-py3-none-any.whl`; SHA-256 `1b1b00a499106dc47d5aa4c056083bffd7160904afaf42b98bee1ad99f2b255f`. |
| Source distribution | Green | `wikix-1.0.0.tar.gz`; SHA-256 `7bcddff6ce6833f175b9fd57af639aecf54fa8663824878745cb6ca8de646671`. |
| Metadata | Green | Version 1.0.0, Production/Stable classifier, Python 3.12+, Apache-2.0 metadata and license file, expected direct dependencies, and `wikix` console entry point were verified. |
| Clean install lifecycle | Green | A clean temporary environment installed the wheel, reported `Wikix 1.0.0`, and uninstalled it successfully. |
| Published artifact verification | Yellow | No tag, PyPI files, Trusted Publishing attestations, GitHub Release, checksums bundle, or SPDX SBOM has been published. |

## Website verification

| Gate | Status | Evidence |
| --- | --- | --- |
| Local pages | Green | Landing, guide, and quick-setup pages passed desktop and 390x844 checks for content, navigation, wrapping, and zero horizontal overflow. |
| Static-only contract | Green | The local pages load without JavaScript, and expected assets and internal routes resolve. |
| Protected preview | Green | A non-production protected Vercel preview returned the expected pages, assets, headers, and exclusions; repository source, tests, local configuration, and private documentation were not served. |
| Production hosting | Yellow | Vercel currently shows preview deployments only. No candidate has been promoted to Production and no Wikix custom production domain was observed. |

## Confidential stream status

| Gate | Status | Evidence |
| --- | --- | --- |
| Private remediation | Green | The fix was reproduced, implemented test-first, verified, independently reviewed, and pushed only through the private security workflow. |
| Coordinated release | Yellow | The advisory remains a draft. The fix has not been merged publicly, released to users, or disclosed. Keep the advisory private until a fixed package is available and disclosure timing is approved. |

## Manual X smoke test

**Yellow: publication blocking.** Automated tests use synthetic X responses. A maintainer must run
the following with the maintainer's own approved app, account, credits, and private test collection.
No credential or private bookmark data belongs in issues, pull requests, logs, or this report.

- sign in through OAuth 2.0 PKCE;
- run a lean complete sync, then an unchanged repeat sync;
- run rich and folder-enabled syncs;
- verify removal and annotated-note restoration;
- interrupt a scan and verify compatible resume;
- sign out and confirm stored credentials are removed;
- repeat the install/version/uninstall check with the release wheel.

Record only pass/fail, sanitized counts, platform, app configuration category, observed rate-limit
headers, and total cost. A failed or unaffordable smoke test is Red and stops publication.

## Repository, PyPI, and hosting gates

| Gate | Status | Observed state and required action |
| --- | --- | --- |
| Private vulnerability reporting | Yellow | Disabled. A repository administrator must enable it before launch. |
| Secret scanning and push protection | Yellow | Both disabled. A repository administrator must enable the available secret protections and verify their effective state. |
| Dependabot alerts and security updates | Yellow | Vulnerability alerts and automated security fixes are disabled. A repository administrator must enable and verify the intended dependency-security controls. |
| `main` branch protection | Yellow | Administrator enforcement and force-push/deletion blocking are active, but no required status checks are configured, conversation resolution is disabled, and zero approving reviews are required. Configure the approved release policy and verify it before merges. |
| GitHub `pypi` environment | Yellow | No repository environments exist. Create `pypi`, require a human reviewer, and prevent the publish job from proceeding without approval. |
| PyPI project and ownership | Yellow | PyPI's public project API returned Not Found for `wikix`. A maintainer must claim or create the project and verify owner access. |
| PyPI Trusted Publisher | Yellow | Cannot be configured or verified until the project exists. Configure GitHub Actions trust for owner `wikix-project`, repository `wikix`, workflow `release.yml`, and environment `pypi`, then verify it in the maintainer's PyPI account. |
| Current X technical documentation | Yellow | A source-to-document comparison on September 1, 2026 found the required scopes (`bookmark.read`, `tweet.read`, `users.read`, `offline.access`) and read endpoints aligned with current public X documentation. Current docs list 180 requests per 15 minutes for bookmark lookup, 50 for each folder lookup, and 75 for `/2/users/me`; owned bookmark reads remain listed at $0.001 per returned resource when the authenticated user owns the app. The Developer Console remains authoritative for account-specific price, credits, access, and limits. |
| X agreement and policy acceptance | Yellow | The current [Developer Agreement](https://docs.x.com/developer-terms/agreement), [Developer Policy](https://docs.x.com/developer-terms/policy), [pricing](https://docs.x.com/x-api/getting-started/pricing), [OAuth scopes](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code), [bookmark endpoints](https://docs.x.com/x-api/posts/bookmarks/introduction), and [rate limits](https://docs.x.com/x-api/fundamentals/rate-limits) were compared with the candidate, but the release checklist requires a human maintainer review. The bundled July 2026 pricing/policy review dates must also be updated through a separate issue and PR after that review. |
| Local repository guidance | Yellow, non-publication-blocking | An untracked local operator-guidance file is excluded from the candidate. Decide separately whether any of it belongs in a public governance issue and PR; do not add it incidentally to a release commit. |
| Vercel production domain and promotion | Yellow | Preview verification passed, but production promotion, domain selection, and public smoke verification await explicit approval. |
| Launch operations | Yellow | PR readiness and merges, signed tag, PyPI publication, GitHub Release, advisory publication, production deployment, and cleanup all require explicit maintainer approval. |

## Launch sequence and rollback points

1. Close every repository, PyPI, X-review, installation-guidance, and credentialed-smoke Yellow gate.
2. Update each draft source PR against the then-current `main`, rerun its complete CI, obtain the
   configured reviews, and merge in the tested order above during one coordinated release window.
3. Verify `main` reproduces the candidate gates and artifacts. If it does not, stop and revert the
   responsible merge commit; do not force-push protected history.
4. Create and verify the signed `v1.0.0` tag only after `main` is green. The tag starts the release
   workflow; the protected `pypi` reviewer must compare the workflow-built artifact names and hashes
   before approving publication.
5. Verify PyPI files, provenance, attestations, checksums, SBOM, clean installation, and the GitHub
   Release. PyPI versions are immutable: if 1.0.0 is defective, yank it and publish a corrected patch
   version rather than replacing files.
6. Deploy the verified static site to Vercel Production, attach the approved domain, and smoke all
   pages and headers. Roll back to the prior production deployment if hosting verification fails.
7. Publish the advisory only after fixed artifacts are available to users and disclosure timing is
   approved. Advisory publication exposes previously confidential information and is not treated as
   a reversible test step.

## Redacted cleanup manifest

All cleanup remains deferred and requires separate approval.

- two local-only release-candidate worktrees and branches;
- issue-specific public worktrees and branches after their PRs are merged and retention is approved;
- private remediation worktree/branch material after coordinated disclosure and retention review;
- protected Vercel preview deployments after production verification;
- temporary build, installation, archive, and response-verification directories;
- the untracked local operator-guidance file, subject to its separate public-content decision.

No branch, worktree, preview, artifact, or local file was deleted while preparing this report.

## Stop boundary

This report does not authorize or perform a PR readiness change, merge, repository-setting change,
tag, PyPI publication, GitHub Release, advisory publication, Vercel production promotion/domain
change, or cleanup. Each remains stopped at the applicable maintainer approval gate.
