from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from pipeline.blog_draft_providers.base import BlogDraftProvider, clean_text
from pipeline.blog_draft_providers.rule_based import RuleBasedBlogDraftProvider
from pipeline.blog_providers.rule_based import build_draft_reason
from pipeline.blog_rules import (
    DEFAULT_DRAFT_STATUS,
    FALLBACK_BUNDLE_ID,
    bundle_primary_topic,
    bundle_related_topics,
    card_text,
    card_title,
)


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIBlogDraftProvider(BlogDraftProvider):
    provider_name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        api_url: str | None = None,
        timeout: int = 30,
    ) -> None:
        self.api_key = clean_text(api_key or os.getenv("OPENAI_API_KEY", ""))
        self.model = clean_text(model or os.getenv("BLOG_DRAFT_OPENAI_MODEL", "")) or DEFAULT_OPENAI_MODEL
        self.api_url = clean_text(api_url or os.getenv("BLOG_DRAFT_OPENAI_URL", "")) or DEFAULT_OPENAI_URL
        self.timeout = timeout
        self._failure_count = 0
        self._fallback_provider = RuleBasedBlogDraftProvider()

    def is_available(self) -> bool:
        return bool(self.api_key)

    def get_failure_count(self) -> int:
        return self._failure_count

    def build_drafts(
        self,
        bundles: list[dict[str, Any]],
        cards: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        self._failure_count = 0

        if not self.is_available():
            print("Blog draft provider fallback: OPENAI_API_KEY is missing; using rule_based.")
            drafts = self._fallback_provider.build_drafts(bundles, cards)
            self._failure_count = len(drafts) if (bundles or cards) else 0
            return self.mark_fallback_drafts(drafts, "fallback:openai provider unavailable")

        if bundles:
            return self.build_drafts_for_bundles(bundles, cards)

        if cards:
            try:
                return [self.build_draft_for_cards(cards)]
            except Exception as exc:  # pragma: no cover - defensive guard for handoff stability
                print(f"Blog draft provider fallback for card fallback draft: {exc}")
                self._failure_count += 1
                drafts = self._fallback_provider.build_drafts([], cards)
                return self.mark_fallback_drafts(drafts, "fallback:openai provider error")

        return []

    def build_drafts_for_bundles(
        self,
        bundles: list[dict[str, Any]],
        cards: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        drafts: list[dict[str, Any]] = []

        for index, bundle in enumerate(bundles):
            bundle_cards = select_cards_for_bundle(bundle, cards)
            try:
                drafts.append(self.build_draft_for_bundle(bundle, bundle_cards))
            except Exception as exc:  # pragma: no cover - defensive guard for handoff stability
                print(f"Blog draft provider fallback for bundle index {index}: {exc}")
                self._failure_count += 1
                fallback_draft = self._fallback_provider.build_drafts([bundle], bundle_cards)[0]
                drafts.append(self.mark_fallback_draft(fallback_draft, "fallback:openai provider error"))

        return drafts

    def build_draft_for_cards(self, cards: list[dict[str, Any]]) -> dict[str, Any]:
        synthetic_bundle = build_fallback_bundle(cards)
        return self.build_draft_for_bundle(synthetic_bundle, cards)

    def build_draft_for_bundle(
        self,
        bundle: dict[str, Any],
        cards: list[dict[str, Any]],
    ) -> dict[str, Any]:
        base_draft = self._fallback_provider.build_drafts([bundle], cards)[0]
        prompt = build_blog_draft_prompt(bundle, cards)
        response_text = self.request_completion(prompt)
        response_data = parse_json_object(response_text)
        if not response_data:
            raise RuntimeError("OpenAI blog draft response did not contain JSON object")

        return merge_draft_payload(base_draft, response_data, bundle, cards)

    def request_completion(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0.3,
            "max_tokens": 900,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Write a compact pre-publish blog draft outline in plain English. "
                        "Return JSON only."
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
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI blog draft request failed: {exc}") from exc

        return extract_response_text(response_payload)

    def mark_fallback_drafts(
        self,
        drafts: list[dict[str, Any]],
        reason: str,
    ) -> list[dict[str, Any]]:
        marked_drafts: list[dict[str, Any]] = []
        for draft in drafts:
            marked_drafts.append(self.mark_fallback_draft(draft, reason))
        return marked_drafts

    def mark_fallback_draft(
        self,
        draft: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        marked_draft = dict(draft)
        existing_reason = clean_text(marked_draft.get("draft_reason"))
        note = clean_text(reason)
        if existing_reason and note and note.lower() not in existing_reason.lower():
            marked_draft["draft_reason"] = f"{existing_reason}; {note}"
        elif note:
            marked_draft["draft_reason"] = note
        return marked_draft


def build_blog_draft_prompt(
    bundle: dict[str, Any],
    cards: list[dict[str, Any]],
) -> str:
    title = clean_text(bundle.get("title"))
    description = clean_text(bundle.get("description"))
    primary_topic = bundle_primary_topic(bundle)
    related_topics = bundle_related_topics(bundle)
    representative_title = clean_text(bundle.get("representative_title"))
    representative_summary = clean_text(bundle.get("representative_summary"))

    lines: list[str] = []
    lines.append("Create a short blog draft outline as JSON only.")
    lines.append("Keep it concise, publish-ready, and not overly long.")
    lines.append("Use these keys exactly: title, subtitle, intro, key_points, recommended_cards, body_sections, closing.")
    lines.append("recommended_cards must be a list of card_id strings from the input.")
    lines.append("body_sections must be a list of objects with heading and summary.")
    lines.append("")
    lines.append(f"Bundle id: {clean_text(bundle.get('bundle_id')) or FALLBACK_BUNDLE_ID}")
    lines.append(f"Bundle type: {clean_text(bundle.get('bundle_type')) or 'bundle'}")
    lines.append(f"Primary topic: {primary_topic}")
    if title:
        lines.append(f"Bundle title: {title}")
    if description:
        lines.append(f"Bundle description: {description}")
    if related_topics:
        lines.append(f"Related topics: {', '.join(related_topics)}")
    if representative_title:
        lines.append(f"Representative title: {representative_title}")
    if representative_summary:
        lines.append(f"Representative summary: {representative_summary}")

    lines.append("")
    lines.append("Cards:")
    for index, card in enumerate(cards[:4], start=1):
        card_id = clean_text(card.get("card_id"))
        card_title_text = card_title(card)
        card_summary = card_text(card)
        lines.append(f"{index}. card_id: {card_id}")
        if card_title_text:
            lines.append(f"   title: {card_title_text}")
        if card_summary:
            lines.append(f"   summary: {card_summary}")

    lines.append("")
    lines.append("Return JSON only, with short text fields and 2-5 key points.")
    lines.append("Avoid copying long passages verbatim.")
    lines.append("If something is missing, keep the field short rather than inventing detail.")

    prompt = "\n".join(lines).strip()
    return prompt[:6000]


def merge_draft_payload(
    base_draft: dict[str, Any],
    response_data: dict[str, Any],
    bundle: dict[str, Any],
    cards: list[dict[str, Any]],
) -> dict[str, Any]:
    merged_draft = dict(base_draft)
    valid_card_ids = collect_card_ids(cards)
    bundle_card_ids = collect_bundle_card_ids(bundle)
    for card_id in bundle_card_ids:
        if card_id not in valid_card_ids:
            valid_card_ids.append(card_id)

    merged_draft["title"] = normalize_text_field(
        response_data.get("title"),
        base_draft.get("title"),
        140,
    )
    merged_draft["subtitle"] = normalize_text_field(
        response_data.get("subtitle"),
        base_draft.get("subtitle"),
        180,
    )
    merged_draft["intro"] = normalize_text_field(
        response_data.get("intro"),
        base_draft.get("intro"),
        320,
    )
    merged_draft["key_points"] = normalize_key_points(
        response_data.get("key_points"),
        base_draft.get("key_points"),
    )
    merged_draft["recommended_cards"] = normalize_recommended_cards(
        response_data.get("recommended_cards"),
        base_draft.get("recommended_cards"),
        valid_card_ids,
    )
    merged_draft["body_sections"] = normalize_body_sections(
        response_data.get("body_sections"),
        base_draft.get("body_sections"),
    )
    merged_draft["closing"] = normalize_text_field(
        response_data.get("closing"),
        base_draft.get("closing"),
        220,
    )
    merged_draft["draft_status"] = clean_text(
        response_data.get("draft_status")
    ) or clean_text(base_draft.get("draft_status")) or DEFAULT_DRAFT_STATUS
    merged_draft["draft_reason"] = build_openai_draft_reason(bundle, cards, base_draft)
    return merged_draft


def build_openai_draft_reason(
    bundle: dict[str, Any],
    cards: list[dict[str, Any]],
    base_draft: dict[str, Any],
) -> str:
    bundle_reason = build_draft_reason(bundle, cards, fallback=False)
    base_reason = clean_text(base_draft.get("draft_reason"))
    reason = f"{bundle_reason} via openai"
    if base_reason and base_reason.lower() not in reason.lower():
        reason = f"{reason}; base: {base_reason}"
    return reason


def normalize_text_field(
    value: object,
    fallback_value: object,
    max_len: int,
) -> str:
    text = clean_text(value)
    if not text:
        text = clean_text(fallback_value)
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3].rstrip() + "..."


def normalize_key_points(
    value: object,
    fallback_value: object,
    max_items: int = 5,
) -> list[str]:
    points = clean_string_list(value, max_items=max_items, max_len=180)
    if points:
        return points

    fallback_points = clean_string_list(fallback_value, max_items=max_items, max_len=180)
    if fallback_points:
        return fallback_points
    return ["Use the draft to capture the main angle before expanding."]


def normalize_recommended_cards(
    value: object,
    fallback_value: object,
    valid_card_ids: list[str],
    max_items: int = 3,
) -> list[str]:
    recommended = clean_card_id_list(value, valid_card_ids, max_items=max_items)
    if recommended:
        return recommended

    fallback_recommended = clean_card_id_list(fallback_value, valid_card_ids, max_items=max_items)
    if fallback_recommended:
        return fallback_recommended
    return valid_card_ids[:max_items]


def normalize_body_sections(
    value: object,
    fallback_value: object,
) -> list[dict[str, str]]:
    sections = clean_body_sections(value)
    if len(sections) < 2:
        sections = clean_body_sections(fallback_value)

    if len(sections) < 2:
        sections = [
            {"heading": "Overview", "summary": "Outline the central angle of the draft."},
            {"heading": "Supporting points", "summary": "Add the strongest supporting points next."},
        ]

    return sections[:4]


def clean_body_sections(value: object) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []

    if not isinstance(value, list):
        return sections

    for index, item in enumerate(value, start=1):
        heading = ""
        summary = ""

        if isinstance(item, dict):
            heading = clean_text(item.get("heading"))
            summary = clean_text(item.get("summary"))
        else:
            summary = clean_text(item)

        if not summary:
            continue

        if not heading:
            heading = f"Section {index}"

        sections.append(
            {
                "heading": limit_text(heading, 80),
                "summary": limit_text(summary, 260),
            }
        )
        if len(sections) >= 4:
            break

    return sections


def clean_string_list(value: object, max_items: int, max_len: int) -> list[str]:
    if not isinstance(value, list):
        return []

    items: list[str] = []
    for item in value:
        text = clean_text(item)
        if not text:
            continue
        items.append(limit_text(text, max_len))
        if len(items) >= max_items:
            break
    return items


def clean_card_id_list(
    value: object,
    valid_card_ids: list[str],
    max_items: int,
) -> list[str]:
    if not isinstance(value, list):
        return []

    recommended: list[str] = []
    valid_lookup = set(valid_card_ids)
    for item in value:
        card_id = clean_text(item)
        if not card_id or card_id not in valid_lookup or card_id in recommended:
            continue
        recommended.append(card_id)
        if len(recommended) >= max_items:
            break
    return recommended


def limit_text(text: str, max_len: int) -> str:
    if max_len < 1:
        return ""
    cleaned = clean_text(text)
    if len(cleaned) <= max_len:
        return cleaned
    if max_len <= 3:
        return cleaned[:max_len]
    return cleaned[: max_len - 3].rstrip() + "..."


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned_text = strip_code_fences(text)
    if not cleaned_text:
        return {}

    json_text = extract_json_text(cleaned_text)
    if not json_text:
        return {}

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        return {}

    if isinstance(parsed, dict):
        return parsed
    return {}


def strip_code_fences(text: str) -> str:
    cleaned = clean_text(text)
    if not cleaned.startswith("```"):
        return cleaned

    lines = cleaned.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def extract_json_text(text: str) -> str:
    start_index = text.find("{")
    end_index = text.rfind("}")
    if start_index < 0 or end_index < 0 or end_index <= start_index:
        return ""
    return text[start_index : end_index + 1]


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


def build_fallback_bundle(cards: list[dict[str, Any]]) -> dict[str, Any]:
    representative = cards[0] if cards else {}
    return {
        "bundle_id": FALLBACK_BUNDLE_ID,
        "bundle_type": "fallback_bundle",
        "title": "",
        "description": "",
        "primary_topic": "general_discussion",
        "related_topics": ["general_discussion"],
        "card_ids": collect_card_ids(cards),
        "representative_card_id": clean_text(representative.get("card_id")),
        "representative_title": clean_text(representative.get("title")),
        "representative_summary": clean_text(
            representative.get("summary") or representative.get("excerpt")
        ),
    }


def collect_card_ids(cards: list[dict[str, Any]]) -> list[str]:
    card_ids: list[str] = []
    for card in cards:
        card_id = clean_text(card.get("card_id"))
        if card_id and card_id not in card_ids:
            card_ids.append(card_id)
    return card_ids


def collect_bundle_card_ids(bundle: dict[str, Any]) -> list[str]:
    bundle_card_ids = bundle.get("card_ids")
    if not isinstance(bundle_card_ids, list):
        return []

    card_ids: list[str] = []
    for item in bundle_card_ids:
        card_id = clean_text(item)
        if card_id and card_id not in card_ids:
            card_ids.append(card_id)
    return card_ids


def index_cards_by_id(cards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed_cards: dict[str, dict[str, Any]] = {}
    for card in cards:
        card_id = clean_text(card.get("card_id"))
        if card_id and card_id not in indexed_cards:
            indexed_cards[card_id] = card
    return indexed_cards


def select_cards_for_bundle(
    bundle: dict[str, Any],
    cards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    bundle_card_ids = bundle.get("card_ids")
    if not isinstance(bundle_card_ids, list):
        return cards

    card_lookup = index_cards_by_id(cards)
    selected_cards: list[dict[str, Any]] = []

    for item in bundle_card_ids:
        card_id = clean_text(item)
        if not card_id:
            continue
        card = card_lookup.get(card_id)
        if card is not None:
            selected_cards.append(card)

    if selected_cards:
        return selected_cards
    return cards
