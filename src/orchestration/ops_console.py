"""
Ops Console API - FastAPI-based orchestration and monitoring interface.

Provides REST and WebSocket endpoints for:
- Agent registry management
- Workflow execution and control
- Real-time job monitoring
- Approval gate handling
- Live parameter injection
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Import your existing components
from enhanced_registry import EnhancedAgentRegistry
from job_execution_engine import JobExecutionEngine, JobExecution, JobStatus
from workflow_compiler import WorkflowCompiler
from patching import GraphPatcher, GraphPatch, PatchType

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for API
# ============================================================================

class AgentInfo(BaseModel):
    """Agent information for API responses."""
    name: str
    type: str
    capabilities: List[str]
    health_status: str
    contract_schema: Optional[Dict[str, Any]] = None
    last_used: Optional[str] = None


class WorkflowDefinition(BaseModel):
    """Workflow definition for API."""
    id: str
    name: str
    description: Optional[str] = None
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    timeout: Optional[int] = 300


class JobRequest(BaseModel):
    """Request to start a new job."""
    workflow_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)


class JobControl(BaseModel):
    """Job control command."""
    action: str  # pause, resume, cancel
    reason: Optional[str] = None


class ParameterUpdate(BaseModel):
    """Parameter update for running job."""
    parameter: str
    value: Any


class ApprovalDecision(BaseModel):
    """Approval gate decision."""
    checkpoint_id: str
    approved: bool
    reason: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None


class GraphPatchRequest(BaseModel):
    """Request to patch a running workflow graph."""
    patch_type: str
    node_id: Optional[str] = None
    new_node: Optional[Dict[str, Any]] = None
    target_node: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


# ============================================================================
# Connection Manager for WebSocket
# ============================================================================

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and store WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, client_id: str):
        """Remove WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected. Remaining: {len(self.active_connections)}")
            
    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """Send message to specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending to {client_id}: {e}")
                self.disconnect(client_id)
                
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        disconnected = []
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)


# ============================================================================
# Ops Console Application
# ============================================================================

class OpsConsole:
    """Main Ops Console application."""
    
    def __init__(
        self,
        registry: Optional[EnhancedAgentRegistry] = None,
        executor: Optional[JobExecutionEngine] = None,
        compiler: Optional[WorkflowCompiler] = None
    ):
        self.app = FastAPI(
            title="UCOP Ops Console",
            description="Unified Content Operations Platform - Orchestration Console",
            version="1.0.0"
        )
        
        # Core components
        self.registry = registry or EnhancedAgentRegistry()
        self.executor = executor or JobExecutionEngine(None, None)
        # Create a mock event bus for WorkflowCompiler
        from unittest.mock import MagicMock
        mock_event_bus = MagicMock()
        self.compiler = compiler or WorkflowCompiler(self.registry, mock_event_bus)
        # Create a mock validator for GraphPatcher
        mock_validator = MagicMock()
        self.patcher = GraphPatcher(mock_validator)
        
        # WebSocket manager
        self.ws_manager = ConnectionManager()
        
        # Active jobs tracking
        self.active_jobs: Dict[str, JobExecution] = {}
        
        # Workflow definitions
        self.workflows: Dict[str, WorkflowDefinition] = {}
        
        # Pending approvals
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
        
        # Setup routes and middleware
        self._setup_middleware()
        self._setup_routes()
        
        logger.info("Ops Console initialized")
        
    def _setup_middleware(self):
        """Configure CORS and other middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
    def _setup_routes(self):
        """Setup all API routes."""
        
        # ====================================================================
        # Agent Registry Endpoints
        # ====================================================================
        
        @self.app.get("/api/agents", response_model=List[AgentInfo])
        async def list_agents():
            """List all registered agents."""
            agents = []
            # Handle both EnhancedAgentRegistry and regular registry
            if hasattr(self.registry, 'list_mcp_contracts'):
                # Enhanced registry
                contracts = self.registry.list_mcp_contracts()
                for contract in contracts:
                    agents.append(AgentInfo(
                        name=contract.agent_id,
                        type="mcp_compliant",
                        capabilities=contract.capabilities,
                        health_status="healthy",
                        contract_schema=contract.input_schema,
                        last_used=None
                    ))
            else:
                # Fallback for regular registry
                agents_data = getattr(self.registry, 'agents', {})
                for name, agent_meta in agents_data.items():
                    agents.append(AgentInfo(
                        name=name,
                        type=agent_meta.get("type", "unknown"),
                        capabilities=agent_meta.get("capabilities", []),
                        health_status=agent_meta.get("health_status", "unknown"),
                        contract_schema=agent_meta.get("contract", {}).get("input_schema"),
                        last_used=agent_meta.get("last_used")
                    ))
            return agents
        
        @self.app.get("/api/agents/{agent_name}", response_model=AgentInfo)
        async def get_agent(agent_name: str):
            """Get details of a specific agent."""
            # Handle both EnhancedAgentRegistry and regular registry
            if hasattr(self.registry, 'get_mcp_contract'):
                # Enhanced registry
                contract = self.registry.get_mcp_contract(agent_name)
                if not contract:
                    raise HTTPException(status_code=404, detail="Agent not found")
                return AgentInfo(
                    name=contract.agent_id,
                    type="mcp_compliant",
                    capabilities=contract.capabilities,
                    health_status="healthy",
                    contract_schema=contract.input_schema,
                    last_used=None
                )
            else:
                # Fallback for regular registry
                agents_data = getattr(self.registry, 'agents', {})
                if agent_name not in agents_data:
                    raise HTTPException(status_code=404, detail="Agent not found")

                agent_meta = agents_data[agent_name]
                return AgentInfo(
                    name=agent_name,
                    type=agent_meta.get("type", "unknown"),
                    capabilities=agent_meta.get("capabilities", []),
                    health_status=agent_meta.get("health_status", "unknown"),
                    contract_schema=agent_meta.get("contract", {}).get("input_schema"),
                    last_used=agent_meta.get("last_used")
                )
        
        @self.app.post("/api/agents/reload")
        async def reload_agents():
            """Reload agent registry from configuration."""
            try:
                # Handle both EnhancedAgentRegistry and regular registry
                if hasattr(self.registry, 'force_rediscovery'):
                    # Enhanced registry
                    self.registry.force_rediscovery()
                    agent_count = len(self.registry.list_mcp_contracts())
                else:
                    # Fallback for regular registry
                    self.registry.reload()
                    agent_count = len(getattr(self.registry, 'agents', {}))

                await self.ws_manager.broadcast({
                    "type": "registry_reloaded",
                    "timestamp": datetime.now().isoformat(),
                    "agent_count": agent_count
                })
                return {"status": "success", "agent_count": agent_count}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # ====================================================================
        # Workflow Management Endpoints
        # ====================================================================
        
        @self.app.get("/api/workflows", response_model=List[WorkflowDefinition])
        async def list_workflows():
            """List all available workflows."""
            return list(self.workflows.values())
        
        @self.app.post("/api/workflows")
        async def create_workflow(workflow: WorkflowDefinition):
            """Create a new workflow definition."""
            self.workflows[workflow.id] = workflow
            await self.ws_manager.broadcast({
                "type": "workflow_created",
                "workflow_id": workflow.id,
                "name": workflow.name
            })
            return {"status": "success", "workflow_id": workflow.id}
        
        @self.app.get("/api/workflows/{workflow_id}", response_model=WorkflowDefinition)
        async def get_workflow(workflow_id: str):
            """Get workflow definition."""
            if workflow_id not in self.workflows:
                raise HTTPException(status_code=404, detail="Workflow not found")
            return self.workflows[workflow_id]
        
        # ====================================================================
        # Job Execution Endpoints
        # ====================================================================
        
        @self.app.post("/api/jobs")
        async def start_job(request: JobRequest, background_tasks: BackgroundTasks):
            """Start a new job execution."""
            if request.workflow_id not in self.workflows:
                raise HTTPException(status_code=404, detail="Workflow not found")
            
            # Create job
            job_id = str(uuid4())
            workflow = self.workflows[request.workflow_id]
            
            # Compile workflow to LangGraph
            try:
                graph = self.compiler.compile_workflow(workflow.model_dump())
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Workflow compilation failed: {e}")
            
            # Create job
            job = JobExecution(
                job_id=job_id,
                workflow_name=request.workflow_id,
                correlation_id=str(uuid4()),
                input_params=request.parameters
            )
            
            self.active_jobs[job_id] = job
            
            # Start execution in background
            background_tasks.add_task(self._execute_job, job_id)
            
            await self.ws_manager.broadcast({
                "type": "job_started",
                "job_id": job_id,
                "workflow_id": request.workflow_id
            })
            
            return {"status": "success", "job_id": job_id}
        
        @self.app.get("/api/jobs")
        async def list_jobs():
            """List all jobs (active and completed)."""
            jobs = []
            for job_id, job in self.active_jobs.items():
                jobs.append({
                    "id": job_id,
                    "workflow_id": job.workflow_name,
                    "status": job.status.value,
                    "progress": job.progress,
                    "started_at": job.started_at,
                    "completed_at": job.completed_at
                })
            return jobs
        
        @self.app.get("/api/jobs/{job_id}")
        async def get_job(job_id: str):
            """Get job details and status."""
            if job_id not in self.active_jobs:
                raise HTTPException(status_code=404, detail="Job not found")
            
            job = self.active_jobs[job_id]
            return {
                "id": job_id,
                "workflow_id": job.workflow_name,
                "status": job.status.value,
                "progress": job.progress,
                "current_node": job.current_step,
                "parameters": job.input_params,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "error": job.error_message
            }
        
        @self.app.post("/api/jobs/{job_id}/control")
        async def control_job(job_id: str, control: JobControl):
            """Control job execution (pause, resume, cancel)."""
            if job_id not in self.active_jobs:
                raise HTTPException(status_code=404, detail="Job not found")
            
            job = self.active_jobs[job_id]
            
            if control.action == "pause":
                job.status = JobStatus.PAUSED
                await self.ws_manager.broadcast({
                    "type": "job_paused",
                    "job_id": job_id,
                    "reason": control.reason
                })
            elif control.action == "resume":
                job.status = JobStatus.RUNNING
                await self.ws_manager.broadcast({
                    "type": "job_resumed",
                    "job_id": job_id
                })
            elif control.action == "cancel":
                job.status = JobStatus.CANCELLED
                await self.ws_manager.broadcast({
                    "type": "job_cancelled",
                    "job_id": job_id,
                    "reason": control.reason
                })
            else:
                raise HTTPException(status_code=400, detail="Invalid action")
            
            return {"status": "success", "action": control.action}
        
        @self.app.post("/api/jobs/{job_id}/parameters")
        async def update_parameters(job_id: str, update: ParameterUpdate):
            """Update job parameters at runtime."""
            if job_id not in self.active_jobs:
                raise HTTPException(status_code=404, detail="Job not found")
            
            job = self.active_jobs[job_id]
            job.input_params[update.parameter] = update.value
            
            await self.ws_manager.broadcast({
                "type": "parameters_updated",
                "job_id": job_id,
                "parameter": update.parameter,
                "value": update.value
            })
            
            return {"status": "success"}
        
        @self.app.post("/api/jobs/{job_id}/patch")
        async def patch_graph(job_id: str, patch: GraphPatchRequest):
            """Patch the workflow graph at runtime."""
            if job_id not in self.active_jobs:
                raise HTTPException(status_code=404, detail="Job not found")
            
            job = self.active_jobs[job_id]
            
            # Create patch
            graph_patch = GraphPatch(
                patch_type=PatchType(patch.patch_type),
                node_id=patch.node_id,
                new_node=patch.new_node,
                target_node=patch.target_node,
                parameters=patch.parameters
            )
            
            # Queue patch
            self.patcher.queue_patch(job_id, graph_patch)
            
            await self.ws_manager.broadcast({
                "type": "graph_patched",
                "job_id": job_id,
                "patch_type": patch.patch_type
            })
            
            return {"status": "success", "patch_queued": True}
        
        # ====================================================================
        # Approval Gate Endpoints
        # ====================================================================
        
        @self.app.get("/api/approvals")
        async def list_pending_approvals():
            """List all pending approvals."""
            return list(self.pending_approvals.values())
        
        @self.app.post("/api/approvals/{job_id}")
        async def submit_approval(job_id: str, decision: ApprovalDecision):
            """Submit approval decision for a checkpoint."""
            if job_id not in self.pending_approvals:
                raise HTTPException(status_code=404, detail="No pending approval for this job")
            
            approval = self.pending_approvals[job_id]
            approval["decision"] = decision.approved
            approval["reason"] = decision.reason
            approval["modifications"] = decision.modifications
            approval["decided_at"] = datetime.now().isoformat()
            
            # Resume job if approved
            if decision.approved and job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                job.status = JobStatus.RUNNING
                
                # Apply modifications if provided
                if decision.modifications:
                    job.input_params.update(decision.modifications)
            
            # Remove from pending
            del self.pending_approvals[job_id]
            
            await self.ws_manager.broadcast({
                "type": "approval_decided",
                "job_id": job_id,
                "checkpoint_id": decision.checkpoint_id,
                "approved": decision.approved
            })
            
            return {"status": "success", "approved": decision.approved}
        
        # ====================================================================
        # WebSocket Endpoint for Real-Time Updates
        # ====================================================================
        
        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            """WebSocket connection for real-time updates."""
            await self.ws_manager.connect(websocket, client_id)
            
            try:
                # Send initial state
                await self.ws_manager.send_personal_message({
                    "type": "connected",
                    "client_id": client_id,
                    "timestamp": datetime.now().isoformat()
                }, client_id)
                
                # Keep connection alive and listen for client messages
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Handle client messages (subscription requests, etc.)
                    if message.get("type") == "subscribe":
                        job_id = message.get("job_id")
                        # Add subscription logic if needed
                        await self.ws_manager.send_personal_message({
                            "type": "subscribed",
                            "job_id": job_id
                        }, client_id)
                        
            except WebSocketDisconnect:
                self.ws_manager.disconnect(client_id)
            except Exception as e:
                logger.error(f"WebSocket error for {client_id}: {e}")
                self.ws_manager.disconnect(client_id)
        
        # ====================================================================
        # Health & Metrics Endpoints
        # ====================================================================
        
        @self.app.get("/api/health")
        async def health_check():
            """Health check endpoint."""
            # Handle both EnhancedAgentRegistry and regular registry
            if hasattr(self.registry, 'list_mcp_contracts'):
                # Enhanced registry
                agent_count = len(self.registry.list_mcp_contracts())
            else:
                # Fallback for regular registry
                agent_count = len(getattr(self.registry, 'agents', {}))

            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "agents": agent_count,
                "active_jobs": len([j for j in self.active_jobs.values() if j.status == JobStatus.RUNNING]),
                "workflows": len(self.workflows)
            }
        
        @self.app.get("/api/metrics")
        async def get_metrics():
            """Get system metrics."""
            total_jobs = len(self.active_jobs)
            running = len([j for j in self.active_jobs.values() if j.status == JobStatus.RUNNING])
            completed = len([j for j in self.active_jobs.values() if j.status == JobStatus.COMPLETED])
            failed = len([j for j in self.active_jobs.values() if j.status == JobStatus.FAILED])

            # Handle both EnhancedAgentRegistry and regular registry
            if hasattr(self.registry, 'list_mcp_contracts'):
                # Enhanced registry
                agents_data = self.registry.list_mcp_contracts()
                total_agents = len(agents_data)
                healthy_agents = len([a for a in agents_data if hasattr(a, 'agent_id')])  # All MCP agents are considered healthy
            else:
                # Fallback for regular registry
                agents_data = getattr(self.registry, 'agents', {})
                total_agents = len(agents_data)
                healthy_agents = len([a for a in agents_data.values() if a.get("health_status") == "healthy"])

            return {
                "agents": {
                    "total": total_agents,
                    "healthy": healthy_agents
                },
                "jobs": {
                    "total": total_jobs,
                    "running": running,
                    "completed": completed,
                    "failed": failed,
                    "pending_approvals": len(self.pending_approvals)
                },
                "workflows": {
                    "total": len(self.workflows)
                },
                "connections": {
                    "websockets": len(self.ws_manager.active_connections)
                }
            }
    
    async def _execute_job(self, job_id: str):
        """Execute job in background."""
        try:
            job = self.active_jobs[job_id]
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now().isoformat()

            await self.ws_manager.broadcast({
                "type": "job_executing",
                "job_id": job_id,
                "workflow_id": job.workflow_name
            })

            # Execute with executor (simplified - would integrate with your actual executor)
            result = await self.executor.start_job(job.workflow_name, job.input_params)

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now().isoformat()
            job.output_data = result

            await self.ws_manager.broadcast({
                "type": "job_completed",
                "job_id": job_id,
                "result": result
            })

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            job = self.active_jobs[job_id]
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now().isoformat()
            job.error_message = str(e)

            await self.ws_manager.broadcast({
                "type": "job_failed",
                "job_id": job_id,
                "error": str(e)
            })


# ============================================================================
# Startup Function
# ============================================================================

def create_ops_console(
    registry: Optional[EnhancedAgentRegistry] = None,
    executor: Optional[JobExecutionEngine] = None
) -> FastAPI:
    """Create and configure Ops Console application."""
    console = OpsConsole(registry=registry, executor=executor)
    return console.app


if __name__ == "__main__":
    import uvicorn
    
    # Create console
    app = create_ops_console()
    
    # Run server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )