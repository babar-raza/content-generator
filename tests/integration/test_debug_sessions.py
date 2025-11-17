"""
Integration tests for Debug Session Management API.

Tests all debug session endpoints:
- POST /api/debug/sessions
- GET /api/debug/sessions
- GET /api/debug/sessions/{session_id}
- DELETE /api/debug/sessions/{session_id}
- POST /api/debug/sessions/{session_id}/breakpoints
- DELETE /api/debug/sessions/{session_id}/breakpoints/{bp_id}
- POST /api/debug/sessions/{session_id}/step
- POST /api/debug/sessions/{session_id}/continue
- GET /api/debug/sessions/{session_id}/trace
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.web.app import create_app
from src.visualization.workflow_debugger import WorkflowDebugger


@pytest.fixture
def debugger():
    """Create a debugger instance for testing."""
    return WorkflowDebugger()


@pytest.fixture
def client(debugger):
    """Create test client with debugger."""
    app = create_app()
    
    # Inject the debugger
    from src.web.routes import debug
    debug._debugger = debugger
    
    return TestClient(app)


class TestDebugSessionLifecycle:
    """Tests for debug session creation, listing, and deletion."""
    
    def test_create_debug_session(self, client):
        """Test creating a new debug session."""
        response = client.post(
            "/api/debug/sessions",
            json={"job_id": "test_job_123", "auto_pause": True}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "session_id" in data
        assert data["job_id"] == "test_job_123"
        assert data["status"] == "paused"
        assert "started_at" in data
        assert data["breakpoint_count"] == 0
    
    def test_create_session_without_auto_pause(self, client):
        """Test creating session without auto-pause."""
        response = client.post(
            "/api/debug/sessions",
            json={"job_id": "test_job_456", "auto_pause": False}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "active"
    
    def test_list_debug_sessions(self, client):
        """Test listing all debug sessions."""
        # Create multiple sessions
        client.post("/api/debug/sessions", json={"job_id": "job1"})
        client.post("/api/debug/sessions", json={"job_id": "job2"})
        
        response = client.get("/api/debug/sessions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sessions" in data
        assert "total" in data
        assert data["total"] >= 2
        assert len(data["sessions"]) >= 2
    
    def test_list_sessions_with_status_filter(self, client):
        """Test listing sessions with status filter."""
        # Create paused and active sessions
        client.post("/api/debug/sessions", json={"job_id": "job1", "auto_pause": True})
        client.post("/api/debug/sessions", json={"job_id": "job2", "auto_pause": False})
        
        response = client.get("/api/debug/sessions?status=paused")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned sessions should be paused
        for session in data["sessions"]:
            assert session["status"] == "paused"
    
    def test_get_debug_session(self, client):
        """Test getting a specific debug session."""
        # Create session
        create_response = client.post(
            "/api/debug/sessions",
            json={"job_id": "test_job_789"}
        )
        session_id = create_response.json()["session_id"]
        
        # Get session
        response = client.get(f"/api/debug/sessions/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == session_id
        assert data["job_id"] == "test_job_789"
        assert "status" in data
        assert "breakpoints" in data
        assert "step_history" in data
    
    def test_get_nonexistent_session(self, client):
        """Test getting a session that doesn't exist."""
        response = client.get("/api/debug/sessions/nonexistent_session")
        assert response.status_code == 404
    
    def test_delete_debug_session(self, client):
        """Test deleting a debug session."""
        # Create session
        create_response = client.post(
            "/api/debug/sessions",
            json={"job_id": "test_job_delete"}
        )
        session_id = create_response.json()["session_id"]
        
        # Delete session
        response = client.delete(f"/api/debug/sessions/{session_id}")
        
        assert response.status_code == 200
        assert "message" in response.json()
        
        # Verify session is deleted
        get_response = client.get(f"/api/debug/sessions/{session_id}")
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_session(self, client):
        """Test deleting a session that doesn't exist."""
        response = client.delete("/api/debug/sessions/nonexistent")
        assert response.status_code == 404


