from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ClassificationProvider(ABC):
    provider_name = "base"

    @abstractmethod
    def classify_card(self, card: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


def clean_text(value: object) -> str:
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip()
        if cleaned:
            return cleaned
    return ""
