from __future__ import annotations

from typing import Any

from pipeline.blog_draft_providers.base import BlogDraftProvider
from pipeline.blog_providers.rule_based import (
    RuleBasedBlogDraftProvider as LegacyRuleBasedBlogDraftProvider,
)


class RuleBasedBlogDraftProvider(BlogDraftProvider):
    provider_name = "rule_based"

    def __init__(self) -> None:
        self._legacy_provider = LegacyRuleBasedBlogDraftProvider()

    def build_drafts(
        self,
        bundles: list[dict[str, Any]],
        cards: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self._legacy_provider.build_drafts(bundles, cards)