class TestBreakpointManagement:
    """Tests for breakpoint management within sessions."""
    
    def test_add_breakpoint_to_session(self, client):
        """Test adding a breakpoint to a debug session."""
        # Create session
        create_response = client.post(
            "/api/debug/sessions",
            json={"job_id": "test_job_bp"}
        )
        session_id = create_response.json()["session_id"]
        
        # Add breakpoint
        response = client.post(
            f"/api/debug/sessions/{session_id}/breakpoints",
            json={
                "agent_id": "outline_creation_node",
                "event_type": "complete"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "breakpoint_id" in data
        assert data["session_id"] == session_id
        assert data["agent_id"] == "outline_creation_node"
        assert data["event_type"] == "complete"
        assert data["enabled"] is True
    
    def test_add_breakpoint_with_condition(self, client):
        """Test adding a conditional breakpoint."""
        create_response = client.post(
            "/api/debug/sessions",
            json={"job_id": "test_job"}
        )
        session_id = create_response.json()["session_id"]
        
        response = client.post(
            f"/api/debug/sessions/{session_id}/breakpoints",
            json={
                "agent_id": "test_agent",
                "event_type": "complete",
                "condition": "output.status == 'success'",
                "max_hits": 5
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["condition"] == "output.status == 'success'"
        assert data["max_hits"] == 5
    
    def test_remove_breakpoint_from_session(self, client):
        """Test removing a breakpoint from a session."""
        # Create session and breakpoint
        create_response = client.post(
            "/api/debug/sessions",
            json={"job_id": "test_job"}
        )
        session_id = create_response.json()["session_id"]
        
        bp_response = client.post(
            f"/api/debug/sessions/{session_id}/breakpoints",
            json={"agent_id": "test_agent", "event_type": "start"}
        )
        breakpoint_id = bp_response.json()["breakpoint_id"]
        
        # Remove breakpoint
        response = client.delete(
            f"/api/debug/sessions/{session_id}/breakpoints/{breakpoint_id}"
        )
        
        assert response.status_code == 200
        assert "message" in response.json()
    
    def test_add_breakpoint_to_nonexistent_session(self, client):
        """Test adding breakpoint to non-existent session."""
        response = client.post(
            "/api/debug/sessions/nonexistent/breakpoints",
            json={"agent_id": "test", "event_type": "start"}
        )
        assert response.status_code == 404


class TestStepControl:
    """Tests for step-through debugging control."""
    
    def test_step_through_session(self, client):
        """Test stepping through a debug session."""
        # Create session
        create_response = client.post(
            "/api/debug/sessions",
            json={"job_id": "test_job_step"}
        )
        session_id = create_response.json()["session_id"]
        
        # Step
        response = client.post(f"/api/debug/sessions/{session_id}/step")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == session_id
        assert "status" in data
        assert "execution_time_ms" in data
    
    def test_step_with_breakpoint(self, client):
        """Test stepping that hits a breakpoint."""
        # Create session
        create_response = client.post(
            "/api/debug/sessions",
            json={"job_id": "test_job"}
        )
        session_id = create_response.json()["session_id"]
        
        # Add breakpoint
        client.post(
            f"/api/debug/sessions/{session_id}/breakpoints",
            json={"agent_id": "test_agent", "event_type": "complete"}
        )
        
        # Step
        response = client.post(f"/api/debug/sessions/{session_id}/step")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should hit breakpoint
        assert "breakpoint_hit" in data
    
    def test_continue_session(self, client):
        """Test continuing execution."""
        # Create session
        create_response = client.post(
            "/api/debug/sessions",
            json={"job_id": "test_job"}
        )
        session_id = create_response.json()["session_id"]
        
        # Continue
        response = client.post(
            f"/api/debug/sessions/{session_id}/continue",
            json={"remove_breakpoints": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
    
    def test_continue_with_breakpoint_removal(self, client):
        """Test continuing with breakpoint removal."""
        # Create session and breakpoint
        create_response = client.post(
            "/api/debug/sessions",
            json={"job_id": "test_job"}
        )
        session_id = create_response.json()["session_id"]
        
        client.post(
            f"/api/debug/sessions/{session_id}/breakpoints",
            json={"agent_id": "test", "event_type": "start"}
        )
        
        # Continue with removal
        response = client.post(
            f"/api/debug/sessions/{session_id}/continue",
            json={"remove_breakpoints": True}
        )
        
        assert response.status_code == 200
        
        # Verify breakpoints removed
        session_response = client.get(f"/api/debug/sessions/{session_id}")
        assert len(session_response.json()["breakpoints"]) == 0
    
    def test_step_nonexistent_session(self, client):
        """Test stepping a non-existent session."""
        response = client.post("/api/debug/sessions/nonexistent/step")
        assert response.status_code == 404


class TestExecutionTrace:
    """Tests for execution trace retrieval."""
    
    def test_get_execution_trace(self, client):
        """Test getting execution trace for a session."""
        # Create session
        create_response = client.post(
            "/api/debug/sessions",
            json={"job_id": "test_job_trace"}
        )
        session_id = create_response.json()["session_id"]
        
        # Get trace
        response = client.get(f"/api/debug/sessions/{session_id}/trace")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == session_id
        assert "entries" in data
        assert "total_entries" in data
        assert isinstance(data["entries"], list)
    
    def test_trace_with_steps(self, client, debugger):
        """Test trace contains step history."""
        # Create session
        create_response = client.post(
            "/api/debug/sessions",
            json={"job_id": "test_job"}
        )
        session_id = create_response.json()["session_id"]
        
        # Add some step history manually
        session = debugger.debug_sessions[session_id]
        session.step_history.append({
            "timestamp": "2025-01-15T10:00:00Z",
            "agent_id": "agent_1",
            "event_type": "start",
            "input_data": {"test": "data"}
        })
        session.step_history.append({
            "timestamp": "2025-01-15T10:00:01Z",
            "agent_id": "agent_1",
            "event_type": "complete",
            "output_data": {"result": "success"},
            "duration_ms": 1000
        })
        
        # Get trace
        response = client.get(f"/api/debug/sessions/{session_id}/trace")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_entries"] == 2
        assert len(data["entries"]) == 2
        
        # Verify first entry
        entry = data["entries"][0]
        assert entry["agent_id"] == "agent_1"
        assert entry["event_type"] == "start"
        assert entry["input_data"]["test"] == "data"
    
    def test_trace_nonexistent_session(self, client):
        """Test getting trace for non-existent session."""
        response = client.get("/api/debug/sessions/nonexistent/trace")
        assert response.status_code == 404


class TestDebugWorkflow:
    """Integration tests for complete debug workflow."""
    
    def test_complete_debug_workflow(self, client, debugger):
        """Test complete debug workflow from creation to trace."""
        # 1. Create debug session
        create_response = client.post(
            "/api/debug/sessions",
            json={"job_id": "workflow_test_job", "auto_pause": True}
        )
        assert create_response.status_code == 201
        session_id = create_response.json()["session_id"]
        
        # 2. Add breakpoints
        bp1_response = client.post(
            f"/api/debug/sessions/{session_id}/breakpoints",
            json={"agent_id": "agent_1", "event_type": "complete"}
        )
        assert bp1_response.status_code == 201
        
        bp2_response = client.post(
            f"/api/debug/sessions/{session_id}/breakpoints",
            json={"agent_id": "agent_2", "event_type": "complete"}
        )
        assert bp2_response.status_code == 201
        
        # 3. Verify session state
        session_response = client.get(f"/api/debug/sessions/{session_id}")
        assert session_response.status_code == 200
        assert len(session_response.json()["breakpoints"]) == 2
        
        # 4. Step through execution
        step1_response = client.post(f"/api/debug/sessions/{session_id}/step")
        assert step1_response.status_code == 200
        
        # 5. Add step history for trace
        session = debugger.debug_sessions[session_id]
        session.step_history.append({
            "timestamp": "2025-01-15T10:00:00Z",
            "agent_id": "agent_1",
            "event_type": "complete",
            "duration_ms": 500
        })
        
        # 6. Get execution trace
        trace_response = client.get(f"/api/debug/sessions/{session_id}/trace")
        assert trace_response.status_code == 200
        assert trace_response.json()["total_entries"] >= 1
        
        # 7. Continue execution
        continue_response = client.post(
            f"/api/debug/sessions/{session_id}/continue",
            json={"remove_breakpoints": True}
        )
        assert continue_response.status_code == 200
        
        # 8. Delete session
        delete_response = client.delete(f"/api/debug/sessions/{session_id}")
        assert delete_response.status_code == 200
        
        # 9. Verify session is deleted
        get_response = client.get(f"/api/debug/sessions/{session_id}")
        assert get_response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
