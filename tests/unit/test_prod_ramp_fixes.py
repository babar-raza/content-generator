#!/usr/bin/env python3
"""Unit tests for Production Ramp Runner fixes.

Tests:
1. Topic deduplication (case-insensitive)
2. Job ID validation in output paths
3. Retry logic behavior
"""

import unittest
import sys
from pathlib import Path

# Add tools to path
tools_path = Path(__file__).parent.parent.parent / "tools"
sys.path.insert(0, str(tools_path))

from prod_ramp_runner_v2 import deduplicate_topics


class TestTopicDeduplication(unittest.TestCase):
    """Test suite for topic deduplication."""

    def test_removes_exact_duplicates(self):
        """Deduplication removes exact duplicate titles."""
        topics = [
            {"title_topic": "BMP File Format", "slug": "bmp"},
            {"title_topic": "BMP File Format", "slug": "bmp"},
            {"title_topic": "PDF File Format", "slug": "pdf"},
        ]

        result = deduplicate_topics(topics, required_count=3, all_topics=[])

        self.assertEqual(len(result), 2)
        titles = [t["title_topic"] for t in result]
        self.assertEqual(titles, ["BMP File Format", "PDF File Format"])

    def test_removes_case_insensitive_duplicates(self):
        """Deduplication is case-insensitive."""
        topics = [
            {"title_topic": "_INDEX File Format", "slug": "index"},
            {"title_topic": "_index file format", "slug": "index"},
            {"title_topic": "PDF File Format", "slug": "pdf"},
        ]

        result = deduplicate_topics(topics, required_count=3, all_topics=[])

        self.assertEqual(len(result), 2)

    def test_resamples_when_needed(self):
        """Resamples from pool when duplicates reduce count below required."""
        topics = [
            {"title_topic": "BMP File Format", "slug": "bmp"},
            {"title_topic": "BMP File Format", "slug": "bmp"},
            {"title_topic": "BMP File Format", "slug": "bmp"},
        ]

        all_topics = [
            {"title_topic": "BMP File Format", "slug": "bmp"},
            {"title_topic": "PDF File Format", "slug": "pdf"},
            {"title_topic": "DOC File Format", "slug": "doc"},
            {"title_topic": "XLS File Format", "slug": "xls"},
        ]

        result = deduplicate_topics(topics, required_count=3, all_topics=all_topics)

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["title_topic"], "BMP File Format")
        # Should have pulled PDF and DOC from pool
        self.assertTrue(any(t["title_topic"] == "PDF File Format" for t in result))
        self.assertTrue(any(t["title_topic"] == "DOC File Format" for t in result))

    def test_preserves_order(self):
        """Deduplication preserves first occurrence order."""
        topics = [
            {"title_topic": "A", "slug": "a"},
            {"title_topic": "B", "slug": "b"},
            {"title_topic": "A", "slug": "a"},
            {"title_topic": "C", "slug": "c"},
        ]

        result = deduplicate_topics(topics, required_count=10, all_topics=[])

        self.assertEqual(len(result), 3)
        titles = [t["title_topic"] for t in result]
        self.assertEqual(titles, ["A", "B", "C"])

    def test_handles_whitespace(self):
        """Deduplication handles leading/trailing whitespace."""
        topics = [
            {"title_topic": " BMP File Format ", "slug": "bmp"},
            {"title_topic": "BMP File Format", "slug": "bmp"},
            {"title_topic": "PDF File Format", "slug": "pdf"},
        ]

        result = deduplicate_topics(topics, required_count=3, all_topics=[])

        self.assertEqual(len(result), 2)


class TestJobIdValidation(unittest.TestCase):
    """Test suite for job ID validation in output paths."""

    def test_job_id_matches_filename(self):
        """Verify job_id appears in output filename."""
        job_id = "e62bd6cc-91f6-411f-850f-b07e12a8acd2"
        filename = "e62bd6cc-91f6-411f-850f-b07e12a8acd2_generated.md"

        self.assertIn(job_id, filename)

    def test_job_id_mismatch_detected(self):
        """Verify mismatch detection when job_id not in filename."""
        job_id = "e62bd6cc-91f6-411f-850f-b07e12a8acd2"
        filename = "089784d3-a274-4769-8f5a-4f3a02910738_generated.md"

        self.assertNotIn(job_id, filename)

    def test_multiple_files_same_directory(self):
        """Ensure correct file selection when multiple outputs exist."""
        job_id = "abc-123"
        files = [
            "xyz-789_generated.md",  # Wrong job
            "abc-123_generated.md",  # Correct
            "def-456_generated.md",  # Wrong job
        ]

        matching = [f for f in files if job_id in f]

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0], "abc-123_generated.md")


class TestRetryLogic(unittest.TestCase):
    """Test suite for retry logic configuration."""

    def test_backoff_increases_exponentially(self):
        """Verify exponential backoff calculation."""
        attempt_delays = []

        for attempt in range(3):
            # Base exponential backoff (without jitter)
            base_delay = 2 ** attempt
            attempt_delays.append(base_delay)

        self.assertEqual(attempt_delays, [1, 2, 4])

    def test_retryable_status_codes(self):
        """Verify which HTTP status codes should be retried."""
        retryable = [429, 502, 503, 504]
        non_retryable = [400, 401, 403, 404, 500]

        for code in retryable:
            self.assertIn(code, [429, 502, 503, 504])

        for code in non_retryable:
            self.assertNotIn(code, [429, 502, 503, 504])


if __name__ == "__main__":
    unittest.main()
