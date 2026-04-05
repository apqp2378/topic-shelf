from __future__ import annotations

from typing import Any

from pipeline.blog_providers.base import BlogDraftProvider
from pipeline.blog_rules import (
    DEFAULT_DRAFT_STATUS,
    FALLBACK_BUNDLE_ID,
    build_body_sections,
    build_closing,
    build_draft_intro,
    build_draft_reason,
    build_draft_subtitle,
    build_draft_title,
    build_key_points,
    bundle_primary_topic,
    bundle_related_topics,
    choose_recommended_cards,
    clean_text,
)


class RuleBasedBlogDraftProvider(BlogDraftProvider):
    provider_name = "rule_based"

    def build_drafts(
        self,
        bundles: list[dict[str, Any]],
        cards: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if bundles:
            drafts: list[dict[str, Any]] = []
            for bundle in bundles:
                bundle_cards = select_cards_for_bundle(bundle, cards)
                drafts.append(self.build_draft(bundle, bundle_cards))
            return drafts

        if not cards:
            return []

        fallback_bundle = {
            "bundle_id": FALLBACK_BUNDLE_ID,
            "bundle_type": "fallback_bundle",
            "title": "Fallback draft",
            "description": "Fallback draft built from the latest available cards.",
            "primary_topic": "general_discussion",
            "related_topics": ["general_discussion"],
            "card_ids": collect_card_ids(cards),
            "representative_card_id": get_card_id(cards[0]) if cards else "",
            "representative_title": clean_text(cards[0].get("title")) if cards else "",
            "representative_summary": clean_text(cards[0].get("summary") or cards[0].get("excerpt")) if cards else "",
        }
        return [self.build_draft(fallback_bundle, cards, fallback=True)]

    def build_draft(
        self,
        bundle: dict[str, Any],
        cards: list[dict[str, Any]],
        fallback: bool = False,
    ) -> dict[str, Any]:
        recommended_cards = choose_recommended_cards(bundle, cards, max_items=3)

        return {
            "draft_id": build_draft_id(bundle),
            "source_bundle_id": clean_text(bundle.get("bundle_id")) or FALLBACK_BUNDLE_ID,
            "title": build_draft_title(bundle, cards),
            "subtitle": build_draft_subtitle(bundle, cards),
            "intro": build_draft_intro(bundle, cards),
            "key_points": build_key_points(bundle, cards),
            "recommended_cards": recommended_cards,
            "primary_topic": bundle_primary_topic(bundle),
            "related_topics": bundle_related_topics(bundle),
            "body_sections": build_body_sections(bundle, cards),
            "closing": build_closing(bundle, cards),
            "draft_status": DEFAULT_DRAFT_STATUS,
            "draft_reason": build_draft_reason(bundle, cards, fallback=fallback),
        }


def build_draft_id(bundle: dict[str, Any]) -> str:
    bundle_id = clean_text(bundle.get("bundle_id"))
    if bundle_id:
        return f"draft_{bundle_id}"
    return FALLBACK_BUNDLE_ID.replace("bundle", "draft")


def select_cards_for_bundle(
    bundle: dict[str, Any],
    cards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    bundle_card_ids = bundle.get("card_ids")
    if not isinstance(bundle_card_ids, list):
        return cards

    card_lookup = index_cards_by_id(cards)
    selected_cards: list[dict[str, Any]] = []

    for item in bundle_card_ids:
        card_id = clean_text(item)
        if not card_id:
            continue
        card = card_lookup.get(card_id)
        if card is not None:
            selected_cards.append(card)

    if selected_cards:
        return selected_cards
    return cards


def index_cards_by_id(cards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed_cards: dict[str, dict[str, Any]] = {}
    for card in cards:
        card_id = get_card_id(card)
        if card_id and card_id not in indexed_cards:
            indexed_cards[card_id] = card
    return indexed_cards


def collect_card_ids(cards: list[dict[str, Any]]) -> list[str]:
    card_ids: list[str] = []
    for card in cards:
        card_id = get_card_id(card)
        if card_id and card_id not in card_ids:
            card_ids.append(card_id)
    return card_ids


def get_card_id(card: dict[str, Any]) -> str:
    return clean_text(card.get("card_id"))
