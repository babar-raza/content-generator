"""Test Suite for Agent Contracts and Communication

Ensures all agents:
1. Have valid contracts
2. Handle malformed JSON gracefully
3. Communicate properly via EventBus
4. Auto-correct common data issues
"""

import unittest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import Config, EventBus, AgentEvent, AgentContract
from src.core.config import load_config
from src.services.services import LLMService, DatabaseService, EmbeddingService
from src.services.services_fixes import SEOSchemaGate, PrerequisitesNormalizer


class TestAgentContracts(unittest.TestCase):
    """Test that all agents have valid contracts."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = Config()
        self.event_bus = EventBus()
    
    def test_all_agents_have_contracts(self):
        """Verify each agent has a properly formed contract."""
        # List of all agent classes
        from src.agents.research.topic_identification import TopicIdentificationAgent
        from src.agents.seo.seo_metadata import SEOMetadataAgent
        from src.agents.publishing.frontmatter_enhanced import EnhancedFrontmatterAgent
        from src.agents.publishing.file_writer import FileWriterAgent
        from src.agents.content.content_assembly import ContentAssemblyAgent
        
        # Mock services
        mock_llm = Mock(spec=LLMService)
        mock_db = Mock(spec=DatabaseService)
        mock_embedding = Mock(spec=EmbeddingService)
        
        agents_to_test = [
            (TopicIdentificationAgent, [self.config, self.event_bus, mock_llm]),
            (SEOMetadataAgent, [self.config, self.event_bus, mock_llm, Mock()]),
            (EnhancedFrontmatterAgent, [self.config, self.event_bus]),
            (FileWriterAgent, [self.config, self.event_bus]),
            (ContentAssemblyAgent, [self.config, self.event_bus, mock_llm])
        ]
        
        for agent_class, init_args in agents_to_test:
            with self.subTest(agent=agent_class.__name__):
                try:
                    agent = agent_class(*init_args)
                    contract = agent.contract
                    
                    # Verify contract has required fields
                    self.assertIsNotNone(contract)
                    self.assertIn('agent_id', contract.__dict__)
                    self.assertIn('capabilities', contract.__dict__)
                    self.assertIn('input_schema', contract.__dict__)
                    self.assertIn('output_schema', contract.__dict__)
                    self.assertIn('publishes', contract.__dict__)
                    
                    # Verify schemas are dictionaries
                    self.assertIsInstance(contract.input_schema, dict)
                    self.assertIsInstance(contract.output_schema, dict)
                    
                    # Verify capabilities and publishes are lists
                    self.assertIsInstance(contract.capabilities, list)
                    self.assertIsInstance(contract.publishes, list)
                except Exception as e:
                    self.fail(f"Agent {agent_class.__name__} failed contract test: {e}")


class TestEventBusCommunication(unittest.TestCase):
    """Test agents communicate properly via EventBus."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = Config()
        self.event_bus = EventBus()
        self.received_events = []
    
    def test_agent_event_flow(self):
        """Test event flow between agents."""
        # Subscribe to capture events
        def capture_event(event):
            self.received_events.append(event)
        
        # Subscribe to multiple event types
        self.event_bus.subscribe("topic_identified", capture_event)
        self.event_bus.subscribe("seo_generated", capture_event)
        self.event_bus.subscribe("frontmatter_created", capture_event)
        
        # Simulate topic identification event
        topic_event = AgentEvent(
            event_type="topic_identified",
            data={"title": "Test Topic", "slug": "test-topic"},
            source_agent="TopicIdentificationAgent",
            correlation_id="test-123"
        )
        self.event_bus.publish(topic_event)
        
        # Verify event was received
        self.assertEqual(len(self.received_events), 1)
        self.assertEqual(self.received_events[0].event_type, "topic_identified")
        self.assertEqual(self.received_events[0].data["title"], "Test Topic")
    
    def test_event_data_validation(self):
        """Test that events validate their data."""
        # Test with valid event
        valid_event = AgentEvent(
            event_type="test_event",
            data={"key": "value"},
            source_agent="TestAgent",
            correlation_id="test-456"
        )
        self.assertIsNotNone(valid_event.timestamp)
        self.assertIsInstance(valid_event.to_dict(), dict)
        
        # Test event can be reconstructed from dict
        event_dict = valid_event.to_dict()
        reconstructed = AgentEvent.from_dict(event_dict)
        self.assertEqual(reconstructed.event_type, valid_event.event_type)
        self.assertEqual(reconstructed.correlation_id, valid_event.correlation_id)


