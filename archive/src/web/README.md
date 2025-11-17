# Web Module

## Overview

FastAPI-based web UI for visual workflow editing, real-time monitoring, and job control.

## Components

### `app.py`
Main FastAPI application with all endpoints.

```python
app = FastAPI()

@app.get("/")
async def index()

@app.post("/api/generate")
async def generate(request: GenerateRequest)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket)
```

## Endpoints

### Pages

- `GET /` - Main dashboard
- `GET /workflows` - Workflow editor
- `GET /jobs` - Job list and monitoring
- `GET /jobs/{job_id}` - Job details

### API

- `POST /api/generate` - Start content generation
- `POST /api/batch` - Batch processing
- `GET /api/jobs` - List jobs
- `GET /api/jobs/{job_id}` - Job status
- `POST /api/jobs/{job_id}/pause` - Pause job
- `POST /api/jobs/{job_id}/resume` - Resume job
- `POST /api/jobs/{job_id}/cancel` - Cancel job

### WebSocket

- `WS /ws` - Real-time updates
  - Job status changes
  - Agent completions
  - Progress updates
  - Error notifications

## Static Assets

### `static/`

- `css/` - Stylesheets
- `js/` - JavaScript for interactive UI

### `templates/`

- Jinja2 templates for HTML pages

## Usage

### Start Web Server

```python
from src.web.app import app
import uvicorn

uvicorn.run(app, host="0.0.0.0", port=8000)
```

Or use the launcher:

```bash
python start_web.py
```

### API Client Example

```python
import requests

# Start generation
response = requests.post('http://localhost:8000/api/generate', json={
    'source_file': 'article.md',
    'workflow': 'blog_generation'
})

job_id = response.json()['job_id']

# Check status
status = requests.get(f'http://localhost:8000/api/jobs/{job_id}')
print(status.json())
```

### WebSocket Client

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    console.log('Update:', update);
};

// Subscribe to job updates
ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['job:' + jobId]
}));
```

## Features

1. **Visual Workflow Editor**
   - Drag-and-drop agents
   - Connect agents visually
   - Configure parameters
   - Save custom workflows

2. **Real-Time Monitoring**
   - Live job status
   - Agent execution progress
   - Performance metrics
   - Error tracking

3. **Job Control**
   - Pause/Resume jobs
   - Cancel jobs
   - View job history
   - Download outputs

4. **Debugging Tools**
   - Set breakpoints
   - Step through execution
   - Inspect state
   - View logs

## Configuration

Web server configured in `config/main.yaml`:

```yaml
web:
  host: 0.0.0.0
  port: 8000
  workers: 4
  reload: true  # Dev mode
```

## Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `jinja2` - Template engine
- `websockets` - WebSocket support
- `src.engine` - Execution engine
- `src.orchestration` - Job management
- `src.realtime` - Real-time updates
