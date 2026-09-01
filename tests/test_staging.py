import json
from pathlib import Path
from typing import Any

import pytest

from wikix.staging import SnapshotStager


def _replace_nested(
    payload: dict[str, Any],
    path: tuple[str | int, ...],
    replacement: object,
) -> None:
    current: Any = payload
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = replacement


def test_stager_resumes_pages_and_clears_incompatible_snapshot(tmp_path: Path) -> None:
    metadata = tmp_path / ".wikix"
    first = SnapshotStager(metadata, "lean-fingerprint")
    first.prepare()
    first.append_page(
        {"data": [{"id": "1", "text": "saved"}], "next_token": "next"},
        next_token="next",
    )

    resumed = SnapshotStager(metadata, "lean-fingerprint")
    resumed.prepare()

    assert resumed.next_token == "next"
    assert list(resumed.iter_pages()) == [
        {"data": [{"id": "1", "text": "saved"}], "next_token": "next"}
    ]

    incompatible = SnapshotStager(metadata, "rich-fingerprint")
    incompatible.prepare()

    assert incompatible.next_token is None
    assert not first.directory.exists()


def test_stager_marks_complete_and_removes_raw_pages(tmp_path: Path) -> None:
    stager = SnapshotStager(tmp_path / ".wikix", "fingerprint")
    stager.prepare()
    stager.append_page({"data": [{"id": "1", "text": "saved"}]}, next_token=None)
    stager.mark_complete()

    assert stager.complete is True
    assert list(stager.iter_pages()) == [{"data": [{"id": "1", "text": "saved"}]}]

    stager.clear()

    assert not stager.directory.exists()
    stager.clear()


def test_stager_clear_preserves_other_fingerprints(tmp_path: Path) -> None:
    stager = SnapshotStager(tmp_path / ".wikix", "current")
    stager.prepare()
    sibling = stager.directory.parent / "other"
    sibling.mkdir()

    stager.clear()

    assert sibling.is_dir()


def test_stager_persists_named_checkpoint_within_namespace(tmp_path: Path) -> None:
    metadata = tmp_path / ".wikix"
    stager = SnapshotStager(metadata, "fingerprint", namespace="folders")
    stager.prepare()
    stager.set_checkpoint({"phase": "memberships", "folder_index": 2})

    resumed = SnapshotStager(metadata, "fingerprint", namespace="folders")
    resumed.prepare()

    assert resumed.page_count == 0
    assert resumed.checkpoint == {"phase": "memberships", "folder_index": 2}


def test_corrupt_manifest_with_missing_page_is_discarded_for_safe_refetch(
    tmp_path: Path,
) -> None:
    stager = SnapshotStager(tmp_path, "fingerprint")
    stager.prepare()
    stager.append_page({"data": [{"id": "1", "text": "saved"}]}, next_token=None)
    stager.mark_complete()
    next(stager.directory.glob("page-*.json")).unlink()

    resumed = SnapshotStager(tmp_path, "fingerprint")
    resumed.prepare()

    assert resumed.page_count == 0
    assert resumed.next_token is None
    assert resumed.complete is False
    assert list(resumed.iter_pages()) == []


def test_corrupt_staged_page_payload_is_discarded_for_safe_refetch(tmp_path: Path) -> None:
    stager = SnapshotStager(tmp_path, "fingerprint")
    stager.prepare()
    stager.append_page({"data": [{"id": "1", "text": "valid"}]}, next_token=None)
    stager.mark_complete()
    next(stager.directory.glob("page-*.json")).write_text("{}\n", encoding="utf-8")

    resumed = SnapshotStager(tmp_path, "fingerprint")
    resumed.prepare()

    assert resumed.page_count == 0
    assert resumed.complete is False


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        pytest.param(("data", 0, "author_id"), 42, id="numeric-author-id"),
        pytest.param(("data", 0, "entities"), [], id="non-object-entities"),
        pytest.param(("data", 0, "note_tweet", "text"), 42, id="invalid-note-tweet-text"),
        pytest.param(
            ("data", 0, "attachments", "media_keys", 0),
            42,
            id="non-string-attachment-media-key",
        ),
        pytest.param(
            ("data", 0, "referenced_tweets", 0, "id"),
            "invalid",
            id="malformed-referenced-post-id",
        ),
        pytest.param(
            ("data", 0, "referenced_tweets", 0, "type"),
            42,
            id="malformed-referenced-post-type",
        ),
        pytest.param(
            ("includes", "users", 0, "username"),
            42,
            id="malformed-included-user",
        ),
        pytest.param(
            ("includes", "media", 0, "media_key"),
            "",
            id="malformed-included-media",
        ),
        pytest.param(
            ("includes", "tweets", 0, "text"),
            42,
            id="malformed-included-post",
        ),
        pytest.param(("next_token",), "", id="empty-next-token"),
    ],
)
def test_recovered_bookmark_pages_enforce_live_api_validation(
    tmp_path: Path,
    path: tuple[str | int, ...],
    replacement: object,
) -> None:
    page: dict[str, Any] = {
        "data": [
            {
                "id": "1",
                "text": "saved",
                "author_id": "42",
                "entities": {
                    "urls": [
                        {
                            "url": "https://t.co/example",
                            "expanded_url": "https://example.com",
                            "display_url": "example.com",
                        }
                    ]
                },
                "note_tweet": {"text": "saved in full"},
                "attachments": {"media_keys": ["3_4"]},
                "referenced_tweets": [{"id": "2", "type": "quoted"}],
            }
        ],
        "includes": {
            "users": [{"id": "42", "name": "Ada", "username": "ada"}],
            "media": [{"media_key": "3_4", "type": "photo"}],
            "tweets": [{"id": "2", "text": "quoted post", "author_id": "43"}],
        },
        "next_token": "next",
    }
    stager = SnapshotStager(tmp_path, "fingerprint")
    stager.prepare()
    stager.append_page(page, next_token="next")

    page_path = next(stager.directory.glob("page-*.json"))
    staged_page = json.loads(page_path.read_text(encoding="utf-8"))
    _replace_nested(staged_page, path, replacement)
    page_path.write_text(json.dumps(staged_page) + "\n", encoding="utf-8")
    if path == ("next_token",):
        manifest_path = stager.directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["next_token"] = ""
        manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")

    resumed = SnapshotStager(tmp_path, "fingerprint")
    resumed.prepare()

    assert resumed.page_count == 0
    assert resumed.complete is False
    assert list(resumed.iter_pages()) == []


