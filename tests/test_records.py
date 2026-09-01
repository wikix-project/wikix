import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from wikix.records import (
    BookmarkRecordV1,
    MediaRecord,
    ReferencedPostRecord,
    ReferenceRecord,
    normalize_pages,
    render_markdown,
    write_jsonl,
)


def rich_page() -> dict[str, object]:
    return {
        "data": [
            {
                "id": "200",
                "text": "Literal *markdown* and `code`\nhttps://t.co/a",
                "author_id": "u1",
                "created_at": "2026-07-27T12:00:00.000Z",
                "lang": "en",
                "conversation_id": "c1",
                "entities": {
                    "urls": [
                        {
                            "url": "https://t.co/a",
                            "expanded_url": "https://example.com/article",
                            "display_url": "example.com/article",
                        }
                    ]
                },
                "attachments": {"media_keys": ["m1"]},
                "referenced_tweets": [{"type": "quoted", "id": "100"}],
            }
        ],
        "includes": {
            "users": [{"id": "u1", "name": "Author", "username": "author"}],
            "media": [
                {
                    "media_key": "m1",
                    "type": "photo",
                    "url": "https://pbs.twimg.com/media/example.jpg",
                    "alt_text": "A useful diagram",
                }
            ],
            "tweets": [
                {
                    "id": "100",
                    "text": "Referenced post truncated…",
                    "note_tweet": {"text": "Complete referenced long-form post"},
                    "author_id": "u2",
                    "created_at": "2026-07-26T12:00:00.000Z",
                }
            ],
        },
    }


def test_normalize_rich_page_preserves_exact_text_and_related_resources() -> None:
    records = list(
        normalize_pages(
            [rich_page()],
            account_id="42",
            profile="rich",
            synced_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
            folder_memberships={
                "200": [{"id": "f1", "name": "Research"}],
            },
        )
    )

    assert len(records) == 1
    record = records[0]
    assert record.text == "Literal *markdown* and `code`\nhttps://t.co/a"
    assert record.source_url == "https://x.com/i/web/status/200"
    assert record.author is not None
    assert record.author.username == "author"
    assert record.media[0].alt_text == "A useful diagram"
    assert record.references[0].post is not None
    assert record.references[0].post.text == "Complete referenced long-form post"
    assert record.folders[0].name == "Research"


def test_normalize_lean_page_keeps_ids_without_expanded_objects() -> None:
    page = rich_page()
    page["includes"] = {}

    record = next(
        normalize_pages(
            [page],
            account_id="42",
            profile="lean",
            synced_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
        )
    )

    assert record.author is None
    assert record.media[0].media_key == "m1"
    assert record.media[0].url is None
    assert record.references[0].post is None


def test_normalize_uses_full_note_post_text_and_entities_when_present() -> None:
    page = {
        "data": [
            {
                "id": "300",
                "text": "Truncated…",
                "note_tweet": {
                    "text": "The complete long-form post text.",
                    "entities": {"urls": [{"url": "https://t.co/full"}]},
                },
            }
        ]
    }

    record = next(
        normalize_pages(
            [page],
            account_id="42",
            profile="lean",
            synced_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
        )
    )

    assert record.text == "The complete long-form post text."
    assert record.entities == {"urls": [{"url": "https://t.co/full"}]}


def test_render_markdown_has_versioned_frontmatter_and_safe_literal_text() -> None:
    record = next(
        normalize_pages(
            [rich_page()],
            account_id="42",
            profile="rich",
            synced_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
        )
    )

    markdown = render_markdown(record, personal_notes="My own annotation.\n")
    frontmatter = yaml.safe_load(markdown.split("---", 2)[1])

    assert set(frontmatter) == {
        "schema_version",
        "profile",
        "x_account_id",
        "x_post_id",
        "x_author_id",
        "source_url",
        "created_at",
        "synced_at",
        "language",
        "conversation_id",
        "in_reply_to_user_id",
        "references",
        "media_keys",
        "x_author",
        "x_media",
        "x_referenced_posts",
    }
    assert frontmatter["schema_version"] == 1
    assert frontmatter["profile"] == "rich"
    assert frontmatter["in_reply_to_user_id"] is None
    assert frontmatter["x_post_id"] == "200"
    assert frontmatter["x_author"]["username"] == "author"
    assert frontmatter["x_media"][0]["alt_text"] == "A useful diagram"
    assert (
        frontmatter["x_referenced_posts"][0]["post"]["text"] == "Complete referenced long-form post"
    )
    assert "```text\nLiteral *markdown* and `code`\nhttps://t.co/a\n```" in markdown
    assert "[example.com/article](<https://example.com/article>)" in markdown
    assert "```text\nComplete referenced long-form post\n```" in markdown
    assert "<!-- wikix:notes:start -->\nMy own annotation.\n<!-- wikix:notes:end -->" in markdown


