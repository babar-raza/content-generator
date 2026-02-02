"""Integration tests for workflows API routes.

Tests all endpoints in src/web/routes/workflows.py including:
- Workflow listing and retrieval
- Mesh orchestration endpoints
- Visual editor endpoints
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from src.web.routes import workflows


@pytest.fixture
def app():
    """Create FastAPI app with workflows router."""
    test_app = FastAPI()
    test_app.include_router(workflows.router)
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_executor():
    """Create mock executor with workflow support."""
    executor = Mock()

    # Workflow methods
    executor.get_workflows = Mock(return_value=[
        {
            "id": "workflow-1",
            "name": "Content Generation",
            "description": "Generate content using AI",
            "agents": ["research_agent", "writer_agent"],
            "metadata": {"version": "1.0"}
        },
        {
            "id": "workflow-2",
            "name": "Quality Check",
            "description": "Validate content quality",
            "agents": ["quality_agent"],
            "metadata": {"version": "2.0"}
        }
    ])

    executor.get_workflow = Mock(side_effect=lambda wid: {
        "workflow-1": {
            "id": "workflow-1",
            "name": "Content Generation",
            "description": "Generate content using AI",
            "agents": ["research_agent", "writer_agent"],
            "metadata": {"version": "1.0"}
        },
        "workflow-2": {
            "id": "workflow-2",
            "name": "Quality Check",
            "description": "Validate content quality",
            "agents": ["quality_agent"],
            "metadata": {"version": "2.0"}
        }
    }.get(wid))

    # Mesh executor
    mesh_executor = Mock()
    mesh_executor.list_agents = Mock(return_value=[
        {"id": "agent-1", "name": "Research Agent", "capabilities": ["research"]},
        {"id": "agent-2", "name": "Writer Agent", "capabilities": ["writing"]}
    ])

    mesh_result = Mock()
    mesh_result.to_dict = Mock(return_value={
        "job_id": "mesh_abc123",
        "status": "completed",
        "result": {"output": "Test result"}
    })
    mesh_executor.execute_mesh_workflow = Mock(return_value=mesh_result)

    mesh_executor.get_mesh_trace = Mock(return_value=[
        {"agent": "agent-1", "timestamp": datetime.now(timezone.utc).isoformat(), "action": "start"},
        {"agent": "agent-2", "timestamp": datetime.now(timezone.utc).isoformat(), "action": "process"}
    ])

    mesh_executor.get_stats = Mock(return_value={
        "total_executions": 10,
        "successful": 8,
        "failed": 2,
        "avg_duration": 5.2
    })

    executor.mesh_executor = mesh_executor

    return executor


@pytest.fixture(autouse=True)
def setup_executor(mock_executor):
    """Set executor before each test."""
    workflows.set_executor(mock_executor)
    yield
    workflows.set_executor(None)


class TestWorkflowListing:
    """Test workflow listing endpoints."""

    def test_list_workflows_success(self, client, mock_executor):
        """Test successfully listing all workflows."""
        response = client.get("/api/workflows")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["workflows"]) == 2
        assert data["workflows"][0]["workflow_id"] == "workflow-1"
        assert data["workflows"][0]["name"] == "Content Generation"
        assert data["workflows"][1]["workflow_id"] == "workflow-2"

    def test_list_workflows_executor_no_method(self, client, mock_executor):
        """Test listing workflows when executor doesn't support get_workflows.

        After commit 93ab3e2, the API falls back to YAML discovery when executor
        doesn't have get_workflows method, so workflows are still returned.
        """
        delattr(mock_executor, 'get_workflows')

        response = client.get("/api/workflows")

        assert response.status_code == 200
        data = response.json()
        # Should return workflows from YAML fallback (4 workflows in test fixtures)
        assert data["total"] == 4
        assert len(data["workflows"]) == 4

    def test_list_workflows_error(self, client, mock_executor):
        """Test error handling when listing workflows fails."""
        mock_executor.get_workflows.side_effect = Exception("Database error")

        response = client.get("/api/workflows")

        assert response.status_code == 500
        assert "Failed to list workflows" in response.json()["detail"]

    @patch.dict('os.environ', {'TEST_MODE': 'live'})
    def test_list_workflows_no_executor(self, client):
        """Test listing workflows when executor not initialized - should fall back to YAML."""
        workflows.set_executor(None)

        response = client.get("/api/workflows")

        # Should return 200 with workflows from YAML fallback
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        # May be empty if YAML not found, but should not error
        assert isinstance(data["workflows"], list)


class TestWorkflowRetrieval:
    """Test individual workflow retrieval."""

    def test_get_workflow_success(self, client, mock_executor):
        """Test successfully getting a specific workflow."""
        response = client.get("/api/workflows/workflow-1")

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "workflow-1"
        assert data["name"] == "Content Generation"
        assert "research_agent" in data["agents"]
        assert data["metadata"]["version"] == "1.0"

    def test_get_workflow_not_found(self, client, mock_executor):
        """Test getting non-existent workflow."""
        response = client.get("/api/workflows/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_workflow_no_method(self, client, mock_executor):
        """Test getting workflow when executor doesn't support get_workflow."""
        delattr(mock_executor, 'get_workflow')

        response = client.get("/api/workflows/workflow-1")

        assert response.status_code == 501
        assert "not supported" in response.json()["detail"]

    def test_get_workflow_error(self, client, mock_executor):
        """Test error handling when getting workflow fails."""
        mock_executor.get_workflow.side_effect = Exception("Database error")

        response = client.get("/api/workflows/workflow-1")

        assert response.status_code == 500
        assert "Failed to get workflow" in response.json()["detail"]


