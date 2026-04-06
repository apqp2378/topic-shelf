from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = PROJECT_ROOT / "python_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))


def load_script_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PurgeOldRawTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = PIPELINE_ROOT / "data" / "test_tmp" / f"purge-{os.getpid()}-{id(self)}"
        self.raw_dir = self.temp_root / "data" / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.script = load_script_module(
            PIPELINE_ROOT / "scripts" / "purge_old_raw.py",
            f"purge_old_raw_test_{id(self)}",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_helper_matches_only_expected_generated_raw_files(self) -> None:
        self.assertTrue(self.script.is_generated_raw_filename("raw_from_urls_example.json"))
        self.assertFalse(self.script.is_generated_raw_filename("sample_raw_minimal.json"))
        self.assertFalse(self.script.is_generated_raw_filename("devvit_keep_2026-04-05.json"))

    def test_dry_run_reports_candidates_without_deleting(self) -> None:
        old_generated = self.raw_dir / "raw_from_urls_old.json"
        new_generated = self.raw_dir / "raw_from_urls_new.json"
        unrelated = self.raw_dir / "sample_raw_minimal.json"

        self._write_file(old_generated, age_days=7)
        self._write_file(new_generated, age_days=0)
        self._write_file(unrelated, age_days=30)

        with mock.patch.object(self.script, "RAW_DIR", self.raw_dir):
            with mock.patch.object(
                self.script,
                "parse_args",
                return_value=SimpleNamespace(
                    older_than_hours=None,
                    older_than_days=1,
                    apply=False,
                    dry_run=False,
                ),
            ):
                buffer = StringIO()
                with redirect_stdout(buffer):
                    exit_code = self.script.main()

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertTrue(old_generated.exists())
        self.assertTrue(new_generated.exists())
        self.assertTrue(unrelated.exists())
        self.assertIn("Mode: dry-run", output)
        self.assertIn("Files to delete: 1", output)
        self.assertIn("Files actually deleted: 0", output)

    def test_apply_deletes_only_matching_old_generated_raw(self) -> None:
        old_generated = self.raw_dir / "raw_from_urls_old.json"
        new_generated = self.raw_dir / "raw_from_urls_new.json"
        unrelated = self.raw_dir / "sample_raw_minimal.json"

        self._write_file(old_generated, age_days=7)
        self._write_file(new_generated, age_days=0)
        self._write_file(unrelated, age_days=30)

        with mock.patch.object(self.script, "RAW_DIR", self.raw_dir):
            with mock.patch.object(
                self.script,
                "parse_args",
                return_value=SimpleNamespace(
                    older_than_hours=12,
                    older_than_days=None,
                    apply=True,
                    dry_run=False,
                ),
            ):
                buffer = StringIO()
                with redirect_stdout(buffer):
                    exit_code = self.script.main()

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertFalse(old_generated.exists())
        self.assertTrue(new_generated.exists())
        self.assertTrue(unrelated.exists())
        self.assertIn("Mode: apply", output)
        self.assertIn("Files actually deleted: 1", output)

    def _write_file(self, path: Path, age_days: int) -> None:
        path.write_text("{}", encoding="utf-8")
        mtime = datetime.now(timezone.utc) - timedelta(days=age_days)
        timestamp = mtime.timestamp()
        os.utime(path, (timestamp, timestamp))


if __name__ == "__main__":
    unittest.main()