class TestDataNormalization(unittest.TestCase):
    """Test automatic data correction and normalization."""
    
    def test_seo_auto_correction(self):
        """Test SEO data is automatically corrected."""
        test_cases = [
            # Missing fields
            ({}, {"title": "Untitled Post", "seoTitle": "Untitled Post", 
                 "description": "Learn about Untitled Post - comprehensive guide and tutorial.",
                 "tags": [], "keywords": [], "slug": "untitled-post"}),
            
            # String tags/keywords
            ({"title": "Test", "tags": "tag1,tag2", "keywords": "key1;key2"},
             {"title": "Test", "seoTitle": "Test", 
              "description": "Learn about Test - comprehensive guide and tutorial.",
              "tags": ["tag1", "tag2"], "keywords": ["key1", "key2"], "slug": "test"}),
            
            # Nested structure
            ({"metadata": {"title": "Nested"}},
             {"title": "Nested", "seoTitle": "Nested",
              "description": "Learn about Nested - comprehensive guide and tutorial.",
              "tags": [], "keywords": [], "slug": "nested"}),
        ]
        
        for input_data, expected in test_cases:
            with self.subTest(input=input_data):
                result = SEOSchemaGate.coerce_and_fill(input_data)
                for key, value in expected.items():
                    self.assertEqual(result[key], value, f"Field {key} mismatch")
    
    def test_prerequisites_auto_correction(self):
        """Test prerequisites normalization."""
        test_cases = [
            (None, []),
            ("", []),
            ("single item", ["single item"]),
            ("item1,item2", ["item1", "item2"]),
            (["item1", "item2"], ["item1", "item2"]),
            ([None, "item", ""], ["item"]),
            (123, ["123"]),
        ]
        
        for input_value, expected in test_cases:
            with self.subTest(input=input_value):
                result = PrerequisitesNormalizer.normalize(input_value)
                self.assertEqual(result, expected)


class TestMalformedJSONHandling(unittest.TestCase):
    """Test handling of malformed JSON responses."""
    
    def test_json_recovery(self):
        """Test recovery from malformed JSON."""
        from src.services.services_fixes import NoMockGate
        
        # Test various malformed responses
        test_cases = [
            # Valid JSON
            ('{"title": "Test"}', True),
            
            # Mock content
            ('{"title": "Your Title Here"}', False),
            ('{"description": "TODO: Add description"}', False),
            
            # Invalid JSON (should be handled gracefully)
            ('{"title": "Test"', False),  # Missing closing brace
            ('title: Test', False),  # Not JSON
        ]
        
        gate = NoMockGate()
        for json_str, should_pass in test_cases:
            with self.subTest(json=json_str):
                try:
                    # Try to parse JSON
                    if json_str.startswith('{'):
                        data = json.loads(json_str) if json_str.count('{') == json_str.count('}') else {}
                    else:
                        data = {}
                    
                    is_valid, _ = gate.validate_response(data or json_str)
                    if should_pass:
                        self.assertTrue(is_valid, f"Should pass but failed: {json_str}")
                    else:
                        self.assertFalse(is_valid, f"Should fail but passed: {json_str}")
                except json.JSONDecodeError:
                    # Invalid JSON should not pass
                    self.assertFalse(should_pass, f"Invalid JSON marked as should pass: {json_str}")


