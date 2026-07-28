from collections.abc import Callable
from urllib.parse import parse_qs

import httpx
import pytest

from wikix.api import IncompleteResponseError, XApiClient, XApiError, default_api_client


def client_with(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    sleeps: list[float] | None = None,
    now: float = 100.0,
    jitter: Callable[[], float] = lambda: 0.0,
) -> tuple[httpx.Client, XApiClient]:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    sleep_values = sleeps if sleeps is not None else []
    return http, XApiClient(
        http,
        sleep=sleep_values.append,
        now=lambda: now,
        jitter=jitter,
        max_attempts=3,
    )


def test_get_me_returns_authenticated_account_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer access"
        return httpx.Response(200, json={"data": {"id": "42"}})

    http, api = client_with(handler)
    with http:
        assert api.get_me("access") == "42"


def test_default_api_client_uses_the_production_transport_factory() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"id": "42"}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        assert default_api_client(http).get_me("access") == "42"


def test_fetch_bookmark_page_uses_lean_fields_and_pagination() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "data": [{"id": "1", "text": "hello"}],
                "meta": {"result_count": 1, "next_token": "next"},
            },
        )

    http, api = client_with(handler)
    with http:
        page = api.fetch_bookmark_page("42", "access", pagination_token="current", rich=False)

    query = parse_qs(captured[0].url.query.decode())
    assert captured[0].url.path == "/2/users/42/bookmarks"
    assert query["max_results"] == ["100"]
    assert query["pagination_token"] == ["current"]
    assert "author_id" in query["tweet.fields"][0]
    assert "note_tweet" in query["tweet.fields"][0]
    assert "expansions" not in query
    assert page.next_token == "next"
    assert page.data[0]["id"] == "1"


def test_fetch_bookmark_page_adds_rich_expansions() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"data": [], "meta": {"result_count": 0}})

    http, api = client_with(handler)
    with http:
        api.fetch_bookmark_page("42", "access", rich=True)

    query = parse_qs(captured[0].url.query.decode())
    assert set(query["expansions"][0].split(",")) == {
        "author_id",
        "attachments.media_keys",
        "referenced_tweets.id",
        "referenced_tweets.id.author_id",
    }
    assert "alt_text" in query["media.fields"][0]
    assert "username" in query["user.fields"][0]


def test_api_retries_server_errors_and_honors_rate_limit_reset() -> None:
    responses = [
        httpx.Response(500, json={"title": "server"}),
        httpx.Response(429, headers={"x-rate-limit-reset": "110"}, json={"title": "rate"}),
        httpx.Response(200, json={"data": {"id": "42"}}),
    ]
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    http, api = client_with(handler, sleeps=sleeps, now=100.0)
    with http:
        assert api.get_me("access") == "42"

    assert sleeps == [1.0, 10.0]


def test_api_rejects_partial_or_forbidden_responses_without_retry() -> None:
    calls = 0

    def partial_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [{"id": "1", "text": "partial"}],
                "errors": [{"detail": "missing post"}],
            },
        )

    partial_http, partial_api = client_with(partial_handler)
    with partial_http, pytest.raises(IncompleteResponseError):
        partial_api.fetch_bookmark_page("42", "access")

    def forbidden_handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(403, json={"detail": "forbidden"})

    forbidden_http, forbidden_api = client_with(forbidden_handler)
    with forbidden_http, pytest.raises(XApiError) as captured:
        forbidden_api.get_me("access")
    assert calls == 1
    assert captured.value.status_code == 403


def test_fetch_folders_and_folder_page() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.endswith("/folders"):
            return httpx.Response(
                200,
                json={
                    "data": [{"id": "f1", "name": "Research"}],
                    "meta": {"result_count": 1},
                },
            )
        return httpx.Response(
            200,
            json={
                "data": [{"id": "1", "text": "saved"}],
                "meta": {"result_count": 1},
            },
        )

    http, api = client_with(handler)
    with http:
        folders = api.fetch_folder_page("42", "access")
        posts = api.fetch_folder_bookmark_page("42", "f1", "access")

    assert folders.data == [{"id": "f1", "name": "Research"}]
    assert posts.data[0]["id"] == "1"
    assert paths == [
        "/2/users/42/bookmarks/folders",
        "/2/users/42/bookmarks/folders/f1",
    ]


