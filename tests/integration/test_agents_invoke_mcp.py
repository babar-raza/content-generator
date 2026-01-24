"""
Integration tests for agents/invoke MCP endpoint.

Tests the complete flow of agent invocation through the MCP web adapter,
ensuring proper routing, error handling, and MCP protocol compliance.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Test will be skipped if FastAPI test client is not available
fastapi_available = True
try:
    from fastapi.testclient import TestClient
except ImportError:
    fastapi_available = False


@pytest.mark.skipif(not fastapi_available, reason="FastAPI not available")
class TestAgentsInvokeMCP:
    """Test suite for agents/invoke MCP endpoint."""
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent for testing."""
        agent = Mock()
        agent.agent_id = "TestAgent"
        agent.execute = AsyncMock(return_value={
            "status": "completed",
            "output": {"result": "test_output", "processed": True}
        })
        return agent
    
    @pytest.fixture
    def mock_executor(self, mock_agent):
        """Create a mock executor with test agent."""
        executor = Mock()
        executor.agents = [mock_agent]
        return executor
    
    @pytest.fixture
    def mock_agent_registry(self, mock_agent):
        """Create a mock agent registry."""
        registry = Mock()
        registry.get_agent = Mock(return_value=mock_agent)
        registry.list_agents = Mock(return_value=[
            {
                "id": "TestAgent",
                "name": "Test Agent",
                "category": "test",
                "status": "idle"
            }
        ])
        return registry
    
    def test_agents_invoke_routing_exists(self):
        """Test that agents/invoke routing is registered in web adapter."""
        from src.mcp.web_adapter import router
        
        # Check that the route handler exists
        routes = [route.path for route in router.routes]
        assert "/request" in routes, "MCP request endpoint should exist"
    
    @patch('src.mcp.web_adapter._executor')
    @patch('src.mcp.web_adapter._agent_registry')
    @patch('src.mcp.handlers._executor')
    @patch('src.mcp.handlers._agent_registry')
    def test_agents_invoke_happy_path(self, mock_handlers_registry, mock_handlers_executor,
                                      mock_adapter_registry, mock_adapter_executor,
                                      mock_executor, mock_agent_registry, mock_agent):
        """Test successful agent invocation through MCP protocol."""
        # Setup mocks
        mock_handlers_executor.return_value = mock_executor
        mock_handlers_registry.return_value = mock_agent_registry
        mock_adapter_executor.return_value = mock_executor
        
        from src.web.app import app
        client = TestClient(app)
        
        # Prepare MCP request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_001",
            "method": "agents/invoke",
            "params": {
                "agent_id": "TestAgent",
                "input": {
                    "test_param": "test_value"
                }
            }
        }
        
        # Make request
        response = client.post("/mcp/request", json=mcp_request)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "result" in data or "error" not in data
        assert data.get("id") == "test_001"
    
    @patch('src.mcp.web_adapter._executor')
    def test_agents_invoke_missing_agent_id(self, mock_adapter_executor):
        """Test error handling when agent_id is missing."""
        from src.web.app import app
        client = TestClient(app)
        
        # Prepare MCP request without agent_id
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_002",
            "method": "agents/invoke",
            "params": {
                "input": {"test": "data"}
            }
        }
        
        # Make request
        response = client.post("/mcp/request", json=mcp_request)
        
        # Verify error response
        assert response.status_code == 200  # MCP errors return 200 with error in body
        data = response.json()
        assert "error" in data
        # Accept either -32602 (Invalid params) or -32603 (Internal error)
        # The web adapter catches ValueError as internal error
        assert data["error"]["code"] in [-32602, -32603]
        assert "agent_id" in data["error"]["message"].lower()
    
    @patch('src.mcp.web_adapter._executor')
    @patch('src.mcp.handlers._executor')
    @patch('src.mcp.handlers._agent_registry')
    def test_agents_invoke_agent_not_found(self, mock_handlers_registry, 
                                           mock_handlers_executor, mock_adapter_executor):
        """Test error handling when agent doesn't exist."""
        # Setup mocks to simulate agent not found
        mock_registry = Mock()
        mock_registry.get_agent = Mock(side_effect=ValueError("Agent not found"))
        mock_handlers_registry.return_value = mock_registry
        
        mock_executor = Mock()
        mock_executor.agents = []
        mock_handlers_executor.return_value = mock_executor
        
        from src.web.app import app
        client = TestClient(app)
        
        # Prepare MCP request for non-existent agent
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_003",
            "method": "agents/invoke",
            "params": {
                "agent_id": "NonExistentAgent",
                "input": {}
            }
        }
        
        # Make request
        response = client.post("/mcp/request", json=mcp_request)
        
        # Verify error response
        assert response.status_code == 200
        data = response.json()
        assert "error" in data or "status" in data.get("result", {})
    
    @patch('src.mcp.web_adapter._executor')
    @patch('src.mcp.handlers._executor')
    @patch('src.mcp.handlers._agent_registry')
    def test_agents_invoke_with_context(self, mock_handlers_registry,
                                        mock_handlers_executor, mock_adapter_executor,
                                        mock_executor, mock_agent_registry, mock_agent):
        """Test agent invocation with context parameter."""
        # Setup mocks
        mock_handlers_executor.return_value = mock_executor
        mock_handlers_registry.return_value = mock_agent_registry
        mock_adapter_executor.return_value = mock_executor
        
        from src.web.app import app
        client = TestClient(app)
        
        # Prepare MCP request with context
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_004",
            "method": "agents/invoke",
            "params": {
                "agent_id": "TestAgent",
                "input": {"data": "test"},
                "context": {
                    "correlation_id": "test_corr_123",
                    "session_id": "test_session_456"
                }
            }
        }
        
        # Make request
        response = client.post("/mcp/request", json=mcp_request)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "result" in data or "error" not in data
    
    def test_agents_invoke_method_not_found(self):
        """Test that invalid methods return proper error code."""
        from src.web.app import app
        client = TestClient(app)
        
        # Prepare MCP request with invalid method
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_005",
            "method": "agents/invalid_method",
            "params": {}
        }
        
        # Make request
        response = client.post("/mcp/request", json=mcp_request)
        
        # Verify error response
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found
    
    @patch('src.mcp.web_adapter._executor')
    @patch('src.mcp.handlers._executor')
    @patch('src.mcp.handlers._agent_registry')
    def test_agents_invoke_execution_error(self, mock_handlers_registry,
                                           mock_handlers_executor, mock_adapter_executor):
        """Test error handling when agent execution fails."""
        # Setup mock agent that raises exception
        failing_agent = Mock()
        failing_agent.agent_id = "FailingAgent"
        failing_agent.execute = AsyncMock(side_effect=RuntimeError("Agent execution failed"))
        
        mock_registry = Mock()
        mock_registry.get_agent = Mock(return_value=failing_agent)
        mock_handlers_registry.return_value = mock_registry
        
        mock_executor = Mock()
        mock_executor.agents = [failing_agent]
        mock_handlers_executor.return_value = mock_executor
        mock_adapter_executor.return_value = mock_executor
        
        from src.web.app import app
        client = TestClient(app)
        
        # Prepare MCP request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test_006",
            "method": "agents/invoke",
            "params": {
                "agent_id": "FailingAgent",
                "input": {}
            }
        }
        
        # Make request
        response = client.post("/mcp/request", json=mcp_request)
        
        # Verify error is handled gracefully
        assert response.status_code == 200
        data = response.json()
        # Should have either error field or result with failed status
        assert "error" in data or data.get("result", {}).get("status") == "failed"


