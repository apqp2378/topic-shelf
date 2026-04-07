from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from pipeline.summary_providers.base import SummaryProvider, clean_text
from pipeline.summary_output_model import SummaryOutput


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class OpenAISummaryProvider(SummaryProvider):
    provider_name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        api_url: str | None = None,
    ) -> None:
        self.api_key = clean_text(api_key or os.getenv("OPENAI_API_KEY", ""))
        self.model = clean_text(model or os.getenv("SUMMARY_OPENAI_MODEL", "")) or DEFAULT_OPENAI_MODEL
        self.api_url = clean_text(api_url or os.getenv("SUMMARY_OPENAI_URL", "")) or DEFAULT_OPENAI_URL

    def is_available(self) -> bool:
        return bool(self.api_key)

    def summarize_card(self, card: dict[str, Any], max_len: int = 180) -> str:
        if not self.is_available():
            raise RuntimeError("OPENAI_API_KEY is missing")

        prompt = build_summary_prompt(card, max_len=max_len)
        if not prompt:
            return ""

        response_text = self.request_summary(prompt)
        return parse_summary_output(response_text, max_len=max_len)

    def request_summary(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "max_tokens": 120,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Write a short, stable card-style summary in plain English. "
                        'Prefer compact JSON like {"summary_text":"..."} when convenient, '
                        "but plain text is also acceptable."
                    ),
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
            with urllib.request.urlopen(request, timeout=30) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI summary request failed: {exc}") from exc

        return extract_response_text(response_payload)


def build_summary_prompt(card: dict[str, Any], max_len: int = 180) -> str:
    title = clean_text(card.get("title"))
    excerpt = clean_text(pick_excerpt_text(card))
    comment = clean_text(pick_best_comment_text(card.get("top_comments") or []))
    snippet = clean_text(pick_best_snippet(card.get("top_comment_snippets") or []))

    lines: list[str] = []
    if title:
        lines.append(f"Title: {title}")
    if excerpt:
        lines.append(f"Excerpt: {excerpt}")
    if comment:
        lines.append(f"Top comment: {comment}")
    elif snippet:
        lines.append(f"Top comment: {snippet}")

    if not lines:
        return ""

    return (
        "Summarize this Reddit card in 1-3 short sentences. "
        "Keep it concise, factual, and natural. Avoid copying long phrases verbatim.\n"
        f"{chr(10).join(lines)}"
    )[: max_len * 4]


def pick_excerpt_text(card: dict[str, Any]) -> str:
    for field_name in ("excerpt", "body_excerpt", "review_note"):
        text = clean_text(card.get(field_name))
        if text:
            return text
    return ""


def pick_best_comment_text(top_comments: list[Any]) -> str:
    best_text = ""
    best_length = 0

    for item in top_comments:
        if not isinstance(item, dict):
            continue

        comment_text = clean_text(item.get("body"))
        if not comment_text:
            continue

        comment_text = first_sentence(comment_text)
        comment_length = len(comment_text)
        if comment_length > best_length:
            best_text = comment_text
            best_length = comment_length

    return best_text


def pick_best_snippet(top_comment_snippets: list[Any]) -> str:
    best_text = ""
    best_length = 0

    for item in top_comment_snippets:
        snippet_text = clean_text(item)
        if not snippet_text:
            continue

        snippet_text = first_sentence(snippet_text)
        snippet_length = len(snippet_text)
        if snippet_length > best_length:
            best_text = snippet_text
            best_length = snippet_length

    return best_text


def first_sentence(text: str) -> str:
    for separator in (". ", "! ", "? ", "\n"):
        if separator in text:
            return text.split(separator, 1)[0].strip()
    return text.strip()


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


def parse_summary_output(text: str, max_len: int = 180) -> str:
    raw_text = clean_text(text)
    if not raw_text:
        return ""

    json_candidate = parse_summary_output_json(raw_text)
    if json_candidate:
        return clean_summary_output(json_candidate, max_len=max_len)

    if looks_like_json_payload(raw_text):
        return ""

    plain_text_candidate = parse_summary_output_plain_text(raw_text)
    if plain_text_candidate:
        return clean_summary_output(plain_text_candidate, max_len=max_len)

    return ""


def parse_summary_output_json(text: str) -> str:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return ""

    if not isinstance(payload, dict):
        return ""

    try:
        return SummaryOutput.model_validate(payload).summary_text
    except Exception:
        return ""


def parse_summary_output_plain_text(text: str) -> str:
    try:
        return SummaryOutput.model_validate({"summary_text": text}).summary_text
    except Exception:
        return ""


def looks_like_json_payload(text: str) -> bool:
    return (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]"))


def clean_summary_output(text: str, max_len: int = 180) -> str:
    cleaned = clean_text(text)
    if not cleaned:
        return ""

    if len(cleaned) <= max_len:
        return cleaned

    if max_len <= 3:
        return cleaned[:max_len]

    return cleaned[: max_len - 3].rstrip() + "..."
