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

from pipeline.io_utils import build_cards_output_path, build_normalized_output_path, read_json_file


class PipelineSmokeTests(unittest.TestCase):
    def test_run_pipeline_smoke_from_raw_to_cards(self) -> None:
        script_path = PIPELINE_ROOT / "scripts" / "run_pipeline.py"
        fixture_path = PROJECT_ROOT / "python_pipeline" / "tests" / "fixtures" / "sample_raw_minimal.json"

        tmp_root = PROJECT_ROOT / "python_pipeline" / "tests" / f".pipeline_smoke_{uuid4().hex}"
        try:
            tmp_root.mkdir(parents=True, exist_ok=False)
            raw_path = tmp_root / "raw" / "sample_raw_minimal.json"
            raw_path.parent.mkdir(parents=True, exist_ok=True)

            raw_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
            raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            normalized_path = build_normalized_output_path(raw_path)
            cards_path = build_cards_output_path(normalized_path)

            result = subprocess.run(
                [sys.executable, str(script_path), str(raw_path)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertTrue(normalized_path.exists())
            self.assertTrue(cards_path.exists())

            normalized_records = read_json_file(normalized_path)
            cards = read_json_file(cards_path)

            self.assertIsInstance(normalized_records, list)
            self.assertIsInstance(cards, list)
            self.assertGreaterEqual(len(normalized_records), 1)
            self.assertGreaterEqual(len(cards), 1)
            self.assertIn("title", cards[0])
            self.assertIn("source_url", cards[0])
            self.assertIn("card_id", cards[0])
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
