"""UCOP Web Application - Integrated with Job Execution Engine."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, File, UploadFile, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from pathlib import Path
import logging
import uuid
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
import shutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.orchestration.job_execution_engine import JobExecutionEngine, JobStatus
from src.realtime.websocket import get_ws_manager, EventType, CommandType
from src.realtime.job_control import JobController

logger = logging.getLogger(__name__)

# Pydantic models for API requests
class JobCreateRequest(BaseModel):
    template_name: str
    workflow: str
    topic: Optional[str] = None
    auto_topic: bool = False
    output_dir: str = './output'
    kb_path: Optional[str] = None
    docs_path: Optional[str] = None
    blog_path: Optional[str] = None
    api_path: Optional[str] = None
    tutorial_path: Optional[str] = None

# Initialize FastAPI app
app = FastAPI(title="UCOP Dashboard")

# Setup templates and static files
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Global references - will be set by start_web_server()
execution_engine: Optional[JobExecutionEngine] = None
job_controller: Optional[JobController] = None
ws_manager = get_ws_manager()


def set_execution_engine(engine: JobExecutionEngine, controller: JobController):
    """Set the job execution engine (called from main)."""
    global execution_engine, job_controller
    execution_engine = engine
    job_controller = controller
    logger.info("Web UI connected to job execution engine")


# ============================================================================
# Web Pages
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/test", response_class=HTMLResponse)
async def test_page(request: Request):
    """Test page to verify server is working."""
    return templates.TemplateResponse("test.html", {"request": request})


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail(request: Request, job_id: str):
    """Job detail page with controls."""
    return templates.TemplateResponse("job_detail.html", {
        "request": request,
        "job_id": job_id
    })


@app.get("/api/jobs/{job_id}/logs/stream")
async def stream_logs(job_id: str):
    """Stream job logs via Server-Sent Events."""
    from fastapi.responses import StreamingResponse
    import asyncio
    
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    job = execution_engine._jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    log_file = Path(f"./data/jobs/{job_id}/logs/job.log")
    
    async def event_generator():
        """Generate SSE events from log file."""
        last_position = 0
        
        while True:
            try:
                if log_file.exists():
                    with open(log_file, 'r') as f:
                        f.seek(last_position)
                        new_content = f.read()
                        
                        if new_content:
                            for line in new_content.split('\n'):
                                if line.strip():
                                    yield f"data: {line}\n\n"
                            last_position = f.tell()
                
                # Check if job is still running
                current_job = execution_engine._jobs.get(job_id)
                if current_job and current_job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    # Send final heartbeat and close
                    yield f"data: [LOG_STREAM_CLOSED]\n\n"
                    break
                
                # Heartbeat
                yield f": heartbeat\n\n"
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error streaming logs: {e}")
                yield f"data: [ERROR: {str(e)}]\n\n"
                break
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/jobs/{job_id}/logs")
async def get_logs(job_id: str):
    """Get full job logs."""
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    job = execution_engine._jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    log_file = Path(f"./data/jobs/{job_id}/logs/job.log")
    if not log_file.exists():
        return {"logs": ""}
    
    try:
        with open(log_file, 'r') as f:
            logs = f.read()
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {e}")


@app.get("/api/jobs/{job_id}/agents/{agent_id}/output")
async def get_agent_output(job_id: str, agent_id: str):
    """Get agent input and output data."""
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    job = execution_engine._jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get output from job.output_data
    output = job.output_data.get(agent_id)
    
    # Try to get input from workflow state if available
    agent_input = None
    if job.state and hasattr(job.state, 'step_inputs'):
        agent_input = job.state.step_inputs.get(agent_id)
    
    # If no input in state, try to infer from job input_params
    if not agent_input:
        agent_input = {
            "topic": job.input_params.get("topic"),
            "kb_path": job.input_params.get("kb_path"),
            "output_dir": job.input_params.get("output_dir"),
            "note": "Input reconstructed from job parameters"
        }
    
    if output:
        return {
            "agent_id": agent_id,
            "job_id": job_id,
            "input": agent_input,
            "output": output,
            "timestamp": output.get("timestamp") if isinstance(output, dict) else None
        }
    
    raise HTTPException(status_code=404, detail=f"No output found for agent {agent_id}")


@app.get("/api/jobs/{job_id}/agent_runs")
async def get_agent_runs(job_id: str):
    """Get all agent runs for a job."""
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    agent_runs_path = Path(f"./data/jobs/{job_id}/agent_runs.json")
    
    if not agent_runs_path.exists():
        return {"agent_runs": [], "summary": {}}
    
    try:
        with open(agent_runs_path) as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read agent runs: {e}")


@app.get("/api/jobs/{job_id}/agent_runs/download")
async def download_agent_runs(job_id: str):
    """Download agent runs as JSON."""
    from fastapi.responses import FileResponse
    
    agent_runs_path = Path(f"./data/jobs/{job_id}/agent_runs.json")
    
    if not agent_runs_path.exists():
        raise HTTPException(status_code=404, detail="Agent runs not found")
    
    return FileResponse(
        agent_runs_path,
        media_type="application/json",
        filename=f"agent_runs_{job_id}.json"
    )


@app.get("/api/jobs/{job_id}/report")
async def get_job_report(job_id: str):
    """Get job execution report."""
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    report_path = Path(f"./data/jobs/{job_id}/report.json")
    
    if not report_path.exists():
        return {"error": "Report not found", "job_id": job_id}
    
    try:
        with open(report_path) as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report: {e}")


# ============================================================================
# REST API - Jobs
# ============================================================================

@app.get("/api/jobs")
async def list_jobs():
    """List all jobs."""
    if not execution_engine:
        return {"jobs": [], "total": 0}
    
    jobs = []
    for job_id, job in execution_engine._jobs.items():
        job_dict = job.to_dict()
        # Add pipeline info from workflow state
        if job.state and hasattr(job.state, 'workflow_def'):
            workflow_def = job.state.workflow_def
            pipeline = []
            for step_id, step in workflow_def.steps.items():
                pipeline.append({
                    "id": step_id,
                    "name": step.get("name", step_id),
                    "status": job.state.step_status.get(step_id, "pending"),
                    "agent": step.get("agent")
                })
            job_dict["pipeline"] = pipeline
        jobs.append(job_dict)
    
    return {"jobs": jobs, "total": len(jobs)}


@app.post("/api/jobs")
async def create_job(
    template_name: str = Form(...),
    workflow: str = Form(...),
    topic: str = Form(""),
    auto_topic: bool = Form(False),
    output_dir: str = Form('./output'),
    kb_path: Optional[str] = Form(None),
    docs_path: Optional[str] = Form(None),
    blog_path: Optional[str] = Form(None),
    api_path: Optional[str] = Form(None),
    tutorial_path: Optional[str] = Form(None),
    kb_files: List[UploadFile] = File(default=[]),
    docs_files: List[UploadFile] = File(default=[]),
    blog_files: List[UploadFile] = File(default=[]),
    api_files: List[UploadFile] = File(default=[]),
    tutorial_files: List[UploadFile] = File(default=[])
):
    """Create a new job from web UI with file upload support."""
    
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not available")
    
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create uploads directory for this job if files are uploaded
        uploads_dir = Path(f"./data/jobs/{job_id}/uploads")
        uploaded_paths = {
            'kb': [],
            'docs': [],
            'blog': [],
            'api': [],
            'tutorial': []
        }
        
        # Process uploaded files
        for file_list, key in [
            (kb_files, 'kb'),
            (docs_files, 'docs'),
            (blog_files, 'blog'),
            (api_files, 'api'),
            (tutorial_files, 'tutorial')
        ]:
            for file in file_list:
                if file.filename:
                    file_path = uploads_dir / key / file.filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'wb') as f:
                        shutil.copyfileobj(file.file, f)
                    uploaded_paths[key].append(str(file_path))
        
        # Build input parameters
        input_params = {
            "topic": topic or None,
            "output_dir": output_dir,
            "template": template_name
        }
        
        # Add uploaded files if any - and map to path parameters
        if any(uploaded_paths.values()):
            input_params["uploaded_files"] = uploaded_paths
            # Map uploaded file directories to path parameters
            if uploaded_paths['kb']:
                input_params["kb_path"] = str(uploads_dir / "kb")
            if uploaded_paths['docs']:
                input_params["docs_path"] = str(uploads_dir / "docs")
            if uploaded_paths['blog']:
                input_params["blog_path"] = str(uploads_dir / "blog")
            if uploaded_paths['api']:
                input_params["api_path"] = str(uploads_dir / "api")
            if uploaded_paths['tutorial']:
                input_params["tutorial_path"] = str(uploads_dir / "tutorial")
        
        # Add path-based context sources (these override uploaded paths if specified)
        if kb_path:
            input_params["kb_path"] = kb_path
        if docs_path:
            input_params["docs_path"] = docs_path
        if blog_path:
            input_params["blog_path"] = blog_path
        if api_path:
            input_params["api_path"] = api_path
        if tutorial_path:
            input_params["tutorial_path"] = tutorial_path
        
        # Submit job
        execution_engine.submit_job(
            workflow_name=workflow,
            input_params=input_params,
            job_id=job_id
        )
        
        total_files = sum(len(v) for v in uploaded_paths.values())
        logger.info(f"Created job {job_id} via web UI with {total_files} uploaded files")
        
        return {"status": "created", "job_id": job_id}
    
    except Exception as e:
        logger.error(f"Failed to create job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/create")
async def create_job_alias(data: Dict[str, Any]):
    """Create job from JSON data (CLI compatibility)."""
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Extract parameters from JSON
        workflow = data.get("workflow")
        topic = data.get("topic")
        output_dir = data.get("output_dir", "./output")
        kb_path = data.get("kb_path")
        docs_path = data.get("docs_path")
        blog_path = data.get("blog_path")
        api_path = data.get("api_path")
        tutorial_path = data.get("tutorial_path")
        template_name = data.get("template", "default")
        
        if not workflow:
            raise HTTPException(status_code=400, detail="workflow is required")
        
        # Build input parameters
        input_params = {
            "topic": topic,
            "output_dir": output_dir,
            "template": template_name
        }
        
        # Add path-based context sources
        if kb_path:
            input_params["kb_path"] = kb_path
        if docs_path:
            input_params["docs_path"] = docs_path
        if blog_path:
            input_params["blog_path"] = blog_path
        if api_path:
            input_params["api_path"] = api_path
        if tutorial_path:
            input_params["tutorial_path"] = tutorial_path
        
        # Submit job
        execution_engine.submit_job(
            workflow_name=workflow,
            input_params=input_params,
            job_id=job_id
        )
        
        logger.info(f"Created job {job_id} via API")
        
        return {"status": "created", "job_id": job_id}
    
    except Exception as e:
        logger.error(f"Failed to create job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job details."""
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    job = execution_engine._jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_dict = job.to_dict()
    
    # Get pipeline from metadata first (if available), or build from workflow state
    if job.metadata and "pipeline" in job.metadata:
        job_dict["pipeline"] = job.metadata["pipeline"]
    elif job.state and hasattr(job.state, 'workflow_def'):
        workflow_def = job.state.workflow_def
        pipeline = []
        for step_id, step in workflow_def.steps.items():
            status = job.state.step_status.get(step_id, "pending")
            pipeline.append({
                "id": step_id,
                "name": step.get("name", step_id),
                "status": status,
                "agent": step.get("agent"),
                "output": job.state.step_outputs.get(step_id) if status == "completed" else None
            })
        job_dict["pipeline"] = pipeline
    else:
        # Load default pipeline from workflow if available
        workflow_def = execution_engine.workflow_compiler.workflows.get(job.workflow_name)
        if workflow_def:
            steps = workflow_def.get('steps', {})
            pipeline = []
            for step_id, step_config in steps.items():
                # Check if this step has output data
                status = "completed" if step_id in job.output_data else "pending"
                pipeline.append({
                    "id": step_id,
                    "name": step_config.get("name", step_id),
                    "agent": step_config.get("agent", step_id),
                    "status": status
                })
            job_dict["pipeline"] = pipeline
        else:
            job_dict["pipeline"] = []
        
    # Build agent execution details from output_data and pipeline
    agents = []
    for step_id, output in job.output_data.items():
        if isinstance(output, dict):
            agent_info = {
                "id": step_id,
                "name": output.get("agent", step_id),
                "status": output.get("status", "completed"),
                "started_at": output.get("timestamp"),
                "duration": None,  # TODO: calculate
                "last_output": f"{len(str(output))} bytes",
                "output_size": len(str(output))
            }
            agents.append(agent_info)
    job_dict["agents"] = agents
    
    return job_dict


