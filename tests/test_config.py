from pathlib import Path

import pytest

from wikix.config import (
    AccountMismatchError,
    CollectionExistsError,
    CollectionNotFoundError,
    bind_account,
    discover_collection,
    init_collection,
    load_config,
)


def test_init_collection_creates_layout_and_loadable_config(tmp_path: Path) -> None:
    root = tmp_path / "vault" / "Wikix"

    paths = init_collection(root, client_id="client-123", callback_port=9876)

    assert paths.root == root.resolve()
    assert paths.bookmarks.is_dir()
    assert paths.review.is_dir()
    assert paths.jsonl.read_text(encoding="utf-8") == ""
    assert paths.state.is_file()
    config = load_config(paths.root)
    assert config.schema_version == 1
    assert config.collection_id
    assert config.client_id == "client-123"
    assert config.callback_port == 9876
    assert config.account_id is None


def test_discover_collection_walks_up_from_nested_directory(tmp_path: Path) -> None:
    root = tmp_path / "collection"
    init_collection(root, client_id="client-123")
    nested = root / "bookmarks" / "nested"
    nested.mkdir()

    assert discover_collection(nested).root == root.resolve()


def test_discover_collection_accepts_a_file_inside_the_collection(tmp_path: Path) -> None:
    root = tmp_path / "collection"
    paths = init_collection(root, client_id="client-123")

    assert discover_collection(paths.jsonl).root == root.resolve()


def test_discover_collection_reports_when_no_collection_exists(tmp_path: Path) -> None:
    with pytest.raises(CollectionNotFoundError, match="no Wikix collection"):
        discover_collection(tmp_path)


def test_init_collection_refuses_to_replace_existing_config(tmp_path: Path) -> None:
    root = tmp_path / "collection"
    init_collection(root, client_id="first")

    with pytest.raises(CollectionExistsError):
        init_collection(root, client_id="second")


def test_bind_account_is_idempotent_but_rejects_different_account(tmp_path: Path) -> None:
    root = tmp_path / "collection"
    init_collection(root, client_id="client")

    bind_account(root, "42")
    bind_account(root, "42")

    assert load_config(root).account_id == "42"
    with pytest.raises(AccountMismatchError):
        bind_account(root, "99")
