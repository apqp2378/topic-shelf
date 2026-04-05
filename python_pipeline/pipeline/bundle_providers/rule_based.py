from __future__ import annotations

from typing import Any

from pipeline.bundle_providers.base import BundleProvider
from pipeline.bundle_rules import (
    GENERAL_TOPIC,
    build_bundle_description,
    build_bundle_id,
    build_bundle_reason,
    build_bundle_title,
    build_related_topics,
    card_preview_summary,
    card_preview_title,
    choose_representative_card,
    group_cards_by_primary_topic,
)


class RuleBasedBundleProvider(BundleProvider):
    provider_name = "rule_based"

    def build_bundles(self, cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not cards:
            return []

        bundles: list[dict[str, Any]] = []
        bundles.append(self.build_weekly_bundle(cards, 1))

        topic_bundles = self.build_topic_bundles(cards)
        if topic_bundles:
            bundles.extend(topic_bundles)
            return bundles

        if len(cards) >= 2:
            bundles.append(self.build_mixed_bundle(cards, 1))

        return bundles

    def build_weekly_bundle(self, cards: list[dict[str, Any]], bundle_index: int) -> dict[str, Any]:
        representative_card = choose_representative_card(cards)
        return self.build_bundle_record(
            bundle_type="weekly_bundle",
            cards=cards,
            representative_card=representative_card,
            bundle_index=bundle_index,
            primary_topic=GENERAL_TOPIC,
        )

    def build_topic_bundles(self, cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped_cards = group_cards_by_primary_topic(cards)
        sorted_topics = sorted(grouped_cards.keys())
        bundles: list[dict[str, Any]] = []
        bundle_index = 1

        for topic in sorted_topics:
            topic_cards = grouped_cards[topic]
            if len(topic_cards) < 2:
                continue

            representative_card = choose_representative_card(topic_cards)
            bundles.append(
                self.build_bundle_record(
                    bundle_type="topic_bundle",
                    cards=topic_cards,
                    representative_card=representative_card,
                    bundle_index=bundle_index,
                    primary_topic=topic,
                )
            )
            bundle_index += 1

        return bundles

    def build_mixed_bundle(
        self,
        cards: list[dict[str, Any]],
        bundle_index: int,
    ) -> dict[str, Any]:
        representative_card = choose_representative_card(cards)
        return self.build_bundle_record(
            bundle_type="mixed_bundle",
            cards=cards,
            representative_card=representative_card,
            bundle_index=bundle_index,
            primary_topic=GENERAL_TOPIC,
        )

    def build_bundle_record(
        self,
        bundle_type: str,
        cards: list[dict[str, Any]],
        representative_card: dict[str, Any] | None,
        bundle_index: int,
        primary_topic: str,
    ) -> dict[str, Any]:
        card_ids = collect_card_ids(cards)
        related_topics = build_related_topics(cards)
        bundle_id = build_bundle_id(bundle_type, primary_topic, bundle_index)

        if representative_card is None and cards:
            representative_card = cards[0]

        return {
            "bundle_id": bundle_id,
            "bundle_type": bundle_type,
            "title": build_bundle_title(bundle_type, len(cards), primary_topic),
            "description": build_bundle_description(
                bundle_type,
                len(cards),
                primary_topic,
                related_topics,
            ),
            "primary_topic": primary_topic,
            "card_ids": card_ids,
            "card_count": len(cards),
            "representative_card_id": get_card_id(representative_card),
            "related_topics": related_topics,
            "bundle_reason": build_bundle_reason(bundle_type, len(cards), primary_topic),
            "representative_title": card_preview_title(representative_card or {}),
            "representative_summary": card_preview_summary(representative_card or {}),
        }


def collect_card_ids(cards: list[dict[str, Any]]) -> list[str]:
    card_ids: list[str] = []
    for card in cards:
        card_id = get_card_id(card)
        if card_id and card_id not in card_ids:
            card_ids.append(card_id)
    return card_ids


def get_card_id(card: dict[str, Any] | None) -> str:
    if not card:
        return ""

    card_id = card.get("card_id")
    if isinstance(card_id, str):
        cleaned = card_id.strip()
        if cleaned:
            return cleaned
    return ""
