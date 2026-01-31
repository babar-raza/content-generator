"""Integration test: /api/agents must return non-empty list."""

import pytest
from fastapi.testclient import TestClient


def test_agents_endpoint_returns_nonempty():
    """Test that /api/agents returns at least one agent via filesystem discovery fallback."""
    from src.web.app import create_app

    # Create app without executor (triggers fallback)
    app = create_app(executor=None)
    client = TestClient(app)

    # Call /api/agents
    response = client.get("/api/agents")

    # Assert response is successful
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # Parse response
    data = response.json()

    # Assert agents list exists and is non-empty
    assert "agents" in data, "Response should contain 'agents' field"
    assert isinstance(data["agents"], list), "agents should be a list"
    assert len(data["agents"]) >= 1, f"Expected at least 1 agent, got {len(data['agents'])}"

    # Assert total count matches
    assert "total" in data, "Response should contain 'total' field"
    assert data["total"] >= 1, f"Expected total >= 1, got {data['total']}"

    print(f"✓ /api/agents returned {len(data['agents'])} agent(s)")
