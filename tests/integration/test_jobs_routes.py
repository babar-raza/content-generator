"""
Comprehensive integration tests for jobs API routes.

Tests all job management endpoints:
- POST /api/jobs - Create job
- POST /api/generate - Generate content
- POST /api/batch - Batch job creation
- GET /api/jobs - List jobs
- GET /api/jobs/{job_id} - Get job status
- POST /api/jobs/{job_id}/pause - Pause job
- POST /api/jobs/{job_id}/resume - Resume job
- POST /api/jobs/{job_id}/cancel - Cancel job
- POST /api/jobs/{job_id}/archive - Archive job
- POST /api/jobs/{job_id}/unarchive - Unarchive job
- POST /api/jobs/{job_id}/retry - Retry failed job
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
import uuid

from src.web.routes import jobs


@pytest.fixture
def app():
    """Create FastAPI app with jobs router."""
    app = FastAPI()
    app.include_router(jobs.router)
    return app


@pytest.fixture
def mock_store():
    """Create mock jobs store."""
    return {}


@pytest.fixture
def mock_executor():
    """Create mock executor with all required methods."""
    executor = Mock()
    executor.submit_job = Mock()
    executor.pause_job = Mock()
    executor.resume_job = Mock()
    executor.cancel_job = Mock()
    executor.archive_job = Mock(return_value=True)
    executor.unarchive_job = Mock(return_value=True)
    executor.retry_job = Mock()
    return executor


@pytest.fixture
def client(app, mock_store, mock_executor):
    """Create test client with mocked dependencies."""
    jobs.set_jobs_store(mock_store)
    jobs.set_executor(mock_executor)

    client = TestClient(app)
    yield client

    # Cleanup
    jobs._jobs_store = None
    jobs._executor = None


class TestCreateJob:
    """Tests for POST /api/jobs endpoint."""

    def test_create_job_success(self, client, mock_store, mock_executor):
        """Test successful job creation."""
        response = client.post("/api/jobs", json={
            "workflow_id": "test_workflow",
            "inputs": {"topic": "AI Testing"}
        })

        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert data["status"] in ["created", "queued"]
        assert data["message"] == "Job created successfully"

        # Verify job was stored
        assert data["job_id"] in mock_store
        stored_job = mock_store[data["job_id"]]
        assert stored_job["workflow_id"] == "test_workflow"
        assert stored_job["inputs"] == {"topic": "AI Testing"}

    def test_create_job_submits_to_executor(self, client, mock_executor):
        """Test that job is submitted to executor."""
        response = client.post("/api/jobs", json={
            "workflow_id": "test_workflow",
            "inputs": {"topic": "Test"}
        })

        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Verify executor was called
        mock_executor.submit_job.assert_called_once()
        call_args = mock_executor.submit_job.call_args
        assert call_args[0][0] == "test_workflow"  # workflow_id is first
        assert call_args[0][2] == job_id  # job_id (correlation_id) is third

    def test_create_job_executor_failure(self, client, mock_executor, mock_store):
        """Test job creation when executor submission fails."""
        mock_executor.submit_job.side_effect = Exception("Executor error")

        response = client.post("/api/jobs", json={
            "workflow_id": "test_workflow",
            "inputs": {"topic": "Test"}
        })

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "failed"

        # Job should still be in store but marked failed
        stored_job = mock_store[data["job_id"]]
        assert stored_job["status"] == "failed"
        assert "error" in stored_job


class TestGenerateContent:
    """Tests for POST /api/generate endpoint."""

    def test_generate_content_success(self, client, mock_store):
        """Test successful content generation."""
        response = client.post("/api/generate", json={
            "topic": "Machine Learning",
            "template": "blog_post",
            "workflow": "default_blog"
        })

        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert "Machine Learning" in data["message"]

    def test_generate_content_with_metadata(self, client, mock_store):
        """Test content generation with metadata."""
        response = client.post("/api/generate", json={
            "topic": "AI Ethics",
            "template": "article",
            "metadata": {"author": "Test Author", "tags": ["ai", "ethics"]}
        })

        assert response.status_code == 201
        job_id = response.json()["job_id"]

        stored_job = mock_store[job_id]
        assert "metadata" in stored_job["inputs"]
        assert stored_job["inputs"]["metadata"]["author"] == "Test Author"

    def test_generate_content_with_config_overrides(self, client, mock_store):
        """Test content generation with config overrides."""
        response = client.post("/api/generate", json={
            "topic": "Testing",
            "template": "blog",
            "config_overrides": {"max_tokens": 1000}
        })

        assert response.status_code == 201
        job_id = response.json()["job_id"]

        stored_job = mock_store[job_id]
        assert stored_job["config_overrides"] == {"max_tokens": 1000}

    def test_generate_content_default_workflow(self, client, mock_store):
        """Test that default workflow is used when not specified."""
        response = client.post("/api/generate", json={
            "topic": "Testing",
            "template": "blog"
        })

        assert response.status_code == 201
        job_id = response.json()["job_id"]

        stored_job = mock_store[job_id]
        assert stored_job["workflow_id"] == "default_blog"


class TestBatchJobs:
    """Tests for POST /api/batch endpoint."""

    def test_create_batch_jobs_success(self, client, mock_store):
        """Test successful batch job creation."""
        response = client.post("/api/batch", json={
            "workflow_id": "batch_workflow",
            "batch_name": "Test Batch",
            "jobs": [
                {"topic": "Topic 1"},
                {"topic": "Topic 2"},
                {"topic": "Topic 3"}
            ]
        })

        assert response.status_code == 201
        data = response.json()
        assert "batch_id" in data
        assert len(data["job_ids"]) == 3
        assert "3 jobs created" in data["message"]

    def test_batch_jobs_stored_correctly(self, client, mock_store):
        """Test that batch jobs are stored with correct metadata."""
        response = client.post("/api/batch", json={
            "workflow_id": "batch_workflow",
            "batch_name": "Test Batch",
            "jobs": [{"topic": "Topic 1"}, {"topic": "Topic 2"}]
        })

        batch_id = response.json()["batch_id"]
        job_ids = response.json()["job_ids"]

        # Verify all jobs have batch metadata
        for job_id in job_ids:
            assert job_id in mock_store
            job = mock_store[job_id]
            assert job["batch_id"] == batch_id
            assert job["batch_name"] == "Test Batch"

    def test_batch_jobs_empty_list(self, client):
        """Test batch job creation with empty jobs list.

        Note: Empty jobs list may be accepted (201) or rejected (422) depending
        on validation rules. Both are valid API behaviors.
        """
        response = client.post("/api/batch", json={
            "workflow_id": "batch_workflow",
            "batch_name": "Empty Batch",
            "jobs": []
        })

        # API may reject empty batch (422) or accept it (201)
        assert response.status_code in [201, 422]
        if response.status_code == 201:
            data = response.json()
            assert len(data["job_ids"]) == 0


class TestListJobs:
    """Tests for GET /api/jobs endpoint."""

    def test_list_jobs_empty(self, client):
        """Test listing jobs when none exist."""
        response = client.get("/api/jobs")

        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["total"] == 0

    def test_list_jobs_with_data(self, client, mock_store):
        """Test listing jobs with existing data."""
        # Create test jobs
        for i in range(5):
            job_id = f"job-{i}"
            mock_store[job_id] = {
                "job_id": job_id,
                "status": "completed" if i % 2 == 0 else "running",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

        response = client.get("/api/jobs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 5
        assert data["total"] == 5

    def test_list_jobs_with_status_filter(self, client, mock_store):
        """Test listing jobs filtered by status."""
        # Create jobs with different statuses
        for i in range(6):
            job_id = f"job-{i}"
            status = "completed" if i < 2 else "running" if i < 4 else "failed"
            mock_store[job_id] = {
                "job_id": job_id,
                "status": status,
                "created_at": datetime.now(timezone.utc)
            }

        response = client.get("/api/jobs?status=completed")

        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 2
        assert data["total"] == 2
        assert all(job["status"] == "completed" for job in data["jobs"])

    def test_list_jobs_pagination(self, client, mock_store):
        """Test job listing with pagination."""
        # Create 10 jobs
        for i in range(10):
            job_id = f"job-{i}"
            mock_store[job_id] = {
                "job_id": job_id,
                "status": "completed",
                "created_at": datetime.now(timezone.utc)
            }

        response = client.get("/api/jobs?limit=5&offset=0")
        assert len(response.json()["jobs"]) == 5

        response = client.get("/api/jobs?limit=5&offset=5")
        assert len(response.json()["jobs"]) == 5

    def test_list_jobs_sorted_by_created_at(self, client, mock_store):
        """Test that jobs are sorted by created_at (newest first)."""
        from datetime import timedelta

        base_time = datetime.now(timezone.utc)
        for i in range(3):
            job_id = f"job-{i}"
            mock_store[job_id] = {
                "job_id": job_id,
                "status": "completed",
                "created_at": base_time - timedelta(hours=i)
            }

        response = client.get("/api/jobs")
        jobs = response.json()["jobs"]

        # Newest should be first (job-0 has most recent timestamp)
        assert jobs[0]["job_id"] == "job-0"


class TestGetJob:
    """Tests for GET /api/jobs/{job_id} endpoint."""

    def test_get_job_success(self, client, mock_store):
        """Test getting an existing job."""
        job_id = "test-job-123"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "running",
            "progress": 50,
            "current_stage": "content_generation",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        response = client.get(f"/api/jobs/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "running"
        assert data["progress"] == 50
        assert data["current_stage"] == "content_generation"

    def test_get_job_not_found(self, client):
        """Test getting a non-existent job."""
        response = client.get("/api/jobs/nonexistent-job")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_job_with_result(self, client, mock_store):
        """Test getting a completed job with result."""
        job_id = "completed-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "result": {"output_path": "/path/to/output.md"},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc)
        }

        response = client.get(f"/api/jobs/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"] == {"output_path": "/path/to/output.md"}


class TestPauseJob:
    """Tests for POST /api/jobs/{job_id}/pause endpoint."""

    def test_pause_running_job(self, client, mock_store, mock_executor):
        """Test pausing a running job."""
        job_id = "running-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "running",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/pause")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"
        assert data["action"] == "pause"

        # Verify executor was called
        mock_executor.pause_job.assert_called_once_with(job_id)

        # Verify job status updated
        assert mock_store[job_id]["status"] == "paused"

    def test_pause_queued_job(self, client, mock_store):
        """Test pausing a queued job."""
        job_id = "queued-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/pause")
        assert response.status_code == 200

    def test_pause_completed_job_fails(self, client, mock_store):
        """Test that pausing a completed job fails."""
        job_id = "completed-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "created_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/pause")

        assert response.status_code == 400
        assert "Cannot pause" in response.json()["detail"]

    def test_pause_nonexistent_job(self, client):
        """Test pausing a non-existent job."""
        response = client.post("/api/jobs/nonexistent/pause")

        assert response.status_code == 404


class TestResumeJob:
    """Tests for POST /api/jobs/{job_id}/resume endpoint."""

    def test_resume_paused_job(self, client, mock_store, mock_executor):
        """Test resuming a paused job."""
        job_id = "paused-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "paused",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/resume")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["action"] == "resume"

        # Verify executor was called
        mock_executor.resume_job.assert_called_once_with(job_id)

        # Verify job status updated
        assert mock_store[job_id]["status"] == "running"

    def test_resume_running_job_fails(self, client, mock_store):
        """Test that resuming a running job fails."""
        job_id = "running-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "running",
            "created_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/resume")

        assert response.status_code == 400
        assert "Cannot resume" in response.json()["detail"]

    def test_resume_nonexistent_job(self, client):
        """Test resuming a non-existent job."""
        response = client.post("/api/jobs/nonexistent/resume")

        assert response.status_code == 404


class TestCancelJob:
    """Tests for POST /api/jobs/{job_id}/cancel endpoint."""

    def test_cancel_running_job(self, client, mock_store, mock_executor):
        """Test cancelling a running job."""
        job_id = "running-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "running",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["action"] == "cancel"

        # Verify executor was called
        mock_executor.cancel_job.assert_called_once_with(job_id)

        # Verify job status updated
        assert mock_store[job_id]["status"] == "cancelled"
        assert "completed_at" in mock_store[job_id]

    def test_cancel_completed_job_fails(self, client, mock_store):
        """Test that cancelling a completed job fails."""
        job_id = "completed-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "created_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/cancel")

        assert response.status_code == 400
        assert "Cannot cancel" in response.json()["detail"]

    def test_cancel_already_cancelled_job_fails(self, client, mock_store):
        """Test that cancelling an already cancelled job fails."""
        job_id = "cancelled-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "cancelled",
            "created_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/cancel")

        assert response.status_code == 400


class TestArchiveJob:
    """Tests for POST /api/jobs/{job_id}/archive endpoint."""

    def test_archive_completed_job(self, client, mock_store, mock_executor):
        """Test archiving a completed job."""
        job_id = "completed-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/archive")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"
        assert data["action"] == "archive"

    def test_archive_failed_job(self, client, mock_store):
        """Test archiving a failed job."""
        job_id = "failed-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "failed",
            "created_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/archive")
        assert response.status_code == 200

    def test_archive_running_job_fails(self, client, mock_store):
        """Test that archiving a running job fails."""
        job_id = "running-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "running",
            "created_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/archive")

        assert response.status_code == 400
        assert "Cannot archive" in response.json()["detail"]

    def test_archive_nonexistent_job(self, client):
        """Test archiving a non-existent job."""
        response = client.post("/api/jobs/nonexistent/archive")

        assert response.status_code == 404


class TestUnarchiveJob:
    """Tests for POST /api/jobs/{job_id}/unarchive endpoint."""

    def test_unarchive_archived_job(self, client, mock_store, mock_executor):
        """Test unarchiving an archived job."""
        job_id = "archived-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "archived",
            "completed_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/unarchive")

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "unarchive"
        assert "job_id" in data

    def test_unarchive_completed_job_fails(self, client, mock_store):
        """Test that unarchiving a completed (non-archived) job fails."""
        job_id = "completed-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "created_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/unarchive")

        assert response.status_code == 400
        assert "Cannot unarchive" in response.json()["detail"]

    def test_unarchive_archived_job_with_error(self, client, mock_store, mock_executor):
        """Test unarchiving an archived job that has an error."""
        job_id = "archived-failed"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "archived",
            "error": "Some error",
            "created_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/unarchive")
        assert response.status_code == 200
        assert response.json()["action"] == "unarchive"


class TestRetryJob:
    """Tests for POST /api/jobs/{job_id}/retry endpoint."""

    def test_retry_failed_job(self, client, mock_store, mock_executor):
        """Test retrying a failed job."""
        job_id = "failed-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "failed",
            "workflow_id": "test_workflow",
            "inputs": {"topic": "Test"},
            "retry_count": 0,
            "max_retries": 3,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/retry")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "retrying"
        assert data["action"] == "retry"
        assert "attempt 1/3" in data["message"]

        # Verify retry count incremented
        assert mock_store[job_id]["retry_count"] == 1
        assert mock_store[job_id]["error"] is None

    def test_retry_completed_job_fails(self, client, mock_store):
        """Test that retrying a completed job fails."""
        job_id = "completed-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "created_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/retry")

        assert response.status_code == 400
        assert "Cannot retry" in response.json()["detail"]

    def test_retry_exceeds_max_retries(self, client, mock_store):
        """Test that retry fails when max retries exceeded."""
        job_id = "failed-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "failed",
            "retry_count": 3,
            "max_retries": 3,
            "created_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/retry")

        assert response.status_code == 400
        assert "exceeded maximum retries" in response.json()["detail"]

    def test_retry_increments_count(self, client, mock_store, mock_executor):
        """Test that retry correctly increments retry count."""
        job_id = "failed-job"
        mock_store[job_id] = {
            "job_id": job_id,
            "status": "failed",
            "workflow_id": "test",
            "inputs": {},
            "retry_count": 1,
            "max_retries": 5,
            "created_at": datetime.now(timezone.utc)
        }

        response = client.post(f"/api/jobs/{job_id}/retry")

        assert response.status_code == 200
        assert mock_store[job_id]["retry_count"] == 2
        assert "attempt 2/5" in response.json()["message"]


class TestDependencyInjection:
    """Tests for dependency injection and error handling."""

    def test_jobs_store_not_initialized(self):
        """Test that endpoints fail when jobs store not initialized."""
        app = FastAPI()
        app.include_router(jobs.router)
        client = TestClient(app)

        response = client.get("/api/jobs")

        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"]

    def test_executor_not_initialized(self, mock_store):
        """Test that endpoints fail when executor not initialized."""
        app = FastAPI()
        app.include_router(jobs.router)
        jobs.set_jobs_store(mock_store)

        client = TestClient(app)

        response = client.post("/api/jobs", json={
            "workflow_id": "test",
            "inputs": {}
        })

        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"]

        # Cleanup
        jobs._jobs_store = None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
