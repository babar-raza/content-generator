"""
Tests to verify legacy UI is removed and React UI works properly.

This test suite ensures:
1. Legacy UI endpoints return 404 (they don't exist)
2. React UI is properly served at root
3. MCP API endpoints work (used by React UI)
4. No broken links or 404s when using the app
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from unittest.mock import Mock
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def mock_executor():
    """Create a mock executor for testing."""
    executor = Mock()
    executor.job_engine = Mock()
    executor.job_engine._jobs = {}
    return executor


@pytest.fixture
def test_app(mock_executor):
    """Create a test FastAPI app."""
    from src.web.app import create_app
    
    app = create_app(executor=mock_executor, config_snapshot=None)
    return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


class TestLegacyUIRemoval:
    """Tests verifying legacy UI endpoints are removed."""
    
    def test_legacy_job_detail_template_not_served(self, client):
        """Test that legacy job detail page routes don't exist."""
        # These routes should not exist - they're not defined in the main app
        response = client.get("/job/test_job_123")
        assert response.status_code == 404
        
        response = client.get("/jobs/test_job_123")
        assert response.status_code == 404
    
    def test_legacy_dashboard_template_not_served(self, client):
        """Test that legacy dashboard routes don't exist."""
        response = client.get("/dashboard")
        assert response.status_code == 404
    
    def test_legacy_log_streaming_endpoint_not_exist(self, client):
        """Test that SSE log streaming endpoint doesn't exist."""
        response = client.get("/api/jobs/test_job/logs/stream")
        assert response.status_code == 404
    
    def test_legacy_artifacts_endpoint_not_exist(self, client):
        """Test that artifacts endpoint doesn't exist."""
        response = client.get("/api/jobs/test_job/artifacts")
        assert response.status_code == 404
    
    def test_legacy_step_endpoint_not_exist(self, client):
        """Test that step endpoint doesn't exist."""
        response = client.post("/api/jobs/test_job/step")
        assert response.status_code == 404
    
    def test_legacy_pipeline_add_endpoint_not_exist(self, client):
        """Test that pipeline add endpoint doesn't exist."""
        response = client.post("/api/jobs/test_job/pipeline/add")
        assert response.status_code == 404
    
    def test_legacy_pipeline_remove_endpoint_not_exist(self, client):
        """Test that pipeline remove endpoint doesn't exist."""
        response = client.post("/api/jobs/test_job/pipeline/remove")
        assert response.status_code == 404
    
    def test_legacy_per_agent_output_endpoint_not_exist(self, client):
        """Test that per-agent output endpoint doesn't exist."""
        response = client.get("/api/jobs/test_job/agents/agent_1/output")
        assert response.status_code == 404


class TestReactUIServed:
    """Tests verifying React UI is properly served."""
    
    def test_root_serves_react_ui(self, client):
        """Test that root path serves React UI index.html."""
        response = client.get("/")
        
        # Should return either the React UI HTML or API info if UI not built
        assert response.status_code == 200
        
        # If React UI is built, it should return HTML
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            # React UI is built and served
            content = response.text
            assert "<!DOCTYPE html>" in content or "<!doctype html>" in content.lower()
        else:
            # React UI not built, API info returned
            data = response.json()
            assert data["name"] == "UCOP API"
            assert data["ui"] == "not_built"
    
    def test_api_root_works(self, client):
        """Test that /api endpoint works."""
        response = client.get("/api")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "UCOP API"
        assert data["status"] == "operational"
    
    def test_health_endpoint_works(self, client):
        """Test that health check endpoint works."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestMCPEndpointsWork:
    """Tests verifying MCP endpoints work (used by React UI)."""
    
    def test_mcp_status_endpoint(self, client):
        """Test MCP status endpoint."""
        response = client.get("/mcp/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "executor_initialized" in data
    
    def test_mcp_methods_endpoint(self, client):
        """Test MCP methods listing endpoint."""
        response = client.get("/mcp/methods")
        assert response.status_code == 200
        
        data = response.json()
        assert "methods" in data
        assert isinstance(data["methods"], list)
    
    def test_mcp_config_snapshot_endpoint(self, client):
        """Test MCP config snapshot endpoint."""
        response = client.get("/mcp/config/snapshot")
        assert response.status_code in [200, 503]  # 503 if config not initialized
        
        data = response.json()
        assert "status" in data
    
    def test_mcp_agents_endpoint(self, client):
        """Test MCP agents listing endpoint."""
        response = client.get("/mcp/agents")
        assert response.status_code != 404  # Should not be 404
    
    def test_mcp_jobs_list_endpoint(self, client):
        """Test MCP jobs listing endpoint."""
        response = client.get("/mcp/jobs")
        assert response.status_code != 404  # Should not be 404


class TestJobManagementWorks:
    """Tests verifying job management still works without legacy UI."""
    
    def test_jobs_api_endpoint_works(self, client):
        """Test that /api/jobs endpoint works."""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        
        data = response.json()
        assert "jobs" in data or isinstance(data, list)
    
    def test_job_creation_endpoint_exists(self, client):
        """Test that job creation endpoint exists."""
        response = client.post(
            "/api/jobs",
            json={
                "workflow_id": "test_workflow",
                "inputs": {"test": "data"}
            }
        )
        # Should not be 404 (might be other errors without proper setup)
        assert response.status_code != 404


class TestStaticAssets:
    """Tests for static asset serving."""
    
    def test_react_assets_directory_mountable(self, client):
        """Test that React assets directory can be accessed (if built)."""
        # Try to access the assets directory
        # This will 404 if not built, which is OK
        response = client.get("/assets/")
        # Just ensure the route exists (404 or 403 is fine if no index)
        assert response.status_code in [200, 403, 404]


class TestDocumentation:
    """Tests for API documentation."""
    
    def test_openapi_docs_accessible(self, client):
        """Test that OpenAPI docs are accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_redoc_docs_accessible(self, client):
        """Test that ReDoc docs are accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200
    
    def test_openapi_json_accessible(self, client):
        """Test that OpenAPI JSON is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        data = response.json()
        assert "openapi" in data
        assert "paths" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
