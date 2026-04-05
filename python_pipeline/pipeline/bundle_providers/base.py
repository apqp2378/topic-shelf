from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BundleProvider(ABC):
    provider_name = "base"

    @abstractmethod
    def build_bundles(self, cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError


def clean_text(value: object) -> str:
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip()
        if cleaned:
            return cleaned
    return ""
