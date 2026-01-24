"""
Live End-to-End Tests for Web and MCP APIs - Wave 3

Comprehensive integration tests that exercise all major endpoints
with the live executor.
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
class TestLiveWebE2E:
    """End-to-end tests for REST API endpoints."""

    @skip_if_not_live()
    def test_get_agents(self, live_executor):
        """Test GET /api/agents with live executor."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        response = client.get("/api/agents")
        assert response.status_code == 200

        data = response.json()
        assert "agents" in data
        assert "total" in data

        print(f"[OK] GET /api/agents returned {data['total']} agents")

    @skip_if_not_live()
    def test_get_workflows(self, live_executor):
        """Test GET /api/workflows with live executor."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        response = client.get("/api/workflows")
        assert response.status_code == 200

        data = response.json()
        assert "workflows" in data
        assert "total" in data
        assert data["total"] > 0

        print(f"[OK] GET /api/workflows returned {data['total']} workflows")

    @skip_if_not_live()
    def test_get_workflow_by_id(self, live_executor):
        """Test GET /api/workflows/{id} with live executor."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        # First get list of workflows
        list_response = client.get("/api/workflows")
        workflows = list_response.json()["workflows"]

        if workflows:
            workflow_id = workflows[0]["workflow_id"]

            # Get specific workflow
            response = client.get(f"/api/workflows/{workflow_id}")
            assert response.status_code == 200

            data = response.json()
            assert data["workflow_id"] == workflow_id
            assert "name" in data
            assert "agents" in data

            print(f"[OK] GET /api/workflows/{workflow_id} successful")

    @skip_if_not_live()
    def test_get_jobs(self, live_executor):
        """Test GET /api/jobs with live executor."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        response = client.get("/api/jobs")
        assert response.status_code == 200

        data = response.json()
        assert "jobs" in data

        print(f"[OK] GET /api/jobs returned {len(data['jobs'])} jobs")

    @skip_if_not_live()
    def test_post_job(self, live_executor):
        """Test POST /api/jobs with live executor."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        # Get a workflow first
        workflows_response = client.get("/api/workflows")
        workflows = workflows_response.json()["workflows"]

        if workflows:
            workflow_id = workflows[0]["workflow_id"]

            # Create a job
            job_payload = {
                "workflow_id": workflow_id,
                "inputs": {
                    "topic": "Test Topic for Wave 3 E2E"
                }
            }

            response = client.post("/api/jobs", json=job_payload)
            assert response.status_code in [200, 201]

            data = response.json()
            assert "job_id" in data

            job_id = data["job_id"]
            print(f"[OK] POST /api/jobs created job {job_id}")

            # Get job status
            status_response = client.get(f"/api/jobs/{job_id}")
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["job_id"] == job_id

            print(f"[OK] GET /api/jobs/{job_id} returned status: {status_data.get('status', 'unknown')}")


@pytest.mark.live
class TestLiveMCPE2E:
    """End-to-end tests for MCP protocol endpoints."""

    @skip_if_not_live()
    def test_mcp_single_request(self, live_executor):
        """Test POST /mcp/request with single request."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

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

        if "result" in data:
            print(f"[OK] POST /mcp/request (single) returned result")
        else:
            print(f"[INFO] POST /mcp/request (single) returned error: {data.get('error')}")

    @skip_if_not_live()
    def test_mcp_batch_request(self, live_executor):
        """Test POST /mcp/request with batch request."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

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
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "jobs/list",
                "params": {}
            }
        ]

        response = client.post("/mcp/request", json=batch_request)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

        for item in data:
            assert "result" in item or "error" in item

        print(f"[OK] POST /mcp/request (batch) processed {len(data)} requests")

    @skip_if_not_live()
    def test_mcp_agents_list(self, live_executor):
        """Test MCP agents/list method."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "agents/list",
            "params": {}
        }

        response = client.post("/mcp/request", json=mcp_request)
        assert response.status_code == 200

        data = response.json()
        if "result" in data:
            agents = data["result"].get("agents", [])
            print(f"[OK] MCP agents/list returned {len(agents)} agents")
        else:
            print(f"[INFO] MCP agents/list returned error: {data.get('error')}")

    @skip_if_not_live()
    def test_mcp_workflows_list(self, live_executor):
        """Test MCP workflows/list method."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "workflows/list",
            "params": {}
        }

        response = client.post("/mcp/request", json=mcp_request)
        assert response.status_code == 200

        data = response.json()
        if "result" in data:
            workflows = data["result"].get("workflows", [])
            print(f"[OK] MCP workflows/list returned {len(workflows)} workflows")
        else:
            print(f"[INFO] MCP workflows/list returned error: {data.get('error')}")

    @skip_if_not_live()
    def test_mcp_jobs_list(self, live_executor):
        """Test MCP jobs/list method."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "jobs/list",
            "params": {}
        }

        response = client.post("/mcp/request", json=mcp_request)
        assert response.status_code == 200

        data = response.json()
        if "result" in data:
            jobs = data["result"].get("jobs", [])
            print(f"[OK] MCP jobs/list returned {len(jobs)} jobs")
        else:
            print(f"[INFO] MCP jobs/list returned error: {data.get('error')}")


@pytest.mark.live
class TestLiveHealthEndpoints:
    """End-to-end tests for health and status endpoints."""

    @skip_if_not_live()
    def test_health_endpoint(self, live_executor):
        """Test GET /health endpoint."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        response = client.get("/health")
        # Health endpoint might return 200 or 503 depending on system state
        assert response.status_code in [200, 503]

        data = response.json()
        assert "status" in data

        print(f"[OK] GET /health returned status: {data['status']}")

    @skip_if_not_live()
    def test_mcp_status_endpoint(self, live_executor):
        """Test GET /mcp/status endpoint."""
        from src.web.app import create_app

        app = create_app(executor=live_executor)
        client = TestClient(app)

        response = client.get("/mcp/status")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "executor_initialized" in data

        print(f"[OK] GET /mcp/status returned: {data['status']}")
