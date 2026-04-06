from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from pipeline.url_fetchers.base import UrlFetchResult
from pipeline.url_fetchers.comment_expander import (
    CommentExpander,
    NoOpCommentExpander,
    CommentThreadSnapshot,
    clean_string,
    coerce_int,
    extract_comment_thread_snapshot,
)
from pipeline.url_fetchers.reddit_public import (
    build_canonical_reddit_url,
    extract_post_data,
    extract_post_fullname,
)
from pipeline.url_fetchers.token_provider import EnvTokenProvider, TokenProvider


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

    def fetch_thread(self, canonical_url: str) -> UrlFetchResult:
        token = self.token_provider.get_token()
        json_url = build_oauth_reddit_json_url(canonical_url)
        payload, ratelimit_snapshot = self._load_json(json_url, token)

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
        # TODO: Expand MoreComments nodes once the richer comment pagination flow exists.
        top_comments = self.comment_expander.expand(comment_snapshot.initial_comment_nodes)

        if not subreddit:
            raise ValueError("Missing subreddit in Reddit OAuth JSON response.")
        if not post_title:
            raise ValueError("Missing post_title in Reddit OAuth JSON response.")
        if not post_url:
            raise ValueError("Missing post_url in Reddit OAuth JSON response.")
        if not post_id:
            raise ValueError("Missing post_id in Reddit OAuth JSON response.")

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
            fetch_metadata={
                "fetch_mode": "oauth",
                "comment_fetch_count": comment_snapshot.comment_fetch_count,
                "comment_fetch_depth": comment_snapshot.comment_fetch_depth,
                "expandable_comment_ids": comment_snapshot.expandable_comment_ids,
                "ratelimit_snapshot": ratelimit_snapshot,
            },
        )

    def _load_json(self, url: str, token: str) -> tuple[Any, dict[str, object]]:
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
                ratelimit_snapshot = extract_rate_limit_snapshot(getattr(exc, "headers", None) or getattr(exc, "hdrs", None))
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if retryable and attempt < self.max_attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise self._format_http_error(exc, url, ratelimit_snapshot) from exc
            except URLError as exc:
                if attempt < self.max_attempts:
                    self._sleep_before_retry(attempt)
                    continue
                raise RuntimeError(f"Reddit OAuth request failed: {exc.reason}.") from exc
            except json.JSONDecodeError as exc:
                raise RuntimeError("Reddit OAuth request returned invalid JSON.") from exc

        raise RuntimeError("Reddit OAuth request failed.")

    def _sleep_before_retry(self, attempt: int) -> None:
        time.sleep(self.backoff_seconds * attempt)

    def _format_http_error(
        self,
        exc: HTTPError,
        url: str,
        ratelimit_snapshot: dict[str, object],
    ) -> RuntimeError:
        snapshot_text = format_ratelimit_snapshot(ratelimit_snapshot)
        if exc.code == 401:
            return RuntimeError(
                "Reddit OAuth request failed with HTTP 401. Check the bearer token and approval state."
            )
        if exc.code == 403:
            return RuntimeError(
                "Reddit OAuth request failed with HTTP 403. The bearer token may lack approval for this thread."
            )
        if exc.code == 404:
            return RuntimeError(f"Reddit OAuth request failed with HTTP 404. Thread not found for {url}.")
        if exc.code == 429:
            return RuntimeError(
                f"Reddit OAuth request rate-limited with HTTP 429 after retries for {url}."
                f" Rate limit snapshot: {snapshot_text}"
            )
        if 500 <= exc.code < 600:
            return RuntimeError(
                f"Reddit OAuth request failed with HTTP {exc.code} after retries for {url}."
                f" Rate limit snapshot: {snapshot_text}"
            )
        return RuntimeError(f"Reddit OAuth request failed with HTTP {exc.code} for {url}.")


def build_oauth_reddit_json_url(canonical_url: str) -> str:
    parts = urlsplit(canonical_url)
    path = parts.path.rstrip("/")
    if not path:
        raise ValueError("Canonical URL path is empty.")
    return urlunsplit(("https", "oauth.reddit.com", f"{path}.json", "", ""))


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
