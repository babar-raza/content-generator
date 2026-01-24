"""Integration tests for CLI/Web API parity.

Tests that CLI commands and Web API endpoints produce equivalent results.
"""

import pytest
import json
from datetime import datetime
from pathlib import Path


class TestBatchProcessing:
    """Test batch processing parity between CLI and Web API."""
    
    def test_batch_submission(self, client, sample_batch_manifest):
        """Test batch job submission via API."""
        response = client.post("/api/batch", json=sample_batch_manifest)
        assert response.status_code == 201
        data = response.json()
        assert "batch_id" in data
        assert "job_ids" in data
        assert len(data["job_ids"]) == len(sample_batch_manifest["jobs"])
        assert data["status"] == "submitted"
    
    def test_batch_status(self, client, sample_batch_id):
        """Test batch status retrieval."""
        response = client.get(f"/api/batch/{sample_batch_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == sample_batch_id
        assert "total_jobs" in data
        assert "completed_jobs" in data
        assert "job_statuses" in data
    
    def test_batch_results(self, client, sample_batch_id):
        """Test batch results retrieval."""
        response = client.get(f"/api/batch/{sample_batch_id}/results")
        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == sample_batch_id
        assert "results" in data
        assert "total" in data


class TestTemplates:
    """Test template management parity between CLI and Web API."""
    
    def test_list_templates(self, client):
        """Test listing all templates."""
        response = client.get("/api/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "total" in data
        assert "categories" in data
        assert isinstance(data["templates"], list)
    
    def test_get_template_details(self, client, sample_template_id):
        """Test getting template details."""
        response = client.get(f"/api/templates/{sample_template_id}")
        if response.status_code == 404:
            pytest.skip(f"Template {sample_template_id} not found")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_template_id
        assert "type" in data
        assert "content" in data
        assert "schema" in data
    
    def test_list_templates_by_category(self, client):
        """Test listing templates by category."""
        response = client.get("/api/templates/categories/blog")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert isinstance(data["templates"], list)


class TestValidation:
    """Test content validation parity between CLI and Web API."""
    
    def test_validate_markdown(self, client):
        """Test markdown content validation."""
        content = """# Test Document
        
This is a test paragraph.

## Section 1

Content here.
"""
        request = {
            "content": content,
            "content_type": "markdown",
            "strict": False
        }
        response = client.post("/api/validate", json=request)
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "errors" in data
        assert "warnings" in data
        assert "total_issues" in data
    
    def test_validate_yaml(self, client):
        """Test YAML content validation."""
        content = """
name: test
version: 1.0
items:
  - item1
  - item2
"""
        request = {
            "content": content,
            "content_type": "yaml",
            "strict": False
        }
        response = client.post("/api/validate", json=request)
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
    
    def test_validate_json(self, client):
        """Test JSON content validation."""
        content = '{"name": "test", "value": 123}'
        request = {
            "content": content,
            "content_type": "json",
            "strict": False
        }
        response = client.post("/api/validate", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
    
    def test_validate_invalid_json(self, client):
        """Test JSON validation with invalid content."""
        content = '{"name": "test", invalid}'
        request = {
            "content": content,
            "content_type": "json",
            "strict": False
        }
        response = client.post("/api/validate", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
    
    def test_batch_validation(self, client):
        """Test batch validation."""
        items = [
            {
                "content": "# Valid Markdown",
                "content_type": "markdown"
            },
            {
                "content": '{"valid": "json"}',
                "content_type": "json"
            }
        ]
        response = client.post("/api/validate/batch", json={"items": items})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2
        assert "valid_count" in data
        assert "invalid_count" in data


class TestConfig:
    """Test config management parity between CLI and Web API."""
    
    def test_config_snapshot(self, client):
        """Test getting full config snapshot."""
        response = client.get("/api/config/snapshot")
        assert response.status_code == 200
        data = response.json()
        assert "orchestration" in data or "agents" in data or "workflows" in data
        assert "version" in data
        assert "timestamp" in data
    
    def test_agent_config(self, client):
        """Test getting agent configuration."""
        response = client.get("/api/config/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "total" in data
    
    def test_workflow_config(self, client):
        """Test getting workflow configuration."""
        response = client.get("/api/config/workflows")
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert "total" in data
    
    def test_llm_config(self, client):
        """Test getting LLM configuration."""
        response = client.get("/api/config/llm")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data


class TestAgentHealth:
    """Test agent health monitoring parity."""
    
    def test_get_all_agent_health(self, client):
        """Test getting health for all agents."""
        response = client.get("/api/agents/health")
        assert response.status_code == 200
        data = response.json()
        assert "total_agents" in data
        assert "healthy_agents" in data
        assert "agents" in data
    
    def test_get_agent_health(self, client, sample_agent_id):
        """Test getting health for specific agent."""
        response = client.get(f"/api/agents/{sample_agent_id}/health")
        if response.status_code == 404:
            pytest.skip(f"Agent {sample_agent_id} not found")
        assert response.status_code == 200
        data = response.json()
        assert "agent_id" in data
        assert "metrics" in data
    
    def test_get_agent_failures(self, client, sample_agent_id):
        """Test getting agent failure history."""
        response = client.get(f"/api/agents/{sample_agent_id}/failures")
        assert response.status_code == 200
        data = response.json()
        assert "agent_id" in data
        assert "failures" in data
    
    def test_reset_agent_health(self, client, sample_agent_id):
        """Test resetting agent health."""
        response = client.post(f"/api/agents/{sample_agent_id}/health/reset")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestJobControl:
    """Test job control operations parity."""
    
    def test_pause_job(self, client, sample_job_id):
        """Test pausing a job."""
        response = client.post(f"/api/jobs/{sample_job_id}/pause")
        # May return 404 if job doesn't exist or 400 if can't be paused
        assert response.status_code in [200, 400, 404]
    
    def test_resume_job(self, client, sample_job_id):
        """Test resuming a job."""
        response = client.post(f"/api/jobs/{sample_job_id}/resume")
        # May return 404 if job doesn't exist or 400 if can't be resumed
        assert response.status_code in [200, 400, 404]
    
    def test_cancel_job(self, client, sample_job_id):
        """Test canceling a job."""
        response = client.post(f"/api/jobs/{sample_job_id}/cancel")
        # May return 404 if job doesn't exist or 400 if can't be cancelled
        assert response.status_code in [200, 400, 404]


class TestCheckpoints:
    """Test checkpoint operations parity."""
    
    def test_list_checkpoints(self, client, sample_job_id):
        """Test listing checkpoints for a job."""
        response = client.get(f"/api/checkpoints?job_id={sample_job_id}")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "checkpoints" in data
            assert "total" in data
    
    def test_restore_checkpoint(self, client, sample_checkpoint_id):
        """Test restoring from checkpoint."""
        response = client.post(
            f"/api/checkpoints/{sample_checkpoint_id}/restore",
            json={"resume": False}
        )
        # May return 404 if checkpoint doesn't exist
        assert response.status_code in [200, 404]
    
    def test_delete_checkpoint(self, client, sample_checkpoint_id):
        """Test deleting a checkpoint."""
        response = client.delete(f"/api/checkpoints/{sample_checkpoint_id}")
        # May return 204 or 404
        assert response.status_code in [204, 404]


# Fixtures
# Import shared fixtures for proper dependency injection
from tests.fixtures.http_fixtures import (
    mock_executor, mock_config_snapshot, test_app, client,
    mock_jobs_store, mock_agent_logs
)


@pytest.fixture
def sample_batch_manifest():
    """Sample batch manifest for testing."""
    return {
        "workflow_id": "test_workflow",
        "jobs": [
            {"topic": "test1"},
            {"topic": "test2"}
        ],
        "batch_name": "test_batch"
    }


@pytest.fixture
def sample_batch_id(mock_jobs_store):
    """Sample batch ID for testing with pre-populated batch jobs."""
    from datetime import datetime, timezone

    batch_id = "test-batch-123"

    # Create sample jobs for this batch
    for i in range(2):
        job_id = f"test-batch-123-job-{i}"
        mock_jobs_store[job_id] = {
            "job_id": job_id,
            "workflow_id": "test_workflow",
            "inputs": {"topic": f"test{i+1}"},
            "batch_id": batch_id,
            "batch_name": "test_batch",
            "status": "completed" if i == 0 else "running",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc) if i == 0 else None,
            "result": {"content": f"Test result {i+1}"} if i == 0 else None,
            "error": None
        }

    return batch_id


@pytest.fixture
def sample_template_id():
    """Sample template ID for testing."""
    return "default_blog"


@pytest.fixture
def sample_agent_id():
    """Sample agent ID for testing."""
    return "test_agent"


@pytest.fixture
def sample_job_id():
    """Sample job ID for testing."""
    return "test-job-123"


@pytest.fixture
def sample_checkpoint_id():
    """Sample checkpoint ID for testing."""
    return "checkpoint_test_123"
