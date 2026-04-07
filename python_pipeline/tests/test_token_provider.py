from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = PROJECT_ROOT / "python_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from pipeline.url_fetchers.token_provider import EnvTokenProvider, StaticTokenProvider


class TokenProviderTests(unittest.TestCase):
    def test_env_token_provider_reads_token_from_env(self) -> None:
        with mock.patch.dict(os.environ, {"TOPIC_SHELF_REDDIT_OAUTH_TOKEN": "  secret-token  "}, clear=True):
            provider = EnvTokenProvider()

            self.assertEqual(provider.get_token(), "secret-token")

    def test_env_token_provider_missing_token_raises_clear_error(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            provider = EnvTokenProvider()

            with self.assertRaisesRegex(
                RuntimeError,
                r"Missing OAuth token\. Set the TOPIC_SHELF_REDDIT_OAUTH_TOKEN environment variable\.",
            ):
                provider.get_token()

    def test_static_token_provider_returns_token_for_tests(self) -> None:
        provider = StaticTokenProvider(token="  test-token  ")

        self.assertEqual(provider.get_token(), "test-token")

    def test_static_token_provider_rejects_blank_token(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            r"StaticTokenProvider requires a non-empty token\.",
        ):
            StaticTokenProvider(token="   ").get_token()


if __name__ == "__main__":
    unittest.main()
