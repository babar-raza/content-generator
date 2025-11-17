"""
MCP API Routes for UCOP

Provides POST /api/mcp endpoint for MCP protocol requests.
All MCP methods are accessed through this single endpoint using
JSON-RPC style method routing.
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Optional

from src.mcp.protocol import MCPRequest, MCPResponse, MCPProtocol

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/mcp", tags=["mcp"])

# Global protocol handler (set by initialization)
_protocol: Optional[MCPProtocol] = None


def set_protocol(protocol: MCPProtocol):
    """Set the MCP protocol handler.
    
    Args:
        protocol: Initialized MCP protocol handler
    """
    global _protocol
    _protocol = protocol
    logger.info("MCP API routes connected to protocol handler")


def get_protocol() -> MCPProtocol:
    """Get the MCP protocol handler.
    
    Returns:
        MCP protocol handler
        
    Raises:
        HTTPException: If protocol not initialized
    """
    if _protocol is None:
        raise HTTPException(
            status_code=503,
            detail="MCP protocol not initialized"
        )
    return _protocol


@router.post("/request", response_model=MCPResponse)
async def mcp_endpoint(request: MCPRequest) -> MCPResponse:
    """MCP protocol endpoint.
    
    Single endpoint for all MCP operations using JSON-RPC style method routing.
    
    Supported methods:
    - workflow.execute: Execute a workflow
    - workflow.status: Get workflow status
    - workflow.checkpoint.list: List checkpoints
    - workflow.checkpoint.restore: Restore from checkpoint
    - agent.invoke: Invoke agent directly
    - agent.list: List all agents
    - realtime.subscribe: Subscribe to real-time updates
    
    Args:
        request: MCP request with method and params
        
    Returns:
        MCP response with result or error
        
    Example:
        POST /api/mcp
        {
            "method": "workflow.execute",
            "params": {
                "workflow_id": "fast-draft",
                "inputs": {"topic": "AI trends"}
            },
            "id": "req_1"
        }
        
    Response:
        {
            "result": {
                "job_id": "job_20250111_120000_001",
                "status": "running",
                ...
            },
            "id": "req_1"
        }
    """
    logger.info(f"MCP request: method={request.method}, id={request.id}")
    
    try:
        # Get protocol handler
        protocol = get_protocol()
        
        # Handle request
        response = await protocol.handle_request(request)
        
        # Log response
        if response.error:
            logger.error(f"MCP error: {response.error}")
        else:
            logger.info(f"MCP success: method={request.method}")
        
        return response
        
    except HTTPException as e:
        # Protocol not initialized - return proper MCP error
        return MCPResponse(
            error={
                "code": -32603,
                "message": f"Service unavailable: {e.detail}"
            },
            id=request.id
        )
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error in MCP endpoint: {e}", exc_info=True)
        return MCPResponse(
            error={
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            id=request.id
        )


@router.get("/methods")
async def list_mcp_methods():
    """List all available MCP methods.
    
    Returns:
        List of supported MCP methods with descriptions
    """
    return {
        "methods": [
            {
                "name": "workflow.execute",
                "description": "Execute a workflow",
                "params": {
                    "workflow_id": "string (required)",
                    "inputs": "object (required)",
                    "checkpoint_enabled": "boolean (optional)"
                }
            },
            {
                "name": "workflow.status",
                "description": "Get workflow execution status",
                "params": {
                    "job_id": "string (required)"
                }
            },
            {
                "name": "workflow.checkpoint.list",
                "description": "List available checkpoints",
                "params": {
                    "job_id": "string (required)"
                }
            },
            {
                "name": "workflow.checkpoint.restore",
                "description": "Restore workflow from checkpoint",
                "params": {
                    "job_id": "string (required)",
                    "checkpoint_id": "string (required)"
                }
            },
            {
                "name": "agent.invoke",
                "description": "Invoke an agent directly",
                "params": {
                    "agent_id": "string (required)",
                    "input": "object (required)",
                    "context": "object (optional)"
                }
            },
            {
                "name": "agent.list",
                "description": "List all available agents",
                "params": {
                    "category": "string (optional)"
                }
            },
            {
                "name": "realtime.subscribe",
                "description": "Subscribe to real-time updates",
                "params": {
                    "job_id": "string (required)",
                    "event_types": "array (optional)"
                }
            }
        ]
    }


@router.get("/status")
async def mcp_status():
    """Check MCP API status.
    
    Returns:
        Status information
    """
    try:
        protocol = get_protocol()
        return {
            "status": "ready",
            "protocol_initialized": True,
            "executor_connected": protocol.executor is not None,
            "job_engine_connected": protocol.job_engine is not None,
            "agent_registry_connected": protocol.agent_registry is not None
        }
    except HTTPException:
        return {
            "status": "not_ready",
            "protocol_initialized": False,
            "message": "MCP protocol not initialized"
        }
# DOCGEN:LLM-FIRST@v4


@router.get("/config/agents")
async def get_agents_config():
    """Get agents configuration.
    
    Returns:
        Agents configuration
    """
    try:
        import yaml
        from pathlib import Path
        
        agents_file = Path("config/agents.yaml")
        if not agents_file.exists():
            return {"agents": {}}
        
        with open(agents_file, 'r') as f:
            config = yaml.safe_load(f)
        
        return {
            "agents": config.get("agents", {})
        }
    except Exception as e:
        logger.error(f"Error getting agents config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agents config: {str(e)}"
        )


@router.get("/config/workflows")
async def get_workflows_config():
    """Get workflows configuration.
    
    Returns:
        Workflows configuration
    """
    try:
        import yaml
        from pathlib import Path
        
        workflows_file = Path("templates/workflows.yaml")
        if not workflows_file.exists():
            return {"workflows": {}}
        
        with open(workflows_file, 'r') as f:
            config = yaml.safe_load(f)
        
        return {
            "workflows": config.get("workflows", {})
        }
    except Exception as e:
        logger.error(f"Error getting workflows config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workflows config: {str(e)}"
        )


@router.get("/traffic")
async def get_mcp_traffic(
    limit: int = 100,
    offset: int = 0,
    agent_id: Optional[str] = None,
    message_type: Optional[str] = None,
    status: Optional[str] = None
):
    """Get MCP traffic with filtering.
    
    Args:
        limit: Maximum number of messages to return
        offset: Number of messages to skip
        agent_id: Filter by agent ID
        message_type: Filter by message type
        status: Filter by status
        
    Returns:
        List of MCP messages
    """
    try:
        from src.mcp.traffic_logger import get_traffic_logger
        from dataclasses import asdict
        
        traffic_logger = get_traffic_logger()
        messages = traffic_logger.get_traffic(
            limit=limit,
            offset=offset,
            agent_id=agent_id,
            message_type=message_type,
            status=status
        )
        
        return {
            "messages": [asdict(m) for m in messages],
            "total": len(messages),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error getting MCP traffic: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get MCP traffic: {str(e)}"
        )


@router.get("/metrics")
async def get_mcp_metrics():
    """Get MCP traffic metrics.
    
    Returns:
        Traffic metrics including message counts, latencies, and error rates
    """
    try:
        from src.mcp.traffic_logger import get_traffic_logger
        
        traffic_logger = get_traffic_logger()
        metrics = traffic_logger.get_metrics()
        
        return metrics
    except Exception as e:
        logger.error(f"Error getting MCP metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get MCP metrics: {str(e)}"
        )


@router.get("/message/{message_id}")
async def get_mcp_message(message_id: str):
    """Get specific MCP message details.
    
    Args:
        message_id: Message identifier
        
    Returns:
        Message details
    """
    try:
        from src.mcp.traffic_logger import get_traffic_logger
        from dataclasses import asdict
        
        traffic_logger = get_traffic_logger()
        message = traffic_logger.get_message(message_id)
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return asdict(message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting MCP message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get MCP message: {str(e)}"
        )


@router.get("/export")
async def export_mcp_traffic(
    format: str = 'json',
    agent_id: Optional[str] = None,
    message_type: Optional[str] = None,
    status: Optional[str] = None
):
    """Export MCP traffic to JSON or CSV.
    
    Args:
        format: Export format ('json' or 'csv')
        agent_id: Filter by agent ID
        message_type: Filter by message type
        status: Filter by status
        
    Returns:
        Exported data file
    """
    try:
        from fastapi.responses import Response
        from src.mcp.traffic_logger import get_traffic_logger
        
        traffic_logger = get_traffic_logger()
        
        filters = {}
        if agent_id:
            filters['agent_id'] = agent_id
        if message_type:
            filters['message_type'] = message_type
        if status:
            filters['status'] = status
        
        data = traffic_logger.export_traffic(format=format, **filters)
        
        media_type = 'application/json' if format == 'json' else 'text/csv'
        filename = f'mcp_traffic.{format}'
        
        return Response(
            content=data,
            media_type=media_type,
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
    except Exception as e:
        logger.error(f"Error exporting MCP traffic: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export MCP traffic: {str(e)}"
        )


@router.post("/cleanup")
async def cleanup_old_traffic():
    """Cleanup old MCP traffic based on retention policy.
    
    Returns:
        Number of records deleted
    """
    try:
        from src.mcp.traffic_logger import get_traffic_logger
        
        traffic_logger = get_traffic_logger()
        deleted = traffic_logger.cleanup_old()
        
        return {
            "deleted": deleted,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error cleaning up MCP traffic: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup MCP traffic: {str(e)}"
        )
