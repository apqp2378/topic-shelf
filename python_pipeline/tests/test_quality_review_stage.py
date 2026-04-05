from __future__ import annotations

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
    build_quality_reviews_output_path,
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def read_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


class QualityReviewStageTests(unittest.TestCase):
    def test_run_pipeline_quality_review_with_and_without_prior_stages(self) -> None:
        sample_payload = [
            {
                "raw_id": "reddit_devvit_quality_001",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "Claude vs ChatGPT for coding",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/quality_001/",
                "post_author": "tester",
                "post_created_utc": 1775323792,
                "post_body": "I want to compare AI tools for coding and daily work.",
                "num_comments": 2,
                "upvotes": 1,
                "top_comments": [
                    {
                        "comment_id": "t1_quality_001",
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
                "raw_id": "reddit_devvit_quality_002",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "ChatGPT vs Claude for coding prompts",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/quality_002/",
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
                "raw_id": "reddit_devvit_quality_003",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "A random daily note",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/quality_003/",
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
        tmp_root = PIPELINE_ROOT / "tests" / f".quality_stage_{uuid4().hex}"

        try:
            tmp_root.mkdir(parents=True, exist_ok=False)
            raw_path = tmp_root / "raw" / "sample_keep.json"
            write_json(raw_path, sample_payload)

            cards_path = build_cards_output_path(build_normalized_output_path(raw_path))
            summary_path = build_cards_with_summary_output_path(cards_path)
            translation_path = build_cards_with_translation_output_path(cards_path)
            topics_path = build_cards_with_topics_output_path(cards_path)
            bundles_path = build_bundles_output_path(cards_path)
            blog_drafts_path = build_blog_drafts_output_path(cards_path)
            quality_reviews_path = build_quality_reviews_output_path(cards_path)

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
            self.assertFalse(quality_reviews_path.exists())

            quality_only_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-quality-review",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                quality_only_result.returncode,
                0,
                msg=f"stdout:\n{quality_only_result.stdout}\nstderr:\n{quality_only_result.stderr}",
            )
            self.assertTrue(quality_reviews_path.exists())
            quality_only_reviews = read_json(quality_reviews_path)
            self.assertIn("source_file", quality_only_reviews)
            self.assertIn("generated_at", quality_only_reviews)
            self.assertIn("review_provider", quality_only_reviews)
            self.assertIn("review_version", quality_only_reviews)
            self.assertIn("input_summary", quality_only_reviews)
            self.assertIn("overall_status", quality_only_reviews)
            self.assertIn("overall_score", quality_only_reviews)
            self.assertIn("summary_stats", quality_only_reviews)
            self.assertIn("card_reviews", quality_only_reviews)
            self.assertIn("bundle_reviews", quality_only_reviews)
            self.assertIn("blog_draft_reviews", quality_only_reviews)
            self.assertGreaterEqual(len(quality_only_reviews["card_reviews"]), 3)
            self.assertEqual(quality_only_reviews["bundle_reviews"], [])
            self.assertEqual(quality_only_reviews["blog_draft_reviews"], [])
            for review in quality_only_reviews["card_reviews"]:
                self.assertEqual(review["review_level"], "card")
                self.assertGreaterEqual(review["score"], 0.0)
                self.assertLessEqual(review["score"], 1.0)
                self.assertIn(review["status"], ["pass", "warning", "fail"])
                self.assertIn("warnings", review)
                self.assertIn("checks", review)
                self.assertIn("review_notes", review)
                self.assertIn("recommended_actions", review)
                self.assertIsInstance(review["review_notes"], list)
                self.assertIsInstance(review["checks"], dict)

            full_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-summary",
                    "--enable-translation",
                    "--enable-topic-classification",
                    "--enable-bundles",
                    "--enable-blog-drafts",
                    "--enable-quality-review",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                full_result.returncode,
                0,
                msg=f"stdout:\n{full_result.stdout}\nstderr:\n{full_result.stderr}",
            )
            self.assertTrue(summary_path.exists())
            self.assertTrue(translation_path.exists())
            self.assertTrue(topics_path.exists())
            self.assertTrue(bundles_path.exists())
            self.assertTrue(blog_drafts_path.exists())
            self.assertTrue(quality_reviews_path.exists())

            cards_without_quality = read_json(cards_path)
            bundles_without_quality = read_json(bundles_path)
            blog_drafts_without_quality = read_json(blog_drafts_path)

            full_quality_reviews = read_json(quality_reviews_path)
            review_levels = {
                "card": full_quality_reviews["card_reviews"],
                "bundle": full_quality_reviews["bundle_reviews"],
                "blog_draft": full_quality_reviews["blog_draft_reviews"],
            }
            self.assertTrue(review_levels["card"])
            self.assertTrue(review_levels["bundle"])
            self.assertTrue(review_levels["blog_draft"])
            self.assertGreaterEqual(
                len(review_levels["card"]) + len(review_levels["bundle"]) + len(review_levels["blog_draft"]),
                7,
            )

            for review_group in review_levels.values():
                for review in review_group:
                    self.assertGreaterEqual(review["score"], 0.0)
                    self.assertLessEqual(review["score"], 1.0)
                    self.assertIn(review["status"], ["pass", "warning", "fail"])
                    self.assertIn("warnings", review)
                    self.assertIn("checks", review)
                    self.assertIn("review_notes", review)
                    self.assertIn("recommended_actions", review)
                    self.assertIsInstance(review["review_notes"], list)
                    self.assertIsInstance(review["checks"], dict)
                    if review["review_level"] == "blog_draft":
                        for card_id in review.get("recommended_cards", []):
                            self.assertTrue(card_id)

            self.assertEqual(cards_without_quality, read_json(cards_path))
            self.assertEqual(bundles_without_quality, read_json(bundles_path))
            self.assertEqual(blog_drafts_without_quality, read_json(blog_drafts_path))
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
