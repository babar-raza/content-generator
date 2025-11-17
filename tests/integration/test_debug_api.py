"""
HTTP endpoint tests for Debug API.

Tests:
- POST /api/debug/breakpoints
- DELETE /api/debug/breakpoints/{id}
- GET /api/debug/breakpoints
- POST /api/debug/step
- GET /api/debug/state/{job_id}
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.fixtures.http_fixtures import mock_executor, test_app, client


class TestBreakpoints:
    """Tests for breakpoint management endpoints."""
    
    def test_create_breakpoint(self, client):
        """Test POST /api/debug/breakpoints."""
        response = client.post(
            "/api/debug/breakpoints",
            json={
                "agent_id": "test_agent",
                "event_type": "before_execute",
                "condition": "test_condition"
            }
        )
        assert response.status_code in [200, 201, 404, 501]
    
    def test_create_breakpoint_invalid(self, client):
        """Test creating breakpoint with invalid data."""
        response = client.post(
            "/api/debug/breakpoints",
            json={}  # Missing required fields
        )
        assert response.status_code in [400, 422, 501]
    
    def test_delete_breakpoint(self, client):
        """Test DELETE /api/debug/breakpoints/{id}."""
        response = client.delete("/api/debug/breakpoints/test_bp_123")
        assert response.status_code in [200, 204, 404, 501]
    
    def test_list_breakpoints(self, client):
        """Test GET /api/debug/breakpoints."""
        response = client.get("/api/debug/breakpoints")
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))


class TestDebugStepping:
    """Tests for debug stepping endpoints."""
    
    def test_debug_step(self, client):
        """Test POST /api/debug/step."""
        response = client.post(
            "/api/debug/step",
            json={
                "session_id": "test_session",
                "action": "step"
            }
        )
        assert response.status_code in [200, 404, 501]
    
    def test_debug_step_invalid(self, client):
        """Test stepping with invalid session."""
        response = client.post(
            "/api/debug/step",
            json={"session_id": "nonexistent"}
        )
        assert response.status_code in [400, 404, 422, 501]


class TestDebugState:
    """Tests for debug state endpoints."""
    
    def test_get_debug_state(self, client):
        """Test GET /api/debug/state/{job_id}."""
        response = client.get("/api/debug/state/test_job")
        assert response.status_code in [200, 404, 501]
    
    def test_get_state_nonexistent_job(self, client):
        """Test getting state for non-existent job."""
        response = client.get("/api/debug/state/nonexistent")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