class TestMeshOrchestration:
    """Test mesh orchestration endpoints."""

    def test_get_mesh_agents_success(self, client, mock_executor):
        """Test successfully listing mesh agents."""
        response = client.get("/api/mesh/agents")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["agents"]) == 2
        assert data["agents"][0]["id"] == "agent-1"

    def test_get_mesh_agents_not_enabled(self, client, mock_executor):
        """Test getting mesh agents when mesh not enabled."""
        mock_executor.mesh_executor = None

        response = client.get("/api/mesh/agents")

        assert response.status_code == 501
        assert "not enabled" in response.json()["detail"]

    def test_get_mesh_agents_error(self, client, mock_executor):
        """Test error handling when listing mesh agents fails."""
        mock_executor.mesh_executor.list_agents.side_effect = Exception("Network error")

        response = client.get("/api/mesh/agents")

        assert response.status_code == 500
        assert "Failed to list mesh agents" in response.json()["detail"]

    def test_execute_mesh_workflow_success(self, client, mock_executor):
        """Test successfully executing mesh workflow."""
        response = client.post("/api/mesh/execute", json={
            "workflow_name": "test_workflow",
            "initial_agent": "agent-1",
            "input_data": {"topic": "AI Testing"}
        })

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "mesh_abc123"
        assert data["status"] == "completed"

    def test_execute_mesh_workflow_missing_agent(self, client, mock_executor):
        """Test executing mesh workflow without initial_agent."""
        response = client.post("/api/mesh/execute", json={
            "workflow_name": "test_workflow",
            "input_data": {"topic": "AI Testing"}
        })

        assert response.status_code == 400
        assert "initial_agent is required" in response.json()["detail"]

    def test_execute_mesh_workflow_not_enabled(self, client, mock_executor):
        """Test executing mesh workflow when mesh not enabled."""
        mock_executor.mesh_executor = None

        response = client.post("/api/mesh/execute", json={
            "initial_agent": "agent-1"
        })

        assert response.status_code == 501
        assert "not enabled" in response.json()["detail"]

    def test_execute_mesh_workflow_error(self, client, mock_executor):
        """Test error handling when executing mesh workflow fails."""
        mock_executor.mesh_executor.execute_mesh_workflow.side_effect = Exception("Execution error")

        response = client.post("/api/mesh/execute", json={
            "initial_agent": "agent-1"
        })

        assert response.status_code == 500
        assert "Failed to execute mesh workflow" in response.json()["detail"]

    def test_get_mesh_trace_success(self, client, mock_executor):
        """Test successfully getting mesh trace."""
        response = client.get("/api/mesh/trace/mesh_abc123")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "mesh_abc123"
        assert len(data["trace"]) == 2
        assert data["trace"][0]["agent"] == "agent-1"

    def test_get_mesh_trace_not_found(self, client, mock_executor):
        """Test getting mesh trace for non-existent job."""
        mock_executor.mesh_executor.get_mesh_trace.return_value = None

        response = client.get("/api/mesh/trace/nonexistent")

        assert response.status_code == 404
        assert "No trace found" in response.json()["detail"]

    def test_get_mesh_trace_not_enabled(self, client, mock_executor):
        """Test getting mesh trace when mesh not enabled."""
        mock_executor.mesh_executor = None

        response = client.get("/api/mesh/trace/mesh_abc123")

        assert response.status_code == 501
        assert "not enabled" in response.json()["detail"]

    def test_get_mesh_trace_error(self, client, mock_executor):
        """Test error handling when getting mesh trace fails."""
        mock_executor.mesh_executor.get_mesh_trace.side_effect = Exception("Database error")

        response = client.get("/api/mesh/trace/mesh_abc123")

        assert response.status_code == 500
        assert "Failed to get mesh trace" in response.json()["detail"]

    def test_get_mesh_stats_success(self, client, mock_executor):
        """Test successfully getting mesh stats."""
        response = client.get("/api/mesh/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_executions"] == 10
        assert data["successful"] == 8
        assert data["failed"] == 2

    def test_get_mesh_stats_not_enabled(self, client, mock_executor):
        """Test getting mesh stats when mesh not enabled."""
        mock_executor.mesh_executor = None

        response = client.get("/api/mesh/stats")

        assert response.status_code == 501
        assert "not enabled" in response.json()["detail"]

    def test_get_mesh_stats_error(self, client, mock_executor):
        """Test error handling when getting mesh stats fails."""
        mock_executor.mesh_executor.get_stats.side_effect = Exception("Stats error")

        response = client.get("/api/mesh/stats")

        assert response.status_code == 500
        assert "Failed to get mesh stats" in response.json()["detail"]


