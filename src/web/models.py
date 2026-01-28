"""Pydantic models for FastAPI web application."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    """Request model for creating a job."""
    workflow_id: str = Field(..., description="Workflow identifier")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Job input parameters")

    # Live E2E execution fields (optional)
    topic: Optional[str] = Field(default=None, description="Topic for content generation (live mode)")
    output_dir: Optional[str] = Field(default=None, description="Output directory path (triggers sync execution)")
    blog_collection: Optional[str] = Field(default=None, description="Chroma collection for blog knowledge")
    ref_collection: Optional[str] = Field(default=None, description="Chroma collection for API reference")


class RunSpec(BaseModel):
    """Request model for /api/generate endpoint with full run specification."""
    topic: str = Field(..., description="Topic for content generation")
    template: str = Field(default="default_blog", description="Template to use")
    workflow: Optional[str] = Field(default=None, description="Workflow ID override")
    config_overrides: Optional[Dict[str, Any]] = Field(default=None, description="Config overrides")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class BatchJobCreate(BaseModel):
    """Request model for batch job creation."""
    workflow_id: str = Field(..., description="Workflow identifier for all jobs")
    jobs: List[Dict[str, Any]] = Field(..., min_length=1, description="List of job input specifications (at least one required)")
    batch_name: Optional[str] = Field(default=None, description="Optional batch identifier")


class JobResponse(BaseModel):
    """Response model for job creation."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Initial job status")
    message: Optional[str] = Field(default=None, description="Additional information")
    output_path: Optional[str] = Field(default=None, description="Path to generated output (sync mode only)")


class BatchJobResponse(BaseModel):
    """Response model for batch job creation."""
    batch_id: str = Field(..., description="Batch identifier")
    job_ids: List[str] = Field(..., description="List of created job IDs")
    status: str = Field(..., description="Batch status")
    message: Optional[str] = Field(default=None, description="Additional information")


