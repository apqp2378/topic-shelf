from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from unittest import mock
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = PROJECT_ROOT / "python_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.io_utils import (
    build_cards_output_path,
    build_cards_with_summary_output_path,
    build_normalized_output_path,
)
from pipeline.summary_providers.openai import OpenAISummaryProvider
from pipeline.summarizers import (
    build_heuristic_summary,
    build_summary_provider,
    enrich_cards_with_summary,
    enrich_cards_with_summary_with_stats,
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def read_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


class SummaryStageTests(unittest.TestCase):
    def test_build_heuristic_summary_returns_empty_for_missing_text(self) -> None:
        card = {
            "title": " ",
            "excerpt": None,
            "top_comments": [],
            "top_comment_snippets": [],
        }

        self.assertEqual(build_heuristic_summary(card, max_len=120), "")

    def test_enrich_cards_with_summary_handles_missing_excerpt_and_comments(self) -> None:
        cards = [
            {
                "card_id": "card-1",
                "title": "Daily workflow question",
                "top_comment_snippets": [],
                "review_note": "",
            },
            {
                "card_id": "card-2",
                "title": "Claude vs ChatGPT for daily work",
                "excerpt": (
                    "I use AI tools for work, writing, and coding. What do people actually use "
                    "each one for?"
                ),
                "top_comment_snippets": [
                    "For daily work, I use Claude more for long writing and document summaries."
                ],
                "review_note": None,
            },
        ]

        enriched_cards = enrich_cards_with_summary(cards, max_len=90)

        self.assertEqual(len(enriched_cards), 2)
        self.assertEqual(enriched_cards[0]["summary"], "Daily workflow question")
        self.assertTrue(enriched_cards[1]["summary"].startswith("Claude vs ChatGPT for daily work"))
        self.assertLessEqual(len(enriched_cards[1]["summary"]), 90)

    def test_openai_provider_selection_uses_provider_branch(self) -> None:
        cards = [
            {
                "card_id": "card-1",
                "title": "Claude vs ChatGPT for coding",
                "excerpt": "A short excerpt.",
                "top_comment_snippets": ["Useful comment."],
            }
        ]

        with mock.patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "test-key", "SUMMARY_OPENAI_MODEL": "test-model"},
            clear=False,
        ):
            provider = build_summary_provider("openai")
            self.assertEqual(provider.provider_name, "openai")
            with mock.patch.object(
                OpenAISummaryProvider,
                "request_summary",
                return_value="OpenAI summary result",
            ):
                enriched_cards, stats = enrich_cards_with_summary_with_stats(
                    cards,
                    max_len=90,
                    provider_name="openai",
                )

        self.assertEqual(enriched_cards[0]["summary"], "OpenAI summary result")
        self.assertEqual(stats.provider_failure_count, 0)
        self.assertEqual(stats.fallback_count, 0)
        self.assertEqual(stats.success_count, 1)

    def test_openai_provider_missing_key_falls_back_safely(self) -> None:
        cards = [
            {
                "card_id": "card-1",
                "title": "Claude vs ChatGPT for coding",
                "excerpt": "A short excerpt.",
                "top_comment_snippets": ["Useful comment."],
            }
        ]

        with mock.patch.dict("os.environ", {}, clear=True):
            enriched_cards, stats = enrich_cards_with_summary_with_stats(
                cards,
                max_len=90,
                provider_name="openai",
            )

        self.assertEqual(len(enriched_cards), 1)
        self.assertNotEqual(enriched_cards[0]["summary"], "")
        self.assertGreaterEqual(stats.provider_failure_count, 1)
        self.assertGreaterEqual(stats.fallback_count, 1)

    def test_openai_provider_exception_falls_back_for_partial_failures(self) -> None:
        cards = [
            {
                "card_id": "card-1",
                "title": "Claude vs ChatGPT for coding",
                "excerpt": "A short excerpt.",
                "top_comment_snippets": ["Useful comment."],
            },
            {
                "card_id": "card-2",
                "title": "Second card",
                "excerpt": "",
                "top_comment_snippets": [],
            },
        ]

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
            provider = build_summary_provider("openai")
            self.assertEqual(provider.provider_name, "openai")
            with mock.patch.object(
                OpenAISummaryProvider,
                "request_summary",
                side_effect=[RuntimeError("temporary failure"), "OpenAI summary result"],
            ):
                enriched_cards, stats = enrich_cards_with_summary_with_stats(
                    cards,
                    max_len=90,
                    provider_name="openai",
                )

        self.assertEqual(len(enriched_cards), 2)
        self.assertNotEqual(enriched_cards[0]["summary"], "")
        self.assertNotEqual(enriched_cards[1]["summary"], "")
        self.assertGreaterEqual(stats.provider_failure_count, 1)
        self.assertGreaterEqual(stats.fallback_count, 1)

    def test_empty_input_is_safe(self) -> None:
        enriched_cards, stats = enrich_cards_with_summary_with_stats([], provider_name="openai")
        self.assertEqual(enriched_cards, [])
        self.assertEqual(stats.input_count, 0)
        self.assertEqual(stats.success_count, 0)

    def test_run_pipeline_without_summary_and_with_summary(self) -> None:
        sample_payload = [
            {
                "raw_id": "reddit_devvit_test_001",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "Claude vs ChatGPT for daily work",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/test_001/",
                "post_author": "tester",
                "post_created_utc": 1775323792,
                "post_body": "I use AI tools for work, writing, and coding.",
                "num_comments": 3,
                "upvotes": 1,
                "top_comments": [
                    {
                        "comment_id": "t1_test_001",
                        "author": "tester",
                        "body": (
                            "For daily work, I use Claude more for long writing and "
                            "document summaries."
                        ),
                        "score": 1,
                        "created_utc": 1775323966,
                    }
                ],
                "devvit_score": 12,
                "devvit_reason_tags": [
                    "title_comparison_pattern",
                    "body_has_min_context",
                ],
                "moderator_status": "keep",
                "review_note": "",
                "collected_at": "2026-04-05T10:00:00Z",
            },
            {
                "raw_id": "reddit_devvit_test_002",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "Short title only",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/test_002/",
                "post_author": "tester",
                "post_created_utc": 1775324792,
                "post_body": "Body text for the second keep record.",
                "num_comments": 0,
                "upvotes": 0,
                "top_comments": [],
                "devvit_score": 5,
                "devvit_reason_tags": [],
                "moderator_status": "keep",
                "review_note": "",
                "collected_at": "2026-04-05T11:00:00Z",
            },
        ]

        script_path = PIPELINE_ROOT / "scripts" / "run_pipeline.py"

        tmp_root = PROJECT_ROOT / "python_pipeline" / "tests" / f".summary_stage_{uuid4().hex}"
        try:
            tmp_root.mkdir(parents=True, exist_ok=False)
            raw_path = tmp_root / "raw" / "sample_keep.json"
            write_json(raw_path, sample_payload)

            cards_path = build_cards_output_path(build_normalized_output_path(raw_path))
            summary_path = build_cards_with_summary_output_path(cards_path)

            disabled_result = subprocess.run(
                [sys.executable, str(script_path), str(raw_path)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                disabled_result.returncode,
                0,
                msg=f"stdout:\n{disabled_result.stdout}\nstderr:\n{disabled_result.stderr}",
            )
            self.assertTrue(cards_path.exists())
            self.assertFalse(summary_path.exists())

            cards_without_summary = read_json(cards_path)

            enabled_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-summary",
                    "--summary-max-len",
                    "120",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                enabled_result.returncode,
                0,
                msg=f"stdout:\n{enabled_result.stdout}\nstderr:\n{enabled_result.stderr}",
            )
            self.assertTrue(cards_path.exists())
            self.assertTrue(summary_path.exists())

            cards_with_summary = read_json(cards_path)
            summary_cards = read_json(summary_path)

            self.assertEqual(cards_without_summary, cards_with_summary)
            self.assertEqual(len(summary_cards), 2)
            self.assertEqual(summary_cards[0]["title"], "Claude vs ChatGPT for daily work")
            self.assertIn("summary", summary_cards[0])
            self.assertIn("summary", summary_cards[1])
            self.assertNotEqual(summary_cards[0]["summary"], "")
            self.assertEqual(summary_cards[1]["summary"], "Short title only")
            self.assertIsInstance(summary_cards, list)
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
