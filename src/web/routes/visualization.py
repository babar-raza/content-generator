"""Visualization API routes for workflow and agent monitoring."""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

from ..models import (
    WorkflowGraphResponse,
    WorkflowListResponse,
    WorkflowRenderResponse,
    AgentMetricsResponse,
    AgentListMetricsResponse,
    SystemMetricsResponse,
    JobMetricsResponse,
)
from ...visualization.workflow_visualizer import WorkflowVisualizer
from ...visualization.agent_flow_monitor import get_flow_monitor
from ...visualization.monitor import VisualOrchestrationMonitor
from ...visualization.workflow_debugger import get_workflow_debugger
from ..connection_manager import get_connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["visualization"])

# Global instances (will be initialized on first use)
_workflow_visualizer = None
_flow_monitor = None
_orchestration_monitor = None


def get_workflow_visualizer():
    """Get or create workflow visualizer instance."""
    global _workflow_visualizer
    if _workflow_visualizer is None:
        _workflow_visualizer = WorkflowVisualizer()
    return _workflow_visualizer


def get_flow_monitor_instance():
    """Get or create flow monitor instance."""
    global _flow_monitor
    if _flow_monitor is None:
        _flow_monitor = get_flow_monitor()
    return _flow_monitor


def get_orchestration_monitor():
    """Get or create orchestration monitor instance."""
    global _orchestration_monitor
    if _orchestration_monitor is None:
        _orchestration_monitor = VisualOrchestrationMonitor()
    return _orchestration_monitor


# ============================================================================
# NEW: Enhanced Visualization Endpoints (Task Card 04)
# ============================================================================

@router.get("/viz/workflows")
async def viz_workflows_json(format: str = Query(default="json")):
    """List all workflows (mirrors cmd_viz_workflows).
    
    Args:
        format: Output format ('json' only for now)
        
    Returns:
        JSON response with workflow profiles
    """
    try:
        visualizer = get_workflow_visualizer()
        profiles = visualizer.workflows.get('profiles', {})
        
        result = {
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
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error getting workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get workflows: {str(e)}")


@router.get("/viz/graph/{workflow_id}")
async def viz_graph(
    workflow_id: str,
    job_id: Optional[str] = None
):
    """Get workflow execution graph (mirrors cmd_viz_graph).
    
    Args:
        workflow_id: Workflow identifier
        job_id: Optional job ID to overlay execution data
        
    Returns:
        Graph data with nodes and edges
    """
    try:
        visualizer = get_workflow_visualizer()
        
        # Check if workflow exists
        if workflow_id not in visualizer.workflows.get('profiles', {}):
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
        
        # Create visual graph
        graph = visualizer.create_visual_graph(workflow_id)
        
        if job_id:
            # Overlay execution data if job_id provided
            debugger = get_workflow_debugger()
            if hasattr(debugger, 'get_execution_trace'):
                try:
                    execution_data = debugger.get_execution_trace(job_id)
                    # Overlay execution state onto graph nodes
                    if execution_data and 'steps' in execution_data:
                        for node in graph.get('nodes', []):
                            step_id = node['id']
                            if step_id in execution_data['steps']:
                                node['data']['execution'] = execution_data['steps'][step_id]
                except Exception as e:
                    logger.warning(f"Could not overlay execution data: {e}")
        
        return JSONResponse(content=graph)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get graph: {str(e)}")


@router.get("/viz/metrics")
async def viz_metrics(
    workflow_id: Optional[str] = None,
    time_range: str = Query(default="24h"),
    granularity: str = Query(default="1h")
):
    """Get system/workflow metrics (mirrors cmd_viz_metrics).
    
    Args:
        workflow_id: Optional workflow to get specific metrics
        time_range: Time range for metrics (e.g., '24h', '7d')
        granularity: Granularity for data points (e.g., '1h', '5m')
        
    Returns:
        Metrics data
    """
    try:
        visualizer = get_workflow_visualizer()
        monitor = get_orchestration_monitor()
        
        if workflow_id:
            # Get workflow-specific metrics
            if workflow_id not in visualizer.workflows.get('profiles', {}):
                raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
            
            metrics = visualizer.get_execution_metrics(workflow_id)
        else:
            # Get system-wide metrics
            metrics = {
                "time_range": time_range,
                "granularity": granularity,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system": {
                    "total_jobs": len(getattr(monitor, 'active_jobs', {})),
                    "total_agents": len(getattr(monitor, 'registered_agents', [])),
                    "active_flows": len(getattr(monitor, 'active_flows', {}))
                },
                "throughput": {
                    "jobs_per_hour": 0,  # Would be calculated from historical data
                    "agents_per_hour": 0
                },
                "performance": {
                    "avg_job_duration": 0.0,
                    "avg_agent_duration": 0.0
                }
            }
        
        return JSONResponse(content=metrics)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/viz/agents")
