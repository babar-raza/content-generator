# UCOP REST API - Package Contents

## Installation & Testing

- `INSTALL_API.sh` - Installation script
- `RUNBOOK_API.sh` - Comprehensive API testing runbook
- `verify_api.py` - Quick verification script
- `API_README.md` - Complete API documentation
- `requirements.txt` - Python dependencies
- `.env.example` - Environment configuration template

## Core Application

### Main Entry Point
- `start_web.py` - Server launcher (simplified, clean)

### Web Module (src/web/)
- `__init__.py` - Module exports
- `app.py` - FastAPI application (300+ lines)
  - CORS configuration
  - Rate limiting (100 req/min per IP)
  - Error handling
  - Logging middleware
  - Health check endpoint
  - Auto-generated Swagger docs

- `models.py` - Pydantic request/response models
  - JobCreate, JobResponse, JobListResponse
  - WorkflowResponse, WorkflowListResponse
  - AgentResponse, AgentListResponse
  - HealthResponse, ErrorResponse

- `dependencies.py` - Dependency injection
  - get_job_engine()
  - get_workflow_compiler()
  - get_checkpoint_manager()
  - get_config()

### Routes (src/web/routes/)
- `__init__.py` - Route exports
- `jobs.py` - Job management endpoints
  - POST /api/jobs - Create job
  - GET /api/jobs - List jobs
  - GET /api/jobs/{job_id} - Get job status
  - POST /api/jobs/{job_id}/pause - Pause job
  - POST /api/jobs/{job_id}/resume - Resume job
  - POST /api/jobs/{job_id}/cancel - Cancel job

- `workflows.py` - Workflow endpoints
  - GET /api/workflows - List workflows
  - GET /api/workflows/{workflow_id} - Get workflow details

- `agents.py` - Agent endpoints
  - GET /api/agents - List agents
  - GET /api/agents/{agent_id} - Get agent details

### Tests (tests/web/)
- `test_api.py` - Comprehensive API tests
  - TestHealthEndpoint (2 tests)
  - TestRootEndpoint (2 tests)
  - TestJobsAPI (10 tests)
  - TestWorkflowsAPI (3 tests)
  - TestAgentsAPI (5 tests)
  - TestCORS (2 tests)
  - TestRateLimiting (2 tests)
  - TestErrorHandling (2 tests)
  - TestDocumentation (3 tests)
  - TestMiddleware (2 tests)
  - TestIntegration (1 test)
  - Total: 34 test cases

## Supporting Modules

### Core (src/core/)
- Configuration management
- Event bus
- Agent base classes
- Workflow compiler
- Job execution engine
- Template registry
- Contract definitions

### Orchestration (src/orchestration/)
- Job execution engine
- Workflow compiler
- Checkpoint manager
- Parallel executor
- LangGraph integration
- Hot reload support
- Dependency resolver

### Agents (src/agents/)
- Research agents (topic identification, duplication check, etc.)
- Ingestion agents (KB, API, blog, docs, tutorials)
- Content agents (outline, introduction, sections, conclusion)
- Code agents (generation, validation, splitting, license)
- SEO agents (keyword extraction/injection, metadata)
- Publishing agents (frontmatter, file writer, link validation)
- Support agents (quality gates, error recovery, validation)

### Services (src/services/)
- Model router (Gemini, OpenAI, Ollama)
- Vector store (ChromaDB)
- MCP service

### Utils (src/utils/)
- Retry logic
- Validators
- Path utilities
- Content utilities
- JSON repair
- Duplication detection
- Citation tracking
- Resilience patterns

### Realtime (src/realtime/)
- WebSocket manager (for future use)
- Job control

### Config (config/)
- main.yaml - Main configuration
- agents.yaml - Agent definitions
- validation.yaml - Validation rules
- tone.json - Tone settings
- perf.json - Performance settings

## Quick Start

```bash
# 1. Install
bash INSTALL_API.sh

# 2. Verify
python verify_api.py

# 3. Start server
python start_web.py

# 4. Test manually
curl http://localhost:8000/health
curl http://localhost:8000/api/workflows

# 5. Run comprehensive tests
pytest tests/web/test_api.py -v

# 6. Run runbook
bash RUNBOOK_API.sh
```

## Key Features

✅ Production-ready REST API
✅ Complete job control and monitoring
✅ Auto-generated Swagger documentation
✅ CORS enabled for frontend access
✅ Rate limiting (100 requests/minute per IP)
✅ Comprehensive error handling
✅ Request logging
✅ Type hints and validation
✅ 34 test cases covering all endpoints
✅ Runbook for end-to-end testing

## API Endpoints Summary

### System
- GET / - API info
- GET /health - Health check
- GET /docs - Swagger UI
- GET /redoc - ReDoc
- GET /openapi.json - OpenAPI schema

### Jobs (7 endpoints)
- POST /api/jobs
- GET /api/jobs
- GET /api/jobs/{job_id}
- POST /api/jobs/{job_id}/pause
- POST /api/jobs/{job_id}/resume
- POST /api/jobs/{job_id}/cancel

### Workflows (2 endpoints)
- GET /api/workflows
- GET /api/workflows/{workflow_id}

### Agents (2 endpoints)
- GET /api/agents
- GET /api/agents/{agent_id}

Total: 13 endpoints

## Architecture

```
FastAPI App (src/web/app.py)
├── Middleware
│   ├── CORS
│   ├── Rate Limiting
│   ├── GZip Compression
│   └── Request Logging
├── Exception Handlers
│   ├── HTTP Exceptions
│   ├── Validation Errors
│   └── General Exceptions
├── Routes
│   ├── Jobs (src/web/routes/jobs.py)
│   ├── Workflows (src/web/routes/workflows.py)
│   └── Agents (src/web/routes/agents.py)
└── Dependencies
    ├── Job Engine
    ├── Workflow Compiler
    └── Checkpoint Manager
```

## Testing Coverage

- Unit tests for all endpoints
- Integration tests for workflows
- Error handling tests
- Rate limiting tests
- CORS tests
- Documentation tests
- Middleware tests

Total: 34 test cases, 100% endpoint coverage

## Notes

- WebSockets NOT included (as per requirements)
- Visual editor UI NOT included (future task)
- MCP handlers present but not exposed in API
- All endpoints use dependency injection
- Async route handlers where appropriate
- Proper HTTP status codes for all responses
- Rate limit headers on all responses
