"""Versioned collection operational state."""

import json
import os
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wikix.config import CollectionPaths


class StateConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    post_id: str
    reason: str


class CollectionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
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

    @field_validator("pricing_reviewed_at", "policy_reviewed_at")
    @classmethod
    def validate_review_date(cls, value: str) -> str:
        try:
            date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("review date must be a valid ISO date") from error
        return value


def load_state(paths: CollectionPaths) -> CollectionState:
    return CollectionState.model_validate_json(paths.state.read_text(encoding="utf-8"))


def save_state(paths: CollectionPaths, state: CollectionState) -> None:
    temporary = paths.state.with_name(f".{paths.state.name}.tmp")
    temporary.write_text(
        json.dumps(state.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, paths.state)
