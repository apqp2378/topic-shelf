from __future__ import annotations

import re
from typing import Any


def enrich_cards_with_summary(
    cards: list[dict[str, Any]],
    max_len: int = 180,
) -> list[dict[str, Any]]:
    enriched_cards: list[dict[str, Any]] = []

    for index, card in enumerate(cards):
        summary = ""
        try:
            summary = build_heuristic_summary(card, max_len=max_len)
        except Exception as exc:  # pragma: no cover - defensive guard for handoff stability
            print(f"Summary stage fallback for card index {index}: {exc}")

        enriched_card = dict(card)
        enriched_card["summary"] = summary
        enriched_cards.append(enriched_card)

    return enriched_cards


def build_heuristic_summary(card: dict[str, Any], max_len: int = 180) -> str:
    if max_len < 1:
        return ""

    title = clean_text(card.get("title"))
    if not title:
        return ""

    summary = shorten_text(title, max_len)
    if len(summary) >= max_len:
        return summary

    excerpt = pick_excerpt_text(card)
    if excerpt:
        summary = append_segment(summary, excerpt, " - ", max_len)

    comment = pick_comment_text(card)
    if comment and comment not in summary:
        summary = append_segment(summary, comment, " | ", max_len)

    return summary[:max_len] if len(summary) > max_len else summary


def pick_excerpt_text(card: dict[str, Any]) -> str:
    for field_name in ("excerpt", "body_excerpt", "review_note"):
        text = clean_text(card.get(field_name))
        if text:
            return shorten_text(text, 120)
    return ""


def pick_comment_text(card: dict[str, Any]) -> str:
    top_comments = card.get("top_comments")
    if isinstance(top_comments, list):
        best_comment = pick_best_comment_text(top_comments)
        if best_comment:
            return shorten_text(best_comment, 120)

    top_comment_snippets = card.get("top_comment_snippets")
    if isinstance(top_comment_snippets, list):
        best_snippet = pick_best_snippet(top_comment_snippets)
        if best_snippet:
            return shorten_text(best_snippet, 120)

    return ""


def pick_best_comment_text(top_comments: list[Any]) -> str:
    best_text = ""
    best_length = 0

    for item in top_comments:
        if not isinstance(item, dict):
            continue

        comment_text = clean_text(item.get("body"))
        if not comment_text:
            continue

        comment_text = first_sentence(comment_text)
        comment_length = len(comment_text)
        if comment_length > best_length:
            best_text = comment_text
            best_length = comment_length

    return best_text


def pick_best_snippet(top_comment_snippets: list[Any]) -> str:
    best_text = ""
    best_length = 0

    for item in top_comment_snippets:
        snippet_text = clean_text(item)
        if not snippet_text:
            continue

        snippet_text = first_sentence(snippet_text)
        snippet_length = len(snippet_text)
        if snippet_length > best_length:
            best_text = snippet_text
            best_length = snippet_length

    return best_text


def append_segment(summary: str, segment: str, separator: str, max_len: int) -> str:
    if not summary or not segment:
        return summary

    candidate = f"{summary}{separator}{segment}"
    if len(candidate) <= max_len:
        return candidate

    shortened_segment = shorten_text(segment, max_len - len(summary) - len(separator))
    if not shortened_segment:
        return summary

    candidate = f"{summary}{separator}{shortened_segment}"
    if len(candidate) <= max_len:
        return candidate

    return truncate_text(candidate, max_len)


def shorten_text(text: str, max_len: int) -> str:
    if max_len < 1:
        return ""

    clean_value = clean_text(text)
    if not clean_value:
        return ""

    sentence = first_sentence(clean_value)
    if len(sentence) <= max_len:
        return sentence

    return truncate_text(sentence, max_len)


def first_sentence(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
    if sentences and sentences[0].strip():
        return sentences[0].strip()
    return text.strip()


def truncate_text(text: str, max_len: int) -> str:
    if max_len < 1:
        return ""

    if len(text) <= max_len:
        return text

    if max_len <= 3:
        return text[:max_len]

    return text[: max_len - 3].rstrip() + "..."


def clean_text(value: object) -> str:
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip()
        if cleaned:
            return cleaned
    return ""
