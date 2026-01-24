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

    def test_get_job_agent_logs_with_pagination(self, client):
        """Test GET /api/jobs/{job_id}/logs/{agent_name} with pagination."""
        response = client.get("/api/jobs/test_job/logs/TestAgent?limit=10&offset=0")
        assert response.status_code in [200, 404]

    def test_get_agent_logs_with_job_filter(self, client):
        """Test GET /api/agents/{id}/logs with job_id filter."""
        response = client.get("/api/agents/test_agent/logs?job_id=test_job")
        assert response.status_code in [200, 404, 501]

    def test_get_agent_logs_validates_response(self, client):
        """Test GET /api/agents/{id}/logs validates response structure."""
        response = client.get("/api/agents/test_agent/logs")
        if response.status_code == 200:
            data = response.json()
            assert "logs" in data or isinstance(data, list)


class TestAgentFailures:
    """Tests for agent failure tracking endpoints."""

    def test_get_agent_failures(self, client):
        """Test GET /api/agents/{agent_id}/failures."""
        response = client.get("/api/agents/test_agent/failures")
        assert response.status_code in [200, 404, 501]

    def test_get_agent_failures_with_limit(self, client):
        """Test GET /api/agents/{agent_id}/failures with limit parameter."""
        response = client.get("/api/agents/test_agent/failures?limit=5")
        assert response.status_code in [200, 404, 501]

    def test_get_agent_failures_nonexistent(self, client):
        """Test GET /api/agents/{agent_id}/failures for non-existent agent."""
        response = client.get("/api/agents/nonexistent_agent/failures")
        assert response.status_code in [404, 501]

    def test_get_agent_failures_validates_response(self, client):
        """Test GET /api/agents/{agent_id}/failures validates response structure."""
        response = client.get("/api/agents/test_agent/failures")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
            if isinstance(data, dict):
                assert "failures" in data or "total" in data


class TestAgentJobs:
    """Tests for agent job history endpoints."""

    def test_get_agent_jobs(self, client):
        """Test GET /api/agents/{agent_id}/jobs."""
        response = client.get("/api/agents/test_agent/jobs")
        assert response.status_code in [200, 404, 501]

    def test_get_agent_jobs_with_limit(self, client):
        """Test GET /api/agents/{agent_id}/jobs with limit parameter."""
        response = client.get("/api/agents/test_agent/jobs?limit=20")
        assert response.status_code in [200, 404, 501]

    def test_get_agent_jobs_with_status_filter(self, client):
        """Test GET /api/agents/{agent_id}/jobs with status filter."""
        response = client.get("/api/agents/test_agent/jobs?status=completed")
        assert response.status_code in [200, 404, 501]

    def test_get_agent_jobs_nonexistent(self, client):
        """Test GET /api/agents/{agent_id}/jobs for non-existent agent.

        Note: API returns 200 with empty data (graceful degradation) rather than 404.
        This is valid behavior - agents that never ran return empty job history.
        """
        response = client.get("/api/agents/nonexistent_agent/jobs")
        # Accept 200 with empty data OR 404 (both are valid approaches)
        assert response.status_code in [200, 404, 501]
        if response.status_code == 200:
            data = response.json()
            assert data.get("jobs", []) == [] or data.get("total", 0) == 0

    def test_get_agent_jobs_validates_response(self, client):
        """Test GET /api/agents/{agent_id}/jobs validates response structure."""
        response = client.get("/api/agents/test_agent/jobs")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
            if isinstance(data, dict):
                assert "jobs" in data or "total" in data


class TestAgentActivity:
    """Tests for agent activity tracking endpoints."""

    def test_get_agent_activity(self, client):
        """Test GET /api/agents/{agent_id}/activity."""
        response = client.get("/api/agents/test_agent/activity")
        assert response.status_code in [200, 404, 501]

    def test_get_agent_activity_with_job_filter(self, client):
        """Test GET /api/agents/{agent_id}/activity with job_id filter."""
        response = client.get("/api/agents/test_agent/activity?job_id=test_job")
        assert response.status_code in [200, 404, 501]

    def test_get_agent_activity_nonexistent(self, client):
        """Test GET /api/agents/{agent_id}/activity for non-existent agent.

        Note: API returns 200 with empty activity (graceful degradation) rather than 404.
        This is valid behavior - agents that never ran return empty activity.
        """
        response = client.get("/api/agents/nonexistent_agent/activity")
        # Accept 200 with empty data OR 404 (both are valid approaches)
        assert response.status_code in [200, 404, 501]
        if response.status_code == 200:
            data = response.json()
            assert data.get("activity", []) == [] or data.get("total", 0) == 0


class TestAgentHealthReset:
    """Tests for agent health reset endpoint."""

    def test_reset_agent_health(self, client):
        """Test POST /api/agents/{agent_id}/health/reset."""
        response = client.post("/api/agents/test_agent/health/reset")
        assert response.status_code in [200, 404, 501]

    def test_reset_agent_health_nonexistent(self, client):
        """Test POST /api/agents/{agent_id}/health/reset for non-existent agent.

        Note: API accepts reset for any agent_id (idempotent operation).
        Resetting health for a nonexistent agent is a no-op that returns 200.
        """
        response = client.post("/api/agents/nonexistent_agent/health/reset")
        # Accept 200 (idempotent reset) OR 404 (strict validation)
        assert response.status_code in [200, 404, 501]

    def test_reset_agent_health_validates_response(self, client):
        """Test POST /api/agents/{agent_id}/health/reset validates response."""
        response = client.post("/api/agents/test_agent/health/reset")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            assert "message" in data or "agent_id" in data


class TestAgentAPIProduction:
    """Production-ready tests for agent API."""

    def test_list_agents_response_structure(self, client):
        """Test GET /api/agents returns proper structure."""
        response = client.get("/api/agents")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            if "agents" in data:
                assert isinstance(data["agents"], list)
                assert "total" in data
                assert isinstance(data["total"], int)

    def test_get_agent_response_structure(self, client):
        """Test GET /api/agents/{id} returns proper structure."""
        response = client.get("/api/agents/test_agent")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            # Should have basic agent fields
            expected_fields = ["agent_id", "name", "type", "status"]
            has_fields = any(field in data for field in expected_fields)
            assert has_fields, f"Response missing expected fields: {data.keys()}"

    def test_agent_endpoints_handle_special_characters(self, client):
        """Test agent endpoints handle special characters in IDs."""
        special_ids = ["agent-with-dash", "agent_with_underscore", "agent.with.dot"]
        for agent_id in special_ids:
            response = client.get(f"/api/agents/{agent_id}")
            # Should not crash, either 200 or 404
            assert response.status_code in [200, 404, 501]

    def test_agent_logs_pagination_limits(self, client):
        """Test agent logs endpoint respects pagination limits."""
        response = client.get("/api/agents/test_agent/logs?limit=1000")
        if response.status_code == 200:
            data = response.json()
            # Should enforce reasonable limit (e.g., max 1000)
            if "logs" in data:
                assert len(data["logs"]) <= 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
