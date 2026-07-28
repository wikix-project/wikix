# Security Policy

## Supported versions

Until Wikix reaches a stable release, security fixes are made on the latest released version and
the default branch.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do not open a public issue
for token exposure, OAuth flaws, unsafe file replacement, path traversal, or another vulnerability
that could put users or their collections at risk.

Include affected versions, impact, reproduction steps, and any suggested mitigation. Do not include
real credentials or private X content. Maintainers will acknowledge a report as soon as practical,
coordinate a fix and disclosure, and credit reporters who want attribution.

## Security model

- Wikix stores OAuth tokens only through the operating system credential store unless the user
  injects tokens through process environment variables.
- Collection configuration and state must not contain access or refresh tokens.
- Exported Markdown and JSONL contain private bookmark content and should be protected like any
  other personal archive.
- X developer app credentials, API spending controls, collection backups, and filesystem access
  remain the user's responsibility.
