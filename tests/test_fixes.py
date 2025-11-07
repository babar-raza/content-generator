"""Test Suite for v9.5 Fixes

Tests all critical fixes:
- NO-MOCK gate
- SEO schema normalization
- Prerequisites handling
- Blog switch policy
- PyTrends guard
- Topic identification fallback
- Run-to-result guarantee
"""

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.services_fixes import (
    NoMockGate, SEOSchemaGate, PrerequisitesNormalizer,
    PyTrendsGuard, TopicIdentificationFallback,
    BlogSwitchPolicy, RunToResultGuarantee
)
from src.core.config import Config
from src.engine.slug_service import slugify, validate_slug


class TestNoMockGate(unittest.TestCase):
    """Test NO-MOCK gate functionality."""
    
    def setUp(self):
        self.gate = NoMockGate()
    
    def test_detects_placeholder_text(self):
        """Test detection of various placeholder patterns."""
        mock_texts = [
            "Your Optimized Title Here",
            "{{placeholder}}",
            "Lorem ipsum dolor sit amet",
            "[PLACEHOLDER]",
            "TODO: Add content here",
            "Insert description here",
            "...",
            "TBD",
            "Coming soon"
        ]
        
        for text in mock_texts:
            self.assertTrue(self.gate.contains_mock(text), f"Failed to detect: {text}")
    
    def test_accepts_real_content(self):
        """Test acceptance of real content."""
        real_texts = [
            "Understanding Python decorators and their practical applications",
            "The comprehensive guide to machine learning algorithms",
            "How to build scalable web applications with Django"
        ]
        
        for text in real_texts:
            self.assertFalse(self.gate.contains_mock(text), f"Wrongly rejected: {text}")
    
    def test_validates_dict_response(self):
        """Test validation of dictionary responses."""
        # Mock response
        mock_response = {
            "title": "Your Title Here",
            "description": "TODO: Add description"
        }
        is_valid, reason = self.gate.validate_response(mock_response)
        self.assertFalse(is_valid)
        self.assertIn("mock content", reason.lower())
        
        # Real response
        real_response = {
            "title": "Python Best Practices",
            "description": "Learn industry-standard Python coding practices"
        }
        is_valid, reason = self.gate.validate_response(real_response)
        self.assertTrue(is_valid)


class TestSEOSchemaGate(unittest.TestCase):
    """Test SEO schema normalization."""
    
    def test_coerce_and_fill_empty(self):
        """Test normalization of empty metadata."""
        result = SEOSchemaGate.coerce_and_fill({})
        
        # Check all required fields exist
        required = ['title', 'seoTitle', 'description', 'tags', 'keywords', 'slug']
        for field in required:
            self.assertIn(field, result)
        
        # Check defaults
        self.assertEqual(result['title'], 'Untitled Post')
        self.assertIsInstance(result['tags'], list)
        self.assertIsInstance(result['keywords'], list)
    
    def test_normalizes_nested_structure(self):
        """Test normalization of nested metadata structures."""
        nested = {
            "metadata": {
                "title": "Test Title",
                "meta_description": "Test description"
            }
        }
        
        result = SEOSchemaGate.coerce_and_fill(nested)
        self.assertEqual(result['title'], 'Test Title')
        self.assertEqual(result['description'], 'Test description')
    
    def test_converts_string_tags_to_list(self):
        """Test conversion of string tags/keywords to lists."""
        data = {
            "title": "Test",
            "tags": "python, django, web",
            "keywords": "programming;coding|development"
        }
        
        result = SEOSchemaGate.coerce_and_fill(data)
        self.assertEqual(result['tags'], ['python', 'django', 'web'])
        self.assertEqual(len(result['keywords']), 3)
    
    def test_auto_generates_slug(self):
        """Test automatic slug generation."""
        data = {"title": "My Amazing Blog Post!"}
        result = SEOSchemaGate.coerce_and_fill(data)
        
        self.assertIn('slug', result)
        self.assertTrue(validate_slug(result['slug']))
        self.assertIn('amazing', result['slug'])
    
    def test_truncates_seo_title(self):
        """Test SEO title truncation at 60 characters."""
        long_title = "This is a very long title that definitely exceeds the recommended sixty character limit for SEO"
        data = {"title": long_title}
        
        result = SEOSchemaGate.coerce_and_fill(data)
        self.assertLessEqual(len(result['seoTitle']), 60)


