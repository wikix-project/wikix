"""Official X API transport."""

import random
import time
from collections.abc import Callable
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field


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
        if not isinstance(data, dict) or "id" not in data:
            raise IncompleteResponseError("authenticated user response did not include an id")
        return str(data["id"])

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
        return self._page(payload, item_kind="post")

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
        item_kind: Literal["post", "folder"],
    ) -> ApiPage:
        data = payload.get("data", [])
        includes = payload.get("includes", {})
        meta = payload.get("meta")
        result_count = meta.get("result_count") if isinstance(meta, dict) else None
        next_token = meta.get("next_token") if isinstance(meta, dict) else None
        if (
            not isinstance(data, list)
            or not isinstance(includes, dict)
            or not isinstance(meta, dict)
            or not isinstance(result_count, int)
            or isinstance(result_count, bool)
            or result_count < 0
            or result_count != len(data)
            or (next_token is not None and (not isinstance(next_token, str) or not next_token))
        ):
            raise IncompleteResponseError("X returned a malformed paginated response")
        validator = XApiClient._valid_post if item_kind == "post" else XApiClient._valid_folder
        if not all(validator(item) for item in data):
            raise IncompleteResponseError(f"X returned a malformed {item_kind} record")
        return ApiPage(
            data=data,
            includes=includes,
            next_token=next_token,
        )

    @staticmethod
    def _valid_post(item: object) -> bool:
        if not isinstance(item, dict):
            return False
        post_id = item.get("id")
        text = item.get("text")
        if not isinstance(post_id, str) or not post_id.isdecimal() or not isinstance(text, str):
            return False
        for field in (
            "author_id",
            "conversation_id",
            "created_at",
            "in_reply_to_user_id",
            "lang",
        ):
            if field in item and not isinstance(item[field], str):
                return False
        if "entities" in item and not isinstance(item["entities"], dict):
            return False
        note_post = item.get("note_tweet")
        if note_post is not None and (
            not isinstance(note_post, dict)
            or not isinstance(note_post.get("text"), str)
            or ("entities" in note_post and not isinstance(note_post["entities"], dict))
        ):
            return False
        attachments = item.get("attachments")
        if attachments is not None and (
            not isinstance(attachments, dict)
            or not isinstance(attachments.get("media_keys", []), list)
            or not all(
                isinstance(media_key, str) for media_key in attachments.get("media_keys", [])
            )
        ):
            return False
        references = item.get("referenced_tweets")
        return references is None or (
            isinstance(references, list)
            and all(
                isinstance(reference, dict)
                and isinstance(reference.get("id"), str)
                and str(reference["id"]).isdecimal()
                and isinstance(reference.get("type"), str)
                for reference in references
            )
        )

    @staticmethod
    def _valid_folder(item: object) -> bool:
        return (
            isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and bool(item["id"])
            and isinstance(item.get("name"), str)
        )

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
                payload: dict[str, Any] = response.json()
            except ValueError as error:
                raise IncompleteResponseError("X returned non-JSON data") from error
            if payload.get("errors"):
                raise IncompleteResponseError(f"X returned partial errors: {payload['errors']}")
            return payload

    def _backoff(self, attempt: int) -> float:
        return min(float(2**attempt), 30.0) + self._jitter()


def default_api_client(client: httpx.Client) -> XApiClient:
    """Build the production transport with real time and sleep functions."""
    return XApiClient(client, sleep=time.sleep, now=time.time, jitter=random.random)
