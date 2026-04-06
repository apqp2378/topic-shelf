from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from pipeline.url_fetchers.base import TOP_COMMENT_LIMIT, UrlFetchResult
from pipeline.url_fetchers.comment_expander import (
    CommentExpander,
    CommentThreadSnapshot,
    NoOpCommentExpander,
    clean_string,
    coerce_int,
    extract_comment_thread_snapshot,
    extract_morechildren_comment_nodes,
    merge_comment_nodes,
)
from pipeline.url_fetchers.reddit_public import (
    build_canonical_reddit_url,
    extract_post_data,
    extract_post_fullname,
)
from pipeline.url_fetchers.token_provider import EnvTokenProvider, TokenProvider

MORECHILDREN_MAX_CHILD_IDS = 5
MORECHILDREN_MAX_BATCHES = 1


class RedditOAuthRequestError(RuntimeError):
    """Request error that preserves a lightweight rate-limit snapshot."""

    def __init__(self, message: str, ratelimit_snapshot: dict[str, object] | None = None):
        super().__init__(message)
        self.ratelimit_snapshot = ratelimit_snapshot or {}


@dataclass(frozen=True)
class MoreChildrenExpansionResult:
    """Result for one bounded MoreComments expansion pass."""

    expanded_comment_nodes: list[dict[str, object]]
    requested_comment_ids: list[str]
    attempted: bool
    succeeded: bool
    error_message: str = ""
    ratelimit_snapshot: dict[str, object] | None = None


