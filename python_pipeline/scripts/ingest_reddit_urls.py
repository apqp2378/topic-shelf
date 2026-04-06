from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.io_utils import build_raw_from_urls_output_path
from pipeline.url_fetchers import build_url_fetcher
from pipeline.url_ingestion import ingest_url_list


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Reddit thread URLs from a txt list and emit raw JSON for run_pipeline.py."
    )
    parser.add_argument(
        "url_list_path",
        nargs="?",
        type=Path,
        help="Path to a txt file under python_pipeline/data/url_lists/.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        help="Optional explicit raw JSON output path.",
    )
    return parser.parse_args()


def resolve_input_path(url_list_path: Path | None) -> Path:
    if url_list_path is not None:
        return url_list_path

    default_dir = PIPELINE_ROOT / "data" / "url_lists"
    raise FileNotFoundError(
        f"Provide a txt URL list path. Expected input folder: {default_dir}"
    )


def main() -> int:
    args = parse_args()

    try:
        input_path = resolve_input_path(args.url_list_path)
    except FileNotFoundError as exc:
        print(str(exc))
        return 1

    output_path = args.output_path
    if output_path is None:
        output_path = build_raw_from_urls_output_path(input_path)

    try:
        fetcher = build_url_fetcher("reddit_public")
        result = ingest_url_list(
            input_path,
            fetcher,
            output_path=output_path,
        )
    except FileNotFoundError as exc:
        print(str(exc))
        return 1
    except ValueError as exc:
        print(str(exc))
        return 1

    print(f"Input URL list: {input_path}")
    print(f"Output raw JSON: {result.output_path}")
    print(f"Input URL count: {result.input_count}")
    print(f"Canonical unique URL count: {result.unique_count}")
    print(f"Success count: {result.success_count}")
    print(f"Failure count: {result.failure_count}")
    print(f"Records written: {len(result.records)}")

    if result.successes:
        print("Successful URLs:")
        for success in result.successes:
            print(
                f"- {success.canonical_url} -> {success.raw_id} ({success.post_id})"
            )

    if result.failures:
        print("Failed URLs:")
        for failure in result.failures:
            print(f"- {failure.canonical_url} -> {failure.reason}")

    return 0 if result.success_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
