from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


TOP_COMMENT_LIMIT = 5


@dataclass(frozen=True)
class UrlFetchResult:
    canonical_url: str
    subreddit: str
    post_title: str
    post_url: str
    post_author: str
    post_created_utc: int
    post_body: str
    num_comments: int
    upvotes: int
    top_comments: list[dict[str, object]]
    post_id: str


class UrlFetcher(Protocol):
    def fetch_thread(self, canonical_url: str) -> UrlFetchResult:
        ...