class TestPrerequisitesNormalizer(unittest.TestCase):
    """Test prerequisites normalization."""
    
    def test_normalizes_none(self):
        """Test normalization of None value."""
        result = PrerequisitesNormalizer.normalize(None)
        self.assertEqual(result, [])
    
    def test_normalizes_string(self):
        """Test normalization of string values."""
        # Single prerequisite
        result = PrerequisitesNormalizer.normalize("Python basics")
        self.assertEqual(result, ["Python basics"])
        
        # Comma-separated
        result = PrerequisitesNormalizer.normalize("Python, JavaScript, HTML")
        self.assertEqual(result, ["Python", "JavaScript", "HTML"])
        
        # Empty string
        result = PrerequisitesNormalizer.normalize("")
        self.assertEqual(result, [])
    
    def test_normalizes_list(self):
        """Test normalization of list values."""
        # Normal list
        result = PrerequisitesNormalizer.normalize(["Python", "Django"])
        self.assertEqual(result, ["Python", "Django"])
        
        # List with None and empty strings
        result = PrerequisitesNormalizer.normalize(["Python", None, "", "Django"])
        self.assertEqual(result, ["Python", "Django"])
    
    def test_normalizes_unusual_types(self):
        """Test normalization of unusual types."""
        # Number
        result = PrerequisitesNormalizer.normalize(42)
        self.assertEqual(result, ["42"])
        
        # Dict (converts to string)
        result = PrerequisitesNormalizer.normalize({"key": "value"})
        self.assertTrue(len(result) > 0)


class TestPyTrendsGuard(unittest.TestCase):
    """Test PyTrends guard with retry logic."""
    
    def test_successful_fetch(self):
        """Test successful fetch on first attempt."""
        guard = PyTrendsGuard(max_retries=3)
        
        mock_func = Mock(return_value={"trend": "data"})
        result = guard.safe_fetch("test query", mock_func)
        
        self.assertEqual(result, {"trend": "data"})
        mock_func.assert_called_once_with("test query")
    
    def test_retry_on_failure(self):
        """Test retry logic on failures."""
        guard = PyTrendsGuard(max_retries=3, backoff=1.0)
        
        # Fail twice, succeed on third
        mock_func = Mock(side_effect=[Exception("Error"), Exception("Error"), {"trend": "data"}])
        
        with patch('time.sleep'):  # Skip actual sleep in tests
            result = guard.safe_fetch("test query", mock_func)
        
        self.assertEqual(result, {"trend": "data"})
        self.assertEqual(mock_func.call_count, 3)
    
    def test_fallback_after_max_retries(self):
        """Test fallback value after max retries."""
        guard = PyTrendsGuard(max_retries=2)
        
        mock_func = Mock(side_effect=Exception("Always fails"))
        
        with patch('time.sleep'):
            result = guard.safe_fetch("test query", mock_func, fallback_value={"fallback": True})
        
        self.assertEqual(result, {"fallback": True})
        self.assertEqual(mock_func.call_count, 2)
    
    def test_default_fallback_structure(self):
        """Test default fallback structure when none provided."""
        guard = PyTrendsGuard(max_retries=1)
        
        mock_func = Mock(side_effect=Exception("Error"))
        
        with patch('time.sleep'):
            result = guard.safe_fetch("test query", mock_func)
        
        self.assertIn("query", result)
        self.assertIn("score", result)
        self.assertIn("note", result)
        self.assertEqual(result["query"], "test query")


class TestTopicIdentificationFallback(unittest.TestCase):
    """Test topic identification fallback logic."""
    
    def test_handles_empty_topic(self):
        """Test handling of empty topic data."""
        result = TopicIdentificationFallback.ensure_topic({})
        
        self.assertIn('title', result)
        self.assertIn('slug', result)
        self.assertIn('description', result)
        self.assertEqual(result['title'], 'Untitled Topic')
    
    def test_uses_alternative_fields(self):
        """Test use of alternative field names."""
        # Using 'name' field
        result = TopicIdentificationFallback.ensure_topic({'name': 'Python Guide'})
        self.assertEqual(result['title'], 'Python Guide')
        
        # Using 'subject' field
        result = TopicIdentificationFallback.ensure_topic({'subject': 'Django Tutorial'})
        self.assertEqual(result['title'], 'Django Tutorial')
    
    def test_generates_slug_from_title(self):
        """Test slug generation from title."""
        result = TopicIdentificationFallback.ensure_topic({'title': 'My Amazing Topic!'})
        
        self.assertIn('slug', result)
        self.assertTrue(validate_slug(result['slug']))
    
    def test_preserves_existing_fields(self):
        """Test preservation of existing valid fields."""
        topic = {
            'title': 'Existing Title',
            'slug': 'existing-slug',
            'description': 'Existing description'
        }
        
        result = TopicIdentificationFallback.ensure_topic(topic)
        self.assertEqual(result['title'], 'Existing Title')
        self.assertEqual(result['slug'], 'existing-slug')
        self.assertEqual(result['description'], 'Existing description')


