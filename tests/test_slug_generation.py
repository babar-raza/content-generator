"""Test slug generation and collision handling."""
import pytest
from pathlib import Path
from src.engine.unified_engine import urlify, RunSpec


def test_urlify_basic():
    """Test basic slug generation."""
    assert urlify("Python Classes") == "python-classes"
    assert urlify("C# Async/Await") == "c-asyncawait"
    assert urlify("  Multiple   Spaces  ") == "multiple-spaces"


def test_urlify_special_chars():
    """Test slug generation with special characters."""
    assert urlify("Hello, World!") == "hello-world"
    assert urlify("Test@123#456") == "test123456"
    assert urlify("Foo & Bar") == "foo-bar"


def test_urlify_empty():
    """Test slug generation with empty string."""
    assert urlify("") == ""
    assert urlify("   ") == ""


def test_blog_template_path(tmp_path):
    """Test output path generation for blog template."""
    spec = RunSpec(
        topic="Python Classes",
        template_name="blog_default",
        output_dir=tmp_path
    )
    path = spec.generate_output_path("Python Classes Tutorial")
    assert path == tmp_path / "python-classes-tutorial" / "index.md"


def test_non_blog_template_path(tmp_path):
    """Test output path generation for non-blog template."""
    spec = RunSpec(
        topic="Python Classes",
        template_name="code_example",
        output_dir=tmp_path
    )
    path = spec.generate_output_path("Python Classes")
    assert path == tmp_path / "Python_Classes.md"


def test_slug_collision_handling(tmp_path):
    """Test collision handling for blog slugs."""
    spec = RunSpec(
        topic="Test",
        template_name="blog_default",
        output_dir=tmp_path
    )
    
    # Create first file
    path1 = spec.generate_output_path("Python Classes")
    path1.parent.mkdir(parents=True, exist_ok=True)
    path1.write_text("first")
    
    # Second should get suffix
    path2 = spec.generate_output_path("Python Classes")
    assert path2 == tmp_path / "python-classes-2" / "index.md"


def test_multiple_collisions(tmp_path):
    """Test handling of multiple collisions."""
    spec = RunSpec(
        topic="Test",
        template_name="blog_tutorial",
        output_dir=tmp_path
    )
    
    # Create multiple files with same base slug
    title = "Python Tutorial"
    paths = []
    
    for i in range(3):
        path = spec.generate_output_path(title)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"content {i}")
        paths.append(path)
    
    # Check all paths are unique
    assert len(set(paths)) == 3
    assert paths[0] == tmp_path / "python-tutorial" / "index.md"
    assert paths[1] == tmp_path / "python-tutorial-2" / "index.md"
    assert paths[2] == tmp_path / "python-tutorial-3" / "index.md"
