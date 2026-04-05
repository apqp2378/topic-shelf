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


def build_normalized_output_path(raw_path: Path) -> Path:
    return raw_path.parent.parent / "normalized" / f"normalized_{raw_path.name}"


def build_cards_output_path(normalized_path: Path) -> Path:
    normalized_name = normalized_path.name
    if normalized_name.startswith("normalized_"):
        suffix = normalized_name[len("normalized_") :]
    else:
        suffix = normalized_name
    return normalized_path.parent.parent / "cards" / f"cards_{suffix}"


def get_file_mtime(path: Path) -> float:
    return path.stat().st_mtime


def find_latest_json_file(directory: Path) -> Path:
    json_files = sorted(directory.glob("*.json"), key=get_file_mtime)
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {directory}")
    return json_files[-1]
