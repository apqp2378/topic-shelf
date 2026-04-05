from __future__ import annotations

from typing import Any


GENERAL_TOPIC = "general_discussion"

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "pricing": (
        "pricing",
        "price",
        "prices",
        "cost",
        "costs",
        "paid",
        "subscription",
        "subscriptions",
        "monthly",
        "annual",
        "tier",
        "tiers",
        "plan",
        "plans",
        "free trial",
        "enterprise",
    ),
    "model_comparison": (
        "compare",
        "comparison",
        "vs",
        "versus",
        "better than",
        "claude vs chatgpt",
        "chatgpt vs claude",
        "gpt-4",
        "gpt-4o",
        "sonnet",
        "opus",
        "haiku",
    ),
    "coding": (
        "code",
        "coding",
        "programming",
        "developer",
        "debugging",
        "debug",
        "refactor",
        "refactoring",
        "python",
        "javascript",
        "typescript",
        "repo",
        "code review",
        "software",
    ),
    "productivity": (
        "productivity",
        "productive",
        "task",
        "tasks",
        "note taking",
        "notes",
        "planning",
        "organize",
        "organization",
        "schedule",
        "time management",
        "daily work",
    ),
    "api_and_tools": (
        "api",
        "sdk",
        "cli",
        "tool",
        "tools",
        "integration",
        "integrations",
        "endpoint",
        "webhook",
        "library",
        "libraries",
        "framework",
        "plugin",
        "plugins",
        "automation",
    ),
    "prompt_engineering": (
        "prompt",
        "prompts",
        "prompting",
        "prompt engineering",
        "system prompt",
        "role prompt",
        "instruction",
        "instructions",
        "jailbreak",
        "few-shot",
        "few shot",
    ),
    "workflow": (
        "workflow",
        "workflows",
        "routine",
        "routines",
        "process",
        "processes",
        "use case",
        "use cases",
        "setup",
        "how do you use",
        "how are you using",
    ),
}

TOPIC_ORDER = tuple(TOPIC_KEYWORDS.keys())
SECTION_WEIGHTS = {
    "title": 3,
    "summary": 2,
    "excerpt": 1,
    "comments": 1,
}


def clean_text(value: object) -> str:
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip().lower()
        if cleaned:
            return cleaned
    return ""


def build_topic_reason(topic: str, matches: list[str], section_name: str | None = None) -> str:
    if not matches:
        return f"{topic}:no-match"

    preview = ", ".join(matches[:3])
    if section_name:
        return f"{section_name}:{topic}:{preview}"
    return f"{topic}:{preview}"


def keyword_hits(text: str, keywords: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for keyword in keywords:
        if keyword and keyword in text and keyword not in hits:
            hits.append(keyword)
    return hits


def collect_card_text_sections(card: dict[str, Any]) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []

    title = clean_text(card.get("title"))
    if title:
        sections.append(("title", title))

    summary = clean_text(card.get("summary"))
    if summary:
        sections.append(("summary", summary))

    excerpt = clean_text(card.get("excerpt"))
    if not excerpt:
        excerpt = clean_text(card.get("body_excerpt"))
    if excerpt:
        sections.append(("excerpt", excerpt))

    comments_text = collect_comment_text(card)
    if comments_text:
        sections.append(("comments", comments_text))

    return sections


def collect_comment_text(card: dict[str, Any]) -> str:
    texts: list[str] = []

    snippets = card.get("top_comment_snippets")
    if isinstance(snippets, list):
        for item in snippets[:3]:
            cleaned = clean_text(item)
            if cleaned:
                texts.append(cleaned)

    top_comments = card.get("top_comments")
    if isinstance(top_comments, list):
        for item in top_comments[:3]:
            if not isinstance(item, dict):
                continue
            cleaned = clean_text(item.get("body"))
            if cleaned:
                texts.append(cleaned)

    unique_texts: list[str] = []
    for text in texts:
        if text not in unique_texts:
            unique_texts.append(text)

    return " ".join(unique_texts)


def has_card_text(card: dict[str, Any]) -> bool:
    return bool(collect_card_text_sections(card))
