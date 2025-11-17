"""WebSocket Handlers for Live Flow Monitoring

This module provides WebSocket connection management for real-time workflow monitoring.
Clients can connect to view live agent execution, data flow, and progress updates.
"""

import logging
import json
import asyncio
from typing import Dict, List, Set
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect

from src.core import EventBus, AgentEvent

logger = logging.getLogger(__name__)


class LiveFlowHandler:
    """Handles WebSocket connections for live flow monitoring."""
    
    def __init__(self, event_bus: EventBus = None):
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.event_bus = event_bus or EventBus()
        self._lock = asyncio.Lock()
        
        # Subscribe to execution events
        self.event_bus.subscribe("agent_started", self._on_agent_started)
        self.event_bus.subscribe("agent_completed", self._on_agent_completed)
        self.event_bus.subscribe("agent_failed", self._on_agent_failed)
        self.event_bus.subscribe("data_flow", self._on_data_flow)
        self.event_bus.subscribe("progress_update", self._on_progress_update)
        
        logger.info("LiveFlowHandler initialized")
    
    async def handle_connection(self, websocket: WebSocket, job_id: str):
        """Handle WebSocket connection for job monitoring.
        
        Args:
            websocket: WebSocket connection
            job_id: Job identifier to monitor
        """
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for job {job_id}")
        
        async with self._lock:
            if job_id not in self.connections:
                self.connections[job_id] = set()
            self.connections[job_id].add(websocket)
        
        try:
            # Send initial connection acknowledgment
            await websocket.send_json({
                "type": "connected",
                "job_id": job_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Keep connection alive with ping/pong
            while True:
                try:
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    
                    if message == "ping":
                        await websocket.send_text("pong")
                    
                except asyncio.TimeoutError:
                    # Send ping to client
                    await websocket.send_text("ping")
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for job {job_id}")
        except Exception as e:
            logger.error(f"WebSocket error for job {job_id}: {e}")
        finally:
            # Remove connection
            async with self._lock:
                if job_id in self.connections:
                    self.connections[job_id].discard(websocket)
                    if not self.connections[job_id]:
                        del self.connections[job_id]
    
    def _on_agent_started(self, event: AgentEvent):
        """Handle agent started event."""
        job_id = event.metadata.get("job_id")
        if not job_id:
            return
        
        message = {
            "type": "agent_started",
            "agent_id": event.source_agent,
            "timestamp": event.timestamp,
            "correlation_id": event.correlation_id
        }
        asyncio.create_task(self._broadcast(job_id, message))
    
    def _on_agent_completed(self, event: AgentEvent):
        """Handle agent completed event."""
        job_id = event.metadata.get("job_id")
        if not job_id:
            return
        
        message = {
            "type": "agent_completed",
            "agent_id": event.source_agent,
            "output": event.data,
            "duration": event.metadata.get("duration", 0),
            "timestamp": event.timestamp,
            "correlation_id": event.correlation_id
        }
        asyncio.create_task(self._broadcast(job_id, message))
    
    def _on_agent_failed(self, event: AgentEvent):
        """Handle agent failed event."""
        job_id = event.metadata.get("job_id")
        if not job_id:
            return
        
        message = {
            "type": "agent_failed",
            "agent_id": event.source_agent,
            "error": event.data.get("error", "Unknown error"),
            "timestamp": event.timestamp,
            "correlation_id": event.correlation_id
        }
        asyncio.create_task(self._broadcast(job_id, message))
    
    def _on_data_flow(self, event: AgentEvent):
        """Handle data flow event."""
        job_id = event.metadata.get("job_id")
        if not job_id:
            return
        
        message = {
            "type": "data_flow",
            "from_agent": event.metadata.get("from_agent"),
            "to_agent": event.metadata.get("to_agent"),
            "data_size": len(str(event.data)),
            "timestamp": event.timestamp,
            "correlation_id": event.correlation_id
        }
        asyncio.create_task(self._broadcast(job_id, message))
    
    def _on_progress_update(self, event: AgentEvent):
        """Handle progress update event."""
        job_id = event.metadata.get("job_id")
        if not job_id:
            return
        
        message = {
            "type": "progress_update",
            "progress": event.data.get("progress", 0),
            "message": event.data.get("message", ""),
            "timestamp": event.timestamp,
            "correlation_id": event.correlation_id
        }
        asyncio.create_task(self._broadcast(job_id, message))
    
    async def _broadcast(self, job_id: str, message: dict):
        """Broadcast message to all connections for a job.
        
        Args:
            job_id: Job identifier
            message: Message to broadcast
        """
        async with self._lock:
            if job_id not in self.connections:
                return
            
            connections = list(self.connections[job_id])
        
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to websocket: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected sockets
        if disconnected:
            async with self._lock:
                if job_id in self.connections:
                    for ws in disconnected:
                        self.connections[job_id].discard(ws)
                    if not self.connections[job_id]:
                        del self.connections[job_id]
    
    def get_connection_count(self, job_id: str = None) -> int:
        """Get count of active connections.
        
        Args:
            job_id: Optional job identifier to count connections for
            
        Returns:
            Connection count
        """
        if job_id:
            return len(self.connections.get(job_id, set()))
        return sum(len(conns) for conns in self.connections.values())


# Global handler instance
_live_flow_handler: LiveFlowHandler = None


def get_live_flow_handler() -> LiveFlowHandler:
    """Get or create the global live flow handler.
    
    Returns:
        LiveFlowHandler instance
    """
    global _live_flow_handler
    if _live_flow_handler is None:
        _live_flow_handler = LiveFlowHandler()
    return _live_flow_handler


def set_live_flow_handler(handler: LiveFlowHandler):
    """Set the global live flow handler.
    
    Args:
        handler: LiveFlowHandler instance
    """
    global _live_flow_handler
    _live_flow_handler = handler
