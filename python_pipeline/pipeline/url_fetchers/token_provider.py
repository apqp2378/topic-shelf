from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol


DEFAULT_REDDIT_OAUTH_TOKEN_ENV_VAR = "TOPIC_SHELF_REDDIT_OAUTH_TOKEN"


class TokenProvider(Protocol):
    """Minimal token-loading abstraction for future OAuth fetchers.

    The current implementation only reads a token from environment variables.
    Later implementations can add caching or refresh logic without changing the
    fetcher surface area.
    """

    def get_token(self) -> str:
        """Return a non-empty bearer token."""


@dataclass(frozen=True)
class EnvTokenProvider:
    """Load a token from a single environment variable."""

    env_var: str = DEFAULT_REDDIT_OAUTH_TOKEN_ENV_VAR

    def get_token(self) -> str:
        token = os.environ.get(self.env_var, "").strip()
        if not token:
            raise RuntimeError(
                f"Missing OAuth token. Set the {self.env_var} environment variable."
            )
        return token


@dataclass(frozen=True)
class StaticTokenProvider:
    """Test helper that returns a fixed token string."""

    token: str

    def get_token(self) -> str:
        token = self.token.strip()
        if not token:
            raise ValueError("StaticTokenProvider requires a non-empty token.")
        return token
