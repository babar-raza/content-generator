"""Debug Controller - Core debug session management.

This module implements the DebugController (VIS-001), which:
- Manages debug sessions (single user mode)
- Subscribes to MCP tracer events
- Broadcasts state changes via WebSocket
- Coordinates with breakpoint manager, snapshot store, and execution controller

Thread Safety:
    All methods are thread-safe for concurrent access.

Author: Migration Implementation Agent
Created: 2025-12-18
Taskcard: VIS-001
"""

import logging
import threading
from typing import Callable, Optional

from fastapi import WebSocket

from src.mcp.tracer import MCPTrace, MCPTracer, get_global_tracer

from .models import DebugSession, ExecutionState, ExecutionStateStatus

logger = logging.getLogger(__name__)


class DebugController:
    """Core debug controller for managing debug sessions.

    The DebugController is the central coordinator for all debug operations.
    It provides:
    - Session lifecycle management (create, end, get)
    - MCP tracer event subscription
    - WebSocket state broadcasting
    - Single-user session enforcement

    Example:
        >>> controller = DebugController()
        >>> session = controller.create_session("job-123")
        >>> controller.subscribe_events(session.id, websocket)
        >>> # ... debug operations ...
        >>> controller.end_session(session.id)

    Thread Safety:
        All public methods are thread-safe and can be called concurrently.
    """

    def __init__(self, mcp_tracer: Optional[MCPTracer] = None):
        """Initialize debug controller.

        Args:
            mcp_tracer: MCP tracer for event subscription (defaults to global)
        """
        self._mcp_tracer = mcp_tracer or get_global_tracer()
        self._active_session: Optional[DebugSession] = None
        self._websockets: dict[str, WebSocket] = {}
        self._lock = threading.RLock()
        self._subscription_id: Optional[str] = None

        logger.info("DebugController initialized")

    def create_session(self, job_id: str) -> DebugSession:
        """Create a new debug session for a job.

        Only one active session is allowed at a time (single user mode).
        If a session already exists, raises ValueError.

        Args:
            job_id: Job identifier to debug

        Returns:
            Created DebugSession

        Raises:
            ValueError: If a session already exists

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = DebugController()
            >>> session = controller.create_session("job-123")
            >>> assert session.job_id == "job-123"
        """
        with self._lock:
            if self._active_session is not None:
                raise ValueError(
                    f"Debug session already active for job {self._active_session.job_id}. "
                    "Only one session allowed at a time (single user mode)."
                )

            # Create initial execution state
            state = ExecutionState(
                job_id=job_id,
                status=ExecutionStateStatus.RUNNING,
                current_agent=None,
                current_step=0,
                total_steps=0,
            )

            # Create debug session
            session = DebugSession(
                job_id=job_id,
                state=state,
                websocket_connected=False,
            )

            self._active_session = session

            # Subscribe to MCP tracer events
            self._subscription_id = self._mcp_tracer.subscribe(self._on_trace_event)

            logger.info(
                f"Created debug session {session.id} for job {job_id} "
                f"(tracer subscription: {self._subscription_id})"
            )

            return session

    def end_session(self, session_id: str) -> None:
        """End an active debug session.

        Args:
            session_id: Session identifier to end

        Raises:
            ValueError: If session_id doesn't match active session

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = DebugController()
            >>> session = controller.create_session("job-123")
            >>> controller.end_session(session.id)
            >>> assert controller.get_session(session.id) is None
        """
        with self._lock:
            if self._active_session is None:
                logger.warning(f"No active session to end (requested: {session_id})")
                return

            if self._active_session.id != session_id:
                raise ValueError(
                    f"Session ID mismatch: active={self._active_session.id}, "
                    f"requested={session_id}"
                )

            # Unsubscribe from MCP tracer
            if self._subscription_id:
                self._mcp_tracer.unsubscribe(self._subscription_id)
                self._subscription_id = None

            # Close all websockets
            for ws in list(self._websockets.values()):
                try:
                    # WebSocket will be closed by the connection manager
                    pass
                except Exception as e:
                    logger.error(f"Error closing WebSocket: {e}")

            self._websockets.clear()

            logger.info(f"Ended debug session {session_id}")
            self._active_session = None

    def get_session(self, session_id: str) -> Optional[DebugSession]:
        """Get an active debug session by ID.

        Args:
            session_id: Session identifier

        Returns:
            DebugSession if found and matches session_id, None otherwise

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = DebugController()
            >>> session = controller.create_session("job-123")
            >>> retrieved = controller.get_session(session.id)
            >>> assert retrieved.id == session.id
        """
        with self._lock:
            if self._active_session and self._active_session.id == session_id:
                return self._active_session
            return None

    def get_active_session(self) -> Optional[DebugSession]:
        """Get the currently active debug session.

        Returns:
            Active DebugSession or None

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = DebugController()
            >>> assert controller.get_active_session() is None
            >>> session = controller.create_session("job-123")
            >>> assert controller.get_active_session() is not None
        """
        with self._lock:
            return self._active_session

    def subscribe_events(self, session_id: str, websocket: WebSocket) -> None:
        """Subscribe a WebSocket to debug events for a session.

        Args:
            session_id: Session identifier
            websocket: WebSocket connection to subscribe

        Raises:
            ValueError: If session not found or session_id mismatch

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = DebugController()
            >>> session = controller.create_session("job-123")
            >>> # In WebSocket endpoint:
            >>> controller.subscribe_events(session.id, websocket)
        """
        with self._lock:
            if self._active_session is None:
                raise ValueError("No active debug session")

            if self._active_session.id != session_id:
                raise ValueError(
                    f"Session ID mismatch: active={self._active_session.id}, "
                    f"requested={session_id}"
                )

            self._websockets[session_id] = websocket
            self._active_session.websocket_connected = True

            logger.info(f"WebSocket subscribed to session {session_id}")

    def unsubscribe_events(self, session_id: str) -> None:
        """Unsubscribe WebSocket from debug events.

        Args:
            session_id: Session identifier

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            if session_id in self._websockets:
                del self._websockets[session_id]

            if self._active_session and self._active_session.id == session_id:
                self._active_session.websocket_connected = False

            logger.info(f"WebSocket unsubscribed from session {session_id}")

    async def broadcast_state(self, session_id: str, state: ExecutionState) -> None:
        """Broadcast execution state change to subscribed WebSockets.

        Args:
            session_id: Session identifier
            state: Updated execution state

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = DebugController()
            >>> session = controller.create_session("job-123")
            >>> new_state = ExecutionState(
            ...     job_id="job-123",
            ...     status=ExecutionStateStatus.PAUSED,
            ...     current_agent="topic_identification",
            ...     current_step=1
            ... )
            >>> await controller.broadcast_state(session.id, new_state)
        """
        with self._lock:
            if self._active_session and self._active_session.id == session_id:
                self._active_session.state = state

            ws = self._websockets.get(session_id)

        if ws:
            try:
                await ws.send_json(
                    {
                        "event": "execution_state",
                        "data": state.dict(),
                    }
                )
                logger.debug(f"Broadcasted state to session {session_id}")
            except Exception as e:
                logger.error(f"Error broadcasting state: {e}")

    async def broadcast_event(
        self, session_id: str, event_type: str, data: dict
    ) -> None:
        """Broadcast a generic debug event to subscribed WebSockets.

        Args:
            session_id: Session identifier
            event_type: Type of event (e.g., "breakpoint_hit", "snapshot_created")
            data: Event data

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> await controller.broadcast_event(
            ...     session.id,
            ...     "breakpoint_hit",
            ...     {"breakpoint_id": "bp-123", "agent": "topic_identification"}
            ... )
        """
        with self._lock:
            ws = self._websockets.get(session_id)

        if ws:
            try:
                await ws.send_json(
                    {
                        "event": event_type,
                        "data": data,
                    }
                )
                logger.debug(f"Broadcasted {event_type} to session {session_id}")
            except Exception as e:
                logger.error(f"Error broadcasting event {event_type}: {e}")

    def _on_trace_event(self, trace: MCPTrace) -> None:
        """Handle MCP trace events.

        This is called by the MCP tracer when a trace completes.
        We extract debug-relevant events and broadcast them.

        Args:
            trace: Completed MCP trace

        Thread Safety:
            This method is called from the tracer thread.
        """
        if not trace.response or not self._active_session:
            return

        # Extract agent execution events
        if trace.method.startswith("agent."):
            # This would be async in real implementation, but for now we log
            logger.debug(
                f"Agent execution trace: {trace.method} "
                f"({trace.duration_ms:.2f}ms, status={trace.status})"
            )

            # In a full implementation, we would:
            # 1. Parse the trace to extract agent name, inputs, outputs
            # 2. Check for breakpoints
            # 3. Create snapshots
            # 4. Broadcast events via WebSocket

    @property
    def mcp_tracer(self) -> MCPTracer:
        """Get the MCP tracer instance.

        Returns:
            MCPTracer instance
        """
        return self._mcp_tracer

    @property
    def active_session(self) -> Optional[DebugSession]:
        """Get the active debug session.

        Returns:
            Active DebugSession or None
        """
        with self._lock:
            return self._active_session


# Global debug controller instance
_global_controller: Optional[DebugController] = None
_global_controller_lock = threading.Lock()


def get_global_debug_controller() -> DebugController:
    """Get or create the global debug controller singleton.

    Returns:
        Global DebugController instance

    Thread Safety:
        This function is thread-safe.

    Example:
        >>> controller = get_global_debug_controller()
        >>> session = controller.create_session("job-123")
    """
    global _global_controller

    if _global_controller is None:
        with _global_controller_lock:
            if _global_controller is None:
                _global_controller = DebugController()
                logger.info("Created global DebugController instance")

    return _global_controller


def reset_global_debug_controller() -> None:
    """Reset the global debug controller singleton.

    This is primarily for testing.

    Thread Safety:
        This function is thread-safe.
    """
    global _global_controller

    with _global_controller_lock:
        if _global_controller and _global_controller.active_session:
            _global_controller.end_session(_global_controller.active_session.id)
        _global_controller = None
        logger.info("Reset global DebugController instance")


__all__ = [
    "DebugController",
    "get_global_debug_controller",
    "reset_global_debug_controller",
]
