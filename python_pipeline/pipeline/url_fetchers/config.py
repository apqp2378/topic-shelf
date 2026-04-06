from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from pipeline.url_fetchers.base import TOP_COMMENT_LIMIT

DEFAULT_REQUEST_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 0.25
DEFAULT_MORECOMMENTS_ENABLED = True
DEFAULT_MORECOMMENTS_MAX_CHILD_IDS = 5
DEFAULT_MORECOMMENTS_MAX_BATCHES = 1

TOPIC_SHELF_REDDIT_REQUEST_TIMEOUT_SECONDS_ENV = "TOPIC_SHELF_REDDIT_REQUEST_TIMEOUT_SECONDS"
TOPIC_SHELF_REDDIT_MAX_RETRY_ATTEMPTS_ENV = "TOPIC_SHELF_REDDIT_MAX_RETRY_ATTEMPTS"
TOPIC_SHELF_REDDIT_RETRY_BACKOFF_SECONDS_ENV = "TOPIC_SHELF_REDDIT_RETRY_BACKOFF_SECONDS"
TOPIC_SHELF_REDDIT_TOP_COMMENT_LIMIT_ENV = "TOPIC_SHELF_REDDIT_TOP_COMMENT_LIMIT"
TOPIC_SHELF_REDDIT_MORECOMMENTS_ENABLED_ENV = "TOPIC_SHELF_REDDIT_MORECOMMENTS_ENABLED"
TOPIC_SHELF_REDDIT_MORECOMMENTS_MAX_CHILD_IDS_ENV = "TOPIC_SHELF_REDDIT_MORECOMMENTS_MAX_CHILD_IDS"
TOPIC_SHELF_REDDIT_MORECOMMENTS_MAX_BATCHES_ENV = "TOPIC_SHELF_REDDIT_MORECOMMENTS_MAX_BATCHES"


@dataclass(frozen=True)
class RedditFetcherConfig:
    """Runtime settings for Reddit URL ingestion fetchers."""

    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS
    max_retry_attempts: int = DEFAULT_MAX_RETRY_ATTEMPTS
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS
    top_comment_limit: int = TOP_COMMENT_LIMIT
    morechildren_enabled: bool = DEFAULT_MORECOMMENTS_ENABLED
    morechildren_max_child_ids: int = DEFAULT_MORECOMMENTS_MAX_CHILD_IDS
    morechildren_max_batches: int = DEFAULT_MORECOMMENTS_MAX_BATCHES

    @property
    def retry_policy(self) -> dict[str, object]:
        return {
            "max_attempts": self.max_retry_attempts,
            "backoff_seconds": self.retry_backoff_seconds,
        }


def load_reddit_fetcher_config(env: Mapping[str, str] | None = None) -> RedditFetcherConfig:
    """Load runtime fetcher settings from environment variables."""

    source = os.environ if env is None else env
    return RedditFetcherConfig(
        request_timeout_seconds=parse_float_env(
            source,
            TOPIC_SHELF_REDDIT_REQUEST_TIMEOUT_SECONDS_ENV,
            default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
            minimum=0.001,
        ),
        max_retry_attempts=parse_int_env(
            source,
            TOPIC_SHELF_REDDIT_MAX_RETRY_ATTEMPTS_ENV,
            default=DEFAULT_MAX_RETRY_ATTEMPTS,
            minimum=1,
        ),
        retry_backoff_seconds=parse_float_env(
            source,
            TOPIC_SHELF_REDDIT_RETRY_BACKOFF_SECONDS_ENV,
            default=DEFAULT_RETRY_BACKOFF_SECONDS,
            minimum=0.0,
        ),
        top_comment_limit=parse_int_env(
            source,
            TOPIC_SHELF_REDDIT_TOP_COMMENT_LIMIT_ENV,
            default=TOP_COMMENT_LIMIT,
            minimum=1,
        ),
        morechildren_enabled=parse_bool_env(
            source,
            TOPIC_SHELF_REDDIT_MORECOMMENTS_ENABLED_ENV,
            default=DEFAULT_MORECOMMENTS_ENABLED,
        ),
        morechildren_max_child_ids=parse_int_env(
            source,
            TOPIC_SHELF_REDDIT_MORECOMMENTS_MAX_CHILD_IDS_ENV,
            default=DEFAULT_MORECOMMENTS_MAX_CHILD_IDS,
            minimum=1,
        ),
        morechildren_max_batches=parse_int_env(
            source,
            TOPIC_SHELF_REDDIT_MORECOMMENTS_MAX_BATCHES_ENV,
            default=DEFAULT_MORECOMMENTS_MAX_BATCHES,
            minimum=1,
        ),
    )


def parse_bool_env(
    env: Mapping[str, str],
    key: str,
    default: bool,
) -> bool:
    value = env.get(key, "").strip()
    if not value:
        return default

    normalized = value.lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(
        f"Invalid boolean value for {key}: {value!r}. Use true/false, yes/no, on/off, or 1/0."
    )


def parse_int_env(
    env: Mapping[str, str],
    key: str,
    default: int,
    minimum: int,
) -> int:
    value = env.get(key, "").strip()
    if not value:
        return default

    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value for {key}: {value!r}.") from exc

    if parsed < minimum:
        raise ValueError(f"{key} must be at least {minimum}. Got {parsed}.")

    return parsed


def parse_float_env(
    env: Mapping[str, str],
    key: str,
    default: float,
    minimum: float,
) -> float:
    value = env.get(key, "").strip()
    if not value:
        return default

    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid number value for {key}: {value!r}.") from exc

    if parsed < minimum:
        raise ValueError(f"{key} must be at least {minimum}. Got {parsed}.")

    return parsed
