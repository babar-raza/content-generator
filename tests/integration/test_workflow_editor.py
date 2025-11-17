"""Integration tests for Workflow Editor API endpoints."""

import pytest
import json
from pathlib import Path
import tempfile
import os

from fastapi.testclient import TestClient


@pytest.fixture
def temp_workflows_file():
    """Create a temporary workflows file."""
    import yaml
    
    workflows_data = {
        'workflows': {
            'test_workflow': {
                'name': 'Test Workflow',
                'description': 'A test workflow for integration tests',
                'steps': [
                    {'agent': 'kb_ingestion'},
                    {'agent': 'outline_creation', 'depends_on': ['kb_ingestion']}
                ],
                'metadata': {
                    'category': 'test',
                    'version': '1.0'
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(workflows_data, f)
        temp_path = f.name
    
    yield Path(temp_path)
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except:
        pass


@pytest.fixture
def app_with_temp_workflows(temp_workflows_file):
    """Create app with temporary workflows file."""
    from src.web.app import create_app
    from src.orchestration.workflow_serializer import WorkflowSerializer
    
    # Patch the serializer to use temp file
    import src.web.routes.workflows as workflows_module
    workflows_module._serializer = WorkflowSerializer(temp_workflows_file)
    
    app = create_app()
    client = TestClient(app)
    
    yield client


def test_list_workflows(app_with_temp_workflows):
    """Test listing workflows."""
    response = app_with_temp_workflows.get("/api/workflows/editor/list")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "workflows" in data
    assert "total" in data
    assert isinstance(data["workflows"], list)
    assert data["total"] >= 1
    
    # Check workflow structure
    if data["workflows"]:
        workflow = data["workflows"][0]
        assert "id" in workflow
        assert "name" in workflow
        assert "description" in workflow


def test_get_workflow(app_with_temp_workflows):
    """Test getting a specific workflow."""
    response = app_with_temp_workflows.get("/api/workflows/editor/test_workflow")
    
    assert response.status_code == 200
    workflow = response.json()
    
    assert workflow["id"] == "test_workflow"
    assert workflow["name"] == "Test Workflow"
    assert "nodes" in workflow
    assert "edges" in workflow
    assert isinstance(workflow["nodes"], list)
    assert isinstance(workflow["edges"], list)


def test_get_nonexistent_workflow(app_with_temp_workflows):
    """Test getting a nonexistent workflow returns 404."""
    response = app_with_temp_workflows.get("/api/workflows/editor/nonexistent")
    
    assert response.status_code == 404


def test_save_workflow(app_with_temp_workflows):
    """Test saving a new workflow."""
    new_workflow = {
        "id": "new_test_workflow",
        "name": "New Test Workflow",
        "description": "A newly created workflow",
        "nodes": [
            {
                "id": "node1",
                "type": "default",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "KB Ingestion",
                    "agentId": "kb_ingestion"
                }
            },
            {
                "id": "node2",
                "type": "default",
                "position": {"x": 400, "y": 100},
                "data": {
                    "label": "Outline Creation",
                    "agentId": "outline_creation"
                }
            }
        ],
        "edges": [
            {
                "id": "edge1",
                "source": "node1",
                "target": "node2"
            }
        ]
    }
    
    response = app_with_temp_workflows.post(
        "/api/workflows/editor/save",
        json=new_workflow
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["status"] == "success"
    assert result["id"] == "new_test_workflow"
    
    # Verify it can be loaded
    get_response = app_with_temp_workflows.get("/api/workflows/editor/new_test_workflow")
    assert get_response.status_code == 200


def test_save_invalid_workflow(app_with_temp_workflows):
    """Test saving an invalid workflow returns error."""
    invalid_workflow = {
        "id": "invalid_workflow",
        # Missing name
        "nodes": [],
        "edges": []
    }
    
    response = app_with_temp_workflows.post(
        "/api/workflows/editor/save",
        json=invalid_workflow
    )
    
    assert response.status_code == 400


def test_validate_workflow_valid(app_with_temp_workflows):
    """Test validating a valid workflow."""
    valid_workflow = {
        "id": "valid_workflow",
        "name": "Valid Workflow",
        "nodes": [
            {
                "id": "node1",
                "type": "default",
                "data": {"agentId": "kb_ingestion"}
            },
            {
                "id": "node2",
                "type": "default",
                "data": {"agentId": "outline_creation"}
            }
        ],
        "edges": [
            {"source": "node1", "target": "node2"}
        ]
    }
    
    response = app_with_temp_workflows.post(
        "/api/workflows/editor/validate",
        json=valid_workflow
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_workflow_with_cycles(app_with_temp_workflows):
    """Test validating a workflow with cycles."""
    cyclic_workflow = {
        "id": "cyclic_workflow",
        "name": "Cyclic Workflow",
        "nodes": [
            {"id": "node1", "type": "default", "data": {"agentId": "agent1"}},
            {"id": "node2", "type": "default", "data": {"agentId": "agent2"}},
            {"id": "node3", "type": "default", "data": {"agentId": "agent3"}}
        ],
        "edges": [
            {"source": "node1", "target": "node2"},
            {"source": "node2", "target": "node3"},
            {"source": "node3", "target": "node1"}
        ]
    }
    
    response = app_with_temp_workflows.post(
        "/api/workflows/editor/validate",
        json=cyclic_workflow
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["valid"] is False
    assert len(result["errors"]) > 0
    assert any("circular" in err.lower() or "cycle" in err.lower() 
               for err in result["errors"])


def test_validate_workflow_missing_agents(app_with_temp_workflows):
    """Test validating a workflow with missing agent IDs."""
    missing_agent_workflow = {
        "id": "missing_agent_workflow",
        "name": "Missing Agent Workflow",
        "nodes": [
            {"id": "node1", "type": "default", "data": {}}  # No agentId
        ],
        "edges": []
    }
    
    response = app_with_temp_workflows.post(
        "/api/workflows/editor/validate",
        json=missing_agent_workflow
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_test_run_workflow(app_with_temp_workflows):
    """Test running a workflow in test mode."""
    test_workflow = {
        "id": "test_run_workflow",
        "name": "Test Run Workflow",
        "nodes": [
            {
                "id": "node1",
                "type": "default",
                "data": {
                    "label": "Test Agent",
                    "agentId": "kb_ingestion"
                }
            }
        ],
        "edges": []
    }
    
    response = app_with_temp_workflows.post(
        "/api/workflows/editor/test-run",
        json=test_workflow
    )
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["status"] == "success"
    assert "workflow_id" in result
    assert result["steps"] == 1


def test_test_run_invalid_workflow(app_with_temp_workflows):
    """Test running an invalid workflow returns error."""
    invalid_workflow = {
        "id": "invalid_test_workflow",
        "name": "Invalid Test Workflow",
        "nodes": [
            {"id": "node1", "type": "default", "data": {}},
            {"id": "node2", "type": "default", "data": {}},
            {"id": "node3", "type": "default", "data": {}}
        ],
        "edges": [
            {"source": "node1", "target": "node2"},
            {"source": "node2", "target": "node3"},
            {"source": "node3", "target": "node1"}  # Cycle
        ]
    }
    
    response = app_with_temp_workflows.post(
        "/api/workflows/editor/test-run",
        json=invalid_workflow
    )
    
    assert response.status_code == 400


def test_workflow_crud_flow(app_with_temp_workflows):
    """Test complete CRUD flow for workflows."""
    # 1. Create workflow
    workflow = {
        "id": "crud_workflow",
        "name": "CRUD Test Workflow",
        "description": "Testing CRUD operations",
        "nodes": [
            {
                "id": "node1",
                "type": "default",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "Agent 1",
                    "agentId": "agent1"
                }
            }
        ],
        "edges": []
    }
    
    # Save
    save_response = app_with_temp_workflows.post(
        "/api/workflows/editor/save",
        json=workflow
    )
    assert save_response.status_code == 200
    
    # Read
    get_response = app_with_temp_workflows.get("/api/workflows/editor/crud_workflow")
    assert get_response.status_code == 200
    loaded_workflow = get_response.json()
    assert loaded_workflow["name"] == "CRUD Test Workflow"
    
    # Update
    loaded_workflow["name"] = "Updated CRUD Workflow"
    loaded_workflow["nodes"].append({
        "id": "node2",
        "type": "default",
        "position": {"x": 400, "y": 100},
        "data": {
            "label": "Agent 2",
            "agentId": "agent2"
        }
    })
    loaded_workflow["edges"].append({
        "id": "edge1",
        "source": "node1",
        "target": "node2"
    })
    
    update_response = app_with_temp_workflows.post(
        "/api/workflows/editor/save",
        json=loaded_workflow
    )
    assert update_response.status_code == 200
    
    # Verify update
    verify_response = app_with_temp_workflows.get("/api/workflows/editor/crud_workflow")
    assert verify_response.status_code == 200
    updated_workflow = verify_response.json()
    assert updated_workflow["name"] == "Updated CRUD Workflow"
    assert len(updated_workflow["nodes"]) == 2
    assert len(updated_workflow["edges"]) == 1


def test_concurrent_workflow_saves(app_with_temp_workflows):
    """Test that concurrent saves don't corrupt the workflow file."""
    import threading
    
    results = []
    
    def save_workflow(workflow_num):
        workflow = {
            "id": f"concurrent_workflow_{workflow_num}",
            "name": f"Concurrent Workflow {workflow_num}",
            "nodes": [
                {
                    "id": "node1",
                    "type": "default",
                    "data": {"agentId": "agent1"}
                }
            ],
            "edges": []
        }
        
        response = app_with_temp_workflows.post(
            "/api/workflows/editor/save",
            json=workflow
        )
        results.append(response.status_code)
    
    # Create multiple threads to save workflows
    threads = []
    for i in range(5):
        thread = threading.Thread(target=save_workflow, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # All saves should succeed
    assert all(status == 200 for status in results)
    
    # Verify all workflows were saved
    list_response = app_with_temp_workflows.get("/api/workflows/editor/list")
    workflows = list_response.json()["workflows"]
    concurrent_workflows = [w for w in workflows if w["id"].startswith("concurrent_workflow_")]
    assert len(concurrent_workflows) == 5
