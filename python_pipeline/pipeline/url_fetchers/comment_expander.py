from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from pipeline.url_fetchers.base import TOP_COMMENT_LIMIT


class CommentExpander(Protocol):
    """Placeholder interface for future MoreComments expansion."""

    def expand(self, comments: list[dict[str, object]]) -> list[dict[str, object]]:
        """Expand or normalize a comment list."""


@dataclass(frozen=True)
class CommentThreadSnapshot:
    """Parsed initial thread comments plus any expandable placeholder ids."""

    initial_comment_nodes: list[dict[str, object]]
    expandable_comment_ids: list[str]
    comment_fetch_count: int
    comment_fetch_depth: int = 0


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


def extract_comment_thread_snapshot(
    children: Iterable[Any],
    limit: int = TOP_COMMENT_LIMIT,
) -> CommentThreadSnapshot:
    """Parse initial comments and expandable placeholders from a thread listing."""

    initial_comment_nodes: list[dict[str, object]] = []
    expandable_comment_ids: list[str] = []

    for child in children:
        if not isinstance(child, dict):
            continue

        kind = clean_string(child.get("kind"))
        data = child.get("data")
        if not isinstance(data, dict):
            continue

        if kind == "t1":
            initial_comment_nodes.append(data)
            continue

        if kind == "more":
            expandable_comment_ids.extend(extract_more_comment_ids(data))

    return CommentThreadSnapshot(
        initial_comment_nodes=initial_comment_nodes,
        expandable_comment_ids=dedupe_preserving_order(expandable_comment_ids),
        comment_fetch_count=len(initial_comment_nodes),
        comment_fetch_depth=0,
    )


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


def merge_comment_nodes(
    initial_nodes: Iterable[Any],
    expanded_nodes: Iterable[Any] | None = None,
    limit: int = TOP_COMMENT_LIMIT,
) -> list[dict[str, object]]:
    """Normalize, merge, dedupe, and cap comment nodes in one shared place."""

    merged_comments: list[dict[str, object]] = []
    seen_comment_ids: set[str] = set()

    for node in initial_nodes:
        normalized = normalize_comment_node(node)
        if normalized is None:
            continue
        comment_id = clean_string(normalized.get("comment_id"))
        if not comment_id or comment_id in seen_comment_ids:
            continue
        seen_comment_ids.add(comment_id)
        merged_comments.append(normalized)

    if expanded_nodes is not None:
        for node in expanded_nodes:
            normalized = normalize_comment_node(node)
            if normalized is None:
                continue
            comment_id = clean_string(normalized.get("comment_id"))
            if not comment_id or comment_id in seen_comment_ids:
                continue
            seen_comment_ids.add(comment_id)
            merged_comments.append(normalized)

    return cap_comments(merged_comments, limit=limit)


def cap_comment_nodes(
    comments: list[dict[str, object]],
    limit: int = TOP_COMMENT_LIMIT,
) -> list[dict[str, object]]:
    """Cap raw comment nodes before later normalization."""

    return comments[:limit]


def cap_comments(
    comments: list[dict[str, object]],
    limit: int = TOP_COMMENT_LIMIT,
) -> list[dict[str, object]]:
    """Apply the shared top-comment cap in one place."""

    return comments[:limit]


def extract_more_comment_ids(node: dict[str, object]) -> list[str]:
    """Collect expandable comment ids from a ``more`` node."""

    candidate_fields = ("children", "ids", "child_ids")
    more_ids: list[str] = []

    for field_name in candidate_fields:
        field_value = node.get(field_name)
        if isinstance(field_value, list):
            for item in field_value:
                comment_id = clean_string(item)
                if comment_id and comment_id not in more_ids:
                    more_ids.append(comment_id)

    return more_ids


def extract_morechildren_comment_nodes(payload: Any) -> list[dict[str, object]]:
    """Extract expanded comment nodes from a ``morechildren`` response payload."""

    if not isinstance(payload, dict):
        return []

    json_data = payload.get("json")
    if isinstance(json_data, dict):
        payload_data = json_data.get("data")
    else:
        payload_data = payload.get("data")

    if not isinstance(payload_data, dict):
        return []

    things = payload_data.get("things")
    if not isinstance(things, list):
        return []

    comment_nodes: list[dict[str, object]] = []
    for thing in things:
        if not isinstance(thing, dict):
            continue
        if clean_string(thing.get("kind")) != "t1":
            continue
        comment_data = thing.get("data")
        if isinstance(comment_data, dict):
            comment_nodes.append(comment_data)

    return comment_nodes


def dedupe_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []

    for value in values:
        cleaned = clean_string(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)

    return deduped


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
