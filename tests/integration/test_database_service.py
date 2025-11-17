"""Comprehensive tests for DatabaseService with VectorStore integration.

Tests add_documents, search, duplicate detection, and collection management
using mock ChromaDB client to avoid real database operations.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.fixtures.mock_chromadb import create_mock_client, create_mock_embedding_model
from src.core.config import Config, DatabaseConfig
from src.services.services import DatabaseService


@pytest.fixture
def mock_config():
    """Create mock configuration for testing.
    
    Returns:
        Config object with test settings
    """
    config = Config()
    config.database = DatabaseConfig()
    config.database.chroma_db_path = "./test_chroma_db"
    config.database.embedding_model = "all-MiniLM-L6-v2"
    config.database.collection_name = "test_collection"
    config.chroma_persist_directory = "./test_chroma_db"
    config.embedding_model = "all-MiniLM-L6-v2"
    return config


@pytest.fixture
def database_service(mock_config):
    """Create DatabaseService with mocked dependencies.
    
    Args:
        mock_config: Mock configuration
        
    Returns:
        DatabaseService instance with mocks (mocking handled by conftest.py)
    """
    service = DatabaseService(mock_config)
    return service


class TestDatabaseServiceInitialization:
    """Test DatabaseService initialization."""
    
    def test_initialization_success(self, database_service):
        """Test successful initialization."""
        assert database_service is not None
        assert database_service.vectorstore is not None
        assert database_service.client is not None
        assert database_service.collection_name == "test_collection"
    
    def test_initialization_without_chromadb(self, mock_config):
        """Test initialization fails without ChromaDB."""
        with patch('src.services.services.CHROMADB_AVAILABLE', False):
            with pytest.raises(ImportError, match="chromadb not available"):
                DatabaseService(mock_config)
    
    def test_client_exposed_for_backward_compatibility(self, database_service):
        """Test that client is exposed for backward compatibility."""
        assert database_service.client is not None
        assert database_service.client == database_service.vectorstore.client


class TestDatabaseServiceAddDocuments:
    """Test document addition functionality."""
    
    def test_add_single_document(self, database_service):
        """Test adding a single document."""
        documents = ["This is a test document"]
        metadatas = [{"source": "test"}]
        ids = ["doc1"]
        
        database_service.add_documents(documents, metadatas, ids)
        
        # Verify document was added
        collection = database_service.vectorstore.collection
        assert collection.count() == 1
        
        # Verify document can be retrieved
        result = collection.get(ids=["doc1"])
        assert len(result['ids']) == 1
        assert result['ids'][0] == "doc1"
        assert result['documents'][0] == "This is a test document"
    
    def test_add_multiple_documents(self, database_service):
        """Test adding multiple documents."""
        documents = [
            "First test document",
            "Second test document",
            "Third test document"
        ]
        metadatas = [
            {"source": "test", "index": 1},
            {"source": "test", "index": 2},
            {"source": "test", "index": 3}
        ]
        ids = ["doc1", "doc2", "doc3"]
        
        database_service.add_documents(documents, metadatas, ids)
        
        # Verify all documents were added
        collection = database_service.vectorstore.collection
        assert collection.count() == 3
        
        # Verify documents can be retrieved
        result = collection.get()
        assert len(result['ids']) == 3
        assert set(result['ids']) == {"doc1", "doc2", "doc3"}
    
    def test_add_documents_with_empty_metadata(self, database_service):
        """Test adding documents with missing metadata."""
        documents = ["Test document"]
        metadatas = []  # Empty metadata list
        ids = ["doc1"]
        
        database_service.add_documents(documents, metadatas, ids)
        
        # Verify document was added with empty metadata
        result = database_service.vectorstore.collection.get(ids=["doc1"])
        assert len(result['ids']) == 1
        assert result['metadatas'][0] == {}
    
    def test_add_documents_to_different_collection(self, database_service):
        """Test adding documents to a different collection."""
        documents = ["Test document"]
        metadatas = [{"source": "test"}]
        ids = ["doc1"]
        
        # Add to different collection
        database_service.add_documents(
            documents, metadatas, ids,
            collection_name="other_collection"
        )
        
        # Verify collection was switched
        assert database_service.vectorstore.collection.name == "other_collection"
        assert database_service.vectorstore.collection.count() == 1


class TestDatabaseServiceQuery:
    """Test query functionality."""
    
    def test_query_single_text(self, database_service):
        """Test querying with a single text."""
        # Add test documents
        documents = [
            "Machine learning is a subset of artificial intelligence",
            "Deep learning uses neural networks",
            "Python is a programming language"
        ]
        metadatas = [{"topic": "AI"}, {"topic": "AI"}, {"topic": "programming"}]
        ids = ["doc1", "doc2", "doc3"]
        
        database_service.add_documents(documents, metadatas, ids)
        
        # Query
        results = database_service.query(
            query_texts=["artificial intelligence"],
            n_results=2
        )
        
        # Verify results structure
        assert 'ids' in results
        assert 'documents' in results
        assert 'metadatas' in results
        assert 'distances' in results
        
        # Verify results format (ChromaDB format)
        assert len(results['ids']) == 1  # One query
        assert len(results['ids'][0]) <= 2  # Up to 2 results
        assert len(results['documents'][0]) == len(results['ids'][0])
    
    def test_query_multiple_texts(self, database_service):
        """Test querying with multiple texts."""
        # Add test documents
        documents = [
            "Machine learning algorithms",
            "Data science analytics",
            "Web development frameworks"
        ]
        metadatas = [{"type": "ML"}, {"type": "DS"}, {"type": "Web"}]
        ids = ["doc1", "doc2", "doc3"]
        
        database_service.add_documents(documents, metadatas, ids)
        
        # Query with multiple texts
        results = database_service.query(
            query_texts=["machine learning", "web development"],
            n_results=2
        )
        
        # Verify results for both queries
        assert len(results['ids']) == 2  # Two queries
        assert all(len(ids) <= 2 for ids in results['ids'])  # Up to 2 results each
    
    def test_query_with_metadata_filter(self, database_service):
        """Test querying with metadata filter."""
        # Add test documents
        documents = [
            "Python tutorial",
            "Java tutorial",
            "Python advanced"
        ]
        metadatas = [
            {"language": "python", "level": "beginner"},
            {"language": "java", "level": "beginner"},
            {"language": "python", "level": "advanced"}
        ]
        ids = ["doc1", "doc2", "doc3"]
        
        database_service.add_documents(documents, metadatas, ids)
        
        # Query with filter
        results = database_service.query(
            query_texts=["tutorial"],
            n_results=5,
            where={"language": "python"}
        )
        
        # Verify only Python documents returned
        assert len(results['ids'][0]) == 2  # Only Python documents
        for metadata in results['metadatas'][0]:
            assert metadata['language'] == "python"
    
    def test_query_empty_collection(self, database_service):
        """Test querying an empty collection."""
        results = database_service.query(
            query_texts=["test query"],
            n_results=5
        )
        
        # Verify empty results
        assert len(results['ids'][0]) == 0
        assert len(results['documents'][0]) == 0
    
    def test_query_with_custom_n_results(self, database_service):
        """Test querying with custom result limit."""
        # Add more documents
        documents = [f"Document {i}" for i in range(10)]
        metadatas = [{"index": i} for i in range(10)]
        ids = [f"doc{i}" for i in range(10)]
        
        database_service.add_documents(documents, metadatas, ids)
        
        # Query with limit
        results = database_service.query(
            query_texts=["document"],
            n_results=3
        )
        
        # Verify result limit
        assert len(results['ids'][0]) <= 3


class TestDatabaseServiceVectorStoreIntegration:
    """Test VectorStore-specific functionality through DatabaseService."""
    
    def test_search_via_vectorstore(self, database_service):
        """Test that DatabaseService properly delegates to VectorStore."""
        # Add documents
        documents = ["AI research paper", "Machine learning tutorial"]
        metadatas = [{"type": "research"}, {"type": "tutorial"}]
        ids = ["doc1", "doc2"]
        
        database_service.add_documents(documents, metadatas, ids)
        
        # Search directly via vectorstore
        vectorstore_results = database_service.vectorstore.search(
            query="artificial intelligence",
            k=2
        )
        
        # Verify results
        assert len(vectorstore_results) <= 2
        assert all('id' in r for r in vectorstore_results)
        assert all('content' in r for r in vectorstore_results)
        assert all('score' in r for r in vectorstore_results)
    
    def test_duplicate_detection(self, database_service):
        """Test duplicate detection through VectorStore."""
        # Add similar documents
        documents = [
            "This is a test document about machine learning",
            "This is a test document about machine learning",  # Exact duplicate
            "This is completely different content about cooking"
        ]
        metadatas = [{"id": i} for i in range(3)]
        ids = ["doc1", "doc2", "doc3"]
        
        database_service.add_documents(documents, metadatas, ids)
        
        # Find duplicates via vectorstore
        duplicates = database_service.vectorstore.find_duplicates(threshold=0.95)
        
        # Verify duplicates found
        assert len(duplicates) >= 1  # At least one duplicate pair
        # Each duplicate is (id1, id2, similarity)
        for id1, id2, similarity in duplicates:
            assert similarity >= 0.95
            assert id1 != id2
    
    def test_collection_stats(self, database_service):
        """Test collection statistics."""
        # Add documents
        documents = ["Doc 1", "Doc 2", "Doc 3"]
        metadatas = [{}, {}, {}]
        ids = ["doc1", "doc2", "doc3"]
        
        database_service.add_documents(documents, metadatas, ids)
        
        # Get stats via vectorstore
        stats = database_service.vectorstore.collection_stats()
        
        # Verify stats
        assert stats['count'] == 3
        assert stats['name'] == "test_collection"
        assert stats['available'] is True


class TestDatabaseServiceCollectionManagement:
    """Test collection management functionality."""
    
    def test_get_or_create_collection(self, database_service):
        """Test getting or creating a collection."""
        collection = database_service.get_or_create_collection()
        
        assert collection is not None
        assert collection.name == "test_collection"
    
    def test_get_or_create_named_collection(self, database_service):
        """Test getting or creating a named collection."""
        collection = database_service.get_or_create_collection("custom_collection")
        
        assert collection is not None
        assert collection.name == "custom_collection"
    
    def test_switch_between_collections(self, database_service):
        """Test switching between collections."""
        # Add to default collection
        database_service.add_documents(
            ["Doc 1"], [{}], ["doc1"]
        )
        
        # Switch to different collection
        database_service.add_documents(
            ["Doc 2"], [{}], ["doc2"],
            collection_name="other_collection"
        )
        
        # Verify current collection is the one we switched to
        assert database_service.vectorstore.collection.name == "other_collection"
    
    def test_delete_collection(self, database_service):
        """Test deleting a collection."""
        # Create and populate collection
        database_service.add_documents(
            ["Test doc"], [{}], ["doc1"],
            collection_name="temp_collection"
        )
        
        # Delete collection
        database_service.delete_collection("temp_collection")
        
        # Verify collection was deleted
        collections = database_service.vectorstore.list_collections()
        assert "temp_collection" not in collections


class TestDatabaseServiceErrorHandling:
    """Test error handling and edge cases."""
    
    def test_add_documents_with_uninitialized_vectorstore(self, mock_config):
        """Test adding documents when VectorStore fails to initialize."""
        with patch('src.services.vectorstore.chromadb') as mock_chromadb_module:
            mock_chromadb_module.PersistentClient.side_effect = Exception("Init failed")
            # VectorStore has graceful degradation, so it doesn't raise
            # It should log a warning and continue
            service = DatabaseService(mock_config)
            # Verify vectorstore is in degraded mode
            assert service.vectorstore.client is None
    
    def test_query_with_uninitialized_vectorstore(self, database_service):
        """Test querying when VectorStore is None."""
        database_service.vectorstore = None
        
        with pytest.raises(RuntimeError, match="VectorStore not initialized"):
            database_service.query(["test"], n_results=5)
    
    def test_add_documents_with_empty_lists(self, database_service):
        """Test adding documents with empty lists."""
        # Should not raise error
        database_service.add_documents([], [], [])
        
        # Verify no documents added
        assert database_service.vectorstore.collection.count() == 0


class TestDatabaseServiceBackwardCompatibility:
    """Test backward compatibility with existing code."""
    
    def test_client_property_accessible(self, database_service):
        """Test that client property is accessible."""
        assert hasattr(database_service, 'client')
        assert database_service.client is not None
    
    def test_collection_name_property(self, database_service):
        """Test collection_name property."""
        assert hasattr(database_service, 'collection_name')
        assert database_service.collection_name == "test_collection"
    
    def test_legacy_add_documents_signature(self, database_service):
        """Test that legacy add_documents signature still works."""
        # Legacy signature with embeddings parameter
        documents = ["Test doc"]
        metadatas = [{"source": "test"}]
        ids = ["doc1"]
        embeddings = None  # Legacy code might pass None
        
        # Should work without error
        database_service.add_documents(
            documents, metadatas, ids, embeddings=embeddings
        )
        
        assert database_service.vectorstore.collection.count() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
