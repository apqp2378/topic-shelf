from __future__ import annotations

import json
import sys
import shutil
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
from uuid import uuid4
from types import SimpleNamespace
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = PROJECT_ROOT / "python_pipeline"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.io_utils import read_json_file
from pipeline.url_fetchers import build_url_fetcher, list_url_fetchers
from pipeline.url_fetchers.base import TOP_COMMENT_LIMIT, UrlFetchResult
from pipeline.url_fetchers.reddit_public import RedditPublicJsonFetcher, extract_top_comments
from pipeline.url_ingestion import (
    build_body_excerpt,
    canonicalize_and_dedupe_urls,
    canonicalize_reddit_thread_url,
    ingest_url_list,
    normalize_top_comments,
)
from pipeline.validators import validate_raw_payload


class FakeFetcher:
    def __init__(self, results: dict[str, UrlFetchResult], failures: dict[str, str] | None = None):
        self._results = results
        self._failures = failures or {}

    def fetch_thread(self, canonical_url: str) -> UrlFetchResult:
        if canonical_url in self._failures:
            raise RuntimeError(self._failures[canonical_url])
        if canonical_url not in self._results:
            raise RuntimeError("missing fake payload")
        return self._results[canonical_url]


@contextmanager
def make_test_root() -> Path:
    base_dir = PROJECT_ROOT / "python_pipeline" / "data" / "test_tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = base_dir / f"url-ingestion-test-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class UrlIngestionTests(unittest.TestCase):
    def test_empty_url_list(self) -> None:
        with make_test_root() as root:
            input_path = root / "data" / "url_lists" / "empty.txt"
            output_path = root / "data" / "raw" / "raw_from_urls_empty.json"
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text("\n# comment only\n\n", encoding="utf-8")

            result = ingest_url_list(input_path, FakeFetcher({}), output_path=output_path)

            self.assertEqual(result.input_count, 0)
            self.assertEqual(result.unique_count, 0)
            self.assertEqual(result.success_count, 0)
            self.assertEqual(result.failure_count, 0)
            self.assertEqual(read_json_file(output_path), [])

    def test_single_url_success_and_validator_pass(self) -> None:
        with make_test_root() as root:
            input_path = root / "data" / "url_lists" / "single.txt"
            output_path = root / "data" / "raw" / "raw_from_urls_single.json"
            input_url = (
                "https://www.reddit.com/r/python/comments/abc123/example-thread/?utm_source=test"
            )
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(f"{input_url}\n", encoding="utf-8")

            canonical_url = "https://reddit.com/r/python/comments/abc123/example-thread"
            fetcher = FakeFetcher(
                {
                    canonical_url: build_fetch_result(
                        canonical_url=canonical_url,
                        post_id="t3_abc123",
                    )
                }
            )

            result = ingest_url_list(
                input_path,
                fetcher,
                output_path=output_path,
                collected_at=datetime(2026, 4, 6, 0, 0, tzinfo=timezone.utc),
            )

            payload = read_json_file(output_path)
            valid_records, issues = validate_raw_payload(payload)

            self.assertEqual(result.success_count, 1)
            self.assertEqual(result.failure_count, 0)
            self.assertEqual(len(valid_records), 1)
            self.assertEqual(issues, [])
            self.assertEqual(payload[0]["raw_id"], "reddit_url_ingest_20260406_001")
            self.assertEqual(payload[0]["candidate_id"], "t3_abc123")
            self.assertEqual(payload[0]["post_url"], input_url)
            self.assertEqual(payload[0]["devvit_reason_tags"], ["url_seeded_ingestion"])

    def test_partial_failure_continues(self) -> None:
        with make_test_root() as root:
            input_path = root / "data" / "url_lists" / "partial.txt"
            output_path = root / "data" / "raw" / "raw_from_urls_partial.json"
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(
                "\n".join(
                    [
                        "https://reddit.com/r/python/comments/abc123/example-thread/",
                        "https://reddit.com/r/python/comments/def456/second-thread/",
                    ]
                ),
                encoding="utf-8",
            )

            first_url = "https://reddit.com/r/python/comments/abc123/example-thread"
            second_url = "https://reddit.com/r/python/comments/def456/second-thread"
            fetcher = FakeFetcher(
                {
                    first_url: build_fetch_result(
                        canonical_url=first_url,
                        post_id="t3_abc123",
                    )
                },
                failures={second_url: "404 not found"},
            )

            result = ingest_url_list(input_path, fetcher, output_path=output_path)
            payload = read_json_file(output_path)

            self.assertEqual(result.success_count, 1)
            self.assertEqual(result.failure_count, 1)
            self.assertEqual(len(payload), 1)
            self.assertIn("404 not found", result.failures[0].reason)

    def test_invalid_url_still_allows_other_successes(self) -> None:
        with make_test_root() as root:
            input_path = root / "data" / "url_lists" / "invalid.txt"
            output_path = root / "data" / "raw" / "raw_from_urls_invalid.json"
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(
                "\n".join(
                    [
                        "https://example.com/not-reddit",
                        "https://reddit.com/comments/abc123/example-thread/",
                    ]
                ),
                encoding="utf-8",
            )

            canonical_url = "https://reddit.com/comments/abc123/example-thread"
            fetcher = FakeFetcher(
                {
                    canonical_url: build_fetch_result(
                        canonical_url=canonical_url,
                        post_id="t3_abc123",
                    )
                }
            )

            result = ingest_url_list(input_path, fetcher, output_path=output_path)

            self.assertEqual(result.success_count, 1)
            self.assertEqual(result.failure_count, 1)
            self.assertIn("Unsupported host", result.failures[0].reason)

    def test_cli_exit_code_is_zero_when_at_least_one_record_succeeds(self) -> None:
        ingest_script = load_script_module(
            PROJECT_ROOT / "python_pipeline" / "scripts" / "ingest_reddit_urls.py",
            "ingest_reddit_urls_test_module",
        )

        fake_result = SimpleNamespace(
            output_path=Path("python_pipeline/data/raw/raw_from_urls_test.json"),
            input_count=2,
            unique_count=2,
            success_count=1,
            failure_count=1,
            records=[{"raw_id": "reddit_url_ingest_20260406_001"}],
            successes=[],
            failures=[],
        )

        with mock.patch.object(ingest_script, "build_url_fetcher", return_value=object()):
            with mock.patch.object(ingest_script, "ingest_url_list", return_value=fake_result):
                with mock.patch.object(ingest_script, "parse_args") as parse_args_mock:
                    parse_args_mock.return_value = SimpleNamespace(
                        url_list_path=Path("python_pipeline/data/url_lists/test.txt"),
                        output_path=None,
                    )
                    exit_code = ingest_script.main()

        self.assertEqual(exit_code, 0)

    def test_fetcher_builder_resolves_supported_fetchers(self) -> None:
        self.assertEqual(list_url_fetchers(), ("reddit_public", "reddit_oauth"))
        self.assertEqual(type(build_url_fetcher("reddit_public")).__name__, "RedditPublicJsonFetcher")
        self.assertEqual(type(build_url_fetcher("reddit_oauth")).__name__, "RedditOAuthFetcher")

    def test_fetcher_builder_rejects_unknown_fetcher(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"Unknown URL fetcher: not_a_fetcher\. Available fetchers: reddit_public, reddit_oauth\.",
        ):
            build_url_fetcher("not_a_fetcher")

    def test_reddit_oauth_placeholder_raises_not_implemented(self) -> None:
        fetcher = build_url_fetcher("reddit_oauth")

        with self.assertRaisesRegex(
            NotImplementedError,
            r"RedditOAuthFetcher is a placeholder\. OAuth token / approval flow is not implemented yet\.",
        ):
            fetcher.fetch_thread("https://reddit.com/comments/abc123")

    def test_ingest_resolve_fetcher_name_prefers_cli_then_env_then_default(self) -> None:
        ingest_script = load_script_module(
            PROJECT_ROOT / "python_pipeline" / "scripts" / "ingest_reddit_urls.py",
            "ingest_reddit_urls_test_resolve_fetcher",
        )

        with mock.patch.dict("os.environ", {"TOPIC_SHELF_FETCHER": "reddit_oauth"}, clear=False):
            self.assertEqual(ingest_script.resolve_fetcher_name("reddit_public"), "reddit_public")
            self.assertEqual(ingest_script.resolve_fetcher_name(None), "reddit_oauth")

        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(ingest_script.resolve_fetcher_name(None), "reddit_public")

    def test_top_comments_missing_maps_to_empty_list(self) -> None:
        with make_test_root() as root:
            input_path = root / "data" / "url_lists" / "comments.txt"
            output_path = root / "data" / "raw" / "raw_from_urls_comments.json"
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(
                "https://reddit.com/comments/abc123\n",
                encoding="utf-8",
            )

            canonical_url = "https://reddit.com/comments/abc123"
            fetcher = FakeFetcher(
                {
                    canonical_url: build_fetch_result(
                        canonical_url=canonical_url,
                        post_id="t3_abc123",
                        top_comments=[],
                    )
                }
            )

            result = ingest_url_list(input_path, fetcher, output_path=output_path)
            record = result.records[0]

            self.assertEqual(record["top_comments"], [])

    def test_top_comments_are_limited_to_five(self) -> None:
        with make_test_root() as root:
            input_path = root / "data" / "url_lists" / "comment_limit.txt"
            output_path = root / "data" / "raw" / "raw_from_urls_comment_limit.json"
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(
                "https://reddit.com/comments/abc123/example\n",
                encoding="utf-8",
            )

            canonical_url = "https://reddit.com/comments/abc123/example"
            fetcher = FakeFetcher(
                {
                    canonical_url: build_fetch_result(
                        canonical_url=canonical_url,
                        post_id="t3_abc123",
                        top_comments=build_comment_list(6),
                    )
                }
            )

            result = ingest_url_list(input_path, fetcher, output_path=output_path)
            self.assertEqual(len(result.records[0]["top_comments"]), TOP_COMMENT_LIMIT)

    def test_reddit_public_fixture_keeps_short_comment_lists_short(self) -> None:
        with make_test_root() as root:
            input_path = root / "data" / "url_lists" / "fixture_short.txt"
            output_path = root / "data" / "raw" / "raw_from_urls_fixture_short.json"
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(
                "https://reddit.com/comments/edge001/edge_case_thread\n",
                encoding="utf-8",
            )

            fetcher = RedditPublicJsonFetcher()
            fixture_payload = load_json_fixture("reddit_public_edge_short.json")
            with mock.patch.object(fetcher, "_load_json", return_value=fixture_payload):
                result = ingest_url_list(input_path, fetcher, output_path=output_path)

            record = result.records[0]
            self.assertEqual(record["post_author"], "[deleted]")
            self.assertEqual(record["post_body"], "")
            self.assertEqual(record["body_excerpt"], "")
            self.assertEqual(len(record["top_comments"]), 2)
            self.assertEqual(record["top_comments"][0]["author"], "[deleted]")

    def test_reddit_public_fixture_caps_long_comment_lists(self) -> None:
        with make_test_root() as root:
            input_path = root / "data" / "url_lists" / "fixture_long.txt"
            output_path = root / "data" / "raw" / "raw_from_urls_fixture_long.json"
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(
                "https://reddit.com/comments/edge002/long_comment_thread\n",
                encoding="utf-8",
            )

            fetcher = RedditPublicJsonFetcher()
            fixture_payload = load_json_fixture("reddit_public_edge_long.json")
            with mock.patch.object(fetcher, "_load_json", return_value=fixture_payload):
                result = ingest_url_list(input_path, fetcher, output_path=output_path)

            record = result.records[0]
            self.assertEqual(len(record["top_comments"]), TOP_COMMENT_LIMIT)
            self.assertEqual(record["post_author"], "tester")
            self.assertEqual(record["post_body"], "Body text for the longer fixture.")

    def test_public_fetcher_top_comment_limit_matches_shared_cap(self) -> None:
        payload = [
            {
                "data": {
                    "children": [
                        {
                            "data": {
                                "name": "t3_abc123",
                                "id": "abc123",
                                "subreddit": "python",
                                "title": "Example thread",
                                "permalink": "/r/python/comments/abc123/example-thread",
                                "author": "spez",
                                "created_utc": 1710000000,
                                "selftext": "",
                                "num_comments": 10,
                                "ups": 5,
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
                                "id": f"comment_{index + 1}",
                                "name": f"t1_comment_{index + 1}",
                                "author": "commenter",
                                "body": "Comment body",
                                "score": index,
                                "created_utc": 1710000000 + index,
                            },
                        }
                        for index in range(TOP_COMMENT_LIMIT + 1)
                    ]
                }
            },
        ]

        self.assertEqual(len(extract_top_comments(payload)), TOP_COMMENT_LIMIT)

    def test_normalize_top_comments_uses_shared_cap(self) -> None:
        comments = build_comment_list(TOP_COMMENT_LIMIT + 2)

        self.assertEqual(len(normalize_top_comments(comments)), TOP_COMMENT_LIMIT)

    def test_shortlink_and_permalink_dedupe_to_one_record(self) -> None:
        with make_test_root() as root:
            input_path = root / "data" / "url_lists" / "dedupe.txt"
            output_path = root / "data" / "raw" / "raw_from_urls_dedupe.json"
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(
                "\n".join(
                    [
                        "https://reddit.com/r/python/comments/abc123/example-thread/",
                        "https://redd.it/abc123",
                    ]
                ),
                encoding="utf-8",
            )

            canonical_url = "https://reddit.com/r/python/comments/abc123/example-thread"
            fetcher = FakeFetcher(
                {
                    canonical_url: build_fetch_result(
                        canonical_url=canonical_url,
                        post_id="t3_abc123",
                    )
                }
            )

            result = ingest_url_list(input_path, fetcher, output_path=output_path)

            self.assertEqual(result.success_count, 1)
            self.assertEqual(result.failure_count, 0)
            self.assertEqual(len(result.records), 1)
            self.assertEqual(len(read_json_file(output_path)), 1)

    def test_post_body_missing_builds_empty_excerpt(self) -> None:
        with make_test_root() as root:
            input_path = root / "data" / "url_lists" / "body.txt"
            output_path = root / "data" / "raw" / "raw_from_urls_body.json"
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(
                "https://reddit.com/comments/abc123/example\n",
                encoding="utf-8",
            )

            canonical_url = "https://reddit.com/comments/abc123/example"
            fetcher = FakeFetcher(
                {
                    canonical_url: build_fetch_result(
                        canonical_url=canonical_url,
                        post_id="t3_abc123",
                        post_body="",
                    )
                }
            )

            result = ingest_url_list(input_path, fetcher, output_path=output_path)

            self.assertEqual(result.records[0]["post_body"], "")
            self.assertEqual(result.records[0]["body_excerpt"], "")
            self.assertEqual(build_body_excerpt(""), "")

    def test_canonicalize_and_dedupe(self) -> None:
        urls = [
            "https://www.reddit.com/r/python/comments/abc123/example-thread/?utm_source=test",
            "https://redd.it/abc123?utm_source=test",
            "https://redd.it/abc123?utm_source=test",
            "https://reddit.com/r/python/comments/def456/another-thread/",
        ]

        canonical_urls = canonicalize_and_dedupe_urls(urls)

        self.assertEqual(
            canonical_urls,
            [
                "https://reddit.com/r/python/comments/abc123/example-thread",
                "https://reddit.com/r/python/comments/def456/another-thread",
            ],
        )
        self.assertEqual(
            canonicalize_reddit_thread_url("https://m.reddit.com/comments/abc123/"),
            "https://reddit.com/comments/abc123",
        )

    def test_generated_raw_validator_pass_with_missing_optional_counts(self) -> None:
        with make_test_root() as root:
            input_path = root / "data" / "url_lists" / "validator.txt"
            output_path = root / "data" / "raw" / "raw_from_urls_validator.json"
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(
                "https://reddit.com/r/python/comments/xyz789/validator-thread/\n",
                encoding="utf-8",
            )

            canonical_url = "https://reddit.com/r/python/comments/xyz789/validator-thread"
            fetcher = FakeFetcher(
                {
                    canonical_url: build_fetch_result(
                        canonical_url=canonical_url,
                        post_id="t3_xyz789",
                        num_comments=0,
                        upvotes=0,
                        post_author="[deleted]",
                        top_comments=[],
                    )
                }
            )

            ingest_url_list(input_path, fetcher, output_path=output_path)
            payload = read_json_file(output_path)
            valid_records, issues = validate_raw_payload(payload)

            self.assertEqual(len(valid_records), 1)
            self.assertEqual(issues, [])