def test_api_rejects_missing_account_id_and_malformed_pages() -> None:
    responses = [
        httpx.Response(200, json={"data": {}}),
        httpx.Response(200, json={"data": {}, "meta": {"result_count": 0}}),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    http, api = client_with(handler)
    with http:
        with pytest.raises(IncompleteResponseError, match="include an id"):
            api.get_me("access")
        with pytest.raises(IncompleteResponseError, match="malformed paginated"):
            api.fetch_bookmark_page("42", "access")


def test_api_rejects_empty_object_instead_of_treating_it_as_an_empty_snapshot() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    http, api = client_with(handler)
    with http, pytest.raises(IncompleteResponseError, match="malformed paginated"):
        api.fetch_bookmark_page("42", "access")


@pytest.mark.parametrize(
    "bad_post",
    [
        "not-an-object",
        {"id": "1", "text": "post", "author_id": 42},
        {"id": "1", "text": "post", "entities": []},
        {"id": "1", "text": "post", "note_tweet": {"text": 42}},
        {"id": "1", "text": "post", "attachments": {"media_keys": [42]}},
        {"id": "1", "text": "post", "referenced_tweets": [{"id": "bad", "type": "quoted"}]},
    ],
)
def test_api_rejects_malformed_fields_in_individual_posts(bad_post: object) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [bad_post], "meta": {"result_count": 1}},
        )

    http, api = client_with(handler)
    with http, pytest.raises(IncompleteResponseError, match="malformed post"):
        api.fetch_bookmark_page("42", "access")


def test_api_rejects_non_json_success_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>not JSON</html>")

    http, api = client_with(handler)
    with http, pytest.raises(IncompleteResponseError, match="non-JSON"):
        api.get_me("access")


def test_api_retries_network_errors_then_fails_actionably() -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("offline", request=request)

    http, api = client_with(handler, sleeps=sleeps)
    with http, pytest.raises(XApiError, match="failed after retries"):
        api.get_me("access")

    assert calls == 3
    assert sleeps == [1.0, 2.0]


def test_rate_limits_do_not_consume_transient_failure_retry_budget() -> None:
    responses = [
        httpx.Response(429, headers={"x-rate-limit-reset": "101"}),
        httpx.Response(429, headers={"x-rate-limit-reset": "101"}),
        httpx.Response(429, headers={"x-rate-limit-reset": "101"}),
        httpx.Response(200, json={"data": {"id": "42"}}),
    ]
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    http, api = client_with(handler, sleeps=sleeps, now=100.0)
    with http:
        assert api.get_me("access") == "42"

    assert sleeps == [1.0, 1.0, 1.0]


def test_transient_backoff_includes_injected_jitter() -> None:
    responses = [
        httpx.Response(503),
        httpx.Response(200, json={"data": {"id": "42"}}),
    ]
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    http, api = client_with(handler, sleeps=sleeps, jitter=lambda: 0.25)
    with http:
        assert api.get_me("access") == "42"

    assert sleeps == [1.25]


def test_invalid_rate_limit_reset_header_uses_safe_default_wait() -> None:
    responses = [
        httpx.Response(429, headers={"x-rate-limit-reset": "not-a-number"}),
        httpx.Response(200, json={"data": {"id": "42"}}),
    ]
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    http, api = client_with(handler, sleeps=sleeps, now=100.0)
    with http:
        assert api.get_me("access") == "42"

    assert sleeps == [60.0]


def test_folder_pagination_token_is_forwarded() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"data": [], "meta": {"result_count": 0}})

    http, api = client_with(handler)
    with http:
        api.fetch_folder_page("42", "access", pagination_token="next-folder")

    assert parse_qs(captured[0].url.query.decode())["pagination_token"] == ["next-folder"]
