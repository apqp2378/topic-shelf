from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_ROOT = SCRIPT_DIR.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ingest_reddit_urls import resolve_fetcher_name as resolve_ingest_fetcher_name
from pipeline.io_utils import build_raw_from_urls_output_path
from pipeline.url_fetchers import build_url_fetcher, list_url_fetchers
from pipeline.url_fetchers.config import RedditFetcherConfig
from pipeline.url_fetchers.token_provider import EnvTokenProvider, DEFAULT_REDDIT_OAUTH_TOKEN_ENV_VAR


@dataclass(frozen=True)
class DoctorReport:
    selected_fetcher: str
    status: str
    warnings: list[str]
    errors: list[str]
    token_present: bool | None
    url_list_path: Path | None
    output_path: Path | None
    config: RedditFetcherConfig | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Reddit URL-ingestion setup without fetching any data."
    )
    parser.add_argument(
        "--fetcher",
        type=str,
        help=f"URL fetcher to validate. Supported values: {', '.join(list_url_fetchers())}.",
    )
    parser.add_argument(
        "--url-list",
        type=Path,
        help="Optional path to a Reddit thread URL list to validate.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        help="Optional explicit output path to validate or create the parent for.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print extra setup details.",
    )
    return parser.parse_args()


def resolve_fetcher_name(fetcher_name: str | None) -> str:
    return resolve_ingest_fetcher_name(fetcher_name)


def inspect_setup(
    fetcher_name: str | None = None,
    url_list_path: Path | None = None,
    output_path: Path | None = None,
) -> DoctorReport:
    warnings: list[str] = []
    errors: list[str] = []
    config: RedditFetcherConfig | None = None
    token_present: bool | None = None
    selected_fetcher_name = resolve_fetcher_name(fetcher_name)

    try:
        config = getattr(build_url_fetcher(selected_fetcher_name), "config", None)
    except Exception as exc:
        errors.append(str(exc))

    if selected_fetcher_name == "reddit_oauth":
        try:
            EnvTokenProvider().get_token()
            token_present = True
        except Exception as exc:
            token_present = False
            errors.append(str(exc))

    checked_output_path = output_path
    if url_list_path is not None:
        if not url_list_path.exists():
            errors.append(f"URL list file not found: {url_list_path}")
        else:
            if checked_output_path is None:
                checked_output_path = build_raw_from_urls_output_path(url_list_path)
            try:
                checked_output_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                errors.append(f"Could not prepare output directory {checked_output_path.parent}: {exc}")
    else:
        warnings.append("No --url-list provided; input readiness was not checked.")

    status = "ERROR" if errors else "WARN" if warnings else "OK"
    return DoctorReport(
        selected_fetcher=selected_fetcher_name,
        status=status,
        warnings=warnings,
        errors=errors,
        token_present=token_present,
        url_list_path=url_list_path,
        output_path=checked_output_path,
        config=config,
    )


def format_report(report: DoctorReport) -> str:
    lines = [
        "Reddit ingestion preflight",
        f"Overall status: {report.status}",
        f"Selected fetcher: {report.selected_fetcher}",
    ]

    if report.token_present is True:
        lines.append("OAuth token: present")
    elif report.token_present is False:
        lines.append(f"OAuth token: missing ({DEFAULT_REDDIT_OAUTH_TOKEN_ENV_VAR})")
    else:
        lines.append("OAuth token: not required")

    if report.config is not None:
        lines.extend(
            [
                f"Request timeout (seconds): {report.config.request_timeout_seconds}",
                f"Retry policy: max_attempts={report.config.max_retry_attempts}, backoff_seconds={report.config.retry_backoff_seconds}",
                f"Top comment cap: {report.config.top_comment_limit}",
                f"MoreComments enabled: {report.config.morechildren_enabled}",
                f"MoreComments child limit: {report.config.morechildren_max_child_ids}",
                f"MoreComments batch limit: {report.config.morechildren_max_batches}",
            ]
        )

    if report.url_list_path is not None:
        lines.append(f"URL list: {report.url_list_path}")
    else:
        lines.append("URL list: not provided")

    if report.output_path is not None:
        lines.append(f"Output path: {report.output_path}")
    else:
        lines.append("Output path: not provided")

    if report.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in report.warnings)

    if report.errors:
        lines.append("Blocking errors:")
        lines.extend(f"- {error}" for error in report.errors)

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    report = inspect_setup(
        fetcher_name=getattr(args, "fetcher", None),
        url_list_path=getattr(args, "url_list", None),
        output_path=getattr(args, "output_path", None),
    )
    print(format_report(report))
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
