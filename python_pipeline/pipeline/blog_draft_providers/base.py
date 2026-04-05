from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BlogDraftProvider(ABC):
    provider_name = "base"

    def is_available(self) -> bool:
        return True

    def get_failure_count(self) -> int:
        return 0

    @abstractmethod
    def build_drafts(
        self,
        bundles: list[dict[str, Any]],
        cards: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError


def clean_text(value: object) -> str:
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip()
        if cleaned:
            return cleaned
    return ""
