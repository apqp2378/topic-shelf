from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from pipeline.translation_providers.base import TranslationProvider, clean_text


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class OpenAITranslationProvider(TranslationProvider):
    provider_name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        api_url: str | None = None,
        timeout: int = 30,
    ) -> None:
        self.api_key = clean_text(api_key or os.getenv("OPENAI_API_KEY", ""))
        self.model = clean_text(model or os.getenv("TRANSLATION_OPENAI_MODEL", "")) or DEFAULT_OPENAI_MODEL
        self.api_url = clean_text(api_url or os.getenv("TRANSLATION_OPENAI_URL", "")) or DEFAULT_OPENAI_URL
        self.timeout = timeout
        self._failure_count = 0

    def is_available(self) -> bool:
        return bool(self.api_key)

    def get_failure_count(self) -> int:
        return self._failure_count

    def translate_text(self, text: str, target_lang: str = "ko") -> str:
        cleaned_text = clean_text(text)
        if not cleaned_text:
            return ""

        if self._should_preserve_original(cleaned_text):
            return cleaned_text

        if not self.is_available():
            raise RuntimeError("OPENAI_API_KEY is missing")

        prompt = build_translation_prompt(cleaned_text, target_lang=target_lang)
        response_text = self.request_translation(prompt)
        return normalize_translation_output(response_text, max_len=max(80, len(cleaned_text) * 2))

    def request_translation(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "max_tokens": 160,
            "messages": [
                {
                    "role": "system",
                    "content": "Translate short text into concise natural Korean. Return plain text only.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        }

        request = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            self._failure_count += 1
            raise RuntimeError(f"OpenAI translation request failed: {exc}") from exc

        response_text = extract_response_text(response_payload)
        if not clean_text(response_text):
            self._failure_count += 1
            raise RuntimeError("OpenAI translation response was empty")

        return response_text

    def _should_preserve_original(self, text: str) -> bool:
        hangul_count = sum(1 for char in text if is_hangul(char))
        latin_count = sum(1 for char in text if char.isascii() and char.isalpha())
        return hangul_count > 0 and hangul_count >= latin_count


def build_translation_prompt(text: str, target_lang: str = "ko") -> str:
    return (
        f"Translate the following text into concise {target_lang}. "
        "Keep it short, natural, and faithful. Preserve code, links, product names, and proper nouns when useful. "
        "Return plain text only.\n"
        f"Text: {text}"
    )


def extract_response_text(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts: list[str] = []
                    for item in content:
                        if isinstance(item, dict):
                            text = item.get("text")
                            if isinstance(text, str):
                                parts.append(text)
                    return " ".join(parts)

    output_text = response_payload.get("output_text")
    if isinstance(output_text, str):
        return output_text

    return ""


def normalize_translation_output(text: str, max_len: int = 240) -> str:
    cleaned = clean_text(text)
    if not cleaned:
        return ""

    if len(cleaned) <= max_len:
        return cleaned

    if max_len <= 3:
        return cleaned[:max_len]

    return cleaned[: max_len - 3].rstrip() + "..."


def is_hangul(char: str) -> bool:
    code_point = ord(char)
    return 0xAC00 <= code_point <= 0xD7A3
