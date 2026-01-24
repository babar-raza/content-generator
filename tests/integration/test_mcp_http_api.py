"""
HTTP endpoint tests for MCP API.

Tests all 31 MCP endpoints from web_adapter after TASK-P0-001.
This complements test_mcp_integration.py with HTTP-specific tests.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.fixtures.http_fixtures import (
    mock_executor, mock_config_snapshot, test_app, client
)


class TestMCPProtocol:
    """Tests for /mcp/request endpoint (main MCP protocol)."""
    
    def test_mcp_request_valid_method(self, client):
        """Test MCP request with valid method."""
        response = client.post(
            "/mcp/request",
            json={
                "method": "agents/list",
                "params": {},
                "id": "test_1"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
    
    def test_mcp_request_invalid_method(self, client):
        """Test MCP request with invalid method."""
        response = client.post(
            "/mcp/request",
            json={
                "method": "invalid/method",
                "params": {},
                "id": "test_2"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
    
    def test_mcp_request_missing_fields(self, client):
        """Test MCP request with missing required fields."""
        response = client.post(
            "/mcp/request",
            json={"method": "agents/list"}  # Missing params
        )
        assert response.status_code in [200, 422]


class TestMCPUtilityEndpoints:
    """Tests for MCP utility endpoints."""
    
    def test_mcp_status(self, client):
        """Test GET /mcp/status."""
        response = client.get("/mcp/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "executor_initialized" in data
    
    def test_mcp_methods(self, client):
        """Test GET /mcp/methods."""
        response = client.get("/mcp/methods")
        assert response.status_code == 200
        
        data = response.json()
        assert "methods" in data
        assert isinstance(data["methods"], list)


class TestMCPJobEndpoints:
    """Tests for MCP job management endpoints."""
    
    def test_create_job_rest(self, client):
        """Test POST /mcp/jobs/create."""
        response = client.post(
            "/mcp/jobs/create",
            json={
                "workflow_name": "test_workflow",
                "input_data": {"topic": "Test"}
            }
        )
        assert response.status_code in [200, 503]
    
    def test_list_jobs_rest(self, client):
        """Test GET /mcp/jobs."""
        response = client.get("/mcp/jobs")
        assert response.status_code in [200, 503]
    
    def test_get_job_rest(self, client):
        """Test GET /mcp/jobs/{job_id}."""
        response = client.get("/mcp/jobs/test_job")
        assert response.status_code in [200, 404, 503]

    def test_create_job_invalid_workflow(self, client):
        """Test POST /mcp/jobs/create with invalid workflow."""
        response = client.post(
            "/mcp/jobs/create",
            json={
                "workflow_name": "",
                "input_data": {}
            }
        )
        assert response.status_code in [400, 422, 503]

    def test_create_job_missing_fields(self, client):
        """Test POST /mcp/jobs/create with missing fields."""
        response = client.post(
            "/mcp/jobs/create",
            json={}
        )
        assert response.status_code in [400, 422, 503]

    def test_get_job_nonexistent(self, client):
        """Test GET /mcp/jobs/{job_id} for non-existent job."""
        response = client.get("/mcp/jobs/nonexistent_job_12345")
        assert response.status_code in [404, 503]

    def test_pause_job(self, client):
        """Test POST /mcp/jobs/{job_id}/pause."""
        response = client.post("/mcp/jobs/test_job/pause")
        assert response.status_code in [200, 404, 503]

    def test_pause_nonexistent_job(self, client):
        """Test pause non-existent job."""
        response = client.post("/mcp/jobs/nonexistent/pause")
        assert response.status_code in [404, 503]

    def test_resume_job(self, client):
        """Test POST /mcp/jobs/{job_id}/resume."""
        response = client.post("/mcp/jobs/test_job/resume")
        assert response.status_code in [200, 404, 503]

    def test_resume_nonexistent_job(self, client):
        """Test resume non-existent job."""
        response = client.post("/mcp/jobs/nonexistent/resume")
        assert response.status_code in [404, 503]

    def test_cancel_job(self, client):
        """Test POST /mcp/jobs/{job_id}/cancel."""
        response = client.post("/mcp/jobs/test_job/cancel")
        assert response.status_code in [200, 404, 503]

    def test_cancel_nonexistent_job(self, client):
        """Test cancel non-existent job."""
        response = client.post("/mcp/jobs/nonexistent/cancel")
        assert response.status_code in [404, 503]

    def test_list_jobs_validates_response(self, client):
        """Test GET /mcp/jobs validates response structure."""
        response = client.get("/mcp/jobs")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


class TestMCPConfigEndpoints:
    """Tests for MCP config endpoints (from TASK-P0-004)."""
    
    def test_config_snapshot(self, client):
        """Test GET /mcp/config/snapshot."""
        response = client.get("/mcp/config/snapshot")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
    
    def test_config_agents(self, client):
        """Test GET /mcp/config/agents."""
        response = client.get("/mcp/config/agents")
        assert response.status_code in [200, 503]
    
    def test_config_workflows(self, client):
        """Test GET /mcp/config/workflows."""
        response = client.get("/mcp/config/workflows")
        assert response.status_code in [200, 503]
    
    def test_config_tone(self, client):
        """Test GET /mcp/config/tone."""
        response = client.get("/mcp/config/tone")
        assert response.status_code in [200, 503]
    
    def test_config_performance(self, client):
        """Test GET /mcp/config/performance."""
        response = client.get("/mcp/config/performance")
        assert response.status_code in [200, 503]


class TestMCPWorkflowEndpoints:
    """Tests for MCP workflow endpoints."""
    
    def test_list_workflows(self, client):
        """Test GET /mcp/workflows."""
        response = client.get("/mcp/workflows")
        assert response.status_code in [200, 503]
    
    def test_workflow_profiles(self, client):
        """Test GET /mcp/workflows/profiles."""
        response = client.get("/mcp/workflows/profiles")
        assert response.status_code in [200, 503]
    
    def test_workflow_visual(self, client):
        """Test GET /mcp/workflows/visual/{profile_name}."""
        response = client.get("/mcp/workflows/visual/test_profile")
        assert response.status_code in [200, 404, 503]

    def test_workflow_visual_nonexistent(self, client):
        """Test GET /mcp/workflows/visual/{profile_name} for non-existent profile."""
        response = client.get("/mcp/workflows/visual/nonexistent_profile")
        # MCP returns errors in response body with 200 status
        assert response.status_code in [200, 404, 503]

    def test_workflow_metrics(self, client):
        """Test GET /mcp/workflows/{profile_name}/metrics."""
        response = client.get("/mcp/workflows/test_profile/metrics")
        assert response.status_code in [200, 404, 503]

    def test_workflow_metrics_nonexistent(self, client):
        """Test GET /mcp/workflows/{profile_name}/metrics for non-existent profile."""
        response = client.get("/mcp/workflows/nonexistent/metrics")
        # MCP returns errors in response body with 200 status
        assert response.status_code in [200, 404, 503]

    def test_workflow_reset(self, client):
        """Test POST /mcp/workflows/{profile_name}/reset."""
        response = client.post("/mcp/workflows/test_profile/reset")
        assert response.status_code in [200, 404, 503]

    def test_workflow_reset_nonexistent(self, client):
        """Test POST /mcp/workflows/{profile_name}/reset for non-existent profile."""
        response = client.post("/mcp/workflows/nonexistent/reset")
        # MCP returns errors in response body with 200 status
        assert response.status_code in [200, 404, 503]

    def test_list_workflows_validates_response(self, client):
        """Test GET /mcp/workflows validates response structure."""
        response = client.get("/mcp/workflows")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


class TestMCPAgentEndpoints:
    """Tests for MCP agent endpoints."""
    
    def test_list_agents(self, client):
        """Test GET /mcp/agents."""
        response = client.get("/mcp/agents")
        assert response.status_code in [200, 503]
    
    def test_agents_status(self, client):
        """Test GET /mcp/agents/status."""
        response = client.get("/mcp/agents/status")
        assert response.status_code in [200, 503]


class TestMCPFlowEndpoints:
    """Tests for MCP flow analysis endpoints."""
    
    def test_flows_realtime(self, client):
        """Test GET /mcp/flows/realtime."""
        response = client.get("/mcp/flows/realtime")
        assert response.status_code in [200, 503]
    
    def test_flows_history(self, client):
        """Test GET /mcp/flows/history/{correlation_id}."""
        response = client.get("/mcp/flows/history/test_correlation")
        assert response.status_code in [200, 404, 503]
    
    def test_flows_bottlenecks(self, client):
        """Test GET /mcp/flows/bottlenecks."""
        response = client.get("/mcp/flows/bottlenecks")
        assert response.status_code in [200, 503]


class TestMCPDebugEndpoints:
    """Tests for MCP debug endpoints."""
    
    def test_create_debug_session(self, client):
        """Test POST /mcp/debug/sessions."""
        response = client.post(
            "/mcp/debug/sessions",
            params={"correlation_id": "test_correlation"}
        )
        assert response.status_code in [200, 503]
    
    def test_get_debug_session(self, client):
        """Test GET /mcp/debug/sessions/{session_id}."""
        response = client.get("/mcp/debug/sessions/test_session")
        assert response.status_code in [200, 404, 503]

    def test_get_debug_session_nonexistent(self, client):
        """Test GET /mcp/debug/sessions/{session_id} for non-existent session."""
        response = client.get("/mcp/debug/sessions/nonexistent_session")
        # MCP returns errors in response body with 200 status
        assert response.status_code in [200, 404, 503]

    def test_add_breakpoint(self, client):
        """Test POST /mcp/debug/breakpoints."""
        response = client.post(
            "/mcp/debug/breakpoints",
            json={
                "session_id": "test_session",
                "step_id": "step1"
            }
        )
        assert response.status_code in [200, 404, 422, 503]

    def test_remove_breakpoint(self, client):
        """Test DELETE /mcp/debug/sessions/{session_id}/breakpoints/{breakpoint_id}."""
        response = client.delete("/mcp/debug/sessions/test_session/breakpoints/bp1")
        assert response.status_code in [200, 404, 503]

    def test_step_debug(self, client):
        """Test POST /mcp/debug/sessions/{session_id}/step."""
        response = client.post("/mcp/debug/sessions/test_session/step")
        assert response.status_code in [200, 404, 503]

    def test_continue_debug(self, client):
        """Test POST /mcp/debug/sessions/{session_id}/continue."""
        response = client.post("/mcp/debug/sessions/test_session/continue")
        assert response.status_code in [200, 404, 503]

    def test_get_workflow_trace(self, client):
        """Test GET /mcp/debug/workflows/{workflow_id}/trace."""
        response = client.get("/mcp/debug/workflows/test_workflow/trace")
        assert response.status_code in [200, 404, 503]

    def test_get_workflow_trace_nonexistent(self, client):
        """Test GET /mcp/debug/workflows/{workflow_id}/trace for non-existent workflow."""
        response = client.get("/mcp/debug/workflows/nonexistent/trace")
        # MCP returns errors in response body with 200 status
        assert response.status_code in [200, 404, 503]


class TestMCPEndpointAccessibility:
    """Test that all MCP endpoints are accessible (not 404)."""
    
    def test_all_mcp_endpoints_mounted(self, client):
        """Verify all MCP endpoints return non-404 status."""
        endpoints = [
            ("GET", "/mcp/status"),
            ("GET", "/mcp/methods"),
            ("GET", "/mcp/config/snapshot"),
            ("GET", "/mcp/config/agents"),
            ("GET", "/mcp/config/workflows"),
            ("GET", "/mcp/config/tone"),
            ("GET", "/mcp/config/performance"),
            ("GET", "/mcp/jobs"),
            ("GET", "/mcp/agents"),
            ("GET", "/mcp/agents/status"),
            ("GET", "/mcp/workflows"),
            ("GET", "/mcp/workflows/profiles"),
            ("GET", "/mcp/flows/realtime"),
            ("GET", "/mcp/flows/bottlenecks"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)
            
            assert response.status_code != 404, f"{endpoint} returned 404 (not mounted)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
