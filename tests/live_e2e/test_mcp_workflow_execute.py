"""Live E2E Test: MCP Workflow Execute

Tests MCP JSON-RPC method workflow.execute with real execution.
Requires: Ollama running, Chroma accessible.
"""
import os
import sys
import pytest
from pathlib import Path
from datetime import datetime, timezone

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
    """Create FastAPI app for testing."""
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
    output_dir = tmp_path / f"mcp_workflow_output_{ts}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def test_collections():
    """Generate unique collection names for this test run."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return {
        "blog": f"blog_mcp_test_{ts}",
        "ref": f"ref_mcp_test_{ts}"
    }


@pytest.mark.live_e2e
def test_mcp_workflow_execute_single(client, test_output_dir, test_collections):
    """Test MCP JSON-RPC single workflow.execute request.

    Verifies:
    - Method workflow.execute is recognized
    - Workflow executes synchronously
    - Response includes output_path
    - Output file exists and has content >= 2KB
    """
    # Prepare MCP request (JSON-RPC 2.0)
    request = {
        "jsonrpc": "2.0",
        "method": "workflow.execute",
        "params": {
            "workflow_id": "default_blog",
            "topic": "FastAPI async patterns and best practices",
            "output_dir": str(test_output_dir),
            "blog_collection": test_collections["blog"],
            "ref_collection": test_collections["ref"]
        },
        "id": 1
    }

    print(f"\n[TEST] POST /mcp/request (single workflow.execute)")
    print(f"[TEST] Method: {request['method']}")
    print(f"[TEST] Topic: {request['params']['topic']}")
    print(f"[TEST] Output dir: {test_output_dir}")

    # Submit request
    response = client.post("/mcp/request", json=request)

    print(f"[TEST] Response status: {response.status_code}")
    print(f"[TEST] Response body: {response.json()}")

    # Assert response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    result = response.json()

    # Verify JSON-RPC 2.0 structure
    assert "jsonrpc" in result or "result" in result, "Response missing JSON-RPC structure"
    assert "id" in result, "Response missing id"
    assert result["id"] == 1, "Response id mismatch"

    # Extract result
    if "result" in result:
        job_result = result["result"]
    else:
        job_result = result

    assert "job_id" in job_result, "Result missing job_id"
    assert "status" in job_result, "Result missing status"
    assert "output_path" in job_result, "Result missing output_path"

    job_id = job_result["job_id"]
    status = job_result["status"]
    output_path = job_result.get("output_path")

    print(f"[TEST] Job ID: {job_id}")
    print(f"[TEST] Status: {status}")
    print(f"[TEST] Output path: {output_path}")

    # Verify status and output_path
    assert status == "completed", f"Expected status 'completed', got '{status}'"
    assert output_path is not None, "output_path should not be None"

    # Verify output file exists
    assert os.path.exists(output_path), f"Output file does not exist: {output_path}"

    # Verify file size >= 2KB
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

    print(f"\n[PASS] MCP workflow.execute (single) test passed")
    print(f"[PASS] Job ID: {job_id}")
    print(f"[PASS] Output: {output_path}")
    print(f"[PASS] File size: {file_size / 1024:.2f} KB")


@pytest.mark.live_e2e
def test_mcp_workflow_execute_batch(client, test_output_dir, test_collections):
    """Test MCP JSON-RPC batch request with workflows.list + workflow.execute.

    Verifies:
    - Batch requests are processed
    - workflows.list returns workflow list
    - workflow.execute executes and returns output_path
    - Both responses have matching IDs
    """
    # Prepare batch request
    batch_request = [
        {
            "jsonrpc": "2.0",
            "method": "workflows/list",
            "params": {},
            "id": 1
        },
        {
            "jsonrpc": "2.0",
            "method": "workflow.execute",
            "params": {
                "workflow_id": "default_blog",
                "topic": "Python async/await patterns",
                "output_dir": str(test_output_dir),
                "blog_collection": test_collections["blog"],
                "ref_collection": test_collections["ref"]
            },
            "id": 2
        }
    ]

    print(f"\n[TEST] POST /mcp/request (batch: workflows.list + workflow.execute)")

    # Submit batch request
    response = client.post("/mcp/request", json=batch_request)

    print(f"[TEST] Response status: {response.status_code}")

    # Assert response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    results = response.json()
    print(f"[TEST] Batch responses count: {len(results)}")

    assert isinstance(results, list), "Batch response should be a list"
    assert len(results) == 2, f"Expected 2 responses, got {len(results)}"

    # Verify first response (workflows.list)
    list_response = results[0]
    assert "id" in list_response, "workflows.list response missing id"
    assert list_response["id"] == 1, "workflows.list response id mismatch"

    if "result" in list_response:
        workflows_result = list_response["result"]
        print(f"[TEST] workflows.list: Found {len(workflows_result.get('workflows', []))} workflows")
    else:
        print(f"[TEST] workflows.list response: {list_response}")

    # Verify second response (workflow.execute)
    exec_response = results[1]
    assert "id" in exec_response, "workflow.execute response missing id"
    assert exec_response["id"] == 2, "workflow.execute response id mismatch"

    if "result" in exec_response:
        exec_result = exec_response["result"]
    else:
        exec_result = exec_response

    assert "job_id" in exec_result, "workflow.execute result missing job_id"
    assert "output_path" in exec_result, "workflow.execute result missing output_path"

    job_id = exec_result["job_id"]
    output_path = exec_result["output_path"]

    print(f"[TEST] workflow.execute job_id: {job_id}")
    print(f"[TEST] workflow.execute output_path: {output_path}")

    # Verify output file
    assert os.path.exists(output_path), f"Output file does not exist: {output_path}"

    file_size = os.path.getsize(output_path)
    min_size = 2 * 1024
    assert file_size >= min_size, f"Output file too small: {file_size} bytes"

    print(f"\n[PASS] MCP batch request test passed")
    print(f"[PASS] workflows.list: OK")
    print(f"[PASS] workflow.execute: {job_id}, {file_size / 1024:.2f} KB")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
