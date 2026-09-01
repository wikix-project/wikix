from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from wikix.config import init_collection
from wikix.reconcile import (
    NOTES_END,
    NOTES_START,
    _managed_hash,
    reconcile_collection,
)
from wikix.records import BookmarkRecordV1, render_markdown
from wikix.state import load_state, save_state

SYNCED = datetime(2026, 7, 28, 12, tzinfo=UTC)


def record(post_id: str = "100", text: str = "Original") -> BookmarkRecordV1:
    return BookmarkRecordV1(
        profile="lean",
        account_id="42",
        post_id=post_id,
        source_url=f"https://x.com/i/web/status/{post_id}",
        text=text,
        created_at="2026-07-27T12:00:00.000Z",
        synced_at="2026-07-28T12:00:00Z",
        author_id="u1",
    )


def add_notes(markdown: str, notes: str) -> str:
    before, remainder = markdown.rsplit(NOTES_START, 1)
    _, after = remainder.split(NOTES_END, 1)
    return f"{before}{NOTES_START}\n{notes.rstrip()}\n{NOTES_END}{after}"


def test_reconcile_writes_snapshot_and_does_not_rewrite_unchanged_note(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")

    first = reconcile_collection(paths, [record()], synced_at=SYNCED)
    note = paths.bookmarks / "100.md"
    first_inode = note.stat().st_ino
    second = reconcile_collection(paths, [record()], synced_at=SYNCED)

    assert first.added == 1
    assert second.unchanged == 1
    assert note.stat().st_ino == first_inode
    assert '"post_id":"100"' in paths.jsonl.read_text(encoding="utf-8")
    state = load_state(paths)
    assert state.account_id == "42"
    assert state.record_count == 1
    assert state.conflicts == []


def test_reconcile_preserves_personal_notes_when_post_changes(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    reconcile_collection(paths, [record()], synced_at=SYNCED)
    note = paths.bookmarks / "100.md"
    note.write_text(
        add_notes(note.read_text(encoding="utf-8"), "Keep this insight."),
        encoding="utf-8",
    )

    result = reconcile_collection(paths, [record(text="Edited upstream")], synced_at=SYNCED)

    updated = note.read_text(encoding="utf-8")
    assert result.updated == 1
    assert "Edited upstream" in updated
    assert "Keep this insight." in updated


def test_reconcile_reports_managed_edit_and_leaves_note_untouched(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    reconcile_collection(paths, [record()], synced_at=SYNCED)
    note = paths.bookmarks / "100.md"
    edited = note.read_text(encoding="utf-8").replace("## Source", "## My changed source")
    note.write_text(edited, encoding="utf-8")

    result = reconcile_collection(paths, [record(text="Edited upstream")], synced_at=SYNCED)

    assert result.conflicts[0].post_id == "100"
    assert note.read_text(encoding="utf-8") == edited
    assert load_state(paths).conflicts[0].post_id == "100"


def test_removed_annotation_moves_to_review_and_restores_if_rebookmarked(
    tmp_path: Path,
) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    reconcile_collection(paths, [record()], synced_at=SYNCED)
    note = paths.bookmarks / "100.md"
    note.write_text(
        add_notes(note.read_text(encoding="utf-8"), "My durable note."),
        encoding="utf-8",
    )

    removed = reconcile_collection(paths, [], synced_at=SYNCED)
    review = paths.review / "100.md"

    assert removed.removed == 1
    assert not note.exists()
    assert "My durable note." in review.read_text(encoding="utf-8")
    assert "Original" not in review.read_text(encoding="utf-8")

    restored = reconcile_collection(paths, [record(text="Back again")], synced_at=SYNCED)

    assert restored.added == 1
    assert "My durable note." in note.read_text(encoding="utf-8")
    assert not review.exists()


def test_malformed_markers_conflict_and_existing_journal_is_recovered(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    reconcile_collection(paths, [record()], synced_at=SYNCED)
    note = paths.bookmarks / "100.md"
    note.write_text(note.read_text(encoding="utf-8").replace(NOTES_END, ""), encoding="utf-8")
    journal = paths.metadata / "reconcile-journal.json"
    journal.write_text('{"status":"interrupted"}\n', encoding="utf-8")

    result = reconcile_collection(paths, [record()], synced_at=SYNCED)

    assert result.conflicts[0].reason == "personal notes markers are malformed"
    assert not journal.exists()


def test_reconcile_recognizes_its_own_partial_note_write_after_crash(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    reconcile_collection(paths, [record()], synced_at=SYNCED)
    updated = record(text="Updated before crash")
    note = paths.bookmarks / "100.md"
    note.write_text(render_markdown(updated), encoding="utf-8")
    journal = paths.metadata / "reconcile-journal.json"
    journal.write_text('{"status":"applying"}\n', encoding="utf-8")

    result = reconcile_collection(paths, [updated], synced_at=SYNCED)

    assert result.conflicts == []
    assert result.unchanged == 1
    assert not journal.exists()


def test_marker_literals_in_remote_text_and_personal_notes_do_not_break_reconciliation(
    tmp_path: Path,
) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    marker_text = f"Remote literals: {NOTES_START} and {NOTES_END}"

    first = reconcile_collection(paths, [record(text=marker_text)], synced_at=SYNCED)
    note = paths.bookmarks / "100.md"
    note.write_text(
        add_notes(note.read_text(encoding="utf-8"), marker_text),
        encoding="utf-8",
    )
    second = reconcile_collection(paths, [record(text=marker_text)], synced_at=SYNCED)

    assert first.added == 1
    assert second.unchanged == 1
    assert marker_text in note.read_text(encoding="utf-8")
    assert not (paths.metadata / "reconcile-journal.json").exists()


def test_recovery_removes_stale_review_after_rebookmark_note_was_already_written(
    tmp_path: Path,
) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    reconcile_collection(paths, [record()], synced_at=SYNCED)
    note = paths.bookmarks / "100.md"
    note.write_text(
        add_notes(note.read_text(encoding="utf-8"), "My durable note."),
        encoding="utf-8",
    )
    reconcile_collection(paths, [], synced_at=SYNCED)
    review = paths.review / "100.md"
    restored = record(text="Back before crash")
    note.write_text(
        render_markdown(restored, personal_notes="My durable note.\n"),
        encoding="utf-8",
    )
    (paths.metadata / "reconcile-journal.json").write_text(
        '{"status":"applying"}\n',
        encoding="utf-8",
    )

    result = reconcile_collection(paths, [restored], synced_at=SYNCED)

    assert result.conflicts == []
    assert not review.exists()
    assert "My durable note." in note.read_text(encoding="utf-8")


def test_reconcile_rejects_duplicate_posts_before_committing(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")

    with pytest.raises(ValueError, match="duplicate post id"):
        reconcile_collection(paths, [record(), record()], synced_at=SYNCED)

    assert paths.jsonl.read_text(encoding="utf-8") == ""
    assert not (paths.bookmarks / "100.md").exists()


def test_reconcile_rejects_mixed_account_snapshot_before_committing(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    other_account = record("200").model_copy(update={"account_id": "99"})

    with pytest.raises(ValueError, match="multiple X accounts"):
        reconcile_collection(paths, [record(), other_account], synced_at=SYNCED)

    assert paths.jsonl.read_text(encoding="utf-8") == ""


def test_reconcile_rejects_unsupported_state_before_mutating_output(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    paths.jsonl.write_text("existing\n", encoding="utf-8")
    paths.state.write_text('{"schema_version":2}\n', encoding="utf-8")

    with pytest.raises(ValidationError):
        reconcile_collection(paths, [record()], synced_at=SYNCED)

    assert paths.jsonl.read_text(encoding="utf-8") == "existing\n"
    assert not (paths.bookmarks / "100.md").exists()
    assert not (paths.metadata / "reconcile-journal.json").exists()


def test_first_reconcile_conflicts_with_unmanaged_existing_note(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    note = paths.bookmarks / "100.md"
    note.write_text(render_markdown(record()), encoding="utf-8")

    result = reconcile_collection(paths, [record()], synced_at=SYNCED)

    assert result.conflicts[0].reason == "Wikix-managed content was edited"
    assert load_state(paths).hashes == {}


def test_first_reconcile_conflicts_with_malformed_existing_note(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    note = paths.bookmarks / "100.md"
    note.write_text("not a Wikix note\n", encoding="utf-8")

    result = reconcile_collection(paths, [record()], synced_at=SYNCED)

    assert result.conflicts[0].reason == "personal notes markers are malformed"
    assert load_state(paths).hashes == {}


def test_reconcile_detects_malformed_review_note_on_rebookmark(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    reconcile_collection(paths, [record()], synced_at=SYNCED)
    note = paths.bookmarks / "100.md"
    note.write_text(
        add_notes(note.read_text(encoding="utf-8"), "Keep this."),
        encoding="utf-8",
    )
    reconcile_collection(paths, [], synced_at=SYNCED)
    review = paths.review / "100.md"
    malformed = review.read_text(encoding="utf-8").replace(NOTES_END, "")
    review.write_text(malformed, encoding="utf-8")

    result = reconcile_collection(paths, [record()], synced_at=SYNCED)

    assert result.conflicts[0].reason == "review note markers are malformed"
    assert review.read_text(encoding="utf-8") == malformed
    assert not note.exists()


def test_reconcile_counts_identical_render_when_record_hash_state_is_missing(
    tmp_path: Path,
) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    reconcile_collection(paths, [record()], synced_at=SYNCED)
    state = load_state(paths)
    state.record_hashes = {}
    save_state(paths, state)

    result = reconcile_collection(paths, [record()], synced_at=SYNCED)

    assert result.unchanged == 1


def test_removed_bookmark_already_missing_from_disk_is_reconciled(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    reconcile_collection(paths, [record()], synced_at=SYNCED)
    (paths.bookmarks / "100.md").unlink()

    result = reconcile_collection(paths, [], synced_at=SYNCED)

    assert result.removed == 0
    assert load_state(paths).record_count == 0


@pytest.mark.parametrize("retain_record_hash", [True, False])
def test_malformed_removed_note_remains_a_conflict(
    tmp_path: Path,
    retain_record_hash: bool,
) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    reconcile_collection(paths, [record()], synced_at=SYNCED)
    note = paths.bookmarks / "100.md"
    malformed = note.read_text(encoding="utf-8").replace(NOTES_END, "")
    note.write_text(malformed, encoding="utf-8")
    if not retain_record_hash:
        state = load_state(paths)
        state.record_hashes = {}
        save_state(paths, state)

    result = reconcile_collection(paths, [], synced_at=SYNCED)

    assert result.conflicts[0].reason == "personal notes markers are malformed"
    assert note.read_text(encoding="utf-8") == malformed


@pytest.mark.parametrize("retain_record_hash", [True, False])
def test_managed_edit_on_removed_note_remains_a_conflict(
    tmp_path: Path,
    retain_record_hash: bool,
) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    reconcile_collection(paths, [record()], synced_at=SYNCED)
    note = paths.bookmarks / "100.md"
    edited = note.read_text(encoding="utf-8").replace("## Source", "## Edited source")
    note.write_text(edited, encoding="utf-8")
    if not retain_record_hash:
        state = load_state(paths)
        state.record_hashes = {}
        save_state(paths, state)

    result = reconcile_collection(paths, [], synced_at=SYNCED)

    assert result.conflicts[0].reason == "Wikix-managed content was edited"
    assert note.read_text(encoding="utf-8") == edited


def test_removed_unannotated_bookmark_is_deleted_without_review_note(
    tmp_path: Path,
) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    reconcile_collection(paths, [record()], synced_at=SYNCED)

    result = reconcile_collection(paths, [], synced_at=SYNCED)

    assert result.removed == 1
    assert not (paths.bookmarks / "100.md").exists()
    assert not (paths.review / "100.md").exists()


def test_managed_hash_rejects_non_wikix_markdown() -> None:
    with pytest.raises(ValueError, match="malformed notes markers"):
        _managed_hash("not a Wikix note")