def test_non_object_manifest_and_invalid_page_json_are_discarded(tmp_path: Path) -> None:
    stager = SnapshotStager(tmp_path, "fingerprint")
    stager.prepare()
    (stager.directory / "manifest.json").write_text("[]\n", encoding="utf-8")
    resumed = SnapshotStager(tmp_path, "fingerprint")
    resumed.prepare()
    assert resumed.page_count == 0

    resumed.append_page({"data": [{"id": "1", "text": "valid"}]}, next_token=None)
    next(resumed.directory.glob("page-*.json")).write_text("{broken", encoding="utf-8")
    reparsed = SnapshotStager(tmp_path, "fingerprint")
    reparsed.prepare()
    assert reparsed.page_count == 0


def test_folder_metadata_and_membership_pages_validate_when_resumed(tmp_path: Path) -> None:
    folders = SnapshotStager(tmp_path, "fingerprint", namespace="folders")
    folders.prepare()
    folders.append_page(
        {
            "kind": "folders",
            "page": {
                "data": [{"id": "10", "name": "Research"}],
                "next_token": "next",
            },
        },
        next_token="next",
    )
    folders.append_page(
        {
            "kind": "membership",
            "folder": {"id": "10", "name": "Research"},
            "page": {"data": [{"id": "1"}]},
        },
        next_token=None,
    )
    folders.mark_complete()

    resumed = SnapshotStager(tmp_path, "fingerprint", namespace="folders")
    resumed.prepare()

    assert resumed.complete is True
    assert resumed.page_count == 2


def test_stager_purges_incompatible_files_at_every_staging_level(tmp_path: Path) -> None:
    metadata = tmp_path / ".wikix"
    staging = metadata / "staging"
    staging.mkdir(parents=True)
    (staging / "loose-namespace-file").write_text("junk", encoding="utf-8")
    folders = staging / "folders"
    folders.mkdir()
    (folders / "old-fingerprint-file").write_text("junk", encoding="utf-8")

    SnapshotStager.purge_incompatible(metadata, "current")

    assert not (staging / "loose-namespace-file").exists()
    assert not (folders / "old-fingerprint-file").exists()

    bookmarks = staging / "bookmarks"
    bookmarks.mkdir(parents=True)
    (bookmarks / "old-fingerprint-file").write_text("junk", encoding="utf-8")
    stager = SnapshotStager(metadata, "current")
    stager.prepare()
    assert not (bookmarks / "old-fingerprint-file").exists()


def test_invalid_manifest_fields_are_discarded(tmp_path: Path) -> None:
    stager = SnapshotStager(tmp_path, "fingerprint")
    stager.prepare()
    (stager.directory / "manifest.json").write_text(
        '{"checkpoint":{},"complete":false,"next_token":null,"page_count":true}\n',
        encoding="utf-8",
    )

    resumed = SnapshotStager(tmp_path, "fingerprint")
    resumed.prepare()

    assert resumed.page_count == 0
    assert resumed.complete is False


@pytest.mark.parametrize(
    "invalid_page",
    [
        {"kind": "unknown", "page": {"data": []}},
        {"kind": "folders", "page": {"data": "not-a-list"}},
    ],
)
def test_invalid_folder_staging_pages_are_discarded(
    tmp_path: Path,
    invalid_page: dict[str, object],
) -> None:
    folders = SnapshotStager(tmp_path, "fingerprint", namespace="folders")
    folders.prepare()
    folders.append_page(invalid_page, next_token=None)
    folders.mark_complete()

    resumed = SnapshotStager(tmp_path, "fingerprint", namespace="folders")
    resumed.prepare()

    assert resumed.page_count == 0
    assert resumed.complete is False
