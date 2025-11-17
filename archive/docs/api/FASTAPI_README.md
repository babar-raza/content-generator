# UCOP FastAPI Implementation

## Overview

FastAPI-based REST API for UCOP job management and workflow orchestration.

## Files Delivered

```
src/web/
├── __init__.py              # Module init
├── app.py                   # FastAPI application (with set_global_executor)
├── models.py                # Pydantic request/response models
├── dependencies.py          # Dependency injection
└── routes/
    ├── __init__.py
    ├── jobs.py             # Job management endpoints
    ├── workflows.py        # Workflow endpoints
    └── agents.py           # Agent information endpoints

start_api.py                 # Simple API-only launcher
tests/web/
├── __init__.py
└── test_api.py             # API endpoint tests
```

## Launch Options

### Option 1: Simple API Server (Recommended for Development)

```bash
python start_api.py --port 8000
```

Features:
- Clean REST API only
- No dependencies on visual/mesh/debug features
- Fast startup
- Perfect for API development and testing

### Option 2: Unified Server (Full Features)

```bash
python start_web.py --port 8080
```

Features:
- Integrated with full UCOP feature set
- Job execution engine injection
- Works with visual/mesh/debug features if enabled
- Production-ready

**Note:** Use `start_web.py` for full web UI or `start_api.py` for lightweight API-only mode.

## API Endpoints

### Health & Info
- `GET /health` - Health check
- `GET /` - API information
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation
- `GET /api/system/health` - Enhanced system health with component status

### Jobs
- `POST /api/jobs` - Submit new job
- `POST /api/generate` - Generate content using RunSpec (topic, template, config)
- `POST /api/batch` - Create batch jobs
- `GET /api/jobs` - List all jobs (supports status filter, pagination)
- `GET /api/jobs/{job_id}` - Get job status
- `POST /api/jobs/{job_id}/pause` - Pause running job
- `POST /api/jobs/{job_id}/resume` - Resume paused job
- `POST /api/jobs/{job_id}/cancel` - Cancel job
- `GET /api/jobs/{job_id}/logs/{agent_name}` - Get agent logs for specific job (with secret redaction)

### Workflows
- `GET /api/workflows` - List workflows
- `GET /api/workflows/{workflow_id}` - Get workflow details

### Agents
- `GET /api/agents` - List agents
- `GET /api/agents/{agent_id}` - Get agent details
- `GET /api/agents/{agent_id}/logs` - Get agent logs across all jobs (with secret redaction)

## Testing

Run API tests:
```bash
pytest tests/web/test_api.py -v
```

## CORS Configuration

Allowed origins:
- http://localhost:3000
- http://localhost:8080
- http://localhost:8000
- http://127.0.0.1:3000
- http://127.0.0.1:8080
- http://127.0.0.1:8000

## Usage Examples

### Submit a job
```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "default", "inputs": {"topic": "Python Testing"}}'
```

### Generate content using RunSpec
```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "Python Testing", "template": "default_blog", "metadata": {"author": "John Doe"}}'
```

### Create batch jobs
```bash
curl -X POST http://localhost:8000/api/batch \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "default_blog", "batch_name": "my_batch", "jobs": [{"topic": "Topic 1"}, {"topic": "Topic 2"}]}'
```

### List jobs
```bash
curl http://localhost:8000/api/jobs
```

### List jobs with filters
```bash
# Filter by status
curl "http://localhost:8000/api/jobs?status=running"

# With pagination
curl "http://localhost:8000/api/jobs?limit=10&offset=0"
```

### Get job status
```bash
curl http://localhost:8000/api/jobs/{job_id}
```

### Pause job
```bash
curl -X POST http://localhost:8000/api/jobs/{job_id}/pause
```

### Resume job
```bash
curl -X POST http://localhost:8000/api/jobs/{job_id}/resume
```

### Cancel job
```bash
curl -X POST http://localhost:8000/api/jobs/{job_id}/cancel
```

### Get agent logs for a job (with secret redaction)
```bash
curl http://localhost:8000/api/jobs/{job_id}/logs/{agent_name}
```

### Get agent logs across all jobs
```bash
curl http://localhost:8000/api/agents/{agent_id}/logs

# Filter by specific job
curl "http://localhost:8000/api/agents/{agent_id}/logs?job_id={job_id}"
```

### List workflows
```bash
curl http://localhost:8000/api/workflows
```

### List agents
```bash
curl http://localhost:8000/api/agents
```

### System health check
```bash
curl http://localhost:8000/api/system/health
```

## Integration with start_web.py

The FastAPI app integrates seamlessly with the unified server:

```python
from src.web.app import app, set_global_executor

# Inject execution engine
set_global_executor(execution_engine, config_snapshot)

# Run with uvicorn
uvicorn.run(app, host="0.0.0.0", port=8080)
```

The `set_global_executor()` function allows the unified server to inject its initialized components into the FastAPI app for seamless integration.
