from __future__ import annotations

from typing import Any

from pipeline.schemas import NormalizedRecord, RawTopComment


def normalize_records(records: list[dict[str, Any]]) -> list[NormalizedRecord]:
    return [normalize_record(record) for record in records]


def normalize_record(record: dict[str, Any]) -> NormalizedRecord:
    top_comments = normalize_top_comments(record.get("top_comments"))

    return {
        "source_id": string_value(record, "raw_id"),
        "source": string_value(record, "source"),
        "source_type": "reddit_post",
        "subreddit": string_value(record, "subreddit"),
        "title": string_value(record, "post_title"),
        "source_url": string_value(record, "post_url"),
        "author": string_value(record, "post_author"),
        "created_utc": int_value(record, "post_created_utc"),
        "body": string_value(record, "post_body"),
        "body_excerpt": string_value(record, "body_excerpt"),
        "num_comments": int_value(record, "num_comments"),
        "upvotes": int_value(record, "upvotes"),
        "top_comments": top_comments,
        "score": int_value(record, "devvit_score"),
        "reason_tags": string_list_value(record, "devvit_reason_tags"),
        "recommended_status": string_value(record, "recommended_status"),
        "moderator_status": string_value(record, "moderator_status"),
        "review_note": string_value(record, "review_note"),
        "collected_at": string_value(record, "collected_at"),
        "devvit_version": string_value(record, "devvit_version"),
        "post_id": string_value(record, "post_id"),
        "candidate_id": string_value(record, "candidate_id"),
    }


def normalize_top_comments(value: Any) -> list[RawTopComment]:
    if not isinstance(value, list):
        return []

    normalized: list[RawTopComment] = []
    for item in value:
        if not isinstance(item, dict):
            continue

        normalized.append(
            {
                "comment_id": string_value(item, "comment_id"),
                "author": string_value(item, "author"),
                "body": string_value(item, "body"),
                "score": int_value(item, "score"),
                "created_utc": int_value(item, "created_utc"),
            }
        )

    return normalized


def string_value(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return ""


def int_value(record: dict[str, Any], key: str) -> int:
    value = record.get(key)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def string_list_value(record: dict[str, Any], key: str) -> list[str]:
    value = record.get(key)
    if not isinstance(value, list):
        return []

    cleaned_values: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if cleaned:
            cleaned_values.append(cleaned)

    return cleaned_values
