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

from pipeline.url_fetchers.base import TOP_COMMENT_LIMIT
from pipeline.url_fetchers.comment_expander import normalize_comment_node
from pipeline.url_fetchers.reddit_oauth import RedditOAuthFetcher
from pipeline.url_fetchers.reddit_parser import (
    extract_post_data,
    extract_thread_comment_snapshot,
    extract_thread_top_comments,
    parse_post_fields,
)
from pipeline.url_fetchers.reddit_public import RedditPublicJsonFetcher
from pipeline.url_fetchers.token_provider import StaticTokenProvider


class FakeHTTPResponse:
    def __init__(self, payload: object):
        self._payload = payload
        self.headers = {}

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload, ensure_ascii=False).encode("utf-8")


class RedditParserTests(unittest.TestCase):
    def test_parse_post_fields_handles_deleted_and_missing_values(self) -> None:
        post_fields = parse_post_fields(
            {
                "id": "abc123",
                "subreddit": "python",
                "title": " Example thread ",
                "author": " ",
                "created_utc": "1710000000",
                "selftext": "",
                "num_comments": "4",
                "ups": "9",
                "permalink": " /r/python/comments/abc123/example-thread/ ",
            }
        )

        self.assertEqual(post_fields.post_id, "t3_abc123")
        self.assertEqual(post_fields.subreddit, "python")
        self.assertEqual(post_fields.title, "Example thread")
        self.assertEqual(post_fields.author, "[deleted]")
        self.assertEqual(post_fields.body, "")
        self.assertEqual(post_fields.created_utc, 1710000000)
        self.assertEqual(post_fields.num_comments, 4)
        self.assertEqual(post_fields.upvotes, 9)
        self.assertEqual(post_fields.permalink, "/r/python/comments/abc123/example-thread/")

    def test_extract_thread_comment_snapshot_handles_partial_payload_sections(self) -> None:
        snapshot = extract_thread_comment_snapshot(
            [
                {"data": {"children": []}},
                {"data": {"children": [{"kind": "more", "data": {"children": ["t1_more_1"]}}]}},
            ]
        )

        self.assertEqual(snapshot.initial_comment_nodes, [])
        self.assertEqual(snapshot.expandable_comment_ids, ["t1_more_1"])
        self.assertEqual(snapshot.comment_fetch_count, 0)

        empty_snapshot = extract_thread_comment_snapshot([])
        self.assertEqual(empty_snapshot.initial_comment_nodes, [])
        self.assertEqual(empty_snapshot.expandable_comment_ids, [])

    def test_public_and_oauth_share_core_parsed_fields(self) -> None:
        payload = load_fixture("reddit_oauth_thread.json")
        public_fetcher = RedditPublicJsonFetcher()
        oauth_fetcher = RedditOAuthFetcher(token_provider=StaticTokenProvider("token"))

        with mock.patch.object(RedditPublicJsonFetcher, "_load_json", return_value=payload):
            public_result = public_fetcher.fetch_thread("https://reddit.com/r/python/comments/oauth001/oauth_thread")

        with mock.patch("pipeline.url_fetchers.reddit_oauth.urlopen", return_value=FakeHTTPResponse(payload)):
            oauth_result = oauth_fetcher.fetch_thread("https://reddit.com/r/python/comments/oauth001/oauth_thread")

        shared_fields = (
            "post_id",
            "subreddit",
            "post_title",
            "post_author",
            "post_created_utc",
            "post_body",
            "num_comments",
            "upvotes",
        )
        for field_name in shared_fields:
            with self.subTest(field_name=field_name):
                self.assertEqual(getattr(public_result, field_name), getattr(oauth_result, field_name))

        self.assertEqual(public_result.top_comments, oauth_result.top_comments)
        self.assertEqual(len(public_result.top_comments), TOP_COMMENT_LIMIT)

    def test_shared_comment_shape_helper_stays_normalized(self) -> None:
        node = {
            "id": "abc123",
            "author": "",
            "body": "  body  ",
            "score": "7",
            "created_utc": "1710000001",
        }

        normalized = normalize_comment_node(node)

        self.assertEqual(normalized["comment_id"], "t1_abc123")
        self.assertEqual(normalized["author"], "[deleted]")
        self.assertEqual(normalized["body"], "body")

    def test_extract_thread_top_comments_caps_and_normalizes(self) -> None:
        payload = load_fixture("reddit_public_edge_long.json")

        top_comments = extract_thread_top_comments(payload, limit=TOP_COMMENT_LIMIT)

        self.assertEqual(len(top_comments), TOP_COMMENT_LIMIT)
        self.assertEqual(top_comments[0]["comment_id"], "t1_comment_1")

    def test_extract_post_data_rejects_partial_payloads(self) -> None:
        cases = [
            [],
            [{}],
            [{"data": {}}],
            [{"data": {"children": []}}],
            [{"data": {"children": [None]}}],
        ]

        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    extract_post_data(payload)


def load_fixture(filename: str) -> object:
    fixture_path = FIXTURES_DIR / filename
    return json.loads(fixture_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
