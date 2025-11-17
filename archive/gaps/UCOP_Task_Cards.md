# UCOP Production Gaps - Task Cards

**Purpose**: Drop-in, production-ready fixes for all identified gaps  
**Total Tasks**: 10 (5 P0 Critical + 5 P1 High Priority)  
**Estimated Effort**: 88 hours

---

## 🔴 P0 CRITICAL TASKS (Must complete before production)

### TASK-P0-001: Mount MCP Web Adapter Router

**Priority**: P0 - BLOCKER  
**Effort**: 2 hours  
**Impact**: Unlocks 27 unmounted endpoints, fixes React UI 404 errors

**Role**: Senior Python/FastAPI engineer. You are wiring an existing, fully-implemented router that was never mounted.

**Scope**: 
- Fix: Mount `src/mcp/web_adapter.py` router to make 27 endpoints accessible
- Root cause: `src/web/app.py` imports minimal `routes/mcp.py` instead of full `web_adapter.py`
- Allowed paths: `src/web/app.py`, `src/mcp/web_adapter.py`, `tests/integration/test_mcp_integration.py`
- Forbidden: Any agent code, engine code, or UI code

**Current State**:
```python
# src/web/app.py:82
from .routes import mcp
app.include_router(mcp.router)  # ← Only 5 endpoints
```

**Target State**:
```python
# Mount the FULL MCP adapter with 29 endpoints
from src.mcp.web_adapter import router as mcp_adapter_router
app.include_router(mcp_adapter_router)
```

**Acceptance Checks**:
1. CLI: `curl http://127.0.0.1:8080/mcp/config/snapshot` returns 200 (not 404)
2. Web: `curl http://127.0.0.1:8080/mcp/flows/bottlenecks` returns 200 (not 404)
3. All 29 endpoints from `web_adapter.py` are accessible
4. Existing 5 endpoints in `routes/mcp.py` still work OR are replaced
5. Tests: `pytest tests/integration/test_mcp_integration.py -v`

**Deliverables**:
1. Updated `src/web/app.py` mounting the correct router
2. Decision: Keep or remove `src/web/routes/mcp.py` (document rationale)
3. Integration test covering all new endpoints return 200-299 status
4. Update `web_adapter.py` to properly initialize with executor/config

**Design Guidance**:
- Check if `web_adapter.py` needs `set_executor()` call during app initialization
- Verify no endpoint path conflicts between old and new routers
- Ensure MCP protocol handler (`/mcp/request`) works end-to-end
- Consider keeping `routes/mcp.py` if it has functionality not in `web_adapter.py`

