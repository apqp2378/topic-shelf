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
    DEFAULT_STATE_PATH,
    DEFAULT_URL_LIST_DIR,
    candidate_path_for_batch,
    load_enabled_batches,
    load_seen_urls,
    merge_batch_candidates,
    read_candidate_payload,
    save_seen_urls,
    write_url_list_from_candidates,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge RSS candidate JSON files into batch-centric URL lists."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the auto-source config file.",
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=DEFAULT_CANDIDATE_DIR,
        help="Directory containing raw RSS candidate JSON files.",
    )
    parser.add_argument(
        "--url-lists-dir",
        type=Path,
        default=DEFAULT_URL_LIST_DIR,
        help="Directory for the final auto URL lists.",
    )
    parser.add_argument(
        "--state-path",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="Path to the seen-URLs state JSON file.",
    )
    parser.add_argument(
        "--batch-name",
        type=str,
        help="Optional single batch name to merge.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    batches = load_enabled_batches(args.config)
    if args.batch_name:
        batches = [batch for batch in batches if batch.batch_name == args.batch_name]

    if not batches:
        print("No enabled auto-source batches matched the merge request.")
        return 1

    seen_urls = load_seen_urls(args.state_path)
    args.url_lists_dir.mkdir(parents=True, exist_ok=True)

    emitted_urls: set[str] = set()
    written_count = 0

    for batch in batches:
        candidate_path = candidate_path_for_batch(batch.batch_name, args.candidate_dir)
        if not candidate_path.exists():
            print(f"Missing candidate JSON for batch {batch.batch_name}: {candidate_path}")
            continue

        payload = read_candidate_payload(candidate_path)
        merge_result = merge_batch_candidates(batch, payload, seen_urls, now=datetime.now(timezone.utc))
        output_path = args.url_lists_dir / f"auto_{batch.batch_name}.txt"
        write_url_list_from_candidates(output_path, merge_result["selected_candidates"])

        written_count += 1
        emitted_urls.update(merge_result["emitted_urls"])

        print(f"Batch name: {batch.batch_name}")
        print(f"URL list: {output_path}")
        print(f"Selected count: {merge_result['selected_count']}")
        print(f"Skipped seen count: {merge_result['skipped_seen_count']}")
        print(f"Skipped old count: {merge_result['skipped_old_count']}")
        print(f"Skipped invalid count: {merge_result['skipped_invalid_count']}")
        print(f"Skipped title filter count: {merge_result['skipped_title_filter_count']}")
        print(f"Skipped url filter count: {merge_result['skipped_url_filter_count']}")
        print(f"Skipped subreddit filter count: {merge_result['skipped_subreddit_filter_count']}")

    if emitted_urls:
        save_seen_urls(seen_urls, args.state_path)

    print(f"Written batches: {written_count}")
    print(f"Seen URL count: {len(seen_urls)}")
    return 0 if written_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
