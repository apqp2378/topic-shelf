from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.io_utils import build_normalized_output_path, read_json_file, write_json_file
from pipeline.normalizers import normalize_records
from pipeline.validators import validate_raw_payload


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python python_pipeline/scripts/normalize_devvit_raw.py <raw_json_path>")
        return 1

    raw_path = Path(sys.argv[1])
    payload = read_json_file(raw_path)
    valid_records, issues = validate_raw_payload(payload)

    if issues:
        print("Normalization stopped because validation failed.")
        for issue in issues:
            print(f"- record {issue.record_index}: {issue.field_name} -> {issue.message}")
        return 1

    normalized_records = normalize_records(valid_records)
    output_path = build_normalized_output_path(raw_path)
    write_json_file(output_path, normalized_records)

    print(f"Input file: {raw_path}")
    print(f"Normalized file: {output_path}")
    print(f"Normalized records: {len(normalized_records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
