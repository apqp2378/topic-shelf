from __future__ import annotations

from pipeline.url_fetchers.base import UrlFetcher
from pipeline.url_fetchers.reddit_public import RedditPublicJsonFetcher


def build_url_fetcher(name: str) -> UrlFetcher:
    normalized_name = name.strip().lower()
    if normalized_name == "reddit_public":
        return RedditPublicJsonFetcher()
    raise ValueError(f"Unknown URL fetcher: {name}")
