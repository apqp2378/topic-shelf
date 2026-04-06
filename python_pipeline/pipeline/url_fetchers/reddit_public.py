from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from pipeline.url_fetchers.base import UrlFetchResult


class RedditPublicJsonFetcher:
    user_agent = "topic-shelf-url-ingest/1.0"

    def fetch_thread(self, canonical_url: str) -> UrlFetchResult:
        json_url = build_reddit_json_url(canonical_url)
        payload = self._load_json(json_url)

        if not isinstance(payload, list) or len(payload) < 1:
            raise ValueError("Reddit public JSON response must be a non-empty list.")

        post_data = extract_post_data(payload)
        top_comments = extract_top_comments(payload)
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
            with urlopen(request, timeout=20) as response:
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

    top_comments: list[dict[str, object]] = []

    for child in children:
        if not isinstance(child, dict):
            continue
        if clean_string(child.get("kind")) != "t1":
            continue

        comment_data = child.get("data")
        if not isinstance(comment_data, dict):
            continue

        comment_short_id = clean_string(comment_data.get("id"))
        comment_fullname = clean_string(comment_data.get("name"))
        comment_id = comment_fullname
        if not comment_id and comment_short_id:
            comment_id = f"t1_{comment_short_id}"
        if not comment_id:
            continue

        top_comments.append(
            {
                "comment_id": comment_id,
                "author": clean_string(comment_data.get("author")) or "[deleted]",
                "body": clean_string(comment_data.get("body")),
                "score": coerce_int(comment_data.get("score")),
                "created_utc": coerce_int(comment_data.get("created_utc")),
            }
        )

    return top_comments[:5]


def extract_post_fullname(post_data: dict[str, Any]) -> str:
    post_name = clean_string(post_data.get("name"))
    if post_name.startswith("t3_"):
        return post_name

    post_short_id = clean_string(post_data.get("id"))
    if post_short_id:
        return f"t3_{post_short_id}"

    return ""


def clean_string(value: object) -> str:
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return ""


def coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0
        try:
            return int(float(stripped))
        except ValueError:
            return 0
    return 0
