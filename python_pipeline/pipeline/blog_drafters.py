from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.blog_draft_providers.base import BlogDraftProvider, clean_text
from pipeline.blog_draft_providers.openai import OpenAIBlogDraftProvider
from pipeline.blog_draft_providers.rule_based import RuleBasedBlogDraftProvider


@dataclass
class BlogDraftStats:
    bundle_input_count: int = 0
    card_input_count: int = 0
    draft_count: int = 0
    fallback_draft_count: int = 0
    provider_failure_count: int = 0


def build_blog_draft_provider(provider_name: str) -> BlogDraftProvider:
    cleaned_provider_name = clean_text(provider_name).lower()
    if cleaned_provider_name in ("", "rule_based", "rule-based"):
        return RuleBasedBlogDraftProvider()

    if cleaned_provider_name == "openai":
        return OpenAIBlogDraftProvider()

    raise ValueError(f"Unsupported blog draft provider: {provider_name}")


def generate_blog_drafts(
    bundles: list[dict[str, Any]],
    cards: list[dict[str, Any]],
    provider: BlogDraftProvider,
) -> list[dict[str, Any]]:
    drafts, _ = generate_blog_drafts_with_stats(bundles, cards, provider)
    return drafts


def generate_blog_drafts_with_stats(
    bundles: list[dict[str, Any]],
    cards: list[dict[str, Any]],
    provider: BlogDraftProvider,
) -> tuple[list[dict[str, Any]], BlogDraftStats]:
    stats = BlogDraftStats(bundle_input_count=len(bundles), card_input_count=len(cards))

    try:
        if hasattr(provider, "is_available") and not provider.is_available():
            print("Blog draft provider fallback: openai is not configured; using rule_based.")
            if bundles or cards:
                stats.provider_failure_count += 1
            provider = RuleBasedBlogDraftProvider()

        drafts = provider.build_drafts(bundles, cards)
    except Exception as exc:  # pragma: no cover - defensive guard for scaffold stability
        print(f"Blog draft generation fallback: {exc}")
        stats.provider_failure_count = 1
        provider = RuleBasedBlogDraftProvider()
        drafts = provider.build_drafts(bundles, cards)

    stats.draft_count = len(drafts)
    for draft in drafts:
        source_bundle_id = clean_text(draft.get("source_bundle_id"))
        draft_reason = clean_text(draft.get("draft_reason")).lower()
        if source_bundle_id == "fallback_bundle_1" or "fallback" in draft_reason:
            stats.fallback_draft_count += 1

    if hasattr(provider, "get_failure_count"):
        stats.provider_failure_count += provider.get_failure_count()

    return drafts, stats
