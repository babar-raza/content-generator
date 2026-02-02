"""Workflow management API routes."""

import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
from fastapi import APIRouter, HTTPException, Depends

from ..models import WorkflowInfo, WorkflowList

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["workflows"], redirect_slashes=False)


def _is_mock_mode() -> bool:
    """Check if running in mock mode."""
    return os.getenv("TEST_MODE", "").lower() == "mock"


def _load_workflows_from_yaml() -> Optional[Dict[str, Any]]:
    """Load workflows from YAML file (fallback for mock mode).

    Returns:
        Dictionary of workflows or None if file not found
    """
    yaml_path = Path("templates/workflows.yaml")
    if not yaml_path.exists():
        logger.warning(f"Workflows YAML not found at {yaml_path}")
        return None

    try:
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
            return data.get("workflows", {})
    except Exception as e:
        logger.error(f"Error loading workflows from YAML: {e}")
        return None


def normalize_agents(raw_agents):
    """Normalize agents to List[str].

    Handles both string and dict formats:
    - str -> keep as is
    - dict -> extract 'agent' or 'id' or 'name' field
    - other -> convert to str

    Args:
        raw_agents: List of agents (can be str or dict)

    Returns:
        List[str]: Normalized agent names
    """
    if not raw_agents:
        return []

    normalized = []
    for item in raw_agents:
        if isinstance(item, str):
            normalized.append(item)
        elif isinstance(item, dict):
            # Try common agent identifier fields
            agent_name = item.get("agent") or item.get("id") or item.get("name") or str(item)
            normalized.append(agent_name)
        else:
            normalized.append(str(item))

    return normalized


# This will be injected by the app
_executor = None


def set_executor(executor):
    """Set the executor for dependency injection."""
    global _executor
    _executor = executor


def get_executor():
    """Dependency to get executor."""
    if _executor is None:
        raise HTTPException(status_code=503, detail="Executor not initialized")
    return _executor


@router.get("/workflows", response_model=WorkflowList)
async def list_workflows():
    """List all available workflows.

    Returns:
        WorkflowList with workflow information

    Raises:
        HTTPException: 503 if executor not initialized (only in live mode)
    """
    try:
        workflows_data = []

        # Check if executor is initialized
        if _executor is None:
            # Fall back to YAML (works in both mock and live modes)
            workflows_yaml = _load_workflows_from_yaml()
            if workflows_yaml:
                for wf_id, wf_data in workflows_yaml.items():
                    # Extract agent list from steps
                    agents = []
                    if "steps" in wf_data:
                        agents = [step.get("agent") for step in wf_data["steps"] if "agent" in step]

                    workflows_data.append(WorkflowInfo(
                        workflow_id=wf_id,
                        name=wf_data.get("name", wf_id),
                        description=wf_data.get("description"),
                        agents=agents,
                        metadata=wf_data.get("metadata"),
                    ))
            # Return workflows from YAML, or empty list if YAML not found
            return WorkflowList(workflows=workflows_data, total=len(workflows_data))

        # Check if executor has get_workflows method
        if hasattr(_executor, 'get_workflows'):
            # Use executor's get_workflows method
            workflows = _executor.get_workflows()

            for workflow in workflows:
                workflows_data.append(WorkflowInfo(
                    workflow_id=workflow.get("id", workflow.get("name", "unknown")),
                    name=workflow.get("name", "Unknown"),
                    description=workflow.get("description"),
                    agents=normalize_agents(workflow.get("agents", [])),
                    metadata=workflow.get("metadata"),
                ))
        else:
            # If executor doesn't have get_workflows, fall back to YAML
            workflows_yaml = _load_workflows_from_yaml()
            if workflows_yaml:
                for wf_id, wf_data in workflows_yaml.items():
                    agents = []
                    if "steps" in wf_data:
                        agents = [step.get("agent") for step in wf_data["steps"] if "agent" in step]

                    workflows_data.append(WorkflowInfo(
                        workflow_id=wf_id,
                        name=wf_data.get("name", wf_id),
                        description=wf_data.get("description"),
                        agents=agents,
                        metadata=wf_data.get("metadata"),
                    ))

        return WorkflowList(workflows=workflows_data, total=len(workflows_data))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")


