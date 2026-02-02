"""Integration test: MCP workflow.execute smoke test."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock
from datetime import datetime


def test_mcp_workflow_execute_smoke():
    """Test that POST /mcp/request with workflow.execute returns job_id and output_path."""
    from src.web.app import create_app
    from src.engine.engine import JobResult, JobStatus

    # Create mock executor

    mock_executor = Mock()
    mock_result = JobResult(
        job_id="test_job_123",
        status=JobStatus.COMPLETED,
        output_path="output/test_job_123.md",
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    mock_executor.run_job = Mock(return_value=mock_result)

    # Create app with mock executor
    app = create_app(executor=mock_executor)
    client = TestClient(app)

    # MCP request with workflow.execute
    mcp_request = {
        "method": "workflow.execute",
        "params": {
            "workflow_id": "blog_workflow",
            "inputs": {"topic": "Test Topic"}
        },
        "id": "test-exec-1"
    }

    # Call /mcp/request
    response = client.post("/mcp/request", json=mcp_request)

    # Assert response is successful
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # Parse response
    data = response.json()

    # Assert MCP response structure
    assert "result" in data or "error" not in data, f"MCP request should not have error: {data}"

    # Get result
    result = data.get("result", {})

    # Assert job_id exists
    assert "job_id" in result, "Result should contain job_id"
    assert result["job_id"] == "test_job_123", f"Expected job_id='test_job_123', got {result['job_id']}"

    # Assert status and uri exist (basic smoke test)
    assert "status" in result, "Result should contain status"
    assert "uri" in result, "Result should contain uri"

    print(f"[OK] MCP workflow.execute returned job_id={result['job_id']}, status={result['status']}, uri={result['uri']}")


def test_mcp_batch_workflow_execute():
    """Test that batch MCP requests work for workflow.execute."""
    from src.web.app import create_app
    from src.engine.engine import JobResult, JobStatus
    from datetime import datetime

    # Create mock executor
    mock_executor = Mock()
    mock_result = JobResult(
        job_id="batch_job",
        status=JobStatus.COMPLETED,
        output_path="output/batch_job.md",
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    mock_executor.run_job = Mock(return_value=mock_result)

    # Create app with mock executor
    app = create_app(executor=mock_executor)
    client = TestClient(app)

    # Batch MCP request
    batch_request = [
        {
            "method": "workflow.list",
            "params": {},
            "id": "batch-1"
        },
        {
            "method": "workflow.execute",
            "params": {
                "workflow_id": "blog_workflow",
                "inputs": {"topic": "Batch Test"}
            },
            "id": "batch-2"
        }
    ]

    # Call /mcp/request with batch
    response = client.post("/mcp/request", json=batch_request)

    # Assert response is successful
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # Parse response (should be a list)
    data = response.json()
    assert isinstance(data, list), "Batch response should be a list"
    assert len(data) == 2, f"Expected 2 responses, got {len(data)}"

    print(f"[OK] Batch MCP request returned {len(data)} responses")