class TestBlogSwitchPolicy(unittest.TestCase):
    """Test blog switch output policy."""
    
    def test_blog_on_creates_directory(self):
        """Test Blog ON mode creates directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.output_dir = tmpdir
            config.blog_switch = True
            
            path = BlogSwitchPolicy.get_output_path(config, "my-post")
            
            self.assertTrue(path.endswith("/my-post/index.md"))
            self.assertTrue(Path(path).parent.exists())
    
    def test_blog_off_creates_file(self):
        """Test Blog OFF mode creates single file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Mock()
            config.output_dir = tmpdir
            config.blog_switch = False
            
            path = BlogSwitchPolicy.get_output_path(config, "my-post")
            
            self.assertTrue(path.endswith("/my-post.md"))
            self.assertFalse(path.endswith("/index.md"))


class TestRunToResultGuarantee(unittest.TestCase):
    """Test run-to-result guarantee."""
    
    def test_creates_minimal_document(self):
        """Test creation of minimal fallback document."""
        doc = RunToResultGuarantee.create_minimal_document("Test Topic", "test-topic")
        
        # Check structure
        self.assertIn("---", doc)  # Frontmatter delimiters
        self.assertIn("# Test Topic", doc)  # Title
        self.assertIn("## Introduction", doc)  # Sections
        self.assertIn("## Overview", doc)
        self.assertIn("## Conclusion", doc)
        
        # Parse frontmatter
        import yaml
        frontmatter_text = doc.split("---")[1]
        frontmatter = yaml.safe_load(frontmatter_text)
        
        # Check frontmatter fields
        self.assertEqual(frontmatter['title'], 'Test Topic')
        self.assertEqual(frontmatter['slug'], 'test-topic')
        self.assertEqual(frontmatter['prerequisites'], [])
        self.assertTrue(frontmatter['draft'])
        self.assertIn('note', frontmatter)


class TestSlugService(unittest.TestCase):
    """Test slug generation service."""
    
    def test_slugify_basic(self):
        """Test basic slug generation."""
        tests = [
            ("Hello World", "hello-world"),
            ("Python 3.9 Guide!", "python-3-9-guide"),
            ("  Spaces  Everywhere  ", "spaces-everywhere"),
            ("CamelCaseTitle", "camelcasetitle"),
            ("Multiple---Hyphens", "multiple-hyphens")
        ]
        
        for input_text, expected in tests:
            result = slugify(input_text)
            self.assertEqual(result, expected, f"Failed for: {input_text}")
    
    def test_slugify_truncation(self):
        """Test slug truncation at max length."""
        long_text = "This is a very long title that needs to be truncated properly at word boundaries"
        result = slugify(long_text, max_length=30)
        
        self.assertLessEqual(len(result), 30)
        self.assertFalse(result.endswith('-'))
    
    def test_validate_slug(self):
        """Test slug validation."""
        valid_slugs = ["hello-world", "python-3-9", "test123", "a-b-c"]
        invalid_slugs = ["", "-start", "end-", "Hello-World", "test--double", "special!char"]
        
        for slug in valid_slugs:
            self.assertTrue(validate_slug(slug), f"Should be valid: {slug}")
        
        for slug in invalid_slugs:
            self.assertFalse(validate_slug(slug), f"Should be invalid: {slug}")


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete flow."""
    
    def test_complete_seo_normalization_flow(self):
        """Test complete SEO normalization flow."""
        # Simulate LLM response with issues
        raw_response = {
            "metadata": {
                "title": "Your Title Here",  # Mock content
                "meta_description": "TODO: Add description",  # Mock content
                "tags": "python,django",  # String instead of list
                # Missing slug
            }
        }
        
        # Apply fixes
        no_mock = NoMockGate()
        
        # First normalize structure
        normalized = SEOSchemaGate.coerce_and_fill(raw_response)
        
        # Check for mock content and replace
        for field in ['title', 'description']:
            if field in normalized and isinstance(normalized[field], str):
                if no_mock.contains_mock(normalized[field]):
                    if field == 'title':
                        normalized[field] = 'Python Guide'
                    elif field == 'description':
                        normalized[field] = 'Learn Python programming'
        
        # Verify final result
        self.assertEqual(normalized['title'], 'Python Guide')
        self.assertEqual(normalized['description'], 'Learn Python programming')
        self.assertIsInstance(normalized['tags'], list)
        self.assertIn('slug', normalized)
        self.assertTrue(validate_slug(normalized['slug']))
    
    def test_prerequisites_in_frontmatter_flow(self):
        """Test prerequisites handling in frontmatter generation."""
        # Various prerequisite formats
        test_cases = [
            None,
            "Python basics",
            "Python, JavaScript, HTML",
            ["Python", "Django"],
            {"invalid": "type"}
        ]
        
        for prereq_value in test_cases:
            result = PrerequisitesNormalizer.normalize(prereq_value)
            self.assertIsInstance(result, list, f"Failed for: {prereq_value}")
            for item in result:
                self.assertIsInstance(item, str)


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()
