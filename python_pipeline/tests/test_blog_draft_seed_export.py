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
def make_draft_root() -> Path:
    temp_dir = PIPELINE_ROOT / "data" / "test_tmp" / "blog_draft_seeds"
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


def load_publish_candidates_fixture() -> dict[str, object]:
    path = PIPELINE_ROOT / "data" / "publish_candidates" / "publish_candidates_claude_code_tips.json"
    return json.loads(path.read_text(encoding="utf-8"))


class BlogDraftSeedExportTests(unittest.TestCase):
    def test_export_from_batch_stem(self) -> None:
        script = load_script_module(
            PIPELINE_ROOT / "scripts" / "export_blog_draft_seeds.py",
            "export_blog_draft_seeds_test_module_stem",
        )
        export_payload = load_publish_candidates_fixture()

        with make_draft_root() as root:
            publish_dir = root / "data" / "publish_candidates"
            draft_dir = root / "data" / "blog_draft_seeds"
            publish_dir.mkdir(parents=True, exist_ok=True)
            export_path = publish_dir / "publish_candidates_claude_code_tips.json"
            export_path.write_text(json.dumps(export_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            with mock.patch.object(script, "PUBLISH_CANDIDATES_DIR", publish_dir):
                with mock.patch.object(script, "BLOG_DRAFT_SEEDS_DIR", draft_dir):
                    with mock.patch.object(
                        script,
                        "parse_args",
                        return_value=SimpleNamespace(target="claude_code_tips", overwrite=False),
                    ):
                        buffer = StringIO()
                        with mock.patch("sys.stdout", buffer):
                            exit_code = script.main()

            self.assertEqual(exit_code, 0)
            files = sorted(draft_dir.glob("*.md"))
            self.assertEqual(len(files), 2)
            self.assertTrue(any("plan_with_opus_execute_with_codex" in path.name for path in files))
            self.assertTrue(any("built_an_ai_job_search_system" in path.name for path in files))

            first_text = files[0].read_text(encoding="utf-8")
            self.assertIn("## Working Headline", first_text)
            self.assertIn("## Evidence / Supporting Points", first_text)
            self.assertIn("## Caution / Framing Notes", first_text)
            self.assertIn("## Possible Outline", first_text)

    def test_export_from_publish_candidates_json_path(self) -> None:
        script = load_script_module(
            PIPELINE_ROOT / "scripts" / "export_blog_draft_seeds.py",
            "export_blog_draft_seeds_test_module_path",
        )
        export_payload = load_publish_candidates_fixture()

        with make_draft_root() as root:
            publish_dir = root / "data" / "publish_candidates"
            draft_dir = root / "data" / "blog_draft_seeds"
            publish_dir.mkdir(parents=True, exist_ok=True)
            export_path = publish_dir / "publish_candidates_claude_code_tips.json"
            export_path.write_text(json.dumps(export_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            with mock.patch.object(script, "PUBLISH_CANDIDATES_DIR", publish_dir):
                with mock.patch.object(script, "BLOG_DRAFT_SEEDS_DIR", draft_dir):
                    with mock.patch.object(
                        script,
                        "parse_args",
                        return_value=SimpleNamespace(target=str(export_path), overwrite=False),
                    ):
                        exit_code = script.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(list(draft_dir.glob("*.md"))), 2)

    def test_framing_note_carries_through_to_markdown(self) -> None:
        script = load_script_module(
            PIPELINE_ROOT / "scripts" / "export_blog_draft_seeds.py",
            "export_blog_draft_seeds_test_module_framing",
        )
        export_payload = load_publish_candidates_fixture()

        with make_draft_root() as root:
            publish_dir = root / "data" / "publish_candidates"
            draft_dir = root / "data" / "blog_draft_seeds"
            publish_dir.mkdir(parents=True, exist_ok=True)
            export_path = publish_dir / "publish_candidates_claude_code_tips.json"
            export_path.write_text(json.dumps(export_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            with mock.patch.object(script, "PUBLISH_CANDIDATES_DIR", publish_dir):
                with mock.patch.object(script, "BLOG_DRAFT_SEEDS_DIR", draft_dir):
                    with mock.patch.object(
                        script,
                        "parse_args",
                        return_value=SimpleNamespace(target="claude_code_tips", overwrite=False),
                    ):
                        exit_code = script.main()

            self.assertEqual(exit_code, 0)
            slug = script.slugify_title(
                str(export_payload["publish_candidates"][1]["title"]),
                str(export_payload["publish_candidates"][1]["card_id"]),
            )
            draft_path = draft_dir / f"claude_code_tips__002__{slug}.md"
            draft_text = draft_path.read_text(encoding="utf-8")
            self.assertIn("Review note suggests framing or headline work", draft_text)
            self.assertIn("740+ offers", draft_text)

    def test_zero_publish_candidates_warns_but_succeeds(self) -> None:
        script = load_script_module(
            PIPELINE_ROOT / "scripts" / "export_blog_draft_seeds.py",
            "export_blog_draft_seeds_test_module_zero",
        )
        export_payload = load_publish_candidates_fixture()
        export_payload["publish_candidates"] = []
        export_payload["publish_candidate_count"] = 0

        with make_draft_root() as root:
            publish_dir = root / "data" / "publish_candidates"
            draft_dir = root / "data" / "blog_draft_seeds"
            publish_dir.mkdir(parents=True, exist_ok=True)
            export_path = publish_dir / "publish_candidates_claude_code_tips.json"
            export_path.write_text(json.dumps(export_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            with mock.patch.object(script, "PUBLISH_CANDIDATES_DIR", publish_dir):
                with mock.patch.object(script, "BLOG_DRAFT_SEEDS_DIR", draft_dir):
                    with mock.patch.object(
                        script,
                        "parse_args",
                        return_value=SimpleNamespace(target="claude_code_tips", overwrite=False),
                    ):
                        buffer = StringIO()
                        with mock.patch("sys.stdout", buffer):
                            exit_code = script.main()

            self.assertEqual(exit_code, 0)
            self.assertIn("Warning: no publish candidates were found", buffer.getvalue())
            self.assertEqual(list(draft_dir.glob("*.md")), [])

    def test_malformed_publish_candidates_json_fails_clearly(self) -> None:
        script = load_script_module(
            PIPELINE_ROOT / "scripts" / "export_blog_draft_seeds.py",
            "export_blog_draft_seeds_test_module_bad_json",
        )

        with make_draft_root() as root:
            publish_dir = root / "data" / "publish_candidates"
            draft_dir = root / "data" / "blog_draft_seeds"
            publish_dir.mkdir(parents=True, exist_ok=True)
            export_path = publish_dir / "publish_candidates_claude_code_tips.json"
            export_path.write_text("[]", encoding="utf-8")

            with mock.patch.object(script, "PUBLISH_CANDIDATES_DIR", publish_dir):
                with mock.patch.object(script, "BLOG_DRAFT_SEEDS_DIR", draft_dir):
                    with mock.patch.object(
                        script,
                        "parse_args",
                        return_value=SimpleNamespace(target=str(export_path), overwrite=False),
                    ):
                        buffer = StringIO()
                        with mock.patch("sys.stdout", buffer):
                            exit_code = script.main()

            self.assertEqual(exit_code, 1)
            self.assertIn("Publish-candidates export must contain a JSON object", buffer.getvalue())

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
