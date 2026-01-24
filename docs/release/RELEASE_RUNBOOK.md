# Content Generator - Release Runbook

## Overview
This runbook documents the release verification process for the content-generator project. It provides one-command verification scripts, explains what "green" means, and ensures reproducible quality gates.

## What Does "Green" Mean?

A release is considered **green** and ready for deployment when ALL of the following gates pass:

### Required Gates (Must Pass)
1. **Unit Tests** - All unit tests in `tests/unit/` pass
2. **Integration Tests** - All integration tests in `tests/integration/` pass
3. **E2E Mock Tests** - All end-to-end tests in `tests/e2e_mock/` pass
4. **Capability Mock Tests** - All 94 capabilities pass in mock mode (100% success rate)

### Optional Gates
5. **Live Tests** - Tests in `tests/live/` (requires environment configuration)
6. **Capability Live Tests** - Capabilities in live mode (requires API keys)

**STOP-THE-LINE:** Do not commit or deploy if any required gate fails. Fix the failure first.

## Quick Start - One-Command Verification

### Windows (PowerShell)
```powershell
# Run all required gates
.\scripts\verify_all.ps1

# Include optional live tests
.\scripts\verify_all.ps1 -IncludeLive
```

### Linux/Mac (Bash)
```bash
# Run all required gates
./scripts/verify_all.sh

# Include optional live tests
./scripts/verify_all.sh --live
```

## What the Verification Scripts Do

Both scripts perform the following steps automatically:

1. **Environment Setup**
   - Create or reuse a verification virtual environment at `.venv_verify/`
   - Install all dependencies from `requirements.txt`

2. **Run Test Suites**
   - Execute `pytest` against `tests/unit/`
   - Execute `pytest` against `tests/integration/`
   - Execute `pytest` against `tests/e2e_mock/`

3. **Run Capability Tests**
   - Execute `tools/run_capabilities.py` in mock mode
   - Verify all 94 capabilities pass
   - Timeout: 180 seconds

4. **Optional Live Mode** (if `--live` or `-IncludeLive` flag provided)
   - Check for required environment variables:
     - `ANTHROPIC_API_KEY`
     - `GOOGLE_API_KEY`
   - Run live tests if environment is configured
   - Skip gracefully if environment is not ready

5. **Generate Report**
   - Save all outputs to `reports/_local_verify/<timestamp>/`
   - Print summary with pass/fail status
   - Exit with non-zero code if any required gate fails

## Manual Verification (Step-by-Step)

If you need to run gates individually:

### 1. Create Virtual Environment
```bash
python -m venv .venv_verify
# Windows
.venv_verify\Scripts\activate
# Linux/Mac
source .venv_verify/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Unit Tests
```bash
pytest -q tests/unit/
```

### 4. Run Integration Tests
```bash
pytest -q tests/integration/
```

### 5. Run E2E Mock Tests
```bash
pytest -q tests/e2e_mock/
```

### 6. Run Capability Mock Tests
```bash
python tools/run_capabilities.py --mode mock --outdir reports/_verify/mock --timeout_seconds 180
```

### 7. (Optional) Run Live Tests
```bash
# Set required environment variables first
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"

# Run live pytest
pytest -q -m live tests/live/

