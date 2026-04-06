from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
RAW_DIR = PIPELINE_ROOT / "data" / "raw"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Purge old generated raw JSON files from python_pipeline/data/raw."
    )
    retention_group = parser.add_mutually_exclusive_group(required=True)
    retention_group.add_argument(
        "--older-than-hours",
        type=float,
        help="Delete generated raw files older than this many hours.",
    )
    retention_group.add_argument(
        "--older-than-days",
        type=float,
        help="Delete generated raw files older than this many days.",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete matching files instead of dry-running.",
    )
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be deleted without removing anything.",
    )
    return parser.parse_args()


def is_generated_raw_filename(filename: str) -> bool:
    """Match only the ingestion-generated raw outputs we intentionally purge."""

    return filename.startswith("raw_from_urls_") and filename.endswith(".json")


def list_generated_raw_files(raw_dir: Path) -> list[Path]:
    if not raw_dir.exists():
        return []

    return sorted(
        path
        for path in raw_dir.glob("*.json")
        if path.is_file() and is_generated_raw_filename(path.name)
    )


def resolve_cutoff(args: argparse.Namespace) -> datetime:
    if getattr(args, "older_than_hours", None) is not None:
        delta = timedelta(hours=float(args.older_than_hours))
    else:
        delta = timedelta(days=float(args.older_than_days))
    return datetime.now(timezone.utc) - delta


def is_older_than(path: Path, cutoff: datetime) -> bool:
    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return modified_at <= cutoff


def main() -> int:
    args = parse_args()
    cutoff = resolve_cutoff(args)
    dry_run = not getattr(args, "apply", False) or getattr(args, "dry_run", False)

    scanned_files = 0
    matched_files = 0
    candidate_files: list[Path] = []

    for path in sorted(RAW_DIR.glob("*.json")):
        scanned_files += 1
        if not is_generated_raw_filename(path.name):
            continue
        matched_files += 1
        if is_older_than(path, cutoff):
            candidate_files.append(path)

    deleted_files: list[Path] = []
    if not dry_run:
        for path in candidate_files:
            path.unlink()
            deleted_files.append(path)

    print(f"Raw directory: {RAW_DIR}")
    print(f"Retention cutoff: {cutoff.isoformat()}")
    print(f"Mode: {'dry-run' if dry_run else 'apply'}")
    print(f"Scanned files: {scanned_files}")
    print(f"Matched generated raw files: {matched_files}")
    print(f"Files to delete: {len(candidate_files)}")
    for path in candidate_files:
        print(f"- {path.name}")
    print(f"Files actually deleted: {len(deleted_files)}")
    for path in deleted_files:
        print(f"- {path.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
