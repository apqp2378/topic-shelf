from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PublishExportProvider(ABC):
    provider_name = "base"

    def is_available(self) -> bool:
        return True

    def get_fallback_section_count(self) -> int:
        return 0

    @abstractmethod
    def build_markdown(
        self,
        source_type: str,
        items: list[dict[str, Any]],
        cards: list[dict[str, Any]],
        quality_reviews: list[dict[str, Any]] | None = None,
    ) -> str:
        raise NotImplementedError
