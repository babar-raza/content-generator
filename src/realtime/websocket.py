"""WebSocket Manager - Real-time control plane for UCOP."""

import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Real-time event types (RT-P2)."""
    RUN_START = "RUN.START"
    NODE_START = "NODE.START"
    NODE_STDOUT = "NODE.STDOUT"
    NODE_CHECKPOINT = "NODE.CHECKPOINT"
    NODE_OUTPUT = "NODE.OUTPUT"
    NODE_ERROR = "NODE.ERROR"
    RUN_PAUSED = "RUN.PAUSED"
    RUN_RESUMED = "RUN.RESUMED"
    RUN_FINISHED = "RUN.FINISHED"
    CACHE_HIT = "CACHE.HIT"
    CACHE_MISS = "CACHE.MISS"
    METRICS_UPDATE = "METRICS.UPDATE"


class CommandType(str, Enum):
    """Control commands (RT-P3)."""
    PAUSE = "CONTROL.PAUSE"
    RESUME = "CONTROL.RESUME"
    STEP_INTO = "CONTROL.STEP_INTO"
    STEP_OVER = "CONTROL.STEP_OVER"
    STEP_OUT = "CONTROL.STEP_OUT"
    RETRY_NODE = "CONTROL.RETRY_NODE"
    CANCEL = "CONTROL.CANCEL"
    INSERT_NODE = "GRAPH.INSERT_NODE"
    SWAP_NODE = "GRAPH.SWAP_NODE"
    REROUTE_EDGE = "GRAPH.REROUTE_EDGE"
    SET_PARAMS = "PARAMS.SET"
    SWITCH_MODEL = "MODEL.SWITCH"
    DUMP_STATE = "CONTROL.DUMP_STATE"
    PREVIEW_OUTPUT = "CONTROL.PREVIEW_OUTPUT"


class WebSocketManager:
    """Manages WebSocket connections for real-time job monitoring."""
    
    def __init__(self):
        self.connections: Dict[str, Set[Any]] = {}  # job_id -> set of websockets
        self.command_handlers: Dict[CommandType, callable] = {}
        
    async def connect(self, websocket: Any, job_id: str):
        """Register a WebSocket connection for a job."""
        if job_id not in self.connections:
            self.connections[job_id] = set()
        self.connections[job_id].add(websocket)
        logger.info(f"WebSocket connected for job {job_id}")
        
    async def disconnect(self, websocket: Any, job_id: str):
        """Unregister a WebSocket connection."""
        if job_id in self.connections:
            self.connections[job_id].discard(websocket)
            if not self.connections[job_id]:
                del self.connections[job_id]
        logger.info(f"WebSocket disconnected for job {job_id}")
    
    async def broadcast(self, job_id: str, event_type: EventType, data: Dict[str, Any]):
        """Broadcast event to all connections for a job."""
        if job_id not in self.connections:
            return
        
        message = {
            "type": event_type.value,
            "timestamp": datetime.now().isoformat(),
            "job_id": job_id,
            "data": data
        }
        
        dead_connections = set()
        for ws in self.connections[job_id]:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to WebSocket: {e}")
                dead_connections.add(ws)
        
        # Clean up dead connections
        for ws in dead_connections:
            await self.disconnect(ws, job_id)
    
    async def handle_command(self, job_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a control command from client."""
        try:
            cmd_type = CommandType(command.get("type"))
            handler = self.command_handlers.get(cmd_type)
            
            if not handler:
                return {"status": "error", "message": f"Unknown command: {cmd_type}"}
            
            result = await handler(job_id, command.get("params", {}))
            
            # Broadcast command result
            await self.broadcast(job_id, EventType.NODE_STDOUT, {
                "message": f"Command {cmd_type.value} executed",
                "result": result
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Command handling error: {e}")
            return {"status": "error", "message": str(e)}
    
    def register_handler(self, command_type: CommandType, handler: callable):
        """Register a handler for a command type."""
        self.command_handlers[command_type] = handler


# Global WebSocket manager
_ws_manager = None


def get_ws_manager() -> WebSocketManager:
    """Get the global WebSocket manager."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


class EventEmitter:
    """Helper for agents to emit events."""
    
    def __init__(self, job_id: str, node_id: str):
        self.job_id = job_id
        self.node_id = node_id
        self.ws_manager = get_ws_manager()
    
    async def emit_start(self):
        """Emit node start event."""
        await self.ws_manager.broadcast(
            self.job_id,
            EventType.NODE_START,
            {"node_id": self.node_id, "timestamp": datetime.now().isoformat()}
        )
    
    async def emit_checkpoint(self, checkpoint: str):
        """Emit checkpoint reached."""
        await self.ws_manager.broadcast(
            self.job_id,
            EventType.NODE_CHECKPOINT,
            {
                "node_id": self.node_id,
                "checkpoint": checkpoint,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    async def emit_output(self, output: Dict[str, Any]):
        """Emit node output."""
        await self.ws_manager.broadcast(
            self.job_id,
            EventType.NODE_OUTPUT,
            {
                "node_id": self.node_id,
                "output": output,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    async def emit_error(self, error: str):
        """Emit node error."""
        await self.ws_manager.broadcast(
            self.job_id,
            EventType.NODE_ERROR,
            {
                "node_id": self.node_id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    async def emit_log(self, message: str):
        """Emit stdout/log message."""
        await self.ws_manager.broadcast(
            self.job_id,
            EventType.NODE_STDOUT,
            {
                "node_id": self.node_id,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        )


# FastAPI WebSocket endpoint (add to main or ops_console)
"""
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/mesh")
async def websocket_endpoint(websocket: WebSocket, job: str):
    await websocket.accept()
    ws_manager = get_ws_manager()
    await ws_manager.connect(websocket, job)
    
    try:
        while True:
            data = await websocket.receive_json()
            result = await ws_manager.handle_command(job, data)
            await websocket.send_json(result)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, job)
"""
