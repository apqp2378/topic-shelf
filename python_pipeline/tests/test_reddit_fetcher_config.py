from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = PROJECT_ROOT / "python_pipeline"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.url_fetchers.config import (
    DEFAULT_MAX_RETRY_ATTEMPTS,
    DEFAULT_MORECOMMENTS_ENABLED,
    DEFAULT_MORECOMMENTS_MAX_BATCHES,
    DEFAULT_MORECOMMENTS_MAX_CHILD_IDS,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_RETRY_BACKOFF_SECONDS,
    RedditFetcherConfig,
    load_reddit_fetcher_config,
)
from pipeline.url_fetchers.reddit_oauth import RedditOAuthFetcher
from pipeline.url_fetchers.reddit_public import RedditPublicJsonFetcher
from pipeline.url_fetchers.token_provider import StaticTokenProvider


class RedditFetcherConfigTests(unittest.TestCase):
    def test_default_config_preserves_current_behavior(self) -> None:
        config = load_reddit_fetcher_config({})

        self.assertEqual(config.request_timeout_seconds, DEFAULT_REQUEST_TIMEOUT_SECONDS)
        self.assertEqual(config.max_retry_attempts, DEFAULT_MAX_RETRY_ATTEMPTS)
        self.assertEqual(config.retry_backoff_seconds, DEFAULT_RETRY_BACKOFF_SECONDS)
        self.assertEqual(config.top_comment_limit, 5)
        self.assertTrue(config.morechildren_enabled)
        self.assertEqual(config.morechildren_max_child_ids, DEFAULT_MORECOMMENTS_MAX_CHILD_IDS)
        self.assertEqual(config.morechildren_max_batches, DEFAULT_MORECOMMENTS_MAX_BATCHES)

    def test_env_config_parses_values(self) -> None:
        env = {
            "TOPIC_SHELF_REDDIT_REQUEST_TIMEOUT_SECONDS": "7.5",
            "TOPIC_SHELF_REDDIT_MAX_RETRY_ATTEMPTS": "4",
            "TOPIC_SHELF_REDDIT_RETRY_BACKOFF_SECONDS": "0.5",
            "TOPIC_SHELF_REDDIT_TOP_COMMENT_LIMIT": "3",
            "TOPIC_SHELF_REDDIT_MORECOMMENTS_ENABLED": "false",
            "TOPIC_SHELF_REDDIT_MORECOMMENTS_MAX_CHILD_IDS": "2",
            "TOPIC_SHELF_REDDIT_MORECOMMENTS_MAX_BATCHES": "2",
        }

        config = load_reddit_fetcher_config(env)

        self.assertEqual(config.request_timeout_seconds, 7.5)
        self.assertEqual(config.max_retry_attempts, 4)
        self.assertEqual(config.retry_backoff_seconds, 0.5)
        self.assertEqual(config.top_comment_limit, 3)
        self.assertFalse(config.morechildren_enabled)
        self.assertEqual(config.morechildren_max_child_ids, 2)
        self.assertEqual(config.morechildren_max_batches, 2)

    def test_invalid_config_values_fail_clearly(self) -> None:
        cases = [
            (
                {"TOPIC_SHELF_REDDIT_MAX_RETRY_ATTEMPTS": "zero"},
                r"Invalid integer value for TOPIC_SHELF_REDDIT_MAX_RETRY_ATTEMPTS",
            ),
            (
                {"TOPIC_SHELF_REDDIT_MORECOMMENTS_ENABLED": "maybe"},
                r"Invalid boolean value for TOPIC_SHELF_REDDIT_MORECOMMENTS_ENABLED",
            ),
            (
                {"TOPIC_SHELF_REDDIT_REQUEST_TIMEOUT_SECONDS": "0"},
                r"TOPIC_SHELF_REDDIT_REQUEST_TIMEOUT_SECONDS must be at least 0.001",
            ),
        ]

        for env, expected_message in cases:
            with self.subTest(env=env):
                with self.assertRaisesRegex(ValueError, expected_message):
                    load_reddit_fetcher_config(env)

    def test_public_fetcher_respects_configured_comment_cap(self) -> None:
        payload = build_thread_payload(comment_count=4)
        config = RedditFetcherConfig(
            request_timeout_seconds=8.0,
            max_retry_attempts=4,
            retry_backoff_seconds=0.5,
            top_comment_limit=2,
            morechildren_enabled=False,
            morechildren_max_child_ids=1,
            morechildren_max_batches=1,
        )
        fetcher = RedditPublicJsonFetcher(config=config)

        with mock.patch.object(RedditPublicJsonFetcher, "_load_json", return_value=payload):
            result = fetcher.fetch_thread("https://reddit.com/r/python/comments/cfg001/config-thread")

        self.assertEqual(len(result.top_comments), 2)
        self.assertEqual(result.fetch_metadata["comment_cap"], 2)
        self.assertEqual(result.fetch_metadata["request_timeout_seconds"], 8.0)
        self.assertEqual(
            result.fetch_metadata["retry_policy"],
            {"max_attempts": 4, "backoff_seconds": 0.5},
        )

    def test_oauth_fetcher_can_disable_morecomments_and_reflect_metadata(self) -> None:
        payload = build_thread_payload(comment_count=3, include_more=True)
        config = RedditFetcherConfig(
            request_timeout_seconds=6.5,
            max_retry_attempts=4,
            retry_backoff_seconds=0.75,
            top_comment_limit=2,
            morechildren_enabled=False,
            morechildren_max_child_ids=1,
            morechildren_max_batches=1,
        )
        fetcher = RedditOAuthFetcher(
            config=config,
            token_provider=StaticTokenProvider("token"),
        )

        with mock.patch("pipeline.url_fetchers.reddit_oauth.urlopen", return_value=FakeHTTPResponse(payload)) as urlopen_mock:
            result = fetcher.fetch_thread("https://reddit.com/r/python/comments/cfg001/config-thread")

        self.assertEqual(len(result.top_comments), 2)
        self.assertEqual(result.fetch_metadata["comment_cap"], 2)
        self.assertFalse(result.fetch_metadata["morechildren_enabled"])
        self.assertEqual(result.fetch_metadata["morechildren_request_limit"], 1)
        self.assertEqual(result.fetch_metadata["request_timeout_seconds"], 6.5)
        self.assertEqual(
            result.fetch_metadata["retry_policy"],
            {"max_attempts": 4, "backoff_seconds": 0.75},
        )
        self.assertEqual(result.fetch_metadata["comment_fetch_mode"], "initial_only")
        self.assertEqual(urlopen_mock.call_count, 1)

    def test_local_url_list_ignore_patterns_do_not_match_fixtures(self) -> None:
        gitignore_path = PROJECT_ROOT / ".gitignore"
        ignored_patterns = {
            line.strip()
            for line in gitignore_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }

        fixture_path = Path("python_pipeline/tests/fixtures/reddit_public_edge_short.json")
        self.assertNotIn(fixture_path.as_posix(), ignored_patterns)
        self.assertFalse(any(fixture_path.match(pattern) for pattern in ignored_patterns))


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


def build_thread_payload(
    comment_count: int,
    include_more: bool = False,
) -> list[object]:
    comments = [
        {
            "kind": "t1",
            "data": {
                "id": f"comment_{index + 1}",
                "name": f"t1_comment_{index + 1}",
                "author": f"helper_{index + 1}",
                "body": f"Comment {index + 1}",
                "score": index,
                "created_utc": 1710000000 + index,
            },
        }
        for index in range(comment_count)
    ]
    if include_more:
        comments.append(
            {
                "kind": "more",
                "data": {
                    "children": ["t1_more_1", "t1_more_2"],
                },
            }
        )

    return [
        {
            "data": {
                "children": [
                    {
                        "data": {
                            "name": "t3_cfg001",
                            "id": "cfg001",
                            "subreddit": "python",
                            "title": "Config thread",
                            "permalink": "/r/python/comments/cfg001/config-thread/",
                            "author": "tester",
                            "created_utc": 1710000000,
                            "selftext": "Config body.",
                            "num_comments": comment_count,
                            "ups": 11,
                        }
                    }
                ]
            }
        },
        {
            "data": {
                "children": comments
            }
        },
    ]


if __name__ == "__main__":
    unittest.main()
