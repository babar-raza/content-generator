"""
MCP-Compliant Protocol Definitions for UCOP Visual Orchestration

Model Context Protocol (MCP) compliance for agent orchestration,
monitoring, and visual workflow management.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# MCP Resource Types
# ============================================================================

class ResourceType(str, Enum):
    """MCP resource types for orchestration."""
    WORKFLOW = "workflow"
    AGENT = "agent"
    JOB = "job"
    CHECKPOINT = "checkpoint"
    FLOW = "flow"
    METRIC = "metric"


class ResourceStatus(str, Enum):
    """Resource execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# MCP Request/Response Models
# ============================================================================

class MCPRequest(BaseModel):
    """Base MCP request."""
    method: str = Field(..., description="MCP method name")
    params: Dict[str, Any] = Field(default_factory=dict)
    id: Optional[Union[str, int]] = Field(None, description="Request ID")

    class Config:
        extra = "allow"  # Allow extra fields like "jsonrpc" for JSON-RPC 2.0 compatibility
        json_schema_extra = {
            "example": {
                "method": "workflows/list",
                "params": {},
                "id": "req_123"
            }
        }


class MCPResponse(BaseModel):
    """Base MCP response."""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

    class Config:
        extra = "allow"  # Allow extra fields for JSON-RPC 2.0 compatibility
        json_schema_extra = {
            "example": {
                "result": {"workflows": []},
                "id": "req_123"
            }
        }


class MCPError(BaseModel):
    """MCP error response."""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


# ============================================================================
# Workflow Resources
# ============================================================================

class WorkflowNode(BaseModel):
    """Workflow node definition."""
    id: str
    agent_id: str
    type: str = "agent"
    params: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    checkpoints: List[str] = Field(default_factory=list)


class WorkflowEdge(BaseModel):
    """Workflow edge/connection."""
    source: str
    target: str
    condition: Optional[str] = None


class WorkflowResource(BaseModel):
    """MCP workflow resource."""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: str = "application/vnd.ucop.workflow+json"
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Agent Resources
# ============================================================================

class AgentCapability(BaseModel):
    """Agent capability definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]


class AgentResource(BaseModel):
    """MCP agent resource."""
    uri: str
    name: str
    type: str
    status: ResourceStatus
    capabilities: List[AgentCapability]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_execution: Optional[datetime] = None


# ============================================================================
# Job Resources
# ============================================================================

class JobStepExecution(BaseModel):
    """Job step execution details."""
    step_id: str
    agent_id: str
    status: ResourceStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class JobResource(BaseModel):
    """MCP job resource."""
    uri: str
    job_id: str
    workflow_uri: str
    status: ResourceStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    steps: List[JobStepExecution] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    progress: float = 0.0


# ============================================================================
# Flow Resources
# ============================================================================

class FlowEvent(BaseModel):
    """Data flow event between agents."""
    event_id: str
    source_agent: str
    target_agent: str
    event_type: str
    timestamp: datetime
    data_size: int
    duration_ms: Optional[int] = None
    status: ResourceStatus


class FlowResource(BaseModel):
    """MCP flow resource for agent data flow tracking."""
    uri: str
    job_id: str
    correlation_id: str
    events: List[FlowEvent]
    bottlenecks: List[Dict[str, Any]] = Field(default_factory=list)


# ============================================================================
# Metric Resources
# ============================================================================

class MetricPoint(BaseModel):
    """Single metric data point."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)


class MetricResource(BaseModel):
    """MCP metric resource."""
    uri: str
    name: str
    description: str
    unit: str
    metric_type: str  # "counter", "gauge", "histogram"
    data_points: List[MetricPoint]


# ============================================================================
# MCP Tools for Orchestration
# ============================================================================

class ToolParameter(BaseModel):
    """Tool parameter definition."""
    name: str
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None


class MCPTool(BaseModel):
    """MCP tool definition."""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "run_workflow",
                "description": "Execute a workflow",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string"}
                    }
                }
            }
        }


# ============================================================================
# MCP Prompts for Orchestration
# ============================================================================

class MCPPrompt(BaseModel):
    """MCP prompt template."""
    name: str
    description: str
    arguments: List[ToolParameter] = Field(default_factory=list)


# ============================================================================
# Real-time Updates
# ============================================================================

