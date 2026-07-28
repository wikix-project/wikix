"""Conflict-aware Markdown and JSONL reconciliation."""

import hashlib
import json
import os
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from wikix.config import CollectionPaths
from wikix.records import BookmarkRecordV1, render_markdown, write_jsonl
from wikix.state import CollectionState, StateConflict, load_state, save_state

NOTES_START = "<!-- wikix:notes:start -->"
NOTES_END = "<!-- wikix:notes:end -->"
NOTES_SECTION = re.compile(
    rf"\A(?P<managed>.*)\n## Personal notes\n{re.escape(NOTES_START)}\n"
    rf"(?P<notes>.*)\n{re.escape(NOTES_END)}\n?\Z",
    re.DOTALL,
)


class ReconcileConflict(BaseModel):
    post_id: str
    reason: str


class ReconcileResult(BaseModel):
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    conflicts: list[ReconcileConflict] = Field(default_factory=list)


def reconcile_collection(
    paths: CollectionPaths,
    records: Iterable[BookmarkRecordV1],
    *,
    synced_at: datetime,
) -> ReconcileResult:
    state = load_state(paths)
    result = ReconcileResult()
    journal = paths.metadata / "reconcile-journal.json"
    recovering = journal.exists()
    spool = paths.metadata / "reconcile-records.jsonl"
    spool_tmp = spool.with_name(f".{spool.name}.tmp")
    _atomic_write_json(journal, {"status": "staging"})

    current_ids: set[str] = set()
    account_id: str | None = None
    profile: str | None = None
    with spool_tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            if record.post_id in current_ids:
                raise ValueError(f"duplicate post id in snapshot: {record.post_id}")
            current_ids.add(record.post_id)
            account_id = account_id or record.account_id
            profile = profile or record.profile
            if account_id != record.account_id:
                raise ValueError("snapshot contains multiple X accounts")
            handle.write(record.model_dump_json(exclude_none=True) + "\n")
    os.replace(spool_tmp, spool)
    _atomic_write_json(journal, {"status": "applying", "record_count": len(current_ids)})

    new_hashes: dict[str, str] = {}
    new_record_hashes: dict[str, str] = {}
    for record in _iter_spool(spool):
        post_id = record.post_id
        note_path = paths.bookmarks / f"{post_id}.md"
        review_path = paths.review / f"{post_id}.md"
        prior_hash = state.hashes.get(post_id)
        notes = ""
        existing: str | None = None

        if note_path.exists():
            existing = note_path.read_text(encoding="utf-8")
            try:
                notes = _extract_notes(existing)
            except ValueError:
                _add_conflict(result, post_id, "personal notes markers are malformed")
                if prior_hash:
                    new_hashes[post_id] = prior_hash
                continue
            current_managed_hash = _managed_hash(existing)
            record_hash = _record_hash(record)
            rendered = render_markdown(record, personal_notes=notes)
            target_managed_hash = _managed_hash(rendered)
            if prior_hash is None or current_managed_hash != prior_hash:
                if recovering and current_managed_hash == target_managed_hash:
                    result.unchanged += 1
                    review_path.unlink(missing_ok=True)
                    new_hashes[post_id] = current_managed_hash
                    new_record_hashes[post_id] = record_hash
                    continue
                _add_conflict(result, post_id, "Wikix-managed content was edited")
                if prior_hash:
                    new_hashes[post_id] = prior_hash
                continue
        elif review_path.exists():
            review_text = review_path.read_text(encoding="utf-8")
            try:
                notes = _extract_notes(review_text)
            except ValueError:
                _add_conflict(result, post_id, "review note markers are malformed")
                continue

        record_hash = _record_hash(record)
        if (
            existing is not None
            and state.record_hashes.get(post_id) == record_hash
            and prior_hash is not None
        ):
            result.unchanged += 1
            new_hashes[post_id] = prior_hash
            new_record_hashes[post_id] = record_hash
            continue

        rendered = render_markdown(record, personal_notes=notes)
        rendered_managed_hash = _managed_hash(rendered)
        if existing == rendered:
            result.unchanged += 1
        else:
            _atomic_write_text(note_path, rendered)
            if existing is None:
                result.added += 1
            else:
                result.updated += 1
        if review_path.exists():
            review_path.unlink()
        new_hashes[post_id] = rendered_managed_hash
        new_record_hashes[post_id] = record_hash

    removed_ids = sorted(set(state.hashes) - current_ids)
    for post_id in removed_ids:
        note_path = paths.bookmarks / f"{post_id}.md"
        if not note_path.exists():
            continue
        existing = note_path.read_text(encoding="utf-8")
        try:
            notes = _extract_notes(existing)
        except ValueError:
            _add_conflict(result, post_id, "personal notes markers are malformed")
            new_hashes[post_id] = state.hashes[post_id]
            if post_id in state.record_hashes:
                new_record_hashes[post_id] = state.record_hashes[post_id]
            continue
        if _managed_hash(existing) != state.hashes[post_id]:
            _add_conflict(result, post_id, "Wikix-managed content was edited")
            new_hashes[post_id] = state.hashes[post_id]
            if post_id in state.record_hashes:
                new_record_hashes[post_id] = state.record_hashes[post_id]
            continue
        if notes.strip():
            review_path = paths.review / f"{post_id}.md"
            _atomic_write_text(
                review_path,
                _render_review(
                    post_id,
                    notes,
                    synced_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                ),
            )
        note_path.unlink()
        result.removed += 1

    write_jsonl(paths.jsonl, _iter_spool(spool))
    completed_at = synced_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    next_state = CollectionState(
        account_id=account_id or state.account_id,
        last_sync=completed_at,
        last_profile=profile or state.last_profile,
        record_count=len(current_ids),
        hashes=new_hashes,
        record_hashes=new_record_hashes,
        conflicts=[
            StateConflict(post_id=conflict.post_id, reason=conflict.reason)
            for conflict in result.conflicts
        ],
        pending=None,
        pricing_reviewed_at=state.pricing_reviewed_at,
        policy_reviewed_at=state.policy_reviewed_at,
    )
    save_state(paths, next_state)
    spool.unlink(missing_ok=True)
    journal.unlink(missing_ok=True)
    return result


