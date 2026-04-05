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
