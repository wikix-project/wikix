"""Versioned collection operational state."""

import json
import os

from pydantic import BaseModel, Field

from wikix.config import CollectionPaths


class StateConflict(BaseModel):
    post_id: str
    reason: str


class CollectionState(BaseModel):
    schema_version: int = 1
    account_id: str | None = None
    last_sync: str | None = None
    last_profile: str | None = None
    record_count: int = 0
    hashes: dict[str, str] = Field(default_factory=dict)
    record_hashes: dict[str, str] = Field(default_factory=dict)
    conflicts: list[StateConflict] = Field(default_factory=list)
    pending: dict[str, object] | None = None
    pricing_reviewed_at: str = "2026-07-28"
    policy_reviewed_at: str = "2026-07-28"


def load_state(paths: CollectionPaths) -> CollectionState:
    return CollectionState.model_validate_json(paths.state.read_text(encoding="utf-8"))


def save_state(paths: CollectionPaths, state: CollectionState) -> None:
    temporary = paths.state.with_name(f".{paths.state.name}.tmp")
    temporary.write_text(
        json.dumps(state.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, paths.state)
