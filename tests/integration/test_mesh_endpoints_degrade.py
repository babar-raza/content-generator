"""Test mesh endpoints degrade gracefully.

Regression test for mesh endpoint 503/500 issues - ensures mesh endpoints
return 200 with structured JSON even when mesh is not configured.
"""
import pytest
from fastapi.testclient import TestClient
from src.web.app import create_app


@pytest.fixture
def client_no_mesh():
    """Create a test client without mesh executor (no executor at all)."""
    app = create_app(executor=None, config_snapshot=None)
    return TestClient(app)


def test_mesh_agents_degrades_gracefully(client_no_mesh):
    """Test GET /api/mesh/agents returns 200 when mesh not configured."""
    response = client_no_mesh.get("/api/mesh/agents")

    # Should return 200, not 501 or 503
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()

    # Should have structured response indicating mesh not available
    assert "available" in data, "Response should have 'available' field"
    assert data["available"] is False, "Mesh should not be available"
    assert "reason" in data, "Response should have 'reason' field"
    assert "agents" in data, "Response should have 'agents' field (empty list)"
    assert isinstance(data["agents"], list), "Agents should be a list"
    assert data["total"] == 0, "Total should be 0"


def test_mesh_stats_degrades_gracefully(client_no_mesh):
    """Test GET /api/mesh/stats returns 200 when mesh not configured."""
    response = client_no_mesh.get("/api/mesh/stats")

    # Should return 200, not 501 or 503
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()

    # Should have structured response indicating mesh not available
    assert "available" in data, "Response should have 'available' field"
    assert data["available"] is False, "Mesh should not be available"
    assert "reason" in data, "Response should have 'reason' field"
    assert "stats" in data, "Response should have 'stats' field (empty dict)"
    assert isinstance(data["stats"], dict), "Stats should be a dict"


def test_mesh_endpoints_json_structure(client_no_mesh):
    """Test that mesh endpoints return valid JSON structure."""
    # Test multiple mesh endpoints
    endpoints = [
        "/api/mesh/agents",
        "/api/mesh/stats",
    ]

    for endpoint in endpoints:
        response = client_no_mesh.get(endpoint)

        # All should return 200 with valid JSON
        assert response.status_code == 200, f"{endpoint} should return 200"
        assert response.headers.get("content-type") == "application/json", \
            f"{endpoint} should return JSON"

        data = response.json()
        assert isinstance(data, dict), f"{endpoint} should return dict"
        assert "available" in data, f"{endpoint} should have 'available' field"


@pytest.mark.parametrize("endpoint,method", [
    ("/api/mesh/agents", "GET"),
    ("/api/mesh/stats", "GET"),
])
def test_mesh_endpoints_no_hard_failures(client_no_mesh, endpoint, method):
    """Test that mesh info endpoints never return 500/503 when mesh not configured."""
    if method == "GET":
        response = client_no_mesh.get(endpoint)
    else:
        response = client_no_mesh.post(endpoint, json={})

    # Should not return server error codes for info endpoints
    assert response.status_code not in [500, 503], \
        f"{endpoint} should not return 500/503, got {response.status_code}"

    # For GET endpoints, should return 200
    if method == "GET":
        assert response.status_code == 200, \
            f"GET {endpoint} should return 200, got {response.status_code}"
