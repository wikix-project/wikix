from datetime import UTC, datetime
from pathlib import Path

import httpx
import portalocker
import pytest
import yaml

from wikix.api import ApiPage, IncompleteResponseError, XApiClient, XApiError
from wikix.config import bind_account, init_collection
from wikix.staging import SnapshotStager
from wikix.sync import SyncEngine

NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)


def post(post_id: str, text: str) -> dict[str, str]:
    return {
        "id": post_id,
        "text": text,
        "author_id": "u1",
        "created_at": f"2026-07-{post_id[-1]}T12:00:00.000Z",
    }


class FakeApi:
    def __init__(
        self,
        bookmark_pages: dict[str | None, ApiPage | Exception],
        *,
        folders: ApiPage | None = None,
        folder_posts: dict[str, ApiPage] | None = None,
    ) -> None:
        self.bookmark_pages = bookmark_pages
        self.folders = folders or ApiPage()
        self.folder_posts = folder_posts or {}
        self.bookmark_tokens: list[str | None] = []

    def fetch_bookmark_page(
        self,
        account_id: str,
        access_token: str,
        *,
        pagination_token: str | None = None,
        rich: bool = False,
    ) -> ApiPage:
        self.bookmark_tokens.append(pagination_token)
        result = self.bookmark_pages[pagination_token]
        if isinstance(result, Exception):
            raise result
        return result

    def fetch_folder_page(
        self,
        account_id: str,
        access_token: str,
        *,
        pagination_token: str | None = None,
    ) -> ApiPage:
        return self.folders

    def fetch_folder_bookmark_page(
        self,
        account_id: str,
        folder_id: str,
        access_token: str,
        *,
        pagination_token: str | None = None,
        rich: bool = False,
    ) -> ApiPage:
        return self.folder_posts[folder_id]


def prepared_collection(tmp_path: Path):
    paths = init_collection(tmp_path / "collection", client_id="client")
    bind_account(paths.root, "42")
    return paths


def test_sync_engine_fetches_complete_snapshot_and_clears_staging(tmp_path: Path) -> None:
    paths = prepared_collection(tmp_path)
    api = FakeApi({None: ApiPage(data=[post("101", "one")])})

    result = SyncEngine(api, now=lambda: NOW).run(paths, access_token="access")

    assert result.record_count == 1
    assert result.reconcile.added == 1
    assert (paths.bookmarks / "101.md").exists()
    assert not (paths.metadata / "staging").exists()


def test_sync_engine_resumes_after_interruption_without_touching_existing_output(
    tmp_path: Path,
) -> None:
    paths = prepared_collection(tmp_path)
    paths.jsonl.write_text("existing\n", encoding="utf-8")
    failing = FakeApi(
        {
            None: ApiPage(data=[post("101", "one")], next_token="next"),
            "next": XApiError("network down"),
        }
    )

    with pytest.raises(XApiError):
        SyncEngine(failing, now=lambda: NOW).run(paths, access_token="access")

    assert paths.jsonl.read_text(encoding="utf-8") == "existing\n"

    resumed = FakeApi({"next": ApiPage(data=[post("102", "two")])})
    result = SyncEngine(resumed, now=lambda: NOW).run(paths, access_token="access")

    assert resumed.bookmark_tokens == ["next"]
    assert result.record_count == 2
    assert (paths.bookmarks / "101.md").exists()
    assert (paths.bookmarks / "102.md").exists()


def test_sync_engine_opt_in_folders_adds_membership_to_frontmatter(tmp_path: Path) -> None:
    paths = prepared_collection(tmp_path)
    api = FakeApi(
        {None: ApiPage(data=[post("101", "one")])},
        folders=ApiPage(data=[{"id": "f1", "name": "Research"}]),
        folder_posts={"f1": ApiPage(data=[post("101", "one")])},
    )

    SyncEngine(api, now=lambda: NOW).run(paths, access_token="access", folders=True)

    markdown = (paths.bookmarks / "101.md").read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(markdown.split("---", 2)[1])
    assert frontmatter["x_folders"] == [{"id": "f1", "name": "Research"}]


