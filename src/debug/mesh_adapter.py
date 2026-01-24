"""Mesh Debug Adapter - Bridge mesh orchestration with debug visualization.

MESH-009: Integrates mesh execution with the Visual Orchestration debug system.

This adapter provides:
- Bid visualization (show bids on debug canvas)
- Mesh event timeline extension
- Integration with DebugController for state broadcasting
- Real-time mesh decision tracking

The adapter listens to mesh events (capability requests, bids, selections, executions)
and translates them into debug events that can be visualized in the React Flow canvas.

Thread Safety:
    All public methods are thread-safe using RLock.

Author: Migration Implementation Agent
Created: 2025-12-19
Updated: 2026-01-01 (TASK-014: Added WebSocket emission)
Taskcard: MESH-009

Example:
    >>> from src.debug.mesh_adapter import MeshDebugAdapter
    >>> from src.debug.controller import get_global_debug_controller
    >>>
    >>> controller = get_global_debug_controller()
    >>> adapter = MeshDebugAdapter(controller)
    >>>
    >>> # In mesh workflow:
    >>> adapter.on_capability_request("workflow-123", "keyword_extraction", {...})
    >>> adapter.on_bid_received("workflow-123", bid)
    >>> adapter.on_agent_selected("workflow-123", "keyword_extraction_agent_1")
"""

import asyncio
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional

from .controller import DebugController, get_global_debug_controller
from .models import ExecutionState, ExecutionStateStatus, SnapshotType, StateSnapshot

logger = logging.getLogger(__name__)