**Hard Rules**:
- Do NOT modify MCP protocol logic, only wire it
- Preserve all existing `/api/*` endpoints
- If removing `routes/mcp.py`, migrate any unique logic first
- No changes to React UI (that's a separate task)

**Self-Review Checklist**:
- [ ] All 29 MCP endpoints return non-404 status
- [ ] React UI can call `/mcp/config/agents` successfully
- [ ] CLI MCP client still works (if exists)
- [ ] No duplicate route definitions
- [ ] Tests pass: `pytest tests/integration/ -k mcp`
- [ ] Documented which router was kept/removed and why

**Runbook**:
```bash
# 1. Update code
# 2. Start server
python start_web.py &
sleep 5

# 3. Test critical endpoints
curl http://127.0.0.1:8080/mcp/config/snapshot
curl http://127.0.0.1:8080/mcp/flows/bottlenecks
curl http://127.0.0.1:8080/mcp/agents/status

# 4. Run tests
pytest tests/integration/test_mcp_integration.py -v

# 5. Verify React UI
# Open http://127.0.0.1:8080 and check browser console for 404s
```

---

### TASK-P0-002: Implement Checkpoint REST API

**Priority**: P0 - BLOCKER  
**Effort**: 8 hours  
**Impact**: Web users can manage job checkpoints (currently CLI only)

**Role**: Senior FastAPI engineer. Build REST endpoints wrapping existing `CheckpointManager`.

**Scope**:
- Fix: Create `/api/checkpoints/*` endpoints for checkpoint management
- Existing: `CheckpointManager` in `src/orchestration/checkpoint_manager.py` works via CLI
- Allowed paths: `src/web/routes/` (new file: `checkpoints.py`), `src/web/models.py`, `tests/integration/`
- Forbidden: Modifying `CheckpointManager` internals, engine code, or CLI

**Required Endpoints**:
```
GET    /api/checkpoints?job_id={id}           - List checkpoints for job
GET    /api/checkpoints/{checkpoint_id}       - Get checkpoint details
POST   /api/checkpoints/{checkpoint_id}/restore - Restore from checkpoint
DELETE /api/checkpoints/{checkpoint_id}       - Delete checkpoint
POST   /api/checkpoints/cleanup               - Cleanup old checkpoints (body: job_id, keep_last)
```

**Acceptance Checks**:
1. CLI: `curl -X GET http://127.0.0.1:8080/api/checkpoints?job_id=test-123` returns checkpoint list
2. Web: Create job, checkpoint it (may need to trigger manually), list checkpoints via API
3. Restore: `curl -X POST http://127.0.0.1:8080/api/checkpoints/{id}/restore` resumes job
4. Tests: `pytest tests/integration/test_checkpoint_api.py -v`
5. Existing CLI commands still work: `python ucop_cli.py checkpoint list --job-id=test`

**Deliverables**:
1. New file: `src/web/routes/checkpoints.py` with all 5 endpoints
2. Pydantic models in `src/web/models.py`: `CheckpointResponse`, `CheckpointList`, `RestoreRequest`, `CleanupRequest`
3. Mount router in `src/web/app.py`
4. Integration tests: create job → checkpoint → list → restore → verify
5. Error handling: 404 if checkpoint not found, 400 if job can't be restored

**Design Guidance**:
- Use dependency injection pattern from `jobs.py` to get `CheckpointManager`
- Checkpoint directory should come from config or environment variable
- `/restore` should trigger job resume if checkpoint valid
- `/cleanup` needs `job_id` and `keep_last` (default 10) in request body
- List endpoint should accept `job_id` query param (required)

**Hard Rules**:
- CheckpointManager already handles file I/O, don't duplicate
- Use existing `CheckpointMetadata` class, don't recreate
- Coordinate with job execution engine for restore (may need executor.resume_job)
- Windows-safe paths: use `Path()` not string concatenation

**Self-Review Checklist**:
- [ ] All 5 endpoints implemented and documented
- [ ] Can list checkpoints for any job via API
- [ ] Can restore job from checkpoint via API
- [ ] Cleanup removes old checkpoints, keeps N most recent
- [ ] Error cases return proper HTTP status codes
- [ ] Integration tests cover happy + error paths
- [ ] CLI checkpoint commands still work

**Runbook**:
```bash
# 1. Start server
python start_web.py &
sleep 5

# 2. Create a test job
curl -X POST http://127.0.0.1:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic":"test","template":"default_blog"}' 
# Note job_id from response

# 3. List checkpoints (should be empty or have auto-checkpoints)
curl "http://127.0.0.1:8080/api/checkpoints?job_id=<JOB_ID>"

# 4. Run tests
pytest tests/integration/test_checkpoint_api.py -v

# 5. Verify CLI still works
python ucop_cli.py checkpoint list --job-id=<JOB_ID>
```

---

### TASK-P0-003: Fix or Remove Legacy UI Missing Endpoints

**Priority**: P0 - BLOCKER  
**Effort**: 6 hours  
**Impact**: Stops 6 broken features in legacy dashboard (404 errors)

**Role**: Senior engineer. Make a binary decision: implement missing endpoints OR remove legacy UI.

**Scope**:
- Fix: 6 endpoints expected by `src/web/static/js/job_detail.js` don't exist
- Decision point: Implement vs remove (recommend REMOVE if React UI covers same features)
- Allowed paths: `src/web/routes/jobs.py`, `src/web/static/js/`, `templates/`, `tests/integration/`
- Forbidden: Agent code, engine internals

**Missing Endpoints Expected by Legacy UI**:
```
GET  /api/jobs/{job_id}/logs/stream          - SSE log streaming (job_detail.js:156)
GET  /api/jobs/{job_id}/artifacts            - List job artifacts (job_detail.js:312)
POST /api/jobs/{job_id}/step                 - Step through job (job_detail.js:428)
POST /api/jobs/{job_id}/pipeline/add         - Add pipeline stage (job_detail.js:544)
POST /api/jobs/{job_id}/pipeline/remove      - Remove pipeline stage (job_detail.js:589)
GET  /api/jobs/{job_id}/agents/{agent_id}/output - Per-agent output (job_detail.js:673)
```

**Acceptance Checks**:
1. **IF IMPLEMENTING**: All 6 endpoints return 200, legacy UI works without console errors
2. **IF REMOVING**: Legacy UI code deleted, only React UI remains, no 404s in browser console
3. CLI: `python ucop_cli.py list-jobs` still works
4. Web: `curl http://127.0.0.1:8080/api/jobs` returns job list
5. Tests: `pytest tests/integration/test_jobs_api.py -v`

**Option A: Implement Missing Endpoints** (6 hours)

**Deliverables**:
1. Implement all 6 endpoints in `src/web/routes/jobs.py`
2. SSE streaming: Use `EventSourceResponse` from fastapi
3. Artifacts: Read from job's output directory
4. Step/pipeline: Wire to executor's step control
5. Tests for each endpoint
6. Verify legacy UI loads and functions

**Option B: Remove Legacy UI** (2 hours) - RECOMMENDED

**Deliverables**:
1. Delete: `templates/job_detail.html`, `src/web/static/js/job_detail.js`
2. Update: `templates/dashboard.html` to redirect to React UI
3. Document: Which features from legacy UI are/aren't in React UI
4. Tests: Verify React UI covers all use cases
5. Update docs: Remove references to legacy UI

**Design Guidance**:
- Check if React UI has feature parity with legacy UI
- If implementing SSE, use `sse_starlette` library
- Artifacts should come from job's `output_path` directory
- Step control requires executor coordination
- Pipeline add/remove is dynamic workflow modification (complex!)

**Hard Rules**:
- Don't leave dead code paths
- If removing UI, also remove unreferenced JS/CSS
- Document the decision and rationale in CHANGELOG
- If implementing, ensure Windows-safe file paths for artifacts

**Self-Review Checklist**:
- [ ] Decision made and justified (implement vs remove)
- [ ] No 404 errors in browser console when using app
- [ ] All existing job management features still work
- [ ] React UI (if kept as only UI) covers critical features
- [ ] Tests verify endpoints work or are removed
- [ ] Documentation updated

**Runbook (Option B - Remove)**:
```bash
# 1. Delete legacy UI files
rm templates/job_detail.html
rm src/web/static/js/job_detail.js
rm src/web/static/js/dashboard.js

# 2. Update templates
# Edit templates/dashboard.html to redirect to React UI

# 3. Start server
python start_web.py &

# 4. Test in browser
# Navigate to http://127.0.0.1:8080
# Check console for 404s
# Verify job creation/listing works

# 5. Run tests
pytest tests/integration/test_jobs_api.py -v
```

---

### TASK-P0-004: Expose Configuration Endpoints

**Priority**: P0 - BLOCKER  
**Effort**: 2 hours  
**Impact**: Runtime config visibility via web (already in unmounted router)

**Role**: Senior engineer. This is a VERIFICATION task - endpoints already exist, just ensure they're mounted.

**Scope**:
- Fix: Verify config endpoints accessible after TASK-P0-001 completes
- Endpoints: `/mcp/config/{snapshot,agents,workflows,tone,performance}`
- Allowed paths: `src/mcp/web_adapter.py`, `tests/integration/test_config_api.py`
- Forbidden: Changing config loading logic, modifying schemas

**Current State**:
- Endpoints implemented in `src/mcp/web_adapter.py:822-934`
- NOT accessible because router not mounted (TASK-P0-001)

**Acceptance Checks**:
1. CLI: `curl http://127.0.0.1:8080/mcp/config/snapshot` returns config hash + summary
2. Web: `curl http://127.0.0.1:8080/mcp/config/agents` returns agent list
3. All 5 config endpoints return valid JSON
4. Tests: `pytest tests/integration/test_config_api.py -v`
5. React UI can fetch and display config (bonus)

**Deliverables**:
1. Integration tests for all 5 config endpoints
2. Verify endpoints return actual config data (not mocks)
3. Ensure config snapshot includes runtime metadata
4. Error handling: 503 if config not loaded

**Design Guidance**:
- This task DEPENDS on TASK-P0-001 being complete
- Test that `_config_snapshot` is properly set during app initialization
- Verify tone/performance configs load from `config/tone.json` and `config/perf.json`
- Ensure agents config matches `config/agents.yaml`

**Hard Rules**:
- Do NOT modify config loading logic
- Return actual runtime config, not static files
- If config not available, return 503 Service Unavailable
- Config should include metadata: loaded_at, config_hash

**Self-Review Checklist**:
- [ ] TASK-P0-001 completed (prerequisite)
- [ ] All 5 endpoints return 200 with valid data
- [ ] Config data matches actual runtime configuration
- [ ] Error cases handled (config not loaded)
- [ ] Tests verify config structure and required fields
- [ ] React UI can consume config endpoints

**Runbook**:
```bash
# 1. Ensure TASK-P0-001 is complete
# 2. Start server
python start_web.py &
sleep 5

# 3. Test each config endpoint
curl http://127.0.0.1:8080/mcp/config/snapshot | jq
curl http://127.0.0.1:8080/mcp/config/agents | jq
curl http://127.0.0.1:8080/mcp/config/workflows | jq
curl http://127.0.0.1:8080/mcp/config/tone | jq
curl http://127.0.0.1:8080/mcp/config/performance | jq

# 4. Verify structure
# Each should return valid JSON with expected fields

# 5. Run tests
pytest tests/integration/test_config_api.py -v
```

---

### TASK-P0-005: Add HTTP Endpoint Test Suite

**Priority**: P0 - BLOCKER  
**Effort**: 12 hours  
**Impact**: Prevent regressions, ensure all endpoints work

**Role**: Senior test engineer. Create comprehensive HTTP endpoint tests covering ALL routes.

**Scope**:
- Fix: No HTTP endpoint tests exist - add full coverage
- Cover: All `/api/*` and `/mcp/*` endpoints
- Allowed paths: `tests/integration/`, `tests/fixtures/`, `conftest.py`
- Forbidden: Modifying production code (except to make testable)

**Test Coverage Required**:
```
Jobs API (8 endpoints):
  ✓ POST /api/jobs - create job
  ✓ POST /api/generate - generate content
  ✓ POST /api/batch - batch jobs
  ✓ GET /api/jobs - list jobs
  ✓ GET /api/jobs/{id} - get job
  ✓ POST /api/jobs/{id}/pause - pause
  ✓ POST /api/jobs/{id}/resume - resume
  ✓ POST /api/jobs/{id}/cancel - cancel

Agents API (4 endpoints):
  ✓ GET /api/agents
  ✓ GET /api/agents/{id}
  ✓ GET /api/jobs/{job_id}/logs/{agent_name}
  ✓ GET /api/agents/{id}/logs

Workflows API (2 endpoints):
  ✓ GET /api/workflows
  ✓ GET /api/workflows/{id}

Visualization API (7 endpoints):
  ✓ GET /api/visualization/workflows
  ✓ GET /api/visualization/workflows/{id}
  ✓ GET /api/visualization/workflows/{id}/render
  ✓ GET /api/monitoring/agents
  ✓ GET /api/monitoring/agents/{id}
  ✓ GET /api/monitoring/system
  ✓ GET /api/monitoring/jobs/{id}/metrics

Debug API (5 endpoints):
  ✓ POST /api/debug/breakpoints
  ✓ DELETE /api/debug/breakpoints/{id}
  ✓ GET /api/debug/breakpoints
  ✓ POST /api/debug/step
  ✓ GET /api/debug/state/{job_id}

MCP API (29 endpoints from web_adapter):
  ✓ All /mcp/* endpoints (after TASK-P0-001)

Checkpoints API (5 endpoints):
  ✓ All /api/checkpoints/* (from TASK-P0-002)
```

**Acceptance Checks**:
1. Tests: `pytest tests/integration/ -v` all pass
2. Coverage: `pytest --cov=src/web/routes --cov-report=term` shows >80%
3. No production code modified except to expose testability hooks
4. All tests use test fixtures, no real network/DB calls
5. Tests are idempotent and can run in parallel

**Deliverables**:
1. New test files:
   - `tests/integration/test_jobs_api.py`
   - `tests/integration/test_agents_api.py`
   - `tests/integration/test_workflows_api.py`
   - `tests/integration/test_visualization_api.py`
   - `tests/integration/test_debug_api.py`
   - `tests/integration/test_mcp_api.py`
   - `tests/integration/test_checkpoints_api.py`

2. Test fixtures in `tests/fixtures/`:
   - Mock executor
   - Mock jobs store
   - Mock agent logs
   - Sample job data

3. Each test file should have:
   - Happy path tests (200 responses)
   - Error path tests (404, 400, 500)
   - Input validation tests
   - Authentication tests (if applicable)

**Design Guidance**:
- Use FastAPI `TestClient` for all HTTP tests
- Create test fixtures for common scenarios
- Use `pytest.mark.parametrize` for testing multiple inputs
- Each endpoint needs minimum 3 tests: success, not found, invalid input
- WebSocket tests separate (use `starlette.testclient.WebSocketTestClient`)

**Hard Rules**:
- Zero network calls (mock all external services)
- No database dependencies (use in-memory stores)
- Tests must be deterministic (set seeds, stable ordering)
- No reliance on test execution order
- Clean up resources after each test

**Self-Review Checklist**:
- [ ] All API endpoints have test coverage
- [ ] Happy path and error paths tested
- [ ] Coverage report shows >80% for routes/
- [ ] Tests run in <30 seconds total
- [ ] No flaky tests (run 10 times, all pass)
- [ ] Can run tests in parallel: `pytest -n auto`
- [ ] Test fixtures are reusable

**Runbook**:
```bash
# 1. Install test dependencies
pip install pytest pytest-cov pytest-xdist httpx

# 2. Run all integration tests
pytest tests/integration/ -v

# 3. Check coverage
pytest tests/integration/ --cov=src/web/routes --cov-report=html

# 4. Open coverage report
# open htmlcov/index.html

# 5. Run tests in parallel
pytest tests/integration/ -n auto -v

# 6. Verify no flakes
for i in {1..10}; do pytest tests/integration/ -q || break; done
```

---

## 🟡 P1 HIGH PRIORITY TASKS (Operational excellence)

### TASK-P1-001: Implement Flow Analysis APIs

**Priority**: P1 - HIGH  
**Effort**: 10 hours  
**Impact**: Monitor agent data flows and detect bottlenecks

**Role**: Senior engineer. Implement realtime flow monitoring endpoints.

**Scope**:
- Fix: Flow analysis features exist in CLI (`viz flows`, `viz bottlenecks`) but no web API
- Create: `/api/flows/*` endpoints for flow monitoring
- Allowed paths: `src/web/routes/` (new file: `flows.py`), `src/visualization/agent_flow_monitor.py`, `tests/integration/`
- Forbidden: Modifying core event bus or agent execution logic

**Required Endpoints**:
```
GET /api/flows/realtime                    - Active flows in last N seconds (query param: window=60)
GET /api/flows/history/{correlation_id}    - Historical flow for specific job/correlation
GET /api/flows/bottlenecks                 - Detect slow agents/stages (query param: threshold_ms=1000)
GET /api/flows/active                      - Currently executing flows
```

**Acceptance Checks**:
1. CLI: `curl http://127.0.0.1:8080/api/flows/realtime` returns active agent flows
2. Web: Create job, poll `/api/flows/realtime` during execution, see agent transitions
3. Bottlenecks: `curl http://127.0.0.1:8080/api/flows/bottlenecks` identifies slow agents
4. Tests: `pytest tests/integration/test_flows_api.py -v`
5. CLI commands still work: `python ucop_cli.py viz flows`

**Deliverables**:
1. New file: `src/web/routes/flows.py` with 4 endpoints
2. Models: `FlowEvent`, `FlowHistory`, `BottleneckReport`, `ActiveFlow`
3. Integration with `AgentFlowMonitor` from visualization module
4. WebSocket endpoint (optional): `/ws/flows` for realtime updates
5. Tests covering flow tracking during job execution

**Design Guidance**:
- Flow data comes from event bus events (agent start/complete)
- Use `AgentFlowMonitor` class if it exists, else create thin wrapper
- Realtime: Return flows from last N seconds (default 60)
- Bottlenecks: Compare agent execution times, flag >threshold
- Correlation ID: Job ID or workflow execution ID

**Hard Rules**:
- Read-only endpoints (don't modify flows)
- Flows should auto-expire after configured TTL
- Use in-memory store for flows (don't persist to DB)
- Return empty list if no flows, not 404

**Self-Review Checklist**:
- [ ] All 4 endpoints implemented and working
- [ ] Can track agent flows during live job execution
- [ ] Bottleneck detection identifies slow agents accurately
- [ ] Historical lookup by correlation_id works
- [ ] Tests verify flow data structure and completeness
- [ ] CLI flow commands still functional

**Runbook**:
```bash
# 1. Start server
python start_web.py &

# 2. Start a job
JOB_ID=$(curl -X POST http://127.0.0.1:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic":"test flow","template":"default_blog"}' | jq -r .job_id)

# 3. Monitor realtime flows
curl "http://127.0.0.1:8080/api/flows/realtime?window=30" | jq

# 4. Check bottlenecks
curl http://127.0.0.1:8080/api/flows/bottlenecks | jq

# 5. Get flow history
curl http://127.0.0.1:8080/api/flows/history/$JOB_ID | jq

# 6. Run tests
pytest tests/integration/test_flows_api.py -v
```

---

### TASK-P1-002: Build Monitoring Dashboard UI

**Priority**: P1 - HIGH  
**Effort**: 20 hours  
**Impact**: Operations team can monitor system without CLI

**Role**: Senior fullstack engineer. Build React monitoring dashboard using existing API endpoints.

**Scope**:
- Fix: Monitoring APIs exist but no UI to display them
- Create: React monitoring dashboard with metrics, health, agents, flows
- Allowed paths: `src/web/static/src/` (new folder: `monitoring/`), `src/web/static/src/App.jsx`
- Forbidden: Modifying backend APIs (use existing endpoints)

**Required Dashboard Sections**:
```
1. System Health
   - API: GET /api/system/health
   - Display: Status, uptime, component health

2. Agent Status
   - API: GET /api/monitoring/agents
   - Display: Agent list, status, last execution time

3. Active Jobs
   - API: GET /api/jobs?status=running
   - Display: Running jobs, progress, current stage

4. Realtime Flows
   - API: GET /api/flows/realtime (from TASK-P1-001)
   - Display: Agent flow diagram, bottlenecks highlighted

5. System Metrics
   - API: GET /api/monitoring/system
   - Display: CPU, memory, active jobs, queue depth
```

**Acceptance Checks**:
1. Web: Navigate to http://127.0.0.1:8080/monitoring - dashboard loads
2. All 5 sections render with live data
3. Auto-refresh every 10 seconds (configurable)
4. Click agent → shows agent details modal
5. Click job → navigates to job detail page
6. WebSocket integration for realtime updates (bonus)

**Deliverables**:
1. New React components:
   - `MonitoringDashboard.jsx` - Main container
   - `SystemHealthCard.jsx` - Health display
   - `AgentStatusGrid.jsx` - Agent grid
   - `ActiveJobsList.jsx` - Jobs table
   - `FlowDiagram.jsx` - Flow visualization
   - `SystemMetricsChart.jsx` - Metrics charts

2. Hooks:
   - `useMonitoring.js` - Custom hook for polling APIs
   - `useWebSocket.js` - WebSocket connection (optional)

3. Routing:
   - Add `/monitoring` route in `App.jsx`
   - Navigation link in main menu

4. Tests:
   - Component tests using React Testing Library
   - Mock API responses
   - Test auto-refresh behavior

**Design Guidance**:
- Use existing UI component library (Tailwind/shadcn)
- Poll endpoints every 10s (don't overwhelm server)
- Show loading states during data fetch
- Handle error states (API down, timeout)
- Use charts library: recharts (already imported)
- Flow diagram: Use react-flow or similar

**Hard Rules**:
- No new backend APIs (use existing only)
- Responsive design (mobile-friendly)
- Accessible (ARIA labels, keyboard navigation)
- No browser console errors
- Graceful degradation if endpoints fail

**Self-Review Checklist**:
- [ ] Dashboard loads and displays live data
- [ ] All 5 sections rendering correctly
- [ ] Auto-refresh works without memory leaks
- [ ] Click interactions work (modals, navigation)
- [ ] Responsive on mobile and desktop
- [ ] No React warnings in console
- [ ] Tests pass: `npm test`

**Runbook**:
```bash
# 1. Install dependencies (if new)
cd src/web/static
npm install recharts react-flow

# 2. Build React app
npm run build

# 3. Start server
cd ../../..
python start_web.py &

# 4. Open dashboard
# Navigate to http://127.0.0.1:8080/monitoring

# 5. Verify auto-refresh
# Watch network tab - should poll every 10s

# 6. Run frontend tests
cd src/web/static
npm test
```

---

### TASK-P1-003: Add Debug Session Management

**Priority**: P1 - HIGH  
**Effort**: 12 hours  
**Impact**: Step debugging workflows from web UI

**Role**: Senior engineer. Implement session-based debugging with breakpoints and step control.

**Scope**:
- Fix: Basic debug endpoints exist but lack session management
- Extend: `/api/debug/*` with session support (or use unmounted `/mcp/debug/*`)
- Allowed paths: `src/web/routes/debug.py`, `src/visualization/workflow_debugger.py`, `tests/integration/`
- Forbidden: Modifying workflow execution engine internals

**Required Endpoints** (extend existing or use MCP):
```
POST   /api/debug/sessions                          - Create debug session for job
GET    /api/debug/sessions/{session_id}             - Get session state
DELETE /api/debug/sessions/{session_id}             - End session
POST   /api/debug/sessions/{session_id}/breakpoints - Add breakpoint
DELETE /api/debug/sessions/{session_id}/breakpoints/{bp_id} - Remove breakpoint
POST   /api/debug/sessions/{session_id}/step        - Step to next breakpoint
POST   /api/debug/sessions/{session_id}/continue    - Continue execution
GET    /api/debug/sessions/{session_id}/trace       - Get execution trace
```

**Acceptance Checks**:
1. Create job in paused mode: `curl -X POST /api/jobs?debug=true`
2. Create debug session: `curl -X POST /api/debug/sessions -d '{"job_id":"..."}'`
3. Add breakpoint: `curl -X POST /api/debug/sessions/{sid}/breakpoints -d '{"agent":"outline_creation_node"}'`
4. Step through: `curl -X POST /api/debug/sessions/{sid}/step`
5. Tests: `pytest tests/integration/test_debug_sessions.py -v`

**Deliverables**:
1. Enhanced `src/web/routes/debug.py` with session management
2. Models: `DebugSession`, `BreakpointConfig`, `StepResult`, `ExecutionTrace`
3. Integration with `WorkflowDebugger` from visualization module
4. Session state stored in memory (or Redis if available)
5. Tests for step debugging a simple workflow

**Design Guidance**:
- Debug session = paused job + breakpoints + step control
- When job hits breakpoint, pause and return control to API
- Step = resume until next breakpoint or completion
- Continue = remove all breakpoints and resume
- Trace = log of all agent executions in job
- Sessions should timeout after inactivity

**Hard Rules**:
- Don't break normal job execution (debug is opt-in)
- Session state in-memory (expire after 1 hour idle)
- Breakpoints by agent name or step number
- Step must be synchronous (wait for next break)
- Trace includes: agent, input, output, duration

**Self-Review Checklist**:
- [ ] Can create debug session for any job
- [ ] Breakpoints pause execution correctly
- [ ] Step control advances to next breakpoint
- [ ] Trace shows complete execution path
- [ ] Session cleanup on timeout/delete
- [ ] Tests verify step-through workflow
- [ ] Existing debug endpoints still work

**Runbook**:
```bash
# 1. Start server
python start_web.py &

# 2. Create job with debug enabled
JOB_ID=$(curl -X POST http://127.0.0.1:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic":"debug test","template":"default_blog","debug":true}' | jq -r .job_id)

# 3. Create debug session
SESSION_ID=$(curl -X POST http://127.0.0.1:8080/api/debug/sessions \
  -H "Content-Type: application/json" \
  -d "{\"job_id\":\"$JOB_ID\"}" | jq -r .session_id)

# 4. Add breakpoint on outline creation
curl -X POST http://127.0.0.1:8080/api/debug/sessions/$SESSION_ID/breakpoints \
  -H "Content-Type: application/json" \
  -d '{"agent":"outline_creation_node"}'

# 5. Step through execution
curl -X POST http://127.0.0.1:8080/api/debug/sessions/$SESSION_ID/step

# 6. Get execution trace
curl http://127.0.0.1:8080/api/debug/sessions/$SESSION_ID/trace | jq

# 7. Run tests
pytest tests/integration/test_debug_sessions.py -v
```

---

### TASK-P1-004: Agent Health Monitoring API

**Priority**: P1 - HIGH  
**Effort**: 8 hours  
**Impact**: Detect failing agents in production

**Role**: Senior engineer. Add health checks and failure tracking for all agents.

**Scope**:
- Fix: Can list agents but no health status or error tracking
- Create: `/api/agents/health` endpoints with failure metrics
- Allowed paths: `src/web/routes/agents.py`, `src/orchestration/monitor.py`, `tests/integration/`
- Forbidden: Modifying agent implementations

**Required Endpoints**:
```
GET /api/agents/health                      - Overall agent health summary
GET /api/agents/{agent_id}/health           - Health for specific agent
GET /api/agents/{agent_id}/failures         - Recent failures for agent
POST /api/agents/{agent_id}/health/reset    - Reset health metrics
```

**Health Metrics to Track**:
- Total executions
- Successful executions
- Failed executions
- Last execution time
- Average execution duration
- Error rate (last 100 executions)
- Current status: healthy, degraded, failing

**Acceptance Checks**:
1. CLI: `curl http://127.0.0.1:8080/api/agents/health` shows all agents
2. Web: Run jobs, then check health - should show execution counts
3. Failure tracking: Failed agent execution appears in `/api/agents/{id}/failures`
4. Tests: `pytest tests/integration/test_agent_health.py -v`
5. Health status changes based on error rate

**Deliverables**:
1. Extend `src/web/routes/agents.py` with health endpoints
2. Models: `AgentHealth`, `HealthSummary`, `FailureReport`
3. Health tracking in `src/orchestration/monitor.py` or new `AgentHealthMonitor` class
4. Metrics stored in-memory with sliding window (last 100 executions)
5. Tests verifying health tracking during job execution

**Design Guidance**:
- Track metrics via event bus (agent_started, agent_completed, agent_failed)
- Health status thresholds:
  - Healthy: <5% error rate
  - Degraded: 5-20% error rate
  - Failing: >20% error rate
- Failures list: Last 10 failures with error messages
- Reset endpoint: Clear metrics (useful after fixing agent)

**Hard Rules**:
- Don't slow down agent execution (async tracking)
- Metrics in-memory (no DB persistence)
- Thread-safe metric updates
- Failures should include: timestamp, error, job_id, input

**Self-Review Checklist**:
- [ ] All agents have health tracking
- [ ] Health status updates based on executions
- [ ] Failure details captured with context
- [ ] Metrics reset works correctly
- [ ] Tests verify health transitions (healthy→degraded→failing)
- [ ] No performance impact on job execution

**Runbook**:
```bash
# 1. Start server
python start_web.py &

# 2. Check initial health (all agents should be "unknown")
curl http://127.0.0.1:8080/api/agents/health | jq

# 3. Run some jobs
for i in {1..5}; do
  curl -X POST http://127.0.0.1:8080/api/generate \
    -H "Content-Type: application/json" \
    -d '{"topic":"health test '$i'","template":"default_blog"}'
done

# 4. Check health after executions
curl http://127.0.0.1:8080/api/agents/health | jq

# 5. Check specific agent
curl http://127.0.0.1:8080/api/agents/outline_creation_node/health | jq

# 6. Check failures (if any)
curl http://127.0.0.1:8080/api/agents/outline_creation_node/failures | jq

# 7. Run tests
pytest tests/integration/test_agent_health.py -v
```

---

### TASK-P1-005: WebSocket Integration in React UI

**Priority**: P1 - HIGH  
**Effort**: 8 hours  
**Impact**: Realtime updates without polling

**Role**: Senior frontend engineer. Integrate existing WebSocket endpoints into React UI.

**Scope**:
- Fix: WebSocket endpoints exist but React UI doesn't use them
- Connect: React UI to `/ws/jobs/{job_id}`, `/ws/agents`, `/ws/visual`
- Allowed paths: `src/web/static/src/` (hooks/, components/), No backend changes
- Forbidden: Modifying WebSocket handlers on backend

**Existing WebSocket Endpoints**:
```
/ws/jobs/{job_id}  - Per-job updates (status, progress, stage changes)
/ws/agents         - Agent monitoring (executions, status)
/ws/visual         - Visual workflow updates
```

**Acceptance Checks**:
1. Job detail page: WebSocket updates progress in realtime (no polling)
2. Agent monitor: WebSocket shows agent executions as they happen
3. Workflow viz: WebSocket updates flow diagram in realtime
4. Connection handling: Reconnects on disconnect, shows connection status
5. Tests: Frontend tests mock WebSocket messages

**Deliverables**:
1. Custom hooks:
   - `useJobWebSocket.js` - Connect to job updates
   - `useAgentWebSocket.js` - Connect to agent updates
   - `useWorkflowWebSocket.js` - Connect to visual updates

2. Updated components:
   - `JobDetail.jsx` - Use WebSocket for job updates
   - `AgentMonitor.jsx` - Use WebSocket for agent status
   - `WorkflowVisualizer.jsx` - Use WebSocket for flow updates

3. Connection management:
   - Reconnect on disconnect
   - Show connection status indicator
   - Graceful fallback to polling if WebSocket fails

4. Tests:
   - Test WebSocket connection lifecycle
   - Test message handling
   - Test reconnection logic

**Design Guidance**:
- Use native WebSocket API or `socket.io-client`
- Reconnect with exponential backoff
- Parse JSON messages from server
- Update React state on message receive
- Close connections on component unmount
- Show connection status: connected, connecting, disconnected

**Hard Rules**:
- Must clean up connections (no memory leaks)
- Handle messages out of order
- Don't trust WebSocket exclusively (have polling fallback)
- Connection status visible in UI
- Reconnect max 5 attempts, then fallback

**Self-Review Checklist**:
- [ ] Job page updates in realtime via WebSocket
- [ ] Agent monitor shows live executions
- [ ] Connection status indicator works
- [ ] Reconnects automatically on disconnect
- [ ] Falls back to polling if WebSocket fails
- [ ] No memory leaks (connections closed)
- [ ] Tests verify WebSocket integration

**Runbook**:
```bash
# 1. Install dependencies (if needed)
cd src/web/static
npm install

# 2. Build React app
npm run build

# 3. Start server
cd ../../..
python start_web.py &

# 4. Create a job
JOB_ID=$(curl -X POST http://127.0.0.1:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic":"websocket test","template":"default_blog"}' | jq -r .job_id)

# 5. Open job in browser
# Navigate to http://127.0.0.1:8080/jobs/$JOB_ID

# 6. Open DevTools Network tab
# Filter: WS (WebSocket)
# Verify WebSocket connection established
# Watch messages as job progresses

# 7. Test reconnection
# In DevTools, close WebSocket connection
# Should automatically reconnect

# 8. Run frontend tests
cd src/web/static
npm test
```

---

## Task Execution Order

**Recommended Sequence**:

**Week 1 (P0 Critical)**:
1. TASK-P0-001 (2h) - Mount MCP router FIRST (unblocks P0-004)
2. TASK-P0-004 (2h) - Verify config endpoints work
3. TASK-P0-003 (6h) - Fix/remove legacy UI
4. TASK-P0-002 (8h) - Checkpoint API
5. TASK-P0-005 (12h) - Endpoint tests (run continuously)

**Week 2 (P1 High Priority)**:
6. TASK-P1-001 (10h) - Flow analysis APIs
7. TASK-P1-004 (8h) - Agent health monitoring
8. TASK-P1-003 (12h) - Debug session management
9. TASK-P1-002 (20h) - Monitoring dashboard
10. TASK-P1-005 (8h) - WebSocket integration

**Total**: 88 hours across 2 weeks

---

## Common Patterns Across All Tasks

### Test Structure
```python
# tests/integration/test_<feature>_api.py
import pytest
from fastapi.testclient import TestClient

def test_happy_path():
    """Test successful operation"""
    pass

def test_not_found():
    """Test 404 handling"""
    pass

def test_invalid_input():
    """Test 400 validation"""
    pass

def test_error_handling():
    """Test 500 graceful failure"""
    pass
```

### Error Response Format
```json
{
  "detail": "Human-readable error message",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2025-11-15T12:00:00Z"
}
```

### Success Response Format
```json
{
  "data": { /* actual response */ },
  "metadata": {
    "timestamp": "2025-11-15T12:00:00Z",
    "request_id": "uuid"
  }
}
```

### WebSocket Message Format
```json
{
  "type": "JOB_UPDATE" | "AGENT_STATUS" | "FLOW_EVENT",
  "data": { /* event-specific data */ },
  "timestamp": "2025-11-15T12:00:00Z"
}
```

---

## Success Criteria for All Tasks

After completing all 10 tasks:

✅ **No 404 errors in any UI (React or legacy if kept)**  
✅ **All API endpoints have test coverage >80%**  
✅ **Monitoring dashboard shows realtime system status**  
✅ **Can debug workflows via web UI (not just CLI)**  
✅ **Web users can manage checkpoints**  
✅ **All features accessible via CLI also accessible via web**  
✅ **Production-ready: can deploy without known blockers**  

---

**Next Steps**: Assign tasks to engineers, execute in recommended order, verify acceptance checks after each task.
