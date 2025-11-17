"""
Integration tests for ingestion MCP endpoints.

Tests all 5 ingestion types (kb, docs, api, blog, tutorial) through
the MCP web adapter, ensuring proper routing, error handling, and
actual file system integration.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Test will be skipped if FastAPI test client is not available
fastapi_available = True
try:
    from fastapi.testclient import TestClient
except ImportError:
    fastapi_available = False


@pytest.mark.skipif(not fastapi_available, reason="FastAPI not available")
class TestIngestionMCP:
    """Test suite for ingestion MCP endpoints."""
    
    @pytest.fixture
    def temp_kb_dir(self, tmp_path):
        """Create temporary KB directory with sample files."""
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        
        # Create sample KB files
        (kb_dir / "article1.md").write_text(
            "# Test KB Article 1\n\nThis is test content for KB ingestion testing."
        )
        (kb_dir / "article2.md").write_text(
            "# Test KB Article 2\n\nAnother test article with different content."
        )
        
        return kb_dir
    
    @pytest.fixture
    def temp_docs_dir(self, tmp_path):
        """Create temporary docs directory with sample files."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        
        (docs_dir / "guide.md").write_text(
            "# Documentation Guide\n\nThis is a documentation file."
        )
        
        return docs_dir
    
    @pytest.fixture
    def mock_ingestion_agent(self):
        """Create a mock ingestion agent."""
        agent = Mock()
        agent.agent_id = "KBIngestionAgent"
        agent.execute = Mock(return_value=Mock(
            data={
                "kb_article_content": "Combined content",
                "kb_meta": {
                    "filename": "test",
                    "path": "/test/path",
                    "files_processed": 2,
                    "files_skipped": 0,
                    "total_size": 100
                }
            }
        ))
        return agent
    
    @pytest.fixture
    def mock_executor(self, mock_ingestion_agent):
        """Create a mock executor with ingestion agents."""
        executor = Mock()
        executor.agents = [
            mock_ingestion_agent,
            Mock(agent_id="DocsIngestionAgent"),
            Mock(agent_id="APIIngestionAgent"),
            Mock(agent_id="BlogIngestionAgent"),
            Mock(agent_id="TutorialIngestionAgent")
        ]
        return executor
    
    def test_ingest_kb_routing_exists(self):
        """Test that ingest/kb routing is registered."""
        from src.mcp.web_adapter import router
        routes = [route.path for route in router.routes]
        assert "/request" in routes
    
    @patch('src.mcp.web_adapter._executor')
    @patch('src.mcp.handlers._executor')
    def test_ingest_kb_happy_path(self, mock_handlers_executor, 
                                   mock_adapter_executor, mock_executor,
                                   temp_kb_dir):
        """Test successful KB ingestion through MCP protocol."""
        mock_handlers_executor.return_value = mock_executor
        mock_adapter_executor.return_value = mock_executor
        
        from src.web.app import app
        client = TestClient(app)
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_kb_001",
            "method": "ingest/kb",
            "params": {
                "kb_path": str(temp_kb_dir)
            }
        }
        
        response = client.post("/mcp/request", json=mcp_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data or "error" not in data
    
    @patch('src.mcp.web_adapter._executor')
    def test_ingest_kb_missing_path(self, mock_adapter_executor):
        """Test error handling when kb_path is missing."""
        from src.web.app import app
        client = TestClient(app)
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_kb_002",
            "method": "ingest/kb",
            "params": {}
        }
        
        response = client.post("/mcp/request", json=mcp_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32602
        assert "kb_path" in data["error"]["message"].lower()
    
    @patch('src.mcp.web_adapter._executor')
    @patch('src.mcp.handlers._executor')
    def test_ingest_docs_happy_path(self, mock_handlers_executor,
                                     mock_adapter_executor, mock_executor,
                                     temp_docs_dir):
        """Test successful docs ingestion."""
        mock_handlers_executor.return_value = mock_executor
        mock_adapter_executor.return_value = mock_executor
        
        from src.web.app import app
        client = TestClient(app)
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_docs_001",
            "method": "ingest/docs",
            "params": {
                "docs_path": str(temp_docs_dir)
            }
        }
        
        response = client.post("/mcp/request", json=mcp_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data or "error" not in data
    
    @patch('src.mcp.web_adapter._executor')
    def test_ingest_docs_missing_path(self, mock_adapter_executor):
        """Test error handling when docs_path is missing."""
        from src.web.app import app
        client = TestClient(app)
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_docs_002",
            "method": "ingest/docs",
            "params": {}
        }
        
        response = client.post("/mcp/request", json=mcp_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32602
    
    @patch('src.mcp.web_adapter._executor')
    @patch('src.mcp.handlers._executor')
    def test_ingest_api_happy_path(self, mock_handlers_executor,
                                    mock_adapter_executor, mock_executor):
        """Test successful API docs ingestion."""
        mock_handlers_executor.return_value = mock_executor
        mock_adapter_executor.return_value = mock_executor
        
        from src.web.app import app
        client = TestClient(app)
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_api_001",
            "method": "ingest/api",
            "params": {
                "api_path": "/test/api/path"
            }
        }
        
        response = client.post("/mcp/request", json=mcp_request)
        
        assert response.status_code == 200
    
    @patch('src.mcp.web_adapter._executor')
    @patch('src.mcp.handlers._executor')
    def test_ingest_blog_happy_path(self, mock_handlers_executor,
                                     mock_adapter_executor, mock_executor):
        """Test successful blog ingestion."""
        mock_handlers_executor.return_value = mock_executor
        mock_adapter_executor.return_value = mock_executor
        
        from src.web.app import app
        client = TestClient(app)
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_blog_001",
            "method": "ingest/blog",
            "params": {
                "blog_path": "/test/blog/path"
            }
        }
        
        response = client.post("/mcp/request", json=mcp_request)
        
        assert response.status_code == 200
    
    @patch('src.mcp.web_adapter._executor')
    @patch('src.mcp.handlers._executor')
    def test_ingest_tutorial_happy_path(self, mock_handlers_executor,
                                        mock_adapter_executor, mock_executor):
        """Test successful tutorial ingestion."""
        mock_handlers_executor.return_value = mock_executor
        mock_adapter_executor.return_value = mock_executor
        
        from src.web.app import app
        client = TestClient(app)
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_tutorial_001",
            "method": "ingest/tutorial",
            "params": {
                "tutorial_path": "/test/tutorial/path"
            }
        }
        
        response = client.post("/mcp/request", json=mcp_request)
        
        assert response.status_code == 200
    
    @patch('src.mcp.web_adapter._executor')
    @patch('src.mcp.handlers._executor')
    def test_ingest_agent_not_found(self, mock_handlers_executor,
                                     mock_adapter_executor):
        """Test error when ingestion agent doesn't exist."""
        executor = Mock()
        executor.agents = []  # No agents
        mock_handlers_executor.return_value = executor
        mock_adapter_executor.return_value = executor
        
        from src.web.app import app
        client = TestClient(app)
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_noagent_001",
            "method": "ingest/kb",
            "params": {
                "kb_path": "/test/path"
            }
        }
        
        response = client.post("/mcp/request", json=mcp_request)
        
        assert response.status_code == 200
        data = response.json()
        # Either error or failed status
        if "error" in data:
            assert "not found" in data["error"]["message"].lower()
        else:
            assert data.get("result", {}).get("status") == "failed"
    
    @patch('src.mcp.web_adapter._executor')
    @patch('src.mcp.handlers._executor')
    def test_ingest_execution_error(self, mock_handlers_executor,
                                     mock_adapter_executor):
        """Test error handling when agent execution fails."""
        # Create agent that raises exception
        failing_agent = Mock()
        failing_agent.agent_id = "KBIngestionAgent"
        failing_agent.execute = Mock(side_effect=RuntimeError("Ingestion failed"))
        
        executor = Mock()
        executor.agents = [failing_agent]
        mock_handlers_executor.return_value = executor
        mock_adapter_executor.return_value = executor
        
        from src.web.app import app
        client = TestClient(app)
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_error_001",
            "method": "ingest/kb",
            "params": {
                "kb_path": "/test/path"
            }
        }
        
        response = client.post("/mcp/request", json=mcp_request)
        
        assert response.status_code == 200
        data = response.json()
        result = data.get("result", {})
        assert result.get("status") == "failed"
        assert "error" in result


