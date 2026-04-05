from __future__ import annotations

from abc import ABC, abstractmethod


class TranslationProvider(ABC):
    provider_name = "base"

    @abstractmethod
    def translate_text(self, text: str, target_lang: str = "ko") -> str:
        raise NotImplementedError


def clean_text(value: object) -> str:
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip()
        if cleaned:
            return cleaned
    return ""
