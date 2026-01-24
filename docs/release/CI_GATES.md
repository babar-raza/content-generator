# CI Gates - Content Generator

## Overview
This document defines the required and optional CI gates for the content-generator project. These gates ensure code quality, integration stability, and functional correctness before deployment.

## Required Gates (Must Pass)

### 1. Integration Tests
**Path:** `tests/integration/`
**Command:** `pytest tests/integration/`
**Purpose:** Verify component integration and API contracts
**Failure Policy:** STOP-THE-LINE - Fix before merging

**Key Test Files:**
- `test_mcp_integration.py` - MCP protocol compliance
- `test_web_api_parity.py` - HTTP/MCP route parity
- `test_config_integration.py` - Configuration validation
- `test_database_service.py` - Database operations
- `test_template_registry.py` - Template management

### 2. E2E Mock Tests
**Path:** `tests/e2e_mock/`
**Command:** `pytest tests/e2e_mock/`
**Purpose:** End-to-end workflows with mocked external services
**Failure Policy:** STOP-THE-LINE - Fix before merging

**What This Tests:**
- Complete user journeys from request to response
- Cross-component integration
- Error handling and edge cases
- No external API dependencies (fully mocked)

### 3. Capability Mock Tests
**Command:** `python tools/run_capabilities.py --mode mock --outdir reports/_ci/mock --timeout_seconds 180`
**Purpose:** Verify all 94 system capabilities work in isolation
**Success Criteria:** 94/94 passed (100% pass rate)
**Failure Policy:** STOP-THE-LINE - Fix before merging

**What This Tests:**
- All agent capabilities (research, write, ingestion, etc.)
- Workflow orchestration
- Template rendering
- Configuration validation
- Mock service responses

## Optional Gates (Best Effort)

### 4. Live Tests
**Path:** `tests/live/`
**Command:** `pytest -m live tests/live/`
**Purpose:** Integration with real external services
**Failure Policy:** WARN - Investigate but don't block merge

**Prerequisites:**
- `ANTHROPIC_API_KEY` environment variable
- `GOOGLE_API_KEY` environment variable
- Network connectivity
- API quota availability

**What This Tests:**
- Real Anthropic API calls
- Real Google Trends API calls
- Real LinkChecker validation
- Actual network latency and error handling

### 5. Capability Live Tests
**Command:** `python tools/run_capabilities.py --mode live --outdir reports/_ci/live --timeout_seconds 180`
**Purpose:** Verify capabilities against real services
**Failure Policy:** WARN - Investigate but don't block merge

**Considerations:**
- Consumes API quota
- Subject to rate limiting
- May have variable latency
- Dependent on external service availability

## CI Configuration

### GitHub Actions Example

```yaml
name: CI Gates

on:
  pull_request:
  push:
    branches: [main]

jobs:
  required-gates:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run integration tests
        run: pytest tests/integration/ -v

      - name: Run E2E mock tests
        run: pytest tests/e2e_mock/ -v

      - name: Run capability mock tests
        run: |
          python tools/run_capabilities.py \
            --mode mock \
            --outdir reports/_ci/mock \
            --timeout_seconds 180

      # Do NOT upload reports by default (excluded via .gitignore)
      # Only upload on failure for debugging
      - name: Upload test artifacts on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: test-reports-${{ matrix.python-version }}
          path: reports/_ci/
          retention-days: 7

  optional-gates:
    runs-on: ubuntu-latest
    continue-on-error: true  # Don't fail the build

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run live tests
        if: env.ANTHROPIC_API_KEY != '' && env.GOOGLE_API_KEY != ''
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
        run: |
          pytest -m live tests/live/ -v
          python tools/run_capabilities.py \
            --mode live \
            --outdir reports/_ci/live \
            --timeout_seconds 180

      - name: Skip live tests
        if: env.ANTHROPIC_API_KEY == '' || env.GOOGLE_API_KEY == ''
        run: echo "Skipping live tests - API keys not configured"
```

## Environment Variables

### Required for Live Tests
- `ANTHROPIC_API_KEY` - Anthropic API key (never logged or committed)
- `GOOGLE_API_KEY` - Google API key (never logged or committed)

### Optional Configuration
- `PYTHONHASHSEED=0` - Deterministic behavior for reproducibility
- `TEST_MODE=live` - Explicitly enable live mode
- `PYTEST_TIMEOUT=300` - Pytest timeout in seconds

## Gate Failure Response

### When a Required Gate Fails

1. **DO NOT MERGE** - The pull request is blocked
2. **Investigate Locally**
   ```bash
   # Reproduce the failure
   ./scripts/verify_all.sh

   # Review logs
   cat reports/_local_verify/<timestamp>/<gate>.txt
   ```
3. **Fix the Issue**
   - Write/update tests
   - Fix the code
   - Verify fix locally
4. **Re-run Gates**
   ```bash
   ./scripts/verify_all.sh
   ```
5. **Push Fix** - CI will re-run automatically

### When an Optional Gate Fails

1. **Investigate** - Determine if it's a real issue or environmental
2. **Document** - Add a comment to the PR explaining the failure
3. **Decision**
   - If critical: Upgrade to required gate (fix before merge)
   - If environmental: Merge with documented caveat
   - If flaky: Fix the test, not the code

## Security Considerations

### No Secrets in Logs
- API keys are validated but NEVER logged
- Only boolean presence is recorded (true/false)
- All logs are excluded from git via `.gitignore`

### No Secrets in CI Artifacts
- Test reports are NOT uploaded by default
- Only uploaded on failure for debugging
- Retention limited to 7 days
- Manual review required before sharing

### No Secrets in Git
- `.env` excluded via `.gitignore`
- `.env.example` provided for reference
- Pre-commit hooks prevent accidental commits

## Determinism & Reproducibility

### Why PYTHONHASHSEED=0?
- Ensures consistent hash ordering
- Makes test failures reproducible
- Helps with debugging intermittent issues

### Cache Considerations
- ChromaDB uses in-memory mock for tests
- No persistent state between test runs
- Each test run starts clean

## Maintenance

### Adding New Gates
1. Add test suite to appropriate directory
2. Update this document with new gate details
3. Update verification scripts (`scripts/verify_all.*`)
4. Update CI workflow (`.github/workflows/`)
5. Test locally before committing

### Removing Gates
1. Document why gate is being removed
2. Update this document
3. Update verification scripts
4. Update CI workflow
5. Notify team of change

### Changing Success Criteria
1. Document rationale for change
2. Update gate definition in this document
3. Update scripts/CI to match new criteria
4. Test thoroughly before deploying

---
**Last Updated:** 2026-01-24
**Version:** 1.0.0
**Maintained By:** Release Orchestrator Agent
