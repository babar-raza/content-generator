"""
ARCHIVED: 2025-11-13
Reason: Features consolidated into src/web/app.py
Replacement: Use src/web/app.py which provides all functionality with React UI and MCP protocol
Historical: This file combined job UI with visual orchestration features

Integrated Web App - Combines existing job UI with Visual Orchestration.
"""

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging
import asyncio
from contextlib import asynccontextmanager

# Import unified engine
from src.engine.unified_engine import get_engine, RunSpec, JobStatus
from src.core.template_registry import get_template_registry

# Import visualization components
from src.visualization.workflow_visualizer import WorkflowVisualizer
from src.visualization.agent_flow_monitor import get_flow_monitor
from src.visualization.workflow_debugger import get_workflow_debugger
from src.visualization.monitor import get_monitor

logger = logging.getLogger(__name__)

# Store for jobs (in-memory for now)
jobs_store = {}

# WebSocket connections
websocket_connections: Dict[str, WebSocket] = {}

# Execution engine (optional, set by launcher)
_execution_engine = None
_job_controller = None


def set_execution_engine(execution_engine, job_controller):
    """Set the execution engine and job controller."""
    global _execution_engine, _job_controller
    _execution_engine = execution_engine
    _job_controller = job_controller
    logger.info("Execution engine connected to web app")


def get_execution_engine():
    """Get the execution engine if available."""
    return _execution_engine


def get_job_controller():
    """Get the job controller if available."""
    return _job_controller



class GenerateRequest(BaseModel):
    """Request model for content generation."""
    topic: Optional[str] = None
    template_name: str = "default_blog"
    auto_topic: bool = False
    kb_path: Optional[str] = None
    docs_path: Optional[str] = None
    blog_path: Optional[str] = None
    api_path: Optional[str] = None
    tutorial_path: Optional[str] = None
    output_dir: str = "./output"


class BatchRequest(BaseModel):
    """Request model for batch generation."""
    topics: List[str]
    template_name: str = "default_blog"
    kb_path: Optional[str] = None
    docs_path: Optional[str] = None
    blog_path: Optional[str] = None
    api_path: Optional[str] = None
    tutorial_path: Optional[str] = None
    output_dir: str = "./output"


class StepStatusUpdate(BaseModel):
    status: str
    data: Optional[Dict[str, Any]] = None


class BreakpointRequest(BaseModel):
    agent_id: str
    event_type: str
    condition: Optional[str] = None
    max_hits: Optional[int] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Integrated UCOP Web UI with Visual Orchestration")
    
    # Initialize monitor
    monitor = get_monitor()
    monitor.start_monitoring()
    
    # Initialize flow monitor
    flow_monitor = get_flow_monitor()
    flow_monitor.start_monitoring()
    
    logger.info("Visual Orchestration System initialized")
    
    yield
    
    # Shutdown
    monitor.stop_monitoring()
    flow_monitor.stop_monitoring()
    logger.info("Application stopped")


app = FastAPI(title="UCOP Integrated Web UI", lifespan=lifespan)

# Templates directory
templates = Jinja2Templates(directory="src/web/templates")

# Initialize visualization components
try:
    workflow_visualizer = WorkflowVisualizer(workflow_dir='./templates')
except Exception as e:
    logger.warning(f"Could not initialize workflow visualizer: {e}")
    workflow_visualizer = None

try:
    workflow_debugger = get_workflow_debugger()
