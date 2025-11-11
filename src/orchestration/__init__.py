"""Orchestration Layer (v-ucop)

Provides workflow compilation, job execution, monitoring, and control.
"""

import logging
logger = logging.getLogger(__name__)

# Try to import LangGraph-dependent components
try:
    from .workflow_compiler import WorkflowCompiler, WorkflowDefinition, WorkflowStep, WorkflowState  # type: ignore
    from .workflow_state import BlogState  # type: ignore
    from .job_execution_engine import JobExecutionEngine  # type: ignore
    LANGGRAPH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LangGraph not available, using fallback: {e}")
    LANGGRAPH_AVAILABLE = False
    # Import fallback components
    from .fallback_engine import (
        FallbackOrchestrationEngine as JobExecutionEngine,
        WorkflowStep, 
        WorkflowState,
        JobStatus
    )
    # Create placeholder classes
    class WorkflowCompiler:
        def __init__(self, *args, **kwargs):
            raise NotImplementedError("WorkflowCompiler requires LangGraph")
    class WorkflowDefinition:
        pass
    class BlogState:
        pass

from .checkpoint_manager import CheckpointManager  # type: ignore

# These imports are optional - may not exist in all installations
try:
    from .ops_console import OpsConsole  # type: ignore
except ImportError:
    OpsConsole = None  # type: ignore

try:
    from .monitor import SystemMonitor  # type: ignore
except ImportError:
    SystemMonitor = None  # type: ignore

try:
    from .hot_reload import HotReloadManager  # type: ignore
except ImportError:
    HotReloadManager = None  # type: ignore

try:
    from .agent_scanner import AgentScanner  # type: ignore
except ImportError:
    AgentScanner = None  # type: ignore

try:
    from .enhanced_registry import EnhancedRegistry  # type: ignore
except ImportError:
    EnhancedRegistry = None  # type: ignore

__all__ = [
    'WorkflowCompiler',
    'WorkflowDefinition',
    'WorkflowStep',
    'WorkflowState',
    'BlogState',
    'JobExecutionEngine',
    'CheckpointManager',
]

# Optional exports
if OpsConsole:
    __all__.append('OpsConsole')
if SystemMonitor:
    __all__.append('SystemMonitor')
if HotReloadManager:
    __all__.append('HotReloadManager')
if AgentScanner:
    __all__.append('AgentScanner')
if EnhancedRegistry:
    __all__.append('EnhancedRegistry')

__version__ = '1.0.0'
