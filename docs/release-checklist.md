# Release checklist

No public release may proceed until every applicable item is complete. The GitHub `pypi`
environment must have required reviewers so the publish job cannot begin without explicit human
approval.

## One-time repository setup

- [ ] Confirm that the `wikix` PyPI project name is available and claim it.
- [ ] Create the PyPI project and configure a GitHub Trusted Publisher for the `release.yml`
      workflow and `pypi` environment.
- [ ] Create a protected GitHub environment named `pypi` with a required human reviewer.
- [ ] Enable GitHub private vulnerability reporting.
- [ ] Confirm repository URLs and maintainer metadata.

## Every release

- [ ] Set and verify the package version.
- [ ] Review the current X Developer Agreement, Developer Policy, API pricing, rate limits,
      bookmark endpoints, OAuth scopes, offline-content requirements, and redistribution/AI-use
      restrictions.
- [ ] Update the pricing-policy review date and assumptions in code and documentation.
- [ ] Confirm Wikix's supported/excluded-use language remains accurate.
- [ ] Run Ruff, strict mypy, pytest, and at least 90% core coverage.
- [ ] Run the 25,000-record bounded-memory test.
- [ ] Run the manual end-to-end smoke test with the maintainer's own app:
  - login;
  - lean sync and unchanged repeat sync;
  - rich sync;
  - folder sync;
  - removal and review-note restoration;
  - interrupted scan and resume;
  - logout;
  - clean wheel installation and uninstall.
- [ ] Build the sdist and wheel in a clean environment and inspect metadata/content.
- [ ] Create a signed `v*` tag only after review.
- [ ] Approve the protected `pypi` environment when the tag workflow reaches the publish gate.
- [ ] Verify the PyPI files, Trusted Publishing attestations, GitHub release, SHA-256 checksums, and
      SPDX SBOM.

The release workflow builds and verifies artifacts in a low-privilege job. A separate,
approval-gated job downloads those exact artifacts and publishes them with OIDC Trusted Publishing.
