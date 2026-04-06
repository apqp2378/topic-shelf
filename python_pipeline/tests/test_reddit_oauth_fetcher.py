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
    def __init__(self, payload: object, headers: dict[str, str] | None = None):
        self._payload = payload
        self.headers = headers or {}

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
        self.assertEqual(result.fetch_metadata["fetch_mode"], "oauth")
        self.assertEqual(result.fetch_metadata["comment_fetch_count"], 6)
        self.assertEqual(result.fetch_metadata["comment_fetch_depth"], 0)
        self.assertEqual(result.fetch_metadata["expandable_comment_ids"], [])
        self.assertEqual(result.fetch_metadata["ratelimit_snapshot"], {})
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.full_url, build_oauth_reddit_json_url(canonical_url))
        self.assertEqual(request.get_header("Authorization"), "bearer token")

    def test_one_morechildren_pass_merges_expanded_comments(self) -> None:
        payload = [
            {
                "data": {
                    "children": [
                        {
                            "data": {
                                "name": "t3_more001",
                                "id": "more001",
                                "subreddit": "python",
                                "title": "More comments thread",
                                "permalink": "/r/python/comments/more001/more_comments_thread/",
                                "author": "tester",
                                "created_utc": 1712222222,
                                "selftext": "Body text.",
                                "num_comments": 2,
                                "ups": 9,
                            }
                        }
                    ]
                }
            },
            {
                "data": {
                    "children": [
                        {
                            "kind": "t1",
                            "data": {
                                "id": "comment_1",
                                "name": "t1_comment_1",
                                "author": "helper_1",
                                "body": "Comment 1",
                                "score": 3,
                                "created_utc": 1712222223,
                            },
                        },
                        {
                            "kind": "more",
                            "data": {
                                "children": ["t1_more_1", "t1_more_2"],
                            },
                        },
                    ]
                }
            },
        ]
        morechildren_payload = {
            "json": {
                "data": {
                    "things": [
                        {
                            "kind": "t1",
                            "data": {
                                "id": "more_1",
                                "name": "t1_more_1",
                                "author": "helper_2",
                                "body": "Comment 2",
                                "score": 2,
                                "created_utc": 1712222224,
                            },
                        }
                    ]
                }
            }
        }
        fetcher = RedditOAuthFetcher(token_provider=StaticTokenProvider("token"))

        with mock.patch(
            "pipeline.url_fetchers.reddit_oauth.urlopen",
            side_effect=[
                FakeHTTPResponse(payload),
                FakeHTTPResponse(morechildren_payload),
            ],
        ):
            result = fetcher.fetch_thread("https://reddit.com/r/python/comments/more001/more_comments_thread")

        self.assertEqual(len(result.top_comments), 2)
        self.assertEqual([item["comment_id"] for item in result.top_comments], ["t1_comment_1", "t1_more_1"])
        self.assertEqual(result.fetch_metadata["comment_fetch_mode"], "initial_plus_morechildren")
        self.assertTrue(result.fetch_metadata["morechildren_expansion_attempted"])
        self.assertTrue(result.fetch_metadata["morechildren_expansion_succeeded"])
        self.assertEqual(result.fetch_metadata["expandable_comment_ids_found"], ["t1_more_1", "t1_more_2"])
        self.assertEqual(result.fetch_metadata["expandable_comment_ids_requested"], ["more_1", "more_2"])
        self.assertEqual(result.fetch_metadata["comment_fetch_count"], 2)

    def test_morechildren_merge_still_respects_shared_cap(self) -> None:
        payload = load_fixture("reddit_oauth_thread.json")
        payload[1]["data"]["children"] = [
            payload[1]["data"]["children"][0],
            {
                "kind": "more",
                "data": {
                    "children": ["t1_more_1", "t1_more_2", "t1_more_3", "t1_more_4", "t1_more_5", "t1_more_6"],
                },
            },
        ]
        morechildren_payload = {
            "json": {
                "data": {
                    "things": [
                        {
                            "kind": "t1",
                            "data": {
                                "id": f"more_{index + 1}",
                                "name": f"t1_more_{index + 1}",
                                "author": f"helper_{index + 1}",
                                "body": f"Comment {index + 2}",
                                "score": index,
                                "created_utc": 1712222230 + index,
                            },
                        }
                        for index in range(6)
                    ]
                }
            }
        }
        fetcher = RedditOAuthFetcher(token_provider=StaticTokenProvider("token"))

        with mock.patch(
            "pipeline.url_fetchers.reddit_oauth.urlopen",
            side_effect=[
                FakeHTTPResponse(payload),
                FakeHTTPResponse(morechildren_payload),
            ],
        ):
            result = fetcher.fetch_thread("https://reddit.com/r/python/comments/oauth001/oauth_thread")

        self.assertEqual(len(result.top_comments), TOP_COMMENT_LIMIT)
        self.assertEqual(result.fetch_metadata["comment_fetch_mode"], "initial_plus_morechildren")
        self.assertTrue(result.fetch_metadata["morechildren_expansion_succeeded"])
        self.assertEqual(result.fetch_metadata["comment_fetch_count"], 7)

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

    def test_failed_morechildren_expansion_preserves_initial_comments(self) -> None:
        payload = [
            {
                "data": {
                    "children": [
                        {
                            "data": {
                                "name": "t3_fail001",
                                "id": "fail001",
                                "subreddit": "python",
                                "title": "Failed expansion thread",
                                "permalink": "/r/python/comments/fail001/failed_expansion_thread/",
                                "author": "tester",
                                "created_utc": 1713333333,
                                "selftext": "Body text.",
                                "num_comments": 1,
                                "ups": 10,
                            }
                        }
                    ]
                }
            },
            {
                "data": {
                    "children": [
                        {
                            "kind": "t1",
                            "data": {
                                "id": "comment_1",
                                "name": "t1_comment_1",
                                "author": "helper",
                                "body": "Initial comment",
                                "score": 1,
                                "created_utc": 1713333334,
                            },
                        },
                        {
                            "kind": "more",
                            "data": {
                                "children": ["t1_more_1"],
                            },
                        },
                    ]
                }
            },
        ]
        fetcher = RedditOAuthFetcher(token_provider=StaticTokenProvider("token"), backoff_seconds=0.0, max_attempts=2)
        rate_headers = {
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": "2.5",
        }

        with mock.patch(
            "pipeline.url_fetchers.reddit_oauth.urlopen",
            side_effect=[
                FakeHTTPResponse(payload),
                HTTPError("https://oauth.reddit.com/api/morechildren", 429, "retry", hdrs=rate_headers, fp=None),
                HTTPError("https://oauth.reddit.com/api/morechildren", 429, "retry", hdrs=rate_headers, fp=None),
            ],
        ):
            with mock.patch("pipeline.url_fetchers.reddit_oauth.time.sleep") as sleep_mock:
                result = fetcher.fetch_thread("https://reddit.com/r/python/comments/fail001/failed_expansion_thread")

        self.assertEqual(len(result.top_comments), 1)
        self.assertEqual(result.top_comments[0]["comment_id"], "t1_comment_1")
        self.assertEqual(result.fetch_metadata["comment_fetch_mode"], "initial_plus_morechildren_failed")
        self.assertTrue(result.fetch_metadata["morechildren_expansion_attempted"])
        self.assertFalse(result.fetch_metadata["morechildren_expansion_succeeded"])
        self.assertEqual(result.fetch_metadata["expandable_comment_ids_requested"], ["more_1"])
        self.assertIn("Rate limit snapshot", result.fetch_metadata["morechildren_expansion_error"])
        self.assertEqual(result.fetch_metadata["morechildren_ratelimit_snapshot"]["remaining"], 0)
        self.assertEqual(sleep_mock.call_count, 1)

    def test_rate_limit_snapshot_is_reported_after_retries(self) -> None:
        canonical_url = "https://reddit.com/r/python/comments/oauth001/oauth_thread"
        fetcher = RedditOAuthFetcher(
            token_provider=StaticTokenProvider("token"),
            backoff_seconds=0.0,
            max_attempts=2,
        )

        rate_headers = {
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": "2.5",
            "x-ratelimit-used": "60",
        }

        with mock.patch(
            "pipeline.url_fetchers.reddit_oauth.urlopen",
            side_effect=[
                HTTPError(canonical_url, 429, "retry", hdrs=rate_headers, fp=None),
                HTTPError(canonical_url, 429, "retry", hdrs=rate_headers, fp=None),
            ],
        ):
            with mock.patch("pipeline.url_fetchers.reddit_oauth.time.sleep") as sleep_mock:
                with self.assertRaisesRegex(
                    RuntimeError,
                    r"Rate limit snapshot: \{remaining=0, reset=2.5, used=60\}",
                ):
                    fetcher.fetch_thread(canonical_url)

        self.assertEqual(sleep_mock.call_count, 1)

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