except Exception as e:
    logger.warning(f"Could not initialize workflow debugger: {e}")
    workflow_debugger = None


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main integrated dashboard."""
    # Get available templates
    registry = get_template_registry()
    templates_list = registry.list_templates()
    
    return templates.TemplateResponse("dashboard_integrated.html", {
        "request": request,
        "templates": [{"name": t.name, "type": t.type.value} for t in templates_list]
    })


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail_page(request: Request, job_id: str):
    """Enhanced job detail page."""
    return templates.TemplateResponse("job_detail_enhanced.html", {
        "request": request,
        "job_id": job_id
    })


# ======================
# Existing Job Endpoints
# ======================

@app.get("/api/templates")
async def get_templates(template_type: Optional[str] = None):
    """Get available templates."""
    registry = get_template_registry()
    templates_list = registry.list_templates(template_type)
    
    return {
        "templates": [
            {
                "name": t.name,
                "type": t.type.value,
                "required_placeholders": t.schema.required_placeholders,
                "optional_placeholders": t.schema.optional_placeholders,
                "metadata": t.metadata
            }
            for t in templates_list
        ]
    }


@app.post("/api/generate")
async def generate_content(req: GenerateRequest):
    """Generate content using unified engine."""
    
    logger.info("="*80)
    logger.info("Received job request via API")
    logger.info(f"  Template: {req.template_name}")
    logger.info(f"  Topic: {req.topic or '(auto-generate)'}")
    logger.info(f"  Auto-topic: {req.auto_topic}")
    logger.info(f"  KB path: {req.kb_path or 'None'}")
    logger.info(f"  Docs path: {req.docs_path or 'None'}")
    logger.info(f"  Blog path: {req.blog_path or 'None'}")
    logger.info(f"  API path: {req.api_path or 'None'}")
    logger.info(f"  Tutorial path: {req.tutorial_path or 'None'}")
    logger.info(f"  Output dir: {req.output_dir}")
    
    # Check if we have an execution engine
    execution_engine = get_execution_engine()
    
    if execution_engine:
        # Use execution engine for job submission
        logger.info("Using job execution engine for submission")
        
        # Prepare input parameters
        input_params = {
            "topic": req.topic or "auto-generated",
            "template_name": req.template_name,
            "auto_topic": req.auto_topic,
            "kb_path": req.kb_path,
            "docs_path": req.docs_path,
            "blog_path": req.blog_path,
            "api_path": req.api_path,
            "tutorial_path": req.tutorial_path,
            "output_dir": str(req.output_dir)
        }
        
        # Submit job to execution engine
        try:
            job_id = execution_engine.submit_job(
                workflow_name=req.template_name,
                input_params=input_params
            )
            
            logger.info(f"Job submitted successfully: {job_id}")
            
            # Wait briefly for initial status
            import asyncio
            await asyncio.sleep(0.5)
            
            # Get job status
            job = execution_engine.get_job(job_id) if hasattr(execution_engine, 'get_job') else None
            
            if job:
                # Broadcast update to WebSocket clients
                await broadcast_job_update(job_id, {
                    "type": "job_started",
                    "job_id": job_id,
                    "status": job.status.value if hasattr(job.status, 'value') else "running"
                })
                
                return {
                    "job_id": job_id,
                    "status": job.status.value if hasattr(job.status, 'value') else "running",
                    "message": "Job submitted successfully",
                    "progress": job.progress,
                    "current_step": job.current_step
                }
            else:
                return {
                    "job_id": job_id,
                    "status": "submitted",
                    "message": "Job submitted for processing"
                }
                
        except Exception as e:
            logger.error(f"Failed to submit job: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Job submission failed: {str(e)}")
    
    else:
        # Fallback to direct engine execution
        logger.info("Using unified engine for direct execution")
        
        # Build run spec
        run_spec = RunSpec(
            topic=req.topic,
            template_name=req.template_name,
            auto_topic=req.auto_topic,
            kb_path=req.kb_path,
            docs_path=req.docs_path,
            blog_path=req.blog_path,
            api_path=req.api_path,
            tutorial_path=req.tutorial_path,
            output_dir=Path(req.output_dir)
        )
        
        try:
            # Get engine and execute
            engine = get_engine()
            logger.info("Starting job execution...")
            
            # Start monitoring this job
            flow_monitor = get_flow_monitor()
            correlation_id = f"job_{run_spec.topic or 'auto'}_{len(jobs_store)}"
            
            result = engine.generate_job(run_spec)
            
            logger.info(f"Job execution completed: {result.status.value}")
            
            # Store job
            jobs_store[result.job_id] = result
            logger.info(f"Job stored in jobs_store: {result.job_id}")
            
            # Broadcast update to WebSocket clients
            await broadcast_job_update(result.job_id, {
                "type": "job_completed",
                "job_id": result.job_id,
                "status": result.status.value
            })
            
            # Return result
            return {
                "job_id": result.job_id,
                "status": result.status.value,
                "output_path": str(result.output_path) if result.output_path else None,
                "manifest_path": str(result.manifest_path) if result.manifest_path else None,
                "error": result.error,
                "duration": result.duration,
                "pipeline_order": result.pipeline_order
            }
            
        except Exception as e:
            logger.error(f"Job execution failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Job execution failed: {str(e)}")


@app.post("/api/batch")
async def batch_generate(req: BatchRequest):
    """Execute batch job with multiple topics."""
    
    batch_id = f"batch_{len(jobs_store)}"
    batch_results = []
    
    engine = get_engine()
    
    for topic in req.topics:
        run_spec = RunSpec(
            topic=topic,
            template_name=req.template_name,
            kb_path=req.kb_path,
            docs_path=req.docs_path,
            blog_path=req.blog_path,
            api_path=req.api_path,
            tutorial_path=req.tutorial_path,
            output_dir=Path(req.output_dir)
        )
        
        result = engine.generate_job(run_spec)
        jobs_store[result.job_id] = result
        
        batch_results.append({
            "job_id": result.job_id,
            "topic": topic,
            "status": result.status.value,
            "output_path": str(result.output_path) if result.output_path else None
        })
    
    return {
        "batch_id": batch_id,
        "total": len(req.topics),
        "results": batch_results
    }


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs."""
    
    return {
        "jobs": [
            {
                "job_id": job.job_id,
                "status": job.status.value,
                "template": job.run_spec.template_name,
                "topic": job.run_spec.topic,
                "duration": job.duration,
                "output_path": str(job.output_path) if job.output_path else None
            }
            for job in jobs_store.values()
        ]
    }


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job details."""
    
    # First check if we're using the execution engine
    execution_engine = get_execution_engine()
    if execution_engine:
        # Try to get job from execution engine
        if hasattr(execution_engine, 'get_job'):
            job = execution_engine.get_job(job_id)
            if job:
                # Convert to response format
                return {
                    "job_id": job.job_id,
                    "workflow_name": job.workflow_name,
                    "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
                    "started_at": job.started_at,
                    "completed_at": job.completed_at,
                    "current_step": job.current_step,
                    "progress": job.progress,
                    "input_params": job.input_params,
                    "output_data": job.output_data,
                    "error_message": job.error_message,
                    "error_details": getattr(job, 'error_details', None),
                    "metadata": job.metadata,
                    "logs": getattr(job, 'logs', [])
                }
    
    # Fallback to jobs_store
    if job_id not in jobs_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = jobs_store[job_id]
    
    return {
        "job_id": result.job_id,
        "status": result.status.value,
        "run_spec": result.run_spec.to_dict() if hasattr(result, 'run_spec') else {},
        "output_path": str(result.output_path) if hasattr(result, 'output_path') and result.output_path else None,
        "manifest_path": str(result.manifest_path) if hasattr(result, 'manifest_path') and result.manifest_path else None,
        "pipeline_order": getattr(result, 'pipeline_order', []),
        "sources_used": getattr(result, 'sources_used', []),
        "duration": getattr(result, 'duration', 0),
        "error": getattr(result, 'error', None)
    }


@app.get("/api/jobs/{job_id}/logs")
async def get_job_logs(job_id: str):
    """Get job execution logs."""
    
    # Try execution engine first
    execution_engine = get_execution_engine()
    if execution_engine:
        if hasattr(execution_engine, 'get_job_logs'):
            logs = execution_engine.get_job_logs(job_id)
            if logs:
                return {"job_id": job_id, "logs": logs, "format": "text"}
        
        # Try to get job and return in-memory logs
        if hasattr(execution_engine, 'get_job'):
            job = execution_engine.get_job(job_id)
            if job and hasattr(job, 'logs'):
                return {"job_id": job_id, "logs": job.logs, "format": "json"}
    
    # Try to read log file directly
    log_file = Path(f"./data/jobs/{job_id}/logs/job.log")
    if log_file.exists():
        logs = log_file.read_text()
        return {"job_id": job_id, "logs": logs, "format": "text"}
    
    raise HTTPException(status_code=404, detail="Job logs not found")


@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get quick job status."""
    
    execution_engine = get_execution_engine()
    if execution_engine and hasattr(execution_engine, 'get_job'):
        job = execution_engine.get_job(job_id)
        if job:
            return {
                "job_id": job.job_id,
                "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
                "progress": job.progress,
                "current_step": job.current_step,
                "error_message": job.error_message
            }
    
    if job_id in jobs_store:
        result = jobs_store[job_id]
        return {
            "job_id": result.job_id,
            "status": result.status.value if hasattr(result.status, 'value') else "unknown",
            "progress": 100.0 if result.status.value == "completed" else 0.0
        }
    
    raise HTTPException(status_code=404, detail="Job not found")


