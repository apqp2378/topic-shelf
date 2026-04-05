from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.io_utils import read_json_file
from pipeline.validators import REQUIRED_RAW_FIELDS, validate_raw_payload


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python python_pipeline/scripts/validate_raw.py <raw_json_path>")
        return 1

    raw_path = Path(sys.argv[1])
    payload = read_json_file(raw_path)
    valid_records, issues = validate_raw_payload(payload)

    print(f"Input file: {raw_path}")
    print(f"Required fields: {', '.join(REQUIRED_RAW_FIELDS)}")

    if issues:
        print("Validation failed.")
        for issue in issues:
            print(
                f"- record {issue.record_index}: {issue.field_name} -> {issue.message}"
            )
        return 1

    print("Validation passed.")
    print(f"Valid records: {len(valid_records)}")
    print("Missing required fields: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