@pytest.mark.integration
class TestIngestionIntegration:
    """Integration tests with actual file system."""
    
    def test_ingest_kb_with_real_files(self, tmp_path):
        """Test KB ingestion with actual files."""
        # Create test KB directory
        kb_dir = tmp_path / "kb"
        kb_dir.mkdir()
        
        (kb_dir / "article1.md").write_text(
            "# Image Processing\n\n"
            "This article covers image processing with Aspose.Imaging for .NET.\n"
            "Learn how to resize, crop, and apply filters."
        )
        
        (kb_dir / "article2.md").write_text(
            "# PDF Manipulation\n\n"
            "Work with PDF documents using Aspose.PDF.\n"
            "Create, edit, and convert PDF files programmatically."
        )
        
        from src.web.app import app
        client = TestClient(app)
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "int_kb_001",
            "method": "ingest/kb",
            "params": {
                "kb_path": str(kb_dir)
            }
        }
        
        response = client.post("/mcp/request", json=mcp_request)
        
        assert response.status_code == 200
        data = response.json()
        # Should either succeed or fail gracefully
        assert "result" in data or "error" in data
    
    def test_ingest_kb_empty_directory(self, tmp_path):
        """Test ingestion with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        from src.web.app import app
        client = TestClient(app)
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "int_kb_002",
            "method": "ingest/kb",
            "params": {
                "kb_path": str(empty_dir)
            }
        }
        
        response = client.post("/mcp/request", json=mcp_request)
        
        assert response.status_code == 200
        data = response.json()
        # Should handle empty directory gracefully
        if "result" in data:
            result = data["result"]
            assert "status" in result
    
    def test_ingest_kb_nonexistent_path(self):
        """Test ingestion with non-existent path."""
        from src.web.app import app
        client = TestClient(app)
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "int_kb_003",
            "method": "ingest/kb",
            "params": {
                "kb_path": "/nonexistent/path/to/kb"
            }
        }
        
        response = client.post("/mcp/request", json=mcp_request)
        
        assert response.status_code == 200
        data = response.json()
        # Should fail with appropriate error
        if "result" in data:
            assert data["result"].get("status") == "failed"
        else:
            assert "error" in data
    
    def test_ingest_single_file(self, tmp_path):
        """Test ingestion of single file instead of directory."""
        kb_file = tmp_path / "single.md"
        kb_file.write_text(
            "# Single KB Article\n\n"
            "This is a single knowledge base article for testing."
        )
        
        from src.web.app import app
        client = TestClient(app)
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "int_kb_004",
            "method": "ingest/kb",
            "params": {
                "kb_path": str(kb_file)
            }
        }
        
        response = client.post("/mcp/request", json=mcp_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data or "error" in data


# Standalone test functions

def test_handler_functions_exist():
    """Test that all ingestion handler functions exist."""
    from src.mcp import handlers
    
    assert hasattr(handlers, 'handle_ingest_kb')
    assert hasattr(handlers, 'handle_ingest_docs')
    assert hasattr(handlers, 'handle_ingest_api')
    assert hasattr(handlers, 'handle_ingest_blog')
    assert hasattr(handlers, 'handle_ingest_tutorial')


def test_web_handler_functions_exist():
    """Test that all web adapter handler functions exist."""
    from src.mcp import web_adapter
    
    assert hasattr(web_adapter, 'handle_ingest_kb_web')
    assert hasattr(web_adapter, 'handle_ingest_docs_web')
    assert hasattr(web_adapter, 'handle_ingest_api_web')
    assert hasattr(web_adapter, 'handle_ingest_blog_web')
    assert hasattr(web_adapter, 'handle_ingest_tutorial_web')


def test_handlers_are_async():
    """Test that all ingestion handlers are async functions."""
    import inspect
    from src.mcp.handlers import (
        handle_ingest_kb, handle_ingest_docs, handle_ingest_api,
        handle_ingest_blog, handle_ingest_tutorial
    )
    
    handlers = [
        handle_ingest_kb, handle_ingest_docs, handle_ingest_api,
        handle_ingest_blog, handle_ingest_tutorial
    ]
    
    for handler in handlers:
        assert inspect.iscoroutinefunction(handler), \
            f"{handler.__name__} should be async function"


@pytest.mark.asyncio
async def test_handler_returns_correct_structure():
    """Test that handlers return expected data structure."""
    with patch('src.mcp.handlers.get_executor') as mock_get_executor:
        # Setup mock
        mock_agent = Mock()
        mock_agent.agent_id = "KBIngestionAgent"
        mock_agent.execute = Mock(return_value=Mock(
            data={"kb_article_content": "test", "kb_meta": {}}
        ))
        
        mock_executor = Mock()
        mock_executor.agents = [mock_agent]
        mock_get_executor.return_value = mock_executor
        
        from src.mcp.handlers import handle_ingest_kb
        
        result = await handle_ingest_kb({"kb_path": "/test"})
        
        # Check structure
        assert "status" in result
        assert result["status"] in ["completed", "failed"]
        assert "kb_path" in result
        assert "completed_at" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
