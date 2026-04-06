from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

from pipeline.io_utils import build_raw_from_urls_output_path, read_text_file, write_json_file
from pipeline.url_fetchers.comment_expander import clean_string, coerce_int, normalize_comment_nodes
from pipeline.url_fetchers.base import TOP_COMMENT_LIMIT, UrlFetchResult, UrlFetcher
from pipeline.validators import validate_raw_record


@dataclass(frozen=True)
class UrlIngestionFailure:
    input_url: str
    canonical_url: str
    reason: str


@dataclass(frozen=True)
class UrlIngestionSuccess:
    input_url: str
    canonical_url: str
    raw_id: str
    post_id: str


@dataclass(frozen=True)
class UrlIngestionResult:
    input_count: int
    unique_count: int
    success_count: int
    failure_count: int
    output_path: Path
    records: list[dict[str, object]]
    successes: list[UrlIngestionSuccess]
    failures: list[UrlIngestionFailure]


def ingest_url_list(
    url_list_path: Path,
    fetcher: UrlFetcher,
    output_path: Path | None = None,
    collected_at: datetime | None = None,
) -> UrlIngestionResult:
    raw_urls = read_url_list(url_list_path)
    utc_now = ensure_utc_datetime(collected_at)
    target_path = output_path or build_raw_from_urls_output_path(url_list_path)

    records: list[dict[str, object]] = []
    successes: list[UrlIngestionSuccess] = []
    failures: list[UrlIngestionFailure] = []
    canonical_urls = prepare_canonical_urls(raw_urls, failures)

    for input_url, canonical_url in canonical_urls:
        try:
            fetch_result = fetcher.fetch_thread(canonical_url)
            record = build_raw_record(input_url, fetch_result, len(records) + 1, utc_now)
            validation_issues = validate_raw_record(len(records), record)
            if validation_issues:
                first_issue = validation_issues[0]
                raise ValueError(first_issue.message)
        except Exception as exc:
            failures.append(
                UrlIngestionFailure(
                    input_url=input_url,
                    canonical_url=canonical_url,
                    reason=str(exc),
                )
            )
            continue

        records.append(record)
        successes.append(
            UrlIngestionSuccess(
                input_url=input_url,
                canonical_url=canonical_url,
                raw_id=record["raw_id"],
                post_id=record["post_id"],
            )
        )

    write_json_file(target_path, records)

    return UrlIngestionResult(
        input_count=len(raw_urls),
        unique_count=len(canonical_urls),
        success_count=len(successes),
        failure_count=len(failures),
        output_path=target_path,
        records=records,
        successes=successes,
        failures=failures,
    )


def prepare_canonical_urls(
    urls: Iterable[str],
    failures: list[UrlIngestionFailure],
) -> list[tuple[str, str]]:
    seen: set[str] = set()
    canonical_urls: list[tuple[str, str]] = []

    for url in urls:
        try:
            canonical_url = canonicalize_reddit_thread_url(url)
        except ValueError as exc:
            failures.append(
                UrlIngestionFailure(
                    input_url=url,
                    canonical_url="",
                    reason=str(exc),
                )
            )
            continue

        dedupe_key = build_reddit_post_dedupe_key(canonical_url)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        canonical_urls.append((url, canonical_url))

    return canonical_urls


def read_url_list(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"URL list file not found: {path}")

    lines = read_text_file(path).splitlines()
    urls: list[str] = []

    for raw_line in lines:
        cleaned_line = raw_line.strip()
        if not cleaned_line:
            continue
        if cleaned_line.startswith("#"):
            continue
        urls.append(cleaned_line)

    return urls


