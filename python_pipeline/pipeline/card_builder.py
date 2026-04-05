from __future__ import annotations

from typing import Iterable

from pipeline.schemas import CardRecord, NormalizedRecord


def build_cards(records: list[NormalizedRecord]) -> list[CardRecord]:
    return [build_card(record, index) for index, record in enumerate(records, start=1)]


def build_card(record: NormalizedRecord, index: int) -> CardRecord:
    card_date = record["collected_at"][:10] if record["collected_at"] else "unknown-date"

    return {
        "card_id": f"reddit_card_{card_date}_{index:03d}",
        "source_id": record["source_id"],
        "title": record["title"],
        "source_url": record["source_url"],
        "subreddit": record["subreddit"],
        "status": record["moderator_status"],
        "score": record["score"],
        "reason_tags": list(record["reason_tags"]),
        "review_note": record["review_note"],
        "top_comment_snippets": build_top_comment_snippets(record["top_comments"]),
        "created_utc": record["created_utc"],
        "collected_at": record["collected_at"],
    }


def build_top_comment_snippets(top_comments: Iterable[dict[str, object]]) -> list[str]:
    snippets: list[str] = []

    for comment in top_comments:
        body = comment.get("body")
        if not isinstance(body, str):
            continue

        cleaned = " ".join(body.split()).strip()
        if not cleaned:
            continue

        snippet = cleaned[:140]
        if len(cleaned) > 140:
            snippet += "..."
        snippets.append(snippet)

    return snippets
