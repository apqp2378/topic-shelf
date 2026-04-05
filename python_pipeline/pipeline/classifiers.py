from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.classification_providers.base import ClassificationProvider, clean_text
from pipeline.classification_providers.rule_based import RuleBasedClassificationProvider
from pipeline.topic_rules import GENERAL_TOPIC, has_card_text


@dataclass
class ClassificationStats:
    input_count: int = 0
    success_count: int = 0
    fallback_count: int = 0
    empty_text_count: int = 0
    card_failure_count: int = 0


def build_classification_provider(provider_name: str) -> ClassificationProvider:
    cleaned_provider_name = clean_text(provider_name).lower()
    if cleaned_provider_name in ("", "rule_based", "rule-based"):
        return RuleBasedClassificationProvider()

    raise ValueError(f"Unsupported classification provider: {provider_name}")


def classify_card(
    card: dict[str, Any],
    provider: ClassificationProvider,
    card_index: int | None = None,
) -> dict[str, Any]:
    classified_card, _ = classify_card_with_status(card, provider, card_index=card_index)
    return classified_card


def enrich_cards_with_topics(
    cards: list[dict[str, Any]],
    provider: ClassificationProvider,
) -> list[dict[str, Any]]:
    classified_cards, _ = classify_cards_with_stats(cards, provider)
    return classified_cards


def classify_cards_with_stats(
    cards: list[dict[str, Any]],
    provider: ClassificationProvider,
) -> tuple[list[dict[str, Any]], ClassificationStats]:
    classified_cards: list[dict[str, Any]] = []
    stats = ClassificationStats(input_count=len(cards))

    for index, card in enumerate(cards, start=1):
        classified_card, card_failed = classify_card_with_status(card, provider, index)
        classified_cards.append(classified_card)
        if card_failed:
            stats.card_failure_count += 1
        if not has_card_text(card):
            stats.empty_text_count += 1
        if clean_text(classified_card.get("primary_topic")).lower() == GENERAL_TOPIC:
            stats.fallback_count += 1

    stats.success_count = stats.input_count - stats.card_failure_count
    return classified_cards, stats


def classify_card_with_status(
    card: dict[str, Any],
    provider: ClassificationProvider,
    card_index: int | None = None,
) -> tuple[dict[str, Any], bool]:
    classified_card = dict(card)
    card_failed = False

    try:
        classification = provider.classify_card(card)
    except Exception as exc:  # pragma: no cover - defensive guard for scaffold stability
        label = card_index if card_index is not None else "unknown"
        print(f"Topic classification fallback for card index {label}: {exc}")
        classification = {
            "topic_labels": [GENERAL_TOPIC],
            "primary_topic": GENERAL_TOPIC,
            "topic_confidence": 0.0,
            "topic_match_reason": "fallback:provider error",
        }
        card_failed = True

    normalized_classification = normalize_classification_result(classification)
    classified_card.update(normalized_classification)
    return classified_card, card_failed


def normalize_classification_result(result: dict[str, Any]) -> dict[str, Any]:
    topic_labels = clean_topic_labels(result.get("topic_labels"))
    primary_topic = clean_text(result.get("primary_topic"))
    topic_confidence = clean_confidence_value(result.get("topic_confidence"))
    topic_match_reason = clean_text(result.get("topic_match_reason"))

    if not topic_labels:
        topic_labels = [GENERAL_TOPIC]
    if not primary_topic:
        primary_topic = GENERAL_TOPIC
    if not topic_match_reason:
        topic_match_reason = "fallback:no keyword hits"

    return {
        "topic_labels": topic_labels,
        "primary_topic": primary_topic,
        "topic_confidence": topic_confidence,
        "topic_match_reason": topic_match_reason,
    }


def clean_topic_labels(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    labels: list[str] = []
    for item in value:
        label = clean_text(item)
        if label and label not in labels:
            labels.append(label)
    return labels


def clean_confidence_value(value: object) -> float:
    if isinstance(value, bool):
        return 0.0

    normalized_value: float | None

    if isinstance(value, int):
        normalized_value = float(value)
    elif isinstance(value, float):
        normalized_value = value
    else:
        return 0.0

    if normalized_value < 0.0:
        return 0.0
    if normalized_value > 1.0:
        return 1.0
    return normalized_value
