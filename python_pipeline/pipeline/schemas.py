from __future__ import annotations

from typing import Literal, TypedDict


CandidateStatus = Literal["new", "keep", "review", "drop"]


class RawTopComment(TypedDict):
    comment_id: str
    author: str
    body: str
    score: int
    created_utc: int


class RawKeepRecord(TypedDict):
    raw_id: str
    source: str
    subreddit: str
    post_title: str
    post_url: str
    post_author: str
    post_created_utc: int
    post_body: str
    num_comments: int
    upvotes: int
    top_comments: list[RawTopComment]
    devvit_score: int
    devvit_reason_tags: list[str]
    moderator_status: CandidateStatus
    review_note: str
    collected_at: str
    recommended_status: CandidateStatus
    candidate_rank: int
    post_id: str
    candidate_id: str
    body_excerpt: str
    devvit_version: str


class NormalizedRecord(TypedDict):
    source_id: str
    source: str
    source_type: str
    subreddit: str
    title: str
    source_url: str
    author: str
    created_utc: int
    body: str
    body_excerpt: str
    num_comments: int
    upvotes: int
    top_comments: list[RawTopComment]
    score: int
    reason_tags: list[str]
    recommended_status: CandidateStatus
    moderator_status: CandidateStatus
    review_note: str
    collected_at: str
    devvit_version: str
    post_id: str
    candidate_id: str


class CardRecord(TypedDict):
    card_id: str
    source_id: str
    title: str
    source_url: str
    subreddit: str
    status: CandidateStatus
    score: int
    reason_tags: list[str]
    review_note: str
    top_comment_snippets: list[str]
    created_utc: int
    collected_at: str


class SummaryCardRecord(CardRecord):
    summary: str


class TranslatedCardRecord(CardRecord):
    title_ko: str
    excerpt_ko: str
    summary_ko: str


class TopicCardRecord(CardRecord, total=False):
    summary: str
    title_ko: str
    excerpt_ko: str
    summary_ko: str
    topic_labels: list[str]
    primary_topic: str
    topic_confidence: float
    topic_match_reason: str


class BundleRecord(TypedDict, total=False):
    bundle_id: str
    bundle_type: str
    title: str
    description: str
    primary_topic: str
    card_ids: list[str]
    card_count: int
    representative_card_id: str
    related_topics: list[str]
    bundle_reason: str
    representative_title: str
    representative_summary: str


class BlogDraftRecord(TypedDict, total=False):
    draft_id: str
    source_bundle_id: str
    title: str
    subtitle: str
    intro: str
    key_points: list[str]
    recommended_cards: list[str]
    primary_topic: str
    related_topics: list[str]
    body_sections: list[dict[str, str]]
    closing: str
    draft_status: str
    draft_reason: str


class QualityReviewIssue(TypedDict, total=False):
    severity: str
    field: str
    message: str


class QualityReviewRecord(TypedDict, total=False):
    review_id: str
    review_level: str
    source_id: str
    title: str
    status: str
    score: float
    issues: list[QualityReviewIssue]
    warnings: list[str]
    checks: dict[str, dict[str, str]]
    review_notes: list[str]
    recommended_actions: list[str]
    review_reason: str
