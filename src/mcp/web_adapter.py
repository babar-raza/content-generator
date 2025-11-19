"""MCP-Compliant Web Adapter for UCOP.

Provides MCP-compliant REST endpoints that wrap the unified engine,
ensuring CLI and Web UI communicate through the same protocol.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.mcp.protocol import (
    MCPRequest, MCPResponse, MCPError,
    ResourceType, ResourceStatus,
    JobResource, WorkflowResource, AgentResource,
    create_resource_uri
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])


class JobCreateRequest(BaseModel):
    """MCP-compliant job creation request."""
    workflow_name: str
    input_data: Dict[str, Any]
    params: Optional[Dict[str, Any]] = {}
    blog_mode: bool = False
    title: Optional[str] = None


class JobControlRequest(BaseModel):
    """MCP-compliant job control request."""
    job_id: str


class MCPToolCallRequest(BaseModel):
    """MCP tool call request."""
    name: str
    arguments: Dict[str, Any]


# Global executor and config references (set by app initialization)
_executor = None
_config_snapshot = None


def set_executor(executor, config_snapshot=None):
    """Set the unified executor instance and config snapshot.
    
    Args:
        executor: Unified engine executor
        config_snapshot: Optional configuration snapshot
    """
    global _executor, _config_snapshot
    _executor = executor
    _config_snapshot = config_snapshot
    logger.info("MCP adapter connected to executor (config=%s)", bool(config_snapshot))


def get_executor():
    """Get the executor instance."""
    if _executor is None:
        raise HTTPException(status_code=503, detail="Executor not initialized")
    return _executor


def get_config_snapshot():
    """Get the configuration snapshot."""
    if _config_snapshot is None:
        logger.warning("Config snapshot not available")
        return None
    return _config_snapshot


@router.post("/request", response_model=MCPResponse)
async def mcp_request(request: MCPRequest):
    """Handle MCP-compliant requests.
    
    This is the main entry point for MCP protocol communication.
    All operations go through this endpoint using MCP's method routing.
    """
    try:
        method = request.method
        params = request.params
        
        # Route to appropriate handler
        if method == "jobs/create":
            result = await handle_job_create(params)
        elif method == "jobs/list":
            result = await handle_jobs_list(params)
        elif method == "jobs/get":
            result = await handle_job_get(params)
        elif method == "jobs/pause":
            result = await handle_job_pause(params)
        elif method == "jobs/resume":
            result = await handle_job_resume(params)
        elif method == "jobs/cancel":
            result = await handle_job_cancel(params)
        elif method == "workflows/list":
            result = await handle_workflows_list(params)
        elif method == "workflows/visual":
            result = await handle_workflow_visual(params)
        elif method == "workflows/profiles":
            result = await handle_workflow_profiles(params)
        elif method == "workflows/metrics":
            result = await handle_workflow_metrics(params)
        elif method == "workflows/reset":
            result = await handle_workflow_reset(params)
        elif method == "agents/list":
            result = await handle_agents_list(params)
        elif method == "agents/invoke":
            result = await handle_agents_invoke(params)
        elif method == "agents/status":
            result = await handle_agents_status(params)
        elif method == "ingest/kb":
            result = await handle_ingest_kb_web(params)
        elif method == "ingest/docs":
            result = await handle_ingest_docs_web(params)
        elif method == "ingest/api":
            result = await handle_ingest_api_web(params)
        elif method == "ingest/blog":
            result = await handle_ingest_blog_web(params)
        elif method == "ingest/tutorial":
            result = await handle_ingest_tutorial_web(params)
        elif method == "topics/discover":
            result = await handle_topics_discover_web(params)
        elif method == "flows/realtime":
            result = await handle_flows_realtime(params)
        elif method == "flows/history":
            result = await handle_flows_history(params)
        elif method == "flows/bottlenecks":
            result = await handle_flows_bottlenecks(params)
        elif method == "debug/sessions/create":
            result = await handle_debug_session_create(params)
        elif method == "debug/sessions/get":
            result = await handle_debug_session_get(params)
        elif method == "debug/breakpoints/add":
            result = await handle_debug_breakpoint_add(params)
        elif method == "debug/breakpoints/remove":
            result = await handle_debug_breakpoint_remove(params)
        elif method == "debug/step":
            result = await handle_debug_step(params)
        elif method == "debug/continue":
            result = await handle_debug_continue(params)
        elif method == "debug/trace":
            result = await handle_debug_trace(params)
        else:
            return MCPResponse(
                error={"code": -32601, "message": f"Method not found: {method}"},
                id=request.id
            )
        
        return MCPResponse(result=result, id=request.id)
        
    except Exception as e:
        logger.error(f"MCP request failed: {e}", exc_info=True)
        return MCPResponse(
            error={"code": -32603, "message": str(e)},
            id=request.id
        )


async def handle_job_create(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle job creation via MCP protocol."""
    executor = get_executor()
    
    workflow_name = params.get("workflow_name")
    input_data = params.get("input_data", {})
    job_params = params.get("params", {})
    blog_mode = params.get("blog_mode", False)
    title = params.get("title")
    
    if not workflow_name:
        raise ValueError("workflow_name is required")
    
    # Create job config
    from src.engine.executor import JobConfig
    
    config = JobConfig(
        workflow=workflow_name,
        input=input_data.get("topic", "Unknown Topic"),
        params=job_params,
        blog_mode=blog_mode,
        title=title
    )
    
    # Execute job
    result = executor.run_job(config)
    
    # Convert to MCP JobResource
    job_resource = JobResource(
        uri=create_resource_uri(ResourceType.JOB, result.job_id),
        job_id=result.job_id,
        workflow_uri=create_resource_uri(ResourceType.WORKFLOW, workflow_name),
        status=ResourceStatus(result.status) if result.status in ResourceStatus.__members__.values() else ResourceStatus.COMPLETED,
        created_at=result.started_at if result.started_at else datetime.now(),
        started_at=result.started_at if result.started_at else None,
        completed_at=result.completed_at if result.completed_at else None,
        metadata={
            "output_path": str(result.output_path) if result.output_path else None,
            "error": result.error
        }
    )
    
    return job_resource.model_dump()


