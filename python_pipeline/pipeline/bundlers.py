from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.bundle_providers.base import BundleProvider, clean_text
from pipeline.bundle_providers.rule_based import RuleBasedBundleProvider


@dataclass
class BundleStats:
    input_count: int = 0
    bundle_count: int = 0
    weekly_bundle_count: int = 0
    topic_bundle_count: int = 0
    mixed_bundle_count: int = 0
    provider_failure_count: int = 0


def build_bundle_provider(provider_name: str) -> BundleProvider:
    cleaned_provider_name = clean_text(provider_name).lower()
    if cleaned_provider_name in ("", "rule_based", "rule-based"):
        return RuleBasedBundleProvider()

    raise ValueError(f"Unsupported bundle provider: {provider_name}")


def generate_bundles(
    cards: list[dict[str, Any]],
    provider: BundleProvider,
) -> list[dict[str, Any]]:
    bundles, _ = generate_bundles_with_stats(cards, provider)
    return bundles


def generate_bundles_with_stats(
    cards: list[dict[str, Any]],
    provider: BundleProvider,
) -> tuple[list[dict[str, Any]], BundleStats]:
    stats = BundleStats(input_count=len(cards))

    try:
        bundles = provider.build_bundles(cards)
    except Exception as exc:  # pragma: no cover - defensive guard for scaffold stability
        print(f"Bundle generation fallback: {exc}")
        stats.provider_failure_count = 1
        return [], stats

    stats.bundle_count = len(bundles)
    for bundle in bundles:
        bundle_type = clean_text(bundle.get("bundle_type")).lower()
        if bundle_type == "weekly_bundle":
            stats.weekly_bundle_count += 1
        elif bundle_type == "topic_bundle":
            stats.topic_bundle_count += 1
        elif bundle_type == "mixed_bundle":
            stats.mixed_bundle_count += 1

    return bundles, stats
