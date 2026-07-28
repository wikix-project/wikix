# Wikix schema contracts

Both public output formats use schema version `1`. Backward-incompatible changes require a new
schema version.

## Markdown

Each current bookmark is stored at `bookmarks/<post-id>.md`. YAML frontmatter contains stable
identity and source fields:

- `schema_version`
- `profile` (`lean` or `rich`)
- `x_account_id`
- `x_post_id`
- `x_author_id`
- `source_url`
- `created_at`
- `synced_at`
- `language`
- `conversation_id`
- `in_reply_to_user_id`
- `references`
- `media_keys`

Rich records may additionally include `x_author`, `x_media`, and `x_referenced_posts`.
Folder-enabled records may include `x_folders`, whose entries contain `id` and `name`.

Post text is preserved exactly in JSONL. Markdown notes put it in a dynamically sized fenced block
so Markdown metacharacters do not change its meaning. Expanded entity links and rich resources are
rendered separately and attributed as generated metadata.

Wikix owns all note content except text strictly between:

```markdown
<!-- wikix:notes:start -->
...
<!-- wikix:notes:end -->
```

The state file stores a hash of the generated region and record. Wikix does not overwrite malformed
markers or locally edited generated content.

## JSONL

`bookmarks.jsonl` contains one UTF-8 JSON object per line. It represents only the current remote
collection and is atomically replaced after a complete successful scan. Records are sorted by post
creation time and then post ID, newest first.

`BookmarkRecordV1` has these stable top-level keys:

| Key | Type | Description |
| --- | --- | --- |
| `schema_version` | integer | Always `1` |
| `profile` | string | `lean` or `rich` |
| `account_id` | string | Authenticated X user ID |
| `post_id` | string | X post ID |
| `author_id` | string or null | Author's X user ID |
| `text` | string | Exact API post text |
| `source_url` | string | Canonical X post URL |
| `created_at` | RFC 3339 string or null | Post creation time |
| `synced_at` | RFC 3339 string | Snapshot time |
| `language` | string or null | X language value |
| `conversation_id` | string or null | X conversation ID |
| `in_reply_to_user_id` | string or null | Replied-to X user ID |
| `entities` | object | X entity metadata |
| `references` | array | Reference type and post ID entries |
| `media` | array | Media keys and optional rich metadata |
| `author` | object or null | Optional rich author metadata |
| `folders` | array | Optional X folder ID/name entries |

Every schema-v1 key is present, with JSON `null` for unavailable nullable values. Object keys are
serialized deterministically. Removed posts and their bodies are absent.

## Internal files

`.wikix/config.toml` is user-facing collection configuration. `.wikix/state.json` and staging or
journal files are recovery internals, not stable public APIs. They must never contain OAuth tokens.
