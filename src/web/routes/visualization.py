"""Visualization API routes for workflow and agent monitoring."""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
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
# Workflow Visualization Endpoints
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
