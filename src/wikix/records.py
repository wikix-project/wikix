"""Normalized public records and file renderers."""

import heapq
import json
import os
import re
import tempfile
import unicodedata
from collections.abc import Iterable, Iterator
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field


class AuthorRecord(BaseModel):
    id: str
    name: str | None = None
    username: str | None = None


class MediaRecord(BaseModel):
    media_key: str
    type: str | None = None
    url: str | None = None
    preview_image_url: str | None = None
    alt_text: str | None = None
    duration_ms: int | None = None
    height: int | None = None
    width: int | None = None


class ReferencedPostRecord(BaseModel):
    id: str
    text: str
    author_id: str | None = None
    created_at: str | None = None


class ReferenceRecord(BaseModel):
    type: str
    id: str
    post: ReferencedPostRecord | None = None


class FolderRecord(BaseModel):
    id: str
    name: str


class BookmarkRecordV1(BaseModel):
    schema_version: Literal[1] = 1
    profile: Literal["lean", "rich"]
    account_id: str
    post_id: str = Field(pattern=r"^\d+$")
    source_url: str
    text: str
    created_at: str | None = None
    synced_at: str
    author_id: str | None = None
    language: str | None = None
    conversation_id: str | None = None
    in_reply_to_user_id: str | None = None
    entities: dict[str, Any] = Field(default_factory=dict)
    references: list[ReferenceRecord] = Field(default_factory=list)
    media: list[MediaRecord] = Field(default_factory=list)
    author: AuthorRecord | None = None
    folders: list[FolderRecord] = Field(default_factory=list)


def normalize_pages(
    pages: Iterable[dict[str, Any]],
    *,
    account_id: str,
    profile: Literal["lean", "rich"],
    synced_at: datetime,
    folder_memberships: dict[str, list[dict[str, str]]] | None = None,
) -> Iterator[BookmarkRecordV1]:
    synced_value = synced_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    memberships = folder_memberships or {}
    for page in pages:
        includes = page.get("includes") or {}
        users = {str(item["id"]): item for item in includes.get("users", [])}
        media = {str(item["media_key"]): item for item in includes.get("media", [])}
        tweets = {str(item["id"]): item for item in includes.get("tweets", [])}
        for post in page.get("data", []):
            note_post = post.get("note_tweet")
            note_post = note_post if isinstance(note_post, dict) else {}
            post_id = str(post["id"])
            author_id = _optional_string(post.get("author_id"))
            attachments = post.get("attachments") or {}
            media_keys = [str(value) for value in attachments.get("media_keys", [])]
            media_records = [
                MediaRecord.model_validate(media[key])
                if profile == "rich" and key in media
                else MediaRecord(media_key=key)
                for key in media_keys
            ]
            references = []
            for reference in post.get("referenced_tweets", []):
                reference_id = str(reference["id"])
                expanded = tweets.get(reference_id) if profile == "rich" else None
                expanded_record = (
                    ReferencedPostRecord.model_validate(
                        {
                            **expanded,
                            "text": _exact_post_text(expanded),
                        }
                    )
                    if expanded is not None
                    else None
                )
                references.append(
                    ReferenceRecord(
                        type=str(reference["type"]),
                        id=reference_id,
                        post=expanded_record,
                    )
                )
            author_data = users.get(author_id or "") if profile == "rich" else None
            folder_records = [
                FolderRecord.model_validate(folder)
                for folder in sorted(
                    memberships.get(post_id, []),
                    key=lambda item: (item["name"], item["id"]),
                )
            ]
            yield BookmarkRecordV1(
                profile=profile,
                account_id=account_id,
                post_id=post_id,
                source_url=f"https://x.com/i/web/status/{post_id}",
                text=_exact_post_text(post),
                created_at=_optional_string(post.get("created_at")),
                synced_at=synced_value,
                author_id=author_id,
                language=_optional_string(post.get("lang")),
                conversation_id=_optional_string(post.get("conversation_id")),
                in_reply_to_user_id=_optional_string(post.get("in_reply_to_user_id")),
                entities=note_post.get("entities") or post.get("entities") or {},
                references=references,
                media=media_records,
                author=AuthorRecord.model_validate(author_data) if author_data else None,
                folders=folder_records,
            )


