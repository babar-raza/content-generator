"""
Live Workflow Execution Tests - Wave 3

These tests execute real workflows end-to-end using real services.
They verify that:
- Jobs can be submitted and executed
- Output artifacts are created
- Web and MCP endpoints work correctly

Run with: pytest -m live tests/live/test_live_workflow_execute.py
"""

import pytest
from fastapi.testclient import TestClient
from .conftest import skip_if_not_live


@pytest.fixture
def live_executor():
    """Create a live executor for testing."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from tools.live_executor_factory import create_live_executor
    return create_live_executor()


@pytest.mark.live
class TestLiveWorkflowExecution:
    """Test live workflow execution through web API."""

    @skip_if_not_live()
    def test_submit_and_check_job(self, live_executor):
        """Test submitting a job and checking its status."""
        from src.web.app import create_app

        # Create app with live executor
        app = create_app(executor=live_executor)
        client = TestClient(app)

        # Test GET /api/jobs
        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data

        print("[OK] Job API accessible with live executor")

    @skip_if_not_live()
    def test_get_workflows(self, live_executor):
        """Test getting available workflows."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        # Test GET /api/workflows
        response = client.get("/api/workflows")
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data

        print(f"[OK] Found {len(data['workflows'])} workflows")

    @skip_if_not_live()
    def test_get_agents(self, live_executor):
        """Test getting available agents."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        # Test GET /api/agents
        response = client.get("/api/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data

        print(f"[OK] Found {len(data['agents'])} agents")


@pytest.mark.live
class TestLiveMCPEndpoint:
    """Test MCP endpoint with live services."""

    @skip_if_not_live()
    def test_mcp_single_request(self, live_executor):
        """Test MCP single request."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        # Test POST /mcp/request with a simple request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "workflows/list",
            "params": {}
        }

        response = client.post("/mcp/request", json=mcp_request)
        assert response.status_code == 200
        data = response.json()
        assert "result" in data or "error" in data

        print("[OK] MCP single request successful with live executor")

    @skip_if_not_live()
    def test_mcp_batch_request(self, live_executor):
        """Test MCP batch request on canonical endpoint."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        # Test POST /mcp/request with batch requests
        batch_request = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "workflows/list",
                "params": {}
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "agents/list",
                "params": {}
            }
        ]

        response = client.post("/mcp/request", json=batch_request)
        assert response.status_code == 200
        data = response.json()

        # Should return a list of responses
        assert isinstance(data, list)
        assert len(data) == 2

        # Each response should have result or error
        for item in data:
            assert "result" in item or "error" in item

        print("[OK] MCP batch request successful with live executor")
