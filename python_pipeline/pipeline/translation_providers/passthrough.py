from __future__ import annotations

from pipeline.translation_providers.base import TranslationProvider, clean_text


class PassthroughTranslationProvider(TranslationProvider):
    provider_name = "passthrough"

    def translate_text(self, text: str, target_lang: str = "ko") -> str:
        return clean_text(text)
