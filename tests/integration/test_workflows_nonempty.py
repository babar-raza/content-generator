"""Integration test: /api/workflows must return non-empty list."""

import pytest
from fastapi.testclient import TestClient


def test_workflows_endpoint_returns_nonempty():
    """Test that /api/workflows returns at least one workflow via YAML fallback."""
    from src.web.app import create_app

    # Create app without executor (triggers YAML fallback)
    app = create_app(executor=None)
    client = TestClient(app)

    # Call /api/workflows
    response = client.get("/api/workflows")

    # Assert response is successful
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # Parse response
    data = response.json()

    # Assert workflows list exists and is non-empty
    assert "workflows" in data, "Response should contain 'workflows' field"
    assert isinstance(data["workflows"], list), "workflows should be a list"
    assert len(data["workflows"]) >= 1, f"Expected at least 1 workflow, got {len(data['workflows'])}"

    # Assert total count matches
    assert "total" in data, "Response should contain 'total' field"
    assert data["total"] >= 1, f"Expected total >= 1, got {data['total']}"

    print(f"✓ /api/workflows returned {len(data['workflows'])} workflow(s)")