@dataclass(frozen=True)
class RedditOAuthFetcher:
    """MVP OAuth fetcher for already-approved bearer tokens.

    The token provider and comment-expander scaffolding are wired in so future
    OAuth work can stay local, but token refresh, approval flow, and deeper
    comment expansion remain intentionally deferred.
    """

    token_provider: TokenProvider = EnvTokenProvider()
    comment_expander: CommentExpander = NoOpCommentExpander()
    timeout_seconds: float = 20.0
    max_attempts: int = 3
    backoff_seconds: float = 0.25
    max_morechildren_child_ids: int = MORECHILDREN_MAX_CHILD_IDS
    max_morechildren_batches: int = MORECHILDREN_MAX_BATCHES

    def fetch_thread(self, canonical_url: str) -> UrlFetchResult:
        token = self.token_provider.get_token()
        thread_url = build_oauth_reddit_json_url(canonical_url)
        payload, thread_ratelimit_snapshot = self._load_json(
            thread_url,
            token,
            request_name="thread",
        )

        if not isinstance(payload, list) or len(payload) < 1:
            raise ValueError("Reddit OAuth JSON response must be a non-empty list.")

        post_data = extract_post_data(payload)
        post_permalink = clean_string(post_data.get("permalink"))
        post_url = canonical_url
        if post_permalink:
            post_url = build_canonical_reddit_url(post_permalink)

        post_id = extract_post_fullname(post_data)
        subreddit = clean_string(post_data.get("subreddit"))
        post_title = clean_string(post_data.get("title"))
        comment_snapshot = extract_comment_snapshot(payload)
        expansion_result = self._expand_morechildren_comments(
            token=token,
            post_id=post_id,
            comment_snapshot=comment_snapshot,
        )
        merged_comments = merge_comment_nodes(
            comment_snapshot.initial_comment_nodes,
            expansion_result.expanded_comment_nodes,
            limit=TOP_COMMENT_LIMIT,
        )
        top_comments = self.comment_expander.expand(merged_comments)

        if not subreddit:
            raise ValueError("Missing subreddit in Reddit OAuth JSON response.")
        if not post_title:
            raise ValueError("Missing post_title in Reddit OAuth JSON response.")
        if not post_url:
            raise ValueError("Missing post_url in Reddit OAuth JSON response.")
        if not post_id:
            raise ValueError("Missing post_id in Reddit OAuth JSON response.")

        fetch_metadata: dict[str, object] = {
            "fetch_mode": "oauth",
            "comment_fetch_mode": (
                "initial_plus_morechildren"
                if expansion_result.attempted and expansion_result.succeeded
                else "initial_plus_morechildren_failed"
                if expansion_result.attempted
                else "initial_only"
            ),
            "comment_fetch_count": comment_snapshot.comment_fetch_count + len(expansion_result.expanded_comment_nodes),
            "comment_fetch_initial_count": comment_snapshot.comment_fetch_count,
            "comment_fetch_depth": 1 if expansion_result.attempted else 0,
            "expandable_comment_ids": comment_snapshot.expandable_comment_ids,
            "expandable_comment_ids_found": comment_snapshot.expandable_comment_ids,
            "expandable_comment_ids_requested": expansion_result.requested_comment_ids,
            "morechildren_expansion_attempted": expansion_result.attempted,
            "morechildren_expansion_succeeded": expansion_result.succeeded,
            "ratelimit_snapshot": thread_ratelimit_snapshot,
            "morechildren_ratelimit_snapshot": expansion_result.ratelimit_snapshot or {},
        }
        if expansion_result.error_message:
            fetch_metadata["morechildren_expansion_error"] = expansion_result.error_message

        return UrlFetchResult(
            canonical_url=canonical_url,
            subreddit=subreddit,
            post_title=post_title,
            post_url=post_url,
            post_author=clean_string(post_data.get("author")) or "[deleted]",
            post_created_utc=coerce_int(post_data.get("created_utc")),
            post_body=clean_string(post_data.get("selftext")),
            num_comments=coerce_int(post_data.get("num_comments")),
            upvotes=coerce_int(post_data.get("ups")) or coerce_int(post_data.get("score")),
            top_comments=top_comments,
            post_id=post_id,
            fetch_metadata=fetch_metadata,
        )

    def _expand_morechildren_comments(
        self,
        token: str,
        post_id: str,
        comment_snapshot: CommentThreadSnapshot,
    ) -> MoreChildrenExpansionResult:
        expandable_comment_ids = comment_snapshot.expandable_comment_ids
        if not expandable_comment_ids or self.max_morechildren_batches < 1:
            return MoreChildrenExpansionResult(
                expanded_comment_nodes=[],
                requested_comment_ids=[],
                attempted=False,
                succeeded=False,
            )

        requested_comment_ids = self._normalize_requested_comment_ids(expandable_comment_ids)
        requested_comment_ids = requested_comment_ids[: self.max_morechildren_child_ids]
        if not requested_comment_ids:
            return MoreChildrenExpansionResult(
                expanded_comment_nodes=[],
                requested_comment_ids=[],
                attempted=False,
                succeeded=False,
            )

        morechildren_url = build_oauth_morechildren_json_url(post_id, requested_comment_ids)

        try:
            payload, ratelimit_snapshot = self._load_json(
                morechildren_url,
                token,
                request_name="morechildren",
            )
            expanded_comment_nodes = extract_morechildren_comment_nodes(payload)
            return MoreChildrenExpansionResult(
                expanded_comment_nodes=expanded_comment_nodes,
                requested_comment_ids=requested_comment_ids,
                attempted=True,
                succeeded=True,
                ratelimit_snapshot=ratelimit_snapshot,
            )
        except RedditOAuthRequestError as exc:
            return MoreChildrenExpansionResult(
                expanded_comment_nodes=[],
                requested_comment_ids=requested_comment_ids,
                attempted=True,
                succeeded=False,
                error_message=str(exc),
                ratelimit_snapshot=exc.ratelimit_snapshot,
            )

    def _load_json(
        self,
        url: str,
        token: str,
        request_name: str,
    ) -> tuple[Any, dict[str, object]]:
        # TODO: Add token refresh and API approval flow before this becomes a full client.
        request = Request(
            url,
            headers={
                "Authorization": f"bearer {token}",
                "User-Agent": "topic-shelf-url-ingest/1.0",
                "Accept": "application/json",
            },
        )

        for attempt in range(1, self.max_attempts + 1):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    raw_body = response.read().decode("utf-8")
                    ratelimit_snapshot = extract_rate_limit_snapshot(getattr(response, "headers", None))
                return json.loads(raw_body), ratelimit_snapshot
            except HTTPError as exc:
                ratelimit_snapshot = extract_rate_limit_snapshot(
                    getattr(exc, "headers", None) or getattr(exc, "hdrs", None)
                )
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if retryable and attempt < self.max_attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise self._format_http_error(exc, url, request_name, ratelimit_snapshot) from exc
            except URLError as exc:
                if attempt < self.max_attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise RedditOAuthRequestError(
                    f"{self._request_label(request_name)}request failed: {exc.reason}.",
                ) from exc
            except json.JSONDecodeError as exc:
                raise RedditOAuthRequestError(
                    f"{self._request_label(request_name)}request returned invalid JSON.",
                ) from exc

        raise RedditOAuthRequestError(f"{self._request_label(request_name)}request failed.")

    def _sleep_before_retry(self, attempt: int) -> None:
        time.sleep(self.backoff_seconds * attempt)

    def _format_http_error(
        self,
        exc: HTTPError,
        url: str,
        request_name: str,
        ratelimit_snapshot: dict[str, object],
    ) -> RedditOAuthRequestError:
        snapshot_text = format_ratelimit_snapshot(ratelimit_snapshot)
        request_label = self._request_label(request_name)
        if exc.code == 401:
            return RedditOAuthRequestError(
                f"{request_label}request failed with HTTP 401. "
                f"Check the bearer token and approval state.",
                ratelimit_snapshot,
            )
        if exc.code == 403:
            return RedditOAuthRequestError(
                f"{request_label}request failed with HTTP 403. "
                f"The bearer token may lack approval for this thread.",
                ratelimit_snapshot,
            )
        if exc.code == 404:
            return RedditOAuthRequestError(
                f"{request_label}request failed with HTTP 404. Thread not found for {url}.",
                ratelimit_snapshot,
            )
        if exc.code == 429:
            return RedditOAuthRequestError(
                f"{request_label}request rate-limited with HTTP 429 after retries for {url}. "
                f"Rate limit snapshot: {snapshot_text}",
                ratelimit_snapshot,
            )
        if 500 <= exc.code < 600:
            return RedditOAuthRequestError(
                f"{request_label}request failed with HTTP {exc.code} after retries for {url}. "
                f"Rate limit snapshot: {snapshot_text}",
                ratelimit_snapshot,
            )
        return RedditOAuthRequestError(
            f"{request_label}request failed with HTTP {exc.code} for {url}.",
            ratelimit_snapshot,
        )

    def _normalize_requested_comment_ids(self, comment_ids: list[str]) -> list[str]:
        normalized_ids: list[str] = []
        for comment_id in comment_ids:
            cleaned = clean_string(comment_id)
            if not cleaned:
                continue
            if cleaned.startswith("t1_"):
                cleaned = cleaned[3:]
            if cleaned not in normalized_ids:
                normalized_ids.append(cleaned)
        return normalized_ids

    def _request_label(self, request_name: str) -> str:
        if request_name == "thread":
            return "Reddit OAuth "
        return f"Reddit OAuth {request_name} "