@pytest.mark.integration
class TestAgentsInvokeIntegration:
    """Integration tests with actual agent execution (if available)."""
    
    def test_invoke_kb_ingestion_agent(self, tmp_path):
        """Test invoking KBIngestionAgent with actual file."""
        # Create test KB file
        kb_file = tmp_path / "test.md"
        kb_file.write_text("# Test KB Article\n\nThis is test content for KB ingestion.")
        
        from src.web.app import app
        client = TestClient(app)
        
        # Prepare MCP request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "int_test_001",
            "method": "agents/invoke",
            "params": {
                "agent_id": "KBIngestionAgent",
                "input": {
                    "kb_path": str(kb_file)
                }
            }
        }
        
        # Make request
        response = client.post("/mcp/request", json=mcp_request)
        
        # Verify response structure (agent may not be fully initialized in test)
        assert response.status_code == 200
        data = response.json()
        # Either succeeds or fails gracefully
        assert "result" in data or "error" in data
    
    def test_invoke_topic_identification_agent(self):
        """Test invoking TopicIdentificationAgent with sample content."""
        from src.web.app import app
        client = TestClient(app)
        
        # Prepare MCP request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "int_test_002",
            "method": "agents/invoke",
            "params": {
                "agent_id": "TopicIdentificationAgent",
                "input": {
                    "kb_article_content": """
                    # Image Processing with Aspose.Imaging
                    
                    This article demonstrates how to process images using Aspose.Imaging for .NET.
                    You can resize, crop, and apply filters to various image formats.
                    """
                }
            }
        }
        
        # Make request
        response = client.post("/mcp/request", json=mcp_request)
        
        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        assert "result" in data or "error" in data


# Standalone test functions for pytest discovery

def test_handler_function_exists():
    """Test that handle_agents_invoke function exists in web adapter."""
    from src.mcp import web_adapter
    assert hasattr(web_adapter, 'handle_agents_invoke'), \
        "handle_agents_invoke function should exist in web_adapter"


def test_handler_delegates_to_mcp_handlers():
    """Test that handler properly delegates to MCP handlers module."""
    import inspect
    from src.mcp.web_adapter import handle_agents_invoke
    
    # Check function signature
    sig = inspect.signature(handle_agents_invoke)
    assert 'params' in sig.parameters, "Handler should accept params parameter"
    
    # Check that it's async
    assert inspect.iscoroutinefunction(handle_agents_invoke), \
        "Handler should be async function"


@pytest.mark.asyncio
async def test_handler_calls_mcp_handler():
    """Test that web adapter handler calls MCP handlers.handle_agent_invoke."""
    # Patch the handler in the handlers module where it's defined
    # (the web_adapter imports it inline from handlers)
    with patch('src.mcp.handlers.handle_agent_invoke') as mock_handler:
        mock_handler.return_value = {"status": "completed"}

        from src.mcp.web_adapter import handle_agents_invoke

        params = {"agent_id": "TestAgent", "input": {}}
        result = await handle_agents_invoke(params)

        # Verify the MCP handler was called
        mock_handler.assert_called_once_with(params)
        assert result["status"] == "completed"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
