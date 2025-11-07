"""Test Suite for JSON Repair Functionality

Tests the JSON repair utility and its integration with agents.
"""

import unittest
import json
from unittest.mock import Mock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.json_repair import JSONRepair, safe_json_loads
from src.agents.research.topic_identification import TopicIdentificationAgent
from src.agents.seo.seo_metadata import SEOMetadataAgent
from src.agents.content.outline_creation import OutlineCreationAgent
from src.core import Config, EventBus, AgentEvent


class TestJSONRepair(unittest.TestCase):
    """Test JSON repair utility."""
    
    def test_valid_json(self):
        """Test that valid JSON passes through unchanged."""
        valid_json = '{"title": "Test", "value": 123}'
        result = JSONRepair.repair(valid_json)
        self.assertEqual(result, {"title": "Test", "value": 123})
    
    def test_unterminated_string(self):
        """Test repair of unterminated strings."""
        # This mimics the actual error from the logs
        malformed = '''
        {
            "topics": [
                {
                    "title": "How to Generate QR Codes in C#",
                    "description": "A comprehensive guide on creating QR codes using C# and Aspose.BarCode
                }
            ]
        }
        '''
        result = JSONRepair.repair(malformed)
        self.assertIsNotNone(result)
        self.assertIn("topics", result)
        self.assertEqual(len(result["topics"]), 1)
    
    def test_missing_closing_quote(self):
        """Test repair of missing closing quotes."""
        malformed = '{"title": "Test Title", "description": "This is a test'
        result = JSONRepair.repair(malformed)
        self.assertEqual(result["title"], "Test Title")
        self.assertEqual(result["description"], "This is a test")
    
    def test_trailing_comma(self):
        """Test repair of trailing commas."""
        malformed = '{"title": "Test", "value": 123,}'
        result = JSONRepair.repair(malformed)
        self.assertEqual(result, {"title": "Test", "value": 123})
    
    def test_missing_comma(self):
        """Test repair of missing commas between elements."""
        malformed = '''
        {
            "title": "Test"
            "description": "Description"
        }
        '''
        result = JSONRepair.repair(malformed)
        self.assertIn("title", result)
        self.assertIn("description", result)
    
    def test_unbalanced_brackets(self):
        """Test repair of unbalanced brackets."""
        malformed = '{"items": ["item1", "item2"'
        result = JSONRepair.repair(malformed)
        self.assertIn("items", result)
        self.assertEqual(len(result["items"]), 2)
    
    def test_mixed_issues(self):
        """Test repair of JSON with multiple issues."""
        malformed = '''
        {
            "title": "Test Title
            "tags": ["tag1", "tag2",
            "keywords": ["key1" "key2"]
            "value": 123,
        '''
        result = JSONRepair.repair(malformed)
        self.assertIn("title", result)
        self.assertIn("tags", result)
        self.assertIn("keywords", result)
    
    def test_extraction_from_garbage(self):
        """Test extraction of JSON from text with extra content."""
        text_with_json = '''
        Here is some text before the JSON:
        
        ```json
        {"title": "Extracted Title", "value": 42}
        ```
        
        And some text after.
        '''
        result = JSONRepair.repair(text_with_json)
        self.assertEqual(result["title"], "Extracted Title")
        self.assertEqual(result["value"], 42)
    
    def test_safe_default(self):
        """Test that completely malformed input returns safe default."""
        garbage = "This is not JSON at all!"
        result = JSONRepair.repair(garbage)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
    
    def test_safe_json_loads(self):
        """Test the safe_json_loads wrapper function."""
        # Valid JSON
        result = safe_json_loads('{"test": true}')
        self.assertEqual(result, {"test": True})
        
        # Malformed JSON with default
        result = safe_json_loads('invalid json', default={"fallback": True})
        self.assertEqual(result, {"fallback": True})
        
        # Malformed JSON without default
        result = safe_json_loads('invalid json')
        self.assertIsInstance(result, dict)


