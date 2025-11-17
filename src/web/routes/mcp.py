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