@router.get("/workflows/{workflow_id}", response_model=WorkflowInfo)
async def get_workflow(workflow_id: str):
    """Get information about a specific workflow.

    Args:
        workflow_id: Workflow identifier

    Returns:
        WorkflowInfo with workflow details

    Raises:
        HTTPException: 503 if executor not initialized (live mode only), 404 if not found
    """
    try:
        # Check if executor is initialized
        if _executor is None:
            # In mock mode, fall back to YAML
            if _is_mock_mode():
                workflows_yaml = _load_workflows_from_yaml()
                if workflows_yaml and workflow_id in workflows_yaml:
                    wf_data = workflows_yaml[workflow_id]
                    # Extract agent list from steps
                    agents = []
                    if "steps" in wf_data:
                        agents = [step.get("agent") for step in wf_data["steps"] if "agent" in step]

                    return WorkflowInfo(
                        workflow_id=workflow_id,
                        name=wf_data.get("name", workflow_id),
                        description=wf_data.get("description"),
                        agents=agents,
                        metadata=wf_data.get("metadata"),
                    )
                else:
                    # Workflow not found in YAML
                    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
            else:
                # In live mode without executor, return 503
                raise HTTPException(status_code=503, detail="Executor not initialized")

        # Check if executor supports workflow retrieval
        if not hasattr(_executor, 'get_workflow'):
            raise HTTPException(status_code=501, detail="Workflow retrieval not supported by executor")

        # Use executor's get_workflow method
        workflow = _executor.get_workflow(workflow_id)

        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

        return WorkflowInfo(
            workflow_id=workflow.get("id", workflow_id),
            name=workflow.get("name", "Unknown"),
            description=workflow.get("description"),
            agents=normalize_agents(workflow.get("agents", [])),
            metadata=workflow.get("metadata"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get workflow: {str(e)}")


# Mesh orchestration endpoints
@router.get("/mesh/agents")
async def get_mesh_agents():
    """List available agents in mesh."""
    try:
        # Check executor directly without Depends to allow graceful degradation
        if _executor is None:
            return {"available": False, "reason": "executor not initialized", "agents": [], "total": 0}

        if not hasattr(_executor, 'mesh_executor') or _executor.mesh_executor is None:
            # Graceful degradation - return 200 with indication mesh not available
            return {"available": False, "reason": "mesh not configured", "agents": [], "total": 0}

        agents = _executor.mesh_executor.list_agents()
        return {"available": True, "agents": agents, "total": len(agents)}
    except Exception as e:
        logger.error(f"Error listing mesh agents: {e}", exc_info=True)
        # Graceful degradation - don't hard-fail with 500
        return {"available": False, "reason": f"error: {str(e)}", "agents": [], "total": 0}


@router.post("/mesh/execute")
async def execute_mesh_workflow(
    request: dict,
    executor=Depends(get_executor)
):
    """Start mesh workflow execution."""
    try:
        if not hasattr(executor, 'mesh_executor') or executor.mesh_executor is None:
            raise HTTPException(status_code=501, detail="Mesh orchestration not enabled")
        
        import uuid
        job_id = f"mesh_{uuid.uuid4().hex[:8]}"
        
        initial_agent = request.get('initial_agent')
        input_data = request.get('input_data', {})
        
        if not initial_agent:
            raise HTTPException(status_code=400, detail="initial_agent is required")
        
        result = executor.mesh_executor.execute_mesh_workflow(
            workflow_name=request.get('workflow_name', 'mesh_workflow'),
            initial_agent_type=initial_agent,
            input_data=input_data,
            job_id=job_id
        )
        
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing mesh workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute mesh workflow: {str(e)}")


@router.get("/mesh/trace/{job_id}")
async def get_mesh_trace(job_id: str, executor=Depends(get_executor)):
    """Get mesh execution trace showing agent hops."""
    try:
        if not hasattr(executor, 'mesh_executor') or executor.mesh_executor is None:
            raise HTTPException(status_code=501, detail="Mesh orchestration not enabled")
        
        trace = executor.mesh_executor.get_mesh_trace(job_id)
        if trace is None:
            raise HTTPException(status_code=404, detail=f"No trace found for job {job_id}")
        
        return {"job_id": job_id, "trace": trace}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting mesh trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get mesh trace: {str(e)}")


@router.get("/mesh/stats")
async def get_mesh_stats():
    """Get mesh orchestration statistics."""
    try:
        # Check executor directly without Depends to allow graceful degradation
        if _executor is None:
            return {"available": False, "reason": "executor not initialized", "stats": {}}

        if not hasattr(_executor, 'mesh_executor') or _executor.mesh_executor is None:
            # Graceful degradation - return 200 with indication mesh not available
            return {"available": False, "reason": "mesh not configured", "stats": {}}

        stats = _executor.mesh_executor.get_stats()
        return {"available": True, **stats}
    except Exception as e:
        logger.error(f"Error getting mesh stats: {e}", exc_info=True)
        # Graceful degradation - don't hard-fail with 500
        return {"available": False, "reason": f"error: {str(e)}", "stats": {}}


# Workflow Editor endpoints
from src.orchestration.workflow_serializer import WorkflowSerializer

_serializer = WorkflowSerializer()


@router.get("/workflows/editor/list")
async def list_editor_workflows():
    """List all workflows for the visual editor.
    
    Returns:
        List of workflow summaries
    """
    try:
        workflows = _serializer.list_workflows()
        return {"workflows": workflows, "total": len(workflows)}
    except Exception as e:
        logger.error(f"Error listing workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")


@router.get("/workflows/editor/{workflow_id}")
async def get_editor_workflow(workflow_id: str):
    """Load workflow for visual editor.
    
    Args:
        workflow_id: Workflow identifier
        
    Returns:
        Workflow in visual JSON format
    """
    try:
        workflow = _serializer.load_workflow(workflow_id)
        return workflow
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error loading workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load workflow: {str(e)}")


@router.post("/workflows/editor/save")
async def save_editor_workflow(workflow: dict):
    """Save workflow from visual editor.
    
    Args:
        workflow: Workflow in visual JSON format
        
    Returns:
        Success response with workflow ID
    """
    try:
        # Validate first
        validation = _serializer.validate_workflow(workflow)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Workflow validation failed",
                    "errors": validation["errors"]
                }
            )
        
        # Save workflow
        _serializer.save_workflow(workflow)
        
        return {
            "status": "success",
            "id": workflow.get("id"),
            "message": "Workflow saved successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save workflow: {str(e)}")


