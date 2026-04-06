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
def make_export_root() -> Path:
    temp_dir = PIPELINE_ROOT / "data" / "test_tmp" / "publish_candidates"
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


def load_cards_fixture(cards_path: Path) -> list[dict[str, object]]:
    return json.loads(cards_path.read_text(encoding="utf-8"))


def build_decisions_payload(cards: list[dict[str, object]], batch_name: str) -> dict[str, object]:
    return {
        "batch_name": batch_name,
        "source_cards_file": str(PIPELINE_ROOT / "data" / "cards" / "cards_raw_from_urls_claude_code_tips.json"),
        "reviewed_at": "2026-04-06T00:00:00Z",
        "decisions": [
            {
                "card_id": str(cards[0]["card_id"]),
                "title": str(cards[0]["title"]),
                "decision": "publish_candidate",
                "publish_candidate": True,
                "review_note": "Strong benchmark details.",
            },
            {
                "card_id": str(cards[1]["card_id"]),
                "title": str(cards[1]["title"]),
                "decision": "hold",
                "publish_candidate": False,
                "review_note": "Needs more review.",
            },
            {
                "card_id": str(cards[2]["card_id"]),
                "title": str(cards[2]["title"]),
                "decision": "publish_candidate",
                "publish_candidate": True,
                "review_note": "Good practical walkthrough.",
            },
        ],
    }