class StreamEvent(BaseModel):
    """Real-time stream event."""
    event_type: str
    resource_type: ResourceType
    resource_uri: str
    timestamp: datetime
    data: Dict[str, Any]


class SubscriptionRequest(BaseModel):
    """Subscription request for real-time updates."""
    resource_uri: str
    event_types: List[str] = Field(default_factory=list)


# ============================================================================
# Monitoring & Debugging
# ============================================================================





def create_resource_uri(resource_type: ResourceType, resource_id: str) -> str:
    """Create MCP-compliant resource URI."""
    return f"ucop://{resource_type.value}/{resource_id}"


def parse_resource_uri(uri: str) -> tuple[ResourceType, str]:
    """Parse MCP resource URI."""
    if not uri.startswith("ucop://"):
        raise ValueError(f"Invalid UCOP resource URI: {uri}")

    parts = uri[7:].split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid UCOP resource URI format: {uri}")

    resource_type = ResourceType(parts[0])
    resource_id = parts[1]

    return resource_type, resource_id


# ============================================================================
# MCP Protocol Handler
# ============================================================================

class MCPProtocol:
    """MCP Protocol handler for routing requests to appropriate handlers.

    Provides a unified interface for handling MCP requests across different
    execution contexts (CLI, Web, etc.)
    """

    # Standard MCP error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    def __init__(
        self,
        executor=None,
        job_engine=None,
        agent_registry=None
    ):
        """Initialize MCP Protocol handler.

        Args:
            executor: Execution engine for running jobs/agents
            job_engine: Job management engine
            agent_registry: Registry of available agents
        """
        self.executor = executor
        self.job_engine = job_engine
        self.agent_registry = agent_registry

        # Method routing table
        self._methods = {
            "workflow.list": self._handle_workflow_list,
            "workflow.execute": self._handle_workflow_execute,
            "workflow.status": self._handle_workflow_status,
            "agent.list": self._handle_agent_list,
            "agent.invoke": self._handle_agent_invoke,
            "job.create": self._handle_job_create,
            "job.status": self._handle_job_status,
        }

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an MCP request and route to appropriate handler.

        Args:
            request: MCPRequest to process

        Returns:
            MCPResponse with result or error
        """
        method = request.method

        # Check if method exists
        if method not in self._methods:
            return MCPResponse(
                id=request.id,
                error={
                    "code": self.METHOD_NOT_FOUND,
                    "message": f"Method not found: {method}"
                }
            )

        try:
            # Call the handler
            handler = self._methods[method]
            result = await handler(request.params)

            return MCPResponse(
                id=request.id,
                result=result
            )
        except Exception as e:
            return MCPResponse(
                id=request.id,
                error={
                    "code": self.INTERNAL_ERROR,
                    "message": str(e)
                }
            )

    async def _handle_workflow_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available workflows."""
        workflows = []
        if self.executor and hasattr(self.executor, 'get_workflows'):
            workflows = self.executor.get_workflows()
        return {"workflows": workflows}

    async def _handle_workflow_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow."""
        if not self.executor:
            return {"error": "No executor configured"}
        workflow_name = params.get("workflow_name", "default")
        return {"status": "started", "workflow": workflow_name}

    async def _handle_workflow_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get workflow execution status."""
        job_id = params.get("job_id")
        if self.job_engine and hasattr(self.job_engine, 'get_job_status'):
            return self.job_engine.get_job_status(job_id)
        return {"status": "unknown", "job_id": job_id}

    async def _handle_agent_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available agents."""
        agents = []
        if self.agent_registry and hasattr(self.agent_registry, 'list_agents'):
            agents = self.agent_registry.list_agents()
        elif self.executor and hasattr(self.executor, 'get_agents'):
            agents = self.executor.get_agents()
        return {"agents": agents}

    async def _handle_agent_invoke(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a specific agent."""
        agent_id = params.get("agent_id")
        if not self.executor:
            return {"error": "No executor configured"}
        return {"status": "invoked", "agent_id": agent_id}

    async def _handle_job_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new job."""
        if not self.job_engine:
            return {"error": "No job engine configured"}
        return {"status": "created", "job_id": "job_placeholder"}

    async def _handle_job_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get job status."""
        job_id = params.get("job_id")
        if self.job_engine and hasattr(self.job_engine, 'get_job_status'):
            return self.job_engine.get_job_status(job_id)
        return {"status": "unknown", "job_id": job_id}