async def viz_agents():
    """Get agent status visualization (mirrors cmd_viz_agents).
    
    Returns:
        Agent status data
    """
    try:
        from src.visualization.monitor import get_monitor

        monitor = get_monitor()

        # Try to get agent states; fall back to empty if method doesn't exist
        try:
            agents = monitor.get_agent_states() if hasattr(monitor, 'get_agent_states') else []
        except Exception:
            agents = []

        result = {
            "agents": agents,
            "total": len(agents)
        }

        return JSONResponse(content=result)
    except Exception as e:
        logger.warning(f"Error getting agents: {e}")
        # Return empty result instead of 500
        return JSONResponse(content={"agents": [], "total": 0})


@router.get("/viz/flows")
async def viz_flows(
    workflow_id: Optional[str] = None,
    job_id: Optional[str] = None
):
    """Get data flow visualization (mirrors cmd_viz_flows).
    
    Args:
        workflow_id: Optional workflow to filter flows
        job_id: Optional job to filter flows
        
    Returns:
        Active data flows
    """
    try:
        from src.visualization.monitor import get_monitor

        monitor = get_monitor()

        # Try to get active flows; fall back to empty if method doesn't exist
        try:
            flows = monitor.get_active_flows() if hasattr(monitor, 'get_active_flows') else []
        except Exception:
            flows = []

        # Filter by workflow_id or job_id if provided
        if workflow_id:
            flows = [f for f in flows if f.get('workflow_id') == workflow_id]
        if job_id:
            flows = [f for f in flows if f.get('job_id') == job_id]

        result = {
            "active_flows": flows,
            "count": len(flows)
        }

        return JSONResponse(content=result)
    except Exception as e:
        logger.warning(f"Error getting flows: {e}")
        # Return empty result instead of 500
        return JSONResponse(content={"active_flows": [], "count": 0})


@router.get("/viz/bottlenecks")
async def viz_bottlenecks(
    workflow_id: Optional[str] = None,
    threshold_seconds: float = Query(default=5.0)
):
    """Analyze performance bottlenecks (mirrors cmd_viz_bottlenecks).
    
    Args:
        workflow_id: Optional workflow to analyze
        threshold_seconds: Threshold for slow operations
        
    Returns:
        Detected bottlenecks
    """
    try:
        flow_monitor = get_flow_monitor_instance()
        
        # Detect bottlenecks
        if hasattr(flow_monitor, 'detect_bottlenecks'):
            bottlenecks = flow_monitor.detect_bottlenecks()
        else:
            # Fallback: analyze agent execution times
            monitor = get_orchestration_monitor()
            bottlenecks = []
            
            for agent_id, metrics in getattr(monitor, 'agent_metrics', {}).items():
                if hasattr(metrics, 'to_dict'):
                    metrics_dict = metrics.to_dict()
                    avg_duration = metrics_dict.get('avg_execution_time', 0)
                    
                    if avg_duration > threshold_seconds:
                        bottlenecks.append({
                            "agent_id": agent_id,
                            "duration": avg_duration,
                            "type": "slow_agent",
                            "threshold": threshold_seconds
                        })
        
        # Filter by workflow if provided
        if workflow_id:
            bottlenecks = [b for b in bottlenecks if b.get('workflow_id') == workflow_id]
        
        result = {
            "bottlenecks": bottlenecks,
            "count": len(bottlenecks),
            "threshold_seconds": threshold_seconds
        }
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error detecting bottlenecks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to detect bottlenecks: {str(e)}")


