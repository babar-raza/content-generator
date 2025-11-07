"""System Integration Test - Validates all v9.5 fixes work together

Tests the complete system with all gates, normalizers, and policies active.
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import Config, EventBus, AgentEvent
from src.core.config import load_config
from src.services.services import LLMService
from src.services.services_fixes import (
    NoMockGate, SEOSchemaGate, PrerequisitesNormalizer,
    PyTrendsGuard, TopicIdentificationFallback,
    BlogSwitchPolicy, RunToResultGuarantee
)
from src.engine.slug_service import slugify, validate_slug


class TestSystemIntegration(unittest.TestCase):
    """Test complete system integration with all fixes."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.config = Config()
        self.config.output_dir = Path(self.test_dir) / "output"
        self.config.blog_switch = True
        self.event_bus = EventBus()
    
    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir and Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)
    
    def test_mock_rejection_and_retry(self):
        """Test that mock content is rejected and retried."""
        # Create LLM service mock
        llm_service = Mock(spec=LLMService)
        
        # First call returns mock, second returns real content
        llm_service.generate.side_effect = [
            '{"title": "Your Title Here", "description": "TODO: Add description"}',
            '{"title": "Real Python Guide", "description": "Learn Python programming"}'
        ]
        
        # Apply NO-MOCK gate
        no_mock_gate = NoMockGate()
        
        # First attempt
        first_response = json.loads(llm_service.generate())
        is_valid, reason = no_mock_gate.validate_response(first_response)
        self.assertFalse(is_valid)
        self.assertIn("mock", reason.lower())
        
        # Second attempt (retry)
        second_response = json.loads(llm_service.generate())
        is_valid, reason = no_mock_gate.validate_response(second_response)
        self.assertTrue(is_valid)
    
    def test_seo_normalization_cascade(self):
        """Test SEO normalization through the full cascade."""
        # Various malformed SEO inputs
        test_inputs = [
            # Missing everything
            {},
            
            # Missing slug and seoTitle
            {"title": "Test Article"},
            
            # String tags/keywords
            {"title": "Guide", "tags": "python,coding", "keywords": "programming"},
            
            # Nested structure
            {"metadata": {"title": "Nested Article", "tags": ["test"]}},
            
            # Long title for seoTitle truncation
            {"title": "This is a very long title that should be truncated for SEO purposes to fit within the recommended length"}
        ]
        
        for input_data in test_inputs:
            with self.subTest(input=input_data):
                normalized = SEOSchemaGate.coerce_and_fill(input_data)
                
                # Verify all required fields exist
                self.assertIn("title", normalized)
                self.assertIn("seoTitle", normalized)
                self.assertIn("description", normalized)
                self.assertIn("tags", normalized)
                self.assertIn("keywords", normalized)
                self.assertIn("slug", normalized)
                
                # Verify types
                self.assertIsInstance(normalized["tags"], list)
                self.assertIsInstance(normalized["keywords"], list)
                
                # Verify slug is valid
                self.assertTrue(validate_slug(normalized["slug"]))
                
                # Verify seoTitle length
                self.assertLessEqual(len(normalized["seoTitle"]), 60)
    
    def test_prerequisites_in_frontmatter(self):
        """Test prerequisites normalization in frontmatter generation."""
        test_cases = [
            # None -> empty list
            (None, []),
            
            # String -> list
            ("Basic Python knowledge", ["Basic Python knowledge"]),
            
            # Comma-separated -> list
            ("Python,JavaScript,HTML", ["Python", "JavaScript", "HTML"]),
            
            # Already a list -> unchanged
            (["React", "Node.js"], ["React", "Node.js"]),
            
            # Mixed with None and empty -> filtered
            ([None, "Valid", "", "Another"], ["Valid", "Another"])
        ]
        
        for input_val, expected in test_cases:
            with self.subTest(input=input_val):
                result = PrerequisitesNormalizer.normalize(input_val)
                self.assertEqual(result, expected)
    
    def test_blog_switch_file_paths(self):
        """Test blog switch creates correct file paths."""
        test_slug = "test-article"
        
        # Test with blog ON
        self.config.blog_switch = True
        path = BlogSwitchPolicy.get_output_path(self.config, test_slug)
        self.assertTrue(path.endswith(f"{test_slug}/index.md"))
        
        # Test with blog OFF
        self.config.blog_switch = False
        path = BlogSwitchPolicy.get_output_path(self.config, test_slug)
        self.assertTrue(path.endswith(f"{test_slug}.md"))
    
    def test_pytrends_fallback(self):
        """Test PyTrends fallback on error."""
        guard = PyTrendsGuard(max_retries=2, backoff=0.1)
        
        def failing_fetch(query):
            raise Exception("PyTrends API error")
        
        # Should return fallback without crashing
        result = guard.safe_fetch("test query", failing_fetch)
        self.assertIsNotNone(result)
        self.assertEqual(result["note"], "fallback_due_to_error")
    
    def test_topic_identification_fallback(self):
        """Test topic fallback for empty/invalid topics."""
        test_cases = [
            # Empty dict -> generates defaults
            ({}, "Untitled Topic", "untitled-topic"),
            
            # Missing title but has name
            ({"name": "My Article"}, "My Article", "my-article"),
            
            # Has title but no slug
            ({"title": "Test Post"}, "Test Post", "test-post"),
            
            # Complete topic -> unchanged
            ({"title": "Complete", "slug": "custom-slug"}, "Complete", "custom-slug")
        ]
        
        for input_topic, expected_title, expected_slug in test_cases:
            with self.subTest(input=input_topic):
                result = TopicIdentificationFallback.ensure_topic(input_topic)
                self.assertEqual(result["title"], expected_title)
                self.assertEqual(result["slug"], expected_slug)
    
    def test_run_to_result_guarantee(self):
        """Test minimal document generation on failure."""
        # Generate minimal document
        doc = RunToResultGuarantee.create_minimal_document(
            topic="Emergency Fallback",
            slug="emergency-fallback"
        )
        
        # Verify it's valid markdown with frontmatter
        self.assertIn("---", doc)
        self.assertIn('"title": "Emergency Fallback"', doc)
        self.assertIn('"slug": "emergency-fallback"', doc)
        self.assertIn('"prerequisites": []', doc)
        self.assertIn('"draft": true', doc)
        self.assertIn("# Emergency Fallback", doc)
    
    def test_slug_service_with_truncation(self):
        """Test slug generation with max length."""
        # Test basic slugification
        slug = slugify("C# Programming: Best Practices & Tips!")
        self.assertEqual(slug, "c-programming-best-practices-tips")
        
        # Test with max_length (truncates to exactly 15 chars)
        slug = slugify("Very Long Title That Needs Truncation", max_length=15)
        self.assertEqual(slug, "very-long-title")  # Exactly 15 chars
        
        # Test validation
        self.assertTrue(validate_slug("valid-slug"))
        self.assertFalse(validate_slug("Invalid Slug"))
        self.assertFalse(validate_slug("double--dash"))
        self.assertFalse(validate_slug("-leading"))
        self.assertFalse(validate_slug("trailing-"))
    
    @patch('src.services.services.LLMService.generate')
    def test_complete_pipeline_with_all_fixes(self, mock_generate):
        """Test complete pipeline with all fixes active."""
        # Setup mock responses
        mock_generate.side_effect = [
            # First response has mock content (should be rejected)
            '{"title": "Your Title Here"}',
            
            # Second response is valid
            json.dumps({
                "title": "Python Advanced Techniques",
                "description": "Master advanced Python programming"
            }),
            
            # SEO response (partial, will be normalized)
            json.dumps({
                "title": "Python Advanced Techniques",
                "tags": "python,advanced,programming"  # String, will be converted to list
            }),
            
            # Content
            "## Introduction\nLearn advanced Python techniques.\n## Main Content\nDetailed content here."
        ]
        
        # Apply NO-MOCK gate to LLM
        from src.services.services_fixes import apply_llm_service_fixes
        
        llm = Mock(spec=LLMService)
        llm.generate = mock_generate
        
        # Track the flow
        first_call = json.loads(mock_generate())
        no_mock = NoMockGate()
        is_valid, _ = no_mock.validate_response(first_call)
        self.assertFalse(is_valid)  # First call rejected
        
        # Second call succeeds
        second_call = json.loads(mock_generate())
        is_valid, _ = no_mock.validate_response(second_call)
        self.assertTrue(is_valid)
        
        # SEO normalization
        seo_raw = json.loads(mock_generate())
        seo_normalized = SEOSchemaGate.coerce_and_fill(seo_raw)
        
        # Verify normalization worked
        self.assertIsInstance(seo_normalized["tags"], list)
        self.assertEqual(seo_normalized["tags"], ["python", "advanced", "programming"])
        self.assertIn("slug", seo_normalized)
        self.assertIn("seoTitle", seo_normalized)
        self.assertIn("description", seo_normalized)
        
        # Content generation
        content = mock_generate()
        self.assertIn("Introduction", content)
        
        # Verify we used all 4 mock responses (1 rejected + 3 successful)
        self.assertEqual(mock_generate.call_count, 4)