@dataclass
class BidVisualization:
    """Visualization data for a bid in the debug UI.

    Attributes:
        bid_id: Unique bid identifier
        agent_id: Agent that submitted the bid
        capability: Capability being bid on
        score: Bid score (0.0 to 1.0)
        confidence: Agent's confidence in executing this capability
        estimated_time: Estimated execution time in seconds
        current_load: Agent's current load
        health_score: Agent's health score
        components: Score component breakdown
        timestamp: When bid was submitted
    """

    bid_id: str
    agent_id: str
    capability: str
    score: float
    confidence: float
    estimated_time: float
    current_load: int
    health_score: float
    components: dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "bid_id": self.bid_id,
            "agent_id": self.agent_id,
            "capability": self.capability,
            "score": self.score,
            "confidence": self.confidence,
            "estimated_time": self.estimated_time,
            "current_load": self.current_load,
            "health_score": self.health_score,
            "components": self.components,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class MeshTimelineEvent:
    """Timeline event for mesh orchestration.

    Attributes:
        event_id: Unique event identifier
        event_type: Type of event (capability_request, bid_received, agent_selected, etc.)
        workflow_id: Workflow this event belongs to
        capability: Capability being negotiated (if applicable)
        agent_id: Agent involved (if applicable)
        data: Event-specific data
        timestamp: When event occurred
    """

    event_id: str
    event_type: str
    workflow_id: str
    capability: Optional[str] = None
    agent_id: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "workflow_id": self.workflow_id,
            "capability": self.capability,
            "agent_id": self.agent_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class MeshDebugAdapter:
    """Bridge between mesh orchestration and debug visualization.

    The adapter subscribes to mesh events and translates them into debug events
    that can be visualized in the React Flow canvas. It provides:

    1. Bid Visualization:
       - Captures all bids for a capability request
       - Shows bid scores and components
       - Highlights winning bid

    2. Timeline Extension:
       - Adds mesh-specific events to debug timeline
       - Tracks capability negotiations
       - Shows agent selection decisions

    3. State Broadcasting:
       - Broadcasts mesh state changes via WebSocket
       - Updates execution state with mesh-specific data
       - Provides real-time mesh decision tracking

    Thread Safety:
        All public methods are thread-safe using RLock.

    Example:
        >>> adapter = MeshDebugAdapter()
        >>> session = adapter.debug_controller.create_session("job-123")
        >>> adapter.on_capability_request("job-123", "keyword_extraction", {...})
        >>> # ... bids arrive ...
        >>> adapter.on_bid_received("job-123", bid)
        >>> adapter.on_agent_selected("job-123", "keyword_extraction_agent_1")
    """

    def __init__(self, debug_controller: Optional[DebugController] = None):
        """Initialize mesh debug adapter.

        Args:
            debug_controller: DebugController instance (defaults to global)
        """
        self.debug_controller = debug_controller or get_global_debug_controller()

        # Storage for mesh-specific data
        self._workflow_bids: dict[str, list[BidVisualization]] = {}
        self._timeline_events: dict[str, list[MeshTimelineEvent]] = {}
        self._lock = threading.RLock()

        logger.info("MeshDebugAdapter initialized")

    def on_capability_request(
        self,
        workflow_id: str,
        capability: str,
        input_data: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Handle capability request event.

        Called when a mesh workflow requests a capability from agents.

        Args:
            workflow_id: Workflow/job identifier
            capability: Capability being requested
            input_data: Input data for the capability
            context: Optional execution context

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            # Clear previous bids for this workflow
            self._workflow_bids[workflow_id] = []

            # Create timeline event
            event = MeshTimelineEvent(
                event_id=str(uuid.uuid4()),
                event_type="capability_request",
                workflow_id=workflow_id,
                capability=capability,
                data={
                    "input_data_summary": self._summarize_data(input_data),
                    "context": context or {},
                },
            )

            # Store timeline event
            if workflow_id not in self._timeline_events:
                self._timeline_events[workflow_id] = []
            self._timeline_events[workflow_id].append(event)

            logger.debug(
                f"Capability request: workflow={workflow_id}, capability={capability}"
            )

        # Broadcast event asynchronously
        self._broadcast_timeline_event(workflow_id, event)

    def on_bid_received(
        self,
        workflow_id: str,
        bid: Any,  # Bid object from contracts
    ) -> None:
        """Handle bid received event.

        Called when an agent submits a bid for a capability.

        Args:
            workflow_id: Workflow/job identifier
            bid: Bid object from src.core.contracts

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            # Convert bid to visualization format
            bid_viz = BidVisualization(
                bid_id=getattr(bid, "bid_id", str(uuid.uuid4())),
                agent_id=bid.agent_id,
                capability=bid.capability,
                score=getattr(bid, "score", bid.confidence),
                confidence=bid.confidence,
                estimated_time=bid.estimated_time,
                current_load=bid.current_load,
                health_score=bid.health_score,
                components=bid.additional_info.get("score_components", {}),
            )

            # Store bid
            if workflow_id not in self._workflow_bids:
                self._workflow_bids[workflow_id] = []
            self._workflow_bids[workflow_id].append(bid_viz)

            # Create timeline event
            event = MeshTimelineEvent(
                event_id=str(uuid.uuid4()),
                event_type="bid_received",
                workflow_id=workflow_id,
                capability=bid.capability,
                agent_id=bid.agent_id,
                data=bid_viz.to_dict(),
            )

            # Store timeline event
            if workflow_id not in self._timeline_events:
                self._timeline_events[workflow_id] = []
            self._timeline_events[workflow_id].append(event)

            logger.debug(
                f"Bid received: workflow={workflow_id}, agent={bid.agent_id}, "
                f"capability={bid.capability}, score={bid_viz.score:.3f}"
            )

        # Broadcast event asynchronously
        self._broadcast_timeline_event(workflow_id, event)

    def on_agent_selected(
        self,
        workflow_id: str,
        agent_id: str,
        capability: str,
        winning_bid: Optional[Any] = None,
    ) -> None:
        """Handle agent selected event.

        Called when an agent is selected to execute a capability.

        Args:
            workflow_id: Workflow/job identifier
            agent_id: Selected agent identifier
            capability: Capability being executed
            winning_bid: Winning bid (if available)

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            # Find all bids for this capability
            all_bids = self._workflow_bids.get(workflow_id, [])
            capability_bids = [b for b in all_bids if b.capability == capability]

            # Create timeline event
            event = MeshTimelineEvent(
                event_id=str(uuid.uuid4()),
                event_type="agent_selected",
                workflow_id=workflow_id,
                capability=capability,
                agent_id=agent_id,
                data={
                    "winning_agent": agent_id,
                    "bids_received": len(capability_bids),
                    "all_bids": [b.to_dict() for b in capability_bids],
                },
            )

            # Store timeline event
            if workflow_id not in self._timeline_events:
                self._timeline_events[workflow_id] = []
            self._timeline_events[workflow_id].append(event)

            logger.info(
                f"Agent selected: workflow={workflow_id}, agent={agent_id}, "
                f"capability={capability}, bids={len(capability_bids)}"
            )

        # Broadcast event asynchronously
        self._broadcast_timeline_event(workflow_id, event)

    def on_agent_execution_start(
        self,
        workflow_id: str,
        agent_id: str,
        capability: str,
        inputs: dict[str, Any],
    ) -> None:
        """Handle agent execution start event.

        Called when an agent begins executing.

        Args:
            workflow_id: Workflow/job identifier
            agent_id: Agent identifier
            capability: Capability being executed
            inputs: Agent inputs

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            # Create snapshot
            snapshot = StateSnapshot(
                job_id=workflow_id,
                step_index=len(self._timeline_events.get(workflow_id, [])),
                agent_name=agent_id,
                snapshot_type=SnapshotType.AGENT_START,
                inputs=inputs,
                context={"capability": capability},
            )

            # Create timeline event
            event = MeshTimelineEvent(
                event_id=str(uuid.uuid4()),
                event_type="agent_execution_start",
                workflow_id=workflow_id,
                capability=capability,
                agent_id=agent_id,
                data={
                    "inputs_summary": self._summarize_data(inputs),
                    "snapshot_id": snapshot.id,
                },
            )

            # Store timeline event
            if workflow_id not in self._timeline_events:
                self._timeline_events[workflow_id] = []
            self._timeline_events[workflow_id].append(event)

            logger.debug(
                f"Agent execution start: workflow={workflow_id}, agent={agent_id}"
            )

        # Broadcast event asynchronously
        self._broadcast_timeline_event(workflow_id, event)
        self._broadcast_snapshot(workflow_id, snapshot)

    def on_agent_execution_complete(
        self,
        workflow_id: str,
        agent_id: str,
        capability: str,
        outputs: dict[str, Any],
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Handle agent execution complete event.

        Called when an agent completes executing.

        Args:
            workflow_id: Workflow/job identifier
            agent_id: Agent identifier
            capability: Capability that was executed
            outputs: Agent outputs
            duration_ms: Execution duration in milliseconds
            success: Whether execution succeeded
            error: Error message if execution failed

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            # Create snapshot
            snapshot = StateSnapshot(
                job_id=workflow_id,
                step_index=len(self._timeline_events.get(workflow_id, [])),
                agent_name=agent_id,
                snapshot_type=SnapshotType.AGENT_END,
                inputs={},  # Already captured in start snapshot
                outputs=outputs,
                context={"capability": capability, "success": success, "error": error},
                duration_ms=duration_ms,
            )

            # Create timeline event
            event = MeshTimelineEvent(
                event_id=str(uuid.uuid4()),
                event_type="agent_execution_complete",
                workflow_id=workflow_id,
                capability=capability,
                agent_id=agent_id,
                data={
                    "outputs_summary": self._summarize_data(outputs),
                    "duration_ms": duration_ms,
                    "success": success,
                    "error": error,
                    "snapshot_id": snapshot.id,
                },
            )

            # Store timeline event
            if workflow_id not in self._timeline_events:
                self._timeline_events[workflow_id] = []
            self._timeline_events[workflow_id].append(event)

            logger.debug(
                f"Agent execution complete: workflow={workflow_id}, agent={agent_id}, "
                f"duration={duration_ms:.1f}ms, success={success}"
            )

        # Broadcast event asynchronously
        self._broadcast_timeline_event(workflow_id, event)
        self._broadcast_snapshot(workflow_id, snapshot)

        # Update execution state
        self._update_execution_state(
            workflow_id=workflow_id,
            agent=agent_id,
            status=ExecutionStateStatus.RUNNING if success else ExecutionStateStatus.ERROR,
            error_message=error,
        )

    def on_workflow_paused(
        self,
        workflow_id: str,
        reason: str,
    ) -> None:
        """Handle workflow paused event.

        Called when a mesh workflow is paused (e.g., for human approval).

        Args:
            workflow_id: Workflow/job identifier
            reason: Reason for pause

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            # Create timeline event
            event = MeshTimelineEvent(
                event_id=str(uuid.uuid4()),
                event_type="workflow_paused",
                workflow_id=workflow_id,
                data={"reason": reason},
            )

            # Store timeline event
            if workflow_id not in self._timeline_events:
                self._timeline_events[workflow_id] = []
            self._timeline_events[workflow_id].append(event)

            logger.info(f"Workflow paused: workflow={workflow_id}, reason={reason}")

        # Broadcast event asynchronously
        self._broadcast_timeline_event(workflow_id, event)

        # Update execution state
        self._update_execution_state(
            workflow_id=workflow_id,
            status=ExecutionStateStatus.PAUSED,
        )

    def on_workflow_resumed(
        self,
        workflow_id: str,
    ) -> None:
        """Handle workflow resumed event.

        Called when a paused mesh workflow is resumed.

        Args:
            workflow_id: Workflow/job identifier

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            # Create timeline event
            event = MeshTimelineEvent(
                event_id=str(uuid.uuid4()),
                event_type="workflow_resumed",
                workflow_id=workflow_id,
            )

            # Store timeline event
            if workflow_id not in self._timeline_events:
                self._timeline_events[workflow_id] = []
            self._timeline_events[workflow_id].append(event)

            logger.info(f"Workflow resumed: workflow={workflow_id}")

        # Broadcast event asynchronously
        self._broadcast_timeline_event(workflow_id, event)

        # Update execution state
        self._update_execution_state(
            workflow_id=workflow_id,
            status=ExecutionStateStatus.RUNNING,
        )

    def get_bids(self, workflow_id: str, capability: Optional[str] = None) -> list[BidVisualization]:
        """Get bids for a workflow.

        Args:
            workflow_id: Workflow/job identifier
            capability: Optional capability filter

        Returns:
            List of BidVisualization objects

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            all_bids = self._workflow_bids.get(workflow_id, [])

            if capability:
                return [b for b in all_bids if b.capability == capability]

            return all_bids.copy()

    def get_timeline_events(self, workflow_id: str) -> list[MeshTimelineEvent]:
        """Get timeline events for a workflow.

        Args:
            workflow_id: Workflow/job identifier

        Returns:
            List of MeshTimelineEvent objects

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            return self._timeline_events.get(workflow_id, []).copy()

    def clear_workflow_data(self, workflow_id: str) -> None:
        """Clear all data for a workflow.

        Args:
            workflow_id: Workflow/job identifier

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            self._workflow_bids.pop(workflow_id, None)
            self._timeline_events.pop(workflow_id, None)

            logger.debug(f"Cleared mesh debug data for workflow: {workflow_id}")

    def _summarize_data(self, data: dict[str, Any], max_length: int = 200) -> str:
        """Create a summary of data for display.

        Args:
            data: Data to summarize
            max_length: Maximum summary length

        Returns:
            Summary string
        """
        summary = str(data)
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        return summary

    def _broadcast_timeline_event(self, workflow_id: str, event: MeshTimelineEvent) -> None:
        """Broadcast a timeline event via WebSocket.

        Args:
            workflow_id: Workflow/job identifier
            event: Timeline event to broadcast

        Note:
            Schedules async broadcast using asyncio.create_task.
            Events are emitted fire-and-forget (no delivery guarantee).

        Thread Safety:
            This method is thread-safe.
        """
        # Get active session
        session = self.debug_controller.get_active_session()
        if not session or session.job_id != workflow_id:
            return

        # Convert event to dict for serialization
        event_data = event.to_dict()

        # Schedule async broadcast
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self.debug_controller.broadcast_event(
                    session.id,
                    "mesh.timeline_event",
                    event_data
                )
            )
            logger.debug(
                f"Scheduled timeline event broadcast: {event.event_type} "
                f"for workflow {workflow_id}"
            )
        except RuntimeError:
            # No event loop running - log warning
            logger.warning(
                f"Cannot broadcast timeline event {event.event_type}: "
                f"no event loop running"
            )

    def _broadcast_snapshot(self, workflow_id: str, snapshot: StateSnapshot) -> None:
        """Broadcast a state snapshot via WebSocket.

        Args:
            workflow_id: Workflow/job identifier
            snapshot: State snapshot to broadcast

        Note:
            Schedules async broadcast using asyncio.create_task.
            Events are emitted fire-and-forget (no delivery guarantee).

        Thread Safety:
            This method is thread-safe.
        """
        # Get active session
        session = self.debug_controller.get_active_session()
        if not session or session.job_id != workflow_id:
            return

        # Convert snapshot to dict for serialization
        snapshot_data = {
            "id": snapshot.id,
            "job_id": snapshot.job_id,
            "step_index": snapshot.step_index,
            "agent_name": snapshot.agent_name,
            "snapshot_type": snapshot.snapshot_type.value,
            "timestamp": snapshot.timestamp.isoformat(),
            "inputs": snapshot.inputs,
            "outputs": snapshot.outputs,
            "context": snapshot.context,
            "duration_ms": snapshot.duration_ms,
        }

        # Schedule async broadcast
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self.debug_controller.broadcast_event(
                    session.id,
                    "mesh.snapshot_created",
                    snapshot_data
                )
            )
            logger.debug(
                f"Scheduled snapshot broadcast: {snapshot.snapshot_type} "
                f"for agent {snapshot.agent_name}"
            )
        except RuntimeError:
            # No event loop running - log warning
            logger.warning(
                f"Cannot broadcast snapshot {snapshot.id}: no event loop running"
            )

    def _update_execution_state(
        self,
        workflow_id: str,
        agent: Optional[str] = None,
        status: Optional[ExecutionStateStatus] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update execution state for a workflow.

        Args:
            workflow_id: Workflow/job identifier
            agent: Current agent (if changed)
            status: New status (if changed)
            error_message: Error message (if any)

        Note:
            Schedules async broadcast using asyncio.create_task.
            State updates are emitted fire-and-forget (no delivery guarantee).

        Thread Safety:
            This method is thread-safe.
        """
        # Get active session
        session = self.debug_controller.get_active_session()
        if not session or session.job_id != workflow_id:
            return

        # Update state
        if agent is not None:
            session.state.current_agent = agent
        if status is not None:
            session.state.status = status
        if error_message is not None:
            session.state.error_message = error_message

        # Schedule async broadcast
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self.debug_controller.broadcast_state(session.id, session.state)
            )
            logger.debug(
                f"Scheduled state broadcast for workflow {workflow_id}: "
                f"status={status}, agent={agent}"
            )
        except RuntimeError:
            # No event loop running - log warning
            logger.warning(
                f"Cannot broadcast state update for {workflow_id}: "
                f"no event loop running"
            )


# Global mesh debug adapter instance
_global_adapter: Optional[MeshDebugAdapter] = None
_global_adapter_lock = threading.Lock()


def get_global_mesh_adapter() -> MeshDebugAdapter:
    """Get or create the global mesh debug adapter singleton.

    Returns:
        Global MeshDebugAdapter instance

    Thread Safety:
        This function is thread-safe.

    Example:
        >>> adapter = get_global_mesh_adapter()
        >>> adapter.on_capability_request("job-123", "keyword_extraction", {...})
    """
    global _global_adapter

    if _global_adapter is None:
        with _global_adapter_lock:
            if _global_adapter is None:
                _global_adapter = MeshDebugAdapter()
                logger.info("Created global MeshDebugAdapter instance")

    return _global_adapter


def reset_global_mesh_adapter() -> None:
    """Reset the global mesh debug adapter singleton.

    This is primarily for testing.

    Thread Safety:
        This function is thread-safe.
    """
    global _global_adapter

    with _global_adapter_lock:
        _global_adapter = None
        logger.info("Reset global MeshDebugAdapter instance")


__all__ = [
    "BidVisualization",
    "MeshTimelineEvent",
    "MeshDebugAdapter",
    "get_global_mesh_adapter",
    "reset_global_mesh_adapter",
]
