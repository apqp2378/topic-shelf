from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import unittest
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = PROJECT_ROOT / "python_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))


@contextmanager
def make_review_root() -> Path:
    temp_dir = PIPELINE_ROOT / "data" / "test_tmp" / "batch_review"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def load_script_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BatchReviewScaffoldTests(unittest.TestCase):
    def test_generate_review_scaffold_from_cards_file(self) -> None:
        script = load_script_module(
            PIPELINE_ROOT / "scripts" / "init_batch_review.py",
            "init_batch_review_test_module",
        )
        cards_path = PIPELINE_ROOT / "data" / "cards" / "cards_raw_from_urls_claude_code_tips.json"

        with make_review_root() as root:
            review_dir = root / "data" / "reviews"
            with mock.patch.object(script, "REVIEW_DIR", review_dir):
                with mock.patch.object(
                    script,
                    "parse_args",
                    return_value=SimpleNamespace(target=str(cards_path), overwrite=False),
                ):
                    buffer = StringIO()
                    with mock.patch("sys.stdout", buffer):
                        exit_code = script.main()

            self.assertEqual(exit_code, 0)
            review_path = review_dir / "claude_code_tips_review.md"
            decisions_path = review_dir / "claude_code_tips_decisions.json"
            self.assertTrue(review_path.exists())
            self.assertTrue(decisions_path.exists())

            payload = json.loads(decisions_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["batch_name"], "claude_code_tips")
            self.assertEqual(payload["source_cards_file"], cards_path.as_posix())
            self.assertIn("reviewed_at", payload)
            self.assertIsInstance(payload["decisions"], list)
            self.assertEqual(len(payload["decisions"]), 3)

            review_text = review_path.read_text(encoding="utf-8")
            self.assertIn("claude_code_tips", review_text)
            self.assertIn("I benchmarked \"Plan with Opus, Execute with Codex\"", review_text)
            self.assertIn("\"card_id\":", decisions_path.read_text(encoding="utf-8"))

    def test_generate_review_scaffold_from_batch_stem(self) -> None:
        script = load_script_module(
            PIPELINE_ROOT / "scripts" / "init_batch_review.py",
            "init_batch_review_test_module_stem",
        )

        with make_review_root() as root:
            review_dir = root / "data" / "reviews"
            with mock.patch.object(script, "REVIEW_DIR", review_dir):
                with mock.patch.object(
                    script,
                    "parse_args",
                    return_value=SimpleNamespace(target="claude_code_tips", overwrite=False),
                    ):
                    exit_code = script.main()

            self.assertEqual(exit_code, 0)
            self.assertTrue((review_dir / "claude_code_tips_review.md").exists())
            self.assertTrue((review_dir / "claude_code_tips_decisions.json").exists())

    def test_overwrite_protection_requires_flag(self) -> None:
        script = load_script_module(
            PIPELINE_ROOT / "scripts" / "init_batch_review.py",
            "init_batch_review_test_module_overwrite",
        )
        cards_path = PIPELINE_ROOT / "data" / "cards" / "cards_raw_from_urls_claude_code_tips.json"

        with make_review_root() as root:
            review_dir = root / "data" / "reviews"
            review_dir.mkdir(parents=True, exist_ok=True)
            review_path = review_dir / "claude_code_tips_review.md"
            decisions_path = review_dir / "claude_code_tips_decisions.json"
            review_path.write_text("keep me", encoding="utf-8")
            decisions_path.write_text("keep me too", encoding="utf-8")

            with mock.patch.object(script, "REVIEW_DIR", review_dir):
                with mock.patch.object(
                    script,
                    "parse_args",
                    return_value=SimpleNamespace(target=str(cards_path), overwrite=False),
                ):
                    buffer = StringIO()
                    with mock.patch("sys.stdout", buffer):
                        exit_code = script.main()

            self.assertEqual(exit_code, 1)
            self.assertEqual(review_path.read_text(encoding="utf-8"), "keep me")
            self.assertEqual(decisions_path.read_text(encoding="utf-8"), "keep me too")
            self.assertIn("already exists", buffer.getvalue())

    def test_canonical_example_path_appears_in_repo_guidance(self) -> None:
        guidance_files = [
            PROJECT_ROOT / "AGENTS.md",
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "python_pipeline" / "README.md",
            PROJECT_ROOT / "docs" / "reddit_oauth_runbook.md",
        ]

        for path in guidance_files:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn("python_pipeline/data/url_lists/claude_code_tips.txt", text)


if __name__ == "__main__":
    unittest.main()
