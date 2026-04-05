from __future__ import annotations

import re
from collections import Counter
from typing import Any


PASS_STATUS = "pass"
WARNING_STATUS = "warning"
FAIL_STATUS = "fail"


def clean_text(value: object) -> str:
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip()
        if cleaned:
            return cleaned
    return ""


def clamp_score(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def normalize_card_text(card: dict[str, Any], field_names: tuple[str, ...]) -> str:
    for field_name in field_names:
        text = clean_text(card.get(field_name))
        if text:
            return text
    return ""


def normalize_card_id(card: dict[str, Any]) -> str:
    return clean_text(card.get("card_id"))


def normalize_bundle_id(bundle: dict[str, Any]) -> str:
    return clean_text(bundle.get("bundle_id"))


def normalize_draft_id(draft: dict[str, Any]) -> str:
    return clean_text(draft.get("draft_id"))


def normalize_topics(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    topics: list[str] = []
    for item in value:
        topic = clean_text(item)
        if topic and topic not in topics:
            topics.append(topic)
    return topics


def normalize_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    items: list[str] = []
    for item in value:
        text = clean_text(item)
        if text and text not in items:
            items.append(text)
    return items


def tokenize_text(text: str) -> list[str]:
    return [item for item in re.split(r"[^a-z0-9]+", text.lower()) if item]


def text_overlap_ratio(left: str, right: str) -> float:
    left_tokens = set(tokenize_text(left))
    right_tokens = set(tokenize_text(right))
    if not left_tokens or not right_tokens:
        return 0.0

    overlap = len(left_tokens & right_tokens)
    smallest = min(len(left_tokens), len(right_tokens))
    if smallest <= 0:
        return 0.0
    return overlap / smallest


def count_duplicate_values(values: list[str]) -> int:
    counts = Counter(values)
    duplicate_count = 0
    for count in counts.values():
        if count > 1:
            duplicate_count += count - 1
    return duplicate_count


def build_review_issues_reason(issues: list[dict[str, str]]) -> str:
    if not issues:
        return "no issues found"

    messages: list[str] = []
    for issue in issues[:4]:
        field = issue.get("field", "")
        message = issue.get("message", "")
        if field and message:
            messages.append(f"{field}: {message}")
        elif message:
            messages.append(message)

    return "; ".join(messages)


def build_warning_messages(issues: list[dict[str, str]]) -> list[str]:
    warnings: list[str] = []
    for issue in issues:
        severity = clean_text(issue.get("severity")).lower()
        if severity != WARNING_STATUS:
            continue
        message = clean_text(issue.get("message"))
        if message and message not in warnings:
            warnings.append(message)
    return warnings


def build_checks(issues: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    checks: dict[str, dict[str, str]] = {}
    for issue in issues:
        field = clean_text(issue.get("field")) or "general"
        checks[field] = {
            "status": clean_text(issue.get("severity")).lower() or WARNING_STATUS,
            "message": clean_text(issue.get("message")),
        }
    return checks


def build_review_notes(issues: list[dict[str, str]]) -> list[str]:
    notes: list[str] = []
    for issue in issues:
        field = clean_text(issue.get("field"))
        message = clean_text(issue.get("message"))
        if field and message:
            note = f"{field}: {message}"
        else:
            note = message or field
        if note and note not in notes:
            notes.append(note)
    return notes


def build_recommended_actions(issues: list[dict[str, str]]) -> list[str]:
    if not issues:
        return ["No immediate action needed."]

    actions: list[str] = []
    for issue in issues:
        severity = clean_text(issue.get("severity")).lower()
        field = clean_text(issue.get("field"))
        message = clean_text(issue.get("message"))
        if severity == FAIL_STATUS:
            action = f"Fix {field or 'content'}: {message or 'review the issue'}"
        else:
            action = f"Review {field or 'content'}: {message or 'consider a small improvement'}"
        if action not in actions:
            actions.append(action)
    return actions


def determine_status(issues: list[dict[str, str]]) -> str:
    has_fail = False
    has_warning = False

    for issue in issues:
        severity = clean_text(issue.get("severity")).lower()
        if severity == FAIL_STATUS:
            has_fail = True
        elif severity == WARNING_STATUS:
            has_warning = True

    if has_fail:
        return FAIL_STATUS
    if has_warning:
        return WARNING_STATUS
    return PASS_STATUS


def score_from_issues(issues: list[dict[str, str]]) -> float:
    warning_count = 0
    fail_count = 0

    for issue in issues:
        severity = clean_text(issue.get("severity")).lower()
        if severity == WARNING_STATUS:
            warning_count += 1
        elif severity == FAIL_STATUS:
            fail_count += 1

    score = 1.0 - (warning_count * 0.15) - (fail_count * 0.35)
    return clamp_score(score)


def build_review_record(
    review_level: str,
    source_id: str,
    title: str,
    issues: list[dict[str, str]],
) -> dict[str, Any]:
    warnings = build_warning_messages(issues)
    return {
        "review_id": f"{review_level}_{source_id or 'unknown'}",
        "review_level": review_level,
        "source_id": source_id,
        "title": title,
        "status": determine_status(issues),
        "score": score_from_issues(issues),
        "issues": issues,
        "warnings": warnings,
        "checks": build_checks(issues),
        "review_notes": build_review_notes(issues),
        "recommended_actions": build_recommended_actions(issues),
        "review_reason": build_review_issues_reason(issues),
    }


def add_issue(
    issues: list[dict[str, str]],
    severity: str,
    field: str,
    message: str,
) -> None:
    issues.append(
        {
            "severity": severity,
            "field": field,
            "message": message,
        }
    )