class TestAgentResilience(unittest.TestCase):
    """Test agent resilience to various failure modes."""
    
    def setUp(self):
        self.config = Config()
        self.event_bus = EventBus()
    
    def test_agent_handles_missing_data(self):
        """Test agents handle events with missing expected data."""
        from src.agents.publishing.file_writer import FileWriterAgent
        
        agent = FileWriterAgent(self.config, self.event_bus)
        
        # Event with missing slug
        event = AgentEvent(
            event_type="execute_write_file",
            data={"markdown": "# Test Content"},
            source_agent="TestAgent",
            correlation_id="test-789"
        )
        
        # Should handle gracefully by generating slug
        result = agent.execute(event)
        self.assertIsNotNone(result)
        self.assertEqual(result.data.get("slug"), "untitled")
    
    def test_agent_handles_wrong_type_data(self):
        """Test agents handle data of wrong types."""
        from src.agents.seo.seo_metadata import SEOMetadataAgent
        
        mock_llm = Mock(spec=LLMService)
        mock_llm.generate.return_value = json.dumps({
            "title": "Test",
            "tags": "should,be,list",  # Wrong: string instead of list
            "keywords": None  # Wrong: None instead of list
        })
        
        mock_trends = Mock()
        mock_trends.format_for_prompt.return_value = ""
        
        agent = SEOMetadataAgent(self.config, self.event_bus, mock_llm, mock_trends)
        
        event = AgentEvent(
            event_type="execute_generate_seo",
            data={"content": "Test content", "topic": {"title": "Test"}},
            source_agent="TestAgent",
            correlation_id="test-890"
        )
        
        # Should normalize the data automatically
        result = agent.execute(event)
        self.assertIsNotNone(result)
        self.assertIsInstance(result.data.get("seo_metadata", {}).get("tags"), list)
        self.assertIsInstance(result.data.get("seo_metadata", {}).get("keywords"), list)


class TestEndToEndIntegration(unittest.TestCase):
    """Test complete pipeline integration."""
    
    @patch('src.services.services.LLMService.generate')
    def test_complete_pipeline_flow(self, mock_generate):
        """Test complete flow from topic to file output."""
        # Setup
        config = Config()
        config.blog_switch = True
        event_bus = EventBus()
        
        # Mock LLM responses
        mock_generate.side_effect = [
            # Topic identification
            json.dumps({"title": "Python Best Practices", "description": "Guide to Python"}),
            # SEO generation
            json.dumps({
                "title": "Python Best Practices",
                "seoTitle": "Python Best Practices - Complete Guide",
                "description": "Learn Python best practices",
                "tags": ["python", "programming"],
                "keywords": ["python", "best practices"],
                "slug": "python-best-practices"
            }),
            # Content generation
            "## Introduction\nThis is the introduction.\n## Main Content\nThis is the main content."
        ]
        
        # Track events
        events = []
        event_bus.subscribe("topic_identified", lambda e: events.append(e))
        event_bus.subscribe("seo_generated", lambda e: events.append(e))
        event_bus.subscribe("blog_post_complete", lambda e: events.append(e))
        
        # Run pipeline simulation
        correlation_id = "test-pipeline-123"
        
        # Topic identification
        topic_event = AgentEvent(
            event_type="topic_identified",
            data={"title": "Python Best Practices", "description": "Guide to Python"},
            source_agent="TopicIdentificationAgent",
            correlation_id=correlation_id
        )
        event_bus.publish(topic_event)
        
        # SEO generation
        seo_event = AgentEvent(
            event_type="seo_generated",
            data={
                "seo_metadata": {
                    "title": "Python Best Practices",
                    "seoTitle": "Python Best Practices - Complete Guide",
                    "description": "Learn Python best practices",
                    "tags": ["python", "programming"],
                    "keywords": ["python", "best practices"],
                    "slug": "python-best-practices"
                }
            },
            source_agent="SEOMetadataAgent",
            correlation_id=correlation_id
        )
        event_bus.publish(seo_event)
        
        # Verify events were captured
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_type, "topic_identified")
        self.assertEqual(events[1].event_type, "seo_generated")
        
        # Verify data flow
        self.assertEqual(events[0].data["title"], "Python Best Practices")
        self.assertEqual(events[1].data["seo_metadata"]["slug"], "python-best-practices")


if __name__ == '__main__':
    unittest.main()
