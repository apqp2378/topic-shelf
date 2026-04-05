from __future__ import annotations

from typing import Any

from pipeline.quality_review_providers.base import QualityReviewProvider, clean_text
from pipeline.quality_review_rules import (
    FAIL_STATUS,
    WARNING_STATUS,
    add_issue,
    build_review_record,
    count_duplicate_values,
    normalize_bundle_id,
    normalize_card_id,
    normalize_draft_id,
    normalize_string_list,
    normalize_topics,
    normalize_card_text,
    text_overlap_ratio,
)


class RuleBasedQualityReviewProvider(QualityReviewProvider):
    provider_name = "rule_based"

    def review(
        self,
        cards: list[dict[str, Any]],
        bundles: list[dict[str, Any]],
        blog_drafts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        reviews: list[dict[str, Any]] = []

        for index, draft in enumerate(blog_drafts, start=1):
            reviews.append(self.review_blog_draft(draft, index))

        for index, bundle in enumerate(bundles, start=1):
            reviews.append(self.review_bundle(bundle, cards, index))

        for index, card in enumerate(cards, start=1):
            reviews.append(self.review_card(card, index))

        return reviews

    def review_card(self, card: dict[str, Any], card_index: int) -> dict[str, Any]:
        issues: list[dict[str, str]] = []

        title = normalize_card_text(card, ("title", "title_ko"))
        summary = normalize_card_text(card, ("summary", "summary_ko"))
        excerpt = normalize_card_text(card, ("excerpt", "excerpt_ko", "body_excerpt"))
        primary_topic = clean_text(card.get("primary_topic"))
        topic_confidence = card.get("topic_confidence")
        title_ko = clean_text(card.get("title_ko"))
        summary_ko = clean_text(card.get("summary_ko"))
        excerpt_ko = clean_text(card.get("excerpt_ko"))

        if not title:
            add_issue(issues, FAIL_STATUS, "title", "title is missing")

        if not summary:
            add_issue(issues, WARNING_STATUS, "summary", "summary is missing")
        elif len(summary) < 20:
            add_issue(issues, WARNING_STATUS, "summary", "summary is shorter than the minimum length")

        if title and excerpt and text_overlap_ratio(title, excerpt) >= 0.8:
            add_issue(issues, WARNING_STATUS, "excerpt", "title and excerpt are too similar")

        if not primary_topic and ("topic_labels" in card or "topic_confidence" in card or "topic_match_reason" in card):
            add_issue(issues, WARNING_STATUS, "primary_topic", "primary_topic is missing")

        if "topic_confidence" in card:
            if not isinstance(topic_confidence, (int, float)) or isinstance(topic_confidence, bool):
                add_issue(issues, WARNING_STATUS, "topic_confidence", "topic_confidence is not numeric")
            elif float(topic_confidence) < 0.0 or float(topic_confidence) > 1.0:
                add_issue(issues, WARNING_STATUS, "topic_confidence", "topic_confidence is outside the normal range")

        if not title and not summary and not excerpt:
            add_issue(issues, WARNING_STATUS, "content", "content is too sparse")

        if title and title_ko and title == title_ko:
            add_issue(issues, WARNING_STATUS, "title_ko", "translation title matches the source title exactly")
        if summary and summary_ko and summary == summary_ko:
            add_issue(issues, WARNING_STATUS, "summary_ko", "translation summary matches the source summary exactly")
        if excerpt and excerpt_ko and excerpt == excerpt_ko:
            add_issue(issues, WARNING_STATUS, "excerpt_ko", "translation excerpt matches the source excerpt exactly")

        source_id = normalize_card_id(card) or f"card-{card_index}"
        review = build_review_record("card", source_id, title or summary or source_id, issues)
        review["review_index"] = card_index
        return review

    def review_bundle(
        self,
        bundle: dict[str, Any],
        cards: list[dict[str, Any]],
        bundle_index: int,
    ) -> dict[str, Any]:
        issues: list[dict[str, str]] = []
        card_ids = normalize_string_list(bundle.get("card_ids"))
        bundle_type = clean_text(bundle.get("bundle_type"))
        primary_topic = clean_text(bundle.get("primary_topic"))
        title = clean_text(bundle.get("title"))
        description = clean_text(bundle.get("description"))
        representative_id = clean_text(bundle.get("representative_card_id"))
        related_topics = normalize_topics(bundle.get("related_topics"))
        card_lookup = index_cards_by_id(cards)

        if not card_ids:
            add_issue(issues, FAIL_STATUS, "card_ids", "card_ids is empty")

        if title and len(title) < 8:
            add_issue(issues, WARNING_STATUS, "title", "bundle title is too short")
        if description and len(description) < 15:
            add_issue(issues, WARNING_STATUS, "description", "bundle summary is too short")
        if not title:
            add_issue(issues, WARNING_STATUS, "title", "bundle preview title is missing")
        if not description:
            add_issue(issues, WARNING_STATUS, "description", "bundle preview summary is missing")

        if representative_id and representative_id not in card_ids:
            add_issue(issues, WARNING_STATUS, "representative_card_id", "representative card is not included in card_ids")

        duplicate_count = count_duplicate_values(card_ids)
        duplicate_ratio = (duplicate_count / len(card_ids)) if card_ids else 0.0
        if duplicate_ratio > 0.0:
            add_issue(issues, WARNING_STATUS, "card_ids", "duplicate card ids are present")

        card_count = len(card_ids)
        if card_count == 0:
            add_issue(issues, FAIL_STATUS, "card_count", "bundle has no cards")
        elif card_count > 12:
            add_issue(issues, WARNING_STATUS, "card_count", "bundle size is larger than expected")

        if bundle_type == "topic_bundle":
            bundle_topics: list[str] = []
            for card_id in card_ids:
                card = card_lookup.get(card_id)
                if not card:
                    continue
                topic = clean_text(card.get("primary_topic"))
                if topic:
                    bundle_topics.append(topic)
            if bundle_topics and any(topic != primary_topic for topic in bundle_topics):
                add_issue(issues, WARNING_STATUS, "primary_topic", "topic bundle cards are not fully consistent")
            if card_count < 2:
                add_issue(issues, WARNING_STATUS, "card_count", "topic bundle is too small")

        if related_topics and primary_topic and primary_topic not in related_topics:
            add_issue(issues, WARNING_STATUS, "related_topics", "primary topic is not reflected in related topics")

        source_id = normalize_bundle_id(bundle) or f"bundle-{bundle_index}"
        review = build_review_record("bundle", source_id, title or source_id, issues)
        review["bundle_type"] = bundle_type
        review["card_count"] = card_count
        review["review_index"] = bundle_index
        return review

    def review_blog_draft(
        self,
        draft: dict[str, Any],
        draft_index: int,
    ) -> dict[str, Any]:
        issues: list[dict[str, str]] = []
        title = clean_text(draft.get("title"))
        subtitle = clean_text(draft.get("subtitle"))
        intro = clean_text(draft.get("intro"))
        key_points = normalize_string_list(draft.get("key_points"))
        body_sections = draft.get("body_sections")
        closing = clean_text(draft.get("closing"))
        recommended_cards = normalize_string_list(draft.get("recommended_cards"))
        primary_topic = clean_text(draft.get("primary_topic"))

        if not title:
            add_issue(issues, FAIL_STATUS, "title", "draft title is missing")
        if not subtitle:
            add_issue(issues, WARNING_STATUS, "subtitle", "draft subtitle is missing")
        if not intro:
            add_issue(issues, FAIL_STATUS, "intro", "draft intro is missing")
        if not closing:
            add_issue(issues, FAIL_STATUS, "closing", "draft closing is missing")
        if not key_points:
            add_issue(issues, WARNING_STATUS, "key_points", "draft key points are missing")
        if not recommended_cards:
            add_issue(issues, WARNING_STATUS, "recommended_cards", "recommended cards are missing")

        if not isinstance(body_sections, list) or not body_sections:
            add_issue(issues, FAIL_STATUS, "body_sections", "draft body sections are missing")
        else:
            headings: list[str] = []
            for section in body_sections:
                if not isinstance(section, dict):
                    continue
                heading = clean_text(section.get("heading"))
                summary = clean_text(section.get("summary"))
                if heading:
                    headings.append(heading)
                if not heading or not summary:
                    add_issue(issues, WARNING_STATUS, "body_sections", "a body section is incomplete")

            if count_duplicate_values(headings) > 0:
                add_issue(issues, WARNING_STATUS, "body_sections", "duplicate section headings are present")

            if len(body_sections) < 2:
                add_issue(issues, WARNING_STATUS, "body_sections", "draft is too thin")

        if len(key_points) < 2:
            add_issue(issues, WARNING_STATUS, "key_points", "draft key points are too few")
        body_section_count = len(body_sections) if isinstance(body_sections, list) else 0
        if body_section_count < 2:
            add_issue(issues, WARNING_STATUS, "body_sections", "draft content density is low")

        repeated_title_hits = 0
        if title and subtitle and title == subtitle:
            repeated_title_hits += 1
        if title and intro and title in intro:
            repeated_title_hits += 1
        if title and closing and title in closing:
            repeated_title_hits += 1
        if repeated_title_hits > 1:
            add_issue(issues, WARNING_STATUS, "title", "title is repeated too often across the draft")

        if primary_topic and primary_topic.lower() == "general_discussion" and not recommended_cards:
            add_issue(issues, WARNING_STATUS, "primary_topic", "draft is too generic")

        source_id = normalize_draft_id(draft) or f"draft-{draft_index}"
        review = build_review_record("blog_draft", source_id, title or source_id, issues)
        review["draft_status"] = clean_text(draft.get("draft_status")) or "draft"
        review["review_index"] = draft_index
        return review


def index_cards_by_id(cards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed_cards: dict[str, dict[str, Any]] = {}
    for card in cards:
        card_id = normalize_card_id(card)
        if card_id and card_id not in indexed_cards:
            indexed_cards[card_id] = card
    return indexed_cards
