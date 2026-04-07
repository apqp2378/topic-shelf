from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import urlopen
import xml.etree.ElementTree as ET

try:
    from pipeline.io_utils import read_json_file, write_json_file, write_text_file
except ModuleNotFoundError:  # pragma: no cover - import shim for direct package imports
    from python_pipeline.pipeline.io_utils import read_json_file, write_json_file, write_text_file


PIPELINE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PIPELINE_ROOT / "config" / "auto_sources.yaml"
DEFAULT_CANDIDATE_DIR = PIPELINE_ROOT / "data" / "url_candidates" / "rss"
DEFAULT_URL_LIST_DIR = PIPELINE_ROOT / "data" / "url_lists"
DEFAULT_STATE_PATH = PIPELINE_ROOT / "state" / "seen_urls.json"


@dataclass(frozen=True)
class AutoSourceDefinition:
    type: str
    url: str
    source_name: str


@dataclass(frozen=True)
class AutoBatchDefinition:
    batch_name: str
    batch_mode: str
    enabled: bool
    max_urls: int
    recent_days: int
    sources: list[AutoSourceDefinition]
    include_title_keywords: list[str]
    exclude_title_keywords: list[str]
    exclude_url_keywords: list[str]
    allow_subreddits: list[str]
    deny_subreddits: list[str]
    parser_fallback_enabled: bool = False


def load_auto_source_batches(config_path: Path = DEFAULT_CONFIG_PATH) -> list[AutoBatchDefinition]:
    payload = load_yaml_compatible_json(config_path)

    parser_fallback_enabled = bool(payload.get("parser_fallback_enabled", False))
    batches_payload = payload.get("batches")
    if not isinstance(batches_payload, list):
        raise ValueError("auto source config must include a list named 'batches'.")

    batches: list[AutoBatchDefinition] = []
    for index, item in enumerate(batches_payload):
        if not isinstance(item, dict):
            raise ValueError(f"Batch config at index {index} must be an object.")

        batch_name = str(item.get("batch_name", "")).strip()
        if not batch_name:
            raise ValueError(f"Batch config at index {index} is missing batch_name.")

        batch_mode = str(item.get("batch_mode", "")).strip().lower()
        if batch_mode not in {"production", "baseline"}:
            raise ValueError(
                f"Batch {batch_name} must set batch_mode to 'production' or 'baseline'."
            )

        enabled = bool(item.get("enabled", False))
        max_urls = parse_positive_int(item.get("max_urls"), f"batch {batch_name} max_urls")
        recent_days = parse_positive_int(item.get("recent_days"), f"batch {batch_name} recent_days")
        include_title_keywords = parse_string_list(item.get("include_title_keywords"))
        exclude_title_keywords = parse_string_list(item.get("exclude_title_keywords"))
        exclude_url_keywords = parse_string_list(item.get("exclude_url_keywords"))
        allow_subreddits = parse_string_list(item.get("allow_subreddits"))
        deny_subreddits = parse_string_list(item.get("deny_subreddits"))

        sources_payload = item.get("sources")
        if not isinstance(sources_payload, list) or not sources_payload:
            raise ValueError(f"Batch {batch_name} must include at least one source.")

        sources: list[AutoSourceDefinition] = []
        for source_index, source_item in enumerate(sources_payload):
            if not isinstance(source_item, dict):
                raise ValueError(
                    f"Source at index {source_index} in batch {batch_name} must be an object."
                )

            source_type = str(source_item.get("type", "")).strip().lower()
            if source_type != "rss":
                raise ValueError(
                    f"Batch {batch_name} source {source_index} uses unsupported type {source_type!r}."
                )

            source_url = str(source_item.get("url", "")).strip()
            source_name = str(source_item.get("source_name", "")).strip()
            if not source_url or not source_name:
                raise ValueError(
                    f"Batch {batch_name} source {source_index} must include url and source_name."
                )

            sources.append(
                AutoSourceDefinition(
                    type=source_type,
                    url=source_url,
                    source_name=source_name,
                )
            )

        batches.append(
            AutoBatchDefinition(
                batch_name=batch_name,
                batch_mode=batch_mode,
                enabled=enabled,
                max_urls=max_urls,
                recent_days=recent_days,
                sources=sources,
                include_title_keywords=include_title_keywords,
                exclude_title_keywords=exclude_title_keywords,
                exclude_url_keywords=exclude_url_keywords,
                allow_subreddits=allow_subreddits,
                deny_subreddits=deny_subreddits,
                parser_fallback_enabled=parser_fallback_enabled,
            )
        )

    return batches


