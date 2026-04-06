from __future__ import annotations

import re

from pydantic import BaseModel, field_validator


INVALID_SUMMARY_VALUES = {"", "n/a", "none", "null", "요약 없음"}


class SummaryOutput(BaseModel):
    summary_text: str

    @field_validator("summary_text", mode="before")
    @classmethod
    def validate_summary_text(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("summary_text must be a string")

        cleaned = re.sub(r"\s+", " ", value).strip()
        if not cleaned:
            raise ValueError("summary_text cannot be empty")

        if cleaned.casefold() in INVALID_SUMMARY_VALUES:
            raise ValueError("summary_text cannot be a placeholder")

        return cleaned
