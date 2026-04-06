from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.io_utils import read_json_file, write_json_file, write_text_file

REVIEW_DIR = PIPELINE_ROOT / "data" / "reviews"
CARDS_DIR = PIPELINE_ROOT / "data" / "cards"

_CARD_PREFIXES = (
    "cards_with_summary_",
    "cards_with_translation_",
    "cards_with_topics_",
    "cards_",
    "normalized_",
    "raw_from_urls_",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a review scaffold for a completed URL batch."
    )
    parser.add_argument(
        "target",
        help=(
            "Batch stem such as claude_code_tips or a cards file path such as "
            "python_pipeline/data/cards/cards_raw_from_urls_claude_code_tips.json."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing review scaffold files if they already exist.",
    )
    return parser.parse_args()


def is_path_like(target: str) -> bool:
    candidate = Path(target)
    return (
        candidate.suffix.lower() == ".json"
        or len(candidate.parts) > 1
        or "/" in target
        or "\\" in target
    )


def strip_known_prefixes(name: str) -> str:
    result = name
    changed = True
    while changed:
        changed = False
        for prefix in _CARD_PREFIXES:
            if result.startswith(prefix):
                result = result[len(prefix) :]
                changed = True
                break
    return result


def derive_batch_name_from_cards_path(cards_path: Path) -> str:
    stem = cards_path.stem
    stem = strip_known_prefixes(stem)
    return stem


def resolve_source_cards_path(target: str) -> tuple[Path, str]:
    normalized = target.strip()
    if not normalized:
        raise ValueError("Provide a batch stem or cards file path.")

    if not is_path_like(normalized):
        batch_name = normalized
        cards_path = CARDS_DIR / f"cards_raw_from_urls_{batch_name}.json"
        return cards_path, batch_name

    candidate = Path(normalized)
    if candidate.exists():
        cards_path = candidate
    else:
        fallback = CARDS_DIR / candidate.name
        if fallback.exists():
            cards_path = fallback
        else:
            raise FileNotFoundError(f"Cards file not found: {normalized}")

    batch_name = derive_batch_name_from_cards_path(cards_path)
    return cards_path, batch_name


def build_review_paths(batch_name: str) -> tuple[Path, Path]:
    review_path = REVIEW_DIR / f"{batch_name}_review.md"
    decisions_path = REVIEW_DIR / f"{batch_name}_decisions.json"
    return review_path, decisions_path


def load_cards(cards_path: Path) -> list[dict[str, Any]]:
    payload = read_json_file(cards_path)
    if not isinstance(payload, list):
        raise ValueError(f"Cards file must contain a JSON list: {cards_path}")

    cards: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Card record at index {index} is not an object: {cards_path}")
        cards.append(item)
    return cards


def build_decisions_payload(
    batch_name: str,
    source_cards_file: Path,
    cards: list[dict[str, Any]],
) -> dict[str, Any]:
    reviewed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    decisions = []

    for card in cards:
        card_id = str(card.get("card_id", "")).strip()
        title = str(card.get("title", "")).strip()
        decisions.append(
            {
                "card_id": card_id,
                "title": title,
                "decision": "hold",
                "publish_candidate": False,
                "review_note": "",
            }
        )

    return {
        "batch_name": batch_name,
        "source_cards_file": source_cards_file.as_posix(),
        "reviewed_at": reviewed_at,
        "decisions": decisions,
    }


def build_review_markdown(
    batch_name: str,
    source_cards_file: Path,
    cards: list[dict[str, Any]],
    reviewed_at: str,
) -> str:
    lines: list[str] = []
    lines.append(f"# Batch Review: {batch_name}")
    lines.append("")
    lines.append("## Batch Info")
    lines.append(f"- Batch name: `{batch_name}`")
    lines.append(f"- Source cards file: `{source_cards_file.as_posix()}`")
    lines.append(f"- Review scaffold created at: `{reviewed_at}`")
    lines.append(f"- Card count: `{len(cards)}`")
    lines.append("")
    lines.append("## Per-Card Review")
    lines.append("")

    for index, card in enumerate(cards, start=1):
        card_id = str(card.get("card_id", "")).strip() or f"card_{index}"
        title = str(card.get("title", "")).strip() or "(untitled)"
        source_url = str(card.get("source_url", "")).strip()

        lines.append(f"### {index}. `{card_id}` - {title}")
        if source_url:
            lines.append(f"- Source URL: `{source_url}`")
        lines.append("- Decision: `hold`")
        lines.append("- Publish candidate: `false`")
        lines.append("- Review note:")
        lines.append("  - ")
        lines.append("")

    lines.append("## Final Batch Summary")
    lines.append("- Publish candidates:")
    lines.append("- Keep:")
    lines.append("- Hold:")
    lines.append("- Drop:")
    lines.append("")
    lines.append("## Next Actions")
    lines.append("- Fill in the decisions JSON sidecar.")
    lines.append("- Update the markdown notes if any card needs context.")
    lines.append("- Use the review artifacts to decide what should be published.")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    try:
        cards_path, batch_name = resolve_source_cards_path(args.target)
        cards = load_cards(cards_path)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc))
        return 1

    review_path, decisions_path = build_review_paths(batch_name)
    review_exists = review_path.exists()
    decisions_exists = decisions_path.exists()
    if (review_exists or decisions_exists) and not args.overwrite:
        print(
            "Review scaffold already exists. Use --overwrite to replace both files."
        )
        return 1

    review_path.parent.mkdir(parents=True, exist_ok=True)
    decisions_payload = build_decisions_payload(batch_name, cards_path, cards)
    review_markdown = build_review_markdown(
        batch_name,
        cards_path,
        cards,
        decisions_payload["reviewed_at"],
    )

    write_json_file(decisions_path, decisions_payload)
    write_text_file(review_path, review_markdown)

    print(f"Batch name: {batch_name}")
    print(f"Source cards file: {cards_path}")
    print(f"Review markdown: {review_path}")
    print(f"Decision JSON: {decisions_path}")
    print(f"Card count: {len(cards)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
