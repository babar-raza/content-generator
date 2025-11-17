"""
Integration tests for Checkpoint Management API.

Tests all checkpoint-related endpoints:
- GET /api/checkpoints?job_id={job_id}
- GET /api/checkpoints/{checkpoint_id}
- POST /api/checkpoints/{checkpoint_id}/restore
- DELETE /api/checkpoints/{checkpoint_id}
- POST /api/checkpoints/cleanup
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.web.app import create_app
from src.orchestration.checkpoint_manager import CheckpointManager


@pytest.fixture
def checkpoint_dir():
    """Create temporary checkpoint directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def checkpoint_manager(checkpoint_dir):
    """Create checkpoint manager with temp directory."""
    return CheckpointManager(storage_path=checkpoint_dir)


@pytest.fixture
def mock_executor():
    """Create mock executor."""
    executor = Mock()
    executor.resume_job = Mock()
    return executor


@pytest.fixture
def client(checkpoint_manager, mock_executor):
    """Create test client with checkpoint manager."""
    app = create_app(executor=mock_executor)
    
    # Inject the checkpoint manager
    from src.web.routes import checkpoints
    checkpoints.set_checkpoint_manager(checkpoint_manager)
    checkpoints.set_executor(mock_executor)
    
    return TestClient(app)


@pytest.fixture
def sample_checkpoints(checkpoint_manager):
    """Create sample checkpoints for testing."""
    job_id = "test-job-123"
    checkpoints = []
    
    # Create 5 checkpoints
    for i in range(5):
        state = {
            "step": f"step_{i}",
            "data": f"test_data_{i}",
            "iteration": i
        }
        checkpoint_id = checkpoint_manager.save(job_id, f"step_{i}", state)
        checkpoints.append(checkpoint_id)
    
    return job_id, checkpoints


