"""Collection configuration and discovery."""

import json
import os
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path

import tomli_w
from pydantic import BaseModel


class CollectionExistsError(RuntimeError):
    """Raised when initialization would replace an existing collection."""


class CollectionNotFoundError(RuntimeError):
    """Raised when no collection can be discovered."""


class AccountMismatchError(RuntimeError):
    """Raised when a collection is already bound to another X account."""


class CollectionConfig(BaseModel):
    """Persisted non-secret collection settings."""

    schema_version: int = 1
    collection_id: str
    client_id: str
    callback_port: int = 8765
    account_id: str | None = None


@dataclass(frozen=True)
class CollectionPaths:
    """Resolved filesystem paths owned by a Wikix collection."""

    root: Path
    bookmarks: Path
    review: Path
    jsonl: Path
    metadata: Path
    config: Path
    state: Path


def collection_paths(root: Path) -> CollectionPaths:
    resolved = root.expanduser().resolve()
    metadata = resolved / ".wikix"
    return CollectionPaths(
        root=resolved,
        bookmarks=resolved / "bookmarks",
        review=resolved / "_review",
        jsonl=resolved / "bookmarks.jsonl",
        metadata=metadata,
        config=metadata / "config.toml",
        state=metadata / "state.json",
    )


def init_collection(root: Path, *, client_id: str, callback_port: int = 8765) -> CollectionPaths:
    paths = collection_paths(root)
    if paths.config.exists():
        raise CollectionExistsError(f"collection already exists at {paths.root}")

    paths.bookmarks.mkdir(parents=True, exist_ok=True)
    paths.review.mkdir(parents=True, exist_ok=True)
    paths.metadata.mkdir(parents=True, exist_ok=True)
    paths.jsonl.touch(exist_ok=True)

    config = CollectionConfig(
        collection_id=str(uuid.uuid4()),
        client_id=client_id,
        callback_port=callback_port,
    )
    state: dict[str, object] = {
        "schema_version": 1,
        "account_id": None,
        "last_sync": None,
        "last_profile": None,
        "record_count": 0,
        "hashes": {},
        "conflicts": [],
        "pending": None,
        "pricing_reviewed_at": "2026-07-28",
        "policy_reviewed_at": "2026-07-28",
    }
    state_temporary = paths.state.with_name(f".{paths.state.name}.tmp")
    state_temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(state_temporary, paths.state)
    save_config(paths.root, config)
    return paths


def discover_collection(start: Path) -> CollectionPaths:
    current = start.expanduser().resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        paths = collection_paths(candidate)
        if paths.config.is_file():
            return paths
    raise CollectionNotFoundError(f"no Wikix collection found from {start}")


def load_config(root: Path) -> CollectionConfig:
    paths = collection_paths(root)
    with paths.config.open("rb") as handle:
        return CollectionConfig.model_validate(tomllib.load(handle))


def save_config(root: Path, config: CollectionConfig) -> None:
    paths = collection_paths(root)
    temporary = paths.config.with_name(f".{paths.config.name}.tmp")
    temporary.write_bytes(tomli_w.dumps(config.model_dump(exclude_none=True)).encode())
    os.replace(temporary, paths.config)


def bind_account(root: Path, account_id: str) -> CollectionConfig:
    config = load_config(root)
    if config.account_id is not None and config.account_id != account_id:
        raise AccountMismatchError(
            f"collection belongs to X account {config.account_id}, not {account_id}"
        )
    bound = config.model_copy(update={"account_id": account_id})
    save_config(root, bound)
    return bound
