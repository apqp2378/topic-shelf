from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SummaryProvider(ABC):
    provider_name = "base"

    def is_available(self) -> bool:
        return True

    @abstractmethod
    def summarize_card(self, card: dict[str, Any], max_len: int = 180) -> str:
        raise NotImplementedError


def clean_text(value: object) -> str:
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip()
        if cleaned:
            return cleaned
    return ""
