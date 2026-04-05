from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.publish_exporters.base import PublishExportProvider
from pipeline.publish_exporters.rule_based import RuleBasedPublishExportProvider
from pipeline.publish_rules import clean_text


@dataclass
class PublishExportStats:
    input_count: int = 0
    generated_file_count: int = 0
    fallback_section_count: int = 0
    provider_failure_count: int = 0


def build_publish_export_provider(provider_name: str) -> PublishExportProvider:
    cleaned_provider_name = clean_text(provider_name).lower()
    if cleaned_provider_name in ("", "rule_based", "rule-based"):
        return RuleBasedPublishExportProvider()

    raise ValueError(f"Unsupported publish export provider: {provider_name}")


def generate_publish_export(
    source_type: str,
    items: list[dict[str, Any]],
    cards: list[dict[str, Any]],
    provider: PublishExportProvider,
    quality_reviews: list[dict[str, Any]] | None = None,
) -> tuple[str, PublishExportStats]:
    stats = PublishExportStats(input_count=len(items))

    try:
        markdown = provider.build_markdown(source_type, items, cards, quality_reviews=quality_reviews)
    except Exception as exc:  # pragma: no cover - defensive guard for handoff stability
        print(f"Publish export fallback: {exc}")
        stats.provider_failure_count = 1
        fallback_provider = RuleBasedPublishExportProvider()
        markdown = fallback_provider.build_markdown(
            source_type,
            items,
            cards,
            quality_reviews=quality_reviews,
        )
        stats.fallback_section_count = fallback_provider.get_fallback_section_count()
        stats.generated_file_count = 1 if clean_text(markdown) else 0
        return markdown, stats

    stats.fallback_section_count = provider.get_fallback_section_count()
    stats.generated_file_count = 1 if clean_text(markdown) else 0
    return markdown, stats
