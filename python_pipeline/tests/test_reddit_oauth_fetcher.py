from __future__ import annotations

import json
import os
import sys
import shutil
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = PROJECT_ROOT / "python_pipeline"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.url_fetchers import build_url_fetcher
from pipeline.url_fetchers.base import TOP_COMMENT_LIMIT
from pipeline.url_fetchers.reddit_oauth import RedditOAuthFetcher, build_oauth_reddit_json_url
from pipeline.url_fetchers.token_provider import StaticTokenProvider
from pipeline.url_ingestion import ingest_url_list


class FakeHTTPResponse:
    def __init__(self, payload: object):
        self._payload = payload

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload, ensure_ascii=False).encode("utf-8")


class RedditOAuthFetcherTests(unittest.TestCase):
    def test_successful_fetch_parses_payload_and_caps_comments(self) -> None:
        payload = load_fixture("reddit_oauth_thread.json")
        fetcher = RedditOAuthFetcher(token_provider=StaticTokenProvider("token"))
        canonical_url = "https://reddit.com/r/python/comments/oauth001/oauth_thread"

        with mock.patch("pipeline.url_fetchers.reddit_oauth.urlopen", return_value=FakeHTTPResponse(payload)) as urlopen_mock:
            result = fetcher.fetch_thread(canonical_url)

        self.assertEqual(result.post_id, "t3_oauth001")
        self.assertEqual(result.subreddit, "python")
        self.assertEqual(result.post_title, "OAuth thread")
        self.assertEqual(result.post_author, "tester")
        self.assertEqual(result.post_body, "OAuth body text.")
        self.assertEqual(result.upvotes, 42)
        self.assertEqual(result.num_comments, 6)
        self.assertEqual(len(result.top_comments), TOP_COMMENT_LIMIT)
        self.assertEqual(result.top_comments[0]["comment_id"], "t1_comment_1")
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.full_url, build_oauth_reddit_json_url(canonical_url))
        self.assertEqual(request.get_header("Authorization"), "bearer token")

    def test_missing_token_raises_clear_error(self) -> None:
        fetcher = RedditOAuthFetcher()

        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                RuntimeError,
                r"Missing OAuth token\. Set the TOPIC_SHELF_REDDIT_OAUTH_TOKEN environment variable\.",
            ):
                fetcher.fetch_thread("https://reddit.com/r/python/comments/oauth001/oauth_thread")

    def test_builder_returns_oauth_fetcher(self) -> None:
        self.assertIsInstance(build_url_fetcher("reddit_oauth"), RedditOAuthFetcher)

    def test_http_error_handling_is_explicit(self) -> None:
        canonical_url = "https://reddit.com/r/python/comments/oauth001/oauth_thread"
        fetcher = RedditOAuthFetcher(token_provider=StaticTokenProvider("token"))

        cases = [
            (401, r"Reddit OAuth request failed with HTTP 401\."),
            (403, r"Reddit OAuth request failed with HTTP 403\."),
            (404, r"Reddit OAuth request failed with HTTP 404\."),
        ]

        for status_code, expected_message in cases:
            with self.subTest(status_code=status_code):
                with mock.patch(
                    "pipeline.url_fetchers.reddit_oauth.urlopen",
                    side_effect=HTTPError(canonical_url, status_code, "error", hdrs=None, fp=None),
                ):
                    with self.assertRaisesRegex(RuntimeError, expected_message):
                        fetcher.fetch_thread(canonical_url)

    def test_retryable_http_errors_retry_then_succeed(self) -> None:
        canonical_url = "https://reddit.com/r/python/comments/oauth001/oauth_thread"
        payload = load_fixture("reddit_oauth_thread.json")
        fetcher = RedditOAuthFetcher(
            token_provider=StaticTokenProvider("token"),
            backoff_seconds=0.0,
            max_attempts=2,
        )

        for status_code in (429, 500):
            with self.subTest(status_code=status_code):
                with mock.patch(
                    "pipeline.url_fetchers.reddit_oauth.urlopen",
                    side_effect=[
                        HTTPError(canonical_url, status_code, "retry", hdrs=None, fp=None),
                        FakeHTTPResponse(payload),
                    ],
                ) as urlopen_mock:
                    with mock.patch("pipeline.url_fetchers.reddit_oauth.time.sleep") as sleep_mock:
                        result = fetcher.fetch_thread(canonical_url)

                self.assertEqual(result.post_id, "t3_oauth001")
                self.assertEqual(len(result.top_comments), TOP_COMMENT_LIMIT)
                self.assertEqual(urlopen_mock.call_count, 2)
                sleep_mock.assert_called_once()

    def test_ingest_works_with_oauth_fetcher_and_mocked_http(self) -> None:
        payload = load_fixture("reddit_oauth_thread.json")
        fetcher = RedditOAuthFetcher(token_provider=StaticTokenProvider("token"))

        with mock.patch("pipeline.url_fetchers.reddit_oauth.urlopen", return_value=FakeHTTPResponse(payload)):
            with mock.patch.dict(os.environ, {}, clear=True):
                with make_temp_url_list() as url_list_path:
                    result = ingest_url_list(
                        url_list_path,
                        fetcher,
                        output_path=url_list_path.parent / "raw.json",
                    )

        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failure_count, 0)
        self.assertEqual(result.records[0]["post_id"], "t3_oauth001")
        self.assertEqual(len(result.records[0]["top_comments"]), TOP_COMMENT_LIMIT)


def load_fixture(filename: str) -> object:
    fixture_path = FIXTURES_DIR / filename
    return json.loads(fixture_path.read_text(encoding="utf-8"))


@contextmanager
def make_temp_url_list() -> Path:
    temp_dir = PIPELINE_ROOT / "data" / "test_tmp" / "oauth_fetcher"
    temp_dir.mkdir(parents=True, exist_ok=True)
    path = temp_dir / "urls.txt"
    path.write_text("https://reddit.com/r/python/comments/oauth001/oauth_thread\n", encoding="utf-8")
    try:
        yield path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
