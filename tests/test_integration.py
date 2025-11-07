"""System Integration Tests - Complete Pipeline Testing"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import Config, EventBus, AgentEvent
from src.services.services import LLMService, DatabaseService, EmbeddingService
from src.services.services_fixes import (
    NoMockGate, SEOSchemaGate, PrerequisitesNormalizer,
    PyTrendsGuard, TopicIdentificationFallback,
    BlogSwitchPolicy, RunToResultGuarantee
)
from src.engine.slug_service import slugify


class TestCompletePipeline(unittest.TestCase):
    """Test complete pipeline execution with all fixes."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.config = Config()
        self.config.output_dir = Path(self.test_dir) / "output"
        self.config.chroma_db_path = Path(self.test_dir) / "chroma_db"
        self.config.cache_dir = Path(self.test_dir) / "cache"
        self.config.blog_switch = True
        self.config.llm_provider = "GEMINI"
        self.config.gemini_api_key = "test-key"
        self.config.gemini_rpm_limit = 60
        self.config.llm_temperature = 0.7
        self.config.llm_top_p = 0.95
        self.config.llm_max_tokens = 1000
        self.config.global_seed = 42
        self.config.deterministic = False
        self.config.pytrends_max_retries = 3
        self.config.pytrends_backoff = 2.0
        
        self.event_bus = EventBus()
    
    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir and Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)
    
    @patch('src.services.services.HAS_CHROMADB', True)
    @patch('src.services.services.chromadb')
    def test_database_lazy_creation_in_pipeline(self, mock_chromadb):
        """Test that database collections are created lazily during pipeline execution."""
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_collection.side_effect = ValueError("Collection doesn't exist")
        mock_client.create_collection.return_value = mock_collection
        mock_collection.add = MagicMock()
        
        # Create services
        embedding_service = EmbeddingService(self.config)
        db_service = DatabaseService(self.config, embedding_service)
        
        # Verify no collections at start
        self.assertEqual(len(db_service.collections), 0, "Should start with no collections")
        
        # Simulate ingestion for barcode family
        from src.agents.ingestion.kb_ingestion import KBIngestionAgent
        
        # Mock the agent dependencies
        with patch.object(KBIngestionAgent, 'execute') as mock_execute:
            mock_execute.return_value = AgentEvent(
                event_type="kb_ingested",
                data={"files_processed": 10, "family": "barcode"},
                source_agent="KBIngestionAgent",
                correlation_id="test-123"
            )
            
            # Create agent
            agent = KBIngestionAgent(
                config=self.config,
                event_bus=self.event_bus,
                database_service=db_service,
                embedding_service=embedding_service
            )
            
            # Simulate adding documents
            db_service.add_documents(
                source="kb",
                documents=["test document"],
                family="barcode"
            )
            
            # Verify barcode collections were created
            self.assertIn("kb-barcode", db_service.collections)
            
            # Verify general collections were NOT created
            self.assertNotIn("kb-general", db_service.collections)
    
    def test_no_mock_gate_integration(self):
        """Test NO-MOCK gate integration in the pipeline."""
        gate = NoMockGate()
        
        # Test various mock responses that should be rejected
        mock_responses = [
            {"title": "Your Title Here", "description": "TODO: Add description"},
            {"content": "Lorem ipsum dolor sit amet"},
            {"text": "[PLACEHOLDER]"},
            {"summary": "..."}
        ]
        
        for response in mock_responses:
            is_valid, reason = gate.validate_response(response)
            self.assertFalse(is_valid, f"Should reject mock content: {response}")
            self.assertIn("mock", reason.lower())
        
        # Test valid responses
        valid_responses = [
            {"title": "Python Best Practices", "description": "Learn Python coding standards"},
            {"content": "This is real content about programming"},
        ]
        
        for response in valid_responses:
            is_valid, _ = gate.validate_response(response)
            self.assertTrue(is_valid, f"Should accept valid content: {response}")
    
    def test_seo_normalization_integration(self):
        """Test SEO normalization in the pipeline."""
        # Test with incomplete/malformed SEO data
        test_cases = [
            # Empty input
            ({}, {
                "title": "Untitled Post",
                "seoTitle": "Untitled Post",
                "description": "Learn about Untitled Post - comprehensive guide and tutorial.",
                "tags": [],
                "keywords": [],
                "slug": "untitled-post"
            }),
            
            # Missing slug
            ({"title": "Test Article"}, {
                "title": "Test Article",
                "seoTitle": "Test Article",
                "description": "Learn about Test Article - comprehensive guide and tutorial.",
                "tags": [],
                "keywords": [],
                "slug": "test-article"
            }),
            
            # String tags/keywords
            ({
                "title": "Guide",
                "tags": "python,coding",
                "keywords": "programming;development"
            }, {
                "title": "Guide",
                "seoTitle": "Guide",
                "description": "Learn about Guide - comprehensive guide and tutorial.",
                "tags": ["python", "coding"],
                "keywords": ["programming", "development"],
                "slug": "guide"
            })
        ]
        
        for input_data, expected in test_cases:
            result = SEOSchemaGate.coerce_and_fill(input_data)
            for key, value in expected.items():
                self.assertEqual(result[key], value, f"Mismatch in {key}")
    
    def test_prerequisites_normalization_integration(self):
        """Test prerequisites normalization in the pipeline."""
        test_cases = [
            (None, []),
            ("Basic knowledge", ["Basic knowledge"]),
            ("Python,JavaScript", ["Python", "JavaScript"]),
            (["React", None, "", "Node.js"], ["React", "Node.js"])
        ]
        
        for input_val, expected in test_cases:
            result = PrerequisitesNormalizer.normalize(input_val)
            self.assertEqual(result, expected)
    
    def test_blog_switch_path_generation(self):
        """Test blog switch generates correct paths."""
        # Test with blog ON
        self.config.blog_switch = True
        path = self.config.get_output_path("test-article")
        self.assertTrue(str(path).endswith("test-article/index.md"))
        
        # Test with blog OFF
        self.config.blog_switch = False
        path = self.config.get_output_path("test-article")
        self.assertTrue(str(path).endswith("test-article.md"))
    
    def test_pytrends_fallback_integration(self):
        """Test PyTrends fallback mechanism."""
        guard = PyTrendsGuard(max_retries=2, backoff=0.1)
        
        def failing_fetch(query):
            raise Exception("API Error 400")
        
        # Should return fallback without crashing
        result = guard.safe_fetch("test query", failing_fetch)
        self.assertIsNotNone(result)
        self.assertEqual(result["note"], "fallback_due_to_error")
        self.assertEqual(result["score"], 50)
    
    def test_topic_fallback_integration(self):
        """Test topic identification fallback."""
        # Empty topic
        result = TopicIdentificationFallback.ensure_topic({})
        self.assertEqual(result["title"], "Untitled Topic")
        self.assertEqual(result["slug"], "untitled-topic")
        
        # Topic with name but no title
        result = TopicIdentificationFallback.ensure_topic({"name": "My Topic"})
        self.assertEqual(result["title"], "My Topic")
        self.assertEqual(result["slug"], "my-topic")
    
    def test_minimal_document_generation(self):
        """Test minimal document generation on failure."""
        doc = RunToResultGuarantee.create_minimal_document(
            topic="Fallback Topic",
            slug="fallback-topic"
        )
        
        # Verify structure
        self.assertIn("---", doc)  # Frontmatter delimiters
        self.assertIn('"title": "Fallback Topic"', doc)
        self.assertIn('"slug": "fallback-topic"', doc)
        self.assertIn('"prerequisites": []', doc)
        self.assertIn('"draft": true', doc)
        self.assertIn("# Fallback Topic", doc)
    
    @patch('src.services.services.requests')
    @patch('src.services.services.genai')
    def test_ollama_to_gemini_fallback(self, mock_genai, mock_requests):
        """Test Ollama fallback to Gemini."""
        # Configure for Ollama with Gemini fallback
        self.config.llm_provider = "OLLAMA"
        self.config.ollama_base_url = "http://localhost:11434"
        
        # Mock Ollama failure
        mock_requests.post.side_effect = Exception("Connection refused")
        
        # Mock Gemini success
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "title": "Generated Title",
            "description": "Generated description"
        })
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.GenerationConfig = MagicMock()
        
        # Create LLM service
        from src.services.services import LLMService
        llm_service = LLMService(self.config)
        
        # Should fallback to Gemini
        result = llm_service.generate("Test prompt")
        self.assertIn("Generated Title", result)


