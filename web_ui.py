"""Enhanced Web UI with Log Route and Live Streaming

Provides web interface with real-time log viewing and event streaming.
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import traceback

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from src.core import Config, EventBus, AgentEvent
from src.core.config import load_config
from src.services.services_fixes import (
    TopicIdentificationFallback, RunToResultGuarantee
)
from main import create_services, create_agents, run_default_pipeline

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="AI Blog Generator v9.5", version="9.5-fixed")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
class AppState:
    def __init__(self):
        self.config: Optional[Config] = None
        self.event_bus: Optional[EventBus] = None
        self.agents: Dict = {}
        self.services: Dict = {}
        self.active_jobs: Dict[str, Dict] = {}
        self.job_logs: Dict[str, List[Dict]] = {}
        self.websockets: List[WebSocket] = []

state = AppState()


class BlogRequest(BaseModel):
    topic: str
    blog_mode: str = "on"
    enable_mesh: bool = False
    enable_orchestration: bool = False


class JobStatus(BaseModel):
    job_id: str
    status: str
    topic: str
    created_at: str
    updated_at: str
    progress: int
    output_path: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info("Starting AI Blog Generator Web UI...")
    
    # Load configuration
    state.config = load_config()
    state.config.blog_switch = True  # Default to blog mode ON
    
    # Create event bus
    state.event_bus = EventBus()
    
    # Subscribe to events for logging
    def log_event(event: AgentEvent):
        """Log events for active jobs."""
        if event.correlation_id in state.active_jobs:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event.event_type,
                "source_agent": event.source_agent,
                "data": event.data
            }
            
            if event.correlation_id not in state.job_logs:
                state.job_logs[event.correlation_id] = []
            
            state.job_logs[event.correlation_id].append(log_entry)
            
            # Broadcast to websockets
            asyncio.create_task(broadcast_event(event.correlation_id, log_entry))
    
    # Subscribe to all events
    state.event_bus.subscribe("*", log_event)
    
    # Create services and agents
    try:
        state.services = create_services(state.config)
        state.agents = create_agents(state.config, state.event_bus, state.services)
        logger.info(f"Initialized {len(state.agents)} agents")
    except Exception as e:
        logger.error(f"Failed to initialize services/agents: {e}")
        logger.debug(traceback.format_exc())
    
    logger.info("Web UI started successfully")


async def broadcast_event(job_id: str, event_data: Dict):
    """Broadcast event to all connected websockets."""
    message = json.dumps({
        "job_id": job_id,
        "event": event_data
    })
    
    disconnected = []
    for websocket in state.websockets:
        try:
            await websocket.send_text(message)
        except:
            disconnected.append(websocket)
    
    # Remove disconnected websockets
    for ws in disconnected:
        if ws in state.websockets:
            state.websockets.remove(ws)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main UI."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>AI Blog Generator v9.5</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        .container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #555;
        }
        input[type="text"], select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            margin-right: 10px;
        }
        button:hover {
            background: #0056b3;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .checkbox-group {
            display: flex;
            gap: 20px;
            margin: 15px 0;
        }
        .checkbox-group label {
            display: flex;
            align-items: center;
            font-weight: normal;
        }
        .checkbox-group input {
            margin-right: 5px;
        }
        #status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 4px;
            display: none;
        }
        .status-success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .status-error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .status-info {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
        }
        #logs {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 15px;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            display: none;
        }
        .log-entry {
            margin-bottom: 8px;
            padding: 8px;
            background: white;
            border-left: 3px solid #007bff;
            border-radius: 2px;
        }
        .log-timestamp {
            color: #6c757d;
            font-size: 12px;
        }
        .log-event {
            font-weight: bold;
            color: #007bff;
        }
        .jobs-list {
            list-style: none;
            padding: 0;
        }
        .job-item {
            padding: 10px;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .job-info {
            flex: 1;
        }
        .job-actions {
            display: flex;
            gap: 10px;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: #007bff;
            transition: width 0.3s ease;
        }
        .version-badge {
            background: #28a745;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <h1>AI Blog Generator <span class="version-badge">v9.5 FIXED</span></h1>
    
    <div class="container">
        <h2>Generate Blog Post</h2>
        <form id="generateForm">
            <div class="form-group">
                <label for="topic">Topic:</label>
                <input type="text" id="topic" name="topic" placeholder="Enter your blog topic..." required>
            </div>
            
            <div class="form-group">
                <label for="blogMode">Blog Mode:</label>
                <select id="blogMode" name="blogMode">
                    <option value="on">ON - Create directory structure (/slug/index.md)</option>
                    <option value="off">OFF - Single file (/slug.md)</option>
                </select>
            </div>
            
            <div class="checkbox-group">
                <label>
                    <input type="checkbox" id="enableMesh" name="enableMesh">
                    Enable Mesh Infrastructure
                </label>
                <label>
                    <input type="checkbox" id="enableOrchestration" name="enableOrchestration">
                    Enable Orchestration
                </label>
            </div>
            
            <button type="submit" id="generateBtn">Generate Blog Post</button>
            <button type="button" id="clearLogsBtn">Clear Logs</button>
        </form>
        
        <div id="status"></div>
        
        <div class="progress-bar" id="progressBar" style="display: none;">
            <div class="progress-fill" id="progressFill"></div>
        </div>
    </div>
    
    <div class="container">
        <h2>Active Jobs</h2>
        <ul id="jobsList" class="jobs-list"></ul>
    </div>
    
    <div class="container">
        <h2>Live Logs</h2>
        <div id="logs"></div>
    </div>
    
    <script>
        let ws = null;
        let currentJobId = null;
        
        // Initialize WebSocket connection
        function initWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = () => {
                console.log('WebSocket connected');
                updateStatus('Connected to server', 'info');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.job_id === currentJobId) {
                    addLogEntry(data.event);
                    updateProgress(data.event);
                }
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                updateStatus('Connection error', 'error');
            };
            
            ws.onclose = () => {
                console.log('WebSocket disconnected');
                updateStatus('Disconnected from server. Reconnecting...', 'info');
                setTimeout(initWebSocket, 3000);
            };
        }
        
        // Initialize on page load
        initWebSocket();
        loadJobs();
        
        // Form submission
        document.getElementById('generateForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const topic = document.getElementById('topic').value;
            const blogMode = document.getElementById('blogMode').value;
            const enableMesh = document.getElementById('enableMesh').checked;
            const enableOrchestration = document.getElementById('enableOrchestration').checked;
            
            if (!topic.trim()) {
                updateStatus('Please enter a topic', 'error');
                return;
            }
            
            // Disable form
            document.getElementById('generateBtn').disabled = true;
            
            // Clear previous logs
            document.getElementById('logs').innerHTML = '';
            document.getElementById('logs').style.display = 'block';
            
            // Show progress bar
            document.getElementById('progressBar').style.display = 'block';
            document.getElementById('progressFill').style.width = '0%';
            
            updateStatus('Starting blog generation...', 'info');
            
            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        topic: topic,
                        blog_mode: blogMode,
                        enable_mesh: enableMesh,
                        enable_orchestration: enableOrchestration
                    })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    currentJobId = result.job_id;
                    updateStatus(`Job started: ${result.job_id}`, 'success');
                    loadJobs();
                } else {
                    updateStatus(`Error: ${result.detail || 'Failed to start job'}`, 'error');
                }
            } catch (error) {
                updateStatus(`Error: ${error.message}`, 'error');
            } finally {
                document.getElementById('generateBtn').disabled = false;
            }
        });
        
        // Clear logs
        document.getElementById('clearLogsBtn').addEventListener('click', () => {
            document.getElementById('logs').innerHTML = '';
            document.getElementById('logs').style.display = 'none';
        });
        
        // Load active jobs
        async function loadJobs() {
            try {
                const response = await fetch('/api/jobs');
                const jobs = await response.json();
                
                const jobsList = document.getElementById('jobsList');
                if (jobs.length === 0) {
                    jobsList.innerHTML = '<li>No active jobs</li>';
                } else {
                    jobsList.innerHTML = jobs.map(job => `
                        <li class="job-item">
                            <div class="job-info">
                                <strong>${job.topic}</strong><br>
                                <span class="log-timestamp">${job.job_id}</span><br>
                                Status: ${job.status} | Progress: ${job.progress}%
                            </div>
                            <div class="job-actions">
                                <button onclick="viewLogs('${job.job_id}')">View Logs</button>
                                ${job.output_path ? `<button onclick="downloadOutput('${job.job_id}')">Download</button>` : ''}
                            </div>
                        </li>
                    `).join('');
                }
            } catch (error) {
                console.error('Failed to load jobs:', error);
            }
        }
        
        // View logs for a job
        async function viewLogs(jobId) {
            currentJobId = jobId;
            document.getElementById('logs').innerHTML = '';
            document.getElementById('logs').style.display = 'block';
            
            try {
                const response = await fetch(`/api/log/${jobId}`);
                const logs = await response.json();
                
                logs.forEach(log => addLogEntry(log));
            } catch (error) {
                console.error('Failed to load logs:', error);
            }
        }
        
        // Download output
        async function downloadOutput(jobId) {
            window.open(`/api/download/${jobId}`, '_blank');
        }
        
        // Add log entry to display
        function addLogEntry(entry) {
            const logsDiv = document.getElementById('logs');
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry';
            logEntry.innerHTML = `
                <span class="log-timestamp">${entry.timestamp}</span>
                <span class="log-event">${entry.event_type}</span>
                <div>${entry.source_agent}</div>
            `;
            logsDiv.appendChild(logEntry);
            logsDiv.scrollTop = logsDiv.scrollHeight;
        }
        
        // Update progress bar
        function updateProgress(event) {
            // Estimate progress based on event type
            const progressMap = {
                'topic_identified': 10,
                'seo_generated': 20,
                'frontmatter_created': 30,
                'outline_created': 40,
                'introduction_written': 50,
                'sections_written': 70,
                'conclusion_written': 80,
                'content_assembled': 90,
                'blog_post_complete': 100
            };
            
            const progress = progressMap[event.event_type];
            if (progress) {
                document.getElementById('progressFill').style.width = `${progress}%`;
                
                if (progress === 100) {
                    updateStatus('Blog post generated successfully!', 'success');
                    loadJobs();
                }
            }
        }
        
        // Update status message
        function updateStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = message;
            statusDiv.className = `status-${type}`;
            statusDiv.style.display = 'block';
            
            if (type !== 'error') {
                setTimeout(() => {
                    statusDiv.style.display = 'none';
                }, 5000);
            }
        }
        
        // Refresh jobs every 5 seconds
        setInterval(loadJobs, 5000);
    </script>
</body>
</html>
"""


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    state.websockets.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in state.websockets:
            state.websockets.remove(websocket)


