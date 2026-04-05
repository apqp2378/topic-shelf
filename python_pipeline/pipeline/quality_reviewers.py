from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from pipeline.quality_review_providers.base import QualityReviewProvider, clean_text
from pipeline.quality_review_providers.rule_based import RuleBasedQualityReviewProvider


@dataclass
class QualityReviewStats:
    card_input_count: int = 0
    bundle_input_count: int = 0
    blog_draft_input_count: int = 0
    review_count: int = 0
    pass_count: int = 0
    warning_count: int = 0
    fail_count: int = 0
    provider_failure_count: int = 0


QUALITY_REVIEW_VERSION = "v2-6"


def build_quality_review_provider(provider_name: str) -> QualityReviewProvider:
    cleaned_provider_name = clean_text(provider_name).lower()
    if cleaned_provider_name in ("", "rule_based", "rule-based"):
        return RuleBasedQualityReviewProvider()

    raise ValueError(f"Unsupported quality review provider: {provider_name}")


def generate_quality_reviews(
    cards: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
    blog_drafts: list[dict[str, Any]],
    provider: QualityReviewProvider,
) -> list[dict[str, Any]]:
    reviews, _ = generate_quality_reviews_with_stats(cards, bundles, blog_drafts, provider)
    return reviews


def generate_quality_reviews_with_stats(
    cards: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
    blog_drafts: list[dict[str, Any]],
    provider: QualityReviewProvider,
) -> tuple[list[dict[str, Any]], QualityReviewStats]:
    stats = QualityReviewStats(
        card_input_count=len(cards),
        bundle_input_count=len(bundles),
        blog_draft_input_count=len(blog_drafts),
    )

    try:
        reviews = provider.review(cards, bundles, blog_drafts)
    except Exception as exc:  # pragma: no cover - defensive guard for scaffold stability
        print(f"Quality review fallback: {exc}")
        stats.provider_failure_count = 1
        return [], stats

    stats.review_count = len(reviews)
    for review in reviews:
        status = clean_text(review.get("status")).lower()
        if status == "pass":
            stats.pass_count += 1
        elif status == "warning":
            stats.warning_count += 1
        elif status == "fail":
            stats.fail_count += 1

    return reviews, stats


def build_quality_review_output(
    source_file: str,
    review_provider: str,
    reviews: list[dict[str, Any]],
    stats: QualityReviewStats,
    input_summary: dict[str, Any],
    review_version: str = QUALITY_REVIEW_VERSION,
) -> dict[str, Any]:
    card_reviews: list[dict[str, Any]] = []
    bundle_reviews: list[dict[str, Any]] = []
    blog_draft_reviews: list[dict[str, Any]] = []

    for review in reviews:
        review_level = clean_text(review.get("review_level")).lower()
        if review_level == "card":
            card_reviews.append(review)
        elif review_level == "bundle":
            bundle_reviews.append(review)
        elif review_level == "blog_draft":
            blog_draft_reviews.append(review)

    overall_score = calculate_overall_score(reviews)
    overall_status = calculate_overall_status(reviews)

    return {
        "source_file": source_file,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "review_provider": review_provider,
        "review_version": review_version,
        "input_summary": input_summary,
        "overall_status": overall_status,
        "overall_score": overall_score,
        "summary_stats": {
            "card_input_count": stats.card_input_count,
            "bundle_input_count": stats.bundle_input_count,
            "blog_draft_input_count": stats.blog_draft_input_count,
            "review_count": stats.review_count,
            "pass_count": stats.pass_count,
            "warning_count": stats.warning_count,
            "fail_count": stats.fail_count,
            "provider_failure_count": stats.provider_failure_count,
        },
        "card_reviews": card_reviews,
        "bundle_reviews": bundle_reviews,
        "blog_draft_reviews": blog_draft_reviews,
    }


def calculate_overall_status(reviews: list[dict[str, Any]]) -> str:
    if not reviews:
        return "pass"

    has_warning = False
    for review in reviews:
        status = clean_text(review.get("status")).lower()
        if status == "fail":
            return "fail"
        if status == "warning":
            has_warning = True

    if has_warning:
        return "warning"
    return "pass"


def calculate_overall_score(reviews: list[dict[str, Any]]) -> float:
    if not reviews:
        return 1.0

    total = 0.0
    for review in reviews:
        score = review.get("score")
        if isinstance(score, bool):
            continue
        if isinstance(score, int):
            total += float(score)
        elif isinstance(score, float):
            total += score

    average = total / len(reviews)
    if average < 0.0:
        return 0.0
    if average > 1.0:
        return 1.0
    return average
