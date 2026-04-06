from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from pipeline.url_fetchers.base import TOP_COMMENT_LIMIT


class CommentExpander(Protocol):
    """Placeholder interface for future MoreComments expansion."""

    def expand(self, comments: list[dict[str, object]]) -> list[dict[str, object]]:
        """Expand or normalize a comment list."""


@dataclass(frozen=True)
class NoOpCommentExpander:
    """Current placeholder expander that only normalizes and caps comments."""

    def expand(self, comments: list[dict[str, object]]) -> list[dict[str, object]]:
        normalized = [
            normalized_comment
            for normalized_comment in (normalize_comment_node(comment) for comment in comments)
            if normalized_comment is not None
        ]
        return cap_comments(normalized)


def normalize_comment_node(node: Any) -> dict[str, object] | None:
    """Normalize a Reddit comment node into the raw top_comments shape.

    The helper intentionally accepts a loose ``Any`` node so future expansion
    code can pass through both API responses and already-parsed comment objects.
    """

    if not isinstance(node, dict):
        return None

    comment_id = clean_string(node.get("comment_id"))
    if not comment_id:
        comment_fullname = clean_string(node.get("name"))
        if comment_fullname:
            comment_id = comment_fullname
        else:
            comment_short_id = clean_string(node.get("id"))
            if comment_short_id:
                comment_id = f"t1_{comment_short_id}"

    if not comment_id:
        return None

    return {
        "comment_id": comment_id,
        "author": clean_string(node.get("author")) or "[deleted]",
        "body": clean_string(node.get("body")),
        "score": coerce_int(node.get("score")),
        "created_utc": coerce_int(node.get("created_utc")),
    }


def normalize_comment_nodes(
    nodes: Iterable[Any],
    limit: int = TOP_COMMENT_LIMIT,
) -> list[dict[str, object]]:
    """Normalize and cap a sequence of comment nodes."""

    normalized_comments: list[dict[str, object]] = []
    for node in nodes:
        normalized = normalize_comment_node(node)
        if normalized is not None:
            normalized_comments.append(normalized)
    return cap_comments(normalized_comments, limit=limit)


def cap_comments(
    comments: list[dict[str, object]],
    limit: int = TOP_COMMENT_LIMIT,
) -> list[dict[str, object]]:
    """Apply the shared top-comment cap in one place."""

    return comments[:limit]


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
