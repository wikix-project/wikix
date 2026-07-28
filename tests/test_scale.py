import tracemalloc
from datetime import UTC, datetime
from pathlib import Path

from wikix.api import ApiPage
from wikix.config import bind_account, init_collection
from wikix.sync import SyncEngine


class LargeSyntheticApi:
    def fetch_bookmark_page(
        self,
        account_id: str,
        access_token: str,
        *,
        pagination_token: str | None = None,
        rich: bool = False,
    ) -> ApiPage:
        page_index = int(pagination_token or "0")
        records = []
        for offset in range(100):
            index = page_index * 100 + offset
            post_id = str(10_000_000_000_000_000 + index)
            records.append(
                {
                    "id": post_id,
                    "text": f"Synthetic bookmark {index}",
                    "author_id": f"user-{index % 500}",
                    "created_at": f"2026-07-{(index % 28) + 1:02d}T12:00:00.000Z",
                }
            )
        next_token = str(page_index + 1) if page_index < 249 else None
        return ApiPage(data=records, next_token=next_token)


def test_25000_record_sync_pipeline_uses_bounded_memory(tmp_path: Path) -> None:
    paths = init_collection(tmp_path / "collection", client_id="client")
    bind_account(paths.root, "42")
    tracemalloc.start()

    result = SyncEngine(
        LargeSyntheticApi(),  # type: ignore[arg-type]
        now=lambda: datetime(2026, 7, 28, 12, tzinfo=UTC),
    ).run(paths, access_token="access")

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    with paths.jsonl.open(encoding="utf-8") as handle:
        line_count = sum(1 for _ in handle)
    markdown_count = sum(1 for _ in paths.bookmarks.iterdir())
    assert result.record_count == 25_000
    assert line_count == 25_000
    assert markdown_count == 25_000
    assert not (paths.metadata / "staging").exists()
    assert peak < 128 * 1024 * 1024
