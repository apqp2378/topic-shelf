from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.card_builder import build_cards
from pipeline.io_utils import (
    build_cards_output_path,
    build_cards_with_summary_output_path,
    build_cards_with_translation_output_path,
    build_cards_with_topics_output_path,
    build_normalized_output_path,
    find_latest_json_file,
    read_json_file,
    write_json_file,
)
from pipeline.classifiers import build_classification_provider, classify_cards_with_stats
from pipeline.normalizers import normalize_records
from pipeline.summarizers import enrich_cards_with_summary
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
    summary_input_count = len(cards) if summary_enabled else 0
    summary_success_count = 0
    summary_empty_count = 0
    cards_with_summary = cards
    cards_with_summary_path = cards_path

    print(f"Summary enabled: {'yes' if summary_enabled else 'no'}")
    print(f"Summary input count: {summary_input_count}")

    if summary_enabled:
        cards_with_summary = enrich_cards_with_summary(cards, max_len=args.summary_max_len)
        cards_with_summary_path = build_cards_with_summary_output_path(cards_path)
        write_json_file(cards_with_summary_path, cards_with_summary)
        summary_success_count = sum(
            1 for card in cards_with_summary if clean_string_value(card.get("summary"))
        )
        summary_empty_count = len(cards_with_summary) - summary_success_count
        print(f"Summary output: {cards_with_summary_path}")
    else:
        summary_empty_count = 0

    print(f"Summary success count: {summary_success_count}")
    print(f"Summary empty count: {summary_empty_count}")

    translation_enabled = args.enable_translation
    translation_provider_name = args.translation_provider
    translation_target = args.translation_target
    translation_provider = None
    translation_input_cards = cards_with_summary
    translation_input_path = cards_with_summary_path
    translation_success_count = 0
    translation_empty_field_count = 0
    translation_card_failure_count = 0

    topic_classification_enabled = args.enable_topic_classification
    classification_provider_name = args.classification_provider
    classification_input_cards = cards
    classification_input_path = cards_path
    classification_success_count = 0
    classification_fallback_count = 0
    classification_empty_text_count = 0
    classification_card_failure_count = 0

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
        translation_card_failure_count = translation_stats.card_failure_count
        classification_input_cards = translated_cards
        classification_input_path = translation_output_path
        print(f"Translation output: {translation_output_path}")

    translation_input_count = len(translation_input_cards) if translation_enabled else 0
    print(f"Translation input count: {translation_input_count}")
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
