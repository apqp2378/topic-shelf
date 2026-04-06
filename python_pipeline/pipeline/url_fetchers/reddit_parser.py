from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.url_fetchers.base import TOP_COMMENT_LIMIT
from pipeline.url_fetchers.comment_expander import (
    CommentThreadSnapshot,
    clean_string,
    coerce_int,
    extract_comment_thread_snapshot,
    normalize_comment_nodes,
)


@dataclass(frozen=True)
class RedditPostFields:
    """Parsed Reddit post fields shared by public and OAuth fetchers."""

    post_id: str
    subreddit: str
    title: str
    author: str
    created_utc: int
    body: str
    num_comments: int
    upvotes: int
    permalink: str


def extract_post_data(payload: list[Any]) -> dict[str, Any]:
    """Extract the first post listing entry from a Reddit thread payload."""

    if not payload:
        raise ValueError("Reddit post listing is missing.")

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


def extract_post_fullname(post_data: dict[str, Any]) -> str:
    post_name = clean_string(post_data.get("name"))
    if post_name.startswith("t3_"):
        return post_name

    post_short_id = clean_string(post_data.get("id"))
    if post_short_id:
        return f"t3_{post_short_id}"

    return ""


def parse_post_fields(post_data: dict[str, Any]) -> RedditPostFields:
    """Parse the common post fields needed by both fetchers."""

    return RedditPostFields(
        post_id=extract_post_fullname(post_data),
        subreddit=clean_string(post_data.get("subreddit")),
        title=clean_string(post_data.get("title")),
        author=clean_string(post_data.get("author")) or "[deleted]",
        created_utc=coerce_int(post_data.get("created_utc")),
        body=clean_string(post_data.get("selftext")),
        num_comments=coerce_int(post_data.get("num_comments")),
        upvotes=coerce_int(post_data.get("ups")) or coerce_int(post_data.get("score")),
        permalink=clean_string(post_data.get("permalink")),
    )


def extract_thread_comment_children(payload: list[Any]) -> list[dict[str, object]]:
    """Extract raw top-level comment listing children from a Reddit thread payload."""

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

    listing_children: list[dict[str, object]] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        listing_children.append(child)

    return listing_children


def extract_thread_comment_snapshot(payload: list[Any]) -> CommentThreadSnapshot:
    """Parse initial comments and placeholder ids from a Reddit thread payload."""

    return extract_comment_thread_snapshot(extract_thread_comment_children(payload))


def extract_thread_top_comment_nodes(payload: list[Any]) -> list[dict[str, object]]:
    """Return the raw top-level comment nodes from a Reddit thread payload."""

    children = extract_thread_comment_children(payload)
    top_comment_nodes: list[dict[str, object]] = []
    for child in children:
        if clean_string(child.get("kind")) != "t1":
            continue

        comment_data = child.get("data")
        if not isinstance(comment_data, dict):
            continue

        top_comment_nodes.append(comment_data)

    return top_comment_nodes


def extract_thread_top_comments(
    payload: list[Any],
    limit: int = TOP_COMMENT_LIMIT,
) -> list[dict[str, object]]:
    """Parse and normalize the top-level comments from a Reddit thread payload."""

    return normalize_comment_nodes(extract_thread_top_comment_nodes(payload), limit=limit)
