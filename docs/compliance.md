# Compliance and scope

Wikix is designed to support compliant personal bookmark export. It is not legal advice, a
compliance warranty, or legal certification. X's developer agreement, policy, product terms,
pricing, and technical requirements can change; users and release maintainers must review current
documents.

Relevant starting points:

- [X Developer Agreement](https://docs.x.com/developer-terms/agreement)
- [X Developer Policy](https://docs.x.com/developer-terms/policy)
- [X API pricing](https://docs.x.com/x-api/getting-started/pricing)
- [X rate limits](https://docs.x.com/x-api/fundamentals/rate-limits)
- [X bookmark API](https://docs.x.com/x-api/users/get-bookmarks)

## Supported v1 uses

Wikix supports private, personal:

- bookmark retrieval and local archival;
- search and retrieval;
- summarization and synthesis;
- classification and organization;
- source citation.

Users must ensure downstream tools, agents, storage providers, and workflows also comply with
applicable terms and law.

## Explicitly excluded from v1

- browser scraping or unofficial API access;
- redistribution as a public dataset;
- user profiling or surveillance;
- model training;
- media downloads;
- extraction of linked external pages;
- thread or conversation crawling;
- background scheduling;
- a hosted OAuth service;
- MCP, HTTP, or other API servers.

Wikix links media but does not download it. Rich mode requests only official expansions directly
associated with bookmarked posts.

## Changes, deletions, and retained annotations

Every sync enumerates the complete collection so local exports reflect additions, edits, and
removals. Removed post bodies are deleted. When a removed note has a personal annotation, the
review file retains only the post ID, canonical source URL, removal timestamp, and user-authored
annotation.

Before any public release, a human maintainer must review X's then-current agreements, policy,
pricing, scopes, endpoint behavior, and offline-content requirements. See the
[release checklist](release-checklist.md).
