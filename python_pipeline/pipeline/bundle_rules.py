from __future__ import annotations

import re
from collections import Counter
from typing import Any


GENERAL_TOPIC = "general_discussion"


def clean_text(value: object) -> str:
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip()
        if cleaned:
            return cleaned
    return ""


def normalize_bundle_component(value: object) -> str:
    cleaned = clean_text(value).lower()
    if not cleaned:
        return ""
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    return cleaned.strip("_")


def humanize_topic(value: object) -> str:
    cleaned = clean_text(value)
    if not cleaned:
        return "General Discussion"

    cleaned = cleaned.replace("_", " ")
    return cleaned.title()


def card_primary_topic(card: dict[str, Any]) -> str:
    topic = normalize_bundle_component(card.get("primary_topic"))
    if topic:
        return topic
    return GENERAL_TOPIC


def card_preview_title(card: dict[str, Any]) -> str:
    title = clean_text(card.get("title"))
    if title:
        return title

    title_ko = clean_text(card.get("title_ko"))
    if title_ko:
        return title_ko

    return ""


def card_preview_summary(card: dict[str, Any]) -> str:
    summary = clean_text(card.get("summary"))
    if summary:
        return summary

    summary_ko = clean_text(card.get("summary_ko"))
    if summary_ko:
        return summary_ko

    excerpt = clean_text(card.get("excerpt"))
    if excerpt:
        return excerpt

    excerpt_ko = clean_text(card.get("excerpt_ko"))
    if excerpt_ko:
        return excerpt_ko

    return card_preview_title(card)


def choose_representative_card(cards: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not cards:
        return None

    ranked_cards: list[tuple[tuple[float, float, float, int], dict[str, Any]]] = []
    for index, card in enumerate(cards):
        ranked_cards.append((representative_score(card, index), card))

    ranked_cards.sort(key=ranked_score_key, reverse=True)
    return ranked_cards[0][1]


def representative_score(card: dict[str, Any], index: int) -> tuple[float, float, float, int]:
    summary_score = 1.0 if card_preview_summary(card) else 0.0
    topic_confidence = clean_float(card.get("topic_confidence"))
    title_score = 1.0 if card_preview_title(card) else 0.0
    return (summary_score, topic_confidence, title_score, -index)


def ranked_score_key(item: tuple[tuple[float, float, float, int], dict[str, Any]]) -> tuple[float, float, float, int]:
    return item[0]


def clean_float(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value
    return 0.0


def group_cards_by_primary_topic(cards: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped_cards: dict[str, list[dict[str, Any]]] = {}

    for card in cards:
        topic = card_primary_topic(card)
        if topic not in grouped_cards:
            grouped_cards[topic] = []
        grouped_cards[topic].append(card)

    return grouped_cards


def build_related_topics(cards: list[dict[str, Any]]) -> list[str]:
    topic_counter: Counter[str] = Counter()

    for card in cards:
        primary_topic = card_primary_topic(card)
        topic_counter[primary_topic] += 1

        topic_labels = card.get("topic_labels")
        if isinstance(topic_labels, list):
            for item in topic_labels:
                topic = normalize_bundle_component(item)
                if topic:
                    topic_counter[topic] += 1

    if not topic_counter:
        return [GENERAL_TOPIC]

    ranked_topics = sorted(topic_counter.items(), key=topic_sort_key, reverse=True)
    return [topic for topic, _ in ranked_topics]


def topic_sort_key(item: tuple[str, int]) -> tuple[int, str]:
    topic, count = item
    return (count, topic)


def build_bundle_id(bundle_type: str, primary_topic: str, bundle_index: int) -> str:
    topic_component = normalize_bundle_component(primary_topic)
    if topic_component:
        return f"{bundle_type}_{topic_component}_{bundle_index}"
    return f"{bundle_type}_{bundle_index}"


def build_bundle_title(
    bundle_type: str,
    card_count: int,
    primary_topic: str = GENERAL_TOPIC,
) -> str:
    if bundle_type == "weekly_bundle":
        return f"Weekly bundle ({card_count} cards)"
    if bundle_type == "topic_bundle":
        return f"{humanize_topic(primary_topic)} bundle ({card_count} cards)"
    return f"Mixed bundle ({card_count} cards)"


def build_bundle_description(
    bundle_type: str,
    card_count: int,
    primary_topic: str = GENERAL_TOPIC,
    related_topics: list[str] | None = None,
) -> str:
    if related_topics is None:
        related_topics = []

    if bundle_type == "weekly_bundle":
        return f"Grouped {card_count} cards from the latest export into one weekly bundle."
    if bundle_type == "topic_bundle":
        return f"Grouped {card_count} cards around {humanize_topic(primary_topic)}."
    if related_topics:
        topic_text = ", ".join(humanize_topic(topic) for topic in related_topics[:3])
        return f"Fallback bundle for a small mixed-topic set: {topic_text}."
    return "Fallback bundle for a small mixed-topic set."


def build_bundle_reason(
    bundle_type: str,
    card_count: int,
    primary_topic: str = GENERAL_TOPIC,
) -> str:
    if bundle_type == "weekly_bundle":
        return f"weekly bundle for {card_count} cards"
    if bundle_type == "topic_bundle":
        return f"topic bundle for {humanize_topic(primary_topic)} with {card_count} cards"
    return f"mixed fallback bundle for {card_count} cards"
