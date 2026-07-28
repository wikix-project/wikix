"""End-to-end snapshot ingestion and reconciliation."""

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from typing import Literal, Protocol

import portalocker
from pydantic import BaseModel

from wikix.api import ApiPage, IncompleteResponseError
from wikix.config import CollectionPaths, load_config
from wikix.reconcile import ReconcileResult, reconcile_collection
from wikix.records import normalize_pages
from wikix.staging import SnapshotStager
from wikix.state import load_state


class ApiTransport(Protocol):
    def fetch_bookmark_page(
        self,
        account_id: str,
        access_token: str,
        *,
        pagination_token: str | None = None,
        rich: bool = False,
    ) -> ApiPage: ...

    def fetch_folder_page(
        self,
        account_id: str,
        access_token: str,
        *,
        pagination_token: str | None = None,
    ) -> ApiPage: ...

    def fetch_folder_bookmark_page(
        self,
        account_id: str,
        folder_id: str,
        access_token: str,
        *,
        pagination_token: str | None = None,
        rich: bool = False,
    ) -> ApiPage: ...


class SyncResult(BaseModel):
    record_count: int
    profile: str
    folders: bool
    reconcile: ReconcileResult


class SyncEngine:
    def __init__(self, api: ApiTransport, *, now: Callable[[], datetime]) -> None:
        self._api = api
        self._now = now

    def run(
        self,
        paths: CollectionPaths,
        *,
        access_token: str,
        rich: bool = False,
        folders: bool = False,
    ) -> SyncResult:
        config = load_config(paths.root)
        if config.account_id is None:
            raise ValueError("authenticate this collection with `wikix auth login` before syncing")
        profile: Literal["lean", "rich"] = "rich" if rich else "lean"
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "schema": 1,
                    "account_id": config.account_id,
                    "profile": profile,
                    "folders": folders,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()[:24]
        lock_path = paths.metadata / "sync.lock"
        with portalocker.Lock(
            lock_path,
            mode="a",
            timeout=0,
            flags=portalocker.LOCK_EX | portalocker.LOCK_NB,
        ):
            SnapshotStager.purge_incompatible(paths.metadata, fingerprint)
            bookmark_stager = SnapshotStager(paths.metadata, fingerprint)
            self._fetch_bookmarks(
                bookmark_stager,
                account_id=config.account_id,
                access_token=access_token,
                rich=rich,
            )
            folder_stager: SnapshotStager | None = None
            memberships: dict[str, list[dict[str, str]]] = {}
            if folders:
                folder_stager = SnapshotStager(
                    paths.metadata,
                    fingerprint,
                    namespace="folders",
                )
                memberships = self._fetch_folders(
                    folder_stager,
                    account_id=config.account_id,
                    access_token=access_token,
                )

            synced_at = self._now()
            records = normalize_pages(
                bookmark_stager.iter_pages(),
                account_id=config.account_id,
                profile=profile,
                synced_at=synced_at,
                folder_memberships=memberships,
            )
            reconcile = reconcile_collection(paths, records, synced_at=synced_at)
            bookmark_stager.clear()
            if folder_stager is not None:
                folder_stager.clear()
            state = load_state(paths)
            return SyncResult(
                record_count=state.record_count,
                profile=profile,
                folders=folders,
                reconcile=reconcile,
            )

    def _fetch_bookmarks(
        self,
        stager: SnapshotStager,
        *,
        account_id: str,
        access_token: str,
        rich: bool,
    ) -> None:
        stager.prepare()
        if stager.complete:
            return
        if stager.page_count > 0 and stager.next_token is None:
            stager.mark_complete()
            return
        staged_tokens = [
            str(page["next_token"])
            for page in stager.iter_pages()
            if page.get("next_token") is not None
        ]
        requested_tokens = set(staged_tokens[:-1])
        pagination_token = stager.next_token
        while True:
            if pagination_token is not None:
                if pagination_token in requested_tokens:
                    raise IncompleteResponseError("X returned a pagination token cycle")
                requested_tokens.add(pagination_token)
            page = self._api.fetch_bookmark_page(
                account_id,
                access_token,
                pagination_token=pagination_token,
                rich=rich,
            )
            if page.next_token is not None and page.next_token in requested_tokens:
                raise IncompleteResponseError("X returned a pagination token cycle")
            stager.append_page(page.model_dump(exclude_none=True), next_token=page.next_token)
            if page.next_token is None:
                stager.mark_complete()
                return
            pagination_token = page.next_token

    def _fetch_folders(
        self,
        stager: SnapshotStager,
        *,
        account_id: str,
        access_token: str,
    ) -> dict[str, list[dict[str, str]]]:
        stager.prepare()
        if not stager.complete:
            checkpoint = stager.checkpoint
            phase = str(checkpoint.get("phase", "folders"))
            if phase == "folders":
                self._fetch_folder_metadata(stager, account_id, access_token)
                checkpoint = {"phase": "memberships", "folder_index": 0}
                stager.set_checkpoint(checkpoint)

            folders = self._folder_metadata(stager)
            folder_index = int(stager.checkpoint.get("folder_index", 0))
            while folder_index < len(folders):
                folder = folders[folder_index]
                prior_pages = [
                    page
                    for page in stager.iter_pages()
                    if page.get("kind") == "membership"
                    and page.get("folder", {}).get("id") == folder["id"]
                ]
                if prior_pages and prior_pages[-1]["page"].get("next_token") is None:
                    folder_index += 1
                    stager.set_checkpoint({"phase": "memberships", "folder_index": folder_index})
                    continue
                prior_tokens = [
                    str(wrapper["page"]["next_token"])
                    for wrapper in prior_pages
                    if wrapper["page"].get("next_token") is not None
                ]
                requested_tokens = set(prior_tokens[:-1])
                token = stager.next_token if prior_pages else None
                if token is not None:
                    if token in requested_tokens:
                        raise IncompleteResponseError("X returned a folder pagination token cycle")
                    requested_tokens.add(token)
                page = self._api.fetch_folder_bookmark_page(
                    account_id,
                    folder["id"],
                    access_token,
                    pagination_token=token,
                    rich=False,
                )
                if page.next_token is not None and page.next_token in requested_tokens:
                    raise IncompleteResponseError("X returned a folder pagination token cycle")
                stager.append_page(
                    {
                        "kind": "membership",
                        "folder": folder,
                        "page": page.model_dump(exclude_none=True),
                    },
                    next_token=page.next_token,
                )
                if page.next_token is None:
                    folder_index += 1
                    stager.set_checkpoint({"phase": "memberships", "folder_index": folder_index})
            stager.mark_complete()
        return self._folder_memberships(stager)

    def _fetch_folder_metadata(
        self,
        stager: SnapshotStager,
        account_id: str,
        access_token: str,
    ) -> None:
        prior_pages = [page for page in stager.iter_pages() if page.get("kind") == "folders"]
        if prior_pages and prior_pages[-1]["page"].get("next_token") is None:
            return
        prior_tokens = [
            str(wrapper["page"]["next_token"])
            for wrapper in prior_pages
            if wrapper["page"].get("next_token") is not None
        ]
        requested_tokens = set(prior_tokens[:-1])
        token = stager.next_token if prior_pages else None
        while True:
            if token is not None:
                if token in requested_tokens:
                    raise IncompleteResponseError("X returned a folder pagination token cycle")
                requested_tokens.add(token)
            page = self._api.fetch_folder_page(
                account_id,
                access_token,
                pagination_token=token,
            )
            if page.next_token is not None and page.next_token in requested_tokens:
                raise IncompleteResponseError("X returned a folder pagination token cycle")
            stager.append_page(
                {"kind": "folders", "page": page.model_dump(exclude_none=True)},
                next_token=page.next_token,
            )
            if page.next_token is None:
                return
            token = page.next_token

    @staticmethod
    def _folder_metadata(stager: SnapshotStager) -> list[dict[str, str]]:
        folders: dict[str, dict[str, str]] = {}
        for wrapper in stager.iter_pages():
            if wrapper.get("kind") != "folders":
                continue
            for folder in wrapper["page"].get("data", []):
                folders[str(folder["id"])] = {
                    "id": str(folder["id"]),
                    "name": str(folder["name"]),
                }
        return sorted(folders.values(), key=lambda folder: (folder["name"], folder["id"]))

    @staticmethod
    def _folder_memberships(
        stager: SnapshotStager,
    ) -> dict[str, list[dict[str, str]]]:
        memberships: dict[str, dict[str, dict[str, str]]] = {}
        for wrapper in stager.iter_pages():
            if wrapper.get("kind") != "membership":
                continue
            folder = wrapper["folder"]
            for post in wrapper["page"].get("data", []):
                post_id = str(post["id"])
                memberships.setdefault(post_id, {})[str(folder["id"])] = {
                    "id": str(folder["id"]),
                    "name": str(folder["name"]),
                }
        return {
            post_id: sorted(
                folder_map.values(),
                key=lambda folder: (folder["name"], folder["id"]),
            )
            for post_id, folder_map in memberships.items()
        }