@app.get("/api/jobs/{job_id}/logs/{agent_name}")
async def get_agent_log(job_id: str, agent_name: str):
    """Get agent step log."""
    
    if job_id not in jobs_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = jobs_store[job_id]
    
    # Find agent log
    agent_log = next((log for log in result.agent_logs if log.agent_name == agent_name), None)
    
    if not agent_log:
        raise HTTPException(status_code=404, detail="Agent log not found")
    
    return agent_log.to_dict()


@app.get("/api/agents/{agent_id}/logs")
async def get_agent_logs(agent_id: str):
    """Get agent input/output JSON with secret redaction."""
    
    # Parse agent_id which should be job_id-agent_name format
    parts = agent_id.split('-', 1)
    if len(parts) < 2:
        # Try to find in all jobs
        for job_id, result in jobs_store.items():
            agent_log = next((log for log in result.agent_logs if log.agent_name == agent_id), None)
            if agent_log:
                break
        else:
            raise HTTPException(status_code=404, detail="Agent not found")
    else:
        job_id = parts[0]
        agent_name = parts[1] if len(parts) > 1 else agent_id
        
        if job_id not in jobs_store:
            raise HTTPException(status_code=404, detail="Job not found")
        
        result = jobs_store[job_id]
        agent_log = next((log for log in result.agent_logs if log.agent_name == agent_name), None)
        
        if not agent_log:
            raise HTTPException(status_code=404, detail="Agent not found")
    
    # Redact secrets
    input_data = redact_secrets(agent_log.input_data)
    output_data = redact_secrets(agent_log.output_data)
    
    return {
        "agent_name": agent_log.agent_name,
        "input": input_data,
        "output": output_data,
        "status": getattr(agent_log, 'status', 'unknown'),
        "duration": f"{agent_log.end_time - agent_log.start_time:.2f}s" if agent_log.end_time > 0 else None
    }


