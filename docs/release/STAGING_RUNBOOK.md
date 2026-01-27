# Staging Deployment Runbook - wave5.4-green

**Version:** wave5.4-green
**Target Environment:** Staging
**Last Updated:** 2026-01-27

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Deployment Steps](#deployment-steps)
4. [Verification](#verification)
5. [Smoke Tests](#smoke-tests)
6. [Rollback Procedure](#rollback-procedure)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- **Python**: 3.11 or 3.12 (3.13 works but has minor warnings)
- **Git**: Latest version
- **pip**: Latest version (`python -m pip install --upgrade pip`)

### Optional (Recommended)
- **Docker**: For containerized deployment
- **PostgreSQL**: If using persistent database (instead of in-memory)
- **Redis**: For caching (optional)

### Environment Variables

The following environment variables may be needed for live operation:

```bash
# API Keys (presence only - DO NOT store values in this document)
ANTHROPIC_API_KEY=<your-key>
GOOGLE_API_KEY=<your-key>

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Database (if using external DB)
DATABASE_URL=<your-database-url>

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

**⚠️ SECURITY NOTE:** Never commit API keys or secrets to version control. Use environment variables, secret managers, or .env files (excluded from git).

### Port Requirements
- **8000**: Default web server port (FastAPI/Uvicorn)
- **5432**: PostgreSQL (if using external DB)
- **6379**: Redis (if using caching)

---

## Pre-Deployment Checklist

- [ ] **Backup Current State**
  - [ ] Database backup (if applicable)
  - [ ] Configuration backup
  - [ ] Note current deployed version/commit

- [ ] **Environment Preparation**
  - [ ] Staging environment is accessible
  - [ ] Sufficient disk space available (min 2GB free)
  - [ ] Network connectivity verified
  - [ ] API keys available (if needed for live tests)

- [ ] **Code Preparation**
  - [ ] Repository cloned or updated
  - [ ] Tag `wave5.4-green` exists remotely
  - [ ] No uncommitted local changes

---

## Deployment Steps

### Step 1: Clone/Update Repository

```bash
# If first deployment
git clone https://github.com/babar-raza/content-generator.git
cd content-generator

# If updating existing deployment
cd content-generator
git fetch --all --tags
```

### Step 2: Checkout Release Tag

```bash
# Checkout the specific release tag
git checkout wave5.4-green

# Verify you're on the correct commit
git rev-parse HEAD
# Expected: 83925651a369a9a9fff1dca19971be6dec40a321
```

### Step 3: Create Virtual Environment

```bash
# Create fresh venv for this release
python -m venv .venv_staging

# Activate the venv
# Windows
.venv_staging\Scripts\activate

# Linux/Mac
source .venv_staging/bin/activate
```

### Step 4: Install Dependencies

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installation
pip list | grep fastapi
pip list | grep langchain
```

### Step 5: Run Verification Suite

```bash
# Run all verification gates (mock mode - no API keys required)
# Windows
powershell -ExecutionPolicy Bypass -File scripts/verify_all.ps1

# Linux/Mac
bash scripts/verify_all.sh
```

**Expected Results:**
- Integration tests: ✅ 816 passed / 14 skipped
- E2E mock tests: ✅ 43 passed
- Capability tests: ✅ 94/94 passed

**Action if verification fails:**
- Review failure logs in `reports/_local_verify/<timestamp>/`
- Check dependencies are correctly installed
- Verify Python version compatibility
- DO NOT proceed to deployment if critical gates fail

### Step 6: Start Web Server

#### Option A: Development Mode (Recommended for Staging)

```bash
# Start server with auto-reload
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000
```

#### Option B: Production Mode

```bash
# Start with multiple workers (no auto-reload)
uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Option C: Using Python Directly

```python
# Alternative: Direct Python execution
python -c "from src.web.app import create_app; import uvicorn; app = create_app(); uvicorn.run(app, host='0.0.0.0', port=8000)"
```

**Expected Output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## Verification

### Health Endpoints

Once the server is running, verify health endpoints:

```bash
# 1. Root health check
curl http://localhost:8000/

# Expected: 200 OK
# {"status":"healthy","version":"..."}

# 2. API health check
curl http://localhost:8000/api/health

# Expected: 200 OK
# {"status":"ok","timestamp":"...","services":{...}}

# 3. Agents health summary
curl http://localhost:8000/api/agents/health

# Expected: 200 OK
# {"total_agents":N,"healthy":N,"degraded":0,"failed":0}

# 4. OpenAPI documentation
curl http://localhost:8000/docs

# Expected: 200 OK (HTML page)
```

### MCP Endpoint Examples

```bash
# 1. List MCP tools
curl -X POST http://localhost:8000/mcp/tools/list \
  -H "Content-Type: application/json" \
  -d '{}'

# Expected: List of available MCP tools

# 2. Get agent list
curl http://localhost:8000/api/agents/list

# Expected: Array of agent definitions

# 3. Config snapshot
curl http://localhost:8000/api/config/snapshot

# Expected: Current configuration state
```

---

## Smoke Tests

### Manual Smoke Test Checklist

Execute these tests to verify core functionality:

- [ ] **Web Server**
  - [ ] Health endpoints respond (200 OK)
  - [ ] OpenAPI docs accessible at `/docs`
  - [ ] Static files load (if applicable)

- [ ] **API Endpoints**
  - [ ] Agents list returns data
  - [ ] Workflows list returns data
  - [ ] Config snapshot returns valid JSON

- [ ] **MCP Integration**
  - [ ] MCP tools list endpoint works
  - [ ] MCP protocol version check

- [ ] **Database/Storage**
  - [ ] Vector store initializes (check logs)
  - [ ] Checkpoint storage accessible

### Automated Smoke Test

```bash
# Run E2E smoke tests
pytest tests/e2e_mock/ -v -k "smoke"

# Run web routes smoke tests
pytest tests/e2e_mock/test_web_routes_smoke.py -v
```

**Expected:** All smoke tests pass

---

## Rollback Procedure

If deployment fails or critical issues are discovered:

### Step 1: Stop Current Server

```bash
# Find the process
ps aux | grep uvicorn

# Kill the process
kill <process-id>

# Or use CTRL+C if running in foreground
```

### Step 2: Checkout Previous Version

```bash
# List available tags
git tag -l

# Checkout previous stable tag (example)
git checkout wave5.3-stable

# Or checkout specific commit
git checkout <previous-commit-sha>
```

### Step 3: Reinstall Dependencies

```bash
# Recreate venv or update dependencies
pip install -r requirements.txt
```

### Step 4: Restart Server

```bash
# Start with previous version
uvicorn src.web.app:app --host 0.0.0.0 --port 8000
```

### Step 5: Verify Rollback

```bash
# Check health endpoint
curl http://localhost:8000/api/health

# Verify version in response matches expected previous version
```

### Step 6: Document Rollback

Create an incident report documenting:
- Time of rollback
- Reason for rollback
- Issues encountered
- Steps taken
- Current deployed version

---

## Troubleshooting

### Issue: Port Already in Use

**Error:** `OSError: [Errno 48] Address already in use`

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill the process
kill <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows

# Or use a different port
uvicorn src.web.app:app --port 8001
```

### Issue: Import Errors

**Error:** `ModuleNotFoundError: No module named 'src'`

**Solution:**
```bash
# Ensure you're in the repository root
pwd  # Should show .../content-generator

# Ensure venv is activated
which python  # Should show .venv path

# Reinstall dependencies
pip install -r requirements.txt

# Verify PYTHONPATH
export PYTHONPATH=.  # Add current directory to Python path
```

### Issue: Database Connection Errors

**Error:** Database connection failed or vector store init errors

**Solution:**
```bash
# Check if external database is required
# Default configuration uses in-memory storage

# If using PostgreSQL, verify connection
psql -h <host> -U <user> -d <database>

# Check DATABASE_URL environment variable
echo $DATABASE_URL

# For ChromaDB vector store, ensure directory exists
mkdir -p data/chroma
```

### Issue: API Key Errors (Live Mode)

**Error:** `AuthenticationError` or `API key not found`

**Solution:**
```bash
# For staging, API keys should be in environment
export ANTHROPIC_API_KEY=your-key
export GOOGLE_API_KEY=your-key

# Or use .env file
# Create .env in repo root (already in .gitignore)
echo "ANTHROPIC_API_KEY=your-key" >> .env
echo "GOOGLE_API_KEY=your-key" >> .env

# Verify the app loads .env (check src/config/ for dotenv usage)
```

### Issue: Tests Failing

**Problem:** Verification tests fail unexpectedly

**Solution:**
```bash
# Run tests with verbose output
pytest tests/integration/ -v -s --tb=long

# Check for specific failures
pytest tests/integration/<failing_test>.py -v

# Review test logs
cat reports/_local_verify/<timestamp>/*

# Common causes:
# - Wrong Python version (ensure 3.11 or 3.12)
# - Missing dependencies (run pip install -r requirements.txt again)
# - Port conflicts (ensure 8000 is free)
# - Environment variables missing (for live tests only)
```

---

## Post-Deployment

### Monitoring

After successful deployment, monitor:

1. **Application Logs**
   ```bash
   tail -f logs/app.log  # If logging to file
   # Or check uvicorn stdout
   ```

2. **System Resources**
   ```bash
   # CPU and memory usage
   top | grep python
   # Or use htop
   ```

3. **Health Endpoints**
   ```bash
   # Set up periodic health checks (every 5 minutes)
   watch -n 300 curl -s http://localhost:8000/api/health
   ```

### Success Criteria

Deployment is successful when:
- ✅ All health endpoints return 200 OK
- ✅ API endpoints respond within expected latency (<500ms for health checks)
- ✅ No critical errors in logs
- ✅ Smoke tests pass
- ✅ System resources are within normal ranges

---

## Support & Escalation

### Documentation
- **Repository:** https://github.com/babar-raza/content-generator
- **Release Notes:** https://github.com/babar-raza/content-generator/releases/tag/wave5.4-green
- **System Overview:** `docs/system-overview.md`
- **API Documentation:** http://localhost:8000/docs (when running)

### Escalation Path
1. Check troubleshooting section above
2. Review logs in `reports/` and application logs
3. Check GitHub issues: https://github.com/babar-raza/content-generator/issues
4. Contact development team with:
   - Deployment timestamp
   - Error logs
   - Steps to reproduce
   - Environment details (OS, Python version, etc.)

---

## Appendix

### Quick Reference Commands

```bash
# Clone and setup
git clone https://github.com/babar-raza/content-generator.git
cd content-generator
git checkout wave5.4-green
python -m venv .venv_staging
source .venv_staging/bin/activate  # Linux/Mac
.venv_staging\Scripts\activate     # Windows
pip install -r requirements.txt

# Verify
powershell -ExecutionPolicy Bypass -File scripts/verify_all.ps1  # Windows
bash scripts/verify_all.sh                                        # Linux/Mac

# Deploy
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000

# Health check
curl http://localhost:8000/api/health

# Rollback
git checkout <previous-tag>
pip install -r requirements.txt
uvicorn src.web.app:app --host 0.0.0.0 --port 8000
```

---

**End of Staging Deployment Runbook**
