"""Integration test: MCP workflow.list alias must work."""

import pytest
from fastapi.testclient import TestClient


def test_mcp_workflow_list_alias():
    """Test that POST /mcp/request with method=workflow.list (singular) returns non-empty workflows."""
    from src.web.app import create_app

    # Create app without executor
    app = create_app(executor=None)
    client = TestClient(app)

    # MCP request with workflow.list (singular form - the alias)
    mcp_request = {
        "method": "workflow.list",
        "params": {},
        "id": "test-1"
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

    # Assert workflows list exists and is non-empty
    assert "workflows" in result, "Result should contain 'workflows' field"
    assert isinstance(result["workflows"], list), "workflows should be a list"
    assert len(result["workflows"]) >= 1, f"Expected at least 1 workflow, got {len(result['workflows'])}"

    print(f"✓ MCP workflow.list returned {len(result['workflows'])} workflow(s)")
