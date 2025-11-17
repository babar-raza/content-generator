# UCOP REST API

Production-ready FastAPI REST API for job control and monitoring.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
python start_web.py

# Server runs on http://localhost:8000
# API docs: http://localhost:8000/docs
# Health check: http://localhost:8000/health
```

## Features

- ✅ REST API for job control
- ✅ Job submission and monitoring
- ✅ Workflow and agent information
- ✅ Health check endpoint
- ✅ Auto-generated Swagger docs
- ✅ CORS enabled for frontend
- ✅ Rate limiting (100 req/min per IP)
- ✅ Proper error handling
- ✅ Request logging
- ✅ Type hints and validation

## API Endpoints

### System

- `GET /` - API information
- `GET /health` - Health check
- `GET /docs` - Swagger documentation
- `GET /redoc` - ReDoc documentation

### Jobs

- `POST /api/jobs` - Submit new job
- `GET /api/jobs` - List all jobs (with pagination and filtering)
- `GET /api/jobs/{job_id}` - Get job status
- `POST /api/jobs/{job_id}/pause` - Pause job
- `POST /api/jobs/{job_id}/resume` - Resume job
- `POST /api/jobs/{job_id}/cancel` - Cancel job

### Workflows

- `GET /api/workflows` - List all workflows
- `GET /api/workflows/{workflow_id}` - Get workflow details

### Agents

- `GET /api/agents` - List all agents (with category filter)
- `GET /api/agents/{agent_id}` - Get agent details

## Testing

```bash
# Run all tests
pytest tests/web/test_api.py -v

# Run specific test class
pytest tests/web/test_api.py::TestHealthEndpoint -v

# Run with coverage
pytest tests/web/test_api.py --cov=src.web --cov-report=html
```

## Runbook

```bash
# Make runbook executable
chmod +x RUNBOOK_API.sh

# Run runbook tests
./RUNBOOK_API.sh
```

The runbook will:
1. Start the API server
2. Test all endpoints
3. Verify rate limiting
4. Check error handling
5. Stop the server
6. Report results

## Manual Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### List Workflows
```bash
curl http://localhost:8000/api/workflows
```

### List Jobs
```bash
curl http://localhost:8000/api/jobs
```

### Create Job
```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "blog_generation",
    "inputs": {
      "topic": "AI trends",
      "target_length": 1000
    }
  }'
```

### Get Job Status
```bash
curl http://localhost:8000/api/jobs/{job_id}
```

### Pause Job
```bash
curl -X POST http://localhost:8000/api/jobs/{job_id}/pause
```

### Resume Job
```bash
curl -X POST http://localhost:8000/api/jobs/{job_id}/resume
```

### Cancel Job
```bash
curl -X POST http://localhost:8000/api/jobs/{job_id}/cancel
```

## Configuration

### Server Options

```bash
python start_web.py --help
```

Options:
- `--host` - Host to bind to (default: 0.0.0.0)
- `--port` - Port to bind to (default: 8000)
- `--reload` - Enable auto-reload for development
- `--log-level` - Set logging level (debug/info/warning/error)

### CORS

CORS is configured to allow:
- http://localhost:3000
- http://localhost:8080
- http://127.0.0.1:3000
- http://127.0.0.1:8080

Modify `src/web/app.py` to add more origins.

### Rate Limiting

Default: 100 requests per minute per IP

Modify `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW` in `src/web/app.py`.

## Error Handling

All errors return proper HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request (invalid input)
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error

Error response format:
```json
{
  "detail": "Error message",
  "error_type": "ErrorType",
  "timestamp": "2025-01-01T00:00:00"
}
```

## Rate Limit Headers

All responses include rate limit headers:

- `X-RateLimit-Limit` - Maximum requests allowed
- `X-RateLimit-Remaining` - Requests remaining
- `X-RateLimit-Reset` - Timestamp when limit resets

## Architecture

```
src/web/
├── __init__.py          # Module exports
├── app.py               # FastAPI application (300+ lines)
├── models.py            # Pydantic request/response models
├── dependencies.py      # Dependency injection
└── routes/
    ├── __init__.py
    ├── jobs.py          # Job management endpoints
    ├── workflows.py     # Workflow endpoints
    └── agents.py        # Agent endpoints
```

## Development

### Adding New Endpoint

1. Define Pydantic models in `models.py`
2. Create route in appropriate `routes/*.py` file
3. Add tests in `tests/web/test_api.py`
4. Update this README

### Code Style

- Use type hints on all functions
- Use async route handlers where appropriate
- Handle errors with proper HTTP status codes
- Log all important operations
- Write tests for all endpoints

## Production Deployment

### With Uvicorn

```bash
uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### With Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### With Gunicorn

```bash
gunicorn src.web.app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Troubleshooting

### Server won't start

1. Check if port 8000 is available
2. Verify dependencies are installed
3. Check log file: `ucop_api.log`

### Tests failing

1. Ensure server is not already running
2. Install test dependencies: `pip install pytest pytest-asyncio`
3. Check `tests/web/test_api.py` for details

### Import errors

```bash
pip install -r requirements.txt
```

## Support

For issues or questions:
1. Check API docs: http://localhost:8000/docs
2. Review logs: `ucop_api.log`
3. Run tests: `pytest tests/web/test_api.py -v`
4. Check runbook: `./RUNBOOK_API.sh`