def canonicalize_and_dedupe_urls(urls: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    canonical_urls: list[str] = []

    for url in urls:
        canonical_url = canonicalize_reddit_thread_url(url)
        dedupe_key = build_reddit_post_dedupe_key(canonical_url)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        canonical_urls.append(canonical_url)

    return canonical_urls


def canonicalize_reddit_thread_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    path = parts.path or ""

    if not netloc:
        raise ValueError(f"URL is missing host: {url}")

    if netloc in ("www.reddit.com", "old.reddit.com", "np.reddit.com", "m.reddit.com"):
        netloc = "reddit.com"
    elif netloc == "redd.it":
        netloc = "reddit.com"
        path = normalize_reddit_shortlink_path(path)
    elif netloc != "reddit.com":
        raise ValueError(f"Unsupported host for Reddit ingestion: {netloc}")

    normalized_path = normalize_reddit_path(path)
    return urlunsplit((scheme, netloc, normalized_path, "", ""))


def normalize_reddit_shortlink_path(path: str) -> str:
    short_id = path.strip().strip("/")
    if not short_id:
        raise ValueError("Reddit shortlink is missing a post id.")
    return f"/comments/{short_id}"


def normalize_reddit_path(path: str) -> str:
    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        raise ValueError("Reddit URL path is empty.")

    if len(segments) >= 4 and segments[0] == "r" and segments[2] == "comments":
        post_id = segments[3].strip()
        if not post_id:
            raise ValueError("Reddit thread URL is missing a post id.")
        if len(segments) >= 5 and segments[4].strip():
            return f"/r/{segments[1]}/comments/{post_id}/{segments[4].strip()}"
        return f"/r/{segments[1]}/comments/{post_id}"

    if len(segments) >= 2 and segments[0] == "comments":
        post_id = segments[1].strip()
        if not post_id:
            raise ValueError("Reddit comments URL is missing a post id.")
        if len(segments) >= 3 and segments[2].strip():
            return f"/comments/{post_id}/{segments[2].strip()}"
        return f"/comments/{post_id}"

    raise ValueError("URL does not look like a Reddit thread URL.")


def extract_post_id_from_url(canonical_url: str) -> str:
    parts = urlsplit(canonical_url)
    segments = [segment for segment in parts.path.split("/") if segment]

    if len(segments) >= 4 and segments[0] == "r" and segments[2] == "comments":
        post_id = segments[3].strip()
        if post_id:
            return f"t3_{post_id}"

    if len(segments) >= 2 and segments[0] == "comments":
        post_id = segments[1].strip()
        if post_id:
            return f"t3_{post_id}"

    return ""


def build_reddit_post_dedupe_key(canonical_url: str) -> str:
    post_id = extract_post_id_from_url(canonical_url)
    if post_id:
        return post_id
    return canonical_url


def build_raw_record(
    input_url: str,
    fetch_result: UrlFetchResult,
    success_index: int,
    collected_at: datetime,
) -> dict[str, object]:
    canonical_post_id = extract_post_id_from_url(fetch_result.canonical_url)
    if not canonical_post_id:
        raise ValueError("Could not parse Reddit post id from canonical URL.")

    if fetch_result.post_id and fetch_result.post_id != canonical_post_id:
        raise ValueError("Fetched Reddit post id does not match canonical URL post id.")

    if not fetch_result.subreddit:
        raise ValueError("Missing subreddit.")
    if not fetch_result.post_title:
        raise ValueError("Missing post_title.")
    if not fetch_result.post_url:
        raise ValueError("Missing post_url.")

    timestamp_tag = collected_at.strftime("%Y%m%d")
    collected_at_iso = format_utc_iso(collected_at)
    post_body = fetch_result.post_body

    return {
        "raw_id": f"reddit_url_ingest_{timestamp_tag}_{success_index:03d}",
        "source": "reddit_url_ingest",
        "subreddit": fetch_result.subreddit,
        "post_title": fetch_result.post_title,
        "post_url": input_url,
        "post_author": fetch_result.post_author or "[deleted]",
        "post_created_utc": int(fetch_result.post_created_utc),
        "post_body": post_body,
        "num_comments": int(fetch_result.num_comments),
        "upvotes": int(fetch_result.upvotes),
        "top_comments": normalize_top_comments(fetch_result.top_comments),
        "devvit_score": 0,
        "devvit_reason_tags": ["url_seeded_ingestion"],
        "moderator_status": "keep",
        "review_note": "",
        "collected_at": collected_at_iso,
        "recommended_status": "keep",
        "candidate_rank": success_index,
        "post_id": canonical_post_id,
        "candidate_id": canonical_post_id,
        "body_excerpt": build_body_excerpt(post_body),
        "devvit_version": "url-ingest-v1",
        **build_additive_fetch_metadata(fetch_result),
    }


def normalize_top_comments(top_comments: list[dict[str, object]]) -> list[dict[str, object]]:
    return normalize_comment_nodes(top_comments, limit=TOP_COMMENT_LIMIT)


def build_additive_fetch_metadata(fetch_result: UrlFetchResult) -> dict[str, object]:
    metadata = fetch_result.fetch_metadata or {}

    fetch_mode = clean_string(metadata.get("fetch_mode")) if isinstance(metadata, dict) else ""
    if not fetch_mode:
        fetch_mode = "public"

    comment_fetch_count = coerce_int(metadata.get("comment_fetch_count")) if isinstance(metadata, dict) else 0
    if comment_fetch_count <= 0:
        comment_fetch_count = len(fetch_result.top_comments)

    comment_fetch_depth = coerce_int(metadata.get("comment_fetch_depth")) if isinstance(metadata, dict) else 0
    ratelimit_snapshot = metadata.get("ratelimit_snapshot") if isinstance(metadata, dict) else {}
    if not isinstance(ratelimit_snapshot, dict):
        ratelimit_snapshot = {}

    extra_metadata: dict[str, object] = {
        "fetch_mode": fetch_mode,
        "comment_fetch_count": comment_fetch_count,
        "comment_fetch_depth": comment_fetch_depth,
        "ratelimit_snapshot": ratelimit_snapshot,
    }

    expandable_comment_ids = metadata.get("expandable_comment_ids") if isinstance(metadata, dict) else []
    if isinstance(expandable_comment_ids, list):
        extra_metadata["expandable_comment_ids"] = [clean_string(value) for value in expandable_comment_ids if clean_string(value)]

    deleted_checked_at = metadata.get("deleted_checked_at") if isinstance(metadata, dict) else ""
    if isinstance(deleted_checked_at, str) and deleted_checked_at.strip():
        extra_metadata["deleted_checked_at"] = deleted_checked_at.strip()

    return extra_metadata


def build_body_excerpt(post_body: str, max_len: int = 280) -> str:
    flattened = " ".join(post_body.split())
    if not flattened:
        return ""
    if len(flattened) <= max_len:
        return flattened
    return flattened[:max_len].rstrip()


def ensure_utc_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_utc_iso(value: datetime) -> str:
    utc_value = ensure_utc_datetime(value)
    return utc_value.replace(microsecond=0).isoformat().replace("+00:00", "Z")