def render_markdown(record: BookmarkRecordV1, *, personal_notes: str = "") -> str:
    frontmatter: dict[str, Any] = {
        "schema_version": record.schema_version,
        "profile": record.profile,
        "x_account_id": record.account_id,
        "x_post_id": record.post_id,
        "x_author_id": record.author_id,
        "source_url": record.source_url,
        "created_at": record.created_at,
        "synced_at": record.synced_at,
        "language": record.language,
        "conversation_id": record.conversation_id,
        "in_reply_to_user_id": record.in_reply_to_user_id,
        "references": [
            {"type": reference.type, "id": reference.id} for reference in record.references
        ],
        "media_keys": [item.media_key for item in record.media],
    }
    if record.author is not None:
        frontmatter["x_author"] = record.author.model_dump(exclude_none=True)
    if record.profile == "rich" and record.media:
        frontmatter["x_media"] = [item.model_dump(exclude_none=True) for item in record.media]
    expanded_reference_values = [
        reference.model_dump(exclude_none=True)
        for reference in record.references
        if reference.post is not None
    ]
    if expanded_reference_values:
        frontmatter["x_referenced_posts"] = expanded_reference_values
    if record.folders:
        frontmatter["x_folders"] = [
            {"id": folder.id, "name": folder.name} for folder in record.folders
        ]
    yaml_text = yaml.safe_dump(
        frontmatter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).rstrip()

    fence = _safe_fence(record.text)
    sections = [
        "---",
        yaml_text,
        "---",
        "",
        "## Post",
        "",
        f"{fence}text",
        record.text,
        fence,
        "",
        "## Source",
        "",
        _render_link("View on X", record.source_url),
    ]
    urls = record.entities.get("urls", [])
    if urls:
        sections.extend(["", "## Links", ""])
        for item in urls:
            url = str(item.get("expanded_url") or item.get("url") or "")
            label = str(item.get("display_url") or url)
            sections.append(f"- {_render_link(label, url)}")
    if record.media and any(item.url or item.alt_text or item.type for item in record.media):
        sections.extend(["", "## Media", ""])
        for item in record.media:
            label = item.alt_text or item.type or item.media_key
            sections.append(
                f"- {_render_link(label, item.url)}"
                if item.url
                else f"- {_escape_markdown_label(label)}"
            )
    expanded_references = [reference for reference in record.references if reference.post]
    if expanded_references:
        sections.extend(["", "## Direct references", ""])
        for reference in expanded_references:
            assert reference.post is not None
            fence = _safe_fence(reference.post.text)
            sections.extend(
                [
                    f"### {_escape_markdown_label(reference.type.title())} post {reference.id}",
                    "",
                    f"{fence}text",
                    reference.post.text,
                    fence,
                    "",
                    f"[View referenced post](https://x.com/i/web/status/{reference.id})",
                    "",
                ]
            )
        while sections[-1] == "":
            sections.pop()
    notes = personal_notes
    if notes and not notes.endswith("\n"):
        notes += "\n"
    sections.extend(
        [
            "",
            "## Personal notes",
            "<!-- wikix:notes:start -->",
            notes.rstrip("\n"),
            "<!-- wikix:notes:end -->",
            "",
        ]
    )
    return "\n".join(sections)


def write_jsonl(
    path: Path,
    records: Iterable[BookmarkRecordV1],
    *,
    chunk_size: int = 1_000,
) -> None:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with tempfile.TemporaryDirectory(prefix=".wikix-sort-", dir=path.parent) as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        chunk_paths: list[Path] = []
        chunk: list[BookmarkRecordV1] = []
        for record in records:
            chunk.append(record)
            if len(chunk) >= chunk_size:
                chunk_paths.append(_write_sorted_chunk(temp_dir, len(chunk_paths), chunk))
                chunk = []
        if chunk:
            chunk_paths.append(_write_sorted_chunk(temp_dir, len(chunk_paths), chunk))

        with temporary.open("w", encoding="utf-8", newline="\n") as output, ExitStack() as stack:
            readers = [
                stack.enter_context(chunk_path.open(encoding="utf-8")) for chunk_path in chunk_paths
            ]
            merged = heapq.merge(
                *readers,
                key=_jsonl_sort_key,
                reverse=True,
            )
            for line in merged:
                output.write(line)
        os.replace(temporary, path)


def _optional_string(value: Any) -> str | None:
    return str(value) if value is not None else None


def _exact_post_text(post: dict[str, Any]) -> str:
    note_post = post.get("note_tweet")
    if isinstance(note_post, dict) and isinstance(note_post.get("text"), str):
        return str(note_post["text"])
    text = post.get("text")
    if not isinstance(text, str):
        raise ValueError("X post record did not include valid text")
    return text


def _safe_fence(text: str) -> str:
    longest = max((len(match.group()) for match in re.finditer(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def _escape_markdown_label(value: str) -> str:
    normalized = re.sub(r"[\x00-\x1f\x7f]", " ", value)
    return re.sub(r"([\\`*_\[\]<>])", r"\\\1", normalized)


def _safe_http_url(value: str) -> str | None:
    if (
        not value
        or any(character in value for character in "<>")
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        return None
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        return None
    return value


def _render_link(label: str, url: str) -> str:
    escaped_label = _escape_markdown_label(label)
    safe_url = _safe_http_url(url)
    return f"[{escaped_label}](<{safe_url}>)" if safe_url else escaped_label


def _record_sort_key(record: BookmarkRecordV1) -> tuple[str, str]:
    return (record.created_at or "", record.post_id)


def _jsonl_sort_key(line: str) -> tuple[str, str]:
    payload = json.loads(line)
    return (str(payload.get("created_at") or ""), str(payload["post_id"]))


def _write_sorted_chunk(
    directory: Path,
    index: int,
    records: list[BookmarkRecordV1],
) -> Path:
    chunk_path = directory / f"chunk-{index:06d}.jsonl"
    with chunk_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in sorted(records, key=_record_sort_key, reverse=True):
            handle.write(record.model_dump_json() + "\n")
    return chunk_path
