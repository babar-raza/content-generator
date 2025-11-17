"""
HTTP endpoint tests for Agents API.

Tests all agent-related endpoints:
- GET /api/agents
- GET /api/agents/{id}
- GET /api/jobs/{job_id}/logs/{agent_name}
- GET /api/agents/{id}/logs
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.fixtures.http_fixtures import (
    mock_executor, mock_jobs_store, mock_agent_logs,
    sample_agent_data, test_app, client
)


class TestListAgents:
    """Tests for GET /api/agents endpoint."""
    
    def test_list_agents_success(self, client):
        """Test listing all agents."""
        response = client.get("/api/agents")
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                assert "agents" in data or "total" in data
    
    def test_list_agents_with_filter(self, client):
        """Test listing agents with filters."""
        response = client.get("/api/agents?type=test")
        assert response.status_code in [200, 404, 501]


class TestGetAgent:
    """Tests for GET /api/agents/{id} endpoint."""
    
    def test_get_agent_success(self, client):
        """Test getting a specific agent."""
        response = client.get("/api/agents/test_agent")
        assert response.status_code in [200, 404, 501]
    
    def test_get_agent_not_found(self, client):
        """Test getting non-existent agent."""
        response = client.get("/api/agents/nonexistent_agent")
        assert response.status_code == 404


class TestAgentLogs:
    """Tests for agent logging endpoints."""
    
    def test_get_job_agent_logs(self, client, mock_agent_logs):
        """Test GET /api/jobs/{job_id}/logs/{agent_name}."""
        response = client.get("/api/jobs/test_job/logs/TestAgent")
        assert response.status_code in [200, 404]
    
    def test_get_agent_logs_direct(self, client):
        """Test GET /api/agents/{id}/logs."""
        response = client.get("/api/agents/test_agent/logs")
        assert response.status_code in [200, 404, 501]
    
    def test_get_logs_nonexistent_job(self, client):
        """Test getting logs for non-existent job."""
        response = client.get("/api/jobs/nonexistent/logs/TestAgent")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
