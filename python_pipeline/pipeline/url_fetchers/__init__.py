from __future__ import annotations

from pipeline.url_fetchers.base import UrlFetcher
from pipeline.url_fetchers.reddit_oauth import RedditOAuthFetcher
from pipeline.url_fetchers.reddit_public import RedditPublicJsonFetcher


def list_url_fetchers() -> tuple[str, ...]:
    return ("reddit_public", "reddit_oauth")


def build_url_fetcher(name: str) -> UrlFetcher:
    normalized_name = name.strip().lower()
    if normalized_name == "reddit_public":
        return RedditPublicJsonFetcher()
    if normalized_name == "reddit_oauth":
        return RedditOAuthFetcher()

    available = ", ".join(list_url_fetchers())
    raise ValueError(f"Unknown URL fetcher: {name}. Available fetchers: {available}.")