class PublishCandidateExportTests(unittest.TestCase):
    def test_export_from_decisions_file_path(self) -> None:
        script = load_script_module(
            PIPELINE_ROOT / "scripts" / "export_publish_candidates.py",
            "export_publish_candidates_test_module",
        )
        cards_path = PIPELINE_ROOT / "data" / "cards" / "cards_raw_from_urls_claude_code_tips.json"
        cards = load_cards_fixture(cards_path)

        with make_export_root() as root:
            review_dir = root / "data" / "reviews"
            export_dir = root / "data" / "publish_candidates"
            review_dir.mkdir(parents=True, exist_ok=True)
            decisions_path = review_dir / "claude_code_tips_decisions.json"
            decisions_path.write_text(
                json.dumps(build_decisions_payload(cards, "claude_code_tips"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with mock.patch.object(script, "REVIEW_DIR", review_dir):
                with mock.patch.object(script, "EXPORT_DIR", export_dir):
                    with mock.patch.object(
                        script,
                        "parse_args",
                        return_value=SimpleNamespace(target=str(decisions_path), overwrite=False),
                    ):
                        buffer = StringIO()
                        with mock.patch("sys.stdout", buffer):
                            exit_code = script.main()

            self.assertEqual(exit_code, 0)
            markdown_path = export_dir / "publish_candidates_claude_code_tips.md"
            json_path = export_dir / "publish_candidates_claude_code_tips.json"
            self.assertTrue(markdown_path.exists())
            self.assertTrue(json_path.exists())

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["batch_name"], "claude_code_tips")
            self.assertEqual(payload["publish_candidate_count"], 2)
            self.assertEqual(len(payload["publish_candidates"]), 2)
            self.assertEqual(payload["publish_candidates"][0]["card_id"], cards[0]["card_id"])
            self.assertEqual(
                payload["publish_candidates"][0]["review_note"],
                "Strong benchmark details.",
            )

            markdown_text = markdown_path.read_text(encoding="utf-8")
            self.assertIn("Publish Candidates: claude_code_tips", markdown_text)
            self.assertIn(str(cards[0]["card_id"]), markdown_text)
            self.assertIn("Strong benchmark details.", markdown_text)
            self.assertIn(str(cards[2]["title"]), markdown_text)

    def test_export_from_batch_stem(self) -> None:
        script = load_script_module(
            PIPELINE_ROOT / "scripts" / "export_publish_candidates.py",
            "export_publish_candidates_test_module_stem",
        )
        cards_path = PIPELINE_ROOT / "data" / "cards" / "cards_raw_from_urls_claude_code_tips.json"
        cards = load_cards_fixture(cards_path)

        with make_export_root() as root:
            review_dir = root / "data" / "reviews"
            export_dir = root / "data" / "publish_candidates"
            review_dir.mkdir(parents=True, exist_ok=True)
            decisions_path = review_dir / "claude_code_tips_decisions.json"
            decisions_path.write_text(
                json.dumps(build_decisions_payload(cards, "claude_code_tips"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with mock.patch.object(script, "REVIEW_DIR", review_dir):
                with mock.patch.object(script, "EXPORT_DIR", export_dir):
                    with mock.patch.object(
                        script,
                        "parse_args",
                        return_value=SimpleNamespace(target="claude_code_tips", overwrite=False),
                    ):
                        exit_code = script.main()

            self.assertEqual(exit_code, 0)
            self.assertTrue((export_dir / "publish_candidates_claude_code_tips.md").exists())
            self.assertTrue((export_dir / "publish_candidates_claude_code_tips.json").exists())

    def test_zero_publish_candidates_warns_but_succeeds(self) -> None:
        script = load_script_module(
            PIPELINE_ROOT / "scripts" / "export_publish_candidates.py",
            "export_publish_candidates_test_module_zero",
        )
        cards_path = PIPELINE_ROOT / "data" / "cards" / "cards_raw_from_urls_claude_code_tips.json"
        cards = load_cards_fixture(cards_path)

        with make_export_root() as root:
            review_dir = root / "data" / "reviews"
            export_dir = root / "data" / "publish_candidates"
            review_dir.mkdir(parents=True, exist_ok=True)
            decisions_path = review_dir / "claude_code_tips_decisions.json"
            payload = build_decisions_payload(cards, "claude_code_tips")
            for decision in payload["decisions"]:
                decision["decision"] = "hold"
                decision["publish_candidate"] = False
            decisions_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with mock.patch.object(script, "REVIEW_DIR", review_dir):
                with mock.patch.object(script, "EXPORT_DIR", export_dir):
                    with mock.patch.object(
                        script,
                        "parse_args",
                        return_value=SimpleNamespace(target=str(decisions_path), overwrite=False),
                    ):
                        buffer = StringIO()
                        with mock.patch("sys.stdout", buffer):
                            exit_code = script.main()

            self.assertEqual(exit_code, 0)
            self.assertIn("Warning: no publish candidates were found", buffer.getvalue())
            payload = json.loads((export_dir / "publish_candidates_claude_code_tips.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["publish_candidate_count"], 0)

    def test_malformed_decisions_json_fails_clearly(self) -> None:
        script = load_script_module(
            PIPELINE_ROOT / "scripts" / "export_publish_candidates.py",
            "export_publish_candidates_test_module_bad_json",
        )

        with make_export_root() as root:
            review_dir = root / "data" / "reviews"
            review_dir.mkdir(parents=True, exist_ok=True)
            bad_path = review_dir / "claude_code_tips_decisions.json"
            bad_path.write_text("[]", encoding="utf-8")

            with mock.patch.object(script, "REVIEW_DIR", review_dir):
                with mock.patch.object(
                    script,
                    "parse_args",
                    return_value=SimpleNamespace(target=str(bad_path), overwrite=False),
                ):
                    buffer = StringIO()
                    with mock.patch("sys.stdout", buffer):
                        exit_code = script.main()

            self.assertEqual(exit_code, 1)
            self.assertIn("Decisions file must contain a JSON object", buffer.getvalue())

    def test_canonical_example_guidance_still_uses_claude_code_tips(self) -> None:
        guidance_files = [
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "python_pipeline" / "README.md",
        ]

        for path in guidance_files:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn("python_pipeline/data/url_lists/claude_code_tips.txt", text)


if __name__ == "__main__":
    unittest.main()
