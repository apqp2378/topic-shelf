from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from pipeline.url_fetchers.config import RedditFetcherConfig, load_reddit_fetcher_config
from pipeline.url_fetchers.base import TOP_COMMENT_LIMIT, UrlFetchResult
from pipeline.url_fetchers.comment_expander import normalize_comment_nodes
from pipeline.url_fetchers.reddit_parser import (
    extract_post_data,
    extract_post_fullname,
    extract_thread_top_comment_nodes,
    extract_thread_top_comments,
    parse_post_fields,
)


@dataclass(frozen=True)
class RedditPublicJsonFetcher:
    config: RedditFetcherConfig = field(default_factory=load_reddit_fetcher_config)

    user_agent = "topic-shelf-url-ingest/1.0"

    def fetch_thread(self, canonical_url: str) -> UrlFetchResult:
        json_url = build_reddit_json_url(canonical_url)
        payload = self._load_json(json_url)

        if not isinstance(payload, list) or len(payload) < 1:
            raise ValueError("Reddit public JSON response must be a non-empty list.")

        post_data = extract_post_data(payload)
        post_fields = parse_post_fields(post_data)
        top_comment_nodes = extract_thread_top_comment_nodes(payload)
        top_comments = extract_thread_top_comments(payload, limit=self.config.top_comment_limit)
        post_permalink = post_fields.permalink
        post_url = canonical_url
        if post_permalink:
            post_url = build_canonical_reddit_url(post_permalink)

        post_id = post_fields.post_id
        subreddit = post_fields.subreddit
        post_title = post_fields.title

        if not subreddit:
            raise ValueError("Missing subreddit in Reddit public JSON response.")
        if not post_title:
            raise ValueError("Missing post_title in Reddit public JSON response.")
        if not post_url:
            raise ValueError("Missing post_url in Reddit public JSON response.")
        if not post_id:
            raise ValueError("Missing post_id in Reddit public JSON response.")

        return UrlFetchResult(
            canonical_url=canonical_url,
            subreddit=subreddit,
            post_title=post_title,
            post_url=post_url,
            post_author=post_fields.author,
            post_created_utc=post_fields.created_utc,
            post_body=post_fields.body,
            num_comments=post_fields.num_comments,
            upvotes=post_fields.upvotes,
            top_comments=top_comments,
            post_id=post_id,
            fetch_metadata={
                "fetch_mode": "public",
                "comment_fetch_mode": "initial_only",
                "comment_fetch_count": len(top_comment_nodes),
                "comment_fetch_depth": 0,
                "comment_cap": self.config.top_comment_limit,
                "morechildren_enabled": False,
                "morechildren_request_limit": 0,
                "morechildren_max_batches": 0,
                "request_timeout_seconds": self.config.request_timeout_seconds,
                "retry_policy": self.config.retry_policy,
                "expandable_comment_ids_found": [],
                "expandable_comment_ids_requested": [],
                "morechildren_expansion_attempted": False,
                "morechildren_expansion_succeeded": False,
                "ratelimit_snapshot": {},
                "morechildren_ratelimit_snapshot": {},
            },
        )

    def _load_json(self, url: str) -> Any:
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=self.config.request_timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise RuntimeError(f"Reddit request failed with HTTP {exc.code}.") from exc
        except URLError as exc:
            raise RuntimeError(f"Reddit request failed: {exc.reason}.") from exc

        return json.loads(raw_body)


def build_reddit_json_url(canonical_url: str) -> str:
    parts = urlsplit(canonical_url)
    path = parts.path.rstrip("/")
    if not path:
        raise ValueError("Canonical URL path is empty.")
    return urlunsplit((parts.scheme, parts.netloc, f"{path}.json", "", ""))


def build_canonical_reddit_url(path: str) -> str:
    clean_path = path.strip()
    if not clean_path.startswith("/"):
        clean_path = f"/{clean_path}"
    return f"https://reddit.com{clean_path.rstrip('/')}"


def extract_top_comments(payload: list[Any]) -> list[dict[str, object]]:
    return extract_thread_top_comments(payload, limit=TOP_COMMENT_LIMIT)


extract_top_comment_nodes = extract_thread_top_comment_nodes


def normalize_top_comment_nodes(
    top_comment_nodes: list[dict[str, object]],
    limit: int = TOP_COMMENT_LIMIT,
) -> list[dict[str, object]]:
    return normalize_comment_nodes(top_comment_nodes, limit=limit)