def build_oauth_reddit_json_url(canonical_url: str) -> str:
    parts = urlsplit(canonical_url)
    path = parts.path.rstrip("/")
    if not path:
        raise ValueError("Canonical URL path is empty.")
    return urlunsplit(("https", "oauth.reddit.com", f"{path}.json", "", ""))


def build_oauth_morechildren_json_url(post_id: str, child_ids: list[str]) -> str:
    normalized_post_id = clean_string(post_id)
    if not normalized_post_id:
        raise ValueError("Post id is required for morechildren requests.")

    normalized_child_ids = [clean_string(child_id) for child_id in child_ids if clean_string(child_id)]
    if not normalized_child_ids:
        raise ValueError("At least one comment id is required for morechildren requests.")

    query_string = urlencode(
        {
            "link_id": normalized_post_id,
            "children": ",".join(normalized_child_ids),
            "api_type": "json",
        }
    )
    return urlunsplit(("https", "oauth.reddit.com", "/api/morechildren", query_string, ""))


def extract_comment_snapshot(payload: list[Any]) -> CommentThreadSnapshot:
    if len(payload) < 2:
        return CommentThreadSnapshot([], [], 0, 0)

    listing = payload[1]
    if not isinstance(listing, dict):
        return CommentThreadSnapshot([], [], 0, 0)

    listing_data = listing.get("data")
    if not isinstance(listing_data, dict):
        return CommentThreadSnapshot([], [], 0, 0)

    children = listing_data.get("children")
    if not isinstance(children, list):
        return CommentThreadSnapshot([], [], 0, 0)

    return extract_comment_thread_snapshot(children)


def extract_rate_limit_snapshot(headers: Any) -> dict[str, object]:
    if headers is None:
        return {}

    getter = getattr(headers, "get", None)
    if not callable(getter):
        return {}

    snapshot: dict[str, object] = {}

    remaining = parse_optional_number(getter("x-ratelimit-remaining"))
    if remaining is not None:
        snapshot["remaining"] = remaining

    reset = parse_optional_number(getter("x-ratelimit-reset"))
    if reset is not None:
        snapshot["reset"] = reset

    used = parse_optional_number(getter("x-ratelimit-used"))
    if used is not None:
        snapshot["used"] = used

    limit = parse_optional_number(getter("x-ratelimit-limit"))
    if limit is not None:
        snapshot["limit"] = limit

    retry_after = parse_optional_number(getter("retry-after"))
    if retry_after is not None:
        snapshot["retry_after"] = retry_after

    return snapshot


def parse_optional_number(value: object) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            number = float(stripped)
        except ValueError:
            return None
        if number.is_integer():
            return int(number)
        return number
    return None


def format_ratelimit_snapshot(snapshot: dict[str, object]) -> str:
    if not snapshot:
        return "{}"
    parts = [f"{key}={value}" for key, value in sorted(snapshot.items())]
    return "{" + ", ".join(parts) + "}"
