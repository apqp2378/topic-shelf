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
    build_cards_output_path,
    build_cards_with_summary_output_path,
    build_cards_with_translation_output_path,
    build_normalized_output_path,
)
from pipeline.translators import (
    build_translation_provider,
    enrich_cards_with_translation,
    translate_card_fields,
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def read_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


class TranslationStageTests(unittest.TestCase):
    def test_passthrough_provider_returns_cleaned_text(self) -> None:
        provider = build_translation_provider("passthrough")

        self.assertEqual(provider.translate_text(" hello "), "hello")
        self.assertEqual(provider.translate_text("   "), "")

    def test_translate_card_fields_adds_ko_fields_without_overwriting_source(self) -> None:
        provider = build_translation_provider("passthrough")
        card = {
            "card_id": "card-1",
            "title": "  Claude vs ChatGPT  ",
            "excerpt": "  Useful excerpt here.  ",
            "summary": "  Short summary here.  ",
        }

        translated_card = translate_card_fields(card, provider, target_lang="ko", card_index=1)

        self.assertEqual(translated_card["title"], "  Claude vs ChatGPT  ")
        self.assertEqual(translated_card["title_ko"], "Claude vs ChatGPT")
        self.assertEqual(translated_card["excerpt_ko"], "Useful excerpt here.")
        self.assertEqual(translated_card["summary_ko"], "Short summary here.")
        self.assertNotIn("title_ko", card)

    def test_enrich_cards_with_translation_handles_missing_summary(self) -> None:
        provider = build_translation_provider("passthrough")
        cards = [
            {
                "card_id": "card-1",
                "title": "First card",
                "excerpt": "",
            },
            {
                "card_id": "card-2",
                "title": "Second card",
                "summary": None,
            },
        ]

        translated_cards = enrich_cards_with_translation(cards, provider)

        self.assertEqual(len(translated_cards), 2)
        self.assertEqual(translated_cards[0]["summary_ko"], "")
        self.assertEqual(translated_cards[1]["summary_ko"], "")
        self.assertEqual(translated_cards[0]["title_ko"], "First card")

    def test_run_pipeline_translation_with_and_without_summary(self) -> None:
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
        tmp_root = PIPELINE_ROOT / "tests" / f".translation_stage_{uuid4().hex}"

        try:
            tmp_root.mkdir(parents=True, exist_ok=False)
            raw_path = tmp_root / "raw" / "sample_keep.json"
            write_json(raw_path, sample_payload)

            cards_path = build_cards_output_path(build_normalized_output_path(raw_path))
            summary_path = build_cards_with_summary_output_path(cards_path)
            translation_path = build_cards_with_translation_output_path(cards_path)

            without_summary = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-translation",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                without_summary.returncode,
                0,
                msg=f"stdout:\n{without_summary.stdout}\nstderr:\n{without_summary.stderr}",
            )
            self.assertTrue(cards_path.exists())
            self.assertTrue(translation_path.exists())
            self.assertFalse(summary_path.exists())

            cards_without_summary = read_json(cards_path)
            translation_without_summary = read_json(translation_path)

            self.assertEqual(cards_without_summary, read_json(cards_path))
            self.assertEqual(
                translation_without_summary[0]["title_ko"],
                "Claude vs ChatGPT for daily work",
            )
            self.assertEqual(translation_without_summary[0]["excerpt_ko"], "")
            self.assertEqual(translation_without_summary[0]["summary_ko"], "")
            cards_after_translation = read_json(cards_path)
            self.assertEqual(cards_without_summary, cards_after_translation)

            with_summary = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--enable-summary",
                    "--enable-translation",
                    str(raw_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                with_summary.returncode,
                0,
                msg=f"stdout:\n{with_summary.stdout}\nstderr:\n{with_summary.stderr}",
            )
            self.assertTrue(summary_path.exists())
            self.assertTrue(translation_path.exists())

            summary_cards = read_json(summary_path)
            translation_with_summary = read_json(translation_path)
            cards_after_summary = read_json(cards_path)

            self.assertEqual(cards_without_summary, cards_after_summary)
            self.assertEqual(
                translation_with_summary[0]["summary_ko"],
                summary_cards[0]["summary"],
            )
            self.assertEqual(
                translation_with_summary[1]["summary_ko"],
                summary_cards[1]["summary"],
            )
            self.assertEqual(translation_with_summary[0]["title_ko"], summary_cards[0]["title"])
            self.assertEqual(translation_with_summary[0]["excerpt_ko"], "")
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
