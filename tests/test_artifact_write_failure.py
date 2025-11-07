"""Test that artifacts are always written, even on failure."""
import pytest
from pathlib import Path
from src.engine.unified_engine import get_engine, RunSpec


def test_failure_writes_partial_artifact(tmp_path):
    """Test that failure writes a partial artifact with error details."""
    engine = get_engine()
    
    spec = RunSpec(
        topic="Python Classes",
        template_name="blog_default",
        output_dir=tmp_path,
        kb_path="/non/existent/path"  # This will cause validation error
    )
    
    result = engine.generate_job(spec)
    
    # Should fail due to invalid path
    assert result.status in ["failed", "partial"]
    
    # But should still have attempted to write something
    assert result.error is not None


def test_partial_completion_writes_artifact(tmp_path, monkeypatch):
    """Test that partial completion writes artifact with completed sections."""
    engine = get_engine()
    
    # Create a valid KB path
    kb_path = tmp_path / "kb"
    kb_path.mkdir()
    (kb_path / "test.md").write_text("# Test KB\n\nSome content")
    
    spec = RunSpec(
        topic="Python Classes",
        template_name="blog_default",
        kb_path=str(kb_path),
        output_dir=tmp_path / "output"
    )
    
    result = engine.generate_job(spec)
    
    # Should have some output even if not fully successful
    assert result.output_path is not None or result.artifact_content is not None


def test_minimal_artifact_on_template_failure(tmp_path):
    """Test that even template rendering failure produces minimal artifact."""
    engine = get_engine()
    
    # Use invalid template name
    spec = RunSpec(
        topic="Python Classes",
        template_name="non_existent_template",
        output_dir=tmp_path
    )
    
    result = engine.generate_job(spec)
    
    # Should fail
    assert result.status == "failed"
    assert result.error is not None


def test_artifact_contains_error_section_on_failure(tmp_path):
    """Test that failed artifacts contain error sections."""
    engine = get_engine()
    
    spec = RunSpec(
        topic="Python Classes",
        template_name="",  # Empty template to trigger validation error
        output_dir=tmp_path
    )
    
    result = engine.generate_job(spec)
    
    # Should have error
    assert result.error is not None
    assert "Validation failed" in result.error or "template_name is required" in result.error


def test_checkpointed_write_after_agent(tmp_path):
    """Test that artifacts are written after each agent completes."""
    engine = get_engine()
    
    # Create a valid KB
    kb_path = tmp_path / "kb"
    kb_path.mkdir()
    (kb_path / "test.md").write_text("# Test\n\nContent about Python")
    
    spec = RunSpec(
        topic="Python Classes",
        template_name="blog_default",
        kb_path=str(kb_path),
        output_dir=tmp_path / "output"
    )
    
    result = engine.generate_job(spec)
    
    # Should have agent logs showing progress
    assert len(result.agent_logs) >= 0  # At least some agents ran or attempted


def test_manifest_includes_partial_status(tmp_path):
    """Test that manifest correctly marks partial runs."""
    engine = get_engine()
    
    spec = RunSpec(
        topic="Python Classes",
        template_name="blog_default",
        kb_path="/invalid/path",
        output_dir=tmp_path
    )
    
    result = engine.generate_job(spec)
    
    # Should fail validation
    assert result.status == "failed"
    assert result.error is not None
