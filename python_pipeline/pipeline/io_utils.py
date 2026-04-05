from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json_file(path: Path, data: Any) -> None:
    ensure_parent_dir(path)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def write_text_file(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with path.open("w", encoding="utf-8") as file:
        file.write(text)


def build_normalized_output_path(raw_path: Path) -> Path:
    return raw_path.parent.parent / "normalized" / f"normalized_{raw_path.name}"


def build_cards_output_path(normalized_path: Path) -> Path:
    normalized_name = normalized_path.name
    if normalized_name.startswith("normalized_"):
        suffix = normalized_name[len("normalized_") :]
    else:
        suffix = normalized_name
    return normalized_path.parent.parent / "cards" / f"cards_{suffix}"


def build_cards_with_summary_output_path(cards_path: Path) -> Path:
    cards_name = cards_path.name
    if cards_name.startswith("cards_"):
        suffix = cards_name[len("cards_") :]
    else:
        suffix = cards_name
    return cards_path.parent / f"cards_with_summary_{suffix}"


def build_cards_with_translation_output_path(cards_path: Path) -> Path:
    cards_name = cards_path.name
    if cards_name.startswith("cards_with_summary_"):
        suffix = cards_name[len("cards_with_summary_") :]
    elif cards_name.startswith("cards_"):
        suffix = cards_name[len("cards_") :]
    else:
        suffix = cards_name
    return cards_path.parent / f"cards_with_translation_{suffix}"


def build_cards_with_topics_output_path(cards_path: Path) -> Path:
    cards_name = cards_path.name
    prefixes = (
        "cards_with_translation_",
        "cards_with_summary_",
        "cards_with_topics_",
        "cards_",
    )

    suffix = cards_name
    for prefix in prefixes:
        if cards_name.startswith(prefix):
            suffix = cards_name[len(prefix) :]
            break

    return cards_path.parent / f"cards_with_topics_{suffix}"


def build_bundles_output_path(cards_path: Path) -> Path:
    cards_name = cards_path.name
    prefixes = (
        "cards_with_topics_",
        "cards_with_translation_",
        "cards_with_summary_",
        "cards_",
        "bundles_",
    )

    suffix = cards_name
    for prefix in prefixes:
        if cards_name.startswith(prefix):
            suffix = cards_name[len(prefix) :]
            break

    return cards_path.parent / f"bundles_{suffix}"


def build_blog_drafts_output_path(cards_path: Path) -> Path:
    cards_name = cards_path.name
    prefixes = (
        "bundles_",
        "cards_with_topics_",
        "cards_with_translation_",
        "cards_with_summary_",
        "cards_",
        "blog_drafts_",
    )

    suffix = cards_name
    for prefix in prefixes:
        if cards_name.startswith(prefix):
            suffix = cards_name[len(prefix) :]
            break

    return cards_path.parent / f"blog_drafts_{suffix}"


def build_quality_reviews_output_path(cards_path: Path) -> Path:
    cards_name = cards_path.name
    prefixes = (
        "blog_drafts_",
        "bundles_",
        "cards_with_topics_",
        "cards_with_translation_",
        "cards_with_summary_",
        "cards_",
        "quality_reviews_",
    )

    suffix = cards_name
    for prefix in prefixes:
        if cards_name.startswith(prefix):
            suffix = cards_name[len(prefix) :]
            break

    return cards_path.parent / f"quality_reviews_{suffix}"


def build_publish_export_output_path(source_path: Path, source_type: str) -> Path:
    source_name = source_path.name
    prefixes = (
        "blog_drafts_",
        "bundles_",
        "cards_with_topics_",
        "cards_with_translation_",
        "cards_with_summary_",
        "cards_",
    )

    suffix = source_name
    for prefix in prefixes:
        if source_name.startswith(prefix):
            suffix = source_name[len(prefix) :]
            break

    safe_source_type = source_type.strip().lower().replace(" ", "_")
    if safe_source_type == "blog_drafts":
        file_tag = "blog_draft"
    elif safe_source_type in ("bundles", "cards"):
        file_tag = safe_source_type
    else:
        file_tag = "cards"

    return source_path.parent.parent / "publish" / f"publish_{file_tag}_{suffix}.md"


def get_file_mtime(path: Path) -> float:
    return path.stat().st_mtime


def find_latest_json_file(directory: Path) -> Path:
    json_files = sorted(directory.glob("*.json"), key=get_file_mtime)
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {directory}")
    return json_files[-1]
