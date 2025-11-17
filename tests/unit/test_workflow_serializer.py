"""Unit tests for WorkflowSerializer."""

import pytest
import json
import yaml
from pathlib import Path
import tempfile
import os

from src.orchestration.workflow_serializer import WorkflowSerializer


@pytest.fixture
def temp_workflows_file():
    """Create a temporary workflows file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({
            'workflows': {
                'test_workflow': {
                    'name': 'Test Workflow',
                    'description': 'A test workflow',
                    'steps': [
                        {'agent': 'agent1'},
                        {'agent': 'agent2', 'depends_on': ['agent1']}
                    ]
                }
            }
        }, f)
        temp_path = f.name
    
    yield Path(temp_path)
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except:
        pass


@pytest.fixture
def serializer(temp_workflows_file):
    """Create a serializer instance."""
    return WorkflowSerializer(temp_workflows_file)


def test_serializer_init():
    """Test serializer initialization."""
    serializer = WorkflowSerializer()
    assert serializer.workflows_file == Path("templates/workflows.yaml")
    
    custom_path = Path("custom/path.yaml")
    serializer = WorkflowSerializer(custom_path)
    assert serializer.workflows_file == custom_path


def test_json_to_yaml_simple(serializer):
    """Test simple JSON to YAML conversion."""
    workflow_json = {
        "id": "simple_workflow",
        "name": "Simple Workflow",
        "description": "A simple workflow",
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
    
    result = serializer.json_to_yaml(workflow_json)
    
    assert "simple_workflow" in result
    assert result["simple_workflow"]["name"] == "Simple Workflow"
    assert result["simple_workflow"]["description"] == "A simple workflow"
    assert len(result["simple_workflow"]["steps"]) == 1
    assert result["simple_workflow"]["steps"][0]["agent"] == "agent1"


def test_json_to_yaml_with_dependencies(serializer):
    """Test JSON to YAML conversion with dependencies."""
    workflow_json = {
        "id": "dep_workflow",
        "name": "Workflow with Dependencies",
        "description": "",
        "nodes": [
            {
                "id": "node1",
                "type": "default",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "Agent 1",
                    "agentId": "agent1"
                }
            },
            {
                "id": "node2",
                "type": "default",
                "position": {"x": 400, "y": 100},
                "data": {
                    "label": "Agent 2",
                    "agentId": "agent2"
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
    
    result = serializer.json_to_yaml(workflow_json)
    
    steps = result["dep_workflow"]["steps"]
    assert len(steps) == 2
    
    # Find the step for agent2
    agent2_step = next(s for s in steps if s["agent"] == "agent2")
    assert "depends_on" in agent2_step
    assert "agent1" in agent2_step["depends_on"]


def test_json_to_yaml_with_config(serializer):
    """Test JSON to YAML conversion with config and params."""
    workflow_json = {
        "id": "config_workflow",
        "name": "Workflow with Config",
        "description": "",
        "nodes": [
            {
                "id": "node1",
                "type": "default",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "Agent 1",
                    "agentId": "agent1",
                    "config": {"key": "value"},
                    "params": {"param1": "val1"}
                }
            }
        ],
        "edges": []
    }
    
    result = serializer.json_to_yaml(workflow_json)
    
    step = result["config_workflow"]["steps"][0]
    assert step["config"] == {"key": "value"}
    assert step["params"] == {"param1": "val1"}


def test_yaml_to_json_simple(serializer):
    """Test simple YAML to JSON conversion."""
    workflow_yaml = {
        "simple_workflow": {
            "name": "Simple Workflow",
            "description": "A simple workflow",
            "steps": [
                {"agent": "agent1"}
            ]
        }
    }
    
    result = serializer.yaml_to_json(workflow_yaml, "simple_workflow")
    
    assert result["id"] == "simple_workflow"
    assert result["name"] == "Simple Workflow"
    assert len(result["nodes"]) == 1
    assert result["nodes"][0]["data"]["agentId"] == "agent1"
    assert len(result["edges"]) == 0


def test_yaml_to_json_with_dependencies(serializer):
    """Test YAML to JSON conversion with dependencies."""
    workflow_yaml = {
        "dep_workflow": {
            "name": "Workflow with Dependencies",
            "description": "",
            "steps": [
                {"agent": "agent1"},
                {"agent": "agent2", "depends_on": ["agent1"]}
            ]
        }
    }
    
    result = serializer.yaml_to_json(workflow_yaml, "dep_workflow")
    
    assert len(result["nodes"]) == 2
    assert len(result["edges"]) == 1
    
    edge = result["edges"][0]
    assert edge["source"] == "node-0"  # agent1
    assert edge["target"] == "node-1"  # agent2


def test_save_and_load_workflow(serializer):
    """Test saving and loading a workflow."""
    workflow_json = {
        "id": "new_workflow",
        "name": "New Workflow",
        "description": "A new workflow",
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
    serializer.save_workflow(workflow_json)
    
    # Load
    loaded = serializer.load_workflow("new_workflow")
    
    assert loaded["id"] == "new_workflow"
    assert loaded["name"] == "New Workflow"
    assert len(loaded["nodes"]) == 1


def test_list_workflows(serializer):
    """Test listing workflows."""
    workflows = serializer.list_workflows()
    
    assert isinstance(workflows, list)
    assert len(workflows) >= 1  # At least the test_workflow from fixture
    
    # Check structure
    if workflows:
        workflow = workflows[0]
        assert "id" in workflow
        assert "name" in workflow
        assert "description" in workflow


def test_validate_workflow_valid(serializer):
    """Test validation of a valid workflow."""
    workflow_json = {
        "id": "valid_workflow",
        "name": "Valid Workflow",
        "nodes": [
            {
                "id": "node1",
                "type": "default",
                "data": {"agentId": "agent1"}
            },
            {
                "id": "node2",
                "type": "default",
                "data": {"agentId": "agent2"}
            }
        ],
        "edges": [
            {"source": "node1", "target": "node2"}
        ]
    }
    
    result = serializer.validate_workflow(workflow_json)
    
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_workflow_missing_id(serializer):
    """Test validation with missing ID."""
    workflow_json = {
        "name": "No ID Workflow",
        "nodes": [],
        "edges": []
    }
    
    result = serializer.validate_workflow(workflow_json)
    
    assert result["valid"] is False
    assert any("id" in err.lower() for err in result["errors"])


def test_validate_workflow_missing_name(serializer):
    """Test validation with missing name."""
    workflow_json = {
        "id": "no_name",
        "nodes": [],
        "edges": []
    }
    
    result = serializer.validate_workflow(workflow_json)
    
    assert result["valid"] is False
    assert any("name" in err.lower() for err in result["errors"])


def test_validate_workflow_no_nodes(serializer):
    """Test validation with no nodes."""
    workflow_json = {
        "id": "empty_workflow",
        "name": "Empty Workflow",
        "nodes": [],
        "edges": []
    }
    
    result = serializer.validate_workflow(workflow_json)
    
    assert result["valid"] is False
    assert any("node" in err.lower() for err in result["errors"])


def test_validate_workflow_cycles(serializer):
    """Test validation detects cycles."""
    workflow_json = {
        "id": "cycle_workflow",
        "name": "Workflow with Cycle",
        "nodes": [
            {"id": "node1", "type": "default", "data": {"agentId": "agent1"}},
            {"id": "node2", "type": "default", "data": {"agentId": "agent2"}},
            {"id": "node3", "type": "default", "data": {"agentId": "agent3"}}
        ],
        "edges": [
            {"source": "node1", "target": "node2"},
            {"source": "node2", "target": "node3"},
            {"source": "node3", "target": "node1"}  # Creates cycle
        ]
    }
    
    result = serializer.validate_workflow(workflow_json)
    
    assert result["valid"] is False
    assert any("circular" in err.lower() or "cycle" in err.lower() for err in result["errors"])


def test_validate_workflow_orphan_nodes(serializer):
    """Test validation warns about orphan nodes."""
    workflow_json = {
        "id": "orphan_workflow",
        "name": "Workflow with Orphans",
        "nodes": [
            {"id": "node1", "type": "default", "data": {"agentId": "agent1"}},
            {"id": "node2", "type": "default", "data": {"agentId": "agent2"}},
            {"id": "node3", "type": "default", "data": {"agentId": "agent3"}}
        ],
        "edges": [
            {"source": "node1", "target": "node2"}
            # node3 is orphaned
        ]
    }
    
    result = serializer.validate_workflow(workflow_json)
    
    # Should be valid (orphans are warnings, not errors)
    assert result["valid"] is True
    assert len(result["warnings"]) > 0
    assert any("disconnected" in warn.lower() or "orphan" in warn.lower() 
               for warn in result["warnings"])


def test_validate_workflow_missing_agent_id(serializer):
    """Test validation detects missing agent IDs."""
    workflow_json = {
        "id": "missing_agent_workflow",
        "name": "Workflow with Missing Agent",
        "nodes": [
            {"id": "node1", "type": "default", "data": {}}  # No agentId
        ],
        "edges": []
    }
    
    result = serializer.validate_workflow(workflow_json)
    
    assert result["valid"] is False
    assert any("agent" in err.lower() for err in result["errors"])


def test_roundtrip_conversion(serializer):
    """Test that JSON->YAML->JSON roundtrip preserves data."""
    original_json = {
        "id": "roundtrip_workflow",
        "name": "Roundtrip Workflow",
        "description": "Testing roundtrip",
        "nodes": [
            {
                "id": "node1",
                "type": "default",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "Agent 1",
                    "agentId": "agent1",
                    "config": {"key": "value"}
                }
            },
            {
                "id": "node2",
                "type": "default",
                "position": {"x": 400, "y": 100},
                "data": {
                    "label": "Agent 2",
                    "agentId": "agent2"
                }
            }
        ],
        "edges": [
            {"source": "node1", "target": "node2"}
        ]
    }
    
    # Convert to YAML
    yaml_format = serializer.json_to_yaml(original_json)
    
    # Convert back to JSON
    json_format = serializer.yaml_to_json(yaml_format, "roundtrip_workflow")
    
    # Verify key properties preserved
    assert json_format["id"] == original_json["id"]
    assert json_format["name"] == original_json["name"]
    assert len(json_format["nodes"]) == len(original_json["nodes"])
    assert len(json_format["edges"]) == len(original_json["edges"])


def test_load_nonexistent_workflow(serializer):
    """Test loading a nonexistent workflow raises error."""
    with pytest.raises(ValueError, match="not found"):
        serializer.load_workflow("nonexistent_workflow")
