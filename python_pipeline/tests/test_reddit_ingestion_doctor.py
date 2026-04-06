from __future__ import annotations

import importlib.util
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = PROJECT_ROOT / "python_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))


@contextmanager
def make_temp_root() -> Path:
    temp_dir = PIPELINE_ROOT / "data" / "test_tmp" / "doctor"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield temp_dir
    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


class RedditIngestionDoctorTests(unittest.TestCase):
    def test_default_fetcher_resolution(self) -> None:
        doctor = load_doctor_module()

        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(doctor.resolve_fetcher_name(None), "reddit_public")

    def test_explicit_fetcher_resolution(self) -> None:
        doctor = load_doctor_module()

        with mock.patch.dict("os.environ", {"TOPIC_SHELF_FETCHER": "reddit_oauth"}, clear=False):
            self.assertEqual(doctor.resolve_fetcher_name("reddit_public"), "reddit_public")
            self.assertEqual(doctor.resolve_fetcher_name(" reddit_oauth "), "reddit_oauth")

    def test_oauth_token_missing_is_blocking_error(self) -> None:
        doctor = load_doctor_module()

        with make_temp_root() as root:
            url_list = root / "data" / "url_lists" / "doctor.txt"
            url_list.parent.mkdir(parents=True, exist_ok=True)
            url_list.write_text("https://reddit.com/r/python/comments/abc123/example-thread/\n", encoding="utf-8")

            with mock.patch.dict("os.environ", {}, clear=True):
                report = doctor.inspect_setup("reddit_oauth", url_list_path=url_list)

        self.assertEqual(report.status, "ERROR")
        self.assertFalse(report.token_present)
        self.assertTrue(any("Missing OAuth token" in error for error in report.errors))

    def test_invalid_config_is_blocking_error(self) -> None:
        doctor = load_doctor_module()

        with make_temp_root() as root:
            url_list = root / "data" / "url_lists" / "doctor.txt"
            url_list.parent.mkdir(parents=True, exist_ok=True)
            url_list.write_text("https://reddit.com/r/python/comments/abc123/example-thread/\n", encoding="utf-8")

            with mock.patch.dict(
                "os.environ",
                {"TOPIC_SHELF_REDDIT_TOP_COMMENT_LIMIT": "0"},
                clear=False,
            ):
                report = doctor.inspect_setup("reddit_public", url_list_path=url_list)

        self.assertEqual(report.status, "ERROR")
        self.assertTrue(any("TOPIC_SHELF_REDDIT_TOP_COMMENT_LIMIT" in error for error in report.errors))

    def test_missing_url_list_path_is_blocking_error(self) -> None:
        doctor = load_doctor_module()

        missing_path = PROJECT_ROOT / "python_pipeline" / "data" / "url_lists" / "does_not_exist.txt"
        with mock.patch.dict("os.environ", {}, clear=True):
            report = doctor.inspect_setup("reddit_public", url_list_path=missing_path)

        self.assertEqual(report.status, "ERROR")
        self.assertTrue(any("URL list file not found" in error for error in report.errors))

    def test_healthy_public_setup_is_ok(self) -> None:
        doctor = load_doctor_module()

        with make_temp_root() as root:
            url_list = root / "data" / "url_lists" / "public.txt"
            output_path = root / "data" / "raw" / "raw_from_urls_public.json"
            url_list.parent.mkdir(parents=True, exist_ok=True)
            url_list.write_text("https://reddit.com/r/python/comments/abc123/example-thread/\n", encoding="utf-8")

            with mock.patch.dict("os.environ", {}, clear=True):
                report = doctor.inspect_setup("reddit_public", url_list_path=url_list, output_path=output_path)

            self.assertEqual(report.status, "OK")
            self.assertIsNone(report.token_present)
            self.assertTrue(report.output_path is not None and report.output_path.parent.exists())

    def test_healthy_oauth_setup_with_token_is_ok(self) -> None:
        doctor = load_doctor_module()

        with make_temp_root() as root:
            url_list = root / "data" / "url_lists" / "oauth.txt"
            url_list.parent.mkdir(parents=True, exist_ok=True)
            url_list.write_text("https://reddit.com/r/python/comments/abc123/example-thread/\n", encoding="utf-8")

            with mock.patch.dict("os.environ", {"TOPIC_SHELF_REDDIT_OAUTH_TOKEN": "token"}, clear=False):
                report = doctor.inspect_setup("reddit_oauth", url_list_path=url_list)

        self.assertEqual(report.status, "OK")
        self.assertTrue(report.token_present)
        self.assertEqual(report.selected_fetcher, "reddit_oauth")
        self.assertIn("MoreComments enabled", doctor.format_report(report))

    def test_no_live_network_calls_are_made(self) -> None:
        doctor = load_doctor_module()

        with make_temp_root() as root:
            url_list = root / "data" / "url_lists" / "public.txt"
            url_list.parent.mkdir(parents=True, exist_ok=True)
            url_list.write_text("https://reddit.com/r/python/comments/abc123/example-thread/\n", encoding="utf-8")

            with mock.patch("pipeline.url_fetchers.reddit_public.urlopen") as public_urlopen_mock:
                with mock.patch("pipeline.url_fetchers.reddit_oauth.urlopen") as oauth_urlopen_mock:
                    report = doctor.inspect_setup("reddit_public", url_list_path=url_list)

        self.assertEqual(report.status, "OK")
        self.assertEqual(public_urlopen_mock.call_count, 0)
        self.assertEqual(oauth_urlopen_mock.call_count, 0)


def load_doctor_module():
    path = PROJECT_ROOT / "python_pipeline" / "scripts" / "check_reddit_ingestion_setup.py"
    spec = importlib.util.spec_from_file_location("check_reddit_ingestion_setup_test_module", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()
