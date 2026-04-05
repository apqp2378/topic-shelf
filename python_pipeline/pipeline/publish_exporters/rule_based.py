from __future__ import annotations

from typing import Any

from pipeline.publish_exporters.base import PublishExportProvider
from pipeline.publish_rules import (
    bullet,
    card_id_list,
    card_link,
    card_lookup,
    card_summary,
    card_title,
    card_topic,
    clean_text,
    heading,
    label_value,
    limit_text,
    normalize_markdown,
    quality_review_snapshot,
)


class RuleBasedPublishExportProvider(PublishExportProvider):
    provider_name = "rule_based"

    def __init__(self) -> None:
        self._fallback_section_count = 0

    def get_fallback_section_count(self) -> int:
        return self._fallback_section_count

    def build_markdown(
        self,
        source_type: str,
        items: list[dict[str, Any]],
        cards: list[dict[str, Any]],
        quality_reviews: list[dict[str, Any]] | None = None,
    ) -> str:
        self._fallback_section_count = 0
        normalized_source_type = clean_text(source_type).lower()
        quality_reviews = quality_reviews or []

        if normalized_source_type == "blog_drafts":
            markdown, fallback_count = build_blog_drafts_markdown(items, cards, quality_reviews)
        elif normalized_source_type == "bundles":
            markdown, fallback_count = build_bundles_markdown(items, cards, quality_reviews)
        else:
            markdown, fallback_count = build_cards_markdown(items, quality_reviews)

        self._fallback_section_count = fallback_count
        return markdown


def build_blog_drafts_markdown(
    blog_drafts: list[dict[str, Any]],
    cards: list[dict[str, Any]],
    quality_reviews: list[dict[str, Any]],
) -> tuple[str, int]:
    lines: list[str] = [heading("Publish Blog Drafts", 1)]
    fallback_count = 0
    card_index = card_lookup(cards)

    lines.append(label_value("Source", "blog_drafts"))
    lines.append(label_value("Draft count", len(blog_drafts)))
    lines.append("")

    if quality_reviews:
        lines.append(heading("Quality Review Snapshot", 2))
        lines.extend(quality_review_snapshot(quality_reviews))
        lines.append("")

    if not blog_drafts:
        lines.append("No blog drafts were available, so this export falls back to a compact draft note.")
        fallback_count += 1
        return normalize_markdown(lines), fallback_count

    for index, draft in enumerate(blog_drafts, start=1):
        title = clean_text(draft.get("title"))
        if not title:
            title = f"Draft {index}"
            fallback_count += 1

        lines.append(heading(f"{title}", 2))
        lines.append(label_value("Source bundle", draft.get("source_bundle_id")))
        lines.append(label_value("Primary topic", draft.get("primary_topic")))
        lines.append(label_value("Draft status", draft.get("draft_status")))
        lines.append("")

        subtitle = clean_text(draft.get("subtitle"))
        if subtitle:
            lines.append(heading("Subtitle", 3))
            lines.append(subtitle)
        else:
            lines.append(heading("Subtitle", 3))
            lines.append("Add a short subtitle for the draft.")
            fallback_count += 1
        lines.append("")

        intro = clean_text(draft.get("intro"))
        if intro:
            lines.append(heading("Intro", 3))
            lines.append(intro)
        else:
            lines.append(heading("Intro", 3))
            lines.append("Write a short opening that frames the draft.")
            fallback_count += 1
        lines.append("")

        key_points = clean_string_list(draft.get("key_points"), 2, 220)
        lines.append(heading("Key Points", 3))
        if key_points:
            for point in key_points[:5]:
                lines.append(bullet(point))
        else:
            lines.append(bullet("Capture the core angle before expanding the post."))
            fallback_count += 1
        lines.append("")

        body_sections = clean_body_sections(draft.get("body_sections"))
        lines.append(heading("Body Sections", 3))
        if body_sections:
            for section in body_sections[:4]:
                section_title = clean_text(section.get("heading")) or "Section"
                section_summary = clean_text(section.get("summary"))
                lines.append(heading(section_title, 4))
                lines.append(section_summary or "Add a short section summary.")
                if not section_summary:
                    fallback_count += 1
                lines.append("")
        else:
            lines.append(heading("Overview", 4))
            lines.append("Add two to four short body sections for the draft.")
            lines.append("")
            fallback_count += 1

        recommended_cards = normalize_recommended_cards(
            draft.get("recommended_cards"),
            cards,
            card_index,
        )
        lines.append(heading("Recommended Cards", 3))
        if recommended_cards:
            for card_id in recommended_cards:
                card = card_index.get(card_id, {})
                card_title_text = card_title(card)
                card_line = f"`{card_id}`"
                if card_title_text:
                    card_line = f"{card_line} - {card_title_text}"
                lines.append(bullet(card_line))
        else:
            lines.append(bullet("Add one to three recommended cards."))
            fallback_count += 1
        lines.append("")

        closing = clean_text(draft.get("closing"))
        lines.append(heading("Closing", 3))
        if closing:
            lines.append(closing)
        else:
            lines.append("Close with a short practical takeaway.")
            fallback_count += 1
        lines.append("")

        draft_reason = clean_text(draft.get("draft_reason"))
        if draft_reason:
            lines.append(label_value("Draft reason", draft_reason))
            lines.append("")

    return normalize_markdown(lines), fallback_count


