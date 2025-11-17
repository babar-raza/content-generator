"""Pytest configuration and shared fixtures for testing.

Sets up proper mocking for ChromaDB and sentence-transformers to enable
testing without installing these dependencies.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import mocks before the actual modules
from tests.fixtures.mock_chromadb import create_mock_client, create_mock_embedding_model


def pytest_configure(config):
    """Configure pytest with module-level mocks."""
    # Import the mock classes
    from tests.fixtures.mock_chromadb import MockChromaClient, MockSentenceTransformer
    
    # Mock chromadb module
    mock_chromadb = MagicMock()
    mock_chromadb.PersistentClient = MockChromaClient
    
    # Mock Settings
    mock_settings = MagicMock()
    mock_chromadb.config.Settings = mock_settings
    
    sys.modules['chromadb'] = mock_chromadb
    sys.modules['chromadb.config'] = mock_chromadb.config
    
    # Mock sentence_transformers
    mock_st = MagicMock()
    mock_st.SentenceTransformer = MockSentenceTransformer
    sys.modules['sentence_transformers'] = mock_st


@pytest.fixture(autouse=True)
def mock_chromadb_availability():
    """Ensure CHROMADB_AVAILABLE and SENTENCE_TRANSFORMERS_AVAILABLE are True."""
    with patch('src.services.services.CHROMADB_AVAILABLE', True):
        with patch('src.services.vectorstore.CHROMADB_AVAILABLE', True):
            with patch('src.services.vectorstore.SENTENCE_TRANSFORMERS_AVAILABLE', True):
                yield
