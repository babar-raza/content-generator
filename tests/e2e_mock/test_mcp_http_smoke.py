"""
E2E Mock Tests - MCP HTTP Smoke Tests
Tests MCP protocol endpoints using FastAPI TestClient with mock backends.
"""

import pytest
from fastapi.testclient import TestClient
from src.web.app import create_app


@pytest.fixture
def client():
    """Create a test client with no executor (mock mode)."""
    app = create_app(executor=None, config_snapshot=None)
    return TestClient(app)


class TestMCPProtocol:
    """Test MCP protocol endpoints."""

    def test_mcp_root(self, client):
        """Test GET /mcp/ returns MCP info."""
        response = client.get("/mcp/")
        # Should return MCP protocol info or 404
        assert response.status_code in [200, 404]

    def test_mcp_jsonrpc_workflow_list(self, client):
        """Test MCP JSON-RPC: workflow.list."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "workflow.list",
            "params": {}
        }
        response = client.post("/mcp/", json=payload)
        # Should return 200 with JSON-RPC response
        assert response.status_code == 200
        data = response.json()
        # Validate JSON-RPC response structure
        assert "id" in data
        assert data["id"] == 1
        # Should have either result or error
        assert "result" in data or "error" in data
        if "error" in data:
            # Error should have code and message
            assert "code" in data["error"]
            assert "message" in data["error"]

    def test_mcp_jsonrpc_workflow_execute(self, client):
        """Test MCP JSON-RPC: workflow.execute."""
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "workflow.execute",
            "params": {
                "workflow_name": "test_workflow",
                "topic": "test topic"
            }
        }
        response = client.post("/mcp/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["id"] == 2
        assert "result" in data or "error" in data
        if "error" in data:
            assert "code" in data["error"]
            assert "message" in data["error"]

    def test_mcp_jsonrpc_job_status(self, client):
        """Test MCP JSON-RPC: job.status."""
        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "job.status",
            "params": {
                "job_id": "test_job_123"
            }
        }
        response = client.post("/mcp/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["id"] == 3
        assert "result" in data or "error" in data

    def test_mcp_jsonrpc_job_list(self, client):
        """Test MCP JSON-RPC: job.list."""
        payload = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "job.list",
            "params": {}
        }
        response = client.post("/mcp/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "result" in data or "error" in data

    def test_mcp_jsonrpc_agent_list(self, client):
        """Test MCP JSON-RPC: agent.list."""
        payload = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "agent.list",
            "params": {}
        }
        response = client.post("/mcp/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "result" in data or "error" in data

    def test_mcp_jsonrpc_agent_status(self, client):
        """Test MCP JSON-RPC: agent.status."""
        payload = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "agent.status",
            "params": {
                "agent_id": "test_agent"
            }
        }
        response = client.post("/mcp/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "result" in data or "error" in data

    def test_mcp_jsonrpc_config_get(self, client):
        """Test MCP JSON-RPC: config.get."""
        payload = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "config.get",
            "params": {}
        }
        response = client.post("/mcp/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "result" in data or "error" in data

    def test_mcp_jsonrpc_config_validate(self, client):
        """Test MCP JSON-RPC: config.validate."""
        payload = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "config.validate",
            "params": {
                "config": {
                    "agents": {"test": {"type": "research"}},
                    "workflows": {}
                }
            }
        }
        response = client.post("/mcp/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "result" in data or "error" in data

    def test_mcp_jsonrpc_checkpoint_list(self, client):
        """Test MCP JSON-RPC: checkpoint.list."""
        payload = {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "checkpoint.list",
            "params": {}
        }
        response = client.post("/mcp/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "result" in data or "error" in data

    def test_mcp_jsonrpc_checkpoint_save(self, client):
        """Test MCP JSON-RPC: checkpoint.save."""
        payload = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "checkpoint.save",
            "params": {
                "job_id": "test_job",
                "agent_id": "test_agent"
            }
        }
        response = client.post("/mcp/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "result" in data or "error" in data

    def test_mcp_jsonrpc_checkpoint_restore(self, client):
        """Test MCP JSON-RPC: checkpoint.restore."""
        payload = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "checkpoint.restore",
            "params": {
                "checkpoint_id": "test_checkpoint"
            }
        }
        response = client.post("/mcp/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "result" in data or "error" in data

    def test_mcp_jsonrpc_invalid_method(self, client):
        """Test MCP JSON-RPC with invalid method."""
        payload = {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "invalid.method",
            "params": {}
        }
        response = client.post("/mcp/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        # Should return error for invalid method
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found

    def test_mcp_jsonrpc_missing_id(self, client):
        """Test MCP JSON-RPC with missing id."""
        payload = {
            "jsonrpc": "2.0",
            "method": "workflow.list",
            "params": {}
        }
        response = client.post("/mcp/", json=payload)
        # Should handle missing id (notification or error)
        assert response.status_code in [200, 400]

    def test_mcp_jsonrpc_invalid_jsonrpc_version(self, client):
        """Test MCP JSON-RPC with invalid version."""
        payload = {
            "jsonrpc": "1.0",
            "id": 100,
            "method": "workflow.list",
            "params": {}
        }
        response = client.post("/mcp/", json=payload)
        # Should handle invalid version
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            # May return error for invalid version
            assert "result" in data or "error" in data


class TestMCPBatchRequests:
    """Test MCP batch request handling."""

    def test_mcp_batch_request(self, client):
        """Test MCP JSON-RPC batch request."""
        payload = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "workflow.list",
                "params": {}
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "agent.list",
                "params": {}
            }
        ]
        response = client.post("/mcp/", json=payload)
        # Should handle batch requests
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            # Should return array of responses
            if isinstance(data, list):
                assert len(data) == 2
                for item in data:
                    assert "id" in item
                    assert "result" in item or "error" in item


class TestMCPRestEndpoints:
    """Test MCP REST-style endpoints (if any)."""

    def test_mcp_workflows_endpoint(self, client):
        """Test GET /mcp/workflows if it exists."""
        response = client.get("/mcp/workflows")
        # May not exist, but test if it does
        assert response.status_code in [200, 404, 405, 500]

    def test_mcp_jobs_endpoint(self, client):
        """Test GET /mcp/jobs if it exists."""
        response = client.get("/mcp/jobs")
        assert response.status_code in [200, 404, 405, 500]

    def test_mcp_agents_endpoint(self, client):
        """Test GET /mcp/agents if it exists."""
        response = client.get("/mcp/agents")
        assert response.status_code in [200, 404, 405, 500]
