"""Tests for prod_ramp_runner_v2 timeout, retry, and job verification logic."""

import json
import time
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import importlib

# Ensure tools/ is importable
_tools_dir = str(Path(__file__).resolve().parent.parent.parent.parent / "tools")
if _tools_dir not in sys.path:
    sys.path.insert(0, _tools_dir)


@pytest.fixture(autouse=True, scope="session")
def _import_runner():
    """Ensure runner module is imported for tests."""
    import prod_ramp_runner_v2  # noqa: F401


def _get_runner():
    import prod_ramp_runner_v2 as runner
    return runner


class TestHttpPostJsonRetry:
    """Test http_post_json retry and backoff behavior."""

    @patch("urllib.request.urlopen")
    def test_successful_post(self, mock_urlopen):
        runner = _get_runner()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({"job_id": "j1"}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        status, data, diag = runner.http_post_json("http://test/api/jobs", {"topic": "t"})
        assert status == 200
        assert data["job_id"] == "j1"
        assert diag == {}

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_429_retries_with_longer_backoff(self, mock_urlopen, mock_sleep):
        """429 rate limit should trigger retry with longer backoff."""
        import urllib.error
        runner = _get_runner()

        # Build 429 errors
        def make_429():
            err = urllib.error.HTTPError(
                "http://test", 429, "Rate limited", {}, None
            )
            err.read = lambda: b"rate limited"
            err.headers = {}
            return err

        success_resp = MagicMock()
        success_resp.status = 200
        success_resp.read.return_value = json.dumps({"job_id": "j1"}).encode()
        success_resp.__enter__ = lambda s: s
        success_resp.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [make_429(), make_429(), success_resp]

        status, data, diag = runner.http_post_json("http://test/api/jobs", {"topic": "t"})
        assert status == 200
        assert data["job_id"] == "j1"
        assert mock_sleep.call_count == 2
        # First backoff should be >= 15s (rate-limit aware)
        first_backoff = mock_sleep.call_args_list[0][0][0]
        assert first_backoff >= 15, f"Rate-limit backoff {first_backoff} should be >= 15s"

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_timeout_retries(self, mock_urlopen, mock_sleep):
        """TimeoutError should trigger retry."""
        runner = _get_runner()

        success_resp = MagicMock()
        success_resp.status = 200
        success_resp.read.return_value = json.dumps({"job_id": "j1"}).encode()
        success_resp.__enter__ = lambda s: s
        success_resp.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [TimeoutError("timed out"), success_resp]

        status, data, diag = runner.http_post_json("http://test/api/jobs", {"topic": "t"})
        assert status == 200
        assert data["job_id"] == "j1"

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_all_retries_exhausted(self, mock_urlopen, mock_sleep):
        """When all retries fail, return error."""
        runner = _get_runner()

        mock_urlopen.side_effect = TimeoutError("timed out")

        status, data, diag = runner.http_post_json(
            "http://test/api/jobs", {"topic": "t"}, retries=3
        )
        assert status is None
        assert "error" in data
        assert mock_urlopen.call_count == 3

    @patch("urllib.request.urlopen")
    def test_default_timeout_is_120s(self, mock_urlopen):
        """Default HTTP timeout should be 120s, not 30s."""
        runner = _get_runner()

        success_resp = MagicMock()
        success_resp.status = 200
        success_resp.read.return_value = json.dumps({"job_id": "j1"}).encode()
        success_resp.__enter__ = lambda s: s
        success_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = success_resp

        runner.http_post_json("http://test/api/jobs", {"topic": "t"})
        # Check urlopen was called with timeout=120
        _, kwargs = mock_urlopen.call_args
        assert kwargs.get("timeout") == 120


class TestVerifyJobSubmitted:
    """Test the verify_job_submitted fallback mechanism."""

    @patch("time.sleep")
    def test_finds_job_by_topic(self, mock_sleep):
        runner = _get_runner()
        original_base = runner.BASE_URL
        runner.BASE_URL = "http://test:8103"

        with patch.object(runner, "http_get_json") as mock_get:
            mock_get.return_value = (200, {
                "jobs": [
                    {"job_id": "j-abc", "topic": "Test Topic", "status": "completed"},
                    {"job_id": "j-other", "topic": "Other", "status": "running"},
                ]
            })

            job_id, data = runner.verify_job_submitted("Test Topic", timeout=5)
            assert job_id == "j-abc"
            assert data["topic"] == "Test Topic"

        runner.BASE_URL = original_base

    @patch("time.sleep")
    def test_returns_none_when_not_found(self, mock_sleep):
        runner = _get_runner()
        original_base = runner.BASE_URL
        runner.BASE_URL = "http://test:8103"

        with patch.object(runner, "http_get_json") as mock_get:
            mock_get.return_value = (200, {
                "jobs": [
                    {"job_id": "j-other", "topic": "Other Topic", "status": "running"},
                ]
            })

            job_id, data = runner.verify_job_submitted("Missing Topic", timeout=1)
            assert job_id is None
            assert data is None

        runner.BASE_URL = original_base


class TestExecuteSingleJobTimeoutRecovery:
    """Test that execute_single_job recovers from submission timeout."""

    @patch("time.sleep")
    def test_recovers_from_submission_timeout(self, mock_sleep):
        """When HTTP submission times out but job exists server-side, recover."""
        runner = _get_runner()
        original_base = runner.BASE_URL
        original_root = runner.SERVER_ROOT
        runner.BASE_URL = "http://test:8103"
        runner.SERVER_ROOT = None

        with patch.object(runner, "http_post_json") as mock_post, \
             patch.object(runner, "verify_job_submitted") as mock_verify, \
             patch.object(runner, "http_get_json") as mock_get:

            # Submission "fails" with timeout
            mock_post.return_value = (None, {"error": "timed out"}, {
                "exception_type": "TimeoutError",
                "exception_message": "timed out",
                "traceback": "",
                "url": "http://test:8103/api/jobs",
                "attempt": 5
            })

            # But job is found server-side
            mock_verify.return_value = ("j-recovered", {
                "job_id": "j-recovered", "topic": "Test", "status": "completed"
            })

            # Polling returns completed
            mock_get.return_value = (200, {
                "job_id": "j-recovered",
                "status": "completed",
                "output_path": None
            })

            result = runner.execute_single_job({
                "job_index": 1,
                "workflow_id": "blog_workflow",
                "topic": "Test Topic",
                "output_path": "/tmp/test"
            })

            assert result["job_id"] == "j-recovered"
            assert result["status"] == "completed"
            mock_verify.assert_called_once()

        runner.BASE_URL = original_base
        runner.SERVER_ROOT = original_root

    @patch("time.sleep")
    def test_confirms_failure_when_not_found_server_side(self, mock_sleep):
        """When HTTP submission fails and job not found server-side, mark failed."""
        runner = _get_runner()
        original_base = runner.BASE_URL
        original_root = runner.SERVER_ROOT
        runner.BASE_URL = "http://test:8103"
        runner.SERVER_ROOT = None

        with patch.object(runner, "http_post_json") as mock_post, \
             patch.object(runner, "verify_job_submitted") as mock_verify:

            mock_post.return_value = (None, {"error": "connection refused"}, {})
            mock_verify.return_value = (None, None)

            result = runner.execute_single_job({
                "job_index": 1,
                "workflow_id": "blog_workflow",
                "topic": "Test Topic",
                "output_path": "/tmp/test"
            })

            assert result["status"] == "submission_failed"

        runner.BASE_URL = original_base
        runner.SERVER_ROOT = original_root
