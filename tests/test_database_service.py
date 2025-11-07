"""Test Suite for Database Service - Lazy Collection Creation"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.services import DatabaseService, EmbeddingService
from src.core.config import Config


class TestDatabaseLazyInitialization(unittest.TestCase):
    """Test that database collections are created lazily, not at startup."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.config = Config()
        self.config.chroma_db_path = Path(self.test_dir) / "chroma_db"
        
        # Mock embedding service
        self.mock_embedding = Mock(spec=EmbeddingService)
        self.mock_embedding.encode.return_value = [[0.1] * 384]  # Mock embeddings
    
    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir and Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)
    
    @patch('src.services.services.HAS_CHROMADB', True)
    @patch('src.services.services.chromadb')
    def test_no_collections_created_at_startup(self, mock_chromadb):
        """Test that no collections are created when DatabaseService is initialized."""
        # Create mock client
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client
        
        # Initialize database service
        db_service = DatabaseService(self.config, self.mock_embedding)
        
        # Verify no collections were created at startup
        self.assertEqual(len(db_service.collections), 0, "Collections should not be created at startup")
        
        # Verify base path is set but no collections
        self.assertIsNotNone(db_service.db_base_path)
        self.assertEqual(len(db_service.clients), 0, "No clients should be created at startup")
    
    @patch('src.services.services.HAS_CHROMADB', True)
    @patch('src.services.services.chromadb')
    def test_collections_created_on_demand(self, mock_chromadb):
        """Test that collections are created only when actually needed."""
        # Create mock client and collection
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_client.get_collection.side_effect = ValueError("Collection doesn't exist")
        mock_client.create_collection.return_value = mock_collection
        
        # Initialize database service
        db_service = DatabaseService(self.config, self.mock_embedding)
        
        # Verify no collections at start
        self.assertEqual(len(db_service.collections), 0)
        
        # Add documents - should create collection on demand
        db_service.add_documents(
            source="kb",
            documents=["test document"],
            metadatas=[{"source": "test"}],
            family="barcode"
        )
        
        # Verify collection was created for barcode family
        self.assertIn("kb-barcode", db_service.collections)
        self.assertIn("blog-barcode", db_service.collections)
        self.assertIn("api-barcode", db_service.collections)
        
        # Verify general collections were NOT created
        self.assertNotIn("kb-general", db_service.collections)
        self.assertNotIn("blog-general", db_service.collections)
        self.assertNotIn("api-general", db_service.collections)
    
    def test_hashlib_import_in_embedding(self):
        """Test that hashlib is properly imported in EmbeddingService.encode."""
        embedding_service = EmbeddingService(self.config)
        
        # This should not raise UnboundLocalError
        try:
            result = embedding_service.encode(["test text"])
            # Should return a list of embeddings
            self.assertIsInstance(result, list)
        except UnboundLocalError as e:
            self.fail(f"hashlib import issue not fixed: {e}")


class TestOllamaFallback(unittest.TestCase):
    """Test Ollama fallback to other providers."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = Config()
        self.config.llm_provider = "OLLAMA"
        self.config.ollama_base_url = "http://localhost:11434"
        self.config.gemini_api_key = "test-key"
        self.config.llm_temperature = 0.7
        self.config.llm_top_p = 0.95
        self.config.llm_max_tokens = 1000
        self.config.global_seed = 42
        self.config.deterministic = False
        self.config.cache_dir = Path(tempfile.mkdtemp()) / "cache"
        self.config.gemini_rpm_limit = 60
    
    def tearDown(self):
        """Clean up."""
        if hasattr(self.config, 'cache_dir') and self.config.cache_dir.parent.exists():
            shutil.rmtree(self.config.cache_dir.parent)
    
    @patch('src.services.services.requests')
    @patch('src.services.services.genai')
    def test_ollama_fallback_to_gemini(self, mock_genai, mock_requests):
        """Test that when Ollama fails, it falls back to Gemini."""
        from src.services.services import LLMService
        
        # Mock Ollama failure
        mock_requests.post.side_effect = Exception("Connection refused")
        
        # Mock Gemini success
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Generated content from Gemini"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.GenerationConfig = MagicMock()
        
        # Create LLM service
        llm_service = LLMService(self.config)
        
        # Generate text - should fallback to Gemini
        result = llm_service.generate(
            prompt="Test prompt",
            system_prompt="System prompt"
        )
        
        # Verify Gemini was called after Ollama failed
        self.assertEqual(result, "Generated content from Gemini")
        mock_genai.GenerativeModel.assert_called()


class TestCriticalPaths(unittest.TestCase):
    """Test critical execution paths."""
    
    def test_embedding_encode_returns_list(self):
        """Test that EmbeddingService.encode always returns a list."""
        config = Config()
        embedding_service = EmbeddingService(config)
        
        # Test with empty list
        result = embedding_service.encode([])
        self.assertEqual(result, [])
        
        # Test with actual texts (will use fallback embeddings)
        result = embedding_service.encode(["text1", "text2"])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
    
    def test_family_detection_from_path(self):
        """Test family detection from file paths."""
        from src.core.config import Config
        
        config = Config()
        
        # Test barcode family detection
        barcode_path = Path("D:/content/kb.aspose.net/barcode/en/2d-barcode-writer")
        family = config.detect_family_from_path(barcode_path)
        self.assertEqual(family, "barcode")
        
        # Test words family detection
        words_path = Path("/content/kb.aspose.net/words/java/document")
        family = config.detect_family_from_path(words_path)
        self.assertEqual(family, "words")
    
    def test_lazy_database_initialization_workflow(self):
        """Test complete workflow with lazy database initialization."""
        config = Config()
        config.chroma_db_path = Path(tempfile.mkdtemp()) / "chroma_db"
        
        # Mock embedding service
        mock_embedding = Mock(spec=EmbeddingService)
        mock_embedding.encode.return_value = [[0.1] * 384]
        
        with patch('src.services.services.HAS_CHROMADB', True):
            with patch('src.services.services.chromadb') as mock_chromadb:
                # Setup mocks
                mock_client = MagicMock()
                mock_collection = MagicMock()
                mock_chromadb.PersistentClient.return_value = mock_client
                mock_client.get_collection.side_effect = ValueError("Collection doesn't exist")
                mock_client.create_collection.return_value = mock_collection
                
                # Create database service
                db_service = DatabaseService(config, mock_embedding)
                
                # No collections at start
                self.assertEqual(len(db_service.collections), 0)
                
                # First job with barcode family
                db_service.add_documents("kb", ["doc1"], family="barcode")
                self.assertIn("kb-barcode", db_service.collections)
                
                # Second job with pdf family
                db_service.add_documents("api", ["doc2"], family="pdf")
                self.assertIn("api-pdf", db_service.collections)
                
                # Verify no general collections were created
                self.assertNotIn("kb-general", db_service.collections)
        
        # Cleanup
        if config.chroma_db_path.parent.exists():
            shutil.rmtree(config.chroma_db_path.parent)


if __name__ == '__main__':
    unittest.main()