async def handle_jobs_list(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle job listing via MCP protocol."""
    executor = get_executor()
    
    try:
        jobs_data = executor.job_engine._jobs
        
        jobs = []
        for job_id, job in jobs_data.items():
            job_dict = job.to_dict() if hasattr(job, 'to_dict') else job
            jobs.append({
                "job_id": job_id,
                "workflow_name": job_dict.get("workflow_name", "unknown"),
                "status": job_dict.get("status", "unknown"),
                "progress": job_dict.get("progress", 0),
                "started_at": job_dict.get("started_at", ""),
            })
        
        return {"jobs": jobs}
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        return {"jobs": []}


async def handle_job_get(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle job detail retrieval via MCP protocol."""
    executor = get_executor()
    
    job_id = params.get("job_id")
    if not job_id:
        raise ValueError("job_id is required")
    
    try:
        job = executor.job_engine._jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job.to_dict() if hasattr(job, 'to_dict') else job
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise HTTPException(status_code=404, detail=str(e))


async def handle_job_pause(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle job pause via MCP protocol."""
    executor = get_executor()
    
    job_id = params.get("job_id")
    if not job_id:
        raise ValueError("job_id is required")
    
    try:
        executor.job_engine.pause_job(job_id)
        return {"success": True, "job_id": job_id, "action": "paused"}
    except Exception as e:
        logger.error(f"Failed to pause job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_job_resume(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle job resume via MCP protocol."""
    executor = get_executor()
    
    job_id = params.get("job_id")
    if not job_id:
        raise ValueError("job_id is required")
    
    try:
        executor.job_engine.resume_job(job_id)
        return {"success": True, "job_id": job_id, "action": "resumed"}
    except Exception as e:
        logger.error(f"Failed to resume job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_job_cancel(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle job cancellation via MCP protocol."""
    executor = get_executor()
    
    job_id = params.get("job_id")
    if not job_id:
        raise ValueError("job_id is required")
    
    try:
        executor.job_engine.cancel_job(job_id)
        return {"success": True, "job_id": job_id, "action": "cancelled"}
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_workflows_list(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle workflow listing via MCP protocol."""
    # Return available workflows
    return {
        "workflows": [
            {
                "name": "blog_generation",
                "description": "Generate blog post from KB article",
                "uri": create_resource_uri(ResourceType.WORKFLOW, "blog_generation")
            },
            {
                "name": "content_generation",
                "description": "General content generation",
                "uri": create_resource_uri(ResourceType.WORKFLOW, "content_generation")
            }
        ]
    }


async def handle_agents_list(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle agent listing via MCP protocol."""
    # Return available agents
    return {
        "agents": [
            {
                "name": "topic_identifier",
                "type": "research",
                "status": "active",
                "uri": create_resource_uri(ResourceType.AGENT, "topic_identifier")
            },
            {
                "name": "content_writer",
                "type": "content",
                "status": "active",
                "uri": create_resource_uri(ResourceType.AGENT, "content_writer")
            }
        ]
    }


async def handle_agents_invoke(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle agent invocation via MCP protocol.
    
    Delegates to the MCP handlers module for actual agent execution.
    Ensures proper error handling and MCP protocol compliance.
    """
    from src.mcp.handlers import handle_agent_invoke
    
    # Delegate to MCP handler
    result = await handle_agent_invoke(params)
    return result


async def handle_ingest_kb_web(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle KB ingestion via MCP protocol."""
    from src.mcp.handlers import handle_ingest_kb
    result = await handle_ingest_kb(params)
    return result


async def handle_ingest_docs_web(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle docs ingestion via MCP protocol."""
    from src.mcp.handlers import handle_ingest_docs
    result = await handle_ingest_docs(params)
    return result


async def handle_ingest_api_web(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle API docs ingestion via MCP protocol."""
    from src.mcp.handlers import handle_ingest_api
    result = await handle_ingest_api(params)
    return result


async def handle_ingest_blog_web(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle blog ingestion via MCP protocol."""
    from src.mcp.handlers import handle_ingest_blog
    result = await handle_ingest_blog(params)
    return result


async def handle_ingest_tutorial_web(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tutorial ingestion via MCP protocol."""
    from src.mcp.handlers import handle_ingest_tutorial
    result = await handle_ingest_tutorial(params)
    return result



# Visualization handlers



async def handle_topics_discover_web(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle topic discovery via MCP protocol."""
    from src.mcp.handlers import handle_topics_discover
    result = await handle_topics_discover(params)
    return result

async def handle_workflow_profiles(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle workflow profiles listing."""
    try:
        from src.visualization.workflow_visualizer import WorkflowVisualizer
        visualizer = WorkflowVisualizer()
        profiles = visualizer.workflows.get('profiles', {})
        return {
            "profiles": [
                {
                    "id": profile_id,
                    "name": profile_data.get('name', profile_id),
                    "description": profile_data.get('description', ''),
                    "steps": len(profile_data.get('steps', []))
                }
                for profile_id, profile_data in profiles.items()
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get workflow profiles: {e}")
        return {"profiles": []}


async def handle_workflow_visual(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle visual workflow graph generation."""
    profile_name = params.get("profile_name")
    if not profile_name:
        raise ValueError("profile_name is required")
    
    try:
        from src.visualization.workflow_visualizer import WorkflowVisualizer
        visualizer = WorkflowVisualizer()
        graph = visualizer.create_visual_graph(profile_name)
        return graph
    except Exception as e:
        logger.error(f"Failed to create visual workflow: {e}")
        raise ValueError(f"Workflow visualization failed: {str(e)}")


async def handle_workflow_metrics(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle workflow metrics retrieval."""
    profile_name = params.get("profile_name")
    if not profile_name:
        raise ValueError("profile_name is required")
    
    try:
        from src.visualization.workflow_visualizer import WorkflowVisualizer
        visualizer = WorkflowVisualizer()
        metrics = visualizer.get_execution_metrics(profile_name)
        return metrics
    except Exception as e:
        logger.error(f"Failed to get workflow metrics: {e}")
        return {"error": str(e)}


async def handle_workflow_reset(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle workflow state reset."""
    profile_name = params.get("profile_name")
    if not profile_name:
        raise ValueError("profile_name is required")
    
    try:
        from src.visualization.workflow_visualizer import WorkflowVisualizer
        visualizer = WorkflowVisualizer()
        visualizer.reset_execution_state(profile_name)
        return {"success": True, "profile": profile_name}
    except Exception as e:
        logger.error(f"Failed to reset workflow: {e}")
        raise ValueError(f"Workflow reset failed: {str(e)}")


async def handle_agents_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle agent status retrieval."""
    try:
        from src.visualization.monitor import get_monitor
        monitor = get_monitor()
        return {
            "agents": monitor.get_agent_states(),
            "total": monitor.get_agent_count()
        }
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
        return {"agents": [], "total": 0}


async def handle_flows_realtime(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle real-time flow state retrieval."""
    try:
        from src.visualization.monitor import get_monitor
        monitor = get_monitor()
        from datetime import datetime
        return {
            "active_flows": monitor.get_active_flows(),
            "agents": monitor.get_agent_states(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get realtime flows: {e}")
        return {"active_flows": [], "agents": []}


async def handle_flows_history(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle flow history retrieval."""
    correlation_id = params.get("correlation_id")
    if not correlation_id:
        raise ValueError("correlation_id is required")
    
    try:
        from src.visualization.agent_flow_monitor import get_flow_monitor
        monitor = get_flow_monitor()
        history = monitor.get_flow_history(correlation_id)
        return {"correlation_id": correlation_id, "history": history}
    except Exception as e:
        logger.error(f"Failed to get flow history: {e}")
        return {"history": []}


async def handle_flows_bottlenecks(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle bottleneck detection."""
    try:
        from src.visualization.agent_flow_monitor import get_flow_monitor
        monitor = get_flow_monitor()
        bottlenecks = monitor.detect_bottlenecks()
        return {"bottlenecks": bottlenecks}
    except Exception as e:
        logger.error(f"Failed to detect bottlenecks: {e}")
        return {"bottlenecks": []}


async def handle_debug_session_create(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle debug session creation."""
    correlation_id = params.get("correlation_id")
    if not correlation_id:
        raise ValueError("correlation_id is required")
    
    try:
        from src.visualization.workflow_debugger import get_workflow_debugger
        debugger = get_workflow_debugger()
        session_id = debugger.start_debug_session(correlation_id)
        return {
            "session_id": session_id,
            "correlation_id": correlation_id,
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Failed to create debug session: {e}")
        raise ValueError(f"Debug session creation failed: {str(e)}")


async def handle_debug_session_get(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle debug session retrieval."""
    session_id = params.get("session_id")
    if not session_id:
        raise ValueError("session_id is required")
    
    try:
        from src.visualization.workflow_debugger import get_workflow_debugger
        debugger = get_workflow_debugger()
        if session_id not in debugger.debug_sessions:
            raise ValueError("Session not found")
        session = debugger.debug_sessions[session_id]
        return session.to_dict()
    except Exception as e:
        logger.error(f"Failed to get debug session: {e}")
        raise ValueError(f"Debug session retrieval failed: {str(e)}")


async def handle_debug_breakpoint_add(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle breakpoint addition."""
    session_id = params.get("session_id")
    agent_id = params.get("agent_id")
    event_type = params.get("event_type")
    condition = params.get("condition")
    max_hits = params.get("max_hits")
    
    if not session_id or not agent_id or not event_type:
        raise ValueError("session_id, agent_id, and event_type are required")
    
    try:
        from src.visualization.workflow_debugger import get_workflow_debugger
        debugger = get_workflow_debugger()
        breakpoint_id = debugger.add_breakpoint(
            session_id=session_id,
            agent_id=agent_id,
            event_type=event_type,
            condition=condition,
            max_hits=max_hits
        )
        return {
            "breakpoint_id": breakpoint_id,
            "session_id": session_id,
            "agent_id": agent_id,
            "event_type": event_type
        }
    except Exception as e:
        logger.error(f"Failed to add breakpoint: {e}")
        raise ValueError(f"Breakpoint addition failed: {str(e)}")


async def handle_debug_breakpoint_remove(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle breakpoint removal."""
    session_id = params.get("session_id")
    breakpoint_id = params.get("breakpoint_id")
    
    if not session_id or not breakpoint_id:
        raise ValueError("session_id and breakpoint_id are required")
    
    try:
        from src.visualization.workflow_debugger import get_workflow_debugger
        debugger = get_workflow_debugger()
        debugger.remove_breakpoint(session_id, breakpoint_id)
        return {"success": True, "breakpoint_id": breakpoint_id}
    except Exception as e:
        logger.error(f"Failed to remove breakpoint: {e}")
        raise ValueError(f"Breakpoint removal failed: {str(e)}")


async def handle_debug_step(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle debug step."""
    session_id = params.get("session_id")
    if not session_id:
        raise ValueError("session_id is required")
    
    try:
        from src.visualization.workflow_debugger import get_workflow_debugger
        debugger = get_workflow_debugger()
        debugger.step_next(session_id)
        return {"success": True, "session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to step debug session: {e}")
        raise ValueError(f"Debug step failed: {str(e)}")


async def handle_debug_continue(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle debug continue."""
    session_id = params.get("session_id")
    if not session_id:
        raise ValueError("session_id is required")
    
    try:
        from src.visualization.workflow_debugger import get_workflow_debugger
        debugger = get_workflow_debugger()
        debugger.continue_execution(session_id)
        return {"success": True, "session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to continue debug session: {e}")
        raise ValueError(f"Debug continue failed: {str(e)}")


async def handle_debug_trace(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle execution trace retrieval."""
    workflow_id = params.get("workflow_id")
    if not workflow_id:
        raise ValueError("workflow_id is required")
    
    try:
        from src.visualization.workflow_debugger import get_workflow_debugger
        debugger = get_workflow_debugger()
        trace = debugger.get_execution_trace(workflow_id)
        return {"workflow_id": workflow_id, "trace": trace}
    except Exception as e:
        logger.error(f"Failed to get execution trace: {e}")
        return {"trace": []}


# REST-style endpoints that wrap MCP protocol (for convenience)

@router.post("/jobs/create")
async def create_job(request: JobCreateRequest):
    """REST endpoint for job creation.
    
    Args:
        request: Job creation request with workflow and input data
        
    Returns:
        Dict with job details
    """
    try:
        params = {
            "workflow_name": request.workflow_name,
            "input_data": request.input_data,
            "params": request.params,
            "blog_mode": request.blog_mode,
            "title": request.title
        }
        result = await handle_job_create(params)
        return result
    except Exception as e:
        logger.error(f"Error creating job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def list_jobs(status: Optional[str] = None, limit: int = 100):
    """REST endpoint for job listing.
    
    Args:
        status: Optional status filter
        limit: Maximum number of jobs to return
        
    Returns:
        Dict containing list of jobs
    """
    try:
        params = {}
        if status:
            params["status"] = status
        if limit:
            params["limit"] = limit
        result = await handle_jobs_list(params)
        return result
    except Exception as e:
        logger.error(f"Error listing jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """REST endpoint for job details.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Dict containing job details
    """
    try:
        result = await handle_job_get({"job_id": job_id})
        return result
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}", exc_info=True)
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    """REST endpoint for pausing a job.
    
    Args:
        job_id: Job identifier to pause
        
    Returns:
        Dict with success status
    """
    try:
        result = await handle_job_pause({"job_id": job_id})
        return result
    except Exception as e:
        logger.error(f"Error pausing job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """REST endpoint for resuming a job.
    
    Args:
        job_id: Job identifier to resume
        
    Returns:
        Dict with success status
    """
    try:
        result = await handle_job_resume({"job_id": job_id})
        return result
    except Exception as e:
        logger.error(f"Error resuming job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """REST endpoint for canceling a job.
    
    Args:
        job_id: Job identifier to cancel
        
    Returns:
        Dict with success status
    """
    try:
        result = await handle_job_cancel({"job_id": job_id})
        return result
    except Exception as e:
        logger.error(f"Error canceling job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows")
async def list_workflows():
    """REST endpoint for workflow listing.
    
    Returns:
        Dict containing list of available workflows
    """
    try:
        result = await handle_workflows_list({})
        return result
    except Exception as e:
        logger.error(f"Error listing workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def list_agents():
    """REST endpoint for agent listing.
    
    Returns:
        Dict containing list of available agents
    """
    try:
        result = await handle_agents_list({})
        return result
    except Exception as e:
        logger.error(f"Error listing agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Visualization REST endpoints

@router.get("/workflows/profiles")
async def list_workflow_profiles():
    """REST endpoint for workflow profiles."""
    request_obj = MCPRequest(method="workflows/profiles", params={})
    return await mcp_request(request_obj)


@router.get("/workflows/visual/{profile_name}")
async def get_visual_workflow(profile_name: str):
    """REST endpoint for visual workflow graph."""
    request_obj = MCPRequest(
        method="workflows/visual",
        params={"profile_name": profile_name}
    )
    return await mcp_request(request_obj)


@router.get("/workflows/{profile_name}/metrics")
async def get_workflow_metrics(profile_name: str):
    """REST endpoint for workflow metrics."""
    request_obj = MCPRequest(
        method="workflows/metrics",
        params={"profile_name": profile_name}
    )
    return await mcp_request(request_obj)


@router.post("/workflows/{profile_name}/reset")
async def reset_workflow(profile_name: str):
    """REST endpoint for workflow reset."""
    request_obj = MCPRequest(
        method="workflows/reset",
        params={"profile_name": profile_name}
    )
    return await mcp_request(request_obj)


@router.get("/agents/status")
async def get_agents_status():
    """REST endpoint for agent status."""
    request_obj = MCPRequest(method="agents/status", params={})
    return await mcp_request(request_obj)


@router.get("/flows/realtime")
async def get_realtime_flows():
    """REST endpoint for real-time flows."""
    request_obj = MCPRequest(method="flows/realtime", params={})
    return await mcp_request(request_obj)


@router.get("/flows/history/{correlation_id}")
async def get_flow_history(correlation_id: str):
    """REST endpoint for flow history."""
    request_obj = MCPRequest(
        method="flows/history",
        params={"correlation_id": correlation_id}
    )
    return await mcp_request(request_obj)


@router.get("/flows/bottlenecks")
async def get_bottlenecks():
    """REST endpoint for bottleneck detection."""
    request_obj = MCPRequest(method="flows/bottlenecks", params={})
    return await mcp_request(request_obj)


@router.post("/debug/sessions")
async def create_debug_session_rest(correlation_id: str):
    """REST endpoint for debug session creation."""
    request_obj = MCPRequest(
        method="debug/sessions/create",
        params={"correlation_id": correlation_id}
    )
    return await mcp_request(request_obj)


@router.get("/debug/sessions/{session_id}")
async def get_debug_session_rest(session_id: str):
    """REST endpoint for debug session retrieval."""
    request_obj = MCPRequest(
        method="debug/sessions/get",
        params={"session_id": session_id}
    )
    return await mcp_request(request_obj)


class BreakpointAddRequest(BaseModel):
    """Breakpoint addition request."""
    session_id: str
    agent_id: str
    event_type: str
    condition: Optional[str] = None
    max_hits: Optional[int] = None


@router.post("/debug/breakpoints")
async def add_breakpoint_rest(request: BreakpointAddRequest):
    """REST endpoint for breakpoint addition."""
    request_obj = MCPRequest(
        method="debug/breakpoints/add",
        params=request.dict()
    )
    return await mcp_request(request_obj)


@router.delete("/debug/sessions/{session_id}/breakpoints/{breakpoint_id}")
async def remove_breakpoint_rest(session_id: str, breakpoint_id: str):
    """REST endpoint for breakpoint removal."""
    request_obj = MCPRequest(
        method="debug/breakpoints/remove",
        params={"session_id": session_id, "breakpoint_id": breakpoint_id}
    )
    return await mcp_request(request_obj)


@router.post("/debug/sessions/{session_id}/step")
async def step_debug_rest(session_id: str):
    """REST endpoint for debug step."""
    request_obj = MCPRequest(
        method="debug/step",
        params={"session_id": session_id}
    )
    return await mcp_request(request_obj)


@router.post("/debug/sessions/{session_id}/continue")
async def continue_debug_rest(session_id: str):
    """REST endpoint for debug continue."""
    request_obj = MCPRequest(
        method="debug/continue",
        params={"session_id": session_id}
    )
    return await mcp_request(request_obj)


@router.get("/debug/workflows/{workflow_id}/trace")
async def get_trace_rest(workflow_id: str):
    """REST endpoint for execution trace."""
    request_obj = MCPRequest(
        method="debug/trace",
        params={"workflow_id": workflow_id}
    )
    return await mcp_request(request_obj)


@router.get("/config/snapshot")
async def get_config_snapshot_rest():
    """REST endpoint for configuration snapshot retrieval.
    
    Returns the current configuration snapshot including:
    - Agent configurations
    - Performance settings
    - Tone settings
    - Main pipeline configuration
    """
    config = get_config_snapshot()
    
    if config is None:
        return {
            "status": "unavailable",
            "message": "Configuration snapshot not initialized"
        }
    
    return {
        "status": "success",
        "config": {
            "hash": config.config_hash,
            "timestamp": config.timestamp,
            "engine_version": config.engine_version,
            "agent_count": len(config.agent_config.get('agents', {})),
            "workflows": list(config.main_config.get('workflows', {}).keys()),
            "tone_sections": list(config.tone_config.get('section_controls', {}).keys()),
            "perf_timeouts": config.perf_config.get('timeouts', {}),
            "perf_limits": config.perf_config.get('limits', {})
        }
    }


@router.get("/config/agents")
async def get_agent_configs_rest():
    """REST endpoint for agent configuration retrieval."""
    config = get_config_snapshot()
    
    if config is None:
        raise HTTPException(status_code=503, detail="Configuration not available")
    
    agents = config.agent_config.get('agents', {})
    
    return {
        "status": "success",
        "agent_count": len(agents),
        "agents": {
            agent_id: {
                "id": agent_data.get('id'),
                "version": agent_data.get('version'),
                "description": agent_data.get('description'),
                "capabilities": agent_data.get('capabilities', {}),
                "resources": agent_data.get('resources', {})
            }
            for agent_id, agent_data in agents.items()
        }
    }


@router.get("/config/workflows")
async def get_workflow_configs_rest():
    """REST endpoint for workflow configuration retrieval."""
    config = get_config_snapshot()
    
    if config is None:
        raise HTTPException(status_code=503, detail="Configuration not available")
    
    workflows = config.main_config.get('workflows', {})
    dependencies = config.main_config.get('dependencies', {})
    
    return {
        "status": "success",
        "workflow_count": len(workflows),
        "workflows": workflows,
        "dependencies": dependencies
    }


@router.get("/config/tone")
async def get_tone_config_rest():
    """REST endpoint for tone configuration retrieval."""
    config = get_config_snapshot()
    
    if config is None:
        raise HTTPException(status_code=503, detail="Configuration not available")
    
    return {
        "status": "success",
        "global_voice": config.tone_config.get('global_voice', {}),
        "section_controls": config.tone_config.get('section_controls', {}),
        "heading_style": config.tone_config.get('heading_style', {}),
        "code_template_overrides": config.tone_config.get('code_template_overrides', {})
    }


@router.get("/config/performance")
async def get_perf_config_rest():
    """REST endpoint for performance configuration retrieval."""
    config = get_config_snapshot()
    
    if config is None:
        raise HTTPException(status_code=503, detail="Configuration not available")
    
    return {
        "status": "success",
        "timeouts": config.perf_config.get('timeouts', {}),
        "limits": config.perf_config.get('limits', {}),
        "batch": config.perf_config.get('batch', {}),
        "hot_paths": config.perf_config.get('hot_paths', {}),
        "tuning": config.perf_config.get('tuning', {})
    }

# DOCGEN:LLM-FIRST@v4


@router.get("/methods")
async def list_mcp_methods():
    """List all available MCP methods.
    
    Returns:
        List of supported MCP methods with descriptions
    """
    return {
        "methods": [
            {
                "name": "jobs/create",
                "description": "Create a new job",
                "params": {
                    "workflow_name": "string (required)",
                    "input_data": "object (required)",
                    "params": "object (optional)",
                    "blog_mode": "boolean (optional)",
                    "title": "string (optional)"
                }
            },
            {
                "name": "jobs/list",
                "description": "List all jobs",
                "params": {}
            },
            {
                "name": "jobs/get",
                "description": "Get job details",
                "params": {
                    "job_id": "string (required)"
                }
            },
            {
                "name": "jobs/pause",
                "description": "Pause a job",
                "params": {
                    "job_id": "string (required)"
                }
            },
            {
                "name": "jobs/resume",
                "description": "Resume a paused job",
                "params": {
                    "job_id": "string (required)"
                }
            },
            {
                "name": "jobs/cancel",
                "description": "Cancel a job",
                "params": {
                    "job_id": "string (required)"
                }
            },
            {
                "name": "workflows/list",
                "description": "List all workflows",
                "params": {}
            },
            {
                "name": "workflows/visual",
                "description": "Get workflow visualization",
                "params": {
                    "profile_name": "string (required)"
                }
            },
            {
                "name": "workflows/profiles",
                "description": "List workflow profiles",
                "params": {}
            },
            {
                "name": "workflows/metrics",
                "description": "Get workflow metrics",
                "params": {
                    "profile_name": "string (required)"
                }
            },
            {
                "name": "workflows/reset",
                "description": "Reset workflow state",
                "params": {
                    "profile_name": "string (required)"
                }
            },
            {
                "name": "agents/list",
                "description": "List all agents",
                "params": {}
            },
            {
                "name": "agents/status",
                "description": "Get agent status",
                "params": {}
            },
            {
                "name": "ingest/kb",
                "description": "Ingest KB articles",
                "params": {
                    "kb_path": "string (required)"
                }
            },
            {
                "name": "ingest/docs",
                "description": "Ingest documentation",
                "params": {
                    "docs_path": "string (required)"
                }
            },
            {
                "name": "ingest/api",
                "description": "Ingest API reference",
                "params": {
                    "api_path": "string (required)"
                }
            },
            {
                "name": "ingest/blog",
                "description": "Ingest blog posts",
                "params": {
                    "blog_path": "string (required)"
                }
            },
            {
                "name": "ingest/tutorial",
                "description": "Ingest tutorials",
                "params": {
                    "tutorial_path": "string (required)"
                }
            },
            {
                "name": "topics/discover",
                "description": "Discover topics from directories",
                "params": {
                    "kb_path": "string (optional)",
                    "docs_path": "string (optional)",
                    "max_topics": "integer (optional, default: 50)"
                }
            },
            {
                "name": "flows/realtime",
                "description": "Get realtime flows",
                "params": {}
            },
            {
                "name": "flows/history",
                "description": "Get flow history",
                "params": {
                    "correlation_id": "string (required)"
                }
            },
            {
                "name": "flows/bottlenecks",
                "description": "Detect bottlenecks",
                "params": {}
            },
            {
                "name": "debug/sessions/create",
                "description": "Create debug session",
                "params": {
                    "correlation_id": "string (required)"
                }
            },
            {
                "name": "debug/sessions/get",
                "description": "Get debug session",
                "params": {
                    "session_id": "string (required)"
                }
            },
            {
                "name": "debug/breakpoints/add",
                "description": "Add breakpoint",
                "params": {
                    "session_id": "string (required)",
                    "agent_id": "string (required)",
                    "event_type": "string (required)",
                    "condition": "string (optional)",
                    "max_hits": "integer (optional)"
                }
            },
            {
                "name": "debug/breakpoints/remove",
                "description": "Remove breakpoint",
                "params": {
                    "session_id": "string (required)",
                    "breakpoint_id": "string (required)"
                }
            },
            {
                "name": "debug/step",
                "description": "Step through debug session",
                "params": {
                    "session_id": "string (required)"
                }
            },
            {
                "name": "debug/continue",
                "description": "Continue debug session",
                "params": {
                    "session_id": "string (required)"
                }
            },
            {
                "name": "debug/trace",
                "description": "Get execution trace",
                "params": {
                    "workflow_id": "string (required)"
                }
            }
        ]
    }


@router.get("/status")
async def mcp_status():
    """Check MCP adapter status.
    
    Returns:
        Status information including executor and config availability
    """
    executor_status = _executor is not None
    config_status = _config_snapshot is not None
    
    status = {
        "status": "ready" if executor_status else "not_ready",
        "executor_initialized": executor_status,
        "config_initialized": config_status,
        "endpoints_available": 31  # Updated count including /methods and /status
    }
    
    if executor_status and hasattr(_executor, 'job_engine'):
        status["job_engine_connected"] = _executor.job_engine is not None
    
    if config_status:
        status["config_hash"] = _config_snapshot.config_hash[:8] if hasattr(_config_snapshot, 'config_hash') else 'unknown'
    
    return status