def test_folder_metadata_and_membership_pagination_is_complete(tmp_path: Path) -> None:
    paths = prepared_collection(tmp_path)

    class PagedFolderApi(FakeApi):
        def __init__(self) -> None:
            super().__init__({None: ApiPage(data=[post("101", "one"), post("102", "two")])})
            self.folder_tokens: list[str | None] = []
            self.membership_tokens: list[tuple[str, str | None]] = []

        def fetch_folder_page(
            self,
            account_id: str,
            access_token: str,
            *,
            pagination_token: str | None = None,
        ) -> ApiPage:
            self.folder_tokens.append(pagination_token)
            if pagination_token is None:
                return ApiPage(
                    data=[{"id": "f1", "name": "Research"}],
                    next_token="folder-next",
                )
            return ApiPage(data=[{"id": "f2", "name": "Writing"}])

        def fetch_folder_bookmark_page(
            self,
            account_id: str,
            folder_id: str,
            access_token: str,
            *,
            pagination_token: str | None = None,
            rich: bool = False,
        ) -> ApiPage:
            self.membership_tokens.append((folder_id, pagination_token))
            if folder_id == "f1" and pagination_token is None:
                return ApiPage(data=[post("101", "one")], next_token="member-next")
            return ApiPage(data=[post("102", "two")])

    api = PagedFolderApi()
    SyncEngine(api, now=lambda: NOW).run(paths, access_token="access", folders=True)

    second_frontmatter = yaml.safe_load(
        (paths.bookmarks / "102.md").read_text(encoding="utf-8").split("---", 2)[1]
    )
    assert api.folder_tokens == [None, "folder-next"]
    assert api.membership_tokens == [
        ("f1", None),
        ("f1", "member-next"),
        ("f2", None),
    ]
    assert second_frontmatter["x_folders"] == [
        {"id": "f1", "name": "Research"},
        {"id": "f2", "name": "Writing"},
    ]