def test_render_markdown_keeps_remote_metadata_inert() -> None:
    referenced_text = "<img src=https://tracker.example/pixel>\n![[Private Note]]"
    record = BookmarkRecordV1(
        profile="rich",
        account_id="42",
        post_id="200",
        source_url="https://x.com/i/web/status/200",
        text="Primary post",
        synced_at="2026-07-28T12:00:00Z",
        entities={
            "urls": [
                {
                    "expanded_url": "javascript:alert(1)",
                    "display_url": "unsafe[]_*",
                }
            ]
        },
        references=[
            ReferenceRecord(
                type="quoted",
                id="201",
                post=ReferencedPostRecord(id="201", text=referenced_text),
            )
        ],
        media=[
            MediaRecord(
                media_key="m1",
                alt_text="diagram[]_*",
                url="../private-note",
            )
        ],
    )

    markdown = render_markdown(record)

    assert f"```text\n{referenced_text}\n```" in markdown
    links_section = markdown.split("## Links\n\n", 1)[1].split("\n\n## Media", 1)[0]
    media_section = markdown.split("## Media\n\n", 1)[1].split(
        "\n\n## Direct references",
        1,
    )[0]
    assert links_section == "- unsafe\\[\\]\\_\\*"
    assert media_section == "- diagram\\[\\]\\_\\*"
    assert "](<javascript:" not in markdown
    assert "](<../private-note>)" not in markdown
    assert record.entities["urls"][0]["expanded_url"] == "javascript:alert(1)"
    assert record.media[0].url == "../private-note"


@pytest.mark.parametrize("control_character", ["\t", "\x1b", "\x7f"])
def test_render_markdown_does_not_link_urls_with_control_characters(
    control_character: str,
) -> None:
    unsafe_url = f"https://example.com/{control_character}private"
    record = BookmarkRecordV1(
        profile="lean",
        account_id="42",
        post_id="200",
        source_url="https://x.com/i/web/status/200",
        text="Primary post",
        synced_at="2026-07-28T12:00:00Z",
        entities={
            "urls": [
                {
                    "expanded_url": unsafe_url,
                    "display_url": "unsafe link",
                }
            ]
        },
    )

    markdown = render_markdown(record)

    assert "## Links\n\n- unsafe link" in markdown
    assert f"](<{unsafe_url}>)" not in markdown


def test_render_markdown_normalizes_personal_note_trailing_newline() -> None:
    record = BookmarkRecordV1(
        account_id="42",
        profile="lean",
        post_id="100",
        source_url="https://x.com/i/web/status/100",
        text="saved",
        synced_at="2026-07-28T12:00:00Z",
    )

    markdown = render_markdown(record, personal_notes="No trailing newline")

    assert ("<!-- wikix:notes:start -->\nNo trailing newline\n<!-- wikix:notes:end -->") in markdown


def test_write_jsonl_atomically_sorts_newest_first(tmp_path: Path) -> None:
    older = BookmarkRecordV1(
        account_id="42",
        profile="lean",
        post_id="100",
        source_url="https://x.com/i/web/status/100",
        text="older",
        created_at="2026-07-26T12:00:00.000Z",
        synced_at="2026-07-28T12:00:00Z",
    )
    newer = older.model_copy(
        update={
            "post_id": "200",
            "source_url": "https://x.com/i/web/status/200",
            "text": "newer",
            "created_at": "2026-07-27T12:00:00.000Z",
        }
    )
    output = tmp_path / "bookmarks.jsonl"

    write_jsonl(output, [older, newer], chunk_size=1)

    lines = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [line["post_id"] for line in lines] == ["200", "100"]
    assert set(lines[0]) == set(BookmarkRecordV1.model_fields)
    assert lines[0]["author_id"] is None
    assert not (tmp_path / ".bookmarks.jsonl.tmp").exists()


def test_bookmark_record_rejects_non_decimal_post_id_before_it_reaches_a_filename() -> None:
    with pytest.raises(ValidationError, match="post_id"):
        BookmarkRecordV1(
            profile="lean",
            account_id="42",
            post_id="../../outside",
            source_url="https://x.com/i/web/status/invalid",
            text="malformed remote record",
            synced_at="2026-07-28T12:00:00Z",
        )


def test_normalize_rejects_post_without_any_valid_text() -> None:
    with pytest.raises(ValueError, match="valid text"):
        next(
            normalize_pages(
                [{"data": [{"id": "300"}]}],
                account_id="42",
                profile="lean",
                synced_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
            )
        )


def test_jsonl_chunk_size_must_be_positive(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="positive"):
        write_jsonl(tmp_path / "bookmarks.jsonl", [], chunk_size=0)
