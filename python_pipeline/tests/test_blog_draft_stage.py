from __future__ import annotations

import os
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = PROJECT_ROOT / "python_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.io_utils import (
    build_blog_drafts_output_path,
    build_bundles_output_path,
    build_cards_output_path,
    build_cards_with_summary_output_path,
    build_cards_with_topics_output_path,
    build_cards_with_translation_output_path,
    build_normalized_output_path,
)
from pipeline.blog_draft_providers.openai import OpenAIBlogDraftProvider
from pipeline.blog_drafters import build_blog_draft_provider, generate_blog_drafts_with_stats

from unittest.mock import patch


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def read_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


class BlogDraftStageTests(unittest.TestCase):
    def test_default_provider_keeps_rule_based_behavior(self) -> None:
        provider = build_blog_draft_provider("rule_based")
        drafts, stats = generate_blog_drafts_with_stats(
            [],
            [
                {
                    "card_id": "card-1",
                    "title": "Claude vs ChatGPT for coding",
                    "summary": "A quick comparison of AI tools for coding.",
                    "excerpt": "",
                }
            ],
            provider,
        )

        self.assertEqual(provider.provider_name, "rule_based")
        self.assertEqual(len(drafts), 1)
        self.assertEqual(stats.provider_failure_count, 0)
        self.assertEqual(drafts[0]["draft_status"], "draft")

    def test_openai_provider_selection_and_fallback_branch(self) -> None:
        provider = OpenAIBlogDraftProvider(api_key="test-key")
        self.assertEqual(provider.provider_name, "openai")
        self.assertTrue(provider.is_available())

        bundle = {
            "bundle_id": "bundle-1",
            "bundle_type": "weekly_bundle",
            "title": "Weekly bundle",
            "description": "A compact weekly draft.",
            "primary_topic": "coding",
            "related_topics": ["coding"],
            "card_ids": ["card-1"],
            "representative_card_id": "card-1",
            "representative_title": "Claude vs ChatGPT for coding",
            "representative_summary": "A quick comparison of AI tools for coding.",
        }
        cards = [
            {
                "card_id": "card-1",
                "title": "Claude vs ChatGPT for coding",
                "summary": "A quick comparison of AI tools for coding.",
                "excerpt": "",
            }
        ]

        fake_response = {
            "title": "AI tools for coding",
            "subtitle": "A compact comparison draft",
            "intro": "This draft compares the main tools and the most useful angle.",
            "key_points": ["Compare the tools", "Keep the framing practical"],
            "recommended_cards": ["card-1"],
            "body_sections": [
                {"heading": "Overview", "summary": "Start from the comparison angle."},
                {"heading": "Practical takeaway", "summary": "Close with a useful recommendation."},
            ],
            "closing": "Keep the ending short and practical.",
        }

        with patch.object(provider, "request_completion", return_value=json.dumps(fake_response)):
            drafts = provider.build_drafts([bundle], cards)

        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["title"], "AI tools for coding")
        self.assertEqual(drafts[0]["recommended_cards"], ["card-1"])
        self.assertEqual(provider.get_failure_count(), 0)

    def test_missing_api_key_uses_fallback(self) -> None:
        provider = OpenAIBlogDraftProvider(api_key="")
        drafts = provider.build_drafts(
            [
                {
                    "bundle_id": "bundle-1",
                    "bundle_type": "weekly_bundle",
                    "title": "Weekly bundle",
                    "description": "A compact weekly draft.",
                    "primary_topic": "coding",
                    "related_topics": ["coding"],
                    "card_ids": ["card-1"],
                    "representative_card_id": "card-1",
                    "representative_title": "Claude vs ChatGPT for coding",
                    "representative_summary": "A quick comparison of AI tools for coding.",
                }
            ],
            [
                {
                    "card_id": "card-1",
                    "title": "Claude vs ChatGPT for coding",
                    "summary": "A quick comparison of AI tools for coding.",
                    "excerpt": "",
                }
            ],
        )

        self.assertFalse(provider.is_available())
        self.assertEqual(len(drafts), 1)
        self.assertGreater(provider.get_failure_count(), 0)
        self.assertEqual(drafts[0]["draft_status"], "draft")

    def test_provider_exception_falls_back_per_bundle(self) -> None:
        provider = OpenAIBlogDraftProvider(api_key="test-key")
        bundles = [
            {
                "bundle_id": "bundle-1",
                "bundle_type": "weekly_bundle",
                "title": "Weekly bundle",
                "description": "A compact weekly draft.",
                "primary_topic": "coding",
                "related_topics": ["coding"],
                "card_ids": ["card-1"],
                "representative_card_id": "card-1",
                "representative_title": "Claude vs ChatGPT for coding",
                "representative_summary": "A quick comparison of AI tools for coding.",
            },
            {
                "bundle_id": "bundle-2",
                "bundle_type": "topic_bundle",
                "title": "Topic bundle",
                "description": "Another compact draft.",
                "primary_topic": "productivity",
                "related_topics": ["productivity"],
                "card_ids": ["card-2"],
                "representative_card_id": "card-2",
                "representative_title": "Prompt workflow notes",
                "representative_summary": "A quick productivity note.",
            },
        ]
        cards = [
            {
                "card_id": "card-1",
                "title": "Claude vs ChatGPT for coding",
                "summary": "A quick comparison of AI tools for coding.",
                "excerpt": "",
            },
            {
                "card_id": "card-2",
                "title": "Prompt workflow notes",
                "summary": "A quick productivity note.",
                "excerpt": "",
            },
        ]

        responses = [
            RuntimeError("temporary provider failure"),
            json.dumps(
                {
                    "title": "A practical productivity draft",
                    "subtitle": "Short outline",
                    "intro": "Keep the draft focused and concrete.",
                    "key_points": ["Point one", "Point two"],
                    "recommended_cards": ["card-2"],
                    "body_sections": [
                        {"heading": "Overview", "summary": "Open with the core angle."},
                        {"heading": "Close", "summary": "End with a practical takeaway."},
                    ],
                    "closing": "Wrap up with a short takeaway.",
                }
            ),
        ]

        def fake_request_completion(prompt: str) -> str:
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        with patch.object(provider, "request_completion", side_effect=fake_request_completion):
            drafts = provider.build_drafts(bundles, cards)

        self.assertEqual(len(drafts), 2)
        self.assertGreaterEqual(provider.get_failure_count(), 1)
        self.assertTrue("fallback" in drafts[0]["draft_reason"].lower())
        self.assertEqual(drafts[1]["title"], "A practical productivity draft")

    def test_empty_bundle_input_creates_fallback_draft(self) -> None:
        provider = build_blog_draft_provider("rule_based")
        drafts, stats = generate_blog_drafts_with_stats(
            [],
            [
                {
                    "card_id": "card-1",
                    "title": "Claude vs ChatGPT for coding",
                    "summary": "A quick comparison of AI tools for coding.",
                    "excerpt": "",
                }
            ],
            provider,
        )

        self.assertEqual(len(drafts), 1)
        self.assertEqual(stats.fallback_draft_count, 1)
        self.assertIn("card-1", drafts[0]["recommended_cards"])

    def test_run_pipeline_openai_blog_provider_flag_regression(self) -> None:
        sample_payload = [
            {
                "raw_id": "reddit_devvit_blog_001",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "Claude vs ChatGPT for coding",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/blog_001/",
                "post_author": "tester",
                "post_created_utc": 1775323792,
                "post_body": "I want to compare AI tools for coding and daily work.",
                "num_comments": 2,
                "upvotes": 1,
                "top_comments": [
                    {
                        "comment_id": "t1_blog_001",
                        "author": "tester",
                        "body": "Coding is where I notice the biggest difference.",
                        "score": 1,
                        "created_utc": 1775323966,
                    }
                ],
                "devvit_score": 12,
                "devvit_reason_tags": ["title_comparison_pattern", "body_has_min_context"],
                "moderator_status": "keep",
                "review_note": "",
                "collected_at": "2026-04-05T10:00:00Z",
            }
        ]

        script_path = PIPELINE_ROOT / "scripts" / "run_pipeline.py"
        tmp_root = PIPELINE_ROOT / "tests" / f".blog_openai_{uuid4().hex}"

        try:
            tmp_root.mkdir(parents=True, exist_ok=False)
            raw_path = tmp_root / "raw" / "sample_keep.json"
            write_json(raw_path, sample_payload)

            env = os.environ.copy()
            env.pop("OPENAI_API_KEY", None)
            env.pop("BLOG_DRAFT_OPENAI_MODEL", None)

            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-blog-drafts",
                    "--blog-draft-provider",
                    "openai",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            blog_path = build_blog_drafts_output_path(
                build_cards_output_path(build_normalized_output_path(raw_path))
            )
            self.assertTrue(blog_path.exists())
            blog_drafts = read_json(blog_path)
            self.assertEqual(len(blog_drafts), 1)
            self.assertIn("draft_status", blog_drafts[0])
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)

    def test_run_pipeline_blog_drafts_with_and_without_bundles(self) -> None:
        sample_payload = [
            {
                "raw_id": "reddit_devvit_blog_001",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "Claude vs ChatGPT for coding",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/blog_001/",
                "post_author": "tester",
                "post_created_utc": 1775323792,
                "post_body": "I want to compare AI tools for coding and daily work.",
                "num_comments": 2,
                "upvotes": 1,
                "top_comments": [
                    {
                        "comment_id": "t1_blog_001",
                        "author": "tester",
                        "body": "Coding is where I notice the biggest difference.",
                        "score": 1,
                        "created_utc": 1775323966,
                    }
                ],
                "devvit_score": 12,
                "devvit_reason_tags": ["title_comparison_pattern", "body_has_min_context"],
                "moderator_status": "keep",
                "review_note": "",
                "collected_at": "2026-04-05T10:00:00Z",
            },
            {
                "raw_id": "reddit_devvit_blog_002",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "ChatGPT vs Claude for coding prompts",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/blog_002/",
                "post_author": "tester",
                "post_created_utc": 1775324792,
                "post_body": "I am comparing the two tools for coding prompts.",
                "num_comments": 0,
                "upvotes": 0,
                "top_comments": [],
                "devvit_score": 5,
                "devvit_reason_tags": [],
                "moderator_status": "keep",
                "review_note": "",
                "collected_at": "2026-04-05T11:00:00Z",
            },
            {
                "raw_id": "reddit_devvit_blog_003",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "A random daily note",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/blog_003/",
                "post_author": "tester",
                "post_created_utc": 1775325792,
                "post_body": "Nothing special here.",
                "num_comments": 0,
                "upvotes": 0,
                "top_comments": [],
                "devvit_score": 1,
                "devvit_reason_tags": [],
                "moderator_status": "keep",
                "review_note": "",
                "collected_at": "2026-04-05T12:00:00Z",
            },
        ]

        script_path = PIPELINE_ROOT / "scripts" / "run_pipeline.py"
        tmp_root = PIPELINE_ROOT / "tests" / f".blog_stage_{uuid4().hex}"

        try:
            tmp_root.mkdir(parents=True, exist_ok=False)
            raw_path = tmp_root / "raw" / "sample_keep.json"
            write_json(raw_path, sample_payload)

            cards_path = build_cards_output_path(build_normalized_output_path(raw_path))
            summary_path = build_cards_with_summary_output_path(cards_path)
            translation_path = build_cards_with_translation_output_path(cards_path)
            topics_path = build_cards_with_topics_output_path(cards_path)
            bundles_path = build_bundles_output_path(cards_path)
            blog_path = build_blog_drafts_output_path(cards_path)

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
            self.assertFalse(blog_path.exists())

            cards_before_blog = read_json(cards_path)

            fallback_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-blog-drafts",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                fallback_result.returncode,
                0,
                msg=f"stdout:\n{fallback_result.stdout}\nstderr:\n{fallback_result.stderr}",
            )
            self.assertTrue(blog_path.exists())
            self.assertEqual(cards_before_blog, read_json(cards_path))

            fallback_drafts = read_json(blog_path)
            self.assertEqual(len(fallback_drafts), 1)
            self.assertEqual(fallback_drafts[0]["source_bundle_id"], "fallback_bundle_1")
            for card_id in fallback_drafts[0]["recommended_cards"]:
                self.assertIn(card_id, [card["card_id"] for card in cards_before_blog])

            bundles_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-summary",
                    "--enable-translation",
                    "--enable-topic-classification",
                    "--enable-bundles",
                    "--enable-blog-drafts",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                bundles_result.returncode,
                0,
                msg=f"stdout:\n{bundles_result.stdout}\nstderr:\n{bundles_result.stderr}",
            )
            self.assertTrue(summary_path.exists())
            self.assertTrue(translation_path.exists())
            self.assertTrue(topics_path.exists())
            self.assertTrue(bundles_path.exists())
            self.assertTrue(blog_path.exists())
            self.assertEqual(cards_before_blog, read_json(cards_path))

            bundle_cards = read_json(bundles_path)
            blog_drafts = read_json(blog_path)
            self.assertEqual(len(blog_drafts), len(bundle_cards))

            bundle_ids = [bundle["bundle_id"] for bundle in bundle_cards]
            card_ids = {
                card["card_id"]
                for card in read_json(cards_path)
                if isinstance(card, dict) and "card_id" in card
            }
            for draft in blog_drafts:
                self.assertIn(draft["source_bundle_id"], bundle_ids)
                for card_id in draft["recommended_cards"]:
                    self.assertIn(card_id, card_ids)
                self.assertEqual(draft["draft_status"], "draft")

            bundle_cards_after = read_json(bundles_path)
            self.assertEqual(bundle_cards, bundle_cards_after)
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
