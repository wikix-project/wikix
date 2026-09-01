"""Official X API transport."""

import random
import time
from collections.abc import Callable
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

PageKind = Literal["post", "folder", "membership"]


class XApiError(RuntimeError):
    """Raised when X rejects a request."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class IncompleteResponseError(XApiError):
    """Raised when X returns partial data that cannot be reconciled safely."""


class ApiPage(BaseModel):
    data: list[dict[str, Any]] = Field(default_factory=list)
    includes: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    next_token: str | None = None


def validate_normalized_page(
    payload: object,
    *,
    item_kind: PageKind,
) -> None:
    """Validate fields retained in an ApiPage or staging file."""
    if not isinstance(payload, dict):
        raise IncompleteResponseError("X returned a malformed paginated response")
    data = payload.get("data")
    includes = payload.get("includes", {})
    next_token = payload.get("next_token")
    if (
        not isinstance(data, list)
        or not isinstance(includes, dict)
        or ("next_token" in payload and (not isinstance(next_token, str) or not next_token))
    ):
        raise IncompleteResponseError("X returned a malformed paginated response")
    validators = {
        "post": _valid_post,
        "folder": _valid_folder,
        "membership": _valid_membership,
    }
    validator = validators[item_kind]
    if not all(validator(item) for item in data):
        raise IncompleteResponseError(f"X returned a malformed {item_kind} record")
    if item_kind == "post" and not _valid_includes(includes):
        raise IncompleteResponseError("X returned malformed post includes")


def _valid_post(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    post_id = item.get("id")
    text = item.get("text")
    if not _is_ascii_decimal(post_id) or not isinstance(text, str):
        return False
    for field in ("created_at", "lang"):
        if field in item and not isinstance(item[field], str):
            return False
    for field in (
        "author_id",
        "conversation_id",
        "in_reply_to_user_id",
    ):
        if field in item and not _is_ascii_decimal(item[field]):
            return False
    if "entities" in item and not _valid_entities(item["entities"]):
        return False
    note_post = item.get("note_tweet")
    if note_post is not None and (
        not isinstance(note_post, dict)
        or not isinstance(note_post.get("text"), str)
        or ("entities" in note_post and not _valid_entities(note_post["entities"]))
    ):
        return False
    attachments = item.get("attachments")
    if attachments is not None and (
        not isinstance(attachments, dict)
        or not isinstance(attachments.get("media_keys", []), list)
        or not all(isinstance(media_key, str) for media_key in attachments.get("media_keys", []))
    ):
        return False
    references = item.get("referenced_tweets")
    return references is None or (
        isinstance(references, list)
        and all(
            isinstance(reference, dict)
            and _is_ascii_decimal(reference.get("id"))
            and isinstance(reference.get("type"), str)
            for reference in references
        )
    )


def _valid_folder(item: object) -> bool:
    return (
        isinstance(item, dict)
        and _is_ascii_decimal(item.get("id"))
        and isinstance(item.get("name"), str)
    )


def _valid_membership(item: object) -> bool:
    return isinstance(item, dict) and _is_ascii_decimal(item.get("id"))


def _valid_entities(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    urls = value.get("urls", [])
    return isinstance(urls, list) and all(
        isinstance(item, dict)
        and all(
            field not in item or isinstance(item[field], str)
            for field in ("url", "expanded_url", "display_url")
        )
        for item in urls
    )


def _valid_includes(includes: dict[str, object]) -> bool:
    if not all(
        isinstance(key, str)
        and isinstance(items, list)
        and all(isinstance(item, dict) for item in items)
        for key, items in includes.items()
    ):
        return False
    users = includes.get("users", [])
    media = includes.get("media", [])
    tweets = includes.get("tweets", [])
    return (
        isinstance(users, list)
        and all(_valid_user(item) for item in users)
        and isinstance(media, list)
        and all(_valid_media(item) for item in media)
        and isinstance(tweets, list)
        and all(_valid_post(item) for item in tweets)
    )


def _valid_user(item: object) -> bool:
    return (
        isinstance(item, dict)
        and _is_ascii_decimal(item.get("id"))
        and all(field not in item or isinstance(item[field], str) for field in ("name", "username"))
    )


def _valid_media(item: object) -> bool:
    if (
        not isinstance(item, dict)
        or not isinstance(item.get("media_key"), str)
        or not item["media_key"]
    ):
        return False
    if not all(
        field not in item or isinstance(item[field], str)
        for field in ("type", "url", "preview_image_url", "alt_text")
    ):
        return False
    return all(
        field not in item or (isinstance(item[field], int) and not isinstance(item[field], bool))
        for field in ("duration_ms", "height", "width")
    )


class XApiClient:
    def __init__(
        self,
        client: httpx.Client,
        *,
        sleep: Callable[[float], None],
        now: Callable[[], float],
        jitter: Callable[[], float],
        max_attempts: int = 3,
    ) -> None:
        self._client = client
        self._sleep = sleep
        self._now = now
        self._jitter = jitter
        self._max_attempts = max_attempts

    def get_me(self, access_token: str) -> str:
        payload = self._request_json(
            "GET",
            "https://api.x.com/2/users/me",
            access_token=access_token,
        )
        data = payload.get("data")
        account_id = data.get("id") if isinstance(data, dict) else None
        if not _is_ascii_decimal(account_id):
            raise IncompleteResponseError("authenticated user response did not include a valid id")
        assert isinstance(account_id, str)
        return account_id

    def fetch_bookmark_page(
        self,
        account_id: str,
        access_token: str,
        *,
        pagination_token: str | None = None,
        rich: bool = False,
    ) -> ApiPage:
        params = self._post_params(pagination_token=pagination_token, rich=rich)
        payload = self._request_json(
            "GET",
            f"https://api.x.com/2/users/{account_id}/bookmarks",
            access_token=access_token,
            params=params,
        )
        return self._page(payload, item_kind="post")

    def fetch_folder_page(
        self,
        account_id: str,
        access_token: str,
        *,
        pagination_token: str | None = None,
    ) -> ApiPage:
        params = {"max_results": "100"}
        if pagination_token is not None:
            params["pagination_token"] = pagination_token
        payload = self._request_json(
            "GET",
            f"https://api.x.com/2/users/{account_id}/bookmarks/folders",
            access_token=access_token,
            params=params,
        )
        return self._page(payload, item_kind="folder")

    def fetch_folder_bookmark_page(
        self,
        account_id: str,
        folder_id: str,
        access_token: str,
        *,
        pagination_token: str | None = None,
        rich: bool = False,
    ) -> ApiPage:
        params = self._post_params(pagination_token=pagination_token, rich=rich)
        payload = self._request_json(
            "GET",
            f"https://api.x.com/2/users/{account_id}/bookmarks/folders/{folder_id}",
            access_token=access_token,
            params=params,
        )
        return self._page(payload, item_kind="membership")

    @staticmethod
    def _post_params(*, pagination_token: str | None, rich: bool) -> dict[str, str]:
        params = {
            "max_results": "100",
            "tweet.fields": (
                "attachments,author_id,conversation_id,created_at,entities,"
                "in_reply_to_user_id,lang,note_tweet,referenced_tweets"
            ),
        }
        if pagination_token is not None:
            params["pagination_token"] = pagination_token
        if rich:
            params.update(
                {
                    "expansions": (
                        "author_id,attachments.media_keys,referenced_tweets.id,"
                        "referenced_tweets.id.author_id"
                    ),
                    "user.fields": "id,name,username",
                    "media.fields": (
                        "media_key,type,url,preview_image_url,alt_text,duration_ms,height,width"
                    ),
                }
            )
        return params

    @staticmethod
    def _page(
        payload: dict[str, Any],
        *,
        item_kind: PageKind,
    ) -> ApiPage:
        data = payload.get("data", [])
        includes = payload.get("includes", {})
        meta = payload.get("meta")
        result_count = meta.get("result_count") if isinstance(meta, dict) else None
        next_token = meta.get("next_token") if isinstance(meta, dict) else None
        count_is_valid = (
            isinstance(data, list)
            and isinstance(result_count, int)
            and not isinstance(result_count, bool)
            and result_count >= 0
            and result_count == len(data)
        )
        if (
            not isinstance(meta, dict)
            or (item_kind == "post" and not count_is_valid)
            or (item_kind != "post" and result_count is not None and not count_is_valid)
        ):
            raise IncompleteResponseError("X returned a malformed paginated response")
        normalized_page = {
            "data": data,
            "includes": includes,
        }
        if next_token is not None:
            normalized_page["next_token"] = next_token
        validate_normalized_page(normalized_page, item_kind=item_kind)
        return ApiPage(**normalized_page)

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        access_token: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        failure_attempt = 0
        while True:
            try:
                response = self._client.request(
                    method,
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            except httpx.RequestError as error:
                if failure_attempt + 1 == self._max_attempts:
                    raise XApiError(f"X request failed after retries: {error}") from error
                self._sleep(self._backoff(failure_attempt))
                failure_attempt += 1
                continue

            if response.status_code == 429:
                current_time = self._now()
                try:
                    reset = float(response.headers.get("x-rate-limit-reset", current_time + 60))
                except ValueError:
                    reset = current_time + 60
                self._sleep(max(reset - current_time, 1.0))
                continue
            if response.status_code >= 500 and failure_attempt + 1 < self._max_attempts:
                self._sleep(self._backoff(failure_attempt))
                failure_attempt += 1
                continue
            if response.status_code >= 400:
                detail = response.text[:500]
                raise XApiError(
                    f"X API returned HTTP {response.status_code}: {detail}",
                    status_code=response.status_code,
                )

            try:
                payload: Any = response.json()
            except ValueError as error:
                raise IncompleteResponseError("X returned non-JSON data") from error
            if not isinstance(payload, dict):
                raise IncompleteResponseError("X returned JSON data that was not a JSON object")
            if payload.get("errors"):
                raise IncompleteResponseError(f"X returned partial errors: {payload['errors']}")
            return payload

    def _backoff(self, attempt: int) -> float:
        return min(float(2**attempt), 30.0) + self._jitter()


def default_api_client(client: httpx.Client) -> XApiClient:
    """Build the production transport with real time and sleep functions."""
    return XApiClient(client, sleep=time.sleep, now=time.time, jitter=random.random)


def _is_ascii_decimal(value: object) -> bool:
    return isinstance(value, str) and value.isascii() and value.isdecimal()
