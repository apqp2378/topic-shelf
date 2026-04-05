from __future__ import annotations

from typing import Any

from pipeline.classification_providers.base import ClassificationProvider
from pipeline.topic_rules import (
    GENERAL_TOPIC,
    SECTION_WEIGHTS,
    TOPIC_KEYWORDS,
    TOPIC_ORDER,
    build_topic_reason,
    collect_card_text_sections,
    keyword_hits,
)


class RuleBasedClassificationProvider(ClassificationProvider):
    provider_name = "rule_based"

    def classify_card(self, card: dict[str, Any]) -> dict[str, Any]:
        sections = collect_card_text_sections(card)
        if not sections:
            return self.build_fallback_result(empty_text=True)

        topic_scores: dict[str, int] = {topic: 0 for topic in TOPIC_ORDER}
        section_reasons: list[str] = []

        for section_name, section_text in sections:
            section_weight = SECTION_WEIGHTS.get(section_name, 1)
            for topic in TOPIC_ORDER:
                hits = keyword_hits(section_text, TOPIC_KEYWORDS[topic])
                if not hits:
                    continue

                topic_scores[topic] += len(hits) * section_weight
                section_reasons.append(build_topic_reason(topic, hits, section_name))

        sorted_topics = sorted(
            TOPIC_ORDER,
            key=lambda topic: (-topic_scores[topic], TOPIC_ORDER.index(topic)),
        )
        matched_topics = [topic for topic in sorted_topics if topic_scores[topic] > 0]

        if not matched_topics:
            return self.build_fallback_result(
                empty_text=False,
                reason="fallback:no keyword hits",
            )

        primary_topic = matched_topics[0]
        total_score = sum(topic_scores[topic] for topic in matched_topics)
        top_score = topic_scores[primary_topic]
        topic_confidence = round(top_score / total_score, 2) if total_score > 0 else 0.0

        return {
            "topic_labels": matched_topics,
            "primary_topic": primary_topic,
            "topic_confidence": topic_confidence,
            "topic_match_reason": "; ".join(section_reasons[:3]),
        }

    def build_fallback_result(
        self,
        empty_text: bool = False,
        reason: str = "fallback:no keyword hits",
    ) -> dict[str, Any]:
        if empty_text:
            reason = "fallback:no usable text"
        return {
            "topic_labels": [GENERAL_TOPIC],
            "primary_topic": GENERAL_TOPIC,
            "topic_confidence": 0.0 if empty_text else 0.2,
            "topic_match_reason": reason,
        }