class TestAgentJSONHandling(unittest.TestCase):
    """Test that agents handle malformed JSON correctly."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = Config()
        self.event_bus = EventBus()
    
    @patch('src.agents.research.topic_identification.LLMService')
    def test_topic_identification_handles_malformed_json(self, mock_llm):
        """Test TopicIdentificationAgent handles malformed JSON."""
        # Setup mock to return malformed JSON (unterminated string)
        mock_llm_instance = Mock()
        mock_llm_instance.generate.return_value = '''
        {
            "topics": [
                {
                    "title": "QR Code Generation",
                    "description": "Learn how to generate QR codes in C#
                }
            ]
        }
        '''
        mock_llm.return_value = mock_llm_instance
        
        # Create agent
        agent = TopicIdentificationAgent(
            config=self.config,
            event_bus=self.event_bus,
            llm_service=mock_llm_instance
        )
        
        # Execute with test event
        event = AgentEvent(
            event_type="test",
            data={"context": "test context"},
            source_agent="test",
            correlation_id="test-123"
        )
        
        # Should not raise JSONDecodeError
        result = agent.execute(event)
        self.assertIsNotNone(result)
        self.assertIn("topics", result.data)
    
    @patch('src.agents.seo.seo_metadata.TrendsService')
    @patch('src.agents.seo.seo_metadata.LLMService')
    def test_seo_metadata_handles_malformed_json(self, mock_llm, mock_trends):
        """Test SEOMetadataAgent handles malformed JSON."""
        # Setup mocks
        mock_llm_instance = Mock()
        mock_llm_instance.generate.return_value = '''
        {
            "title": "Test Title",
            "seoTitle": "SEO Title
            "description": "Test description",
            "tags": ["tag1", "tag2"
        '''
        mock_llm.return_value = mock_llm_instance
        
        mock_trends_instance = Mock()
        mock_trends_instance.format_for_prompt.return_value = ""
        mock_trends.return_value = mock_trends_instance
        
        # Create agent
        agent = SEOMetadataAgent(
            config=self.config,
            event_bus=self.event_bus,
            llm_service=mock_llm_instance,
            trends_service=mock_trends_instance
        )
        
        # Execute with test event
        event = AgentEvent(
            event_type="test",
            data={"content": "test content", "topic": {"title": "Test"}},
            source_agent="test",
            correlation_id="test-456"
        )
        
        # Should not raise JSONDecodeError
        result = agent.execute(event)
        self.assertIsNotNone(result)
    
    @patch('src.agents.content.outline_creation.LLMService')
    def test_outline_creation_handles_malformed_json(self, mock_llm):
        """Test OutlineCreationAgent handles malformed JSON."""
        # Setup mock
        mock_llm_instance = Mock()
        mock_llm_instance.generate.return_value = '''
        {
            "outline": {
                "sections": [
                    {"title": "Introduction", "description": "Intro text
                    {"title": "Main Content", "description": "Main text"}
                ]
            }
        '''
        mock_llm.return_value = mock_llm_instance
        
        # Create agent
        agent = OutlineCreationAgent(
            config=self.config,
            event_bus=self.event_bus,
            llm_service=mock_llm_instance
        )
        
        # Execute with test event
        event = AgentEvent(
            event_type="test",
            data={"topic": {"title": "Test Topic"}},
            source_agent="test",
            correlation_id="test-789"
        )
        
        # Should not raise JSONDecodeError
        result = agent.execute(event)
        self.assertIsNotNone(result)


class TestRealWorldScenarios(unittest.TestCase):
    """Test real-world JSON repair scenarios."""
    
    def test_gemini_response_with_markdown(self):
        """Test handling of Gemini responses wrapped in markdown."""
        gemini_response = '''```json
        {
            "title": "Python Best Practices",
            "seoTitle": "Python Best Practices - Complete Guide",
            "description": "Learn Python best practices
        }
        ```'''
        result = JSONRepair.repair(gemini_response)
        self.assertEqual(result["title"], "Python Best Practices")
        self.assertIn("description", result)
    
    def test_ollama_truncated_response(self):
        """Test handling of truncated Ollama responses."""
        truncated = '''
        {
            "topics": [
                {"title": "Topic 1", "description": "Description 1"},
                {"title": "Topic 2", "description": "Description 2"},
                {"title": "Topic 3", "descripti
        '''
        result = JSONRepair.repair(truncated)
        self.assertIn("topics", result)
        self.assertIsInstance(result["topics"], list)
    
    def test_nested_json_with_errors(self):
        """Test handling of nested JSON with multiple errors."""
        nested_malformed = '''
        {
            "metadata": {
                "title": "Main Title",
                "author": "John Doe
            },
            "sections": [
                {
                    "id": 1,
                    "title": "Section 1
                    "content": "Content 1"
                },
                {
                    "id": 2
                    "title": "Section 2",
                    "content": "Content 2",
                }
            ],
        }
        '''
        result = JSONRepair.repair(nested_malformed)
        self.assertIn("metadata", result)
        self.assertIn("sections", result)
    
    def test_array_response(self):
        """Test handling of array responses with errors."""
        array_malformed = '''
        [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2
            {"id": 3, "name": "Item 3"}
        '''
        result = JSONRepair.repair(array_malformed)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
    
    def test_mixed_quotes_and_escapes(self):
        """Test handling of mixed quotes and escape sequences."""
        mixed = '''
        {
            "title": "Test \\"Title\\" with quotes",
            "description": "Line 1\\nLine 2
            "code": "print(\\"Hello World\\")"
        }
        '''
        result = JSONRepair.repair(mixed)
        self.assertIn("title", result)
        self.assertIn("code", result)


if __name__ == '__main__':
    unittest.main()
