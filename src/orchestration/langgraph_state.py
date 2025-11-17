# langgraph_state.py
"""State definitions for LangGraph workflow execution.

Defines TypedDict state schema for type-safe workflow state management.
"""

from typing import TypedDict, Dict, List, Any, Optional
from typing_extensions import NotRequired


class WorkflowState(TypedDict):
    """Workflow state passed between LangGraph nodes.
    
    This state structure mirrors the context dict used in sequential execution
    to maintain output parity.
    """
    # Job identification
    job_id: str
    workflow_name: str
    correlation_id: NotRequired[str]
    
    # Execution progress
    current_step: int
    total_steps: int
    completed_steps: List[str]
    
    # Agent outputs - keyed by agent type
    agent_outputs: Dict[str, Dict[str, Any]]
    
    # Shared state accumulated across agents
    shared_state: Dict[str, Any]
    
    # Input data
    input_data: Dict[str, Any]
    
    # Execution metrics
    llm_calls: int
    tokens_used: int
    
    # Error handling
    errors: NotRequired[List[Dict[str, str]]]
    failed_agents: NotRequired[List[str]]
    
    # Conditional branching flags
    code_generated: NotRequired[bool]
    requires_validation: NotRequired[bool]
    
    # Execution timestamps
    start_time: NotRequired[str]
    end_time: NotRequired[str]


class AgentOutput(TypedDict):
    """Standard agent output structure."""
    agent_id: str
    status: str  # "completed", "failed", "skipped"
    output_data: Dict[str, Any]
    error: NotRequired[str]
    execution_time: float
    llm_calls: int
    tokens_used: int


class CheckpointState(TypedDict):
    """Checkpoint state for persistence."""
    workflow_state: WorkflowState
    checkpoint_id: str
    step_name: str
    timestamp: str
# DOCGEN:LLM-FIRST@v4