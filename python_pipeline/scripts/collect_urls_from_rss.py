from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.auto_url_collection import (
    DEFAULT_CANDIDATE_DIR,
    DEFAULT_CONFIG_PATH,
    collect_batch_candidates,
    load_enabled_batches,
    write_candidate_payload,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect RSS-backed URL candidates into batch-centric JSON files."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the auto-source config file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_CANDIDATE_DIR,
        help="Directory for raw RSS candidate JSON files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    batches = load_enabled_batches(args.config)

    if not batches:
        print("No enabled auto-source batches were found.")
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    total_candidates = 0

    for batch in batches:
        payload = collect_batch_candidates(batch, collected_at=now)
        output_path = args.output_dir / f"rss_candidates_{batch.batch_name}.json"
        write_candidate_payload(output_path, payload)
        total_candidates += int(payload.get("candidate_count", 0))

        print(f"Batch name: {batch.batch_name}")
        print(f"Batch mode: {batch.batch_mode}")
        print(f"Candidate JSON: {output_path}")
        print(f"Source count: {len(batch.sources)}")
        print(f"Candidate count: {payload['candidate_count']}")
        if payload.get("source_errors"):
            print("Source errors:")
            for error in payload["source_errors"]:
                print(f"- {error['source_name']}: {error['error']}")

    print(f"Enabled batch count: {len(batches)}")
    print(f"Total candidate count: {total_candidates}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
