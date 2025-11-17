"""Tests for slug service."""

import pytest
from src.engine.slug_service import slugify


class TestSlugify:
    """Test slug generation."""
    
    def test_basic_slug(self):
        """Test basic slug generation."""
        assert slugify("Hello World") == "hello-world"
    
    def test_special_characters(self):
        """Test handling of special characters."""
        assert slugify("C# 10 Features: Pattern Matching+") == "c-10-features-pattern-matching"
    
    def test_diacritics(self):
        """Test unicode to ASCII conversion."""
        assert slugify("Café Münchën") == "cafe-munchen"
    
    def test_mixed_case(self):
        """Test case normalization."""
        assert slugify("MixedCaseTitle") == "mixedcasetitle"
    
    def test_whitespace_collapse(self):
        """Test whitespace handling."""
        assert slugify("Multiple   Spaces") == "multiple-spaces"
    
    def test_hyphen_collapse(self):
        """Test hyphen collapsing."""
        assert slugify("Too---Many---Hyphens") == "too-many-hyphens"
    
    def test_trim_hyphens(self):
        """Test leading/trailing hyphen removal."""
        assert slugify("-Leading and Trailing-") == "leading-and-trailing"
    
    def test_empty_input(self):
        """Test empty input."""
        assert slugify("") == ""
    
    def test_only_special_chars(self):
        """Test input with only special characters."""
        assert slugify("!!!@@@###") == ""
    
    def test_complex_example(self):
        """Test complex real-world example."""
        # Note: apostrophe becomes hyphen per spec (non-alphanumeric → -)
        assert slugify("Python's Best Practices & Tips (2024)!") == "python-s-best-practices-tips-2024"
# DOCGEN:LLM-FIRST@v4