# ======================
# Visual Orchestration Endpoints
# ======================

@app.get("/api/workflows/profiles")
async def list_workflow_profiles():
    """List available workflow profiles."""
    if not workflow_visualizer:
        return {"profiles": []}
    
    profiles = workflow_visualizer.workflows.get('profiles', {})
    return {
        "profiles": [
            {
                "id": profile_id,
                "name": profile_data.get('name', profile_id),
                "description": profile_data.get('description', ''),
                "steps": len(profile_data.get('steps', []))
            }
            for profile_id, profile_data in profiles.items()
        ]
    }


@app.get("/api/workflows/visual/{profile_name}")
async def get_visual_workflow(profile_name: str):
    """Get visual workflow graph for React Flow."""
    if not workflow_visualizer:
        raise HTTPException(status_code=503, detail="Workflow visualizer not available")
    
    try:
        graph = workflow_visualizer.create_visual_graph(profile_name)
        return graph
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/api/workflows/visual/{profile_name}/step/{step_id}/status")
async def update_step_status(
    profile_name: str,
    step_id: str,
    update: StepStatusUpdate
):
    """Update step status and broadcast to WebSocket clients."""
    if not workflow_visualizer:
        raise HTTPException(status_code=503, detail="Workflow visualizer not available")
    
    try:
        workflow_visualizer.update_step_status(
            profile_name,
            step_id,
            update.status,
            update.data
        )
        
        # Broadcast update to WebSocket clients
        await broadcast_workflow_update(
            profile_name,
            step_id,
            update.status,
            update.data
        )
        
        return {"success": True, "profile": profile_name, "step": step_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flows/realtime")
async def get_realtime_flows():
    """Get real-time flow state."""
    flow_monitor = get_flow_monitor()
    state = flow_monitor.get_real_time_state()
    
    return {
        "flows": state.get('active_flows', [])
    }


@app.get("/api/flows/history/{correlation_id}")
async def get_flow_history(correlation_id: str):
    """Get flow history for a correlation ID."""
    flow_monitor = get_flow_monitor()
    history = flow_monitor.get_flow_history(correlation_id)
    
    return {
        "correlation_id": correlation_id,
        "flows": history
    }


@app.get("/api/flows/bottlenecks")
async def get_bottlenecks():
    """Get detected bottlenecks."""
    flow_monitor = get_flow_monitor()
    bottlenecks = flow_monitor.detect_bottlenecks()
    
    return {"bottlenecks": bottlenecks}


# Debugging endpoints
@app.post("/api/debug/sessions")
async def create_debug_session(correlation_id: str):
    """Create a new debug session."""
    if not workflow_debugger:
        raise HTTPException(status_code=503, detail="Debugger not available")
    
    session_id = workflow_debugger.start_debug_session(correlation_id)
    return {"session_id": session_id, "correlation_id": correlation_id}


@app.post("/api/debug/sessions/{session_id}/breakpoints")
async def add_breakpoint(session_id: str, breakpoint: BreakpointRequest):
    """Add a breakpoint to a debug session."""
    if not workflow_debugger:
        raise HTTPException(status_code=503, detail="Debugger not available")
    
    workflow_debugger.add_breakpoint(
        session_id,
        breakpoint.agent_id,
        breakpoint.event_type,
        breakpoint.condition,
        breakpoint.max_hits
    )
    
    return {"success": True, "session_id": session_id}


@app.get("/api/debug/workflows/{correlation_id}/trace")
async def get_execution_trace(correlation_id: str):
    """Get execution trace for a workflow."""
    if not workflow_debugger:
        raise HTTPException(status_code=503, detail="Debugger not available")
    
    trace = workflow_debugger.get_execution_trace(correlation_id)
    return {"correlation_id": correlation_id, "trace": trace}


# WebSocket endpoint for real-time updates
@app.websocket("/ws/workflow-updates")
async def workflow_updates_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time workflow updates."""
    await websocket.accept()
    connection_id = str(len(websocket_connections))
    websocket_connections[connection_id] = websocket
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            # Echo back or process client messages if needed
    except WebSocketDisconnect:
        del websocket_connections[connection_id]


async def broadcast_workflow_update(profile_name: str, step_id: str, status: str, data: Optional[Dict] = None):
    """Broadcast workflow update to all connected clients."""
    message = {
        "type": "step_update",
        "profile": profile_name,
        "step": step_id,
        "status": status,
        "data": data or {}
    }
    
    disconnected = []
    for connection_id, websocket in websocket_connections.items():
        try:
            await websocket.send_json(message)
        except:
            disconnected.append(connection_id)
    
    # Clean up disconnected clients
    for connection_id in disconnected:
        del websocket_connections[connection_id]


async def broadcast_job_update(job_id: str, data: Dict):
    """Broadcast job update to all connected clients."""
    message = {
        "type": "job_update",
        "job_id": job_id,
        **data
    }
    
    disconnected = []
    for connection_id, websocket in websocket_connections.items():
        try:
            await websocket.send_json(message)
        except:
            disconnected.append(connection_id)
    
    # Clean up disconnected clients
    for connection_id in disconnected:
        del websocket_connections[connection_id]


def redact_secrets(data: dict) -> dict:
    """Redact sensitive fields from data."""
    if not isinstance(data, dict):
        return data
    
    sensitive_keys = ['api_key', 'token', 'password', 'secret', 'key', 'auth']
    redacted = {}
    
    for key, value in data.items():
        if any(s in key.lower() for s in sensitive_keys):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_secrets(value)
        elif isinstance(value, list):
            redacted[key] = [redact_secrets(item) if isinstance(item, dict) else item for item in value]
        else:
            redacted[key] = value
    
    return redacted


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