def _iter_spool(path: Path) -> Iterable[BookmarkRecordV1]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            yield BookmarkRecordV1.model_validate_json(line)


def _extract_notes(markdown: str) -> str:
    match = NOTES_SECTION.fullmatch(markdown)
    if match is None:
        raise ValueError("malformed notes markers")
    content = match.group("notes")
    return f"{content}\n" if content else ""


def _managed_hash(markdown: str) -> str:
    match = NOTES_SECTION.fullmatch(markdown)
    if match is None:
        raise ValueError("malformed notes markers")
    start, end = match.span("notes")
    normalized = f"{markdown[:start]}{markdown[end:]}"
    return hashlib.sha256(normalized.encode()).hexdigest()


def _record_hash(record: BookmarkRecordV1) -> str:
    payload = record.model_dump(mode="json", exclude={"synced_at"}, exclude_none=True)
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def _render_review(post_id: str, notes: str, removed_at: str) -> str:
    frontmatter: dict[str, Any] = {
        "wikix_review_schema": 1,
        "x_post_id": post_id,
        "source_url": f"https://x.com/i/web/status/{post_id}",
        "removed_at": removed_at,
    }
    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False).rstrip()
    body = notes.rstrip("\n")
    return f"---\n{yaml_text}\n---\n\n## Personal notes\n{NOTES_START}\n{body}\n{NOTES_END}\n"


def _add_conflict(result: ReconcileResult, post_id: str, reason: str) -> None:
    result.conflicts.append(ReconcileConflict(post_id=post_id, reason=reason))


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)
