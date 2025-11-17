"""
ARCHIVED: 2025-11-13
Reason: Features consolidated into src/web/app.py
Replacement: Use src/web/app.py which provides all functionality with React UI and MCP protocol
Historical: This file provided unified engine integration for web interface

Updated Web App - Using unified engine for parity with CLI.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path

# Import unified engine
from src.engine.unified_engine import get_engine, RunSpec, JobStatus
from src.core.template_registry import list_templates

app = FastAPI(title="UCOP Web UI")

# Templates directory
templates = Jinja2Templates(directory="src/web/templates")

# Store for jobs (in-memory for now)
jobs_store = {}


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


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard."""
    # Get available templates
    templates_list = list_templates()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "templates": [{"name": t.name, "type": t.type.value} for t in templates_list]
    })


@app.get("/api/templates")
async def get_templates(template_type: Optional[str] = None):
    """Get available templates."""
    templates_list = list_templates(template_type)
    
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
    
    # Build run spec - SAME as CLI
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
    
    # Get engine and execute - SAME as CLI
    engine = get_engine()
    result = engine.generate_job(run_spec)
    
    # Store job
    jobs_store[result.job_id] = result
    
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
    
    if job_id not in jobs_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = jobs_store[job_id]
    
    return {
        "job_id": result.job_id,
        "status": result.status.value,
        "run_spec": result.run_spec.to_dict(),
        "output_path": str(result.output_path) if result.output_path else None,
        "manifest_path": str(result.manifest_path) if result.manifest_path else None,
        "pipeline_order": result.pipeline_order,
        "sources_used": result.sources_used,
        "duration": result.duration,
        "error": result.error
    }


@app.get("/api/jobs/{job_id}/logs/{agent_name}")
async def get_agent_log(job_id: str, agent_name: str):
    """Get agent step log (for Log button)."""
    
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
# DOCGEN:LLM-FIRST@v4