@app.get("/api/jobs/{job_id}/artifacts")
async def get_job_artifacts(job_id: str):
    """Get list of artifacts for a job."""
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    job = execution_engine._jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get artifacts directory
    artifacts_dir = Path(f"./data/jobs/{job_id}/artifacts")
    if not artifacts_dir.exists():
        return {"artifacts": []}
    
    artifacts = []
    for artifact_file in artifacts_dir.iterdir():
        if artifact_file.is_file():
            stat = artifact_file.stat()
            artifacts.append({
                "name": artifact_file.name,
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "download_url": f"/api/jobs/{job_id}/artifacts/{artifact_file.name}"
            })
    
    return {"artifacts": artifacts}


@app.get("/api/jobs/{job_id}/artifacts/{filename}")
async def download_artifact(job_id: str, filename: str):
    """Download a specific artifact."""
    from fastapi.responses import FileResponse
    
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    job = execution_engine._jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    artifact_file = Path(f"./data/jobs/{job_id}/artifacts/{filename}")
    if not artifact_file.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    return FileResponse(artifact_file, filename=filename)


@app.post("/api/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    """Pause a running job."""
    if not job_controller:
        raise HTTPException(status_code=503, detail="Job controller not initialized")
    
    try:
        job_controller.pause_job(job_id)
        await ws_manager.broadcast(job_id, EventType.RUN_PAUSED, {})
        return {"status": "paused", "job_id": job_id}
    except Exception as e:
        logger.error(f"Failed to pause job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/{job_id}/resume")
async def resume_job(job_id: str, data: Optional[Dict[str, Any]] = None):
    """Resume a paused job."""
    if not job_controller:
        raise HTTPException(status_code=503, detail="Job controller not initialized")
    
    try:
        params = data.get("params") if data else None
        job_controller.resume_job(job_id, params)
        await ws_manager.broadcast(job_id, EventType.RUN_RESUMED, {})
        return {"status": "running", "job_id": job_id}
    except Exception as e:
        logger.error(f"Failed to resume job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/{job_id}/step")
async def step_job(job_id: str, data: Dict[str, Any]):
    """Step job execution (debugger-style)."""
    if not job_controller:
        raise HTTPException(status_code=503, detail="Job controller not initialized")
    
    try:
        mode = data.get("mode", "into")  # into, over, out
        job_controller.step_job(job_id, mode)
        
        await ws_manager.broadcast(job_id, EventType.NODE_STDOUT, {
            "message": f"Step {mode} executed"
        })
        return {"status": "stepped", "mode": mode}
    except Exception as e:
        logger.error(f"Failed to step job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a job."""
    if not job_controller:
        raise HTTPException(status_code=503, detail="Job controller not initialized")
    
    try:
        job_controller.cancel_job(job_id)
        await ws_manager.broadcast(job_id, EventType.RUN_FINISHED, {"status": "cancelled"})
        return {"status": "cancelled", "job_id": job_id}
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/batch")
async def create_batch_jobs(data: Dict[str, Any]):
    """Submit a batch of jobs."""
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    try:
        batch_config = data.get("jobs", [])
        batch_group_id = data.get("batch_group_id")
        
        if not batch_config:
            raise HTTPException(status_code=400, detail="No jobs specified")
        
        job_ids = execution_engine.submit_batch(batch_config, batch_group_id)
        
        # Start all jobs
        for job_id in job_ids:
            execution_engine.start_job(job_id)
        
        return {
            "batch_group_id": execution_engine._jobs[job_ids[0]].batch_group_id,
            "job_ids": job_ids,
            "total_jobs": len(job_ids),
            "status": "submitted"
        }
    
    except Exception as e:
        logger.error(f"Failed to create batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/batch/{batch_group_id}")
async def get_batch_status(batch_group_id: str):
    """Get status of a batch of jobs."""
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    try:
        return execution_engine.get_batch_status(batch_group_id)
    except Exception as e:
        logger.error(f"Failed to get batch status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# REST API - Pipeline Editing
# ============================================================================

@app.post("/api/jobs/{job_id}/pipeline/add")
async def add_agent_to_pipeline(job_id: str, data: Dict[str, Any]):
    """Add agent to pipeline (in-memory for pending jobs, saved for new jobs)."""
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    job = execution_engine._jobs.get(job_id)
    if not job:
        # For new job creation, just return success - pipeline will be saved on submit
        return {"status": "success", "message": "Agent will be added on job creation"}
    
    try:
        agent_id = data.get("agent_id")
        agent_name = data.get("agent_name", agent_id)
        insert_after = data.get("insert_after")
        
        # Update pipeline in job metadata
        if "pipeline" not in job.metadata:
            job.metadata["pipeline"] = []
        
        # Find insertion point
        pipeline = job.metadata["pipeline"]
        insert_index = len(pipeline)  # Default to end
        
        if insert_after:
            for idx, step in enumerate(pipeline):
                if step["id"] == insert_after:
                    insert_index = idx + 1
                    break
        
        # Insert new agent
        new_step = {
            "id": agent_id,
            "name": agent_name,
            "agent": agent_id,
            "status": "pending"
        }
        pipeline.insert(insert_index, new_step)
        
        # Persist changes
        execution_engine._persist_job(job)
        
        await ws_manager.broadcast(job_id, EventType.NODE_STDOUT, {
            "message": f"Agent {agent_name} added to pipeline"
        })
        
        return {"status": "success", "pipeline": pipeline}
    
    except Exception as e:
        logger.error(f"Failed to add agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/{job_id}/pipeline/save")
async def save_pipeline(job_id: str, data: Dict[str, Any]):
    """Save pipeline configuration."""
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    job = execution_engine._jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        pipeline = data.get("pipeline", [])
        job.metadata["pipeline"] = pipeline
        execution_engine._persist_job(job)
        
        return {"status": "success", "message": "Pipeline saved"}
    except Exception as e:
        logger.error(f"Failed to save pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/{job_id}/pipeline/insert")
async def insert_agent(job_id: str, data: Dict[str, Any]):
    """Insert agent into pipeline."""
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    job = execution_engine._jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        insert_after = data.get("insert_after")
        agent_type = data.get("agent_type")
        params = data.get("params", {})
        
        # TODO: Implement dynamic pipeline modification
        # This would require enhancing the workflow state to support runtime changes
        
        await ws_manager.broadcast(job_id, EventType.NODE_STDOUT, {
            "message": f"Agent {agent_type} insertion requested (not yet implemented)"
        })
        
        return {"status": "pending", "message": "Pipeline modification coming soon"}
    
    except Exception as e:
        logger.error(f"Failed to insert agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/{job_id}/pipeline/remove")
async def remove_agent(job_id: str, data: Dict[str, Any]):
    """Remove agent from pipeline."""
    if not execution_engine:
        raise HTTPException(status_code=503, detail="Job execution engine not initialized")
    
    job = execution_engine._jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        agent_id = data.get("agent_id")
        
        # TODO: Implement dynamic pipeline modification
        
        await ws_manager.broadcast(job_id, EventType.NODE_STDOUT, {
            "message": f"Agent {agent_id} removal requested (not yet implemented)"
        })
        
        return {"status": "pending", "message": "Pipeline modification coming soon"}
    
    except Exception as e:
        logger.error(f"Failed to remove agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# REST API - Agents
# ============================================================================

@app.get("/api/agents")
async def list_agents():
    """List all registered agents from the agents directory."""
    agents_dir = Path(__file__).parent.parent / "agents"
    discovered_agents = []
    
    # Scan agents directory for all agent files
    agent_categories = {
        "research": ["topic_identification", "kb_search", "api_search", "blog_search", "duplication_check"],
        "ingestion": ["kb_ingestion", "api_ingestion", "blog_ingestion"],
        "content": ["outline_creation", "introduction_writer", "section_writer", "conclusion_writer", 
                   "supplementary_content", "content_assembly"],
        "seo": ["keyword_extraction", "keyword_injection", "seo_metadata"],
        "code": ["code_extraction", "code_generation", "code_validation", "code_splitting", "license_injection"],
        "publishing": ["file_writer", "frontmatter", "gist_readme", "gist_upload", "link_validation"],
        "support": ["model_selection", "error_recovery"]
    }
    
    for category, agent_names in agent_categories.items():
        category_dir = agents_dir / category
        if category_dir.exists():
            for agent_name in agent_names:
                agent_file = category_dir / f"{agent_name}.py"
                if agent_file.exists():
                    # Create agent entry
                    display_name = agent_name.replace("_", " ").title()
                    discovered_agents.append({
                        "name": display_name,
                        "type": category,
                        "id": agent_name,
                        "category": category,
                        "status": "idle"
                    })
    
    return discovered_agents


# ============================================================================
# WebSocket - Real-time updates
# ============================================================================

@app.websocket("/ws/mesh")
async def websocket_endpoint(websocket: WebSocket, job: str):
    """WebSocket for real-time job updates."""
    await websocket.accept()
    await ws_manager.connect(websocket, job)
    
    logger.info(f"WebSocket connected for job {job}")
    
    try:
        while True:
            # Receive commands from client
            data = await websocket.receive_json()
            logger.info(f"WebSocket command: {data}")
            
            # Handle command
            result = await ws_manager.handle_command(job, data)
            
            # Send response
            await websocket.send_json({
                "type": "COMMAND_RESPONSE",
                "timestamp": datetime.now().isoformat(),
                "data": result
            })
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, job)
        logger.info(f"WebSocket disconnected for job {job}")


# ============================================================================
# Startup
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info("UCOP Web Application started")
    if not execution_engine:
        logger.warning("Job execution engine not connected - limited functionality")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "engine_connected": execution_engine is not None,
        "controller_connected": job_controller is not None
    }


@app.get("/api/status")
async def api_status():
    """API status endpoint - alias for health check."""
    return {
        "status": "healthy" if execution_engine else "limited",
        "engine_connected": execution_engine is not None,
        "controller_connected": job_controller is not None,
        "features": {
            "job_creation": execution_engine is not None,
            "job_control": job_controller is not None,
            "websocket": True,
            "rest_api": True
        }
    }