class TestWorkflowEditor:
    """Test visual workflow editor endpoints."""

    @patch('src.web.routes.workflows._serializer')
    def test_list_editor_workflows_success(self, mock_serializer, client):
        """Test successfully listing editor workflows."""
        mock_serializer.list_workflows.return_value = [
            {"id": "wf-1", "name": "Workflow 1"},
            {"id": "wf-2", "name": "Workflow 2"}
        ]

        response = client.get("/api/workflows/editor/list")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["workflows"]) == 2

    @patch('src.web.routes.workflows._serializer')
    def test_list_editor_workflows_error(self, mock_serializer, client):
        """Test error handling when listing editor workflows fails."""
        mock_serializer.list_workflows.side_effect = Exception("Storage error")

        response = client.get("/api/workflows/editor/list")

        assert response.status_code == 500
        assert "Failed to list workflows" in response.json()["detail"]

    @patch('src.web.routes.workflows._serializer')
    def test_get_editor_workflow_success(self, mock_serializer, client):
        """Test successfully loading editor workflow."""
        mock_serializer.load_workflow.return_value = {
            "id": "wf-1",
            "name": "Test Workflow",
            "nodes": [{"id": "node-1", "type": "agent"}]
        }

        response = client.get("/api/workflows/editor/wf-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "wf-1"
        assert data["name"] == "Test Workflow"

    @patch('src.web.routes.workflows._serializer')
    def test_get_editor_workflow_not_found(self, mock_serializer, client):
        """Test loading non-existent editor workflow."""
        mock_serializer.load_workflow.side_effect = ValueError("Workflow not found")

        response = client.get("/api/workflows/editor/nonexistent")

        assert response.status_code == 404
        assert "Workflow not found" in response.json()["detail"]

    @patch('src.web.routes.workflows._serializer')
    def test_get_editor_workflow_error(self, mock_serializer, client):
        """Test error handling when loading editor workflow fails."""
        mock_serializer.load_workflow.side_effect = Exception("Storage error")

        response = client.get("/api/workflows/editor/wf-1")

        assert response.status_code == 500
        assert "Failed to load workflow" in response.json()["detail"]

    @patch('src.web.routes.workflows._serializer')
    def test_save_editor_workflow_success(self, mock_serializer, client):
        """Test successfully saving editor workflow."""
        mock_serializer.validate_workflow.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_serializer.save_workflow.return_value = None

        workflow = {
            "id": "wf-1",
            "name": "Test Workflow",
            "nodes": [{"id": "node-1", "type": "agent"}]
        }

        response = client.post("/api/workflows/editor/save", json=workflow)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["id"] == "wf-1"

    @patch('src.web.routes.workflows._serializer')
    def test_save_editor_workflow_validation_failed(self, mock_serializer, client):
        """Test saving workflow with validation errors."""
        mock_serializer.validate_workflow.return_value = {
            "valid": False,
            "errors": ["Missing required field: name"],
            "warnings": []
        }

        workflow = {"id": "wf-1"}

        response = client.post("/api/workflows/editor/save", json=workflow)

        assert response.status_code == 400
        assert "validation failed" in response.json()["detail"]["message"]
        assert len(response.json()["detail"]["errors"]) == 1

    @patch('src.web.routes.workflows._serializer')
    def test_save_editor_workflow_error(self, mock_serializer, client):
        """Test error handling when saving editor workflow fails."""
        mock_serializer.validate_workflow.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_serializer.save_workflow.side_effect = Exception("Storage error")

        workflow = {"id": "wf-1", "name": "Test"}

        response = client.post("/api/workflows/editor/save", json=workflow)

        assert response.status_code == 500
        assert "Failed to save workflow" in response.json()["detail"]

    @patch('src.web.routes.workflows._serializer')
    def test_validate_editor_workflow_success(self, mock_serializer, client):
        """Test successfully validating editor workflow."""
        mock_serializer.validate_workflow.return_value = {
            "valid": True,
            "errors": [],
            "warnings": ["Consider adding description"]
        }

        workflow = {"id": "wf-1", "name": "Test"}

        response = client.post("/api/workflows/editor/validate", json=workflow)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["warnings"]) == 1

    @patch('src.web.routes.workflows._serializer')
    def test_validate_editor_workflow_invalid(self, mock_serializer, client):
        """Test validating invalid editor workflow."""
        mock_serializer.validate_workflow.return_value = {
            "valid": False,
            "errors": ["Missing required field: name"],
            "warnings": []
        }

        workflow = {"id": "wf-1"}

        response = client.post("/api/workflows/editor/validate", json=workflow)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) == 1

    @patch('src.web.routes.workflows._serializer')
    def test_validate_editor_workflow_error(self, mock_serializer, client):
        """Test error handling during workflow validation."""
        mock_serializer.validate_workflow.side_effect = Exception("Validation engine error")

        workflow = {"id": "wf-1"}

        response = client.post("/api/workflows/editor/validate", json=workflow)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) == 1

    @patch('src.web.routes.workflows._serializer')
    def test_test_run_workflow_success(self, mock_serializer, client, mock_executor):
        """Test successfully running workflow test."""
        mock_serializer.validate_workflow.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_serializer.json_to_yaml.return_value = {"test_workflow": {}}

        workflow = {
            "id": "wf-1",
            "name": "Test",
            "nodes": [{"id": "n1"}, {"id": "n2"}]
        }

        response = client.post("/api/workflows/editor/test-run", json=workflow)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["workflow_id"] == "test_workflow"
        assert data["steps"] == 2

    @patch('src.web.routes.workflows._serializer')
    def test_test_run_workflow_validation_failed(self, mock_serializer, client, mock_executor):
        """Test test-running workflow with validation errors."""
        mock_serializer.validate_workflow.return_value = {
            "valid": False,
            "errors": ["Invalid node configuration"],
            "warnings": []
        }

        workflow = {"id": "wf-1"}

        response = client.post("/api/workflows/editor/test-run", json=workflow)

        assert response.status_code == 400
        assert "validation failed" in response.json()["detail"]["message"]

    @patch('src.web.routes.workflows._serializer')
    def test_test_run_workflow_error(self, mock_serializer, client, mock_executor):
        """Test error handling when test-running workflow fails."""
        mock_serializer.validate_workflow.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_serializer.json_to_yaml.side_effect = Exception("Conversion error")

        workflow = {"id": "wf-1", "name": "Test"}

        response = client.post("/api/workflows/editor/test-run", json=workflow)

        assert response.status_code == 500
        assert "Failed to test run workflow" in response.json()["detail"]


class TestDependencyInjection:
    """Test dependency injection behavior."""

    @patch.dict('os.environ', {'TEST_MODE': 'live'})
    def test_get_executor_not_initialized(self, client):
        """Test accessing routes when executor not initialized - should fall back to YAML."""
        workflows.set_executor(None)

        response = client.get("/api/workflows")

        # Should return 200 with workflows from YAML fallback
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        # May be empty if YAML not found, but should not error
        assert isinstance(data["workflows"], list)

    def test_set_executor(self):
        """Test setting executor via set_executor."""
        mock_exec = Mock()
        workflows.set_executor(mock_exec)

        result = workflows.get_executor()

        assert result == mock_exec
