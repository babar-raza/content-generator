"""
Comprehensive integration tests for agents API routes.

Tests all agent management endpoints:
- GET /api/agents - List agents
- GET /api/agents/health - Health summary
- GET /api/agents/{agent_id} - Get agent info
- GET /api/jobs/{job_id}/logs/{agent_name} - Job agent logs
- GET /api/agents/{agent_id}/logs - Agent logs
- GET /api/agents/{agent_id}/health - Agent health
- GET /api/agents/{agent_id}/failures - Agent failures
- POST /api/agents/{agent_id}/health/reset - Reset health
- GET /api/agents/{agent_id}/jobs - Agent job history
- GET /api/agents/{agent_id}/activity - Agent activity
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.web.routes import agents


@pytest.fixture
def app():
    """Create FastAPI app with agents router."""
    app = FastAPI()
    app.include_router(agents.router)
    return app


@pytest.fixture
def mock_store():
    """Create mock jobs store."""
    return {
        "job-1": {"job_id": "job-1", "status": "completed"},
        "job-2": {"job_id": "job-2", "status": "running"}
    }


@pytest.fixture
def mock_executor():
    """Create mock executor."""
    executor = Mock()
    executor.get_agents = Mock(return_value=[
        {"id": "agent-1", "name": "TestAgent1", "type": "content", "capabilities": ["generate"]},
        {"id": "agent-2", "name": "TestAgent2", "type": "research", "capabilities": ["search"]}
    ])
    executor.get_agent = Mock(side_effect=lambda id:
        {"id": id, "name": f"Agent-{id}", "type": "test", "capabilities": ["test"]}
        if id in ["agent-1", "agent-2"] else None
    )
    return executor


@pytest.fixture
def mock_agent_logs():
    """Create mock agent logs storage."""
    return {
        "job-1:agent-1": [
            {"timestamp": datetime.now(timezone.utc), "level": "INFO", "message": "Test log 1"},
            {"timestamp": datetime.now(timezone.utc), "level": "DEBUG", "message": "api_key=secret123"}
        ]
    }


@pytest.fixture
def mock_health_monitor():
    """Create mock health monitor."""
    from threading import RLock

    monitor = Mock()
    timestamp_str = datetime.now(timezone.utc).isoformat()

    # These internal attributes are accessed directly by route handlers
    monitor._lock = RLock()
    monitor.execution_history = {"agent-1": []}  # Dict for agent_id in checks
    monitor.recent_failures = {"agent-1": []}  # Dict for agent_id in checks

    monitor.get_health_summary = Mock(return_value={
        "timestamp": timestamp_str,
        "total_agents": 5,
        "healthy_agents": 3,
        "degraded_agents": 1,
        "failing_agents": 1,
        "unknown_agents": 0,
        "agents": [
            {
                "agent_id": "agent-1",
                "total_executions": 100,
                "successful_executions": 95,
                "failed_executions": 5,
                "last_execution_time": timestamp_str,
                "average_duration_ms": 150.5,
                "error_rate": 0.05,
                "status": "healthy"
            }
        ]
    })
    monitor.get_agent_health = Mock(return_value={
        "agent_id": "agent-1",
        "total_executions": 100,
        "successful_executions": 95,
        "failed_executions": 5,
        "last_execution_time": timestamp_str,
        "average_duration_ms": 150.5,
        "error_rate": 0.05,
        "status": "healthy"
    })
    monitor.get_agent_failures = Mock(return_value=[
        {
            "timestamp": timestamp_str,
            "agent_id": "agent-1",
            "job_id": "job-1",
            "error_type": "ValueError",
            "error_message": "Test error",
            "input_data": {},
            "stack_trace": "..."
        }
    ])
    monitor.get_agent_name = Mock(return_value="TestAgent")
    monitor.reset_agent_health = Mock()
    monitor.get_agent_job_history = Mock(return_value=[
        {"job_id": "job-1", "status": "completed"},
        {"job_id": "job-2", "status": "failed"}
    ])
    return monitor


@pytest.fixture
def client(app, mock_store, mock_executor, mock_agent_logs):
    """Create test client with mocked dependencies."""
    agents.set_jobs_store(mock_store)
    agents.set_executor(mock_executor)
    agents.set_agent_logs(mock_agent_logs)

    client = TestClient(app)
    yield client

    # Cleanup
    agents._jobs_store = None
    agents._executor = None
    agents._agent_logs = {}


class TestListAgents:
    """Tests for GET /api/agents endpoint."""

    def test_list_agents_success(self, client):
        """Test successful listing of agents."""
        response = client.get("/api/agents")

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert data["total"] == 2
        assert len(data["agents"]) == 2
        assert data["agents"][0]["agent_id"] == "agent-1"

    def test_list_agents_empty(self, app, mock_store, mock_agent_logs):
        """Test listing agents when none available."""
        executor = Mock()
        executor.get_agents = Mock(return_value=[])
        agents.set_executor(executor)

        client = TestClient(app)
        response = client.get("/api/agents")

        assert response.status_code == 200
        data = response.json()
        assert data["agents"] == []
        assert data["total"] == 0

        # Cleanup
        agents._executor = None

    def test_list_agents_no_get_agents_method(self, app, mock_store, mock_agent_logs):
        """Test listing agents when executor doesn't support get_agents."""
        executor = Mock(spec=[])  # Empty spec, no methods
        agents.set_executor(executor)

        client = TestClient(app)
        response = client.get("/api/agents")

        assert response.status_code == 200
        data = response.json()
        assert data["agents"] == []

        # Cleanup
        agents._executor = None


