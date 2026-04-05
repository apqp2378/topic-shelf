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

from pipeline.bundlers import build_bundle_provider
from pipeline.io_utils import (
    build_bundles_output_path,
    build_cards_output_path,
    build_cards_with_summary_output_path,
    build_cards_with_topics_output_path,
    build_cards_with_translation_output_path,
    build_normalized_output_path,
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def read_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


class BundleStageTests(unittest.TestCase):
    def test_rule_based_provider_handles_zero_one_and_many_cards(self) -> None:
        provider = build_bundle_provider("rule_based")

        self.assertEqual(provider.build_bundles([]), [])

        one_card_bundles = provider.build_bundles(
            [
                {
                    "card_id": "card-1",
                    "title": "Single card",
                    "summary": "Summary text",
                    "primary_topic": "coding",
                }
            ]
        )
        self.assertEqual(len(one_card_bundles), 1)
        self.assertEqual(one_card_bundles[0]["bundle_type"], "weekly_bundle")
        self.assertEqual(one_card_bundles[0]["card_count"], 1)
        self.assertIn(one_card_bundles[0]["representative_card_id"], one_card_bundles[0]["card_ids"])

        many_card_bundles = provider.build_bundles(
            [
                {
                    "card_id": "card-1",
                    "title": "Claude vs ChatGPT for coding",
                    "summary": "A comparison post",
                    "primary_topic": "model_comparison",
                    "topic_confidence": 0.9,
                },
                {
                    "card_id": "card-2",
                    "title": "Another model comparison",
                    "summary": "",
                    "primary_topic": "model_comparison",
                    "topic_confidence": 0.4,
                },
                {
                    "card_id": "card-3",
                    "title": "Prompting tips",
                    "summary": "",
                    "primary_topic": "prompt_engineering",
                    "topic_confidence": 0.7,
                },
            ]
        )
        bundle_types = [bundle["bundle_type"] for bundle in many_card_bundles]
        self.assertIn("weekly_bundle", bundle_types)
        self.assertIn("topic_bundle", bundle_types)
        for bundle in many_card_bundles:
            self.assertIn(bundle["representative_card_id"], bundle["card_ids"])

        mixed_bundles = provider.build_bundles(
            [
                {
                    "card_id": "card-a",
                    "title": "Pricing question",
                    "primary_topic": "pricing",
                },
                {
                    "card_id": "card-b",
                    "title": "Workflow question",
                    "primary_topic": "workflow",
                },
            ]
        )
        mixed_types = [bundle["bundle_type"] for bundle in mixed_bundles]
        self.assertIn("weekly_bundle", mixed_types)
        self.assertIn("mixed_bundle", mixed_types)

    def test_run_pipeline_bundle_across_stage_combinations(self) -> None:
        sample_payload = [
            {
                "raw_id": "reddit_devvit_bundle_001",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "Claude vs ChatGPT for coding",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/bundle_001/",
                "post_author": "tester",
                "post_created_utc": 1775323792,
                "post_body": "I want to compare AI tools for coding and daily work.",
                "num_comments": 2,
                "upvotes": 1,
                "top_comments": [
                    {
                        "comment_id": "t1_bundle_001",
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
                "raw_id": "reddit_devvit_bundle_002",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "ChatGPT vs Claude for coding prompts",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/bundle_002/",
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
                "raw_id": "reddit_devvit_bundle_003",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "A random daily note",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/bundle_003/",
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
        tmp_root = PIPELINE_ROOT / "tests" / f".bundle_stage_{uuid4().hex}"

        try:
            tmp_root.mkdir(parents=True, exist_ok=False)
            raw_path = tmp_root / "raw" / "sample_keep.json"
            write_json(raw_path, sample_payload)

            cards_path = build_cards_output_path(build_normalized_output_path(raw_path))
            summary_path = build_cards_with_summary_output_path(cards_path)
            translation_path = build_cards_with_translation_output_path(cards_path)
            topics_path = build_cards_with_topics_output_path(cards_path)
            bundles_path = build_bundles_output_path(cards_path)

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
            self.assertFalse(bundles_path.exists())

            cards_before_bundle = read_json(cards_path)

            bundle_only_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-bundles",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                bundle_only_result.returncode,
                0,
                msg=f"stdout:\n{bundle_only_result.stdout}\nstderr:\n{bundle_only_result.stderr}",
            )
            self.assertTrue(bundles_path.exists())
            self.assertEqual(cards_before_bundle, read_json(cards_path))

            bundle_cards = read_json(bundles_path)
            bundle_types = [bundle["bundle_type"] for bundle in bundle_cards]
            self.assertIn("weekly_bundle", bundle_types)

            summary_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-summary",
                    "--enable-bundles",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                summary_result.returncode,
                0,
                msg=f"stdout:\n{summary_result.stdout}\nstderr:\n{summary_result.stderr}",
            )
            self.assertTrue(summary_path.exists())
            self.assertEqual(cards_before_bundle, read_json(cards_path))

            translation_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-translation",
                    "--enable-bundles",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                translation_result.returncode,
                0,
                msg=f"stdout:\n{translation_result.stdout}\nstderr:\n{translation_result.stderr}",
            )
            self.assertTrue(translation_path.exists())
            self.assertEqual(cards_before_bundle, read_json(cards_path))

            topic_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-topic-classification",
                    "--enable-bundles",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                topic_result.returncode,
                0,
                msg=f"stdout:\n{topic_result.stdout}\nstderr:\n{topic_result.stderr}",
            )
            self.assertTrue(topics_path.exists())
            self.assertTrue(bundles_path.exists())

            topic_bundle_cards = read_json(bundles_path)
            topic_bundle_types = [bundle["bundle_type"] for bundle in topic_bundle_cards]
            self.assertIn("weekly_bundle", topic_bundle_types)
            self.assertIn("topic_bundle", topic_bundle_types)
            for bundle in topic_bundle_cards:
                self.assertIn(bundle["representative_card_id"], bundle["card_ids"])

            all_stage_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-summary",
                    "--enable-translation",
                    "--enable-topic-classification",
                    "--enable-bundles",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                all_stage_result.returncode,
                0,
                msg=f"stdout:\n{all_stage_result.stdout}\nstderr:\n{all_stage_result.stderr}",
            )
            self.assertTrue(summary_path.exists())
            self.assertTrue(translation_path.exists())
            self.assertTrue(topics_path.exists())
            self.assertTrue(bundles_path.exists())
            self.assertEqual(cards_before_bundle, read_json(cards_path))
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
