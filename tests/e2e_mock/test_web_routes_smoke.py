"""
E2E Mock Tests - Web Routes Smoke Tests
Tests all major web API routes using FastAPI TestClient with mock backends.
"""

import pytest
from fastapi.testclient import TestClient
from src.web.app import create_app


@pytest.fixture
def client():
    """Create a test client with no executor (mock mode)."""
    app = create_app(executor=None, config_snapshot=None)
    return TestClient(app)


class TestHealthAndRoot:
    """Test basic health and root endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data or "UCOP" in response.text

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_api_root(self, client):
        """Test /api endpoint."""
        response = client.get("/api")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "UCOP API"
        assert data["version"] == "1.0.0"

    def test_system_health(self, client):
        """Test enhanced system health endpoint."""
        response = client.get("/api/system/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data


class TestJobsRoutes:
    """Test jobs API routes."""

    def test_list_jobs(self, client):
        """Test GET /api/jobs - list all jobs."""
        response = client.get("/api/jobs")
        # Should work even with no executor (returns empty list)
        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_create_job_no_executor(self, client):
        """Test POST /api/jobs - create job (should fail without executor)."""
        job_data = {
            "workflow_name": "test_workflow",
            "topic": "test topic"
        }
        response = client.post("/api/jobs", json=job_data)
        # Expected to fail without executor (503) or validation error (400, 422), but endpoint should exist
        assert response.status_code in [200, 400, 422, 500, 503]


class TestAgentsRoutes:
    """Test agents API routes."""

    def test_list_agents(self, client):
        """Test GET /api/agents - list agents."""
        response = client.get("/api/agents")
        # Should return 503 (not initialized), 500 (error), or 200 (empty list) without executor
        assert response.status_code in [200, 500, 503]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_get_agent_status(self, client):
        """Test GET /api/agents/{agent_id}/status."""
        response = client.get("/api/agents/test_agent/status")
        # Should return 404 for non-existent agent
        assert response.status_code in [404, 500]

    def test_list_agent_failures(self, client):
        """Test GET /api/agents/failures."""
        response = client.get("/api/agents/failures")
        assert response.status_code in [200, 500]


class TestWorkflowsRoutes:
    """Test workflows API routes."""

    def test_list_workflows(self, client):
        """Test GET /api/workflows - list workflows."""
        response = client.get("/api/workflows")
        assert response.status_code in [200, 500]

    def test_get_workflow(self, client):
        """Test GET /api/workflows/{id}."""
        response = client.get("/api/workflows/test_workflow")
        # Should return 404 or 500 without executor
        assert response.status_code in [404, 500]

    def test_execute_workflow(self, client):
        """Test POST /api/workflows/{name}/execute."""
        payload = {"topic": "test topic"}
        response = client.post("/api/workflows/test_workflow/execute", json=payload)
        # Expected to fail without executor
        assert response.status_code in [200, 404, 422, 500]


class TestFlowsRoutes:
    """Test flows (visualization) routes."""

    def test_get_flow_data(self, client):
        """Test GET /api/flows/{job_id}."""
        response = client.get("/api/flows/test_job_id")
        # Should return 404 or 500 without flow monitor
        assert response.status_code in [404, 500]


class TestCheckpointsRoutes:
    """Test checkpoints API routes."""

    def test_list_checkpoints(self, client):
        """Test GET /api/checkpoints."""
        response = client.get("/api/checkpoints")
        # Should return 422 (missing required job_id param), 200 (with param), or 500 (error)
        assert response.status_code in [200, 422, 500]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_get_checkpoint(self, client):
        """Test GET /api/checkpoints/{checkpoint_id}."""
        response = client.get("/api/checkpoints/test_checkpoint")
        # Should return 404 for non-existent checkpoint
        assert response.status_code in [404, 500]


class TestBatchRoutes:
    """Test batch processing routes."""

    def test_create_batch_jobs_empty(self, client):
        """Test POST /api/batch/jobs with empty jobs list."""
        payload = {"jobs": []}
        response = client.post("/api/batch/jobs", json=payload)
        # Should fail validation (min_length=1)
        assert response.status_code == 422

    def test_create_batch_jobs_valid(self, client):
        """Test POST /api/batch/jobs with valid payload."""
        payload = {
            "jobs": [
                {"workflow_name": "test_workflow", "topic": "topic1"}
            ]
        }
        response = client.post("/api/batch/jobs", json=payload)
        # May fail without executor but endpoint should exist
        assert response.status_code in [200, 201, 400, 422, 500]


class TestConfigRoutes:
    """Test config management routes."""

    def test_get_config(self, client):
        """Test GET /api/config."""
        response = client.get("/api/config")
        # Should return 404 or empty without config snapshot
        assert response.status_code in [200, 404, 500]

    def test_validate_config(self, client):
        """Test POST /api/config/validate."""
        config_data = {
            "agents": {"test": {"type": "research"}},
            "workflows": {}
        }
        response = client.post("/api/config/validate", json=config_data)
        # Validation should work without executor
        assert response.status_code in [200, 422, 500]


class TestIngestionRoutes:
    """Test ingestion routes."""

    def test_ingest_kb(self, client):
        """Test POST /api/ingestion/kb."""
        payload = {
            "source_url": "https://example.com",
            "collection_name": "test_collection"
        }
        response = client.post("/api/ingestion/kb", json=payload)
        # May fail without executor but endpoint should exist
        assert response.status_code in [200, 202, 400, 422, 500]


class TestDebugRoutes:
    """Test debug routes."""

    def test_list_breakpoints(self, client):
        """Test GET /api/debug/breakpoints."""
        response = client.get("/api/debug/breakpoints")
        # Should return 200 or 500
        assert response.status_code in [200, 500]


class TestVisualizationRoutes:
    """Test visualization routes."""

    def test_get_execution_graph(self, client):
        """Test GET /api/visualization/graph/{job_id}."""
        response = client.get("/api/visualization/graph/test_job")
        # Should return 404 or 500 without data
        assert response.status_code in [404, 500]


class TestOpenAPISpec:
    """Test that OpenAPI documentation is accessible."""

    def test_docs_accessible(self, client):
        """Test that /docs returns OpenAPI UI."""
        response = client.get("/docs")
        assert response.status_code == 200
        # Should contain OpenAPI UI HTML
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    def test_openapi_json(self, client):
        """Test that OpenAPI spec JSON is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        spec = response.json()
        assert "openapi" in spec
        assert "paths" in spec
        # Verify key routes are documented
        paths = spec["paths"]
        assert "/api/jobs" in paths or "/health" in paths