class TestCriticalBugFixes(unittest.TestCase):
    """Test critical bug fixes."""
    
    def test_hashlib_import_fix(self):
        """Test that hashlib import issue is fixed."""
        config = Config()
        embedding_service = EmbeddingService(config)
        
        # This should not raise UnboundLocalError
        try:
            # Test with multiple texts to ensure caching logic works
            result = embedding_service.encode(["text1", "text2", "text3"])
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 3)
        except UnboundLocalError as e:
            self.fail(f"hashlib import not fixed: {e}")
    
    @patch('src.services.services.HAS_CHROMADB', True)
    @patch('src.services.services.chromadb')
    def test_no_general_db_at_startup(self, mock_chromadb):
        """Test that general database is not created at startup."""
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client
        
        config = Config()
        config.chroma_db_path = Path(tempfile.mkdtemp()) / "chroma_db"
        
        embedding_service = Mock(spec=EmbeddingService)
        db_service = DatabaseService(config, embedding_service)
        
        # Should have no collections at startup
        self.assertEqual(len(db_service.collections), 0)
        self.assertNotIn("kb-general", db_service.collections)
        self.assertNotIn("blog-general", db_service.collections)
        self.assertNotIn("api-general", db_service.collections)
        
        # Cleanup
        if config.chroma_db_path.parent.exists():
            shutil.rmtree(config.chroma_db_path.parent)
    
    def test_family_specific_collection_creation(self):
        """Test that family-specific collections are created on demand."""
        config = Config()
        config.chroma_db_path = Path(tempfile.mkdtemp()) / "chroma_db"
        
        with patch('src.services.services.HAS_CHROMADB', True):
            with patch('src.services.services.chromadb') as mock_chromadb:
                mock_client = MagicMock()
                mock_collection = MagicMock()
                mock_chromadb.PersistentClient.return_value = mock_client
                mock_client.get_collection.side_effect = ValueError("Collection doesn't exist")
                mock_client.create_collection.return_value = mock_collection
                
                embedding_service = Mock(spec=EmbeddingService)
                embedding_service.encode.return_value = [[0.1] * 384]
                
                db_service = DatabaseService(config, embedding_service)
                
                # Add documents for barcode family
                db_service.add_documents("kb", ["doc"], family="barcode")
                
                # Should create barcode collections, not general
                self.assertIn("kb-barcode", db_service.collections)
                self.assertNotIn("kb-general", db_service.collections)
        
        # Cleanup
        if config.chroma_db_path.parent.exists():
            shutil.rmtree(config.chroma_db_path.parent)


if __name__ == '__main__':
    unittest.main()
