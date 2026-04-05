from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.translation_providers.base import TranslationProvider, clean_text
from pipeline.translation_providers.passthrough import PassthroughTranslationProvider

TRANSLATION_FIELD_MAP = {
    "title": "title_ko",
    "excerpt": "excerpt_ko",
    "summary": "summary_ko",
}


@dataclass
class TranslationStats:
    input_count: int = 0
    success_count: int = 0
    empty_field_count: int = 0
    card_failure_count: int = 0


def build_translation_provider(provider_name: str) -> TranslationProvider:
    cleaned_provider_name = clean_text(provider_name).lower()
    if cleaned_provider_name in ("", "passthrough"):
        return PassthroughTranslationProvider()

    raise ValueError(f"Unsupported translation provider: {provider_name}")


def translate_card_fields(
    card: dict[str, Any],
    provider: TranslationProvider,
    target_lang: str = "ko",
    card_index: int | None = None,
) -> dict[str, Any]:
    translated_card = dict(card)

    for source_field, target_field in TRANSLATION_FIELD_MAP.items():
        translated_card[target_field] = translate_field_value(
            card,
            provider,
            source_field,
            target_lang,
            card_index,
        )

    return translated_card


def enrich_cards_with_translation(
    cards: list[dict[str, Any]],
    provider: TranslationProvider,
    target_lang: str = "ko",
) -> list[dict[str, Any]]:
    translated_cards, _ = translate_cards_with_stats(cards, provider, target_lang)
    return translated_cards


def translate_cards_with_stats(
    cards: list[dict[str, Any]],
    provider: TranslationProvider,
    target_lang: str = "ko",
) -> tuple[list[dict[str, Any]], TranslationStats]:
    translated_cards: list[dict[str, Any]] = []
    stats = TranslationStats(input_count=len(cards))

    for index, card in enumerate(cards, start=1):
        translated_card, card_failed, empty_field_count = translate_card_with_stats(
            card,
            provider,
            target_lang,
            index,
        )
        translated_cards.append(translated_card)
        stats.card_failure_count += 1 if card_failed else 0
        stats.empty_field_count += empty_field_count

    stats.success_count = stats.input_count - stats.card_failure_count
    return translated_cards, stats


def translate_card_with_stats(
    card: dict[str, Any],
    provider: TranslationProvider,
    target_lang: str,
    card_index: int,
) -> tuple[dict[str, Any], bool, int]:
    translated_card = dict(card)
    card_failed = False
    empty_field_count = 0

    for source_field, target_field in TRANSLATION_FIELD_MAP.items():
        translated_text, field_failed = translate_field_value_with_status(
            card,
            provider,
            source_field,
            target_lang,
            card_index,
        )
        translated_card[target_field] = translated_text
        empty_field_count += 1 if not translated_text else 0
        card_failed = card_failed or field_failed

    return translated_card, card_failed, empty_field_count


def translate_field_value(
    card: dict[str, Any],
    provider: TranslationProvider,
    source_field: str,
    target_lang: str,
    card_index: int | None,
) -> str:
    translated_text, _ = translate_field_value_with_status(
        card,
        provider,
        source_field,
        target_lang,
        card_index,
    )
    return translated_text


def translate_field_value_with_status(
    card: dict[str, Any],
    provider: TranslationProvider,
    source_field: str,
    target_lang: str,
    card_index: int | None,
) -> tuple[str, bool]:
    source_value = card.get(source_field)
    if not isinstance(source_value, str) or not clean_text(source_value):
        return "", False

    try:
        translated_text = provider.translate_text(source_value, target_lang=target_lang)
        if not isinstance(translated_text, str):
            return "", False
        if not translated_text.strip():
            return "", False
        return translated_text, False
    except Exception as exc:  # pragma: no cover - defensive guard for scaffold stability
        label = card_index if card_index is not None else "unknown"
        print(f"Translation fallback for card index {label}, field {source_field}: {exc}")
        return "", True
