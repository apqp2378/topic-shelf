from __future__ import annotations

from typing import Iterable

from pipeline.schemas import CardRecord, NormalizedRecord


def build_cards(records: list[NormalizedRecord]) -> list[CardRecord]:
    return [build_card(record, index) for index, record in enumerate(records, start=1)]


def build_card(record: NormalizedRecord, index: int) -> CardRecord:
    collected_at = clean_string_value(record["collected_at"])
    card_date = collected_at[:10] if collected_at else "unknown-date"

    return {
        "card_id": f"reddit_card_{card_date}_{index:03d}",
        "source_id": clean_string_value(record["source_id"]),
        "title": clean_string_value(record["title"]),
        "source_url": clean_string_value(record["source_url"]),
        "subreddit": clean_string_value(record["subreddit"]),
        "status": clean_string_value(record["moderator_status"]),
        "score": record["score"],
        "reason_tags": clean_reason_tags(record["reason_tags"]),
        "review_note": clean_string_value(record["review_note"]),
        "top_comment_snippets": build_top_comment_snippets(record["top_comments"]),
        "created_utc": record["created_utc"],
        "collected_at": collected_at,
    }


def build_top_comment_snippets(top_comments: Iterable[dict[str, object]]) -> list[str]:
    snippets: list[str] = []

    for comment in top_comments:
        body = clean_string_value(comment.get("body"))
        if not body:
            continue

        cleaned = " ".join(body.split())
        if not cleaned:
            continue

        snippet = cleaned[:140]
        if len(cleaned) > 140:
            snippet += "..."
        snippets.append(snippet)

    return snippets


def clean_string_value(value: object) -> str:
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return ""


def clean_reason_tags(reason_tags: list[str]) -> list[str]:
    cleaned_tags: list[str] = []
    for tag in reason_tags:
        cleaned_tag = clean_string_value(tag)
        if cleaned_tag:
            cleaned_tags.append(cleaned_tag)
    return cleaned_tags