def test_sync_engine_requires_collection_account_binding(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    api = FakeApi({None: ApiPage()})

    with pytest.raises(ValueError, match="authenticate"):
        SyncEngine(api, now=lambda: NOW).run(paths, access_token="access")


def test_sync_engine_rejects_pagination_token_cycles_before_committing(tmp_path: Path) -> None:
    paths = prepared_collection(tmp_path)
    paths.jsonl.write_text("existing\n", encoding="utf-8")

    class CyclingApi(FakeApi):
        def fetch_bookmark_page(
            self,
            account_id: str,
            access_token: str,
            *,
            pagination_token: str | None = None,
            rich: bool = False,
        ) -> ApiPage:
            self.bookmark_tokens.append(pagination_token)
            if len(self.bookmark_tokens) > 3:
                raise AssertionError("cycle was not detected")
            next_tokens = {None: "a", "a": "b", "b": "a"}
            return ApiPage(data=[post("101", "one")], next_token=next_tokens[pagination_token])

    api = CyclingApi({})
    with pytest.raises(IncompleteResponseError, match="pagination token cycle"):
        SyncEngine(api, now=lambda: NOW).run(paths, access_token="access")

    assert api.bookmark_tokens == [None, "a", "b"]
    assert paths.jsonl.read_text(encoding="utf-8") == "existing\n"


def test_malformed_success_response_cannot_erase_populated_collection(tmp_path: Path) -> None:
    paths = prepared_collection(tmp_path)
    SyncEngine(
        FakeApi({None: ApiPage(data=[post("101", "keep me")])}),
        now=lambda: NOW,
    ).run(paths, access_token="access")
    original_jsonl = paths.jsonl.read_text(encoding="utf-8")
    original_note = (paths.bookmarks / "101.md").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        api = XApiClient(
            client,
            sleep=lambda seconds: None,
            now=lambda: 0.0,
            jitter=lambda: 0.0,
        )
        with pytest.raises(IncompleteResponseError, match="malformed paginated"):
            SyncEngine(api, now=lambda: NOW).run(paths, access_token="access")

    assert paths.jsonl.read_text(encoding="utf-8") == original_jsonl
    assert (paths.bookmarks / "101.md").read_text(encoding="utf-8") == original_note


def test_missing_post_text_cannot_overwrite_populated_collection(tmp_path: Path) -> None:
    paths = prepared_collection(tmp_path)
    SyncEngine(
        FakeApi({None: ApiPage(data=[post("101", "keep me")])}),
        now=lambda: NOW,
    ).run(paths, access_token="access")
    original_jsonl = paths.jsonl.read_text(encoding="utf-8")
    original_note = (paths.bookmarks / "101.md").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [{"id": "101"}],
                "meta": {"result_count": 1},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        api = XApiClient(
            client,
            sleep=lambda seconds: None,
            now=lambda: 0.0,
            jitter=lambda: 0.0,
        )
        with pytest.raises(IncompleteResponseError, match="malformed post"):
            SyncEngine(api, now=lambda: NOW).run(paths, access_token="access")

    assert paths.jsonl.read_text(encoding="utf-8") == original_jsonl
    assert (paths.bookmarks / "101.md").read_text(encoding="utf-8") == original_note


def test_missing_resumable_page_is_discarded_and_full_scan_restarts(tmp_path: Path) -> None:
    paths = prepared_collection(tmp_path)
    SyncEngine(
        FakeApi({None: ApiPage(data=[post("101", "existing")])}),
        now=lambda: NOW,
    ).run(paths, access_token="access")
    interrupted = FakeApi(
        {
            None: ApiPage(data=[post("102", "staged")], next_token="next"),
            "next": XApiError("interrupted"),
        }
    )
    with pytest.raises(XApiError):
        SyncEngine(interrupted, now=lambda: NOW).run(paths, access_token="access")
    staged_page = next((paths.metadata / "staging" / "bookmarks").glob("*/page-*.json"))
    staged_page.unlink()

    restarted = FakeApi({None: ApiPage(data=[post("101", "still current")])})
    result = SyncEngine(restarted, now=lambda: NOW).run(paths, access_token="access")

    assert restarted.bookmark_tokens == [None]
    assert result.record_count == 1
    assert "still current" in (paths.bookmarks / "101.md").read_text(encoding="utf-8")
    assert not (paths.bookmarks / "102.md").exists()


def test_profile_change_purges_incompatible_staging_across_namespaces(
    tmp_path: Path,
) -> None:
    paths = prepared_collection(tmp_path)
    stale = paths.metadata / "staging" / "folders" / "old-fingerprint"
    stale.mkdir(parents=True)
    (stale / "manifest.json").write_text("{}\n", encoding="utf-8")

    SyncEngine(
        FakeApi({None: ApiPage(data=[post("101", "one")])}),
        now=lambda: NOW,
    ).run(paths, access_token="access", rich=False, folders=False)

    assert not (paths.metadata / "staging").exists()


def test_sync_engine_lock_rejects_concurrent_collection_writer(tmp_path: Path) -> None:
    paths = prepared_collection(tmp_path)
    api = FakeApi({None: ApiPage(data=[post("101", "one")])})

    with (
        portalocker.Lock(paths.metadata / "sync.lock", mode="a", timeout=0),
        pytest.raises(portalocker.LockException),
    ):
        SyncEngine(api, now=lambda: NOW).run(paths, access_token="access")

    assert not (paths.bookmarks / "101.md").exists()


def test_bookmark_resume_accepts_complete_and_terminal_staging(tmp_path: Path) -> None:
    api = FakeApi({})
    engine = SyncEngine(api, now=lambda: NOW)
    complete = SnapshotStager(tmp_path, "complete")
    complete.prepare()
    complete.append_page({"data": [post("101", "one")]}, next_token=None)
    complete.mark_complete()

    engine._fetch_bookmarks(
        complete,
        account_id="42",
        access_token="access",
        rich=False,
    )

    terminal = SnapshotStager(tmp_path, "terminal")
    terminal.prepare()
    terminal.append_page({"data": [post("102", "two")]}, next_token=None)

    engine._fetch_bookmarks(
        terminal,
        account_id="42",
        access_token="access",
        rich=False,
    )

    assert api.bookmark_tokens == []
    assert terminal.complete is True


def test_bookmark_resume_rejects_cycle_already_present_in_staging(tmp_path: Path) -> None:
    stager = SnapshotStager(tmp_path, "fingerprint")
    stager.prepare()
    for token in ("a", "b", "a"):
        stager.append_page(
            {"data": [post("101", "one")], "next_token": token},
            next_token=token,
        )

    with pytest.raises(IncompleteResponseError, match="pagination token cycle"):
        SyncEngine(FakeApi({}), now=lambda: NOW)._fetch_bookmarks(
            stager,
            account_id="42",
            access_token="access",
            rich=False,
        )


def test_folder_resume_reads_an_already_complete_snapshot(tmp_path: Path) -> None:
    stager = SnapshotStager(tmp_path, "fingerprint", namespace="folders")
    stager.prepare()
    stager.append_page(
        {
            "kind": "membership",
            "folder": {"id": "f1", "name": "Research"},
            "page": {"data": [post("101", "one")]},
        },
        next_token=None,
    )
    stager.mark_complete()

    memberships = SyncEngine(FakeApi({}), now=lambda: NOW)._fetch_folders(
        stager,
        account_id="42",
        access_token="access",
    )

    assert memberships == {"101": [{"id": "f1", "name": "Research"}]}


def test_folder_resume_skips_terminal_membership_page_after_crash(tmp_path: Path) -> None:
    stager = SnapshotStager(tmp_path, "fingerprint", namespace="folders")
    stager.prepare()
    stager.append_page(
        {
            "kind": "folders",
            "page": {"data": [{"id": "f1", "name": "Research"}]},
        },
        next_token=None,
    )
    stager.append_page(
        {
            "kind": "membership",
            "folder": {"id": "f1", "name": "Research"},
            "page": {"data": [post("101", "one")]},
        },
        next_token=None,
    )
    stager.set_checkpoint({"phase": "memberships", "folder_index": 0})

    memberships = SyncEngine(FakeApi({}), now=lambda: NOW)._fetch_folders(
        stager,
        account_id="42",
        access_token="access",
    )

    assert stager.complete is True
    assert memberships == {"101": [{"id": "f1", "name": "Research"}]}


def test_folder_resume_accepts_terminal_metadata_page_after_crash(tmp_path: Path) -> None:
    stager = SnapshotStager(tmp_path, "fingerprint", namespace="folders")
    stager.prepare()
    stager.append_page(
        {
            "kind": "folders",
            "page": {"data": [{"id": "f1", "name": "Research"}]},
        },
        next_token=None,
    )
    api = FakeApi(
        {},
        folder_posts={"f1": ApiPage(data=[post("101", "one")])},
    )

    memberships = SyncEngine(api, now=lambda: NOW)._fetch_folders(
        stager,
        account_id="42",
        access_token="access",
    )

    assert memberships == {"101": [{"id": "f1", "name": "Research"}]}


def test_folder_resume_rejects_membership_cycle_in_staging(tmp_path: Path) -> None:
    stager = SnapshotStager(tmp_path, "fingerprint", namespace="folders")
    stager.prepare()
    stager.append_page(
        {
            "kind": "folders",
            "page": {"data": [{"id": "f1", "name": "Research"}]},
        },
        next_token=None,
    )
    for token in ("a", "b", "a"):
        stager.append_page(
            {
                "kind": "membership",
                "folder": {"id": "f1", "name": "Research"},
                "page": {
                    "data": [post("101", "one")],
                    "next_token": token,
                },
            },
            next_token=token,
        )
    stager.set_checkpoint({"phase": "memberships", "folder_index": 0})

    with pytest.raises(IncompleteResponseError, match="folder pagination token cycle"):
        SyncEngine(FakeApi({}), now=lambda: NOW)._fetch_folders(
            stager,
            account_id="42",
            access_token="access",
        )


def test_folder_fetch_rejects_repeated_membership_token(tmp_path: Path) -> None:
    stager = SnapshotStager(tmp_path, "fingerprint", namespace="folders")
    stager.prepare()
    stager.append_page(
        {
            "kind": "folders",
            "page": {"data": [{"id": "f1", "name": "Research"}]},
        },
        next_token=None,
    )
    stager.append_page(
        {
            "kind": "membership",
            "folder": {"id": "f1", "name": "Research"},
            "page": {
                "data": [post("101", "one")],
                "next_token": "same",
            },
        },
        next_token="same",
    )
    stager.set_checkpoint({"phase": "memberships", "folder_index": 0})
    api = FakeApi(
        {},
        folder_posts={
            "f1": ApiPage(
                data=[post("102", "two")],
                next_token="same",
            )
        },
    )

    with pytest.raises(IncompleteResponseError, match="folder pagination token cycle"):
        SyncEngine(api, now=lambda: NOW)._fetch_folders(
            stager,
            account_id="42",
            access_token="access",
        )


def test_folder_resume_rejects_metadata_cycle_in_staging(tmp_path: Path) -> None:
    stager = SnapshotStager(tmp_path, "fingerprint", namespace="folders")
    stager.prepare()
    for token in ("a", "b", "a"):
        stager.append_page(
            {
                "kind": "folders",
                "page": {
                    "data": [{"id": token, "name": token.upper()}],
                    "next_token": token,
                },
            },
            next_token=token,
        )

    with pytest.raises(IncompleteResponseError, match="folder pagination token cycle"):
        SyncEngine(FakeApi({}), now=lambda: NOW)._fetch_folders(
            stager,
            account_id="42",
            access_token="access",
        )


def test_folder_fetch_rejects_repeated_metadata_token(tmp_path: Path) -> None:
    stager = SnapshotStager(tmp_path, "fingerprint", namespace="folders")
    stager.prepare()
    stager.append_page(
        {
            "kind": "folders",
            "page": {
                "data": [{"id": "f1", "name": "Research"}],
                "next_token": "same",
            },
        },
        next_token="same",
    )
    api = FakeApi(
        {},
        folders=ApiPage(
            data=[{"id": "f2", "name": "Writing"}],
            next_token="same",
        ),
    )

    with pytest.raises(IncompleteResponseError, match="folder pagination token cycle"):
        SyncEngine(api, now=lambda: NOW)._fetch_folders(
            stager,
            account_id="42",
            access_token="access",
        )
