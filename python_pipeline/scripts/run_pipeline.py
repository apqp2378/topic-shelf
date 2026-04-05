from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.card_builder import build_cards
from pipeline.blog_drafters import build_blog_draft_provider, generate_blog_drafts_with_stats
from pipeline.bundlers import build_bundle_provider, generate_bundles_with_stats
from pipeline.publish_exports import build_publish_export_provider, generate_publish_export
from pipeline.quality_reviewers import (
    build_quality_review_provider,
    build_quality_review_output,
    generate_quality_reviews_with_stats,
)
from pipeline.io_utils import (
    build_blog_drafts_output_path,
    build_bundles_output_path,
    build_cards_output_path,
    build_cards_with_summary_output_path,
    build_cards_with_translation_output_path,
    build_cards_with_topics_output_path,
    build_quality_reviews_output_path,
    build_publish_export_output_path,
    build_normalized_output_path,
    find_latest_json_file,
    read_json_file,
    write_text_file,
    write_json_file,
)
from pipeline.classifiers import build_classification_provider, classify_cards_with_stats
from pipeline.normalizers import normalize_records
from pipeline.summarizers import enrich_cards_with_summary_with_stats
from pipeline.translators import build_translation_provider, translate_cards_with_stats
from pipeline.validators import validate_raw_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Devvit Python pipeline.")
    parser.add_argument(
        "raw_json_path",
        nargs="?",
        type=Path,
        help="Path to the raw JSON input file.",
    )
    parser.add_argument(
        "--enable-summary",
        action="store_true",
        help="Write cards_with_summary output.",
    )
    parser.add_argument(
        "--summary-max-len",
        type=int,
        default=180,
        help="Maximum length for heuristic summaries.",
    )
    parser.add_argument(
        "--summary-provider",
        default="rule_based",
        help="Summary provider name.",
    )
    parser.add_argument(
        "--enable-translation",
        action="store_true",
        help="Write cards_with_translation output.",
    )
    parser.add_argument(
        "--translation-provider",
        default="passthrough",
        help="Translation provider name.",
    )
    parser.add_argument(
        "--translation-target",
        default="ko",
        help="Translation target language code.",
    )
    parser.add_argument(
        "--enable-topic-classification",
        action="store_true",
        help="Write cards_with_topics output.",
    )
    parser.add_argument(
        "--classification-provider",
        default="rule_based",
        help="Classification provider name.",
    )
    parser.add_argument(
        "--enable-bundles",
        action="store_true",
        help="Write bundles output.",
    )
    parser.add_argument(
        "--bundle-provider",
        default="rule_based",
        help="Bundle provider name.",
    )
    parser.add_argument(
        "--enable-blog-drafts",
        action="store_true",
        help="Write blog_drafts output.",
    )
    parser.add_argument(
        "--blog-draft-provider",
        default="rule_based",
        help="Blog draft provider name.",
    )
    parser.add_argument(
        "--enable-quality-review",
        action="store_true",
        help="Write quality_reviews output.",
    )
    parser.add_argument(
        "--quality-review-provider",
        default="rule_based",
        help="Quality review provider name.",
    )
    parser.add_argument(
        "--enable-publish-export",
        action="store_true",
        help="Write publish markdown export.",
    )
    parser.add_argument(
        "--publish-export-provider",
        default="rule_based",
        help="Publish export provider name.",
    )
    return parser.parse_args()


def resolve_input_path(raw_json_path: Path | None) -> Path:
    if raw_json_path is not None:
        return raw_json_path
    return find_latest_json_file(PIPELINE_ROOT / "data" / "raw")


def count_keep_records(payload: object) -> int:
    if not isinstance(payload, list):
        return 0

    keep_count = 0
    for item in payload:
        if isinstance(item, dict) and clean_string_value(item.get("moderator_status")) == "keep":
            keep_count += 1
    return keep_count


