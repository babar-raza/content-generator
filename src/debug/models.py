"""Debug Data Models - Pydantic models for debug system.

This module defines all data models used by the debug backend:
- DebugSession: Active debug session
- Breakpoint: Breakpoint configuration
- StateSnapshot: Captured execution state
- ExecutionState: Current execution state
- Injection: Agent injection record

All models use Pydantic for validation and serialization.

Author: Migration Implementation Agent
Created: 2025-12-18
Taskcard: VIS-001
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class BreakpointType(str, Enum):
    """Breakpoint trigger types."""

    AGENT_BEFORE = "agent_before"
    AGENT_AFTER = "agent_after"
    LLM_BEFORE = "llm_before"
    LLM_AFTER = "llm_after"


class SnapshotType(str, Enum):
    """Snapshot capture points."""

    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    LLM_START = "llm_start"
    LLM_END = "llm_end"


class StepMode(str, Enum):
    """Execution step modes."""

    NONE = "none"  # Not stepping
    OVER = "over"  # Step over (execute one agent, pause at next)
    INTO = "into"  # Step into (pause at next LLM call)


class ExecutionStateStatus(str, Enum):
    """Execution state statuses."""

    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class Breakpoint(BaseModel):
    """Breakpoint configuration.

    Attributes:
        id: Unique breakpoint identifier
        job_id: Job this breakpoint applies to
        type: When to trigger (agent_before, agent_after, llm_before, llm_after)
        target: Agent name or "*" for all agents
        condition: Optional Python expression (safe AST-based evaluation)
        enabled: Whether breakpoint is active
        hit_count: Number of times this breakpoint has been hit
        created_at: When breakpoint was created
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    type: BreakpointType
    target: str  # Agent name or "*"
    condition: Optional[str] = None
    enabled: bool = True
    hit_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def matches(self, agent_name: str, bp_type: BreakpointType) -> bool:
        """Check if this breakpoint matches the given agent and type.

        Args:
            agent_name: Name of agent being executed
            bp_type: Type of breakpoint to check

        Returns:
            True if this breakpoint should trigger
        """
        if not self.enabled:
            return False
        if self.type != bp_type:
            return False
        if self.target != "*" and self.target != agent_name:
            return False
        return True


class StateSnapshot(BaseModel):
    """Captured execution state at a point in time.

    Attributes:
        id: Unique snapshot identifier
        job_id: Job this snapshot belongs to
        step_index: Execution step number (0, 1, 2, ...)
        agent_name: Name of agent being executed
        snapshot_type: When this snapshot was captured
        inputs: Agent inputs at this point
        outputs: Agent outputs (None if before execution)
        prompt_template: LLM prompt template (for LLM snapshots)
        prompt_rendered: Actual prompt sent to LLM
        llm_response: Raw LLM response
        context: Full execution context
        timestamp: When snapshot was captured
        duration_ms: Duration of execution (None if not yet complete)
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    step_index: int
    agent_name: str
    snapshot_type: SnapshotType
    inputs: dict[str, Any]
    outputs: Optional[dict[str, Any]] = None
    prompt_template: Optional[str] = None
    prompt_rendered: Optional[str] = None
    llm_response: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: Optional[float] = None

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class ExecutionState(BaseModel):
    """Current execution state for a job.

    Attributes:
        job_id: Job identifier
        status: Current status (running, paused, completed, error)
        current_agent: Name of agent currently executing
        current_step: Current step index
        total_steps: Total number of steps in workflow
        paused_at: When execution was paused (None if not paused)
        error_message: Error message if status is error
    """

    job_id: str
    status: ExecutionStateStatus
    current_agent: Optional[str] = None
    current_step: int = 0
    total_steps: int = 0
    paused_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class DebugSession(BaseModel):
    """Active debug session.

    Attributes:
        id: Unique session identifier
        job_id: Job being debugged
        created_at: When session was created
        state: Current execution state
        websocket_connected: Whether WebSocket is connected
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    state: ExecutionState
    websocket_connected: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class Injection(BaseModel):
    """Agent injection record.

    Attributes:
        id: Unique injection identifier
        job_id: Job this injection applies to
        agent_name: Name of agent to inject
        position: Where to inject (before, after, at_index)
        target: Target agent name or step index
        config: Agent configuration
        created_at: When injection was created
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    agent_name: str
    position: Literal["before", "after", "at_index"]
    target: str | int  # Agent name or step index
    config: dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


__all__ = [
    "Breakpoint",
    "BreakpointType",
    "StateSnapshot",
    "SnapshotType",
    "ExecutionState",
    "ExecutionStateStatus",
    "DebugSession",
    "StepMode",
    "Injection",
]