def load_enabled_batches(config_path: Path = DEFAULT_CONFIG_PATH) -> list[AutoBatchDefinition]:
    return [batch for batch in load_auto_source_batches(config_path) if batch.enabled]


def load_yaml_compatible_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError(f"Auto source config must contain a JSON object: {path}")
    return payload


def parse_positive_int(value: object, field_name: str) -> int:
    try:
        parsed = int(value)
    except Exception as exc:
        raise ValueError(f"{field_name} must be a positive integer.") from exc

    if parsed < 1:
        raise ValueError(f"{field_name} must be a positive integer.")
    return parsed


def parse_string_list(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError("Config filter values must be lists of strings.")

    result: list[str] = []
    for item in value:
        text = str(item).strip().lower()
        if text:
            result.append(text)
    return result


def collect_batch_candidates(
    batch: AutoBatchDefinition,
    collected_at: datetime | None = None,
) -> dict[str, Any]:
    fetched_at = ensure_utc_datetime(collected_at)
    fetched_at_iso = iso_z(fetched_at)

    candidates: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []
    source_errors: list[dict[str, Any]] = []

    for source in batch.sources:
        try:
            feed_items = fetch_rss_items(source.url)
        except Exception as exc:
            source_errors.append(
                {
                    "source_name": source.source_name,
                    "source_url": source.url,
                    "source_type": source.type,
                    "error": str(exc),
                }
            )
            source_summaries.append(
                {
                    "source_name": source.source_name,
                    "source_url": source.url,
                    "source_type": source.type,
                    "candidate_count": 0,
                    "error": str(exc),
                }
            )
            continue

        source_candidate_count = 0
        source_subreddit = extract_reddit_subreddit_from_url(source.url)
        for item in feed_items:
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            published_at = item.get("published_at", "")
            if not title or not url:
                continue

            normalized_url = normalize_url(url)
            candidates.append(
                {
                    "batch_name": batch.batch_name,
                    "batch_mode": batch.batch_mode,
                    "source_name": source.source_name,
                    "source_type": source.type,
                    "source_feed_url": source.url,
                    "source_subreddit": source_subreddit,
                    "title": title,
                    "url": url,
                    "normalized_url": normalized_url,
                    "subreddit": extract_reddit_subreddit_from_url(normalized_url) or source_subreddit,
                    "published_at": published_at,
                    "collected_at": fetched_at_iso,
                }
            )
            source_candidate_count += 1

        source_summaries.append(
            {
                "source_name": source.source_name,
                "source_url": source.url,
                "source_type": source.type,
                "candidate_count": source_candidate_count,
            }
        )

    return {
        "batch_name": batch.batch_name,
        "batch_mode": batch.batch_mode,
        "enabled": batch.enabled,
        "max_urls": batch.max_urls,
        "recent_days": batch.recent_days,
        "include_title_keywords": batch.include_title_keywords,
        "exclude_title_keywords": batch.exclude_title_keywords,
        "exclude_url_keywords": batch.exclude_url_keywords,
        "allow_subreddits": batch.allow_subreddits,
        "deny_subreddits": batch.deny_subreddits,
        "parser_fallback_enabled": batch.parser_fallback_enabled,
        "generated_at": fetched_at_iso,
        "source_summaries": source_summaries,
        "source_errors": source_errors,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def fetch_rss_items(feed_url: str) -> list[dict[str, str]]:
    with urlopen(feed_url) as response:
        payload = response.read()

    root = ET.fromstring(payload)
    results: list[dict[str, str]] = []

    for element in root.iter():
        local_name = strip_namespace(element.tag)
        if local_name not in {"item", "entry"}:
            continue

        title = first_child_text(element, {"title"})
        url = extract_item_url(element, feed_url)
        published_at = extract_item_published_at(element)

        results.append(
            {
                "title": title,
                "url": url,
                "published_at": published_at,
            }
        )

    return results


def extract_item_url(element: ET.Element, feed_url: str) -> str:
    for child in element:
        child_name = strip_namespace(child.tag)
        if child_name != "link":
            continue

        href = child.attrib.get("href", "").strip()
        if href:
            return urljoin(feed_url, href)

        text = (child.text or "").strip()
        if text:
            return urljoin(feed_url, text)

    guid_text = first_child_text(element, {"guid", "id"})
    if guid_text:
        return urljoin(feed_url, guid_text)

    return ""


def extract_item_published_at(element: ET.Element) -> str:
    candidates = [
        first_child_text(element, {"published"}),
        first_child_text(element, {"updated"}),
        first_child_text(element, {"pubDate"}),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        parsed = parse_datetime(candidate)
        if parsed is not None:
            return iso_z(parsed)
    return ""


def parse_datetime(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None

    try:
        parsed = parsedate_to_datetime(text)
    except Exception:
        parsed = None

    if parsed is None:
        normalized = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def ensure_utc_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def strip_namespace(tag: object) -> str:
    value = str(tag)
    return value.rsplit("}", 1)[-1]


def first_child_text(element: ET.Element, names: set[str]) -> str:
    for child in element:
        if strip_namespace(child.tag) not in names:
            continue
        text = (child.text or "").strip()
        if text:
            return text
    return ""


def normalize_url(url: str) -> str:
    text = url.strip()
    if not text:
        return ""

    parts = urlsplit(text)
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    path = parts.path or ""

    if not netloc:
        return text

    if netloc.endswith("reddit.com") or netloc == "redd.it":
        netloc = normalize_reddit_netloc(netloc)
        path = normalize_reddit_path(path, netloc)
    else:
        path = path.rstrip("/")

    return urlunsplit((scheme, netloc, path, "", ""))


def normalize_reddit_netloc(netloc: str) -> str:
    if netloc.startswith("www."):
        return netloc[4:]
    if netloc.startswith("old."):
        return netloc[4:]
    if netloc.startswith("np."):
        return netloc[3:]
    if netloc.startswith("m."):
        return netloc[2:]
    if netloc == "redd.it":
        return "reddit.com"
    return netloc


def normalize_reddit_path(path: str, netloc: str) -> str:
    cleaned = path.rstrip("/")
    if netloc == "reddit.com" and cleaned.startswith("/comments/"):
        return cleaned
    if netloc == "reddit.com" and "/comments/" in cleaned:
        parts = [segment for segment in cleaned.split("/") if segment]
        if len(parts) >= 4 and parts[0] == "r" and parts[2] == "comments":
            slug = "/".join(parts[:5]) if len(parts) >= 5 else "/".join(parts[:4])
            return f"/{slug}"
    return cleaned or "/"


def extract_reddit_subreddit_from_url(url: str) -> str:
    parts = urlsplit(url)
    path_parts = [segment for segment in parts.path.split("/") if segment]
    if len(path_parts) >= 2 and path_parts[0] == "r":
        return path_parts[1].lower()
    return ""


def load_seen_urls(path: Path = DEFAULT_STATE_PATH) -> set[str]:
    if not path.exists():
        return set()

    payload = read_json_file(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Seen URL state must be a JSON object: {path}")

    urls = payload.get("seen_urls", [])
    if not isinstance(urls, list):
        raise ValueError(f"Seen URL state must contain a list named 'seen_urls': {path}")

    seen_urls: set[str] = set()
    for item in urls:
        normalized = normalize_url(str(item))
        if normalized:
            seen_urls.add(normalized)
    return seen_urls


def save_seen_urls(seen_urls: set[str], path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seen_urls": sorted(seen_urls),
        "updated_at": iso_z(datetime.now(timezone.utc)),
    }
    write_json_file(path, payload)


def write_candidate_payload(path: Path, payload: dict[str, Any]) -> None:
    write_json_file(path, payload)


def read_candidate_payload(path: Path) -> dict[str, Any]:
    payload = read_json_file(path)
    if not isinstance(payload, dict):
        raise ValueError(f"RSS candidate file must contain a JSON object: {path}")
    return payload


def candidate_path_for_batch(batch_name: str, candidate_dir: Path = DEFAULT_CANDIDATE_DIR) -> Path:
    return candidate_dir / f"rss_candidates_{batch_name}.json"


def url_list_path_for_batch(batch_name: str, url_list_dir: Path = DEFAULT_URL_LIST_DIR) -> Path:
    return url_list_dir / f"auto_{batch_name}.txt"


def batch_recent_cutoff(batch: AutoBatchDefinition, now: datetime | None = None) -> datetime:
    utc_now = ensure_utc_datetime(now)
    return utc_now - timedelta(days=batch.recent_days)


def merge_batch_candidates(
    batch: AutoBatchDefinition,
    payload: dict[str, Any],
    seen_urls: set[str],
    now: datetime | None = None,
) -> dict[str, Any]:
    raw_candidates = payload.get("candidates", [])
    if not isinstance(raw_candidates, list):
        raise ValueError(f"RSS candidate payload for {batch.batch_name} must include a list of candidates.")

    cutoff = batch_recent_cutoff(batch, now)
    unique_candidates: list[dict[str, Any]] = []
    batch_seen: set[str] = set()
    allow_subreddits = set(batch.allow_subreddits)
    deny_subreddits = set(batch.deny_subreddits)
    skipped_seen = 0
    skipped_old = 0
    skipped_invalid = 0
    skipped_title_filter = 0
    skipped_url_filter = 0
    skipped_subreddit_filter = 0

    for candidate in raw_candidates:
        if not isinstance(candidate, dict):
            skipped_invalid += 1
            continue

        raw_url = str(candidate.get("url", "")).strip()
        normalized_url = normalize_url(raw_url)
        if not raw_url or not normalized_url:
            skipped_invalid += 1
            continue

        if normalized_url in seen_urls or normalized_url in batch_seen:
            skipped_seen += 1
            continue

        title = str(candidate.get("title", "")).strip()
        subreddit = get_candidate_subreddit(candidate)
        if batch.include_title_keywords and not contains_any(title, batch.include_title_keywords):
            skipped_title_filter += 1
            continue
        if batch.exclude_title_keywords and contains_any(title, batch.exclude_title_keywords):
            skipped_title_filter += 1
            continue
        if batch.exclude_url_keywords and contains_any(normalized_url, batch.exclude_url_keywords):
            skipped_url_filter += 1
            continue
        if allow_subreddits and subreddit not in allow_subreddits:
            skipped_subreddit_filter += 1
            continue
        if deny_subreddits and subreddit in deny_subreddits:
            skipped_subreddit_filter += 1
            continue

        published_at = parse_datetime(str(candidate.get("published_at", "")))
        if published_at is None:
            published_at = ensure_utc_datetime(now)
        if published_at < cutoff:
            skipped_old += 1
            continue

        enriched = dict(candidate)
        enriched["normalized_url"] = normalized_url
        enriched["published_at"] = iso_z(published_at)
        unique_candidates.append(enriched)
        batch_seen.add(normalized_url)

    unique_candidates.sort(
        key=lambda item: parse_datetime(str(item.get("published_at", ""))) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    final_candidates = unique_candidates[: batch.max_urls]
    emitted_urls = [str(item["normalized_url"]) for item in final_candidates]

    for url in emitted_urls:
        seen_urls.add(url)

    return {
        "batch_name": batch.batch_name,
        "batch_mode": batch.batch_mode,
        "source_candidate_count": len(raw_candidates),
        "selected_count": len(final_candidates),
        "skipped_seen_count": skipped_seen,
        "skipped_old_count": skipped_old,
        "skipped_invalid_count": skipped_invalid,
        "skipped_title_filter_count": skipped_title_filter,
        "skipped_url_filter_count": skipped_url_filter,
        "skipped_subreddit_filter_count": skipped_subreddit_filter,
        "emitted_urls": emitted_urls,
        "selected_candidates": final_candidates,
        "output_path": url_list_path_for_batch(batch.batch_name),
    }


def write_url_list_from_candidates(output_path: Path, candidates: list[dict[str, Any]]) -> None:
    lines = [str(candidate["normalized_url"]).strip() for candidate in candidates if str(candidate.get("normalized_url", "")).strip()]
    write_text_file(output_path, "\n".join(lines) + ("\n" if lines else ""))


def contains_any(text: str, keywords: list[str]) -> bool:
    haystack = text.lower()
    return any(keyword in haystack for keyword in keywords)


def get_candidate_subreddit(candidate: dict[str, Any]) -> str:
    subreddit = str(candidate.get("subreddit", "")).strip().lower()
    if subreddit:
        return subreddit

    normalized_url = str(candidate.get("normalized_url", "")).strip()
    if normalized_url:
        derived = extract_reddit_subreddit_from_url(normalized_url)
        if derived:
            return derived

    source_feed_url = str(candidate.get("source_feed_url", "")).strip()
    if source_feed_url:
        return extract_reddit_subreddit_from_url(source_feed_url)

    return ""
