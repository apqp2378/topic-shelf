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

from pipeline.classifiers import build_classification_provider
from pipeline.io_utils import (
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


class TopicClassificationStageTests(unittest.TestCase):
    def test_rule_based_provider_classifies_and_falls_back(self) -> None:
        provider = build_classification_provider("rule_based")

        matched = provider.classify_card(
            {
                "title": "Claude vs ChatGPT for coding",
                "summary": "",
                "excerpt": "",
                "top_comment_snippets": [],
            }
        )
        fallback = provider.classify_card(
            {
                "title": "A random daily note",
                "summary": "",
                "excerpt": "",
                "top_comment_snippets": [],
            }
        )

        self.assertEqual(matched["primary_topic"], "model_comparison")
        self.assertIn("coding", matched["topic_labels"])
        self.assertGreater(matched["topic_confidence"], 0.0)
        self.assertEqual(fallback["primary_topic"], "general_discussion")

    def test_run_pipeline_topic_classification_across_stage_combinations(self) -> None:
        sample_payload = [
            {
                "raw_id": "reddit_devvit_topic_001",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "Claude vs ChatGPT for coding",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/topic_001/",
                "post_author": "tester",
                "post_created_utc": 1775323792,
                "post_body": "I want to compare AI tools for coding and daily work.",
                "num_comments": 2,
                "upvotes": 1,
                "top_comments": [
                    {
                        "comment_id": "t1_topic_001",
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
                "raw_id": "reddit_devvit_topic_002",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "How much does Claude cost?",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/topic_002/",
                "post_author": "tester",
                "post_created_utc": 1775324792,
                "post_body": "I am trying to understand pricing and plans.",
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
                "raw_id": "reddit_devvit_topic_003",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "A random daily note",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/topic_003/",
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
        tmp_root = PIPELINE_ROOT / "tests" / f".topic_stage_{uuid4().hex}"

        try:
            tmp_root.mkdir(parents=True, exist_ok=False)
            raw_path = tmp_root / "raw" / "sample_keep.json"
            write_json(raw_path, sample_payload)

            cards_path = build_cards_output_path(build_normalized_output_path(raw_path))
            summary_path = build_cards_with_summary_output_path(cards_path)
            translation_path = build_cards_with_translation_output_path(cards_path)
            topics_path = build_cards_with_topics_output_path(cards_path)

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
            self.assertFalse(topics_path.exists())

            cards_before_topic = read_json(cards_path)

            topic_only_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-topic-classification",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                topic_only_result.returncode,
                0,
                msg=f"stdout:\n{topic_only_result.stdout}\nstderr:\n{topic_only_result.stderr}",
            )
            self.assertTrue(topics_path.exists())

            topic_cards = read_json(topics_path)
            self.assertEqual(cards_before_topic, read_json(cards_path))
            self.assertEqual(topic_cards[0]["primary_topic"], "model_comparison")
            self.assertIn("coding", topic_cards[0]["topic_labels"])
            self.assertEqual(topic_cards[2]["primary_topic"], "general_discussion")
            self.assertNotIn("summary", topic_cards[0])
            self.assertNotIn("title_ko", topic_cards[0])

            summary_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-summary",
                    "--enable-topic-classification",
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
            topic_cards = read_json(topics_path)
            self.assertIn("summary", topic_cards[0])

            translation_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-translation",
                    "--enable-topic-classification",
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
            topic_cards = read_json(topics_path)
            self.assertIn("title_ko", topic_cards[0])

            summary_translation_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-summary",
                    "--enable-translation",
                    "--enable-topic-classification",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                summary_translation_result.returncode,
                0,
                msg=f"stdout:\n{summary_translation_result.stdout}\nstderr:\n{summary_translation_result.stderr}",
            )
            self.assertTrue(summary_path.exists())
            self.assertTrue(translation_path.exists())
            self.assertTrue(topics_path.exists())

            summary_cards = read_json(summary_path)
            translation_cards = read_json(translation_path)
            topic_cards = read_json(topics_path)

            self.assertEqual(topic_cards[0]["summary"], summary_cards[0]["summary"])
            self.assertEqual(topic_cards[0]["title_ko"], translation_cards[0]["title_ko"])
            self.assertEqual(topic_cards[2]["primary_topic"], "general_discussion")
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
