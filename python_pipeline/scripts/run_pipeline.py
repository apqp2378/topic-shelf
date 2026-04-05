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


def main() -> int:
    raw_path = resolve_input_path()
    payload = read_json_file(raw_path)
    valid_records, issues = validate_raw_payload(payload)

    print(f"Raw input: {raw_path}")

    if issues:
        print("Pipeline stopped during validation.")
        for issue in issues:
            print(f"- record {issue.record_index}: {issue.field_name} -> {issue.message}")
        return 1

    normalized_records = normalize_records(valid_records)
    normalized_path = build_normalized_output_path(raw_path)
    write_json_file(normalized_path, normalized_records)

    cards = build_cards(normalized_records)
    cards_path = build_cards_output_path(normalized_path)
    write_json_file(cards_path, cards)

    print(f"Normalized output: {normalized_path}")
    print(f"Cards output: {cards_path}")
    print(f"Final record count: {len(cards)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
