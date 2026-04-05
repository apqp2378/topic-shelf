from __future__ import annotations

from typing import Any

from pipeline.summary_providers.base import SummaryProvider
from pipeline.summarizers import build_heuristic_summary


class RuleBasedSummaryProvider(SummaryProvider):
    provider_name = "rule_based"

    def summarize_card(self, card: dict[str, Any], max_len: int = 180) -> str:
        return build_heuristic_summary(card, max_len=max_len)
