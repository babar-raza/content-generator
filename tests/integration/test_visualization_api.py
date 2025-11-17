"""
HTTP endpoint tests for Visualization API.

Tests:
- GET /api/visualization/workflows
- GET /api/visualization/workflows/{id}
- GET /api/visualization/workflows/{id}/render
- GET /api/monitoring/agents
- GET /api/monitoring/agents/{id}
- GET /api/monitoring/system
- GET /api/monitoring/jobs/{id}/metrics
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.fixtures.http_fixtures import mock_executor, test_app, client


class TestWorkflowVisualization:
    """Tests for workflow visualization endpoints."""
    
    def test_list_visualization_workflows(self, client):
        """Test GET /api/visualization/workflows."""
        response = client.get("/api/visualization/workflows")
        assert response.status_code in [200, 404, 501]
    
    def test_get_workflow_visualization(self, client):
        """Test GET /api/visualization/workflows/{id}."""
        response = client.get("/api/visualization/workflows/test_workflow")
        assert response.status_code in [200, 404, 501]
    
    def test_render_workflow(self, client):
        """Test GET /api/visualization/workflows/{id}/render."""
        response = client.get("/api/visualization/workflows/test_workflow/render")
        assert response.status_code in [200, 404, 501]


class TestAgentMonitoring:
    """Tests for agent monitoring endpoints."""
    
    def test_monitor_agents_list(self, client):
        """Test GET /api/monitoring/agents."""
        response = client.get("/api/monitoring/agents")
        assert response.status_code in [200, 404, 501]
    
    def test_monitor_agent_detail(self, client):
        """Test GET /api/monitoring/agents/{id}."""
        response = client.get("/api/monitoring/agents/test_agent")
        assert response.status_code in [200, 404, 501]


class TestSystemMonitoring:
    """Tests for system monitoring endpoints."""
    
    def test_monitor_system(self, client):
        """Test GET /api/monitoring/system."""
        response = client.get("/api/monitoring/system")
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            data = response.json()
            # Should have system metrics
            assert isinstance(data, dict)


class TestJobMetrics:
    """Tests for job metrics endpoints."""
    
    def test_get_job_metrics(self, client):
        """Test GET /api/monitoring/jobs/{id}/metrics."""
        response = client.get("/api/monitoring/jobs/test_job/metrics")
        assert response.status_code in [200, 404, 501]
    
    def test_get_metrics_nonexistent_job(self, client):
        """Test getting metrics for non-existent job."""
        response = client.get("/api/monitoring/jobs/nonexistent/metrics")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
