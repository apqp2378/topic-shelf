from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.translation_providers.base import TranslationProvider, clean_text
from pipeline.translation_providers.openai import (
    OpenAITranslationProvider,
    normalize_translation_output,
)
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
    translated_field_count: int = 0
    passthrough_count: int = 0
    fallback_count: int = 0
    provider_failure_count: int = 0
    card_failure_count: int = 0


def build_translation_provider(provider_name: str) -> TranslationProvider:
    cleaned_provider_name = clean_text(provider_name).lower()
    if cleaned_provider_name in ("", "passthrough"):
        return PassthroughTranslationProvider()

    if cleaned_provider_name == "openai":
        return OpenAITranslationProvider()

    raise ValueError(f"Unsupported translation provider: {provider_name}")


def translate_card_fields(
    card: dict[str, Any],
    provider: TranslationProvider,
    target_lang: str = "ko",
    card_index: int | None = None,
) -> dict[str, Any]:
    translated_card = dict(card)
    fallback_provider = PassthroughTranslationProvider()
    provider_available = not hasattr(provider, "is_available") or provider.is_available()

    for source_field, target_field in TRANSLATION_FIELD_MAP.items():
        translated_card[target_field] = translate_field_value(
            card,
            provider,
            fallback_provider,
            source_field,
            target_lang,
            card_index,
            provider_available,
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
    fallback_provider = PassthroughTranslationProvider()
    provider_available = not hasattr(provider, "is_available") or provider.is_available()

    if not provider_available and cards:
        print("Translation provider fallback: OPENAI_API_KEY is missing; using passthrough.")
        stats.provider_failure_count += 1

    for index, card in enumerate(cards, start=1):
        translated_card, card_failed, counts = translate_card_with_stats(
            card,
            provider,
            fallback_provider,
            target_lang,
            index,
            provider_available,
        )
        translated_cards.append(translated_card)
        stats.card_failure_count += 1 if card_failed else 0
        stats.empty_field_count += counts["empty_field_count"]
        stats.translated_field_count += counts["translated_field_count"]
        stats.passthrough_count += counts["passthrough_count"]
        stats.fallback_count += counts["fallback_count"]
        stats.provider_failure_count += counts["provider_failure_count"]

    stats.success_count = stats.input_count - stats.card_failure_count
    return translated_cards, stats


def translate_card_with_stats(
    card: dict[str, Any],
    provider: TranslationProvider,
    fallback_provider: TranslationProvider,
    target_lang: str,
    card_index: int,
    provider_available: bool,
) -> tuple[dict[str, Any], bool, dict[str, int]]:
    translated_card = dict(card)
    card_failed = False
    counts = {
        "empty_field_count": 0,
        "translated_field_count": 0,
        "passthrough_count": 0,
        "fallback_count": 0,
        "provider_failure_count": 0,
    }

    for source_field, target_field in TRANSLATION_FIELD_MAP.items():
        translated_text, field_failed, used_passthrough, used_fallback = translate_field_value_with_status(
            card,
            provider,
            fallback_provider,
            source_field,
            target_lang,
            card_index,
            provider_available,
        )
        translated_card[target_field] = translated_text
        if not clean_text(card.get(source_field)):
            counts["empty_field_count"] += 1
        elif clean_text(translated_text):
            counts["translated_field_count"] += 1
            if used_passthrough:
                counts["passthrough_count"] += 1
            if used_fallback:
                counts["fallback_count"] += 1
                counts["provider_failure_count"] += 1
        card_failed = card_failed or field_failed

    return translated_card, card_failed, counts


def translate_field_value(
    card: dict[str, Any],
    provider: TranslationProvider,
    fallback_provider: TranslationProvider | None,
    source_field: str,
    target_lang: str,
    card_index: int | None,
    provider_available: bool = True,
) -> str:
    translated_text, _, _, _ = translate_field_value_with_status(
        card,
        provider,
        fallback_provider or PassthroughTranslationProvider(),
        source_field,
        target_lang,
        card_index,
        provider_available,
    )
    return translated_text


def translate_field_value_with_status(
    card: dict[str, Any],
    provider: TranslationProvider,
    fallback_provider: TranslationProvider,
    source_field: str,
    target_lang: str,
    card_index: int | None,
    provider_available: bool = True,
) -> tuple[str, bool, bool, bool]:
    source_value = card.get(source_field)
    if not isinstance(source_value, str) or not clean_text(source_value):
        return "", False, False, False

    if not hasattr(provider, "is_available") or provider.is_available():
        try:
            translated_text = provider.translate_text(source_value, target_lang=target_lang)
            normalized_text = normalize_translation_output(translated_text)
            if normalized_text:
                return normalized_text, False, provider.provider_name == "passthrough", False
        except Exception as exc:  # pragma: no cover - defensive guard for scaffold stability
            label = card_index if card_index is not None else "unknown"
            print(f"Translation fallback for card index {label}, field {source_field}: {exc}")
            fallback_text = fallback_provider.translate_text(source_value, target_lang=target_lang)
            return normalize_translation_output(fallback_text), True, True, True

    try:
        fallback_text = fallback_provider.translate_text(source_value, target_lang=target_lang)
        return normalize_translation_output(fallback_text), True, True, True
    except Exception as exc:  # pragma: no cover - defensive guard for scaffold stability
        label = card_index if card_index is not None else "unknown"
        print(f"Translation fallback for card index {label}, field {source_field}: {exc}")
        return "", True, False, True
