from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from pipeline.url_fetchers.comment_expander import (
    cap_comments,
    clean_string,
    coerce_int,
    normalize_comment_node,
)
from pipeline.url_fetchers.config import RedditFetcherConfig, load_reddit_fetcher_config
from pipeline.url_fetchers.base import TOP_COMMENT_LIMIT, UrlFetchResult


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
        top_comment_nodes = extract_top_comment_nodes(payload)
        top_comments = normalize_top_comment_nodes(top_comment_nodes, limit=self.config.top_comment_limit)
        post_permalink = clean_string(post_data.get("permalink"))
        post_url = canonical_url
        if post_permalink:
            post_url = build_canonical_reddit_url(post_permalink)

        post_id = extract_post_fullname(post_data)
        subreddit = clean_string(post_data.get("subreddit"))
        post_title = clean_string(post_data.get("title"))

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
            post_author=clean_string(post_data.get("author")) or "[deleted]",
            post_created_utc=coerce_int(post_data.get("created_utc")),
            post_body=clean_string(post_data.get("selftext")),
            num_comments=coerce_int(post_data.get("num_comments")),
            upvotes=coerce_int(post_data.get("ups")),
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


def extract_post_data(payload: list[Any]) -> dict[str, Any]:
    listing = payload[0]
    if not isinstance(listing, dict):
        raise ValueError("Reddit post listing is not an object.")

    listing_data = listing.get("data")
    if not isinstance(listing_data, dict):
        raise ValueError("Reddit post listing is missing data.")

    children = listing_data.get("children")
    if not isinstance(children, list) or not children:
        raise ValueError("Reddit post listing has no children.")

    first_child = children[0]
    if not isinstance(first_child, dict):
        raise ValueError("Reddit post child is not an object.")

    post_data = first_child.get("data")
    if not isinstance(post_data, dict):
        raise ValueError("Reddit post child is missing data.")

    return post_data


def extract_top_comments(payload: list[Any]) -> list[dict[str, object]]:
    return cap_comments(normalize_top_comment_nodes(extract_top_comment_nodes(payload)), limit=TOP_COMMENT_LIMIT)


def extract_top_comment_nodes(payload: list[Any]) -> list[dict[str, object]]:
    if len(payload) < 2:
        return []

    listing = payload[1]
    if not isinstance(listing, dict):
        return []

    listing_data = listing.get("data")
    if not isinstance(listing_data, dict):
        return []

    children = listing_data.get("children")
    if not isinstance(children, list):
        return []

    top_comment_nodes: list[dict[str, object]] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        if clean_string(child.get("kind")) != "t1":
            continue

        comment_data = child.get("data")
        if not isinstance(comment_data, dict):
            continue

        top_comment_nodes.append(comment_data)

    return top_comment_nodes


def normalize_top_comment_nodes(
    top_comment_nodes: list[dict[str, object]],
    limit: int = TOP_COMMENT_LIMIT,
) -> list[dict[str, object]]:
    normalized_comments: list[dict[str, object]] = []
    for comment_data in top_comment_nodes:
        comment = normalize_comment_node(comment_data)
        if comment is not None:
            normalized_comments.append(comment)
    return cap_comments(normalized_comments, limit=limit)


def extract_post_fullname(post_data: dict[str, Any]) -> str:
    post_name = clean_string(post_data.get("name"))
    if post_name.startswith("t3_"):
        return post_name

    post_short_id = clean_string(post_data.get("id"))
    if post_short_id:
        return f"t3_{post_short_id}"

    return ""