class TestGetAgent:
    """Tests for GET /api/agents/{agent_id} endpoint."""

    def test_get_agent_success(self, client):
        """Test getting an existing agent."""
        response = client.get("/api/agents/agent-1")

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "agent-1"
        assert data["name"] == "Agent-agent-1"
        assert data["type"] == "test"

    def test_get_agent_not_found(self, client):
        """Test getting a non-existent agent."""
        response = client.get("/api/agents/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_agent_no_support(self, app, mock_store, mock_agent_logs):
        """Test getting agent when executor doesn't support get_agent."""
        executor = Mock(spec=[])
        agents.set_executor(executor)

        client = TestClient(app)
        response = client.get("/api/agents/agent-1")

        assert response.status_code == 501
        assert "not supported" in response.json()["detail"]

        # Cleanup
        agents._executor = None


class TestJobAgentLogs:
    """Tests for GET /api/jobs/{job_id}/logs/{agent_name} endpoint."""

    def test_get_job_agent_logs_success(self, client):
        """Test getting logs for a job and agent."""
        response = client.get("/api/jobs/job-1/logs/agent-1")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-1"
        assert data["agent_name"] == "agent-1"
        assert data["total"] == 2
        assert len(data["logs"]) == 2

    def test_get_job_agent_logs_secrets_redacted(self, client):
        """Test that secrets are redacted from logs."""
        response = client.get("/api/jobs/job-1/logs/agent-1")

        data = response.json()
        logs = data["logs"]

        # Check that api_key is redacted
        secret_log = [l for l in logs if "api" in l["message"].lower()]
        assert len(secret_log) > 0
        assert "***REDACTED***" in secret_log[0]["message"]
        assert "secret123" not in secret_log[0]["message"]

    def test_get_job_agent_logs_pagination(self, client):
        """Test logs pagination."""
        response = client.get("/api/jobs/job-1/logs/agent-1?limit=1&offset=0")

        data = response.json()
        assert len(data["logs"]) == 1
        assert data["total"] == 2

    def test_get_job_agent_logs_job_not_found(self, client):
        """Test getting logs for non-existent job."""
        response = client.get("/api/jobs/nonexistent/logs/agent-1")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_job_agent_logs_no_logs(self, client):
        """Test getting logs when none exist."""
        response = client.get("/api/jobs/job-1/logs/unknown-agent")

        assert response.status_code == 200
        data = response.json()
        assert data["logs"] == []
        assert data["total"] == 0


class TestAgentLogs:
    """Tests for GET /api/agents/{agent_id}/logs endpoint."""

    def test_get_agent_logs_all_jobs(self, client):
        """Test getting logs for agent across all jobs."""
        response = client.get("/api/agents/agent-1/logs")

        assert response.status_code == 200
        data = response.json()
        assert data["agent_name"] == "agent-1"
        assert "logs" in data

    def test_get_agent_logs_specific_job(self, client):
        """Test getting logs for agent in specific job."""
        response = client.get("/api/agents/agent-1/logs?job_id=job-1")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-1"
        assert data["total"] == 2

    def test_get_agent_logs_pagination(self, client):
        """Test agent logs pagination."""
        response = client.get("/api/agents/agent-1/logs?limit=1")

        data = response.json()
        assert len(data["logs"]) <= 1

    def test_get_agent_logs_empty(self, client):
        """Test getting logs for agent with no logs."""
        response = client.get("/api/agents/unknown-agent/logs")

        assert response.status_code == 200
        data = response.json()
        assert data["logs"] == []


class TestAgentsHealthSummary:
    """Tests for GET /api/agents/health endpoint."""

    @patch('src.web.routes.agents.get_health_monitor')
    def test_get_health_summary_success(self, mock_get_monitor, client, mock_health_monitor):
        """Test getting overall health summary."""
        mock_get_monitor.return_value = mock_health_monitor

        response = client.get("/api/agents/health")

        assert response.status_code == 200
        data = response.json()
        assert data["total_agents"] == 5
        assert data["healthy_agents"] == 3
        assert data["degraded_agents"] == 1
        assert data["failing_agents"] == 1
        assert len(data["agents"]) == 1

    @patch('src.web.routes.agents.get_health_monitor')
    def test_get_health_summary_contains_metrics(self, mock_get_monitor, client, mock_health_monitor):
        """Test that health summary contains agent metrics."""
        mock_get_monitor.return_value = mock_health_monitor

        response = client.get("/api/agents/health")

        data = response.json()
        agent = data["agents"][0]
        assert agent["agent_id"] == "agent-1"
        assert agent["total_executions"] == 100
        assert agent["error_rate"] == 0.05


class TestAgentHealth:
    """Tests for GET /api/agents/{agent_id}/health endpoint."""

    @patch('src.web.routes.agents.get_health_monitor')
    def test_get_agent_health_success(self, mock_get_monitor, client, mock_health_monitor):
        """Test getting health for specific agent."""
        mock_get_monitor.return_value = mock_health_monitor

        response = client.get("/api/agents/agent-1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "agent-1"
        assert data["name"] == "TestAgent"
        assert data["metrics"]["total_executions"] == 100
        assert len(data["recent_failures"]) > 0

    @patch('src.web.routes.agents.get_health_monitor')
    def test_get_agent_health_includes_failures(self, mock_get_monitor, client, mock_health_monitor):
        """Test that agent health includes recent failures."""
        mock_get_monitor.return_value = mock_health_monitor

        response = client.get("/api/agents/agent-1/health")

        data = response.json()
        assert "recent_failures" in data
        assert len(data["recent_failures"]) == 1


class TestAgentFailures:
    """Tests for GET /api/agents/{agent_id}/failures endpoint."""

    @patch('src.web.routes.agents.get_health_monitor')
    def test_get_agent_failures_success(self, mock_get_monitor, client, mock_health_monitor):
        """Test getting failures for agent."""
        mock_get_monitor.return_value = mock_health_monitor

        response = client.get("/api/agents/agent-1/failures")

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "agent-1"
        assert data["total"] == 1
        assert len(data["failures"]) == 1

    @patch('src.web.routes.agents.get_health_monitor')
    def test_get_agent_failures_with_limit(self, mock_get_monitor, client, mock_health_monitor):
        """Test getting failures with custom limit."""
        mock_get_monitor.return_value = mock_health_monitor

        response = client.get("/api/agents/agent-1/failures?limit=5")

        assert response.status_code == 200
        # Verify limit was passed to monitor
        mock_health_monitor.get_agent_failures.assert_called_with("agent-1", limit=5)

    @patch('src.web.routes.agents.get_health_monitor')
    def test_get_agent_failures_contains_details(self, mock_get_monitor, client, mock_health_monitor):
        """Test that failures contain error details."""
        mock_get_monitor.return_value = mock_health_monitor

        response = client.get("/api/agents/agent-1/failures")

        data = response.json()
        failure = data["failures"][0]
        assert failure["error_type"] == "ValueError"
        assert failure["error_message"] == "Test error"
        assert "job_id" in failure


class TestResetAgentHealth:
    """Tests for POST /api/agents/{agent_id}/health/reset endpoint."""

    @patch('src.web.routes.agents.get_health_monitor')
    def test_reset_agent_health_success(self, mock_get_monitor, client, mock_health_monitor):
        """Test resetting agent health metrics."""
        mock_get_monitor.return_value = mock_health_monitor

        response = client.post("/api/agents/agent-1/health/reset")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["agent_id"] == "agent-1"

        # Verify monitor was called
        mock_health_monitor.reset_agent_health.assert_called_once_with("agent-1")

    @patch('src.web.routes.agents.get_health_monitor')
    def test_reset_agent_health_for_different_agents(self, mock_get_monitor, client, mock_health_monitor):
        """Test resetting health for different agents."""
        mock_get_monitor.return_value = mock_health_monitor

        agents_to_reset = ["agent-1", "agent-2", "agent-3"]

        for agent_id in agents_to_reset:
            response = client.post(f"/api/agents/{agent_id}/health/reset")
            assert response.status_code == 200
            assert response.json()["agent_id"] == agent_id


class TestAgentJobs:
    """Tests for GET /api/agents/{agent_id}/jobs endpoint."""

    @patch('src.web.routes.agents.get_health_monitor')
    def test_get_agent_jobs_success(self, mock_get_monitor, client, mock_health_monitor):
        """Test getting job history for agent."""
        mock_get_monitor.return_value = mock_health_monitor

        response = client.get("/api/agents/agent-1/jobs")

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "agent-1"
        assert data["total"] == 2
        assert len(data["jobs"]) == 2

    @patch('src.web.routes.agents.get_health_monitor')
    def test_get_agent_jobs_with_status_filter(self, mock_get_monitor, client, mock_health_monitor):
        """Test getting jobs filtered by status."""
        mock_get_monitor.return_value = mock_health_monitor

        response = client.get("/api/agents/agent-1/jobs?status=completed")

        assert response.status_code == 200
        data = response.json()
        assert all(job["status"] == "completed" for job in data["jobs"])

    @patch('src.web.routes.agents.get_health_monitor')
    def test_get_agent_jobs_with_limit(self, mock_get_monitor, client, mock_health_monitor):
        """Test getting jobs with custom limit."""
        mock_get_monitor.return_value = mock_health_monitor

        response = client.get("/api/agents/agent-1/jobs?limit=1")

        assert response.status_code == 200
        # Verify limit was passed
        mock_health_monitor.get_agent_job_history.assert_called()


class TestAgentActivity:
    """Tests for GET /api/agents/{agent_id}/activity endpoint."""

    @patch('src.web.routes.agents.get_health_monitor')
    def test_get_agent_activity_all_jobs(self, mock_get_monitor, client, mock_health_monitor):
        """Test getting activity for all jobs."""
        mock_get_monitor.return_value = mock_health_monitor

        response = client.get("/api/agents/agent-1/activity")

        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "agent-1"
        assert "activity" in data
        assert data["total"] == 2

    @patch('src.web.routes.agents.get_health_monitor')
    def test_get_agent_activity_specific_job(self, mock_get_monitor, client, mock_health_monitor):
        """Test getting activity for specific job."""
        mock_get_monitor.return_value = mock_health_monitor

        response = client.get("/api/agents/agent-1/activity?job_id=job-1")

        assert response.status_code == 200
        data = response.json()
        # Should filter to only job-1
        assert all(a["job_id"] == "job-1" for a in data["activity"])


class TestSecretRedaction:
    """Tests for secret redaction functionality."""

    def test_redact_api_key(self):
        """Test API key redaction."""
        text = 'apikey="secret123"'
        redacted = agents.redact_secrets(text)

        assert "***REDACTED***" in redacted
        assert "secret123" not in redacted

    def test_redact_password(self):
        """Test password redaction."""
        text = "password=mysecret123"
        redacted = agents.redact_secrets(text)

        assert "***REDACTED***" in redacted
        assert "mysecret123" not in redacted

    def test_redact_bearer_token(self):
        """Test Bearer token redaction."""
        text = "Authorization: Bearer abc123xyz"
        redacted = agents.redact_secrets(text)

        assert "***REDACTED***" in redacted
        assert "abc123xyz" not in redacted

    def test_redact_multiple_secrets(self):
        """Test multiple secret patterns."""
        text = 'api_key=secret1, password=secret2, token=secret3'
        redacted = agents.redact_secrets(text)

        assert "secret1" not in redacted
        assert "secret2" not in redacted
        assert "secret3" not in redacted
        assert redacted.count("***REDACTED***") == 3

    def test_redact_empty_string(self):
        """Test redacting empty string."""
        redacted = agents.redact_secrets("")
        assert redacted == ""

    def test_redact_none(self):
        """Test redacting None."""
        redacted = agents.redact_secrets(None)
        assert redacted is None


class TestDependencyInjection:
    """Tests for dependency injection validation."""

    def test_executor_not_initialized(self):
        """Test endpoints fail when executor not initialized."""
        app = FastAPI()
        app.include_router(agents.router)
        client = TestClient(app)

        response = client.get("/api/agents")

        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"]

    def test_jobs_store_not_initialized(self):
        """Test endpoints fail when jobs store not initialized."""
        app = FastAPI()
        app.include_router(agents.router)

        # Set executor but not store
        executor = Mock()
        agents.set_executor(executor)

        client = TestClient(app)
        response = client.get("/api/jobs/job-1/logs/agent-1")

        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"]

        # Cleanup
        agents._executor = None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
