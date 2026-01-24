"""
MCP Web Adapter Endpoint Accessibility Tests

Verifies that all 31 MCP endpoints are mounted and return non-404 status codes.
This test ensures the web_adapter router is properly wired to the FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def mock_executor():
    """Create a mock executor for testing."""
    executor = Mock()

    # Mock run_job for job creation tests
    job_result = Mock()
    job_result.job_id = "test_job_123"
    job_result.status = "running"
    job_result.started_at = "2025-01-15T12:00:00"
    job_result.completed_at = None
    job_result.output_path = Path("./output")
    job_result.error = None
    job_result.to_dict = Mock(return_value={
        "job_id": "test_job_123",
        "status": "running",
        "started_at": "2025-01-15T12:00:00",
        "completed_at": None,
        "output_path": "./output",
        "error": None
    })
    executor.run_job = Mock(return_value=job_result)

    # Mock job engine with the test job
    executor.job_engine = Mock()
    executor.job_engine._jobs = {"test_job_123": job_result}
    executor.job_engine.pause_job = Mock()
    executor.job_engine.resume_job = Mock()
    executor.job_engine.cancel_job = Mock()

    return executor


@pytest.fixture
def mock_config():
    """Create a mock config snapshot."""
    config = Mock()
    config.config_hash = "test_config_abc123"
    config.timestamp = "2025-01-15T12:00:00"
    config.engine_version = "1.0.0"
    config.agent_config = {
        'agents': {
            'test_agent': {
                'id': 'test_agent',
                'version': '1.0',
                'description': 'Test agent',
                'capabilities': {},
                'resources': {}
            }
        }
    }
    config.main_config = {
        'workflows': {
            'test_workflow': {
                'name': 'Test Workflow',
                'steps': []
            }
        },
        'dependencies': {}
    }
    config.tone_config = {
        'global_voice': {},
        'section_controls': {},
        'heading_style': {},
        'code_template_overrides': {}
    }
    config.perf_config = {
        'timeouts': {},
        'limits': {},
        'batch': {},
        'hot_paths': {},
        'tuning': {}
    }
    
    return config


@pytest.fixture
def test_app(mock_executor, mock_config):
    """Create a test FastAPI app with MCP adapter mounted."""
    from src.web.app import create_app
    
    app = create_app(executor=mock_executor, config_snapshot=mock_config)
    return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


class TestMCPEndpointAccessibility:
    """Test all MCP endpoints are accessible (return non-404 status)."""
    
    def test_mcp_protocol_endpoint(self, client):
        """Test POST /mcp/request endpoint."""
        response = client.post(
            "/mcp/request",
            json={
                "method": "agents/list",
                "params": {},
                "id": "test_1"
            }
        )
        # Should not be 404 (may be 200, 500, etc. depending on implementation)
        assert response.status_code != 404, "MCP protocol endpoint returns 404"
    
    def test_mcp_methods_endpoint(self, client):
        """Test GET /mcp/methods endpoint."""
        response = client.get("/mcp/methods")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "methods" in data
        assert len(data["methods"]) > 0
    
    def test_mcp_status_endpoint(self, client):
        """Test GET /mcp/status endpoint."""
        response = client.get("/mcp/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "status" in data
        assert "executor_initialized" in data
    
    def test_jobs_create_endpoint(self, client):
        """Test POST /mcp/jobs/create endpoint."""
        response = client.post(
            "/mcp/jobs/create",
            json={
                "workflow_name": "test_workflow",
                "input_data": {"topic": "test"}
            }
        )
        assert response.status_code != 404, "Jobs create endpoint returns 404"
    
    def test_jobs_list_endpoint(self, client):
        """Test GET /mcp/jobs endpoint."""
        response = client.get("/mcp/jobs")
        assert response.status_code != 404, "Jobs list endpoint returns 404"
    
    def test_job_get_endpoint(self, client):
        """Test GET /mcp/jobs/{job_id} endpoint."""
        response = client.get("/mcp/jobs/test_job_123")
        # Should not be 404 (may be 200, 500 if job not found, etc.)
        assert response.status_code != 404, "Job get endpoint returns 404"
    
    def test_job_pause_endpoint(self, client):
        """Test POST /mcp/jobs/{job_id}/pause endpoint."""
        response = client.post("/mcp/jobs/test_job_123/pause")
        assert response.status_code != 404, "Job pause endpoint returns 404"
    
    def test_job_resume_endpoint(self, client):
        """Test POST /mcp/jobs/{job_id}/resume endpoint."""
        response = client.post("/mcp/jobs/test_job_123/resume")
        assert response.status_code != 404, "Job resume endpoint returns 404"
    
    def test_job_cancel_endpoint(self, client):
        """Test POST /mcp/jobs/{job_id}/cancel endpoint."""
        response = client.post("/mcp/jobs/test_job_123/cancel")
        assert response.status_code != 404, "Job cancel endpoint returns 404"
    
    def test_workflows_list_endpoint(self, client):
        """Test GET /mcp/workflows endpoint."""
        response = client.get("/mcp/workflows")
        assert response.status_code != 404, "Workflows list endpoint returns 404"
    
    def test_workflows_profiles_endpoint(self, client):
        """Test GET /mcp/workflows/profiles endpoint."""
        response = client.get("/mcp/workflows/profiles")
        assert response.status_code != 404, "Workflows profiles endpoint returns 404"
    
    def test_workflow_visual_endpoint(self, client):
        """Test GET /mcp/workflows/visual/{profile_name} endpoint."""
        response = client.get("/mcp/workflows/visual/test_profile")
        assert response.status_code != 404, "Workflow visual endpoint returns 404"
    
    def test_workflow_metrics_endpoint(self, client):
        """Test GET /mcp/workflows/{profile_name}/metrics endpoint."""
        response = client.get("/mcp/workflows/test_profile/metrics")
        assert response.status_code != 404, "Workflow metrics endpoint returns 404"
    
    def test_workflow_reset_endpoint(self, client):
        """Test POST /mcp/workflows/{profile_name}/reset endpoint."""
        response = client.post("/mcp/workflows/test_profile/reset")
        assert response.status_code != 404, "Workflow reset endpoint returns 404"
    
    def test_agents_list_endpoint(self, client):
        """Test GET /mcp/agents endpoint."""
        response = client.get("/mcp/agents")
        assert response.status_code != 404, "Agents list endpoint returns 404"
    
    def test_agents_status_endpoint(self, client):
        """Test GET /mcp/agents/status endpoint."""
        response = client.get("/mcp/agents/status")
        assert response.status_code != 404, "Agents status endpoint returns 404"
    
    def test_flows_realtime_endpoint(self, client):
        """Test GET /mcp/flows/realtime endpoint."""
        response = client.get("/mcp/flows/realtime")
        assert response.status_code != 404, "Flows realtime endpoint returns 404"
    
    def test_flows_history_endpoint(self, client):
        """Test GET /mcp/flows/history/{correlation_id} endpoint."""
        response = client.get("/mcp/flows/history/test_correlation_123")
        assert response.status_code != 404, "Flows history endpoint returns 404"
    
    def test_flows_bottlenecks_endpoint(self, client):
        """Test GET /mcp/flows/bottlenecks endpoint."""
        response = client.get("/mcp/flows/bottlenecks")
        assert response.status_code != 404, "Flows bottlenecks endpoint returns 404"
    
    def test_debug_sessions_create_endpoint(self, client):
        """Test POST /mcp/debug/sessions endpoint."""
        response = client.post(
            "/mcp/debug/sessions",
            params={"correlation_id": "test_correlation"}
        )
        assert response.status_code != 404, "Debug sessions create endpoint returns 404"
    
    def test_debug_session_get_endpoint(self, client):
        """Test GET /mcp/debug/sessions/{session_id} endpoint."""
        response = client.get("/mcp/debug/sessions/test_session_123")
        assert response.status_code != 404, "Debug session get endpoint returns 404"
    
    def test_debug_breakpoints_add_endpoint(self, client):
        """Test POST /mcp/debug/breakpoints endpoint."""
        response = client.post(
            "/mcp/debug/breakpoints",
            json={
                "session_id": "test_session",
                "agent_id": "test_agent",
                "event_type": "before_execute"
            }
        )
        assert response.status_code != 404, "Debug breakpoints add endpoint returns 404"
    
    def test_debug_breakpoint_remove_endpoint(self, client):
        """Test DELETE /mcp/debug/sessions/{session_id}/breakpoints/{breakpoint_id} endpoint."""
        response = client.delete("/mcp/debug/sessions/test_session/breakpoints/test_bp_123")
        assert response.status_code != 404, "Debug breakpoint remove endpoint returns 404"
    
    def test_debug_step_endpoint(self, client):
        """Test POST /mcp/debug/sessions/{session_id}/step endpoint."""
        response = client.post("/mcp/debug/sessions/test_session/step")
        assert response.status_code != 404, "Debug step endpoint returns 404"
    
    def test_debug_continue_endpoint(self, client):
        """Test POST /mcp/debug/sessions/{session_id}/continue endpoint."""
        response = client.post("/mcp/debug/sessions/test_session/continue")
        assert response.status_code != 404, "Debug continue endpoint returns 404"
    
    def test_debug_trace_endpoint(self, client):
        """Test GET /mcp/debug/workflows/{workflow_id}/trace endpoint."""
        response = client.get("/mcp/debug/workflows/test_workflow/trace")
        assert response.status_code != 404, "Debug trace endpoint returns 404"
    
    def test_config_snapshot_endpoint(self, client):
        """Test GET /mcp/config/snapshot endpoint."""
        response = client.get("/mcp/config/snapshot")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "status" in data
    
    def test_config_agents_endpoint(self, client):
        """Test GET /mcp/config/agents endpoint."""
        response = client.get("/mcp/config/agents")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "status" in data
        assert "agents" in data
    
    def test_config_workflows_endpoint(self, client):
        """Test GET /mcp/config/workflows endpoint."""
        response = client.get("/mcp/config/workflows")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "status" in data
        assert "workflows" in data
    
    def test_config_tone_endpoint(self, client):
        """Test GET /mcp/config/tone endpoint."""
        response = client.get("/mcp/config/tone")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "status" in data
    
    def test_config_performance_endpoint(self, client):
        """Test GET /mcp/config/performance endpoint."""
        response = client.get("/mcp/config/performance")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "status" in data


class TestEndpointCoverage:
    """Test that all expected endpoints are covered."""
    
    def test_all_31_endpoints_tested(self):
        """Verify we have tests for all 31 MCP endpoints."""
        # Count test methods in TestMCPEndpointAccessibility
        test_methods = [
            method for method in dir(TestMCPEndpointAccessibility)
            if method.startswith('test_') and callable(getattr(TestMCPEndpointAccessibility, method))
        ]
        
        # Should have 31 endpoint tests
        assert len(test_methods) >= 31, f"Expected 31 endpoint tests, found {len(test_methods)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
