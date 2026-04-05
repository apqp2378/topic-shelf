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
    build_normalized_output_path,
    build_quality_reviews_output_path,
    build_publish_export_output_path,
)
from pipeline.publish_exporters.rule_based import RuleBasedPublishExportProvider


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def read_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


class PublishExportStageTests(unittest.TestCase):
    def test_rule_based_provider_handles_empty_and_missing_fields(self) -> None:
        provider = RuleBasedPublishExportProvider()

        empty_markdown = provider.build_markdown("cards", [], [], quality_reviews=[])
        self.assertIn("# Publish Cards", empty_markdown)
        self.assertGreater(provider.get_fallback_section_count(), 0)

        missing_markdown = provider.build_markdown(
            "blog_drafts",
            [
                {
                    "source_bundle_id": "",
                    "title": "",
                    "subtitle": "",
                    "intro": "",
                    "key_points": [],
                    "recommended_cards": [],
                    "body_sections": [],
                    "closing": "",
                }
            ],
            [],
            quality_reviews=[],
        )
        self.assertIn("# Publish Blog Drafts", missing_markdown)
        self.assertIn("Draft 1", missing_markdown)

    def test_run_pipeline_publish_export_sources(self) -> None:
        sample_payload = [
            {
                "raw_id": "reddit_devvit_publish_001",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "Claude vs ChatGPT for coding",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/publish_001/",
                "post_author": "tester",
                "post_created_utc": 1775323792,
                "post_body": "I want to compare AI tools for coding and daily work.",
                "num_comments": 2,
                "upvotes": 1,
                "top_comments": [
                    {
                        "comment_id": "t1_publish_001",
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
                "raw_id": "reddit_devvit_publish_002",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "ChatGPT vs Claude for prompts",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/publish_002/",
                "post_author": "tester",
                "post_created_utc": 1775324792,
                "post_body": "I am comparing the two tools for prompts.",
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
        tmp_root = PIPELINE_ROOT / "tests" / f".publish_stage_{uuid4().hex}"

        try:
            tmp_root.mkdir(parents=True, exist_ok=False)
            raw_path = tmp_root / "raw" / "sample_keep.json"
            write_json(raw_path, sample_payload)

            cards_path = build_cards_output_path(build_normalized_output_path(raw_path))
            summary_path = cards_path.parent / f"cards_with_summary_{cards_path.name[len('cards_') :]}"
            translation_path = cards_path.parent / f"cards_with_translation_{cards_path.name[len('cards_') :]}"
            topics_path = cards_path.parent / f"cards_with_topics_{cards_path.name[len('cards_') :]}"
            bundles_path = build_bundles_output_path(cards_path)
            blog_path = build_blog_drafts_output_path(cards_path)

            cards_only_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-publish-export",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                cards_only_result.returncode,
                0,
                msg=f"stdout:\n{cards_only_result.stdout}\nstderr:\n{cards_only_result.stderr}",
            )
            publish_cards_path = build_publish_export_output_path(cards_path, "cards")
            self.assertTrue(publish_cards_path.exists())
            self.assertIn("# Publish Cards", read_json_or_text(publish_cards_path))

            bundles_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-bundles",
                    "--enable-publish-export",
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
            publish_bundles_path = build_publish_export_output_path(bundles_path, "bundles")
            self.assertTrue(publish_bundles_path.exists())
            self.assertIn("# Publish Bundles", read_json_or_text(publish_bundles_path))

            blog_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-summary",
                    "--enable-translation",
                    "--enable-topic-classification",
                    "--enable-bundles",
                    "--enable-blog-drafts",
                    "--enable-publish-export",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                blog_result.returncode,
                0,
                msg=f"stdout:\n{blog_result.stdout}\nstderr:\n{blog_result.stderr}",
            )
            publish_blog_path = build_publish_export_output_path(blog_path, "blog_drafts")
            self.assertTrue(publish_blog_path.exists())
            markdown = read_json_or_text(publish_blog_path)
            self.assertIn("# Publish Blog Drafts", markdown)
            self.assertIn("Key Points", markdown)
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)

    def test_run_pipeline_publish_export_does_not_change_json_outputs(self) -> None:
        sample_payload = [
            {
                "raw_id": "reddit_devvit_publish_003",
                "source": "reddit_devvit",
                "subreddit": "topic_shelf_dev",
                "post_title": "Prompt workflow notes",
                "post_url": "https://reddit.com/r/topic_shelf_dev/comments/publish_003/",
                "post_author": "tester",
                "post_created_utc": 1775325792,
                "post_body": "Some useful workflow notes.",
                "num_comments": 1,
                "upvotes": 0,
                "top_comments": [],
                "devvit_score": 4,
                "devvit_reason_tags": [],
                "moderator_status": "keep",
                "review_note": "",
                "collected_at": "2026-04-05T12:00:00Z",
            }
        ]

        script_path = PIPELINE_ROOT / "scripts" / "run_pipeline.py"
        tmp_root = PIPELINE_ROOT / "tests" / f".publish_regression_{uuid4().hex}"

        try:
            tmp_root.mkdir(parents=True, exist_ok=False)
            raw_path = tmp_root / "raw" / "sample_keep.json"
            write_json(raw_path, sample_payload)

            baseline_result = subprocess.run(
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
                baseline_result.returncode,
                0,
                msg=f"stdout:\n{baseline_result.stdout}\nstderr:\n{baseline_result.stderr}",
            )

            cards_path = build_cards_output_path(build_normalized_output_path(raw_path))
            bundles_path = build_bundles_output_path(cards_path)
            blog_path = build_blog_drafts_output_path(cards_path)
            summary_path = cards_path.parent / f"cards_with_summary_{cards_path.name[len('cards_') :]}"
            translation_path = cards_path.parent / f"cards_with_translation_{cards_path.name[len('cards_') :]}"
            topics_path = cards_path.parent / f"cards_with_topics_{cards_path.name[len('cards_') :]}"
            quality_path = build_quality_reviews_output_path(topics_path)

            baseline_cards = read_json(cards_path)
            baseline_bundles = read_json(bundles_path)
            baseline_blog = read_json(blog_path)
            baseline_summary = read_json(summary_path)
            baseline_translation = read_json(translation_path)
            baseline_topics = read_json(topics_path)
            baseline_quality = read_json(quality_path)

            publish_result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-summary",
                    "--enable-translation",
                    "--enable-topic-classification",
                    "--enable-bundles",
                    "--enable-blog-drafts",
                    "--enable-quality-review",
                    "--enable-publish-export",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                publish_result.returncode,
                0,
                msg=f"stdout:\n{publish_result.stdout}\nstderr:\n{publish_result.stderr}",
            )

            self.assertEqual(baseline_cards, read_json(cards_path))
            self.assertEqual(baseline_bundles, read_json(bundles_path))
            self.assertEqual(baseline_blog, read_json(blog_path))
            self.assertEqual(baseline_summary, read_json(summary_path))
            self.assertEqual(baseline_translation, read_json(translation_path))
            self.assertEqual(baseline_topics, read_json(topics_path))
            self.assertEqual(
                strip_generated_at(baseline_quality),
                strip_generated_at(read_json(quality_path)),
            )

            publish_blog_path = build_publish_export_output_path(blog_path, "blog_drafts")
            self.assertTrue(publish_blog_path.exists())
            self.assertIn("# Publish Blog Drafts", read_json_or_text(publish_blog_path))
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)


def read_json_or_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as file:
        return file.read()


def strip_generated_at(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload

    cleaned = dict(payload)
    cleaned.pop("generated_at", None)
    return cleaned


if __name__ == "__main__":
    unittest.main()
