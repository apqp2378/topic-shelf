from __future__ import annotations

from pipeline.url_fetchers.base import UrlFetchResult


class RedditOAuthFetcher:
    """Placeholder fetcher for the future OAuth-based Reddit URL ingestion path.

    This class mirrors the public fetcher interface so fetcher selection can be
    wired in now without enabling any real OAuth network flow yet.
    """

    def fetch_thread(self, canonical_url: str) -> UrlFetchResult:
        raise NotImplementedError(
            "RedditOAuthFetcher is a placeholder. OAuth token / approval flow is "
            "not implemented yet."
        )
