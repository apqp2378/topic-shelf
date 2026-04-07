from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.io_utils import read_json_file, write_text_file

PUBLISH_CANDIDATES_DIR = PIPELINE_ROOT / "data" / "publish_candidates"
BLOG_DRAFT_SEEDS_DIR = PIPELINE_ROOT / "data" / "blog_draft_seeds"

FRAMING_CUE_RE = re.compile(
    r"\b(frame|framing|reframe|reframing|headline|title|rewrite|reword|"
    r"보정|프레이밍|제목)\b",
    re.IGNORECASE,
)
QUANTIFIED_CLAIM_RE = re.compile(
    r"\b\d[\d,]*(?:\+)?\b.*\b(offer|offers|job|jobs|client|clients|customer|customers|"
    r"user|users|sale|sales|download|downloads|win|wins)\b",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export blog draft seed markdown files from publish-candidate exports."
    )
    parser.add_argument(
        "target",
        help=(
            "A publish-candidates JSON or markdown path such as "
            "python_pipeline/data/publish_candidates/publish_candidates_claude_code_tips.json, "
            "the matching .md path, or a batch stem such as claude_code_tips."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing blog draft seed files if they already exist.",
    )
    return parser.parse_args()


def is_path_like(target: str) -> bool:
    candidate = Path(target)
    return (
        candidate.suffix.lower() in {".json", ".md"}
        or len(candidate.parts) > 1
        or "/" in target
        or "\\" in target
    )


def strip_publish_candidate_prefixes(name: str) -> str:
    result = name
    if result.startswith("publish_candidates_"):
        result = result[len("publish_candidates_") :]
    if result.endswith("_publish_candidates"):
        result = result[: -len("_publish_candidates")]
    return result


def resolve_publish_candidates_path(target: str) -> tuple[Path, str]:
    normalized = target.strip()
    if not normalized:
        raise ValueError("Provide a batch stem or publish-candidates path.")

    if not is_path_like(normalized):
        batch_name = normalized
        export_path = PUBLISH_CANDIDATES_DIR / f"publish_candidates_{batch_name}.json"
        return export_path, batch_name

    candidate = Path(normalized)
    search_paths = [candidate]

    if candidate.suffix.lower() == ".md":
        search_paths.append(candidate.with_suffix(".json"))
        search_paths.append(PUBLISH_CANDIDATES_DIR / candidate.with_suffix(".json").name)
    elif candidate.suffix.lower() == ".json":
        search_paths.append(PUBLISH_CANDIDATES_DIR / candidate.name)
        search_paths.append(candidate.with_suffix(".md"))
    else:
        search_paths.append(PUBLISH_CANDIDATES_DIR / candidate.name)

    export_path = None
    for path in search_paths:
        if path.exists() and path.suffix.lower() == ".json":
            export_path = path
            break

    if export_path is None:
        raise FileNotFoundError(f"Publish-candidates export file not found: {normalized}")

    batch_name = strip_publish_candidate_prefixes(export_path.stem)
    return export_path, batch_name


def load_publish_candidates(export_path: Path) -> dict[str, Any]:
    payload = read_json_file(export_path)
    if not isinstance(payload, dict):
        raise ValueError(f"Publish-candidates export must contain a JSON object: {export_path}")

    candidates = payload.get("publish_candidates")
    if not isinstance(candidates, list):
        raise ValueError(
            f"Publish-candidates export must include a list named 'publish_candidates': {export_path}"
        )

    return payload


def normalize_candidate_text(value: object) -> str:
    return str(value or "").strip()


def slugify_title(title: str, fallback: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", title.lower()).strip("_")
    return slug or fallback


def infer_framing_note(review_note: str, title: str) -> str | None:
    notes: list[str] = []
    if review_note and FRAMING_CUE_RE.search(review_note):
        notes.append(f"Review note suggests framing or headline work: {review_note}")

    if title and QUANTIFIED_CLAIM_RE.search(title):
        notes.append(
            "Headline contains a quantified claim. Verify the framing before publishing."
        )

    if notes:
        return " ".join(notes)
    return None


def build_draft_markdown(
    batch_name: str,
    source_publish_candidates_file: Path,
    candidate: dict[str, Any],
    generated_at: str,
    ordinal: int,
) -> str:
    card_id = normalize_candidate_text(candidate.get("card_id"))
    title = normalize_candidate_text(candidate.get("title")) or "(untitled)"
    source_url = normalize_candidate_text(candidate.get("source_url"))
    subreddit = normalize_candidate_text(candidate.get("subreddit"))
    review_note = normalize_candidate_text(candidate.get("review_note"))
    decision = normalize_candidate_text(candidate.get("decision")) or "publish_candidate"
    slug = slugify_title(title, card_id or f"candidate_{ordinal:03d}")
    framing_note = infer_framing_note(review_note, title)

    lines: list[str] = []
    lines.append(f"# Draft Seed: {title}")
    lines.append("")
    lines.append("## Seed Info")
    lines.append(f"- Batch name: `{batch_name}`")
    lines.append(f"- Generated at: `{generated_at}`")
    lines.append(f"- Source publish-candidates file: `{source_publish_candidates_file.as_posix()}`")
    lines.append(f"- Card ID: `{card_id}`")
    lines.append(f"- Decision: `{decision}`")
    if source_url:
        lines.append(f"- Source URL: `{source_url}`")
    if subreddit:
        lines.append(f"- Subreddit: `{subreddit}`")
    if review_note:
        lines.append(f"- Review note: {review_note}")
    lines.append("")
    lines.append("## Working Headline")
    lines.append(f"- {title}")
    lines.append("- [ ] Adjust the headline if the review note calls for reframing.")
    lines.append("")
    lines.append("## Core Takeaway")
    lines.append("- [ ] State the main lesson in one or two sentences.")
    lines.append("")
    lines.append("## Why This Matters")
    lines.append("- [ ] Explain why a reader should care now.")
    lines.append("")
    lines.append("## Evidence / Supporting Points")
    lines.append("- [ ] Pull the strongest concrete detail from the source thread.")
    lines.append("- [ ] Add one example, quote, or measured result.")
    lines.append("")
    lines.append("## Caution / Framing Notes")
    if framing_note:
        lines.append(f"- {framing_note}")
    else:
        lines.append("- [ ] Check for title, framing, or accuracy issues before drafting.")
    lines.append("- [ ] Make sure the final draft does not overstate the source thread.")
    lines.append("")
    lines.append("## Possible Outline")
    lines.append("1. Hook with the main claim or takeaway.")
    lines.append("2. Explain the context and the problem being solved.")
    lines.append("3. Share the evidence or workflow details.")
    lines.append("4. Close with what readers can apply themselves.")
    lines.append("")
    lines.append("## Notes for Rewrite")
    lines.append("- [ ] Leave room for the final tone and structure.")
    lines.append("- [ ] Replace placeholders with your own judgment.")
    lines.append("- [ ] Confirm any quantified claim before publication.")
    lines.append("")
    lines.append("## File Metadata")
    lines.append(f"- Suggested filename slug: `{slug}`")
    lines.append(f"- Candidate ordinal: `{ordinal:03d}`")
    lines.append("")

    return "\n".join(lines)


def build_output_path(batch_name: str, ordinal: int, title: str, card_id: str) -> Path:
    slug_source = title or card_id or f"candidate_{ordinal:03d}"
    slug = slugify_title(slug_source, card_id or f"candidate_{ordinal:03d}")
    return BLOG_DRAFT_SEEDS_DIR / f"{batch_name}__{ordinal:03d}__{slug}.md"


def main() -> int:
    args = parse_args()

    try:
        export_path, batch_name = resolve_publish_candidates_path(args.target)
        payload = load_publish_candidates(export_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc))
        return 1

    candidates = payload.get("publish_candidates", [])
    if not candidates:
        print("Warning: no publish candidates were found in the selected export file.")

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    BLOG_DRAFT_SEEDS_DIR.mkdir(parents=True, exist_ok=True)

    output_paths: list[Path] = []
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            print(f"Publish candidate at index {index - 1} is not an object.")
            return 1

        card_id = normalize_candidate_text(candidate.get("card_id"))
        title = normalize_candidate_text(candidate.get("title"))
        output_path = build_output_path(batch_name, index, title, card_id)
        output_paths.append(output_path)

        if output_path.exists() and not args.overwrite:
            print(f"Draft seed already exists: {output_path}. Use --overwrite to replace it.")
            return 1

    for index, candidate in enumerate(candidates, start=1):
        card_id = normalize_candidate_text(candidate.get("card_id"))
        title = normalize_candidate_text(candidate.get("title"))
        output_path = build_output_path(batch_name, index, title, card_id)
        markdown = build_draft_markdown(
            batch_name=batch_name,
            source_publish_candidates_file=export_path,
            candidate=candidate,
            generated_at=generated_at,
            ordinal=index,
        )
        write_text_file(output_path, markdown)

    print(f"Batch name: {batch_name}")
    print(f"Source publish-candidates file: {export_path}")
    print(f"Draft seed count: {len(candidates)}")
    for path in output_paths:
        print(f"- {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