@app.post("/api/generate")
async def generate_blog(request: BlogRequest):
    """Generate a blog post."""
    try:
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Update configuration
        state.config.blog_switch = (request.blog_mode == "on")
        state.config.mesh.enabled = request.enable_mesh
        state.config.orchestration.enabled = request.enable_orchestration
        
        # Create job record
        job = {
            "job_id": job_id,
            "status": "running",
            "topic": request.topic,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "progress": 0,
            "output_path": None
        }
        state.active_jobs[job_id] = job
        state.job_logs[job_id] = []
        
        # Run pipeline in background
        asyncio.create_task(run_pipeline_async(job_id, request.topic))
        
        return {"job_id": job_id, "status": "started"}
    
    except Exception as e:
        logger.error(f"Failed to start job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_pipeline_async(job_id: str, topic: str):
    """Run the pipeline asynchronously."""
    try:
        # Run the pipeline
        await asyncio.get_event_loop().run_in_executor(
            None,
            run_default_pipeline,
            state.config,
            state.event_bus,
            state.agents,
            topic
        )
        
        # Update job status
        state.active_jobs[job_id]["status"] = "completed"
        state.active_jobs[job_id]["progress"] = 100
        state.active_jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        # Get output path
        from src.engine.slug_service import slugify
        slug = slugify(topic)
        output_path = state.config.get_output_path(slug)
        state.active_jobs[job_id]["output_path"] = str(output_path)
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        state.active_jobs[job_id]["status"] = "failed"
        state.active_jobs[job_id]["error"] = str(e)
        state.active_jobs[job_id]["updated_at"] = datetime.now().isoformat()


@app.get("/api/jobs")
async def get_jobs():
    """Get list of active jobs."""
    jobs = []
    for job_id, job_data in state.active_jobs.items():
        jobs.append(JobStatus(
            job_id=job_id,
            status=job_data["status"],
            topic=job_data["topic"],
            created_at=job_data["created_at"],
            updated_at=job_data["updated_at"],
            progress=job_data.get("progress", 0),
            output_path=job_data.get("output_path")
        ))
    return jobs


@app.get("/api/log/{job_id}")
async def get_job_logs(job_id: str):
    """Get logs for a specific job."""
    if job_id not in state.job_logs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return state.job_logs[job_id]


@app.get("/api/download/{job_id}")
async def download_output(job_id: str):
    """Download the generated blog post."""
    if job_id not in state.active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = state.active_jobs[job_id]
    if not job.get("output_path"):
        raise HTTPException(status_code=404, detail="Output not available")
    
    output_path = Path(job["output_path"])
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")
    
    return FileResponse(
        path=output_path,
        filename=output_path.name,
        media_type="text/markdown"
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "9.5-fixed",
        "agents": len(state.agents),
        "active_jobs": len(state.active_jobs)
    }


def start_web_ui(host: str = "0.0.0.0", port: int = 5000):
    """Start the web UI server."""
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    import sys
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start server
    host = os.getenv("WEB_UI_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_UI_PORT", 5000))
    
    logger.info(f"Starting web UI at http://{host}:{port}")
    start_web_ui(host, port)
