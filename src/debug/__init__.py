"""Debug Backend Infrastructure - Visual Orchestration System.

This package implements the debug backend for Visual Studio-style debugging
of agent workflows, including:

- DebugController: Core debug session management (VIS-001)
- BreakpointManager: Breakpoint CRUD and condition evaluation (VIS-002)
- StateSnapshotStore: Capture/restore execution state (VIS-003)
- ExecutionController: Pause/Resume/Step controls (VIS-004)
- AgentInjector: Hot-inject agents into workflows (VIS-005)
- MeshDebugAdapter: Mesh orchestration debug visualization (MESH-009)

Author: Migration Implementation Agent
Created: 2025-12-18
Phase: 5 - Visual Orchestration
Taskcards: VIS-001 through VIS-006, MESH-009
"""

from typing import TYPE_CHECKING

from .models import (
    DebugSession,
    Breakpoint,
    BreakpointType,
    StateSnapshot,
    SnapshotType,
    ExecutionState,
    StepMode,
    Injection,
)
from .controller import DebugController, get_global_debug_controller
from .breakpoint_manager import BreakpointManager
from .condition_parser import ConditionParser, ConditionEvaluationError
from .state_snapshot import StateSnapshotStore
from .execution_controller import ExecutionController
from .agent_injector import AgentInjector

# Defer mesh_adapter import to avoid circular dependency
# mesh_adapter → controller → mcp.tracer → mcp → ... → mesh_handlers → debug.mesh_adapter (circular)
if TYPE_CHECKING:
    from .mesh_adapter import (
        MeshDebugAdapter,
        BidVisualization,
        MeshTimelineEvent,
        get_global_mesh_adapter,
        reset_global_mesh_adapter,
    )

__all__ = [
    # Models
    "DebugSession",
    "Breakpoint",
    "BreakpointType",
    "StateSnapshot",
    "SnapshotType",
    "ExecutionState",
    "StepMode",
    "Injection",
    # Controllers
    "DebugController",
    "get_global_debug_controller",
    "BreakpointManager",
    "ConditionParser",
    "ConditionEvaluationError",
    "StateSnapshotStore",
    "ExecutionController",
    "AgentInjector",
    # Mesh debug adapter (MESH-009)
    "MeshDebugAdapter",
    "BidVisualization",
    "MeshTimelineEvent",
    "get_global_mesh_adapter",
    "reset_global_mesh_adapter",
]