@router.get("/viz/debug/{job_id}")
async def viz_debug(job_id: str):
    """Get debug visualization for job (mirrors cmd_viz_debug).
    
    Args:
        job_id: Job identifier
        
    Returns:
        Debug data for job
    """
    try:
        debugger = get_workflow_debugger()
        
        # Get debug data
        debug_data = {
            "job_id": job_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if hasattr(debugger, 'get_debug_data'):
            debug_data.update(debugger.get_debug_data(job_id))
        elif hasattr(debugger, 'debug_sessions'):
            # Try to find session for this job
            sessions = debugger.debug_sessions
            for session_id, session in sessions.items():
                if hasattr(session, 'correlation_id') and session.correlation_id == job_id:
                    if hasattr(session, 'to_dict'):
                        debug_data['session'] = session.to_dict()
                    break
        
        return JSONResponse(content=debug_data)
    except Exception as e:
        logger.error(f"Error getting debug data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get debug data: {str(e)}")


# ============================================================================
# Workflow Visualization Endpoints (Existing)
# ============================================================================

@router.get("/visualization/workflows", response_model=WorkflowListResponse)
async def list_workflows():
    """List all available workflows.
    
    Returns:
        WorkflowListResponse with list of workflow IDs and names
    """
    try:
        visualizer = get_workflow_visualizer()
        
        workflows = []
        for profile_name, profile_data in visualizer.workflows.get('profiles', {}).items():
            workflows.append({
                "workflow_id": profile_name,
                "name": profile_data.get('name', profile_name),
                "description": profile_data.get('description', ''),
                "total_steps": len(profile_data.get('steps', []))
            })
        
        # Sort alphabetically by workflow_id for deterministic output
        workflows.sort(key=lambda x: x['workflow_id'])
        
        return WorkflowListResponse(
            workflows=workflows,
            total=len(workflows)
        )
    except Exception as e:
        logger.error(f"Error listing workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")


@router.get("/visualization/workflows/{workflow_id}", response_model=WorkflowGraphResponse)
async def get_workflow_graph(workflow_id: str):
    """Get workflow graph data for visualization.
    
    Args:
        workflow_id: Workflow identifier
        
    Returns:
        WorkflowGraphResponse with nodes and edges for React Flow
    """
    try:
        visualizer = get_workflow_visualizer()
        
        # Check if workflow exists
        if workflow_id not in visualizer.workflows.get('profiles', {}):
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
        
        # Create visual graph
        graph_data = visualizer.create_visual_graph(workflow_id)
        
        return WorkflowGraphResponse(**graph_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get workflow graph: {str(e)}")


@router.get("/visualization/workflows/{workflow_id}/render", response_model=WorkflowRenderResponse)
async def render_workflow(workflow_id: str, format: str = "json"):
    """Render workflow as DOT or JSON format.
    
    Args:
        workflow_id: Workflow identifier
        format: Output format ('dot' or 'json')
        
    Returns:
        WorkflowRenderResponse with rendered workflow
    """
    try:
        visualizer = get_workflow_visualizer()
        
        # Check if workflow exists
        if workflow_id not in visualizer.workflows.get('profiles', {}):
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
        
        if format not in ["dot", "json"]:
            raise HTTPException(status_code=400, detail="Format must be 'dot' or 'json'")
        
        # Get workflow data
        graph_data = visualizer.create_visual_graph(workflow_id)
        
        if format == "json":
            return WorkflowRenderResponse(
                workflow_id=workflow_id,
                format="json",
                content=graph_data
            )
        else:
            # Convert to DOT format
            dot_content = _convert_to_dot(graph_data)
            return WorkflowRenderResponse(
                workflow_id=workflow_id,
                format="dot",
                content={"dot": dot_content}
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to render workflow: {str(e)}")


def _convert_to_dot(graph_data: dict) -> str:
    """Convert graph data to DOT format."""
    lines = ["digraph workflow {"]
    lines.append("  rankdir=TB;")
    lines.append("  node [shape=box, style=rounded];")
    
    # Add nodes
    for node in graph_data.get('nodes', []):
        node_id = node['id']
        label = node['data']['label']
        lines.append(f'  "{node_id}" [label="{label}"];')
    
    # Add edges
    for edge in graph_data.get('edges', []):
        source = edge['source']
        target = edge['target']
        lines.append(f'  "{source}" -> "{target}";')
    
    lines.append("}")
    return "\n".join(lines)


# ============================================================================
# Agent Flow Monitoring Endpoints
# ============================================================================

@router.get("/monitoring/agents", response_model=AgentListMetricsResponse)
async def get_agent_metrics():
    """Get execution metrics for all agents.
    
    Returns:
        AgentListMetricsResponse with metrics for all agents
    """
    try:
        monitor = get_orchestration_monitor()
        
        agents = []
        for agent_id, metrics in monitor.agent_metrics.items():
            agents.append(metrics.to_dict())
        
        # Sort alphabetically by agent_id for deterministic output
        agents.sort(key=lambda x: x['agent_id'])
        
        return AgentListMetricsResponse(
            agents=agents,
            total=len(agents)
        )
    except Exception as e:
        logger.error(f"Error getting agent metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent metrics: {str(e)}")


@router.get("/monitoring/agents/{agent_id}", response_model=AgentMetricsResponse)
async def get_agent_metrics_by_id(agent_id: str):
    """Get metrics for a specific agent.
    
    Args:
        agent_id: Agent identifier
        
    Returns:
        AgentMetricsResponse with agent metrics
    """
    try:
        monitor = get_orchestration_monitor()
        
        if agent_id not in monitor.agent_metrics:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
        
        metrics = monitor.agent_metrics[agent_id]
        return AgentMetricsResponse(**metrics.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent metrics: {str(e)}")


@router.websocket("/ws/monitoring")
async def monitoring_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring updates.
    
    Streams agent execution updates and flow events.
    """
    await websocket.accept()
    logger.info("Monitoring WebSocket connection established")
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Monitoring WebSocket connected"
        })
        
        # Keep connection alive and send periodic updates
        while True:
            try:
                # Wait for messages from client (keep-alive, etc.)
                message = await websocket.receive_text()
                
                # Echo back for keep-alive
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
            except WebSocketDisconnect:
                logger.info("Monitoring WebSocket disconnected by client")
                break
            except Exception as e:
                logger.error(f"Error in monitoring WebSocket: {e}")
                await websocket.send_json({
                    "type": "error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": str(e)
                })
                break
    except Exception as e:
        logger.error(f"Monitoring WebSocket error: {e}", exc_info=True)
    finally:
        try:
            await websocket.close()
        except:
            pass


# ============================================================================
# System Monitoring Endpoints
# ============================================================================

@router.get("/monitoring/system", response_model=SystemMetricsResponse)
async def get_system_metrics():
    """Get system resource metrics.
    
    Returns:
        SystemMetricsResponse with CPU, memory, and job metrics
    """
    try:
        import psutil
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        monitor = get_orchestration_monitor()
        
        return SystemMetricsResponse(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available_mb=memory.available / (1024 * 1024),
            memory_total_mb=memory.total / (1024 * 1024),
            active_jobs=len(monitor.active_jobs),
            total_agents=len(monitor.registered_agents),
            uptime_seconds=(datetime.now(timezone.utc) - monitor.start_time).total_seconds(),
            timestamp=datetime.now(timezone.utc)
        )
    except ImportError:
        # psutil not available, return mock data
        monitor = get_orchestration_monitor()
        return SystemMetricsResponse(
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_available_mb=0.0,
            memory_total_mb=0.0,
            active_jobs=len(monitor.active_jobs),
            total_agents=len(monitor.registered_agents),
            uptime_seconds=(datetime.now(timezone.utc) - monitor.start_time).total_seconds(),
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get system metrics: {str(e)}")


@router.get("/monitoring/jobs/{job_id}/metrics", response_model=JobMetricsResponse)
async def get_job_metrics(job_id: str):
    """Get execution metrics for a specific job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JobMetricsResponse with job execution metrics
    """
    try:
        monitor = get_orchestration_monitor()
        
        if job_id not in monitor.active_jobs:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
        
        job_data = monitor.active_jobs[job_id]
        
        # Get flow data for this job
        flows = monitor.active_flows.get(job_id, [])
        
        return JobMetricsResponse(
            job_id=job_id,
            status=job_data.get('status', 'unknown'),
            total_agents=job_data.get('total_agents', 0),
            completed_agents=job_data.get('completed_agents', 0),
            failed_agents=job_data.get('failed_agents', 0),
            total_flows=len(flows),
            start_time=job_data.get('start_time'),
            end_time=job_data.get('end_time'),
            duration_seconds=job_data.get('duration_seconds', 0.0)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get job metrics: {str(e)}")
