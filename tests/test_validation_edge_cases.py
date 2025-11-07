"""Test validation edge cases for RunSpec."""
import pytest
from pathlib import Path
from src.engine.unified_engine import RunSpec


def test_auto_topic_requires_context():
    """Test that auto_topic=True requires at least one context source."""
    spec = RunSpec(
        topic=None,
        auto_topic=True,
        template_name="blog_default",
        output_dir=Path("./output")
    )
    
    errors = spec.validate()
    assert len(errors) > 0
    assert any("auto_topic=True requires at least one context source" in err for err in errors)


def test_auto_topic_with_context_valid():
    """Test that auto_topic=True with context is valid."""
    spec = RunSpec(
        topic=None,
        auto_topic=True,
        template_name="blog_default",
        kb_path="./data/kb",
        output_dir=Path("./output")
    )
    
    # Create dummy kb path
    Path("./data/kb").mkdir(parents=True, exist_ok=True)
    Path("./data/kb/test.md").write_text("test")
    
    errors = spec.validate()
    # Should only fail on path existence if any
    context_errors = [e for e in errors if "context source" in e]
    assert len(context_errors) == 0


def test_no_topic_without_auto_topic():
    """Test that topic is required when auto_topic=False."""
    spec = RunSpec(
        topic=None,
        auto_topic=False,
        template_name="blog_default",
        output_dir=Path("./output")
    )
    
    errors = spec.validate()
    assert len(errors) > 0
    assert any("Must provide topic when auto_topic=False" in err for err in errors)


def test_template_required():
    """Test that template_name is required."""
    spec = RunSpec(
        topic="Python Classes",
        template_name="",
        output_dir=Path("./output")
    )
    
    errors = spec.validate()
    assert len(errors) > 0
    assert any("template_name is required" in err for err in errors)


def test_template_none():
    """Test that template_name=None is caught."""
    spec = RunSpec(
        topic="Python Classes",
        template_name=None,
        output_dir=Path("./output")
    )
    
    errors = spec.validate()
    assert len(errors) > 0
    assert any("template_name is required" in err for err in errors)


def test_valid_spec_with_topic():
    """Test a valid spec with topic."""
    spec = RunSpec(
        topic="Python Classes",
        template_name="blog_default",
        output_dir=Path("./output")
    )
    
    errors = spec.validate()
    assert len(errors) == 0


def test_multiple_context_sources():
    """Test that multiple context sources work with auto_topic."""
    spec = RunSpec(
        topic=None,
        auto_topic=True,
        template_name="blog_default",
        kb_path="./data/kb",
        docs_path="./data/docs",
        blog_path="./data/blog",
        output_dir=Path("./output")
    )
    
    # Create dummy paths
    for path in ["./data/kb", "./data/docs", "./data/blog"]:
        Path(path).mkdir(parents=True, exist_ok=True)
        Path(f"{path}/test.md").write_text("test")
    
    errors = spec.validate()
    # Should be valid with multiple context sources
    context_errors = [e for e in errors if "context source" in e]
    assert len(context_errors) == 0


def test_invalid_path_validation(tmp_path):
    """Test that non-existent paths are caught."""
    spec = RunSpec(
        topic="Python Classes",
        template_name="blog_default",
        kb_path="/non/existent/path",
        output_dir=tmp_path
    )
    
    errors = spec.validate()
    assert len(errors) > 0
    assert any("does not exist" in err for err in errors)
