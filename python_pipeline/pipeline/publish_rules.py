from __future__ import annotations

from typing import Any


GENERAL_TOPIC = "general_discussion"


def clean_text(value: object) -> str:
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip()
        if cleaned:
            return cleaned
    return ""


def limit_text(text: str, max_len: int) -> str:
    cleaned = clean_text(text)
    if max_len < 1:
        return ""
    if len(cleaned) <= max_len:
        return cleaned
    if max_len <= 3:
        return cleaned[:max_len]
    return cleaned[: max_len - 3].rstrip() + "..."


def first_sentence(text: str) -> str:
    cleaned = clean_text(text)
    if not cleaned:
        return ""

    for separator in (". ", "! ", "? ", "\n"):
        if separator in cleaned:
            return cleaned.split(separator, 1)[0].strip()
    return cleaned


def normalize_markdown(lines: list[str]) -> str:
    normalized_lines: list[str] = []
    previous_blank = False

    for line in lines:
        cleaned_line = line.rstrip()
        is_blank = not cleaned_line.strip()
        if is_blank and previous_blank:
            continue
        normalized_lines.append(cleaned_line)
        previous_blank = is_blank

    while normalized_lines and not normalized_lines[0].strip():
        normalized_lines.pop(0)
    while normalized_lines and not normalized_lines[-1].strip():
        normalized_lines.pop()

    return "\n".join(normalized_lines).strip() + "\n"


def heading(text: str, level: int = 2) -> str:
    safe_level = level if 1 <= level <= 6 else 2
    safe_text = clean_text(text) or "Untitled"
    return f"{'#' * safe_level} {safe_text}"


def bullet(text: str, indent: int = 0) -> str:
    safe_indent = max(indent, 0)
    safe_text = clean_text(text) or "Unavailable"
    return f"{'  ' * safe_indent}- {safe_text}"


def label_value(label: str, value: object, fallback: str = "Unavailable") -> str:
    safe_label = clean_text(label) or "Value"
    safe_value = clean_text(value) or fallback
    return f"- {safe_label}: {safe_value}"


def card_lookup(cards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for card in cards:
        card_id = clean_text(card.get("card_id"))
        if card_id and card_id not in lookup:
            lookup[card_id] = card
    return lookup


def card_id_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    ids: list[str] = []
    for item in value:
        card_id = clean_text(item)
        if card_id and card_id not in ids:
            ids.append(card_id)
    return ids


def card_title(card: dict[str, Any]) -> str:
    for field_name in ("title_ko", "title", "post_title"):
        text = clean_text(card.get(field_name))
        if text:
            return text
    return ""


def card_summary(card: dict[str, Any]) -> str:
    for field_name in (
        "summary_ko",
        "summary",
        "excerpt_ko",
        "excerpt",
        "body_excerpt",
        "review_note",
    ):
        text = clean_text(card.get(field_name))
        if text:
            return text
    return ""


def card_topic(card: dict[str, Any]) -> str:
    for field_name in ("primary_topic", "topic", "topic_labels"):
        value = card.get(field_name)
        if isinstance(value, list):
            for item in value:
                topic = clean_text(item)
                if topic:
                    return topic
        else:
            topic = clean_text(value)
            if topic:
                return topic
    return GENERAL_TOPIC


def card_link(card: dict[str, Any]) -> str:
    for field_name in ("source_url", "post_url", "url"):
        link = clean_text(card.get(field_name))
        if link:
            return link
    return ""


def quality_review_snapshot(quality_reviews: list[dict[str, Any]]) -> list[str]:
    if not quality_reviews:
        return []

    pass_count = 0
    warning_count = 0
    fail_count = 0

    for review in quality_reviews:
        status = clean_text(review.get("status")).lower()
        if status == "pass":
            pass_count += 1
        elif status == "warning":
            warning_count += 1
        elif status == "fail":
            fail_count += 1

    return [
        f"- Review count: {len(quality_reviews)}",
        f"- Pass: {pass_count}",
        f"- Warning: {warning_count}",
        f"- Fail: {fail_count}",
    ]
