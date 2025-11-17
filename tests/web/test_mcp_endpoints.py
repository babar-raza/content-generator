"""Test MCP web endpoints.

Tests verify that all MCP REST endpoints are properly mounted and return
correct responses without making actual network calls.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from src.web.app import create_app


@pytest.fixture
def mock_executor():
    """Create a mock executor with job engine."""
    executor = Mock()
    executor.job_engine = Mock()
    executor.job_engine._jobs = {}
    return executor


@pytest.fixture
def mock_config_snapshot():
    """Create a mock configuration snapshot."""
    config = Mock()
    config.config_hash = "test_hash_12345678"
    config.timestamp = "2025-01-15T10:00:00Z"
    config.engine_version = "1.0.0"
    config.agent_config = {
        "agents": {
            "topic_identifier": {
                "id": "topic_identifier",
                "version": "1.0",
                "description": "Identifies topics from content",
                "capabilities": {}
            },
            "content_writer": {
                "id": "content_writer",
                "version": "1.0",
                "description": "Writes content",
                "capabilities": {}
            }
        }
    }
    config.main_config = {
        "workflows": {
            "blog_generation": {"steps": []},
            "content_generation": {"steps": []}
        },
        "dependencies": {}
    }
    config.tone_config = {"section_controls": {}}
    config.perf_config = {"timeouts": {}, "limits": {}}
    return config


@pytest.fixture
def test_client(mock_executor, mock_config_snapshot):
    """Create test client with mocked dependencies."""
    app = create_app(executor=mock_executor, config_snapshot=mock_config_snapshot)
    return TestClient(app)


def test_mcp_agents_endpoint(test_client):
    """Test /mcp/agents returns agent list."""
    with patch("src.mcp.web_adapter.handle_agents_list", new_callable=AsyncMock) as mock_handler:
        mock_handler.return_value = {
            "agents": [
                {
                    "name": "topic_identifier",
                    "type": "research",
                    "status": "active"
                },
                {
                    "name": "content_writer",
                    "type": "content",
                    "status": "active"
                }
            ]
        }
        
        response = test_client.get("/mcp/agents")
        
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)
        assert len(data["agents"]) == 2
        assert data["agents"][0]["name"] == "topic_identifier"
        assert data["agents"][1]["name"] == "content_writer"


def test_mcp_workflows_endpoint(test_client):
    """Test /mcp/workflows returns workflow list."""
    with patch("src.mcp.web_adapter.handle_workflows_list", new_callable=AsyncMock) as mock_handler:
        mock_handler.return_value = {
            "workflows": [
                {
                    "name": "blog_generation",
                    "description": "Generate blog post from KB article"
                },
                {
                    "name": "content_generation",
                    "description": "General content generation"
                }
            ]
        }
        
        response = test_client.get("/mcp/workflows")
        
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert isinstance(data["workflows"], list)
        assert len(data["workflows"]) == 2
        assert data["workflows"][0]["name"] == "blog_generation"


def test_mcp_jobs_endpoint(test_client, mock_executor):
    """Test /mcp/jobs returns job list."""
    # Setup mock jobs
    mock_job1 = Mock()
    mock_job1.to_dict.return_value = {
        "job_id": "job1",
        "workflow_name": "blog_generation",
        "status": "running",
        "progress": 50,
        "started_at": "2025-01-15T10:00:00Z"
    }
    
    mock_job2 = Mock()
    mock_job2.to_dict.return_value = {
        "job_id": "job2",
        "workflow_name": "content_generation",
        "status": "completed",
        "progress": 100,
        "started_at": "2025-01-15T09:00:00Z"
    }
    
    mock_executor.job_engine._jobs = {
        "job1": mock_job1,
        "job2": mock_job2
    }
    
    response = test_client.get("/mcp/jobs")
    
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert isinstance(data["jobs"], list)
    assert len(data["jobs"]) == 2


def test_mcp_jobs_with_status_filter(test_client, mock_executor):
    """Test /mcp/jobs with status filter."""
    response = test_client.get("/mcp/jobs?status=running")
    
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert isinstance(data["jobs"], list)


def test_mcp_jobs_with_limit(test_client, mock_executor):
    """Test /mcp/jobs with limit parameter."""
    response = test_client.get("/mcp/jobs?limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data


def test_mcp_job_detail_endpoint(test_client, mock_executor):
    """Test /mcp/jobs/{job_id} returns job details."""
    mock_job = Mock()
    mock_job.to_dict.return_value = {
        "job_id": "test-job-1",
        "workflow_name": "blog_generation",
        "status": "running",
        "progress": 75
    }
    
    mock_executor.job_engine._jobs = {"test-job-1": mock_job}
    
    response = test_client.get("/mcp/jobs/test-job-1")
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "test-job-1"
    assert data["status"] == "running"


def test_mcp_config_snapshot_endpoint(test_client, mock_config_snapshot):
    """Test /mcp/config/snapshot returns config."""
    response = test_client.get("/mcp/config/snapshot")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
    assert "config" in data
    assert isinstance(data["config"], dict)
    assert "hash" in data["config"]
    assert "timestamp" in data["config"]


def test_mcp_config_agents_endpoint(test_client, mock_config_snapshot):
    """Test /mcp/config/agents returns agent configs."""
    response = test_client.get("/mcp/config/agents")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
    assert "agents" in data
    assert isinstance(data["agents"], dict)
    assert len(data["agents"]) == 2


def test_mcp_config_workflows_endpoint(test_client, mock_config_snapshot):
    """Test /mcp/config/workflows returns workflow configs."""
    response = test_client.get("/mcp/config/workflows")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
    assert "workflows" in data
    assert isinstance(data["workflows"], dict)


def test_mcp_status_endpoint(test_client):
    """Test /mcp/status returns status info."""
    response = test_client.get("/mcp/status")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "executor_initialized" in data
    assert "config_initialized" in data


def test_mcp_methods_endpoint(test_client):
    """Test /mcp/methods returns available methods."""
    response = test_client.get("/mcp/methods")
    
    assert response.status_code == 200
    data = response.json()
    assert "methods" in data
    assert isinstance(data["methods"], list)
    assert len(data["methods"]) > 0


def test_mcp_invalid_endpoint(test_client):
    """Test invalid MCP endpoint returns 404."""
    response = test_client.get("/mcp/invalid-endpoint-that-does-not-exist")
    
    assert response.status_code == 404


def test_mcp_agents_error_handling(test_client):
    """Test agents endpoint handles errors gracefully."""
    with patch("src.mcp.web_adapter.handle_agents_list", new_callable=AsyncMock) as mock_handler:
        mock_handler.side_effect = Exception("Test error")
        
        response = test_client.get("/mcp/agents")
        
        assert response.status_code == 500


def test_mcp_workflows_error_handling(test_client):
    """Test workflows endpoint handles errors gracefully."""
    with patch("src.mcp.web_adapter.handle_workflows_list", new_callable=AsyncMock) as mock_handler:
        mock_handler.side_effect = Exception("Test error")
        
        response = test_client.get("/mcp/workflows")
        
        assert response.status_code == 500


def test_mcp_jobs_error_handling(test_client, mock_executor):
    """Test jobs endpoint handles errors gracefully."""
    mock_executor.job_engine._jobs = None  # Cause an error
    
    response = test_client.get("/mcp/jobs")
    
    # Should still return 200 with empty jobs list due to error handling in handler
    assert response.status_code == 200
    data = response.json()
    assert data["jobs"] == []


def test_mcp_job_not_found(test_client, mock_executor):
    """Test /mcp/jobs/{job_id} returns 404 for non-existent job."""
    mock_executor.job_engine._jobs = {}
    
    response = test_client.get("/mcp/jobs/non-existent-job")
    
    assert response.status_code == 404


def test_mcp_config_without_snapshot(mock_executor):
    """Test config endpoints when config snapshot is not available."""
    app = create_app(executor=mock_executor, config_snapshot=None)
    client = TestClient(app)
    
    response = client.get("/mcp/config/snapshot")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unavailable"


def test_mcp_config_agents_without_snapshot(mock_executor):
    """Test config/agents endpoint when config snapshot is not available."""
    app = create_app(executor=mock_executor, config_snapshot=None)
    client = TestClient(app)
    
    response = client.get("/mcp/config/agents")
    
    assert response.status_code == 503


def test_mcp_config_workflows_without_snapshot(mock_executor):
    """Test config/workflows endpoint when config snapshot is not available."""
    app = create_app(executor=mock_executor, config_snapshot=None)
    client = TestClient(app)
    
    response = client.get("/mcp/config/workflows")
    
    assert response.status_code == 503
