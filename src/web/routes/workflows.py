"""Workflow management API routes."""

import logging
from fastapi import APIRouter, HTTPException, Depends

from ..models import WorkflowInfo, WorkflowList

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["workflows"])


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
async def list_workflows(
    executor=Depends(get_executor)
):
    """List all available workflows.
    
    Returns:
        WorkflowList with workflow information
    """
    try:
        workflows_data = []
        
        # Get workflows from executor
        if hasattr(executor, 'get_workflows'):
            workflows = executor.get_workflows()
            
            for workflow in workflows:
                workflows_data.append(WorkflowInfo(
                    workflow_id=workflow.get("id", workflow.get("name", "unknown")),
                    name=workflow.get("name", "Unknown"),
                    description=workflow.get("description"),
                    agents=workflow.get("agents", []),
                    metadata=workflow.get("metadata"),
                ))
        else:
            # Return empty list if executor doesn't support get_workflows
            logger.warning("Executor does not support get_workflows method")
        
        return WorkflowList(workflows=workflows_data, total=len(workflows_data))
        
    except Exception as e:
        logger.error(f"Error listing workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")


@router.get("/workflows/{workflow_id}", response_model=WorkflowInfo)
async def get_workflow(
    workflow_id: str,
    executor=Depends(get_executor)
):
    """Get information about a specific workflow.
    
    Args:
        workflow_id: Workflow identifier
        
    Returns:
        WorkflowInfo with workflow details
    """
    try:
        # Get workflow from executor
        if hasattr(executor, 'get_workflow'):
            workflow = executor.get_workflow(workflow_id)
            
            if not workflow:
                raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
            
            return WorkflowInfo(
                workflow_id=workflow.get("id", workflow_id),
                name=workflow.get("name", "Unknown"),
                description=workflow.get("description"),
                agents=workflow.get("agents", []),
                metadata=workflow.get("metadata"),
            )
        else:
            raise HTTPException(status_code=501, detail="Workflow lookup not supported")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get workflow: {str(e)}")


# Mesh orchestration endpoints
@router.get("/mesh/agents")
async def get_mesh_agents(executor=Depends(get_executor)):
    """List available agents in mesh."""
    try:
        if not hasattr(executor, 'mesh_executor') or executor.mesh_executor is None:
            raise HTTPException(status_code=501, detail="Mesh orchestration not enabled")
        
        agents = executor.mesh_executor.list_agents()
        return {"agents": agents, "total": len(agents)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing mesh agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list mesh agents: {str(e)}")


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
async def get_mesh_stats(executor=Depends(get_executor)):
    """Get mesh orchestration statistics."""
    try:
        if not hasattr(executor, 'mesh_executor') or executor.mesh_executor is None:
            raise HTTPException(status_code=501, detail="Mesh orchestration not enabled")
        
        stats = executor.mesh_executor.get_stats()
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting mesh stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get mesh stats: {str(e)}")