class JobStatus(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str
    progress: Optional[float] = None
    current_stage: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    output_path: Optional[str] = Field(default=None, description="Path to generated output file")


class JobList(BaseModel):
    """Response model for job list."""
    jobs: List[JobStatus] = Field(default_factory=list)
    total: int = Field(default=0)


class JobControl(BaseModel):
    """Response model for job control actions (pause/resume/cancel)."""
    job_id: str
    action: str
    status: str
    message: Optional[str] = None


class AgentLogEntry(BaseModel):
    """Model for a single agent log entry."""
    timestamp: datetime
    level: str
    agent_name: str
    message: str
    metadata: Optional[Dict[str, Any]] = None


class AgentLogs(BaseModel):
    """Response model for agent logs."""
    job_id: Optional[str] = None
    agent_name: str
    logs: List[AgentLogEntry] = Field(default_factory=list)
    total: int = Field(default=0)


class WorkflowInfo(BaseModel):
    """Response model for workflow information."""
    workflow_id: str
    name: str
    description: Optional[str] = None
    agents: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class WorkflowList(BaseModel):
    """Response model for workflow list."""
    workflows: List[WorkflowInfo] = Field(default_factory=list)
    total: int = Field(default=0)


class AgentInfo(BaseModel):
    """Response model for agent information."""
    agent_id: str
    name: str
    type: str
    description: Optional[str] = None
    status: str = Field(default="available")
    capabilities: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class AgentList(BaseModel):
    """Response model for agent list."""
    agents: List[AgentInfo] = Field(default_factory=list)
    total: int = Field(default=0)


class SystemHealth(BaseModel):
    """Response model for system health check."""
    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    components: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Component health status")
    version: Optional[str] = None
    uptime: Optional[float] = None


class ErrorResponse(BaseModel):
    """Response model for error cases."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# Visualization Models
# ============================================================================

class WorkflowListResponse(BaseModel):
    """Response model for workflow list."""
    workflows: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = Field(default=0)


class WorkflowGraphResponse(BaseModel):
    """Response model for workflow graph data."""
    profile_name: str
    name: str
    description: str = Field(default="")
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowRenderResponse(BaseModel):
    """Response model for rendered workflow."""
    workflow_id: str
    format: str
    content: Dict[str, Any]


class AgentMetricsResponse(BaseModel):
    """Response model for agent metrics."""
    agent_id: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    last_execution: Optional[str] = None
    current_status: str = "pending"
    recent_executions: List[Dict[str, Any]] = Field(default_factory=list)


class AgentListMetricsResponse(BaseModel):
    """Response model for list of agent metrics."""
    agents: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = Field(default=0)


class SystemMetricsResponse(BaseModel):
    """Response model for system metrics."""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    memory_total_mb: float
    active_jobs: int
    total_agents: int
    uptime_seconds: float
    timestamp: datetime


class JobMetricsResponse(BaseModel):
    """Response model for job execution metrics."""
    job_id: str
    status: str
    total_agents: int = 0
    completed_agents: int = 0
    failed_agents: int = 0
    total_flows: int = 0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0


# ============================================================================
# Debug Models
# ============================================================================

class BreakpointCreateRequest(BaseModel):
    """Request model for creating a breakpoint."""
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    agent_id: str
    event_type: str
    condition: Optional[str] = None
    max_hits: Optional[int] = None


class BreakpointResponse(BaseModel):
    """Response model for breakpoint."""
    breakpoint_id: str
    session_id: str
    agent_id: str
    event_type: str
    condition: Optional[str] = None
    enabled: bool = True
    hit_count: int = 0
    max_hits: Optional[int] = None
    created_at: datetime


class BreakpointListResponse(BaseModel):
    """Response model for list of breakpoints."""
    breakpoints: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = Field(default=0)


class DebugStepRequest(BaseModel):
    """Request model for debug step operation."""
    session_id: str
    action: str = Field(default="step", description="Step action: 'step', 'continue', 'step_over'")


class DebugStepResponse(BaseModel):
    """Response model for debug step operation."""
    session_id: str
    status: str
    current_step: Optional[str] = None
    message: str


class DebugStateResponse(BaseModel):
    """Response model for debug state."""
    job_id: str
    session_id: str
    status: str
    current_step: Optional[str] = None
    step_history: List[Dict[str, Any]] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict)
    breakpoints: List[Dict[str, Any]] = Field(default_factory=list)


# Session Management Models
class DebugSessionCreate(BaseModel):
    """Request model for creating a debug session."""
    job_id: str = Field(..., description="Job ID to debug")
    auto_pause: bool = Field(default=True, description="Pause job at start")


class DebugSessionResponse(BaseModel):
    """Response model for debug session."""
    session_id: str = Field(..., description="Debug session ID")
    job_id: str = Field(..., description="Job ID being debugged")
    status: str = Field(..., description="Session status")
    started_at: str = Field(..., description="Session start time")
    breakpoint_count: int = Field(default=0, description="Number of active breakpoints")


class DebugSessionListResponse(BaseModel):
    """Response model for list of debug sessions."""
    sessions: List[DebugSessionResponse] = Field(default_factory=list)
    total: int = Field(default=0)


class StepResult(BaseModel):
    """Result of a step operation."""
    session_id: str
    status: str  # 'paused', 'completed', 'error'
    current_agent: Optional[str] = None
    next_agent: Optional[str] = None
    execution_time_ms: Optional[float] = None
    output: Optional[Dict[str, Any]] = None
    breakpoint_hit: Optional[str] = None


class ExecutionTraceEntry(BaseModel):
    """Single entry in execution trace."""
    timestamp: str
    agent_id: str
    event_type: str  # 'start', 'complete', 'error'
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class ExecutionTrace(BaseModel):
    """Complete execution trace for a session."""
    session_id: str
    job_id: str
    entries: List[ExecutionTraceEntry] = Field(default_factory=list)
    total_entries: int = Field(default=0)
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class ContinueRequest(BaseModel):
    """Request to continue execution."""
    remove_breakpoints: bool = Field(default=False, description="Remove all breakpoints")


# ============================================================================
# Agent Health Models
# ============================================================================

class AgentHealthMetrics(BaseModel):
    """Health metrics for an agent."""
    agent_id: str = Field(..., description="Agent identifier")
    total_executions: int = Field(default=0, description="Total executions")
    successful_executions: int = Field(default=0, description="Successful executions")
    failed_executions: int = Field(default=0, description="Failed executions")
    last_execution_time: Optional[str] = Field(default=None, description="Last execution timestamp")
    average_duration_ms: Optional[float] = Field(default=None, description="Average execution duration")
    error_rate: float = Field(default=0.0, description="Error rate (0-1)")
    status: str = Field(default="unknown", description="Health status: unknown, healthy, degraded, failing")


class AgentHealth(BaseModel):
    """Complete health information for an agent."""
    agent_id: str
    name: str
    metrics: AgentHealthMetrics
    recent_failures: List[Dict[str, Any]] = Field(default_factory=list, description="Recent failure details")


class HealthSummary(BaseModel):
    """Overall health summary for all agents."""
    timestamp: str
    total_agents: int
    healthy_agents: int
    degraded_agents: int
    failing_agents: int
    unknown_agents: int
    agents: List[AgentHealthMetrics]


class FailureReport(BaseModel):
    """Detailed failure report."""
    timestamp: str
    agent_id: str
    job_id: str
    error_type: str
    error_message: str
    input_data: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None


class FailureList(BaseModel):
    """List of failures for an agent."""
    agent_id: str
    failures: List[FailureReport]
    total: int




# ============================================================================
# Flow Analysis Models
# ============================================================================

class FlowEvent(BaseModel):
    """Model for a data flow event between agents."""
    flow_id: str = Field(..., description="Unique flow identifier")
    source_agent: str = Field(..., description="Source agent name")
    target_agent: str = Field(..., description="Target agent name")
    event_type: str = Field(..., description="Type of event")
    timestamp: str = Field(..., description="Event timestamp (ISO format)")
    correlation_id: str = Field(..., description="Job/workflow correlation ID")
    status: str = Field(default='active', description="Flow status (active/completed/failed)")
    latency_ms: Optional[float] = Field(default=None, description="Latency in milliseconds")
    data_size_bytes: Optional[int] = Field(default=None, description="Data size in bytes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class FlowRealtimeResponse(BaseModel):
    """Response model for realtime flows endpoint."""
    flows: List[FlowEvent] = Field(default_factory=list, description="Active flows in time window")
    window_seconds: int = Field(..., description="Time window in seconds")
    count: int = Field(..., description="Number of flows returned")
    timestamp: str = Field(..., description="Response timestamp (ISO format)")


class FlowHistoryResponse(BaseModel):
    """Response model for flow history endpoint."""
    correlation_id: str = Field(..., description="Job/workflow correlation ID")
    flows: List[FlowEvent] = Field(default_factory=list, description="Historical flows")
    total_flows: int = Field(..., description="Total number of flows")
    start_time: Optional[str] = Field(default=None, description="First flow timestamp")
    end_time: Optional[str] = Field(default=None, description="Last flow timestamp")
    total_duration_ms: Optional[float] = Field(default=None, description="Total duration in milliseconds")


class BottleneckReport(BaseModel):
    """Model for a detected bottleneck."""
    agent_id: str = Field(..., description="Agent with bottleneck")
    avg_latency_ms: float = Field(..., description="Average latency in milliseconds")
    max_latency_ms: float = Field(..., description="Maximum latency in milliseconds")
    flow_count: int = Field(..., description="Number of flows analyzed")
    severity: str = Field(..., description="Severity level (low/medium/high/critical)")
    timestamp: str = Field(..., description="Detection timestamp (ISO format)")


class BottleneckResponse(BaseModel):
    """Response model for bottlenecks endpoint."""
    bottlenecks: List[BottleneckReport] = Field(default_factory=list, description="Detected bottlenecks")
    threshold_ms: float = Field(..., description="Latency threshold used")
    count: int = Field(..., description="Number of bottlenecks detected")
    timestamp: str = Field(..., description="Response timestamp (ISO format)")


class ActiveFlow(BaseModel):
    """Model for an active flow."""
    flow_id: str = Field(..., description="Flow identifier")
    correlation_id: str = Field(..., description="Job/workflow correlation ID")
    source_agent: str = Field(..., description="Source agent name")
    target_agent: str = Field(..., description="Target agent name")
    event_type: str = Field(..., description="Event type")
    started_at: Optional[str] = Field(default=None, description="Flow start timestamp")
    current_duration_ms: Optional[float] = Field(default=None, description="Current duration in milliseconds")


class ActiveFlowsResponse(BaseModel):
    """Response model for active flows endpoint."""
    active_flows: List[ActiveFlow] = Field(default_factory=list, description="Currently active flows")
    count: int = Field(..., description="Number of active flows")
    timestamp: str = Field(..., description="Response timestamp (ISO format)")


# Checkpoint models
class CheckpointMetadata(BaseModel):
    """Checkpoint metadata."""
    checkpoint_id: str
    job_id: str
    step_name: str
    timestamp: str
    workflow_version: str
    workflow_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CheckpointList(BaseModel):
    """List of checkpoints for a job."""
    job_id: str
    checkpoints: List[CheckpointMetadata]
    total: int
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class CheckpointResponse(BaseModel):
    """Single checkpoint details."""
    checkpoint_id: str
    job_id: str
    step_name: str
    timestamp: str
    workflow_version: str
    workflow_name: Optional[str] = None
    state_snapshot: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class RestoreRequest(BaseModel):
    """Request to restore from checkpoint."""
    resume: bool = Field(default=False, description="If true, resume job execution after restore")


class RestoreResponse(BaseModel):
    """Response after restoring checkpoint."""
    checkpoint_id: str
    job_id: str
    state: Dict[str, Any]
    job_status: str
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class CleanupRequest(BaseModel):
    """Request to cleanup old checkpoints."""
    job_id: str = Field(..., description="Job ID to cleanup checkpoints for")
    keep_last: int = Field(default=10, ge=1, le=100, description="Number of most recent checkpoints to keep")


class CleanupResponse(BaseModel):
    """Response after cleanup operation."""
    job_id: str
    deleted_count: int
    kept_count: int
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
