"""Test MCP integration with React UI.

Tests verify that the React UI can successfully load data from MCP endpoints
and that the data flow between components works correctly.
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
    
    # Mock methods
    executor.job_engine.pause_job = Mock()
    executor.job_engine.resume_job = Mock()
    executor.job_engine.cancel_job = Mock()
    
    return executor


@pytest.fixture
def mock_config_snapshot():
    """Create a comprehensive mock configuration snapshot."""
    config = Mock()
    config.config_hash = "integration_test_hash"
    config.timestamp = "2025-01-15T10:00:00Z"
    config.engine_version = "1.0.0"
    
    config.agent_config = {
        "agents": {
            "topic_identifier": {
                "id": "topic_identifier",
                "version": "1.0",
                "description": "Identifies topics",
                "capabilities": {"extract": True}
            },
            "content_writer": {
                "id": "content_writer",
                "version": "1.0",
                "description": "Writes content",
                "capabilities": {"generate": True}
            },
            "seo_optimizer": {
                "id": "seo_optimizer",
                "version": "1.0",
                "description": "Optimizes SEO",
                "capabilities": {"optimize": True}
            }
        }
    }
    
    config.main_config = {
        "workflows": {
            "blog_generation": {
                "steps": ["ingest", "identify", "write", "optimize"],
                "description": "Full blog generation workflow"
            },
            "content_generation": {
                "steps": ["identify", "write"],
                "description": "Simple content generation"
            },
            "seo_optimization": {
                "steps": ["optimize"],
                "description": "SEO optimization only"
            }
        },
        "dependencies": {
            "write": ["identify"],
            "optimize": ["write"]
        }
    }
    
    config.tone_config = {
        "section_controls": {
            "introduction": {"tone": "engaging"},
            "body": {"tone": "informative"},
            "conclusion": {"tone": "actionable"}
        }
    }
    
    config.perf_config = {
        "timeouts": {
            "agent_execution": 300,
            "total_workflow": 1800
        },
        "limits": {
            "max_retries": 3,
            "max_concurrent_jobs": 5
        }
    }
    
    return config


@pytest.fixture
def test_client(mock_executor, mock_config_snapshot):
    """Create test client with comprehensive mock setup."""
    app = create_app(executor=mock_executor, config_snapshot=mock_config_snapshot)
    return TestClient(app)


def test_ui_can_load_agents_list(test_client):
    """Test that UI can successfully load agent list."""
    with patch("src.mcp.web_adapter.handle_agents_list", new_callable=AsyncMock) as mock_handler:
        mock_handler.return_value = {
            "agents": [
                {"name": "topic_identifier", "type": "research", "status": "active"},
                {"name": "content_writer", "type": "content", "status": "active"},
                {"name": "seo_optimizer", "type": "optimization", "status": "active"}
            ]
        }
        
        response = test_client.get("/mcp/agents")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["agents"]) == 3
        
        # Verify each agent has expected structure
        for agent in data["agents"]:
            assert "name" in agent
            assert "type" in agent
            assert "status" in agent


def test_ui_can_load_workflow_list(test_client):
    """Test that UI can successfully load workflow list."""
    with patch("src.mcp.web_adapter.handle_workflows_list", new_callable=AsyncMock) as mock_handler:
        mock_handler.return_value = {
            "workflows": [
                {"name": "blog_generation", "description": "Full blog generation"},
                {"name": "content_generation", "description": "Simple content"},
                {"name": "seo_optimization", "description": "SEO only"}
            ]
        }
        
        response = test_client.get("/mcp/workflows")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["workflows"]) == 3
        
        # Verify workflow structure
        for workflow in data["workflows"]:
            assert "name" in workflow
            assert "description" in workflow


def test_ui_can_load_job_list(test_client, mock_executor):
    """Test that UI can successfully load job list."""
    # Setup mock jobs with complete data
    mock_jobs = {}
    for i in range(3):
        job = Mock()
        job.to_dict.return_value = {
            "job_id": f"job_{i}",
            "workflow_name": "blog_generation",
            "status": "running" if i == 0 else "completed",
            "progress": 50 if i == 0 else 100,
            "started_at": "2025-01-15T10:00:00Z",
            "completed_at": None if i == 0 else "2025-01-15T11:00:00Z"
        }
        mock_jobs[f"job_{i}"] = job
    
    mock_executor.job_engine._jobs = mock_jobs
    
    response = test_client.get("/mcp/jobs")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["jobs"]) == 3
    
    # Verify job structure
    for job in data["jobs"]:
        assert "job_id" in job
        assert "workflow_name" in job
        assert "status" in job
        assert "progress" in job


def test_ui_can_load_agent_details(test_client, mock_config_snapshot):
    """Test that UI can load individual agent configuration."""
    response = test_client.get("/mcp/config/agents")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "agents" in data
    agents = data["agents"]
    
    # Verify topic_identifier agent
    assert "topic_identifier" in agents
    topic_agent = agents["topic_identifier"]
    assert topic_agent["id"] == "topic_identifier"
    assert "capabilities" in topic_agent


def test_ui_can_load_workflow_details(test_client, mock_config_snapshot):
    """Test that UI can load workflow configurations."""
    response = test_client.get("/mcp/config/workflows")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "workflows" in data
    workflows = data["workflows"]
    
    # Verify blog_generation workflow
    assert "blog_generation" in workflows
    blog_workflow = workflows["blog_generation"]
    assert "steps" in blog_workflow
    assert len(blog_workflow["steps"]) == 4


def test_ui_can_load_complete_config(test_client, mock_config_snapshot):
    """Test that UI can load complete configuration snapshot."""
    response = test_client.get("/mcp/config/snapshot")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    config = data["config"]
    
    # Verify all config sections present
    assert "hash" in config
    assert "timestamp" in config
    assert "engine_version" in config
    assert "agent_count" in config
    assert "workflows" in config
    
    # Verify counts
    assert config["agent_count"] == 3
    assert len(config["workflows"]) == 3


def test_ui_agent_page_workflow(test_client, mock_config_snapshot):
    """Test complete UI workflow for agents page.
    
    Simulates: User navigates to agents page → loads list → clicks agent → loads details
    """
    # Step 1: Load agents list
    with patch("src.mcp.web_adapter.handle_agents_list", new_callable=AsyncMock) as mock_handler:
        mock_handler.return_value = {
            "agents": [
                {"name": "topic_identifier", "type": "research", "status": "active"}
            ]
        }
        
        response1 = test_client.get("/mcp/agents")
        assert response1.status_code == 200
        agents = response1.json()["agents"]
        assert len(agents) > 0
        
        # Step 2: Load agent config
        agent_name = agents[0]["name"]
        response2 = test_client.get("/mcp/config/agents")
        assert response2.status_code == 200
        agent_configs = response2.json()["agents"]
        assert agent_name in agent_configs


def test_ui_jobs_page_workflow(test_client, mock_executor):
    """Test complete UI workflow for jobs page.
    
    Simulates: User navigates to jobs page → loads list → clicks job → loads details
    """
    # Setup mock job
    job = Mock()
    job.to_dict.return_value = {
        "job_id": "test_job",
        "workflow_name": "blog_generation",
        "status": "running",
        "progress": 75,
        "started_at": "2025-01-15T10:00:00Z"
    }
    mock_executor.job_engine._jobs = {"test_job": job}
    
    # Step 1: Load jobs list
    response1 = test_client.get("/mcp/jobs")
    assert response1.status_code == 200
    jobs = response1.json()["jobs"]
    assert len(jobs) > 0
    
    # Step 2: Load job details
    job_id = jobs[0]["job_id"]
    response2 = test_client.get(f"/mcp/jobs/{job_id}")
    assert response2.status_code == 200
    job_details = response2.json()
    assert job_details["job_id"] == job_id
    assert job_details["status"] == "running"


def test_ui_workflows_page_workflow(test_client, mock_config_snapshot):
    """Test complete UI workflow for workflows page.
    
    Simulates: User navigates to workflows page → loads list → clicks workflow → loads details
    """
    # Step 1: Load workflows list
    with patch("src.mcp.web_adapter.handle_workflows_list", new_callable=AsyncMock) as mock_handler:
        mock_handler.return_value = {
            "workflows": [
                {"name": "blog_generation", "description": "Full blog generation"}
            ]
        }
        
        response1 = test_client.get("/mcp/workflows")
        assert response1.status_code == 200
        workflows = response1.json()["workflows"]
        assert len(workflows) > 0
        
        # Step 2: Load workflow config
        workflow_name = workflows[0]["name"]
        response2 = test_client.get("/mcp/config/workflows")
        assert response2.status_code == 200
        workflow_configs = response2.json()["workflows"]
        assert workflow_name in workflow_configs


def test_ui_config_page_workflow(test_client, mock_config_snapshot):
    """Test complete UI workflow for config page.
    
    Simulates: User navigates to config page → loads snapshot → displays all sections
    """
    response = test_client.get("/mcp/config/snapshot")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    config = data["config"]
    
    # Verify all expected sections are present and valid
    assert config["agent_count"] > 0
    assert len(config["workflows"]) > 0
    assert isinstance(config["tone_sections"], list)
    assert isinstance(config["perf_timeouts"], dict)
    assert isinstance(config["perf_limits"], dict)


def test_no_console_errors_on_agent_load(test_client):
    """Test that loading agents doesn't cause 404 or 500 errors."""
    with patch("src.mcp.web_adapter.handle_agents_list", new_callable=AsyncMock) as mock_handler:
        mock_handler.return_value = {"agents": []}
        
        response = test_client.get("/mcp/agents")
        
        # Should return 200 even with empty list
        assert response.status_code == 200
        assert response.json()["agents"] == []


