"""Test Services functionality including fixes."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from src.services.services import (
    LLMService,
    NoMockGate,
    SEOSchemaGate,
    PrerequisitesNormalizer,
    PyTrendsGuard,
    TopicIdentificationFallback,
    BlogSwitchPolicy,
    RunToResultGuarantee,
    apply_llm_service_fixes
)


class TestNoMockGate:
    """Test NO-MOCK gate functionality."""
    
    @pytest.fixture
    def gate(self):
        """Create NoMockGate instance."""
        return NoMockGate()
    
    def test_detect_placeholder_content(self, gate):
        """Test detection of placeholder content."""
        # Test various placeholder patterns
        assert gate.contains_mock("Your Optimized Title Here")
        assert gate.contains_mock("{{placeholder}}")
        assert gate.contains_mock("Lorem ipsum dolor sit")
        assert gate.contains_mock("TODO: Add content")
        assert gate.contains_mock("FIXME: Update this")
        assert gate.contains_mock("Insert content here")
        assert gate.contains_mock("Add description content")
        assert gate.contains_mock("Example content goes here")
        assert gate.contains_mock("Sample text")
        assert gate.contains_mock("Your text here")
        assert gate.contains_mock("...")
        assert gate.contains_mock("TBD")
        assert gate.contains_mock("Coming soon")
    
    def test_accept_valid_content(self, gate):
        """Test acceptance of valid content."""
        assert not gate.contains_mock("This is real content about Python programming")
        assert not gate.contains_mock("Learn how to build web applications with Django")
        assert not gate.contains_mock("The quick brown fox jumps over the lazy dog")
    
    def test_reject_short_content(self, gate):
        """Test rejection of too-short content."""
        assert gate.contains_mock("")
        assert gate.contains_mock("   ")
        assert gate.contains_mock("Short")
    
    def test_validate_string_response(self, gate):
        """Test validation of string responses."""
        # Valid response
        is_valid, reason = gate.validate_response("This is valid content about testing")
        assert is_valid
        assert reason == ""
        
        # Invalid response with mock content
        is_valid, reason = gate.validate_response("Your Title Here")
        assert not is_valid
        assert "mock/placeholder" in reason
        
        # None response
        is_valid, reason = gate.validate_response(None)
        assert not is_valid
        assert reason == "Response is None"
    
    def test_validate_dict_response(self, gate):
        """Test validation of dictionary responses."""
        # Valid dict
        is_valid, reason = gate.validate_response({
            "title": "Real Title",
            "content": "Real content about the topic"
        })
        assert is_valid
        
        # Dict with mock content
        is_valid, reason = gate.validate_response({
            "title": "Your Title Here",
            "content": "Real content"
        })
        assert not is_valid
        assert "title" in reason
    
    def test_validate_list_response(self, gate):
        """Test validation of list responses."""
        # Valid list
        is_valid, reason = gate.validate_response([
            "Real item 1",
            "Real item 2"
        ])
        assert is_valid
        
        # List with mock content
        is_valid, reason = gate.validate_response([
            "Real item",
            "TODO: Add item"
        ])
        assert not is_valid
        assert "Item 1" in reason


class TestSEOSchemaGate:
    """Test SEO schema normalization."""
    
    def test_coerce_basic_fields(self):
        """Test basic field coercion."""
        meta = {
            "title": "Test Title",
            "description": "Test description"
        }
        
        result = SEOSchemaGate.coerce_and_fill(meta)
        
        assert result["title"] == "Test Title"
        assert result["seoTitle"] == "Test Title"
        assert result["description"] == "Test description"
        assert "slug" in result
        assert result["slug"] == "test-title"
    
    def test_handle_nested_metadata(self):
        """Test handling of nested metadata structures."""
        meta = {
            "metadata": {
                "title": "Nested Title"
            }
        }
        
        result = SEOSchemaGate.coerce_and_fill(meta)
        assert result["title"] == "Nested Title"
        
        # Test deeper nesting
        meta = {
            "data": {
                "metadata": {
                    "title": "Deep Title"
                }
            }
        }
        
        result = SEOSchemaGate.coerce_and_fill(meta)
        assert result["title"] == "Deep Title"
    
    def test_field_mappings(self):
        """Test alternative field name mappings."""
        meta = {
            "articleTitle": "Article Title",
            "meta_description": "Meta desc",
            "seo_keywords": "keyword1, keyword2",
            "url_slug": "custom-slug"
        }
        
        result = SEOSchemaGate.coerce_and_fill(meta)
        
        assert result["title"] == "Article Title"
        assert result["description"] == "Meta desc"
        assert result["keywords"] == ["keyword1", "keyword2"]
        assert result["slug"] == "custom-slug"
    
    def test_convert_tags_keywords_to_lists(self):
        """Test conversion of tags/keywords to lists."""
        meta = {
            "title": "Test",
            "tags": "tag1, tag2; tag3|tag4",
            "keywords": "key1;key2"
        }
        
        result = SEOSchemaGate.coerce_and_fill(meta)
        
        assert result["tags"] == ["tag1", "tag2", "tag3", "tag4"]
        assert result["keywords"] == ["key1", "key2"]
    
    def test_truncate_long_seo_title(self):
        """Test truncation of long SEO titles."""
        meta = {
            "title": "This is a very long title that exceeds the maximum recommended length for SEO purposes and needs truncation"
        }
        
        result = SEOSchemaGate.coerce_and_fill(meta)
        
        assert len(result["seoTitle"]) <= 60
        assert result["seoTitle"].startswith("This is a very long title")
    
    def test_generate_missing_fields(self):
        """Test generation of missing required fields."""
        meta = {}
        
        result = SEOSchemaGate.coerce_and_fill(meta)
        
        assert result["title"] == "Untitled Post"
        assert result["seoTitle"] == "Untitled Post"
        assert "description" in result
        assert result["slug"] == "untitled-post"
        assert result["tags"] == []
        assert result["keywords"] == []
    
    def test_validate_slug_format(self):
        """Test slug format validation."""
        meta = {
            "title": "Test",
            "slug": "Invalid Slug With Spaces!"
        }
        
        result = SEOSchemaGate.coerce_and_fill(meta)
        
        assert result["slug"] == "invalid-slug-with-spaces"


class TestPrerequisitesNormalizer:
    """Test prerequisites normalization."""
    
    def test_normalize_none(self):
        """Test normalizing None value."""
        result = PrerequisitesNormalizer.normalize(None)
        assert result == []
    
    def test_normalize_string(self):
        """Test normalizing string values."""
        # Single prerequisite
        result = PrerequisitesNormalizer.normalize("Python basics")
        assert result == ["Python basics"]
        
        # Comma-separated prerequisites
        result = PrerequisitesNormalizer.normalize("Python, JavaScript, HTML")
        assert result == ["Python", "JavaScript", "HTML"]
        
        # Empty string
        result = PrerequisitesNormalizer.normalize("")
        assert result == []
        
        # Whitespace only
        result = PrerequisitesNormalizer.normalize("   ")
        assert result == []
    
    def test_normalize_list(self):
        """Test normalizing list values."""
        # Valid list
        result = PrerequisitesNormalizer.normalize(["Python", "JS"])
        assert result == ["Python", "JS"]
        
        # List with None values
        result = PrerequisitesNormalizer.normalize(["Python", None, "JS"])
        assert result == ["Python", "JS"]
        
        # List with empty strings
        result = PrerequisitesNormalizer.normalize(["Python", "", "JS", "  "])
        assert result == ["Python", "JS"]
    
    def test_normalize_other_types(self):
        """Test normalizing other types."""
        # Integer
        result = PrerequisitesNormalizer.normalize(123)
        assert result == ["123"]
        
        # Boolean
        result = PrerequisitesNormalizer.normalize(True)
        assert result == ["True"]


class TestPyTrendsGuard:
    """Test PyTrends guard functionality."""
    
    @pytest.fixture
    def guard(self):
        """Create PyTrendsGuard instance."""
        return PyTrendsGuard(max_retries=3, backoff=1.0)
    
    def test_successful_fetch(self, guard):
        """Test successful fetch on first try."""
        mock_func = Mock(return_value={"data": "success"})
        
        result = guard.safe_fetch("test query", mock_func)
        
        assert result == {"data": "success"}
        mock_func.assert_called_once_with("test query")
    
    def test_retry_on_failure(self, guard):
        """Test retry logic on failures."""
        mock_func = Mock(side_effect=[
            Exception("First failure"),
            Exception("Second failure"),
            {"data": "success"}
        ])
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = guard.safe_fetch("test query", mock_func)
        
        assert result == {"data": "success"}
        assert mock_func.call_count == 3
    
    def test_fallback_after_max_retries(self, guard):
        """Test fallback after maximum retries."""
        mock_func = Mock(side_effect=Exception("Always fails"))
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = guard.safe_fetch("test query", mock_func)
        
        assert result["query"] == "test query"
        assert result["score"] == 50
        assert result["note"] == "fallback_due_to_error"
        assert result["trending"] == False
        assert mock_func.call_count == 3
    
    def test_custom_fallback_value(self, guard):
        """Test custom fallback value."""
        mock_func = Mock(side_effect=Exception("Always fails"))
        custom_fallback = {"custom": "fallback"}
        
        with patch('time.sleep'):
            result = guard.safe_fetch("test", mock_func, custom_fallback)
        
        assert result == custom_fallback


class TestTopicIdentificationFallback:
    """Test topic identification fallback."""
    
    def test_ensure_topic_with_title(self):
        """Test ensuring topic with existing title."""
        topic = {"title": "Existing Title"}
        
        result = TopicIdentificationFallback.ensure_topic(topic)
        
        assert result["title"] == "Existing Title"
        assert result["slug"] == "existing-title"
        assert result["description"] == "Content about Existing Title"
    
    def test_ensure_topic_with_alternative_fields(self):
        """Test fallback to alternative fields."""
        # Using 'name' field
        topic = {"name": "Topic Name"}
        result = TopicIdentificationFallback.ensure_topic(topic)
        assert result["title"] == "Topic Name"
        
        # Using 'topic' field
        topic = {"topic": "Topic Value"}
        result = TopicIdentificationFallback.ensure_topic(topic)
        assert result["title"] == "Topic Value"
        
        # Using 'subject' field
        topic = {"subject": "Subject Value"}
        result = TopicIdentificationFallback.ensure_topic(topic)
        assert result["title"] == "Subject Value"
    
    def test_ensure_topic_empty_dict(self):
        """Test ensuring topic with empty dictionary."""
        result = TopicIdentificationFallback.ensure_topic({})
        
        assert result["title"] == "Untitled Topic"
        assert result["slug"] == "untitled-topic"
        assert result["description"] == "Content about Untitled Topic"
    
    def test_ensure_topic_non_dict(self):
        """Test ensuring topic with non-dict input."""
        result = TopicIdentificationFallback.ensure_topic("not a dict")
        
        assert result["title"] == "Untitled Topic"
        assert result["slug"] == "untitled-topic"
    
    def test_preserve_existing_fields(self):
        """Test preservation of existing fields."""
        topic = {
            "title": "Test",
            "slug": "custom-slug",
            "description": "Custom description",
            "extra": "preserved"
        }
        
        result = TopicIdentificationFallback.ensure_topic(topic)
        
        assert result["title"] == "Test"
        assert result["slug"] == "custom-slug"
        assert result["description"] == "Custom description"
        assert result["extra"] == "preserved"


class TestBlogSwitchPolicy:
    """Test blog switch output policy."""
    
    def test_blog_switch_on(self):
        """Test output path with blog_switch=True."""
        config = Mock(blog_switch=True, output_dir="./output")
        
        path = BlogSwitchPolicy.get_output_path(config, "test-slug")
        
        assert path == "./output/test-slug/index.md"
    
    def test_blog_switch_off(self):
        """Test output path with blog_switch=False."""
        config = Mock(blog_switch=False, output_dir="./output")
        
        path = BlogSwitchPolicy.get_output_path(config, "test-slug")
        
        assert path == "./output/test-slug.md"
    
    @patch('pathlib.Path.mkdir')
    def test_directory_creation(self, mock_mkdir):
        """Test directory creation."""
        config = Mock(blog_switch=True, output_dir="./output")
        
        BlogSwitchPolicy.get_output_path(config, "test-slug")
        
        # Should create directories
        assert mock_mkdir.call_count >= 1


class TestRunToResultGuarantee:
    """Test run-to-result guarantee."""
    
    def test_create_minimal_document(self):
        """Test creation of minimal fallback document."""
        content = RunToResultGuarantee.create_minimal_document(
            topic="Test Topic",
            slug="test-topic"
        )
        
        # Check frontmatter
        assert "title: Test Topic" in content or '"title": "Test Topic"' in content
        assert "slug: test-topic" in content or '"slug": "test-topic"' in content
        assert "draft: true" in content or '"draft": true' in content
        
        # Check content sections
        assert "# Test Topic" in content
        assert "## Introduction" in content
        assert "## Overview" in content
        assert "## Key Points" in content
        assert "## Conclusion" in content
        
        # Check it mentions it's a placeholder
        assert "placeholder" in content.lower() or "pending" in content.lower()
    
    def test_create_minimal_document_defaults(self):
        """Test minimal document with defaults."""
        content = RunToResultGuarantee.create_minimal_document()
        
        assert "Untitled" in content
        assert "untitled" in content


class TestLLMServiceFixes:
    """Test LLM service fixes application."""
    
    def test_apply_fixes_to_llm_service(self):
        """Test applying NO-MOCK fixes to LLMService."""
        # Create mock LLMService class
        class MockLLMService:
            def generate(self, prompt, schema=None, **kwargs):
                return "Your Title Here"  # Returns mock content
        
        # Apply fixes
        FixedLLMService = apply_llm_service_fixes(MockLLMService)
        
        # Create instance
        service = FixedLLMService()
        
        # Test that mock content is rejected
        with pytest.raises(ValueError) as excinfo:
            service.generate("Generate a title", max_attempts=1)
        
        assert "mock content detected" in str(excinfo.value)
    
    def test_retry_with_stricter_prompt(self):
        """Test retry with stricter prompt."""
        class MockLLMService:
            def __init__(self):
                self.call_count = 0
            
            def generate(self, prompt, schema=None, **kwargs):
                self.call_count += 1
                if self.call_count == 1:
                    return "TODO: Add content"
                else:
                    # Second attempt with stricter prompt
                    if "IMPORTANT:" in prompt:
                        return "Real content about the topic"
                    return "TODO: Add content"
        
        # Apply fixes
        FixedLLMService = apply_llm_service_fixes(MockLLMService)
        
        # Create instance
        service = FixedLLMService()
        
        # Should succeed on second attempt
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = service.generate("Generate content", max_attempts=2)
        
        assert result == "Real content about the topic"
        assert service.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