class TestCriticalPaths(unittest.TestCase):
    """Test critical execution paths that caused failures."""
    
    def test_prerequisites_keyerror_fix(self):
        """Test the specific prerequisites KeyError is fixed."""
        # This was the reported error
        frontmatter_data = {
            "title": "Test Article",
            "seoTitle": "Test Article - Guide",
            "description": "Test description",
            "tags": ["test"],
            "keywords": ["test"],
            "slug": "test-article"
            # Note: prerequisites is missing
        }
        
        # Should not raise KeyError
        normalized_prereqs = PrerequisitesNormalizer.normalize(
            frontmatter_data.get("prerequisites")  # Returns None
        )
        self.assertEqual(normalized_prereqs, [])
    
    def test_pytrends_400_handling(self):
        """Test PyTrends 400 error doesn't break execution."""
        guard = PyTrendsGuard(max_retries=2, backoff=1.0)
        
        def failing_fetch(query):
            raise Exception("400 Bad Request")
        
        # Should return fallback, not raise
        result = guard.safe_fetch("test query", failing_fetch)
        self.assertIsNotNone(result)
        self.assertEqual(result["note"], "fallback_due_to_error")
    
    def test_untitled_topic_handling(self):
        """Test handling of 'untitled-topic' slug generation."""
        # Empty topic
        result = TopicIdentificationFallback.ensure_topic({})
        self.assertEqual(result["slug"], "untitled-topic")
        
        # None topic
        result = TopicIdentificationFallback.ensure_topic(None)
        self.assertEqual(result["slug"], "untitled-topic")
    
    def test_gemini_placeholder_response(self):
        """Test Gemini placeholder responses are rejected."""
        mock_responses = [
            "Compelling content about {{topic}}",
            "Your Optimized Title Here",
            "TODO: Generate introduction",
            "..."
        ]
        
        gate = NoMockGate()
        for response in mock_responses:
            is_valid, _ = gate.validate_response(response)
            self.assertFalse(is_valid, f"Should reject: {response}")


if __name__ == '__main__':
    unittest.main()
