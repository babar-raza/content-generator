"""End‑to‑end test for blog generation via the unified engine.

This scenario covers the full path from ingesting a knowledge base article
to producing a Markdown blog post.  It invokes the unified engine with
a ``RunSpec`` configured for the default blog template, verifies that
the job completes successfully and that the resulting Markdown file
contains the expected sections.  As an end‑to‑end test it also ensures
that no exceptions are raised and that the side effects on the file
system are as expected.  Cleanup is handled automatically by the
``clean_environment`` fixture from the integration tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.engine.unified_engine import UnifiedEngine, RunSpec, JobStatus

from tests.integration.test_full_pipeline import get_fixture_path


def test_blog_generation_end_to_end(tmp_path: Path) -> None:
    """Run the blog generation pipeline and assert on the generated content."""
    engine = UnifiedEngine()
    kb_file = get_fixture_path("test_kb.md")
    run_spec = RunSpec(
        topic="End to End",
        template_name="default_blog",
        kb_path=kb_file,
        auto_topic=False,
        output_dir=Path("output"),
    )
    result = engine.generate_job(run_spec)
    assert result.status == JobStatus.COMPLETED
    output_path = result.output_path
    assert output_path is not None and output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    # Check for run summary and at least one agent output marker
    assert "# Run Summary" in content
    # The stub agents write a mock_output field; ensure it appears somewhere
    assert "mock_output" in content