from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.card_builder import build_cards
from pipeline.io_utils import build_cards_output_path, read_json_file, write_json_file


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python python_pipeline/scripts/make_cards.py <normalized_json_path>")
        return 1

    normalized_path = Path(sys.argv[1])
    payload = read_json_file(normalized_path)

    if not isinstance(payload, list):
        print("Normalized input must be a JSON list.")
        return 1

    cards = build_cards(payload)
    output_path = build_cards_output_path(normalized_path)
    write_json_file(output_path, cards)

    print(f"Input file: {normalized_path}")
    print(f"Cards file: {output_path}")
    print(f"Cards created: {len(cards)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