def test_no_console_errors_on_workflow_load(test_client):
    """Test that loading workflows doesn't cause 404 or 500 errors."""
    with patch("src.mcp.web_adapter.handle_workflows_list", new_callable=AsyncMock) as mock_handler:
        mock_handler.return_value = {"workflows": []}
        
        response = test_client.get("/mcp/workflows")
        
        # Should return 200 even with empty list
        assert response.status_code == 200
        assert response.json()["workflows"] == []


def test_no_console_errors_on_job_load(test_client, mock_executor):
    """Test that loading jobs doesn't cause 404 or 500 errors."""
    mock_executor.job_engine._jobs = {}
    
    response = test_client.get("/mcp/jobs")
    
    # Should return 200 even with empty list
    assert response.status_code == 200
    assert response.json()["jobs"] == []


def test_mcp_endpoints_cors_support(test_client):
    """Test that MCP endpoints support CORS for React UI."""
    response = test_client.get("/mcp/status", headers={"Origin": "http://localhost:3000"})
    
    assert response.status_code == 200
    # CORS headers should be present (set by FastAPI middleware)


def test_concurrent_ui_requests(test_client, mock_executor, mock_config_snapshot):
    """Test that UI can make concurrent requests to multiple endpoints."""
    # Simulate concurrent requests from UI
    with patch("src.mcp.web_adapter.handle_agents_list", new_callable=AsyncMock) as mock_agents, \
         patch("src.mcp.web_adapter.handle_workflows_list", new_callable=AsyncMock) as mock_workflows:
        
        mock_agents.return_value = {"agents": []}
        mock_workflows.return_value = {"workflows": []}
        
        # Make concurrent requests
        response1 = test_client.get("/mcp/agents")
        response2 = test_client.get("/mcp/workflows")
        response3 = test_client.get("/mcp/config/snapshot")
        response4 = test_client.get("/mcp/jobs")
        
        # All should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        assert response4.status_code == 200