def build_bundles_markdown(
    bundles: list[dict[str, Any]],
    cards: list[dict[str, Any]],
    quality_reviews: list[dict[str, Any]],
) -> tuple[str, int]:
    lines: list[str] = [heading("Publish Bundles", 1)]
    fallback_count = 0
    card_index = card_lookup(cards)

    lines.append(label_value("Source", "bundles"))
    lines.append(label_value("Bundle count", len(bundles)))
    lines.append("")

    if quality_reviews:
        lines.append(heading("Quality Review Snapshot", 2))
        lines.extend(quality_review_snapshot(quality_reviews))
        lines.append("")

    if not bundles:
        lines.append("No bundles were available, so this export falls back to a compact bundle note.")
        fallback_count += 1
        return normalize_markdown(lines), fallback_count

    for index, bundle in enumerate(bundles, start=1):
        title = clean_text(bundle.get("title"))
        if not title:
            title = f"Bundle {index}"
            fallback_count += 1

        lines.append(heading(title, 2))
        lines.append(label_value("Bundle type", bundle.get("bundle_type")))
        lines.append(label_value("Primary topic", bundle.get("primary_topic")))
        lines.append(label_value("Card count", bundle.get("card_count")))
        lines.append(label_value("Representative card", bundle.get("representative_card_id")))
        lines.append(label_value("Bundle reason", bundle.get("bundle_reason")))
        lines.append("")

        description = clean_text(bundle.get("description"))
        lines.append(heading("Representative Summary", 3))
        if description:
            lines.append(description)
        else:
            lines.append("Summarize the bundle in one or two short paragraphs.")
            fallback_count += 1
        lines.append("")

        card_ids = card_id_list(bundle.get("card_ids"))
        lines.append(heading("Included Cards", 3))
        if card_ids:
            for card_id in card_ids:
                card = card_index.get(card_id, {})
                card_title_text = card_title(card)
                card_line = f"`{card_id}`"
                if card_title_text:
                    card_line = f"{card_line} - {card_title_text}"
                lines.append(bullet(card_line))
        else:
            lines.append(bullet("Add the bundle card list before publishing."))
            fallback_count += 1
        lines.append("")

        lines.append(heading("Card Notes", 3))
        if card_ids:
            for card_id in card_ids:
                card = card_index.get(card_id, {})
                card_summary_text = card_summary(card) or card_title(card)
                card_line = f"`{card_id}`"
                if card_summary_text:
                    card_line = f"{card_line} - {limit_text(card_summary_text, 120)}"
                lines.append(bullet(card_line))
                if not card_summary_text:
                    fallback_count += 1
        else:
            lines.append(bullet("Add one-line notes for the cards in this bundle."))
            fallback_count += 1
        lines.append("")

    return normalize_markdown(lines), fallback_count


def build_cards_markdown(
    cards: list[dict[str, Any]],
    quality_reviews: list[dict[str, Any]],
) -> tuple[str, int]:
    lines: list[str] = [heading("Publish Cards", 1)]
    fallback_count = 0

    lines.append(label_value("Source", "cards"))
    lines.append(label_value("Card count", len(cards)))
    lines.append("")

    if quality_reviews:
        lines.append(heading("Quality Review Snapshot", 2))
        lines.extend(quality_review_snapshot(quality_reviews))
        lines.append("")

    if not cards:
        lines.append("No cards were available, so this export falls back to a compact card note.")
        fallback_count += 1
        return normalize_markdown(lines), fallback_count

    for index, card in enumerate(cards, start=1):
        title = card_title(card)
        if not title:
            title = f"Card {index}"
            fallback_count += 1

        lines.append(heading(title, 2))
        lines.append(label_value("Card ID", card.get("card_id")))
        lines.append(label_value("Topic", card_topic(card)))
        lines.append(label_value("Link", card_link(card), fallback=""))
        lines.append("")

        summary_text = card_summary(card)
        lines.append(heading("Summary", 3))
        if summary_text:
            lines.append(summary_text)
        else:
            lines.append("Add a short summary for this card.")
            fallback_count += 1
        lines.append("")

        if clean_text(card.get("review_note")):
            lines.append(heading("Review Note", 3))
            lines.append(clean_text(card.get("review_note")))
            lines.append("")

    return normalize_markdown(lines), fallback_count


def clean_string_list(value: object, max_items: int, max_len: int) -> list[str]:
    if not isinstance(value, list):
        return []

    items: list[str] = []
    for item in value:
        text = clean_text(item)
        if not text:
            continue
        items.append(limit_text(text, max_len))
        if len(items) >= max_items:
            break
    return items


def clean_body_sections(value: object) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    if not isinstance(value, list):
        return sections

    for item in value:
        if not isinstance(item, dict):
            summary = clean_text(item)
            heading_text = ""
        else:
            summary = clean_text(item.get("summary"))
            heading_text = clean_text(item.get("heading"))
        if not summary:
            continue
        sections.append(
            {
                "heading": heading_text or f"Section {len(sections) + 1}",
                "summary": limit_text(summary, 260),
            }
        )
        if len(sections) >= 4:
            break
    return sections


def normalize_recommended_cards(
    value: object,
    cards: list[dict[str, Any]],
    card_index: dict[str, dict[str, Any]],
) -> list[str]:
    recommended = card_id_list(value)
    if recommended:
        valid_recommended = [card_id for card_id in recommended if card_id in card_index]
        if valid_recommended:
            return valid_recommended[:3]

    fallback_cards: list[str] = []
    for card in cards:
        card_id = clean_text(card.get("card_id"))
        if card_id and card_id not in fallback_cards:
            fallback_cards.append(card_id)
        if len(fallback_cards) >= 3:
            break
    return fallback_cards
