# Operating Manual - Content Generator (UCOP)

**Version:** wave5.4-green (commit: 2a6f363795eba57f42092097aacdb03c1d3a2ce5)
**Last Updated:** 2026-01-27
**Purpose:** Single source of truth for running, verifying, deploying, and troubleshooting UCOP

---

## Table of Contents

1. [What the System Does](#what-the-system-does)
2. [Quickstart (Local)](#quickstart-local)
3. [Verification Matrix](#verification-matrix)
4. [CI Behavior](#ci-behavior)
5. [Deployment & Staging](#deployment--staging)
6. [Troubleshooting Playbook](#troubleshooting-playbook)
7. [Change Policy](#change-policy)

---

## What the System Does

### System Overview

The **Unified Content Operations Platform (UCOP)** is a production-ready, autonomous content generation system that transforms knowledge base articles into SEO-optimized blog posts using 38 specialized AI agents orchestrated via LangGraph workflows.

**Key Capabilities:**
- **Content Pipeline**: Ingestion → Planning → Generation → Code Generation (conditional) → SEO Optimization → Publishing → Validation
- **38 Specialized Agents**: Organized into 7 categories (Content, SEO, Code, Publishing, Research, Support, Ingestion)
- **Multi-LLM Support**: Intelligent fallback cascade across Ollama (local), Google Gemini, and OpenAI
- **Dual Interface**: CLI (23 commands) and FastAPI-based Web API with React UI
- **Event-Driven**: LangGraph workflows with checkpoint persistence and hot-reload capabilities

### Architecture Layers

```
┌────────────────────────────────────────────────────┐
│         CLI / Web UI (FastAPI + React)             │
├────────────────────────────────────────────────────┤
│      Orchestration Layer (LangGraph + Jobs)        │
├────────────────────────────────────────────────────┤
│          Agent Mesh (38 Agents)                    │
│  Content│SEO│Code│Publishing│Research│Support      │
├────────────────────────────────────────────────────┤
│     Engine & Services (Templates, Validation)      │
├────────────────────────────────────────────────────┤
│  LLM Providers (Ollama│Gemini│OpenAI) + Storage    │
└────────────────────────────────────────────────────┘
```

### Web API + MCP Interface

**FastAPI Web Server:**
- **Port**: 8000 (default)
- **Health Endpoints**: `/`, `/api/health`, `/api/agents/health`
- **OpenAPI Docs**: `/docs` (Swagger UI)
- **Core APIs**: `/api/agents/*`, `/api/workflows/*`, `/api/config/*`

**MCP (Model Context Protocol):**
- **Endpoint**: `/mcp/tools/list`
- **Purpose**: Tool discovery and invocation for MCP-compliant agents
- **Protocol**: JSON-RPC style interface for tool registration

### Mock vs Live Modes

| Mode | Purpose | Services | Data | Speed | Use Case |
|------|---------|----------|------|-------|----------|
| **Mock** (default) | Fast testing | Mocked | Synthetic | Fast | CI/CD, unit tests |
| **Live** | Real validation | Real LLMs | Sample data | Slow | E2E validation, production |

**Mode Control:**
- Environment variable: `TEST_MODE=live` (default: `mock`)
- Engine factory auto-switches: `UnifiedEngine` (mock) vs `ProductionExecutionEngine` (live)
- Marker: `@pytest.mark.live` for live-only tests

**Live E2E Testing:**
For comprehensive end-to-end testing with real Ollama and ChromaDB, see [Live E2E Testing Guide](live_e2e/README.md).

---

## Quickstart (Local)

### Prerequisites

- **Python**: 3.11 or 3.12 (3.13 works with minor warnings)
- **Git**: Latest version
- **pip**: Latest (`python -m pip install --upgrade pip`)
- **Optional**: Ollama (for local LLM), Docker (for containerized deployment)

### Installation Steps

```bash
# 1. Clone repository
git clone https://github.com/babar-raza/content-generator.git
cd content-generator

# 2. Checkout stable release
git checkout wave5.4-green

# 3. Create virtual environment
python -m venv .venv

# 4. Activate venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 5. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 6. Verify installation
python -c "import src; print('Installation successful')"
```

### Running Verification Scripts

**Windows:**
```powershell
# Run all required gates (mock mode)
powershell -ExecutionPolicy Bypass -File scripts/verify_all.ps1

# Include optional live tests (requires API keys)
powershell -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -IncludeLive
```

**Linux/Mac:**
```bash
# Run all required gates (mock mode)
bash scripts/verify_all.sh

# Include optional live tests (requires API keys)
bash scripts/verify_all.sh --live
```

**Expected Output:**
```
[PASS] Unit tests
[PASS] Integration tests
[PASS] E2E mock tests
[PASS] Capability mock tests
All gates passed - ready for release
```

### Starting the Web Server

**Option A: Development Mode (with auto-reload)**
```bash
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000
```

**Option B: Production Mode (multi-worker)**
```bash
uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --workers 4
```

**Option C: Using CLI**
```bash
# Alternative: Use start_web.py if available
python start_web.py
```

**Verify Server is Running:**
```bash
# Health check
curl http://localhost:8000/api/health

# Expected: {"status":"ok","timestamp":"...","services":{...}}
```

### Running CLI Commands

```bash
# List available workflows
python ucop_cli.py viz workflows

# Generate a blog post (requires sample data)
python ucop_cli.py generate \
    --input kb_articles/example.md \
    --output output/ \
    --workflow blog_generation

# List agents
python ucop_cli.py agent list

# View job status
python ucop_cli.py job list --status running
```

---

## Verification Matrix

### Required Gates (MUST Pass for Release)

These gates are **STOP-THE-LINE** failures. Do not merge or deploy if any fail.

| Gate | Command | Purpose | Success Criteria | Failure Policy |
|------|---------|---------|------------------|----------------|
| **1. Integration Tests** | `pytest tests/integration/` | Verify component integration and API contracts | 816 passed / 14 skipped | STOP-THE-LINE |
| **2. E2E Mock Tests** | `pytest tests/e2e_mock/` | End-to-end workflows with mocked services | 43 passed | STOP-THE-LINE |
| **3. Capability Mock** | `python tools/run_capabilities.py --mode mock` | All 94 system capabilities work in isolation | 94/94 passed (100%) | STOP-THE-LINE |

**Key Test Files:**
- Integration: `test_mcp_integration.py`, `test_web_api_parity.py`, `test_config_integration.py`
- E2E Mock: `test_web_routes_smoke.py`, `test_mock_workflows.py`
- Capability: Runs `tools/run_capabilities.py` against all agent capabilities

### Optional Gates (Best Effort)

These gates are informational. Failures should be investigated but do not block merge.

| Gate | Command | Purpose | Prerequisites | Failure Policy |
|------|---------|---------|---------------|----------------|
| **4. Live Tests** | `TEST_MODE=live pytest -m live tests/live/` | Integration with real external services | API keys, network | WARN |
| **5. Capability Live** | `python tools/run_capabilities.py --mode live` | Verify capabilities against real services | API keys, quota | WARN |

**Live Test Prerequisites:**
- `ANTHROPIC_API_KEY` environment variable set
- `GOOGLE_API_KEY` environment variable set
- Network connectivity
- API quota availability
- Sample data in `samples/` directory

**Marker Policy:**
- Tests marked `@pytest.mark.live` require `TEST_MODE=live`
- Tests marked `@pytest.mark.network` are excluded from required gates
- Required gates exclude all `live` and `network` markers

---

## CI Behavior

### Python Version Matrix

| Python Version | Parallelization | Rationale |
|----------------|----------------|-----------|
| **3.11** | `-n 0` (serial) | Stability; some async edge cases with parallel execution |
| **3.12** | `-n auto` (parallel) | Full compatibility; parallel execution stable |
| **3.13** | `-n auto` (parallel) | Experimental; minor warnings expected |

**Configuration:**
```yaml
# .github/workflows/ci.yml (example)
strategy:
  matrix:
    python-version: ['3.11', '3.12']
    include:
      - python-version: '3.11'
        pytest-args: '-n 0'  # Serial execution
      - python-version: '3.12'
        pytest-args: '-n auto'  # Parallel execution
```

### Marker Policy for CI

**Required Gates (CI):**
- Excludes: `live`, `network`, `slow` (optionally)
- Includes: `integration`, `e2e` (mock only), `smoke`
- Command: `pytest tests/integration tests/e2e_mock -m "not live and not network"`

**Optional Gates (CI):**
- Includes: `live`
- Runs only if `ANTHROPIC_API_KEY` and `GOOGLE_API_KEY` secrets configured
- Uses `continue-on-error: true` in GitHub Actions
- Command: `TEST_MODE=live pytest -m live tests/live/`

### How to Read CI Failures

**Step 1: Identify the failing gate**
```
[FAIL] Integration tests
[FAIL] E2E mock tests
[FAIL] Capability mock tests
```

**Step 2: Download artifacts (CI only)**
- GitHub Actions uploads test reports on failure (retention: 7 days)
- Path: `reports/_ci/<gate>/`

**Step 3: Reproduce locally**
```bash
# Reproduce integration test failure
pytest tests/integration/ -v --tb=long

# Reproduce specific test
pytest tests/integration/test_mcp_integration.py::test_specific_case -v -s
```

**Step 4: Review logs**
```bash
# If using verify_all scripts, logs are saved to:
cat reports/_local_verify/<timestamp>/<gate>.txt
```

**Step 5: Fix and re-verify**
```bash
# After fixing, run verification again
./scripts/verify_all.sh  # or .ps1 on Windows
```

### Determinism & Reproducibility

**Environment Settings for CI:**
```bash
# Ensure consistent hash ordering
export PYTHONHASHSEED=0

# Explicit test mode
export TEST_MODE=mock

# Pytest timeout
export PYTEST_TIMEOUT=300
```

**Cache Considerations:**
- ChromaDB uses in-memory mock for tests (no persistent state)
- Each test run starts with clean state
- No cross-test pollution

---

## Deployment & Staging

### Staging Runbook Reference

For detailed staging deployment, see: [docs/release/STAGING_RUNBOOK.md](release/STAGING_RUNBOOK.md)

**Quick Summary:**
1. Clone/update repository
2. Checkout release tag: `git checkout wave5.4-green`
3. Create venv: `python -m venv .venv_staging`
4. Install dependencies: `pip install -r requirements.txt`
5. Run verification: `scripts/verify_all.ps1` or `scripts/verify_all.sh`
6. Start server: `uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000`
7. Verify health: `curl http://localhost:8000/api/health`

### Minimal Environment Variables (Names Only)

**Required for Live Operation:**
- `ANTHROPIC_API_KEY` - Anthropic API key (NEVER log or commit)
- `GOOGLE_API_KEY` - Google API key (NEVER log or commit)

**Optional Configuration:**
- `HOST` - Server host (default: `0.0.0.0`)
- `PORT` - Server port (default: `8000`)
- `WORKERS` - Number of workers (default: `4`)
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `LOG_FORMAT` - Log format (default: `json`)
- `DATABASE_URL` - External database URL (default: in-memory)
- `PYTHONHASHSEED` - Hash seed for determinism (CI: `0`)
- `TEST_MODE` - Test mode (`mock` or `live`, default: `mock`)

**Security Note:** Use environment variables, secret managers, or `.env` files (excluded from git). NEVER commit secrets to version control.

### Rollback Steps

**Step 1: Stop current server**
```bash
# Find process
ps aux | grep uvicorn  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill process
kill <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows
```

**Step 2: Checkout previous stable tag**
```bash
git tag -l  # List tags
git checkout wave5.3-stable  # Example previous tag
```

**Step 3: Reinstall dependencies**
```bash
pip install -r requirements.txt
```

**Step 4: Restart server**
```bash
uvicorn src.web.app:app --host 0.0.0.0 --port 8000
```

**Step 5: Verify rollback**
```bash
curl http://localhost:8000/api/health
# Verify version in response
```

**Step 6: Document rollback**
- Create incident report with: time, reason, issues, steps, current version

---

## Troubleshooting Playbook

### Common Failures

#### 1. Capability Runner Failures

**Symptom:** `tools/run_capabilities.py` exits with non-zero status, some capabilities fail

**Diagnosis:**
```bash
# Check capability runner output
cat reports/_local_verify/<timestamp>/capability_mock.txt

# Look for specific capability failures
grep "FAIL" reports/_local_verify/<timestamp>/capability_mock.txt
```

**Common Causes:**
- Missing mock fixtures in `tests/fixtures/`
- Import errors in agent modules
- Timeout (default: 180 seconds per capability)
- Reports directory permissions

**Fix:**
```bash
# Ensure reports directory exists and is writable
mkdir -p reports/_local_verify

# Run with increased timeout
python tools/run_capabilities.py --mode mock --timeout_seconds 300

# Run specific capability in debug mode
python tools/run_capabilities.py --mode mock --capability <name> --debug
```

#### 2. Reports Directory Issues

**Symptom:** Tests fail with "Permission denied" or "Directory not found" when writing reports

**Diagnosis:**
```bash
# Check directory exists
ls -ld reports/

# Check permissions
ls -l reports/
```

**Common Causes:**
- `reports/` directory doesn't exist
- Insufficient permissions
- Disk full

**Fix:**
```bash
# Create directory with correct permissions
mkdir -p reports/_local_verify
chmod 755 reports/

# Check disk space
df -h .

# If disk full, clean up old reports
rm -rf reports/_local_verify/20260101-*
```

#### 3. Network Calls in Required Tests

**Symptom:** Required tests (integration, e2e_mock) fail with network errors or timeouts

**Diagnosis:**
```bash
# Run tests with network tracing
pytest tests/integration/ -v -s --tb=long 2>&1 | grep -i "connection\|network\|timeout"
```

**Common Causes:**
- Test incorrectly calling real LLM APIs instead of mocks
- Missing `@pytest.mark.network` or `@pytest.mark.live` marker
- Mock not properly configured in `tests/conftest.py`

**Fix:**
```bash
# Ensure test uses mock mode
# In test file, verify:
from src.utils.testing_mode import is_mock_mode
assert is_mock_mode()

# Patch external service calls
from unittest.mock import patch
with patch('src.services.llm_service.LLMService.generate') as mock_gen:
    mock_gen.return_value = "mock response"
    # Run test
```

#### 4. Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'src'`

**Diagnosis:**
```bash
# Check Python path
echo $PYTHONPATH

# Check venv activation
which python  # Should show .venv path
```

**Fix:**
```bash
# Ensure you're in repo root
cd /path/to/content-generator
pwd  # Verify

# Activate venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate  # Windows

# Add current dir to PYTHONPATH
export PYTHONPATH=.:$PYTHONPATH  # Linux/Mac
set PYTHONPATH=.;%PYTHONPATH%  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### 5. Port Already in Use

**Symptom:** `OSError: [Errno 48] Address already in use` when starting server

**Diagnosis:**
```bash
# Find process using port 8000
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows
```

**Fix:**
```bash
# Kill existing process
kill <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows

# Or use different port
uvicorn src.web.app:app --port 8001
```

### How to Rerun Locally

**Rerun entire verification suite:**
```bash
# Windows
powershell -ExecutionPolicy Bypass -File scripts/verify_all.ps1

# Linux/Mac
bash scripts/verify_all.sh
```

**Rerun specific gate:**
```bash
# Integration tests
pytest tests/integration/ -v

# E2E mock tests
pytest tests/e2e_mock/ -v

# Capability mock tests
python tools/run_capabilities.py --mode mock --outdir reports/debug
```

**Rerun specific test:**
```bash
# Run single test with full output
pytest tests/integration/test_mcp_integration.py::test_mcp_tools_list -v -s --tb=long
```

**Rerun with debugging:**
```bash
# Enable pytest debugging
pytest --pdb tests/integration/test_failing.py

# Add print statements (mock mode only, no network calls)
pytest -s tests/unit/test_my_module.py
```

### How to Collect Evidence

**For Bug Reports:**
```bash
# 1. Run verification with timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
./scripts/verify_all.sh > reports/debug_${TIMESTAMP}.txt 2>&1

# 2. Collect system info
python --version > reports/sysinfo_${TIMESTAMP}.txt
pip list >> reports/sysinfo_${TIMESTAMP}.txt
uname -a >> reports/sysinfo_${TIMESTAMP}.txt

# 3. Collect git state
git rev-parse HEAD > reports/gitinfo_${TIMESTAMP}.txt
git status --porcelain >> reports/gitinfo_${TIMESTAMP}.txt
git log -n 5 --oneline >> reports/gitinfo_${TIMESTAMP}.txt

# 4. Package evidence
tar -czf evidence_${TIMESTAMP}.tar.gz reports/debug_${TIMESTAMP}.txt reports/sysinfo_${TIMESTAMP}.txt reports/gitinfo_${TIMESTAMP}.txt reports/_local_verify/
```

**For Performance Issues:**
```bash
# Run with profiling
python -m cProfile -o profile.stats tools/run_capabilities.py --mode mock

# Analyze profile
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

---

## Change Policy

### Never Commit Reports/Output

**Excluded via `.gitignore`:**
```
reports/
output/
logs/
*.log
htmlcov/
.coverage
.pytest_cache/
```

**Before committing:**
```bash
# Verify no reports in staging
git status --porcelain | grep reports/
# Should return nothing

# If accidentally staged
git reset HEAD reports/
```

### How to Add New Capabilities/Tests Safely

**Step 1: Create capability definition**
```python
# src/agents/<category>/my_new_agent.py
from src.core.base_agent import BaseAgent

class MyNewAgent(BaseAgent):
    def execute(self, inputs: dict) -> dict:
        # Implementation
        pass
```

**Step 2: Register capability**
```python
# tools/capabilities_registry.py
CAPABILITIES = {
    # ... existing
    "my_new_capability": {
        "agent": "MyNewAgent",
        "category": "content",
        "timeout": 60
    }
}
```

**Step 3: Add mock test**
```python
# tests/unit/test_my_new_agent.py
import pytest
from src.agents.content.my_new_agent import MyNewAgent

def test_my_new_agent_mock():
    agent = MyNewAgent()
    result = agent.execute({"input": "test"})
    assert result is not None
```

**Step 4: Add live test (optional)**
```python
# tests/live/test_my_new_agent_live.py
import pytest

pytestmark = pytest.mark.live

def test_my_new_agent_live(skip_if_no_live_env):
    # Live test with real services
    pass
```

**Step 5: Verify locally**
```bash
# Run unit test
pytest tests/unit/test_my_new_agent.py -v

# Run capability test
python tools/run_capabilities.py --mode mock --capability my_new_capability

# Run full verification
./scripts/verify_all.sh
```

**Step 6: Update documentation**
```markdown
# docs/agents.md
## MyNewAgent
- **Category**: Content
- **Purpose**: [Description]
- **Inputs**: [List]
- **Outputs**: [List]
```

**Step 7: Commit**
```bash
git add src/agents/<category>/my_new_agent.py tests/unit/test_my_new_agent.py docs/agents.md
git commit -m "feat(agents): add MyNewAgent capability"
```

### How to Mark Tests Live/Network

**Marking a test as `live`:**
```python
import pytest

# Option 1: Mark individual test
@pytest.mark.live
def test_with_real_api():
    pass

# Option 2: Mark entire module
pytestmark = pytest.mark.live

# Option 3: Mark test class
@pytest.mark.live
class TestLiveWorkflows:
    def test_workflow_1(self):
        pass
```

**Marking a test as `network`:**
```python
@pytest.mark.network
def test_external_service():
    # Calls external API
    pass
```

**Best Practices:**
- Use `live` for tests that require real LLM services
- Use `network` for tests that make external HTTP calls
- Required gates should NOT have `live` or `network` markers
- Use `skip_if_no_live_env` fixture in live tests to gracefully skip

**Verification:**
```bash
# List all live tests
pytest --collect-only -m live

# List all network tests
pytest --collect-only -m network

# Verify required gates exclude live/network
pytest tests/integration tests/e2e_mock -m "not live and not network" --collect-only
```

---

## Additional Resources

### Documentation Index

- **System Overview**: [docs/system-overview.md](system-overview.md)
- **Architecture**: [docs/architecture.md](architecture.md)
- **Getting Started**: [docs/getting-started.md](getting-started.md)
- **CLI Reference**: [docs/cli-reference.md](cli-reference.md)
- **Web API Reference**: [docs/web-api-reference.md](web-api-reference.md)
- **Testing Guide**: [docs/testing.md](testing.md)
- **Live E2E Testing**: [docs/live_e2e/README.md](live_e2e/README.md)
- **Troubleshooting**: [docs/troubleshooting.md](troubleshooting.md)
- **Release Runbook**: [docs/release/RELEASE_RUNBOOK.md](release/RELEASE_RUNBOOK.md)
- **Staging Runbook**: [docs/release/STAGING_RUNBOOK.md](release/STAGING_RUNBOOK.md)
- **CI Gates**: [docs/release/CI_GATES.md](release/CI_GATES.md)

### Quick Command Reference

```bash
# Verification
./scripts/verify_all.sh                      # Run all gates
pytest tests/integration/ -v                 # Integration tests only
python tools/run_capabilities.py --mode mock # Capability tests

# Server
uvicorn src.web.app:app --reload --port 8000 # Dev server
curl http://localhost:8000/api/health        # Health check

# CLI
python ucop_cli.py --help                    # CLI help
python ucop_cli.py agent list                # List agents
python ucop_cli.py viz workflows             # List workflows

# Testing
pytest -m unit                               # Unit tests only
TEST_MODE=live pytest -m live tests/live/    # Live tests
pytest --cov=src --cov-report=html           # Coverage report

# Debugging
pytest --pdb tests/unit/test_failing.py      # Debug with pdb
pytest -v -s --tb=long                       # Verbose output

# Git
git checkout wave5.4-green                   # Checkout release
git tag -l                                   # List tags
git rev-parse HEAD                           # Current commit
```

---

**End of Operating Manual**

**Maintained By:** Project Closure Agent
**Version History:**
- v1.0.0 (2026-01-27): Initial operating manual for wave5.4-green