def build_fetch_result(
    canonical_url: str,
    post_id: str,
    post_body: str = "Post body text.\n\nMore details here.",
    top_comments: list[dict[str, object]] | None = None,
    num_comments: int = 12,
    upvotes: int = 34,
    post_author: str = "spez",
) -> UrlFetchResult:
    comments = top_comments
    if comments is None:
        comments = [
            {
                "comment_id": "t1_comment1",
                "author": "commenter",
                "body": "Helpful comment body",
                "score": 5,
                "created_utc": 1710000001,
            }
        ]

    return UrlFetchResult(
        canonical_url=canonical_url,
        subreddit="python",
        post_title="Example thread",
        post_url=canonical_url,
        post_author=post_author,
        post_created_utc=1710000000,
        post_body=post_body,
        num_comments=num_comments,
        upvotes=upvotes,
        top_comments=comments,
        post_id=post_id,
    )


def build_comment_list(count: int) -> list[dict[str, object]]:
    comments: list[dict[str, object]] = []
    for index in range(count):
        comments.append(
            {
                "comment_id": f"t1_comment_{index + 1}",
                "author": f"author_{index + 1}",
                "body": f"Comment body {index + 1}",
                "score": index,
                "created_utc": 1710000000 + index,
            }
        )
    return comments


def load_json_fixture(filename: str) -> object:
    fixture_path = FIXTURES_DIR / filename
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def load_script_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()
