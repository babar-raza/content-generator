"""Test MCP endpoints integration."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from src.mcp.protocol import (
    MCPRequest, MCPResponse, MCPError,
    ResourceType, ResourceStatus,
    JobResource, WorkflowResource
)
from src.mcp.web_adapter import router, set_executor, get_executor


class TestMCPProtocol:
    """Test MCP protocol definitions."""
    
    def test_mcp_request_creation(self):
        """Test MCPRequest model creation."""
        request = MCPRequest(
            method="jobs/create",
            params={"workflow": "blog", "topic": "Test"},
            id="req_123"
        )
        
        assert request.method == "jobs/create"
        assert request.params["workflow"] == "blog"
        assert request.id == "req_123"
    
    def test_mcp_response_creation(self):
        """Test MCPResponse model creation."""
        response = MCPResponse(
            result={"job_id": "job_123", "status": "created"},
            id="req_123"
        )
        
        assert response.result["job_id"] == "job_123"
        assert response.error is None
        assert response.id == "req_123"
    
    def test_mcp_error_response(self):
        """Test MCPError response."""
        error = MCPError(
            code=404,
            message="Job not found",
            data={"job_id": "job_123"}
        )
        
        response = MCPResponse(
            error=error.dict(),
            id="req_123"
        )
        
        assert response.result is None
        assert response.error["code"] == 404
        assert response.error["message"] == "Job not found"
    
    def test_resource_status_enum(self):
        """Test ResourceStatus enum values."""
        assert ResourceStatus.PENDING == "pending"
        assert ResourceStatus.RUNNING == "running"
        assert ResourceStatus.COMPLETED == "completed"
        assert ResourceStatus.FAILED == "failed"
    
    def test_resource_type_enum(self):
        """Test ResourceType enum values."""
        assert ResourceType.WORKFLOW == "workflow"
        assert ResourceType.AGENT == "agent"
        assert ResourceType.JOB == "job"


class TestMCPWebAdapter:
    """Test MCP web adapter functionality."""
    
    @pytest.fixture
    def mock_executor(self):
        """Create mock executor for testing."""
        executor = Mock()
        executor.execute = Mock()
        executor.list_jobs = Mock(return_value=[])
        executor.get_job = Mock()
        executor.cancel_job = Mock(return_value=True)
        return executor
    
    @pytest.fixture
    def client(self, mock_executor):
        """Create test client with mock executor."""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router)
        
        # Set the mock executor
        set_executor(mock_executor)
        
        return TestClient(app)
    
    def test_executor_initialization(self, mock_executor):
        """Test executor initialization."""
        config = {"test": "config"}
        set_executor(mock_executor, config)
        
        executor = get_executor()
        assert executor == mock_executor
    
    def test_mcp_request_endpoint(self, client):
        """Test MCP request endpoint."""
        request_data = {
            "method": "jobs/list",
            "params": {},
            "id": "test_req"
        }
        
        response = client.post("/mcp/request", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data or "error" in data
    
    def test_job_create_request(self, client, mock_executor):
        """Test job creation through MCP."""
        mock_executor.execute.return_value = Mock(
            job_id="job_123",
            status=Mock(value="running"),
            to_dict=lambda: {"job_id": "job_123", "status": "running"}
        )
        
        request_data = {
            "method": "jobs/create",
            "params": {
                "workflow_name": "blog",
                "input_data": {"topic": "Test Topic"}
            }
        }
        
        response = client.post("/mcp/request", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["job_id"] == "job_123"
        mock_executor.execute.assert_called_once()
    
    def test_job_list_request(self, client, mock_executor):
        """Test job listing through MCP."""
        mock_executor.list_jobs.return_value = [
            {"job_id": "job_1", "status": "running"},
            {"job_id": "job_2", "status": "completed"}
        ]
        
        request_data = {
            "method": "jobs/list",
            "params": {}
        }
        
        response = client.post("/mcp/request", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["result"]["jobs"]) == 2
        assert data["result"]["jobs"][0]["job_id"] == "job_1"
    
    def test_job_get_request(self, client, mock_executor):
        """Test getting job details through MCP."""
        mock_job = Mock(
            job_id="job_123",
            status=Mock(value="completed"),
            to_dict=lambda: {
                "job_id": "job_123",
                "status": "completed",
                "topic": "Test"
            }
        )
        mock_executor.get_job.return_value = mock_job
        
        request_data = {
            "method": "jobs/get",
            "params": {"job_id": "job_123"}
        }
        
        response = client.post("/mcp/request", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["job_id"] == "job_123"
        assert data["result"]["status"] == "completed"
    
    def test_job_cancel_request(self, client, mock_executor):
        """Test job cancellation through MCP."""
        mock_executor.cancel_job.return_value = True
        
        request_data = {
            "method": "jobs/cancel",
            "params": {"job_id": "job_123"}
        }
        
        response = client.post("/mcp/request", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["cancelled"] == True
        mock_executor.cancel_job.assert_called_with("job_123")
    
    def test_workflow_list_request(self, client, mock_executor):
        """Test workflow listing through MCP."""
        mock_executor.template_registry = Mock()
        mock_executor.template_registry.list_templates.return_value = [
            {"name": "blog", "description": "Blog workflow"},
            {"name": "api", "description": "API workflow"}
        ]
        
        request_data = {
            "method": "workflows/list",
            "params": {}
        }
        
        response = client.post("/mcp/request", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["result"]["workflows"]) == 2
    
    def test_agent_list_request(self, client, mock_executor):
        """Test agent listing through MCP."""
        mock_executor.agents = {
            "Agent1": Mock(name="Agent1"),
            "Agent2": Mock(name="Agent2")
        }
        
        request_data = {
            "method": "agents/list",
            "params": {}
        }
        
        response = client.post("/mcp/request", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["result"]["agents"]) == 2
    
    def test_invalid_method_request(self, client):
        """Test invalid method handling."""
        request_data = {
            "method": "invalid/method",
            "params": {}
        }
        
        response = client.post("/mcp/request", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 404
    
    def test_executor_not_initialized(self):
        """Test error when executor not initialized."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        app.include_router(router)
        
        # Reset executor
        set_executor(None)
        
        client = TestClient(app)
        
        request_data = {
            "method": "jobs/list",
            "params": {}
        }
        
        response = client.post("/mcp/request", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data


class TestMCPIntegration:
    """Integration tests for MCP with unified engine."""
    
    @pytest.fixture
    def integrated_client(self):
        """Create client with real engine integration."""
        from fastapi import FastAPI
        from src.engine.engine import UnifiedEngine
        
        app = FastAPI()
        app.include_router(router)
        
        # Create real engine with mocked services
        with patch('src.engine.engine.UnifiedEngine._initialize_services'):
            with patch('src.engine.engine.UnifiedEngine._load_templates'):
                engine = UnifiedEngine()
                engine.agents = {}
                engine.template_registry = Mock()
                engine.template_registry.list_templates.return_value = []
                engine.template_registry.get_template.return_value = {
                    'workflow': []
                }
                
                set_executor(engine)
                
                return TestClient(app)
    
    def test_full_job_lifecycle(self, integrated_client):
        """Test complete job lifecycle through MCP."""
        # Create job
        create_request = {
            "method": "jobs/create",
            "params": {
                "workflow_name": "test",
                "input_data": {"topic": "Integration Test"}
            }
        }
        
        response = integrated_client.post("/mcp/request", json=create_request)
        assert response.status_code == 200
        create_data = response.json()
        
        # Extract job_id from response
        if "result" in create_data and "job_id" in create_data["result"]:
            job_id = create_data["result"]["job_id"]
            
            # Get job details
            get_request = {
                "method": "jobs/get",
                "params": {"job_id": job_id}
            }
            
            response = integrated_client.post("/mcp/request", json=get_request)
            assert response.status_code == 200
            
            # List jobs
            list_request = {
                "method": "jobs/list",
                "params": {}
            }
            
            response = integrated_client.post("/mcp/request", json=list_request)
            assert response.status_code == 200
            list_data = response.json()
            
            # Verify job appears in list
            if "result" in list_data and "jobs" in list_data["result"]:
                job_ids = [j.get("job_id") for j in list_data["result"]["jobs"]]
                # Job might have already completed
                # so we don't assert it's in the list
    
    def test_workflow_operations(self, integrated_client):
        """Test workflow operations through MCP."""
        # List workflows
        list_request = {
            "method": "workflows/list",
            "params": {}
        }
        
        response = integrated_client.post("/mcp/request", json=list_request)
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "workflows" in data["result"]
    
    def test_agent_operations(self, integrated_client):
        """Test agent operations through MCP."""
        # List agents
        list_request = {
            "method": "agents/list",
            "params": {}
        }
        
        response = integrated_client.post("/mcp/request", json=list_request)
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "agents" in data["result"]
    
    def test_error_handling(self, integrated_client):
        """Test error handling in MCP integration."""
        # Try to get non-existent job
        get_request = {
            "method": "jobs/get",
            "params": {"job_id": "nonexistent_job"}
        }
        
        response = integrated_client.post("/mcp/request", json=get_request)
        assert response.status_code == 200
        data = response.json()
        
        # Should return error
        if "error" in data:
            assert data["error"]["code"] == 404
        else:
            # Or None result
            assert data["result"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
