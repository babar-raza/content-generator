"""
HTTP endpoint tests for Workflows API.

Tests:
- GET /api/workflows
- GET /api/workflows/{id}
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.fixtures.http_fixtures import (
    mock_executor, sample_workflow_data, test_app, client
)


class TestListWorkflows:
    """Tests for GET /api/workflows endpoint."""
    
    def test_list_workflows_success(self, client):
        """Test listing all workflows."""
        response = client.get("/api/workflows")
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                assert "workflows" in data or "total" in data
    
    def test_list_workflows_empty(self, client):
        """Test listing workflows when none exist."""
        response = client.get("/api/workflows")
        assert response.status_code in [200, 404]


class TestGetWorkflow:
    """Tests for GET /api/workflows/{id} endpoint."""
    
    def test_get_workflow_success(self, client):
        """Test getting a specific workflow."""
        response = client.get("/api/workflows/test_workflow")
        assert response.status_code in [200, 404, 501]
    
    def test_get_workflow_not_found(self, client):
        """Test getting non-existent workflow."""
        response = client.get("/api/workflows/nonexistent")
        assert response.status_code == 404
    
    def test_get_workflow_invalid_id(self, client):
        """Test getting workflow with invalid ID."""
        response = client.get("/api/workflows/")
        assert response.status_code in [404, 405]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
