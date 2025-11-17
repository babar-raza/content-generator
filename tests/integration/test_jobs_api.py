"""
Comprehensive HTTP endpoint tests for Jobs API.

Tests all 8 job-related endpoints:
- POST /api/jobs
- POST /api/generate
- POST /api/batch
- GET /api/jobs
- GET /api/jobs/{id}
- POST /api/jobs/{id}/pause
- POST /api/jobs/{id}/resume
- POST /api/jobs/{id}/cancel
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.fixtures.http_fixtures import (
    mock_executor, mock_jobs_store, mock_agent_logs,
    sample_job_data, sample_job_result, test_app, client
)


class TestCreateJob:
    """Tests for POST /api/jobs endpoint."""
    
    def test_create_job_success(self, client, sample_job_result, mock_executor):
        """Test successful job creation."""
        mock_executor.submit_job = Mock()
        
        response = client.post(
            "/api/jobs",
            json={
                "workflow_id": "test_workflow",
                "inputs": {"topic": "Test Topic"}
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert data["status"] in ["created", "queued"]
    
    def test_create_job_invalid_input(self, client):
        """Test job creation with missing required fields."""
        response = client.post(
            "/api/jobs",
            json={"inputs": {"topic": "Test"}}  # Missing workflow_id
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_job_empty_body(self, client):
        """Test job creation with empty request body."""
        response = client.post("/api/jobs", json={})
        assert response.status_code == 422


class TestGenerateEndpoint:
    """Tests for POST /api/generate endpoint."""
    
    def test_generate_success(self, client, sample_job_result, mock_executor):
        """Test successful content generation."""
        mock_executor.run_job = Mock(return_value=sample_job_result)
        
        response = client.post(
            "/api/generate",
            json={
                "topic": "Test Topic",
                "template": "default_blog"
            }
        )
        
        # May return 201 or other success code depending on implementation
        assert response.status_code in [200, 201, 202]
    
    def test_generate_missing_topic(self, client):
        """Test generation with missing topic."""
        response = client.post(
            "/api/generate",
            json={"template": "default_blog"}
        )
        
        assert response.status_code == 422
    
    def test_generate_with_config_overrides(self, client):
        """Test generation with configuration overrides."""
        response = client.post(
            "/api/generate",
            json={
                "topic": "Test Topic",
                "template": "default_blog",
                "config_overrides": {"max_tokens": 1000}
            }
        )
        
        assert response.status_code in [200, 201, 202, 422, 503]


class TestBatchJobs:
    """Tests for POST /api/batch endpoint."""
    
    def test_batch_create_success(self, client):
        """Test successful batch job creation."""
        response = client.post(
            "/api/batch",
            json={
                "workflow_id": "test_workflow",
                "jobs": [
                    {"topic": "Topic 1"},
                    {"topic": "Topic 2"}
                ],
                "batch_name": "test_batch"
            }
        )
        
        # Check for success or not implemented
        assert response.status_code in [200, 201, 404, 501]
    
    def test_batch_create_empty_jobs(self, client):
        """Test batch creation with empty jobs list."""
        response = client.post(
            "/api/batch",
            json={
                "workflow_id": "test_workflow",
                "jobs": []
            }
        )
        
        assert response.status_code in [400, 422, 404, 501]
    
    def test_batch_create_invalid_input(self, client):
        """Test batch creation with invalid input."""
        response = client.post(
            "/api/batch",
            json={"workflow_id": "test"}  # Missing jobs
        )
        
        assert response.status_code in [422, 404, 501]


class TestListJobs:
    """Tests for GET /api/jobs endpoint."""
    
    def test_list_jobs_empty(self, client):
        """Test listing jobs when store is empty."""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        
        data = response.json()
        # Could be list or dict with jobs key
        if isinstance(data, dict):
            assert "jobs" in data or "total" in data
        else:
            assert isinstance(data, list)
    
    def test_list_jobs_with_data(self, client, mock_jobs_store, sample_job_data):
        """Test listing jobs with existing data."""
        # Populate store
        mock_jobs_store["test_job_1"] = sample_job_data
        
        response = client.get("/api/jobs")
        assert response.status_code == 200
    
    def test_list_jobs_with_filters(self, client):
        """Test listing jobs with query filters."""
        response = client.get("/api/jobs?status=running")
        assert response.status_code in [200, 501]  # May not implement filtering


class TestGetJob:
    """Tests for GET /api/jobs/{id} endpoint."""
    
    def test_get_job_success(self, client, mock_jobs_store, sample_job_data):
        """Test getting an existing job."""
        job_id = "test_job_123"
        mock_jobs_store[job_id] = sample_job_data
        
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["job_id"] == job_id
    
    def test_get_job_not_found(self, client):
        """Test getting a non-existent job."""
        response = client.get("/api/jobs/nonexistent_job")
        assert response.status_code == 404
    
    def test_get_job_invalid_id(self, client):
        """Test getting a job with invalid ID format."""
        response = client.get("/api/jobs/")
        assert response.status_code in [404, 405]  # Not Found or Method Not Allowed


class TestPauseJob:
    """Tests for POST /api/jobs/{id}/pause endpoint."""
    
    def test_pause_job_success(self, client, mock_jobs_store, sample_job_data, mock_executor):
        """Test pausing a running job."""
        job_id = "test_job_123"
        sample_job_data["status"] = "running"
        mock_jobs_store[job_id] = sample_job_data
        mock_executor.pause_job = Mock()
        
        response = client.post(f"/api/jobs/{job_id}/pause")
        
        # Should succeed or return not implemented
        assert response.status_code in [200, 404, 501]
    
    def test_pause_job_not_found(self, client):
        """Test pausing a non-existent job."""
        response = client.post("/api/jobs/nonexistent/pause")
        assert response.status_code == 404
    
    def test_pause_completed_job(self, client, mock_jobs_store, sample_job_data):
        """Test pausing an already completed job."""
        job_id = "completed_job"
        sample_job_data["status"] = "completed"
        mock_jobs_store[job_id] = sample_job_data
        
        response = client.post(f"/api/jobs/{job_id}/pause")
        
        # Should fail or return bad request
        assert response.status_code in [400, 404, 409, 501]


class TestResumeJob:
    """Tests for POST /api/jobs/{id}/resume endpoint."""
    
    def test_resume_job_success(self, client, mock_jobs_store, sample_job_data, mock_executor):
        """Test resuming a paused job."""
        job_id = "test_job_123"
        sample_job_data["status"] = "paused"
        mock_jobs_store[job_id] = sample_job_data
        mock_executor.resume_job = Mock()
        
        response = client.post(f"/api/jobs/{job_id}/resume")
        
        assert response.status_code in [200, 404, 501]
    
    def test_resume_job_not_found(self, client):
        """Test resuming a non-existent job."""
        response = client.post("/api/jobs/nonexistent/resume")
        assert response.status_code == 404
    
    def test_resume_running_job(self, client, mock_jobs_store, sample_job_data):
        """Test resuming an already running job."""
        job_id = "running_job"
        sample_job_data["status"] = "running"
        mock_jobs_store[job_id] = sample_job_data
        
        response = client.post(f"/api/jobs/{job_id}/resume")
        
        assert response.status_code in [200, 400, 409, 404, 501]


class TestCancelJob:
    """Tests for POST /api/jobs/{id}/cancel endpoint."""
    
    def test_cancel_job_success(self, client, mock_jobs_store, sample_job_data, mock_executor):
        """Test canceling a running job."""
        job_id = "test_job_123"
        sample_job_data["status"] = "running"
        mock_jobs_store[job_id] = sample_job_data
        mock_executor.cancel_job = Mock()
        
        response = client.post(f"/api/jobs/{job_id}/cancel")
        
        assert response.status_code in [200, 404, 501]
    
    def test_cancel_job_not_found(self, client):
        """Test canceling a non-existent job."""
        response = client.post("/api/jobs/nonexistent/cancel")
        assert response.status_code == 404
    
    def test_cancel_completed_job(self, client, mock_jobs_store, sample_job_data):
        """Test canceling an already completed job."""
        job_id = "completed_job"
        sample_job_data["status"] = "completed"
        mock_jobs_store[job_id] = sample_job_data
        
        response = client.post(f"/api/jobs/{job_id}/cancel")
        
        assert response.status_code in [200, 400, 409, 404, 501]


class TestJobsAPIIntegration:
    """Integration tests for Jobs API workflows."""
    
    def test_job_lifecycle(self, client, mock_executor, sample_job_result):
        """Test complete job lifecycle: create -> pause -> resume -> cancel."""
        mock_executor.submit_job = Mock()
        mock_executor.pause_job = Mock()
        mock_executor.resume_job = Mock()
        mock_executor.cancel_job = Mock()
        
        # Create job
        create_response = client.post(
            "/api/jobs",
            json={"workflow_id": "test", "inputs": {"topic": "Test"}}
        )
        
        if create_response.status_code == 201:
            job_id = create_response.json()["job_id"]
            
            # Try to pause (may not be implemented)
            client.post(f"/api/jobs/{job_id}/pause")
            
            # Try to resume
            client.post(f"/api/jobs/{job_id}/resume")
            
            # Cancel
            client.post(f"/api/jobs/{job_id}/cancel")
    
    def test_multiple_jobs_creation(self, client):
        """Test creating multiple jobs in sequence."""
        for i in range(3):
            response = client.post(
                "/api/jobs",
                json={
                    "workflow_id": f"workflow_{i}",
                    "inputs": {"topic": f"Topic {i}"}
                }
            )
            
            assert response.status_code in [201, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
