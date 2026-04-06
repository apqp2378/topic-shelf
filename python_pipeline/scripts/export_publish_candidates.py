from __future__ import annotations

import argparse
import json
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
EXPORT_DIR = PIPELINE_ROOT / "data" / "publish_candidates"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export publish candidates from a batch review decisions JSON file."
    )
    parser.add_argument(
        "target",
        help=(
            "A decisions JSON path such as "
            "python_pipeline/data/reviews/claude_code_tips_decisions.json "
            "or a batch stem such as claude_code_tips."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing publish-candidate export files if they already exist.",
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


def strip_known_suffixes(name: str) -> str:
    result = name
    if result.endswith("_decisions"):
        result = result[: -len("_decisions")]
    if result.endswith("_review"):
        result = result[: -len("_review")]
    if result.startswith("publish_candidates_"):
        result = result[len("publish_candidates_") :]
    return result


def resolve_decisions_path(target: str) -> tuple[Path, str]:
    normalized = target.strip()
    if not normalized:
        raise ValueError("Provide a batch stem or decisions JSON path.")

    if not is_path_like(normalized):
        batch_name = normalized
        decisions_path = REVIEW_DIR / f"{batch_name}_decisions.json"
        return decisions_path, batch_name

    candidate = Path(normalized)
    if candidate.exists():
        decisions_path = candidate
    else:
        fallback = REVIEW_DIR / candidate.name
        if fallback.exists():
            decisions_path = fallback
        else:
            raise FileNotFoundError(f"Decisions JSON file not found: {normalized}")

    batch_name = strip_known_suffixes(decisions_path.stem)
    return decisions_path, batch_name


def load_decisions(decisions_path: Path) -> dict[str, Any]:
    payload = read_json_file(decisions_path)
    if not isinstance(payload, dict):
        raise ValueError(f"Decisions file must contain a JSON object: {decisions_path}")

    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError(f"Decisions file must include a list named 'decisions': {decisions_path}")

    return payload


def resolve_cards_path(decisions_payload: dict[str, Any], batch_name: str) -> Path:
    source_value = str(decisions_payload.get("source_cards_file", "")).strip()
    if source_value:
        source_path = Path(source_value)
        if source_path.exists():
            return source_path

        fallback = CARDS_DIR / source_path.name
        if fallback.exists():
            return fallback

    fallback_name = f"cards_raw_from_urls_{batch_name}.json"
    fallback_path = CARDS_DIR / fallback_name
    if fallback_path.exists():
        return fallback_path

    raise FileNotFoundError(
        f"Could not resolve source cards file for batch {batch_name}."
    )


def load_cards_index(cards_path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json_file(cards_path)
    if not isinstance(payload, list):
        raise ValueError(f"Cards file must contain a JSON list: {cards_path}")

    cards_index: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Card record at index {index} is not an object: {cards_path}")
        card_id = str(item.get("card_id", "")).strip()
        if card_id:
            cards_index[card_id] = item
    return cards_index


def is_publish_candidate(decision: dict[str, Any]) -> bool:
    decision_value = str(decision.get("decision", "")).strip()
    candidate_value = decision.get("publish_candidate")
    return bool(candidate_value) or decision_value == "publish_candidate"


def build_publish_candidates(
    decisions_payload: dict[str, Any],
    cards_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    decisions = decisions_payload.get("decisions", [])

    for index, item in enumerate(decisions):
        if not isinstance(item, dict):
            raise ValueError(f"Decision record at index {index} is not an object.")

        if not is_publish_candidate(item):
            continue

        card_id = str(item.get("card_id", "")).strip()
        if not card_id:
            raise ValueError(f"Decision record at index {index} is missing card_id.")

        card = cards_index.get(card_id, {})
        if not card:
            print(f"Warning: card {card_id} was not found in the source cards file.")

        title = str(item.get("title", "")).strip() or str(card.get("title", "")).strip()
        source_url = str(card.get("source_url", "")).strip()
        subreddit = str(card.get("subreddit", "")).strip()
        review_note = str(item.get("review_note", "")).strip()
        decision_value = str(item.get("decision", "")).strip() or "publish_candidate"

        candidates.append(
            {
                "card_id": card_id,
                "title": title,
                "source_url": source_url,
                "subreddit": subreddit,
                "decision": decision_value,
                "publish_candidate": True,
                "review_note": review_note,
            }
        )

    return candidates


def build_markdown(
    batch_name: str,
    decisions_path: Path,
    cards_path: Path,
    generated_at: str,
    candidates: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append(f"# Publish Candidates: {batch_name}")
    lines.append("")
    lines.append("## Batch Info")
    lines.append(f"- Batch name: `{batch_name}`")
    lines.append(f"- Generated at: `{generated_at}`")
    lines.append(f"- Source decisions file: `{decisions_path.as_posix()}`")
    lines.append(f"- Source cards file: `{cards_path.as_posix()}`")
    lines.append(f"- Candidate count: `{len(candidates)}`")
    lines.append("")

    if not candidates:
        lines.append("> No publish candidates were selected for this batch.")
        lines.append("")

    lines.append("## Publish Candidates")
    lines.append("")
    for index, candidate in enumerate(candidates, start=1):
        lines.append(f"### {index}. `{candidate['card_id']}` - {candidate['title']}")
        if candidate["source_url"]:
            lines.append(f"- Source URL: `{candidate['source_url']}`")
        if candidate["subreddit"]:
            lines.append(f"- Subreddit: `{candidate['subreddit']}`")
        lines.append(f"- Decision: `{candidate['decision']}`")
        lines.append(f"- Review note: {candidate['review_note'] or '(none)'}")
        lines.append("")

    lines.append("## Summary")
    lines.append(f"- Publish candidates exported: `{len(candidates)}`")
    lines.append("")
    lines.append("## Next Steps")
    lines.append("- Review the exported markdown with the batch notes.")
    lines.append("- Use the exported JSON if you want a machine-readable handoff.")
    lines.append("")

    return "\n".join(lines)


def build_export_payload(
    batch_name: str,
    decisions_path: Path,
    cards_path: Path,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "batch_name": batch_name,
        "generated_at": generated_at,
        "source_decisions_file": decisions_path.as_posix(),
        "source_cards_file": cards_path.as_posix(),
        "publish_candidate_count": len(candidates),
        "publish_candidates": candidates,
    }


def main() -> int:
    args = parse_args()

    try:
        decisions_path, batch_name = resolve_decisions_path(args.target)
        decisions_payload = load_decisions(decisions_path)
        cards_path = resolve_cards_path(decisions_payload, batch_name)
        cards_index = load_cards_index(cards_path)
        candidates = build_publish_candidates(decisions_payload, cards_index)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc))
        return 1

    if not candidates:
        print("Warning: no publish candidates were found in the selected decisions file.")

    export_payload = build_export_payload(batch_name, decisions_path, cards_path, candidates)
    export_markdown = build_markdown(
        batch_name,
        decisions_path,
        cards_path,
        export_payload["generated_at"],
        candidates,
    )

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    markdown_path = EXPORT_DIR / f"publish_candidates_{batch_name}.md"
    json_path = EXPORT_DIR / f"publish_candidates_{batch_name}.json"

    if (markdown_path.exists() or json_path.exists()) and not args.overwrite:
        print("Publish-candidate export already exists. Use --overwrite to replace both files.")
        return 1

    write_text_file(markdown_path, export_markdown)
    write_json_file(json_path, export_payload)

    print(f"Batch name: {batch_name}")
    print(f"Source decisions file: {decisions_path}")
    print(f"Source cards file: {cards_path}")
    print(f"Export markdown: {markdown_path}")
    print(f"Export JSON: {json_path}")
    print(f"Publish candidate count: {len(candidates)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