@router.post("/workflows/editor/validate")
async def validate_editor_workflow(workflow: dict):
    """Validate workflow structure.
    
    Args:
        workflow: Workflow in visual JSON format
        
    Returns:
        Validation result with errors and warnings
    """
    try:
        validation = _serializer.validate_workflow(workflow)
        return validation
    except Exception as e:
        logger.error(f"Error validating workflow: {e}", exc_info=True)
        return {
            "valid": False,
            "errors": [str(e)],
            "warnings": []
        }


@router.post("/workflows/editor/test-run")
async def test_run_editor_workflow(workflow: dict):
    """Test run workflow without saving.

    This endpoint validates the workflow structure without requiring an executor.
    It performs dry-run validation only, not actual execution.

    Args:
        workflow: Workflow in visual JSON format

    Returns:
        Test execution result
    """
    try:
        # Validate first
        validation = _serializer.validate_workflow(workflow)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Workflow validation failed",
                    "errors": validation["errors"]
                }
            )

        # Convert to YAML format
        workflow_yaml = _serializer.json_to_yaml(workflow)
        workflow_id = list(workflow_yaml.keys())[0]

        # Test run is a dry-run validation - no actual execution
        logger.info(f"Test run workflow: {workflow_id}")

        return {
            "status": "success",
            "message": "Workflow validation passed",
            "workflow_id": workflow_id,
            "steps": len(workflow.get("nodes", []))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error test running workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to test run workflow: {str(e)}")
