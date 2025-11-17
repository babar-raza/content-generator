"""Tests for output path resolver."""

import pytest
from pathlib import Path
from src.engine.output_path_resolver import is_blog_template, resolve_output_path


class TestOutputPathResolver:
    """Test output path resolution."""
    
    def test_is_blog_template_true(self):
        """Test blog template detection - positive cases."""
        assert is_blog_template("blog")
        assert is_blog_template("Blog")
        assert is_blog_template("BLOG")
        assert is_blog_template("blog_post")
        assert is_blog_template("technical_blog")
    
    def test_is_blog_template_false(self):
        """Test blog template detection - negative cases."""
        assert not is_blog_template("code")
        assert not is_blog_template("markdown")
        assert not is_blog_template("docs")
        assert not is_blog_template("technical")
    
    def test_is_blog_template_edge_cases(self):
        """Test blog template detection - edge cases."""
        assert not is_blog_template("")
        assert not is_blog_template(None)
    
    def test_blog_template_output_path(self):
        """Test blog template creates folder structure."""
        path = resolve_output_path("blog", "my-post", Path("./output"))
        assert path == Path("./output/my-post/index.md")
    
    def test_non_blog_template_output_path(self):
        """Test non-blog template creates single file."""
        path = resolve_output_path("code", "my-snippet", Path("./output"))
        assert path == Path("./output/my-snippet.md")
    
    def test_default_output_dir(self):
        """Test default output directory."""
        path = resolve_output_path("blog", "test")
        assert str(path).startswith("output")
    
    def test_custom_output_dir(self):
        """Test custom output directory."""
        path = resolve_output_path("blog", "test", Path("/custom/output"))
        assert path == Path("/custom/output/test/index.md")
# DOCGEN:LLM-FIRST@v4