def main() -> int:
    args = parse_args()

    if args.summary_max_len < 1:
        print("--summary-max-len must be at least 1.")
        return 1

    raw_path = resolve_input_path(args.raw_json_path)
    payload = read_json_file(raw_path)
    valid_records, issues = validate_raw_payload(payload)
    raw_input_count = len(payload) if isinstance(payload, list) else 0
    keep_count = count_keep_records(payload)
    dropped_count = max(keep_count - len(valid_records), 0)

    print(f"Raw input: {raw_path}")
    print(f"Raw input count: {raw_input_count}")
    print(f"Keep count: {keep_count}")
    print(f"Validated count: {len(valid_records)}")
    print(f"Dropped count: {dropped_count}")

    if issues:
        print("Validation issues:")
        for issue in issues:
            record_number = issue.record_index + 1 if issue.record_index >= 0 else "root"
            print(f"- record {record_number}: {issue.field_name} -> {issue.message}")

    normalized_records = normalize_records(valid_records)
    normalized_path = build_normalized_output_path(raw_path)
    write_json_file(normalized_path, normalized_records)

    cards = build_cards(normalized_records)
    cards_path = build_cards_output_path(normalized_path)
    write_json_file(cards_path, cards)

    print(f"Normalized output: {normalized_path}")
    print(f"Normalized count: {len(normalized_records)}")
    print(f"Cards output: {cards_path}")
    print(f"Cards count: {len(cards)}")

    summary_enabled = args.enable_summary
    summary_provider_name = args.summary_provider
    summary_input_count = len(cards) if summary_enabled else 0
    summary_success_count = 0
    summary_empty_count = 0
    summary_fallback_count = 0
    summary_provider_failure_count = 0
    cards_with_summary = cards
    cards_with_summary_path = cards_path

    print(f"Summary enabled: {'yes' if summary_enabled else 'no'}")
    print(f"Summary provider: {summary_provider_name}")
    print(f"Summary input count: {summary_input_count}")

    if summary_enabled:
        try:
            cards_with_summary, summary_stats = enrich_cards_with_summary_with_stats(
                cards,
                max_len=args.summary_max_len,
                provider_name=summary_provider_name,
            )
        except ValueError as exc:
            print(str(exc))
            return 1

        cards_with_summary_path = build_cards_with_summary_output_path(cards_path)
        write_json_file(cards_with_summary_path, cards_with_summary)
        summary_success_count = summary_stats.success_count
        summary_empty_count = summary_stats.empty_count
        summary_fallback_count = summary_stats.fallback_count
        summary_provider_failure_count = summary_stats.provider_failure_count
        print(f"Summary output: {cards_with_summary_path}")
    else:
        summary_empty_count = 0

    print(f"Summary success count: {summary_success_count}")
    print(f"Summary empty count: {summary_empty_count}")
    print(f"Summary fallback count: {summary_fallback_count}")
    print(f"Summary provider failure count: {summary_provider_failure_count}")

    translation_enabled = args.enable_translation
    translation_provider_name = args.translation_provider
    translation_target = args.translation_target
    translation_provider = None
    translation_input_cards = cards_with_summary
    translation_input_path = cards_with_summary_path
    translation_success_count = 0
    translation_empty_field_count = 0
    translation_translated_field_count = 0
    translation_passthrough_count = 0
    translation_fallback_count = 0
    translation_provider_failure_count = 0
    translation_card_failure_count = 0

    topic_classification_enabled = args.enable_topic_classification
    classification_provider_name = args.classification_provider
    classification_input_cards = cards
    classification_input_path = cards_path
    classification_success_count = 0
    classification_fallback_count = 0
    classification_empty_text_count = 0
    classification_card_failure_count = 0

    bundle_enabled = args.enable_bundles
    bundle_provider_name = args.bundle_provider
    bundle_input_cards = cards
    bundle_input_path = cards_path
    bundle_count = 0
    weekly_bundle_count = 0
    topic_bundle_count = 0
    mixed_bundle_count = 0
    provider_failure_count = 0
    bundles: list[dict[str, object]] = []
    bundles_output_path = cards_path

    blog_drafts_enabled = args.enable_blog_drafts
    blog_draft_provider_name = args.blog_draft_provider
    blog_bundle_records: list[dict[str, object]] = []
    blog_bundle_input_path = bundle_input_path
    blog_drafts: list[dict[str, object]] = []
    blog_drafts_output_path = cards_path
    blog_draft_count = 0
    blog_fallback_draft_count = 0
    blog_provider_failure_count = 0

    quality_review_enabled = args.enable_quality_review
    quality_review_provider_name = args.quality_review_provider
    quality_review_cards = cards
    quality_review_cards_path = cards_path
    quality_review_cards_count = len(quality_review_cards)
    quality_review_source_label = "cards"
    quality_review_source_file = str(cards_path)
    quality_reviews: list[dict[str, object]] = []
    quality_review_count = 0
    quality_pass_count = 0
    quality_warning_count = 0
    quality_fail_count = 0
    quality_provider_failure_count = 0

    publish_export_enabled = args.enable_publish_export
    publish_export_provider_name = args.publish_export_provider
    publish_source_type = "cards"
    publish_source_items = cards
    publish_source_path = cards_path
    publish_markdown = ""
    publish_output_path = cards_path.parent.parent / "publish" / f"publish_cards_{cards_path.name}"
    publish_generated_file_count = 0
    publish_fallback_section_count = 0

    if summary_enabled:
        classification_input_cards = cards_with_summary
        classification_input_path = cards_with_summary_path

    print(f"Translation enabled: {'yes' if translation_enabled else 'no'}")
    print(f"Translation provider: {translation_provider_name}")
    print(f"Translation target: {translation_target}")

    if translation_enabled:
        try:
            translation_provider = build_translation_provider(translation_provider_name)
        except ValueError as exc:
            print(str(exc))
            return 1

        translated_cards, translation_stats = translate_cards_with_stats(
            translation_input_cards,
            translation_provider,
            target_lang=translation_target,
        )
        translation_output_path = build_cards_with_translation_output_path(
            translation_input_path
        )
        write_json_file(translation_output_path, translated_cards)
        translation_success_count = translation_stats.success_count
        translation_empty_field_count = translation_stats.empty_field_count
        translation_translated_field_count = translation_stats.translated_field_count
        translation_passthrough_count = translation_stats.passthrough_count
        translation_fallback_count = translation_stats.fallback_count
        translation_provider_failure_count = translation_stats.provider_failure_count
        translation_card_failure_count = translation_stats.card_failure_count
        classification_input_cards = translated_cards
        classification_input_path = translation_output_path
        print(f"Translation output: {translation_output_path}")

    translation_input_count = len(translation_input_cards) if translation_enabled else 0
    print(f"Translation input count: {translation_input_count}")
    print(f"Translation translated field count: {translation_translated_field_count}")
    print(f"Translation passthrough count: {translation_passthrough_count}")
    print(f"Translation fallback count: {translation_fallback_count}")
    print(f"Translation provider failure count: {translation_provider_failure_count}")
    print(f"Translation success count: {translation_success_count}")
    print(f"Translation empty field count: {translation_empty_field_count}")
    print(f"Translation card failure count: {translation_card_failure_count}")

    classification_input_count = (
        len(classification_input_cards) if topic_classification_enabled else 0
    )
    print(f"Topic classification enabled: {'yes' if topic_classification_enabled else 'no'}")
    print(f"Classification provider: {classification_provider_name}")
    print(f"Classification input count: {classification_input_count}")

    if topic_classification_enabled:
        try:
            classification_provider = build_classification_provider(
                classification_provider_name
            )
        except ValueError as exc:
            print(str(exc))
            return 1

        classified_cards, classification_stats = classify_cards_with_stats(
            classification_input_cards,
            classification_provider,
        )
        topics_output_path = build_cards_with_topics_output_path(classification_input_path)
        write_json_file(topics_output_path, classified_cards)
        classification_success_count = classification_stats.success_count
        classification_fallback_count = classification_stats.fallback_count
        classification_empty_text_count = classification_stats.empty_text_count
        classification_card_failure_count = classification_stats.card_failure_count
        print(f"Topic output path: {topics_output_path}")

    print(f"Topic success count: {classification_success_count}")
    print(f"Topic fallback count: {classification_fallback_count}")
    print(f"Topic empty text count: {classification_empty_text_count}")
    print(f"Topic card failure count: {classification_card_failure_count}")

    if topic_classification_enabled:
        bundle_input_cards = classified_cards
        bundle_input_path = topics_output_path
    elif translation_enabled:
        bundle_input_cards = translated_cards
        bundle_input_path = translation_output_path
    elif summary_enabled:
        bundle_input_cards = cards_with_summary
        bundle_input_path = cards_with_summary_path

    bundle_input_count = len(bundle_input_cards) if bundle_enabled else 0
    print(f"Bundles enabled: {'yes' if bundle_enabled else 'no'}")
    print(f"Bundle provider: {bundle_provider_name}")
    print(f"Bundle input count: {bundle_input_count}")

    if bundle_enabled:
        try:
            bundle_provider = build_bundle_provider(bundle_provider_name)
        except ValueError as exc:
            print(str(exc))
            return 1

        bundles, bundle_stats = generate_bundles_with_stats(
            bundle_input_cards,
            bundle_provider,
        )
        bundles_output_path = build_bundles_output_path(bundle_input_path)
        write_json_file(bundles_output_path, bundles)
        blog_bundle_records = bundles
        blog_bundle_input_path = bundles_output_path
        bundle_count = bundle_stats.bundle_count
        weekly_bundle_count = bundle_stats.weekly_bundle_count
        topic_bundle_count = bundle_stats.topic_bundle_count
        mixed_bundle_count = bundle_stats.mixed_bundle_count
        provider_failure_count = bundle_stats.provider_failure_count
        print(f"Bundles output path: {bundles_output_path}")
    else:
        candidate_bundles_path = build_bundles_output_path(bundle_input_path)
        if candidate_bundles_path.exists():
            try:
                loaded_bundles = read_json_file(candidate_bundles_path)
            except Exception:
                loaded_bundles = []
            if isinstance(loaded_bundles, list):
                blog_bundle_records = loaded_bundles
                blog_bundle_input_path = candidate_bundles_path

    print(f"Bundle count: {bundle_count}")
    print(f"Weekly bundle count: {weekly_bundle_count}")
    print(f"Topic bundle count: {topic_bundle_count}")
    print(f"Mixed bundle count: {mixed_bundle_count}")
    print(f"Provider failure count: {provider_failure_count}")

    blog_card_input_cards = bundle_input_cards
    blog_card_input_count = len(blog_card_input_cards) if blog_drafts_enabled else 0
    blog_bundle_input_count = len(blog_bundle_records) if blog_drafts_enabled else 0
    print(f"Blog drafts enabled: {'yes' if blog_drafts_enabled else 'no'}")
    print(f"Blog draft provider: {blog_draft_provider_name}")
    print(f"Blog draft bundle input count: {blog_bundle_input_count}")
    print(f"Blog draft card input count: {blog_card_input_count}")

    if blog_drafts_enabled:
        try:
            blog_draft_provider = build_blog_draft_provider(blog_draft_provider_name)
        except ValueError as exc:
            print(str(exc))
            return 1

        blog_drafts, blog_stats = generate_blog_drafts_with_stats(
            blog_bundle_records,
            blog_card_input_cards,
            blog_draft_provider,
        )
        blog_drafts_output_path = build_blog_drafts_output_path(blog_bundle_input_path)
        write_json_file(blog_drafts_output_path, blog_drafts)
        blog_draft_count = blog_stats.draft_count
        blog_fallback_draft_count = blog_stats.fallback_draft_count
        blog_provider_failure_count = blog_stats.provider_failure_count
        print(f"Blog drafts output path: {blog_drafts_output_path}")

    print(f"Blog draft generated count: {blog_draft_count}")
    print(f"Blog draft count: {blog_draft_count}")
    print(f"Blog fallback draft count: {blog_fallback_draft_count}")
    print(f"Blog provider failure count: {blog_provider_failure_count}")

    if summary_enabled:
        quality_review_cards = cards_with_summary
        quality_review_cards_path = cards_with_summary_path
        quality_review_source_label = "cards_with_summary"
        quality_review_source_file = str(cards_with_summary_path)
    if translation_enabled:
        quality_review_cards = translated_cards
        quality_review_cards_path = translation_output_path
        quality_review_source_label = "cards_with_translation"
        quality_review_source_file = str(translation_output_path)
    if topic_classification_enabled:
        quality_review_cards = classified_cards
        quality_review_cards_path = topics_output_path
        quality_review_source_label = "cards_with_topics"
        quality_review_source_file = str(topics_output_path)

    if bundle_enabled and bundles:
        quality_review_source_label = "bundles"
        quality_review_source_file = str(bundles_output_path)

    if blog_drafts_enabled and blog_drafts:
        quality_review_source_label = "blog_drafts"
        quality_review_source_file = str(blog_drafts_output_path)

    quality_review_cards_count = len(quality_review_cards)
    quality_bundles = bundles if bundle_enabled else []
    quality_blog_drafts = blog_drafts if blog_drafts_enabled else []

    quality_review_card_input_count = len(quality_review_cards) if quality_review_enabled else 0
    quality_review_bundle_input_count = len(quality_bundles) if quality_review_enabled else 0
    quality_review_blog_input_count = len(quality_blog_drafts) if quality_review_enabled else 0

    print(f"Quality review enabled: {'yes' if quality_review_enabled else 'no'}")
    print(f"Quality review provider: {quality_review_provider_name}")
    print(f"Quality review card input count: {quality_review_card_input_count}")
    print(f"Quality review bundle input count: {quality_review_bundle_input_count}")
    print(f"Quality review blog draft input count: {quality_review_blog_input_count}")

    if quality_review_enabled:
        try:
            quality_review_provider = build_quality_review_provider(
                quality_review_provider_name
            )
        except ValueError as exc:
            print(str(exc))
            return 1

        quality_reviews, quality_stats = generate_quality_reviews_with_stats(
            quality_review_cards,
            quality_bundles,
            quality_blog_drafts,
            quality_review_provider,
        )
        quality_reviews_output_path = build_quality_reviews_output_path(quality_review_cards_path)
        quality_review_output = build_quality_review_output(
            source_file=quality_review_source_file,
            review_provider=quality_review_provider_name,
            reviews=quality_reviews,
            stats=quality_stats,
            input_summary={
                "source_priority": quality_review_source_label,
                "card_input_count": quality_review_cards_count,
                "bundle_input_count": len(quality_bundles),
                "blog_draft_input_count": len(quality_blog_drafts),
            },
        )
        write_json_file(quality_reviews_output_path, quality_review_output)
        quality_review_count = quality_stats.review_count
        quality_pass_count = quality_stats.pass_count
        quality_warning_count = quality_stats.warning_count
        quality_fail_count = quality_stats.fail_count
        quality_provider_failure_count = quality_stats.provider_failure_count
        print(f"Quality reviews output path: {quality_reviews_output_path}")

    print(f"Quality review count: {quality_review_count}")
    print(f"Quality review pass count: {quality_pass_count}")
    print(f"Quality review warning count: {quality_warning_count}")
    print(f"Quality review fail count: {quality_fail_count}")
    print(f"Quality provider failure count: {quality_provider_failure_count}")

    publish_quality_reviews = quality_reviews if quality_review_enabled else []

    if blog_drafts_enabled and blog_drafts:
        publish_source_type = "blog_drafts"
        publish_source_items = blog_drafts
        publish_source_path = blog_drafts_output_path
    elif bundle_enabled and bundles:
        publish_source_type = "bundles"
        publish_source_items = bundles
        publish_source_path = bundles_output_path
    elif topic_classification_enabled and classified_cards:
        publish_source_items = classified_cards
        publish_source_path = topics_output_path
    elif translation_enabled and translated_cards:
        publish_source_items = translated_cards
        publish_source_path = translation_output_path
    elif summary_enabled and cards_with_summary:
        publish_source_items = cards_with_summary
        publish_source_path = cards_with_summary_path

    print(f"Publish export enabled: {'yes' if publish_export_enabled else 'no'}")
    print(f"Publish export source type: {publish_source_type}")
    print(f"Publish export input count: {len(publish_source_items) if publish_export_enabled else 0}")

    if publish_export_enabled:
        try:
            publish_export_provider = build_publish_export_provider(publish_export_provider_name)
        except ValueError as exc:
            print(str(exc))
            return 1

        publish_markdown, publish_stats = generate_publish_export(
            publish_source_type,
            publish_source_items,
            cards,
            publish_export_provider,
            quality_reviews=publish_quality_reviews,
        )
        publish_output_path = build_publish_export_output_path(publish_source_path, publish_source_type)
        write_text_file(publish_output_path, publish_markdown)
        publish_generated_file_count = publish_stats.generated_file_count
        publish_fallback_section_count = publish_stats.fallback_section_count
        print(f"Publish output path: {publish_output_path}")

    print(f"Publish generated file count: {publish_generated_file_count}")
    print(f"Publish fallback section count: {publish_fallback_section_count}")

    if issues:
        return 1
    return 0


def clean_string_value(value: object) -> str:
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
