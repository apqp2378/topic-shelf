from __future__ import annotations

from dataclasses import dataclass
from typing import Any


REQUIRED_RAW_FIELDS = [
    "raw_id",
    "source",
    "subreddit",
    "post_title",
    "post_url",
    "post_author",
    "post_created_utc",
    "post_body",
    "num_comments",
    "upvotes",
    "top_comments",
    "devvit_score",
    "devvit_reason_tags",
    "moderator_status",
    "review_note",
    "collected_at",
]


@dataclass
class ValidationIssue:
    record_index: int
    field_name: str
    message: str


def validate_raw_payload(payload: Any) -> tuple[list[dict[str, Any]], list[ValidationIssue]]:
    issues: list[ValidationIssue] = []

    if not isinstance(payload, list):
        issues.append(
            ValidationIssue(
                record_index=-1,
                field_name="root",
                message="Top-level JSON value must be a list.",
            )
        )
        return [], issues

    valid_records: list[dict[str, Any]] = []

    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            issues.append(
                ValidationIssue(
                    record_index=index,
                    field_name="record",
                    message="Each item must be an object.",
                )
            )
            continue

        record_issues = validate_raw_record(index, item)
        if record_issues:
            issues.extend(record_issues)
            continue

        valid_records.append(item)

    return valid_records, issues


def validate_raw_record(index: int, record: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for field_name in REQUIRED_RAW_FIELDS:
        if field_name not in record:
            issues.append(
                ValidationIssue(
                    record_index=index,
                    field_name=field_name,
                    message="Missing required field.",
                )
            )

    if issues:
        return issues

    if record.get("moderator_status") != "keep":
        issues.append(
            ValidationIssue(
                record_index=index,
                field_name="moderator_status",
                message="Expected moderator_status to be 'keep'.",
            )
        )

    top_comments = record.get("top_comments")
    if not isinstance(top_comments, list):
        issues.append(
            ValidationIssue(
                record_index=index,
                field_name="top_comments",
                message="top_comments must be a list.",
            )
        )

    reason_tags = record.get("devvit_reason_tags")
    if not isinstance(reason_tags, list):
        issues.append(
            ValidationIssue(
                record_index=index,
                field_name="devvit_reason_tags",
                message="devvit_reason_tags must be a list.",
            )
        )

    return issues
