from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.card_builder import build_cards
from pipeline.io_utils import (
    build_cards_output_path,
    build_normalized_output_path,
    find_latest_json_file,
    read_json_file,
    write_json_file,
)
from pipeline.normalizers import normalize_records
from pipeline.validators import validate_raw_payload


def resolve_input_path() -> Path:
    if len(sys.argv) >= 2:
        return Path(sys.argv[1])
    return find_latest_json_file(PIPELINE_ROOT / "data" / "raw")


def count_keep_records(payload: object) -> int:
    if not isinstance(payload, list):
        return 0

    keep_count = 0
    for item in payload:
        if isinstance(item, dict) and clean_string_value(item.get("moderator_status")) == "keep":
            keep_count += 1
    return keep_count


def main() -> int:
    raw_path = resolve_input_path()
    payload = read_json_file(raw_path)
    valid_records, issues = validate_raw_payload(payload)
    raw_input_count = len(payload) if isinstance(payload, list) else 0
    keep_count = count_keep_records(payload)
    dropped_count = max(keep_count - len(valid_records), 0)

    print(f"Raw input: {raw_path}")
    print(f"Raw input count: {raw_input_count}")
    print(f"Keep count: {keep_count}")
    print(f"Validated count: {len(valid_records)}")
    print(f"Dropped count: {dropped_count}")

    if issues:
        print("Validation issues:")
        for issue in issues:
            record_number = issue.record_index + 1 if issue.record_index >= 0 else "root"
            print(f"- record {record_number}: {issue.field_name} -> {issue.message}")

    normalized_records = normalize_records(valid_records)
    normalized_path = build_normalized_output_path(raw_path)
    write_json_file(normalized_path, normalized_records)

    cards = build_cards(normalized_records)
    cards_path = build_cards_output_path(normalized_path)
    write_json_file(cards_path, cards)

    print(f"Normalized output: {normalized_path}")
    print(f"Normalized count: {len(normalized_records)}")
    print(f"Cards output: {cards_path}")
    print(f"Cards count: {len(cards)}")

    if issues:
        return 1
    return 0


def clean_string_value(value: object) -> str:
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
