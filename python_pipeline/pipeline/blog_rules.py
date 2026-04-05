from __future__ import annotations

from typing import Any


FALLBACK_BUNDLE_ID = "fallback_bundle_1"
DEFAULT_DRAFT_STATUS = "draft"


def clean_text(value: object) -> str:
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip()
        if cleaned:
            return cleaned
    return ""


def normalize_card_id(value: object) -> str:
    cleaned = clean_text(value)
    return cleaned


def bundle_value(bundle: dict[str, Any], key: str) -> str:
    return clean_text(bundle.get(key))


def card_text(card: dict[str, Any]) -> str:
    for field_name in (
        "summary_ko",
        "summary",
        "excerpt_ko",
        "excerpt",
        "body_excerpt",
        "title_ko",
        "title",
    ):
        text = clean_text(card.get(field_name))
        if text:
            return text
    return ""


def card_title(card: dict[str, Any]) -> str:
    for field_name in ("title_ko", "title"):
        text = clean_text(card.get(field_name))
        if text:
            return text
    return ""


def bundle_primary_topic(bundle: dict[str, Any]) -> str:
    topic = clean_text(bundle.get("primary_topic"))
    if topic:
        return topic
    return "general_discussion"


def bundle_related_topics(bundle: dict[str, Any]) -> list[str]:
    related_topics = bundle.get("related_topics")
    if isinstance(related_topics, list):
        cleaned_topics: list[str] = []
        for item in related_topics:
            topic = clean_text(item)
            if topic and topic not in cleaned_topics:
                cleaned_topics.append(topic)
        if cleaned_topics:
            return cleaned_topics
    primary_topic = bundle_primary_topic(bundle)
    return [primary_topic]


def build_draft_title(bundle: dict[str, Any], cards: list[dict[str, Any]]) -> str:
    bundle_title = bundle_value(bundle, "title")
    if bundle_title:
        return bundle_title

    primary_topic = bundle_primary_topic(bundle)
    if cards:
        representative = choose_representative_card(cards)
        rep_title = card_title(representative)
        if rep_title:
            return f"{rep_title} draft"

    return f"{primary_topic.replace('_', ' ').title()} draft"


def build_draft_subtitle(bundle: dict[str, Any], cards: list[dict[str, Any]]) -> str:
    card_count = len(cards)
    topics = bundle_related_topics(bundle)
    topic_text = ", ".join(topic.replace("_", " ").title() for topic in topics[:3])
    if topic_text:
        return f"{card_count} cards, focused on {topic_text}"
    return f"{card_count} cards"


def build_draft_intro(bundle: dict[str, Any], cards: list[dict[str, Any]]) -> str:
    bundle_description = bundle_value(bundle, "description")
    if bundle_description:
        return bundle_description

    representative = choose_representative_card(cards)
    representative_summary = card_text(representative)
    if representative_summary:
        return f"This draft starts from the strongest available card and keeps the framing compact: {representative_summary}"

    return "This draft is a compact starting point for turning the current card set into a publishable post."


def build_key_points(bundle: dict[str, Any], cards: list[dict[str, Any]]) -> list[str]:
    points: list[str] = []
    for card in cards:
        text = card_text(card)
        if text and text not in points:
            points.append(text)
        if len(points) >= 5:
            break

    if not points:
        points.append("Collect the main angle before expanding the draft.")

    if len(points) == 1:
        points.append("Add supporting context or a second example if needed.")

    return points[:5]


def build_body_sections(bundle: dict[str, Any], cards: list[dict[str, Any]]) -> list[dict[str, str]]:
    representative = choose_representative_card(cards)
    representative_summary = card_text(representative)
    related_topics = bundle_related_topics(bundle)
    topic_text = ", ".join(topic.replace("_", " ").title() for topic in related_topics[:3])

    sections: list[dict[str, str]] = []
    sections.append(
        {
            "heading": "Overview",
            "summary": bundle_value(bundle, "description")
            or "Summarize the core angle of this bundle in one or two paragraphs.",
        }
    )
    sections.append(
        {
            "heading": "Representative card",
            "summary": representative_summary
            or "Use the representative card as the anchor example for the draft.",
        }
    )
    sections.append(
        {
            "heading": "Related topics",
            "summary": f"Keep the draft connected to: {topic_text}."
            if topic_text
            else "Keep the draft connected to the nearby follow-up questions.",
        }
    )

    if len(cards) > 3:
        sections.append(
            {
                "heading": "Optional expansion",
                "summary": "Add one short supporting paragraph if the post needs more context.",
            }
        )

    return sections[:4]


def build_closing(bundle: dict[str, Any], cards: list[dict[str, Any]]) -> str:
    primary_topic = bundle_primary_topic(bundle).replace("_", " ").title()
    if cards:
        return f"Close with a short, practical takeaway for the {primary_topic} angle."
    return "Close with a short practical takeaway."


def choose_recommended_cards(
    bundle: dict[str, Any],
    cards: list[dict[str, Any]],
    max_items: int = 3,
) -> list[str]:
    recommended: list[str] = []
    bundle_card_ids = bundle.get("card_ids")
    preferred_ids: list[str] = []

    if isinstance(bundle_card_ids, list):
        for item in bundle_card_ids:
            card_id = normalize_card_id(item)
            if card_id and card_id not in preferred_ids:
                preferred_ids.append(card_id)

    representative_id = normalize_card_id(bundle.get("representative_card_id"))
    if representative_id and representative_id not in preferred_ids:
        preferred_ids.insert(0, representative_id)

    if preferred_ids:
        for card_id in preferred_ids:
            if card_id not in recommended:
                recommended.append(card_id)
            if len(recommended) >= max_items:
                return recommended[:max_items]

    for card in cards:
        card_id = normalize_card_id(card.get("card_id"))
        if card_id and card_id not in recommended:
            recommended.append(card_id)
        if len(recommended) >= max_items:
            break

    return recommended[:max_items]


def build_draft_reason(bundle: dict[str, Any], cards: list[dict[str, Any]], fallback: bool = False) -> str:
    if fallback:
        return "fallback draft built from the available cards because no bundle was provided"

    bundle_type = bundle_value(bundle, "bundle_type") or "bundle"
    bundle_id = bundle_value(bundle, "bundle_id") or "unknown_bundle"
    card_count = len(cards)
    representative_title = bundle_value(bundle, "representative_title")

    if representative_title:
        return f"built from {bundle_type} {bundle_id} using representative card {representative_title} and {card_count} cards"
    return f"built from {bundle_type} {bundle_id} using {card_count} cards"


def choose_representative_card(cards: list[dict[str, Any]]) -> dict[str, Any]:
    if not cards:
        return {}

    ranked_cards: list[tuple[tuple[int, int, int], dict[str, Any]]] = []
    for index, card in enumerate(cards):
        summary_score = 1 if clean_text(card.get("summary_ko") or card.get("summary")) else 0
        title_score = 1 if clean_text(card.get("title_ko") or card.get("title")) else 0
        ranked_cards.append(((summary_score, title_score, -index), card))

    ranked_cards.sort(key=representative_sort_key, reverse=True)
    return ranked_cards[0][1]


def representative_sort_key(item: tuple[tuple[int, int, int], dict[str, Any]]) -> tuple[int, int, int]:
    return item[0]
