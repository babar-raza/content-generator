# UCOP FastAPI Implementation

## Overview

FastAPI-based REST API for UCOP job management and workflow orchestration.

## Files Delivered

```
src/web/
├── __init__.py              # Module init
├── app.py                   # FastAPI application (with set_execution_engine)
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
python start_web.py --mode api --port 8080
```

Features:
- Integrated with full UCOP feature set
- Job execution engine injection
- Works with visual/mesh/debug features if enabled
- Production-ready

## API Endpoints

### Health & Info
- `GET /health` - Health check
- `GET /` - API information
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

### Jobs
- `POST /api/jobs` - Submit new job
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/{job_id}` - Get job status
- `POST /api/jobs/{job_id}/pause` - Pause job
- `POST /api/jobs/{job_id}/resume` - Resume job
- `POST /api/jobs/{job_id}/cancel` - Cancel job

### Workflows
- `GET /api/workflows` - List workflows
- `GET /api/workflows/{workflow_id}` - Get workflow details

### Agents
- `GET /api/agents` - List agents
- `GET /api/agents/{agent_id}` - Get agent details

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

### List jobs
```bash
curl http://localhost:8000/api/jobs
```

### Get job status
```bash
curl http://localhost:8000/api/jobs/{job_id}
```

### Pause job
```bash
curl -X POST http://localhost:8000/api/jobs/{job_id}/pause
```

### List workflows
```bash
curl http://localhost:8000/api/workflows
```

### List agents
```bash
curl http://localhost:8000/api/agents
```

## Integration with start_web.py

The FastAPI app integrates seamlessly with the unified server:

```python
from src.web.app import app, set_execution_engine

# Inject execution engine
set_execution_engine(execution_engine, job_controller)

# Run with uvicorn
uvicorn.run(app, host="0.0.0.0", port=8080)
```

The `set_execution_engine()` function allows the unified server to inject its initialized components into the FastAPI app for seamless integration.