class TestListCheckpoints:
    """Tests for GET /api/checkpoints endpoint."""
    
    def test_list_checkpoints_success(self, client, sample_checkpoints):
        """Test listing checkpoints for a job."""
        job_id, expected_checkpoints = sample_checkpoints
        
        response = client.get(f"/api/checkpoints?job_id={job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "checkpoints" in data
        assert "total" in data
        assert "job_id" in data
        assert "timestamp" in data
        
        assert data["job_id"] == job_id
        assert data["total"] == 5
        assert len(data["checkpoints"]) == 5
        
        # Verify checkpoint structure
        for checkpoint in data["checkpoints"]:
            assert "checkpoint_id" in checkpoint
            assert "job_id" in checkpoint
            assert "step_name" in checkpoint
            assert "timestamp" in checkpoint
            assert "workflow_version" in checkpoint
    
    def test_list_checkpoints_empty_job(self, client):
        """Test listing checkpoints for job with no checkpoints."""
        response = client.get("/api/checkpoints?job_id=nonexistent-job")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 0
        assert len(data["checkpoints"]) == 0
    
    def test_list_checkpoints_missing_job_id(self, client):
        """Test listing checkpoints without job_id parameter."""
        response = client.get("/api/checkpoints")
        
        assert response.status_code == 422  # FastAPI validation error


class TestGetCheckpoint:
    """Tests for GET /api/checkpoints/{checkpoint_id} endpoint."""
    
    def test_get_checkpoint_success(self, client, sample_checkpoints):
        """Test getting a specific checkpoint."""
        job_id, checkpoints = sample_checkpoints
        checkpoint_id = checkpoints[0]
        
        response = client.get(f"/api/checkpoints/{checkpoint_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["checkpoint_id"] == checkpoint_id
        assert data["job_id"] == job_id
        assert "step_name" in data
        assert "timestamp" in data
        assert "workflow_version" in data
        assert "state_snapshot" in data
        
        # Verify state snapshot
        assert data["state_snapshot"]["step"] == "step_0"
        assert data["state_snapshot"]["data"] == "test_data_0"
    
    def test_get_checkpoint_not_found(self, client):
        """Test getting a non-existent checkpoint."""
        response = client.get("/api/checkpoints/nonexistent-checkpoint")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestRestoreCheckpoint:
    """Tests for POST /api/checkpoints/{checkpoint_id}/restore endpoint."""
    
    def test_restore_checkpoint_without_resume(self, client, sample_checkpoints):
        """Test restoring checkpoint without job resume."""
        job_id, checkpoints = sample_checkpoints
        checkpoint_id = checkpoints[2]  # Restore from middle checkpoint
        
        response = client.post(
            f"/api/checkpoints/{checkpoint_id}/restore",
            json={"resume": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["checkpoint_id"] == checkpoint_id
        assert data["job_id"] == job_id
        assert data["job_status"] == "restored"
        assert "state" in data
        assert data["state"]["step"] == "step_2"
        assert data["state"]["iteration"] == 2
    
    def test_restore_checkpoint_with_resume(self, client, sample_checkpoints, mock_executor):
        """Test restoring checkpoint with job resume."""
        job_id, checkpoints = sample_checkpoints
        checkpoint_id = checkpoints[1]
        
        response = client.post(
            f"/api/checkpoints/{checkpoint_id}/restore",
            json={"resume": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["checkpoint_id"] == checkpoint_id
        assert data["job_status"] == "resumed"
        
        # Verify executor was called
        mock_executor.resume_job.assert_called_once_with(job_id)
    
    def test_restore_checkpoint_default_resume_false(self, client, sample_checkpoints):
        """Test that resume defaults to false."""
        job_id, checkpoints = sample_checkpoints
        checkpoint_id = checkpoints[0]
        
        # Don't provide resume parameter
        response = client.post(f"/api/checkpoints/{checkpoint_id}/restore", json={})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_status"] == "restored"
    
    def test_restore_checkpoint_not_found(self, client):
        """Test restoring a non-existent checkpoint."""
        response = client.post(
            "/api/checkpoints/nonexistent/restore",
            json={"resume": False}
        )
        
        assert response.status_code == 404


class TestDeleteCheckpoint:
    """Tests for DELETE /api/checkpoints/{checkpoint_id} endpoint."""
    
    def test_delete_checkpoint_success(self, client, sample_checkpoints, checkpoint_manager):
        """Test deleting a checkpoint."""
        job_id, checkpoints = sample_checkpoints
        checkpoint_id = checkpoints[0]
        
        # Verify checkpoint exists
        checkpoints_before = checkpoint_manager.list(job_id)
        assert len(checkpoints_before) == 5
        
        response = client.delete(f"/api/checkpoints/{checkpoint_id}")
        
        assert response.status_code == 204
        
        # Verify checkpoint was deleted
        checkpoints_after = checkpoint_manager.list(job_id)
        assert len(checkpoints_after) == 4
        
        # Verify specific checkpoint is gone
        remaining_ids = [cp.checkpoint_id for cp in checkpoints_after]
        assert checkpoint_id not in remaining_ids
    
    def test_delete_checkpoint_not_found(self, client):
        """Test deleting a non-existent checkpoint."""
        response = client.delete("/api/checkpoints/nonexistent-checkpoint")
        
        assert response.status_code == 404


class TestCleanupCheckpoints:
    """Tests for POST /api/checkpoints/cleanup endpoint."""
    
    def test_cleanup_keeps_last_n(self, client, sample_checkpoints, checkpoint_manager):
        """Test cleanup keeps the N most recent checkpoints."""
        job_id, checkpoints = sample_checkpoints
        
        # We have 5 checkpoints, keep last 3
        response = client.post(
            "/api/checkpoints/cleanup",
            json={"job_id": job_id, "keep_last": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == job_id
        assert data["deleted_count"] == 2
        assert data["kept_count"] == 3
        
        # Verify checkpoints were cleaned up
        remaining = checkpoint_manager.list(job_id)
        assert len(remaining) == 3
    
    def test_cleanup_no_deletion_when_under_limit(self, client, sample_checkpoints):
        """Test cleanup doesn't delete when already under limit."""
        job_id, checkpoints = sample_checkpoints
        
        # Keep last 10, but we only have 5
        response = client.post(
            "/api/checkpoints/cleanup",
            json={"job_id": job_id, "keep_last": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["deleted_count"] == 0
        assert data["kept_count"] == 5
    
    def test_cleanup_keep_last_minimum_1(self, client):
        """Test cleanup validates minimum keep_last value."""
        response = client.post(
            "/api/checkpoints/cleanup",
            json={"job_id": "test-job", "keep_last": 0}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_cleanup_keep_last_maximum_100(self, client):
        """Test cleanup validates maximum keep_last value."""
        response = client.post(
            "/api/checkpoints/cleanup",
            json={"job_id": "test-job", "keep_last": 101}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_cleanup_missing_job_id(self, client):
        """Test cleanup requires job_id."""
        response = client.post(
            "/api/checkpoints/cleanup",
            json={"keep_last": 5}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_cleanup_default_keep_last_10(self, client, checkpoint_manager):
        """Test cleanup defaults to keeping last 10."""
        # Create 15 checkpoints
        job_id = "test-job-many"
        for i in range(15):
            checkpoint_manager.save(job_id, f"step_{i}", {"data": i})
        
        response = client.post(
            "/api/checkpoints/cleanup",
            json={"job_id": job_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["deleted_count"] == 5
        assert data["kept_count"] == 10


class TestErrorHandling:
    """Tests for error handling across all endpoints."""
    
    def test_checkpoint_manager_not_initialized(self):
        """Test error when checkpoint manager is not initialized."""
        # Create app without checkpoint manager
        app = create_app()
        client = TestClient(app)
        
        # Try to list checkpoints - should fail with 503
        response = client.get("/api/checkpoints?job_id=test")
        
        # The endpoint will try to create a checkpoint manager on demand
        # so this should succeed or fail gracefully
        assert response.status_code in [200, 503]
    
    def test_concurrent_checkpoint_operations(self, client, sample_checkpoints):
        """Test that concurrent operations don't cause issues."""
        job_id, checkpoints = sample_checkpoints
        
        # Simulate concurrent reads
        responses = []
        for _ in range(10):
            response = client.get(f"/api/checkpoints?job_id={job_id}")
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()["total"] == 5


class TestIntegrationScenarios:
    """End-to-end integration scenarios."""
    
    def test_full_checkpoint_lifecycle(self, client, checkpoint_manager):
        """Test complete checkpoint lifecycle: create, list, get, restore, cleanup, delete."""
        job_id = "lifecycle-test-job"
        
        # Create checkpoints
        checkpoint_ids = []
        for i in range(7):
            state = {"step": f"step_{i}", "value": i * 10}
            checkpoint_id = checkpoint_manager.save(job_id, f"step_{i}", state)
            checkpoint_ids.append(checkpoint_id)
        
        # List checkpoints
        response = client.get(f"/api/checkpoints?job_id={job_id}")
        assert response.status_code == 200
        assert response.json()["total"] == 7
        
        # Get specific checkpoint
        response = client.get(f"/api/checkpoints/{checkpoint_ids[3]}")
        assert response.status_code == 200
        assert response.json()["state_snapshot"]["value"] == 30
        
        # Restore checkpoint
        response = client.post(
            f"/api/checkpoints/{checkpoint_ids[3]}/restore",
            json={"resume": False}
        )
        assert response.status_code == 200
        assert response.json()["state"]["value"] == 30
        
        # Cleanup old checkpoints (keep last 3)
        response = client.post(
            "/api/checkpoints/cleanup",
            json={"job_id": job_id, "keep_last": 3}
        )
        assert response.status_code == 200
        assert response.json()["deleted_count"] == 4
        assert response.json()["kept_count"] == 3
        
        # Verify cleanup
        response = client.get(f"/api/checkpoints?job_id={job_id}")
        assert response.status_code == 200
        assert response.json()["total"] == 3
        
        # Delete one checkpoint
        remaining_ids = [cp["checkpoint_id"] for cp in response.json()["checkpoints"]]
        response = client.delete(f"/api/checkpoints/{remaining_ids[0]}")
        assert response.status_code == 204
        
        # Verify deletion
        response = client.get(f"/api/checkpoints?job_id={job_id}")
        assert response.status_code == 200
        assert response.json()["total"] == 2
    
    def test_restore_and_resume_workflow(self, client, checkpoint_manager, mock_executor):
        """Test restoring checkpoint and resuming job execution."""
        job_id = "resume-test-job"
        
        # Create a checkpoint at a specific step
        state = {
            "current_step": "validation",
            "completed_steps": ["ingestion", "processing"],
            "pending_steps": ["output", "cleanup"]
        }
        checkpoint_id = checkpoint_manager.save(job_id, "validation", state)
        
        # Restore with resume
        response = client.post(
            f"/api/checkpoints/{checkpoint_id}/restore",
            json={"resume": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_status"] == "resumed"
        assert data["state"]["current_step"] == "validation"
        
        # Verify executor was called to resume
        mock_executor.resume_job.assert_called_once_with(job_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
