# Contributing to Wikix

Thank you for helping make personal X bookmark exports safer and more dependable.

## Development setup

Wikix requires Python 3.12 or newer and uses uv:

```shell
git clone https://github.com/atharvafulay/wikix.git
cd wikix
uv sync --extra dev
```

Run the complete local quality gate before proposing a change:

```shell
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=wikix
```

Coverage for core modules must remain at least 90%.

## Change guidelines

- Start with a failing test for behavior changes and bug fixes.
- Keep modules bounded around configuration, authentication, X API access, staging,
  normalization, rendering, reconciliation, and CLI orchestration.
- Preserve local-first operation and the complete-snapshot commit boundary.
- Use only official X APIs. Do not add scraping or shared credentials.
- Never commit real X posts, tokens, client IDs, or personal account identifiers. Fixtures must be
  synthetic.
- Treat Markdown and JSONL formats as public contracts. Document intentional schema changes.
- Keep tokens in the operating system credential store or injected environment variables only.

## Pull requests

Explain the user-visible change, tests run, security/privacy impact, and schema or policy impact.
Small, focused pull requests are easiest to review. By contributing, you agree that your
contribution is licensed under Apache-2.0.