# Run live capabilities
python tools/run_capabilities.py --mode live --outdir reports/_verify/live --timeout_seconds 180
```

## Running Live Mode Safely

### Prerequisites
Live mode requires:
- Valid API keys for Anthropic and Google
- Rate limiting awareness (API quotas apply)
- No secrets in logs (keys are never logged, only presence is recorded)

### Environment Variables
```bash
# Required for live tests
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Optional
TEST_MODE=live
PYTHONHASHSEED=0  # For deterministic behavior
```

### Safety Checks
- API keys are validated but NEVER logged or committed
- All test outputs are saved to `reports/_local_verify/` (excluded from git)
- Rate limiting: Live tests may take longer due to API rate limits
- Cost awareness: Live tests consume API quota

## Common Failure Classes & Debugging

### 1. Import Errors
**Symptom:** `ModuleNotFoundError` or `ImportError`
**Cause:** Missing dependencies or incorrect Python path
**Fix:**
```bash
pip install -r requirements.txt --upgrade
# Ensure you're in the correct virtual environment
```

### 2. Configuration Errors
**Symptom:** `ConfigValidationError` or missing config files
**Cause:** Invalid `config/config.yaml` or missing templates
**Fix:**
```bash
# Validate configuration
python -c "from src.core.config_validator import ConfigValidator; ConfigValidator.validate()"
```

### 3. Fixture Errors
**Symptom:** `pytest` fixtures fail to load
**Cause:** Mock fixtures not properly initialized
**Fix:**
- Check `tests/conftest.py` is present
- Verify `tests/fixtures/` directory exists
- Review `tests/fixtures/mock_chromadb.py` and `http_fixtures.py`

### 4. Capability Test Failures
**Symptom:** Some capabilities fail in mock mode
**Cause:** Missing mock data or incorrect test mapping
**Fix:**
```bash
# Check capability overrides
cat tools/capability_overrides.json
# Review capability test mapper
python tools/capability_test_mapper.py
```

### 5. MCP Integration Failures
**Symptom:** MCP protocol tests fail
**Cause:** Route mismatch or protocol version issues
**Fix:**
- Review `src/mcp/protocol.py`
- Check `src/mcp/web_adapter.py`
- Verify route parity with `tests/integration/test_web_api_parity.py`

## Reproducing Wave 1-5 Verification

This section documents how to reproduce the verification process from development waves 1-5.

### Wave 1: Core API & MCP Setup
```bash
pytest tests/integration/test_mcp_integration.py
pytest tests/integration/test_config_integration.py
```

### Wave 2: Route Parity & Batch Support
```bash
pytest tests/integration/test_web_api_parity.py
pytest tests/integration/test_mcp_http_api.py
pytest tests/integration/test_agents_routes.py
pytest tests/integration/test_batch.py  # If exists
```

### Wave 3: Live Integration Fixes
```bash
# Mock mode first
pytest tests/integration/test_database_service.py
pytest tests/integration/test_template_registry.py

# Live mode (with env)
pytest -m live tests/live/
```

### Wave 4: E2E Mock Coverage
```bash
pytest tests/e2e_mock/
python tools/run_capabilities.py --mode mock --outdir reports/_wave4/mock
```

### Wave 5: Capability Coverage (94/94)
```bash
# All capabilities in mock mode
python tools/run_capabilities.py --mode mock --outdir reports/_wave5/mock --timeout_seconds 180

# Verify 100% pass rate
# Expected: 94/94 passed
```

## No Commit of Reports Policy

**CRITICAL:** Never commit report artifacts to git.

### What NOT to Commit
- `reports/**` - All test reports, logs, and artifacts
- `output/**` - Generated content files
- `.pack_staging/**` - Staging artifacts
- `*.tar.gz`, `*.zip` - Archive files
- `reports*.txt` - Stray report files

### Why This Policy Exists
- Bloats git history with non-source artifacts
- Causes merge conflicts on report updates
- Makes repository size grow unnecessarily
- Reports are reproducible via verification scripts

### How It's Enforced
- `.gitignore` excludes all report directories
- Pre-commit hooks (if configured) block report commits
- Verification scripts save to excluded directories
- Release evidence packs are external (not in git)

### Exceptions
None. If you need to preserve reports:
- Create release evidence packs (tarballs)
- Upload to external storage (S3, SharePoint, etc.)
- Reference in release notes by URL

## Exit Codes

Verification scripts use standard exit codes:
- `0` - All required gates passed (green)
- `1` - One or more required gates failed (red)

## Troubleshooting

### Verification Script Won't Run
```powershell
# Windows: Execution policy
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\verify_all.ps1
```

```bash
# Linux/Mac: Permissions
chmod +x scripts/verify_all.sh
./scripts/verify_all.sh
```

### Virtual Environment Issues
```bash
# Remove and recreate
rm -rf .venv_verify
python -m venv .venv_verify
```

### Timeout Errors
Increase timeout for capability tests:
```bash
python tools/run_capabilities.py --mode mock --timeout_seconds 300
```

## Support

For issues with this runbook or verification process:
1. Check GitHub Issues
2. Review recent commits in `git log`
3. Consult `docs/system-overview.md` for architecture context

---
**Last Updated:** 2026-01-24
**Version:** 1.0.0
**Maintained By:** Release Orchestrator Agent
