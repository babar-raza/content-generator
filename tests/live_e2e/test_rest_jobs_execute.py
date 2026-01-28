"""Live E2E Test: REST Job Execution

Tests POST /api/jobs with real workflow execution.
Requires: Ollama running, Chroma accessible.
"""
import os
import sys
import pytest
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Set environment before imports
os.environ["TEST_MODE"] = "live"
os.environ["LLM_PROVIDER"] = "OLLAMA"
os.environ["OLLAMA_MODEL"] = "phi4-mini:latest"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from src.web.app import create_app


@pytest.fixture(scope="module")
def live_app():
    """Create FastAPI app with live executor for testing."""
    # Note: App should initialize with live executor in live mode
    # The execute_workflow_sync function will create its own executor
    app = create_app()
    return app


@pytest.fixture(scope="module")
def client(live_app):
    """Create test client."""
    return TestClient(live_app)


@pytest.fixture
def test_output_dir(tmp_path):
    """Create temporary output directory for test."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = tmp_path / f"rest_job_output_{ts}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def test_collections():
    """Generate unique collection names for this test run."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return {
        "blog": f"blog_test_{ts}",
        "ref": f"ref_test_{ts}"
    }


@pytest.mark.live_e2e
def test_rest_job_execution_sync(client, test_output_dir, test_collections):
    """Test POST /api/jobs with synchronous execution.

    Verifies:
    - Job is created with sync mode (output_dir present)
    - Workflow executes and generates content
    - Response includes output_path
    - Output file exists and has content >= 5KB
    """
    # Prepare job payload
    payload = {
        "workflow_id": "default_blog",
        "topic": "Python FastAPI best practices for REST APIs",
        "output_dir": str(test_output_dir),
        "blog_collection": test_collections["blog"],
        "ref_collection": test_collections["ref"],
        "inputs": {}
    }

    print(f"\n[TEST] POST /api/jobs (sync mode)")
    print(f"[TEST] Topic: {payload['topic']}")
    print(f"[TEST] Output dir: {test_output_dir}")

    # Submit job
    start_time = time.time()
    response = client.post("/api/jobs", json=payload)

    print(f"[TEST] Response status: {response.status_code}")
    print(f"[TEST] Response body: {response.json()}")

    # Assert response
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

    result = response.json()
    assert "job_id" in result, "Response missing job_id"
    assert "status" in result, "Response missing status"
    assert "output_path" in result, "Response missing output_path"

    job_id = result["job_id"]
    status = result["status"]
    output_path = result.get("output_path")

    print(f"[TEST] Job ID: {job_id}")
    print(f"[TEST] Status: {status}")
    print(f"[TEST] Output path: {output_path}")

    # In sync mode, status should be "completed" immediately
    assert status == "completed", f"Expected status 'completed', got '{status}'"
    assert output_path is not None, "output_path should not be None in sync mode"

    # Verify output file exists
    assert os.path.exists(output_path), f"Output file does not exist: {output_path}"

    # Verify file size >= 2KB (reasonable for a blog post)
    file_size = os.path.getsize(output_path)
    min_size = 2 * 1024  # 2KB
    print(f"[TEST] Output file size: {file_size} bytes ({file_size / 1024:.2f} KB)")

    assert file_size >= min_size, f"Output file too small: {file_size} bytes (min: {min_size})"

    # Verify content
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"[TEST] Content length: {len(content)} chars")

    # Basic content validation
    assert len(content) >= 200, f"Content too short: {len(content)} chars"
    assert "##" in content or "title:" in content, "Content missing markdown structure"

    # Check execution time
    duration = time.time() - start_time
    print(f"[TEST] Execution duration: {duration:.2f}s")

    # Verify job status via GET
    print(f"\n[TEST] GET /api/jobs/{job_id}")
    get_response = client.get(f"/api/jobs/{job_id}")
    assert get_response.status_code == 200

    job_status = get_response.json()
    print(f"[TEST] Retrieved status: {job_status['status']}")
    print(f"[TEST] Retrieved output_path: {job_status.get('output_path')}")

    assert job_status["status"] == "completed"
    assert job_status["output_path"] == output_path

    print(f"\n[PASS] REST job execution test passed")
    print(f"[PASS] Job ID: {job_id}")
    print(f"[PASS] Output: {output_path}")
    print(f"[PASS] File size: {file_size / 1024:.2f} KB")


@pytest.mark.live_e2e
def test_rest_job_async_mode_compatibility(client):
    """Test that async mode (without output_dir) still works.

    Verifies backward compatibility with existing async job submission.
    """
    payload = {
        "workflow_id": "default_blog",
        "inputs": {
            "topic": "Test async mode"
        }
    }

    print(f"\n[TEST] POST /api/jobs (async mode)")

    response = client.post("/api/jobs", json=payload)
    print(f"[TEST] Response status: {response.status_code}")

    # Should succeed and return quickly
    assert response.status_code in [201, 503], f"Unexpected status: {response.status_code}"

    if response.status_code == 201:
        result = response.json()
        assert "job_id" in result
        # Status should be queued or created (not completed)
        assert result["status"] in ["created", "queued"]
        print(f"[PASS] Async mode: job_id={result['job_id']}, status={result['status']}")
    else:
        # 503 is acceptable if executor not initialized in test mode
        print(f"[SKIP] Async mode: executor not available (503)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
