# Taskcard Template - Content Generator

## Role
Senior engineer. Produce drop-in, production-ready code following all repository rules in `.claude/rules.md`.

---

## Scope (only this)

### Fix/Feature
- **Description**: `<one module, feature, or bug fix>`
- **Example**: "Add keyword extraction agent" or "Fix workflow loading in Web UI"

### Allowed Paths
```
<list of specific files and folders>
Examples:
- src/agents/seo/
- src/web/routes/workflows.py
- src/core/workflow_compiler.py
- templates/workflows.yaml
```

### Forbidden
- ❌ Any other files not listed above
- ❌ Changes to `.env` (only `.env.example` allowed)
- ❌ Root-level markdown files (use `reports/` or `docs/`)
- ❌ Breaking changes without migration path

---

## Acceptance Checks (must pass locally)

### 1. Python Tests
```bash
# Run all tests
python -m pytest -v

# Run specific test suite
python -m pytest tests/<test_category>/<test_file>.py -v

# Run with coverage
python -m pytest --cov=src tests/

# Integration tests
python -m pytest tests/integration/ -v

# E2E tests
python -m pytest tests/e2e/ -v
```

### 2. API Endpoints (if applicable)
```bash
# Start the server
python start_server_port_5555.py

# Check API health
curl http://localhost:5555/health

# Check OpenAPI docs
curl http://localhost:5555/docs

# Test specific endpoint
curl -X POST http://localhost:5555/api/<endpoint> \
  -H "Content-Type: application/json" \
  -d '{<test-payload>}'
```

### 3. CLI Testing (if applicable)
```bash
# Test CLI commands
python ucop_cli.py --help
python ucop_cli.py workflow run <workflow-name>
python ucop_cli.py agent test <agent-name>
```

### 4. Web UI (if applicable)
```bash
# Build frontend
cd src/web/static
npm run build

# Test in browser
# Open http://localhost:5555 and verify changes
```

### 5. Code Quality (MANDATORY)
```bash
# Format check
python -m black --check .

# Apply formatting
python -m black .

# Run pre-commit hooks
pre-commit run --all-files
```

---

## System Integration Checks

### Agent Integration
- [ ] Agent inherits from `AgentBase`
- [ ] Agent declares proper contracts (inputs/outputs)
- [ ] Agent registered via `@agent_scanner` decorator
- [ ] Agent category correctly set
- [ ] Agent works in workflow context

### Workflow Integration
- [ ] Workflow defined in `templates/workflows.yaml`
- [ ] Dependencies properly declared
- [ ] Workflow compiles without errors
- [ ] Workflow executes end-to-end

### API Integration
- [ ] Endpoints have Pydantic models
- [ ] OpenAPI documentation generated
- [ ] Response models defined
- [ ] Error handling implemented

### Configuration
- [ ] Config changes in appropriate files (`config/`)
- [ ] Validation rules updated if needed
- [ ] Environment variables documented in `.env.example`

---

## Deliverables

### 1. Code Changes
- ✅ **Full file replacements only** (no diffs, no stubs, no TODO comments)
- ✅ All affected `.py` files with **100% DOCGEN documentation**
- ✅ Type hints on all new functions/methods
- ✅ Error handling for all edge cases
- ✅ Logging with appropriate context (no sensitive data)

### 2. Tests (in `tests/`)
```
tests/
├── unit/<module>/test_<feature>.py          # Unit tests
├── integration/test_<feature>_integration.py # Integration tests
├── e2e/test_<feature>_e2e.py                 # E2E tests
└── fixtures/<feature>_fixtures.py            # Test data fixtures
```

**Test Coverage Requirements:**
- [ ] Happy path test case
- [ ] Error path test cases
- [ ] Edge cases (empty input, null values, boundary conditions)
- [ ] Integration test covering full workflow
- [ ] Regression test if fixing a bug

### 3. Configuration Changes (if applicable)
- [ ] Update `config/main.yaml`
- [ ] Update `config/validation.yaml`
- [ ] Update `.env.example` with new variables
- [ ] Update `templates/workflows.yaml` if workflows change

### 4. Documentation
- [ ] **Reports**: Analysis/findings in `reports/<TASKID>_<description>.md`
- [ ] **User Docs**: User-facing docs in `docs/<feature>.md`
- [ ] **Dev Docs**: Developer docs in `development/<feature>.md`
- [ ] **API Docs**: OpenAPI spec updated (if API changes)

---

## Hard Rules (Non-Negotiable)

### API & Interface Stability
- ❌ **DO NOT** change public function signatures without justification
- ✅ **IF** signature must change: update ALL call sites in the codebase
- ✅ Provide backward compatibility layer or migration guide
- ✅ Document breaking changes in commit message and docs

### Testing Hygiene
- ❌ **Zero** network calls in unit tests (use mocks)
- ❌ **Zero** external API dependencies in CI tests
- ✅ Use `@pytest.fixture` for test data
- ✅ Use `@patch` or `monkeypatch` for external dependencies
- ✅ Clean up test data in teardown

### Code Style & Consistency
- ✅ Follow PEP 8 (enforced by `black`)
- ✅ Use Google-style docstrings
- ✅ Match existing patterns in the module
- ✅ No commented-out code in final submission
- ✅ No debug print statements in production code

### Documentation Sync
- ✅ Keep docs in sync with code changes (same commit)
- ✅ Update examples if behavior changes
- ✅ Update API docs if endpoints change

### Test Sync
- ✅ Update tests in same commit as code changes
- ✅ Add new tests for new features
- ✅ Update existing tests if behavior changes
- ✅ All tests must pass before submission

---

## Self-Review Checklist

Answer YES/NO to each before claiming task complete:

### Implementation Completeness
- [ ] **YES/NO**: Thorough, end-to-end implementation (no TODOs, no partial work)?
- [ ] **YES/NO**: All requirements from scope section addressed?
- [ ] **YES/NO**: All edge cases handled with tests?
- [ ] **YES/NO**: All error paths tested and logged properly?

### System Integration
- [ ] **YES/NO**: Feature integrated into appropriate workflows?
- [ ] **YES/NO**: Agent contracts properly defined?
- [ ] **YES/NO**: Configuration changes documented and applied?
- [ ] **YES/NO**: API documentation updated and verified?

### Code Quality
- [ ] **YES/NO**: 100% DOCGEN documentation coverage for all `.py` files?
- [ ] **YES/NO**: Code formatted with `black` and type-hinted?
- [ ] **YES/NO**: No security vulnerabilities (SQL injection, XSS, etc.)?
- [ ] **YES/NO**: No sensitive data in logs or code?

### Testing & Verification
- [ ] **YES/NO**: All tests passing (`pytest -v`)?
- [ ] **YES/NO**: Integration tests covering realistic workflows?
- [ ] **YES/NO**: Regression check performed (no existing features broken)?
- [ ] **YES/NO**: Tested with actual workflow execution?

### Documentation & Deliverables
- [ ] **YES/NO**: Report written to `reports/` folder?
- [ ] **YES/NO**: User docs written to `docs/` folder?
- [ ] **YES/NO**: Dev docs written to `development/` folder?
- [ ] **YES/NO**: API documentation updated (if applicable)?

---

## Execution Workflow

### 1. Design Phase
**Output**: Minimal design document

```markdown
## Design: <Feature/Fix Name>

### Problem Statement
<What is broken or missing>

### Proposed Solution
<High-level approach>

### Components Affected
- Module: <module_name>
  - Changes: <brief description>
  - Risk: <Low/Medium/High>

### Data Flow
<Before>: <current flow>
<After>: <new flow>

### Edge Cases
1. <edge case 1>: <handling approach>
2. <edge case 2>: <handling approach>

### Rollback Plan
<How to revert if issues arise>
```

### 2. Implementation Phase
**Output**: Full updated files

- Provide complete file contents (not diffs)
- Include all imports, docstrings, type hints
- Show file path clearly
- Follow all hard rules

### 3. Testing Phase
**Output**: Test files and results

```python
# tests/<category>/test_<feature>.py

"""Tests for <feature>.

This module tests:
- Happy path: <description>
- Error path: <description>
- Edge cases: <list>
"""

import pytest
from unittest.mock import patch, MagicMock

# Test fixtures
@pytest.fixture
def sample_data():
    """Fixture for test data."""
    return {...}

# Happy path test
def test_<feature>_success(sample_data):
    """Test successful execution of <feature>."""
    result = <function>(sample_data)
    assert result.status == "success"
    assert result.data is not None

# Error path test
def test_<feature>_handles_error():
    """Test that <feature> handles errors gracefully."""
    with pytest.raises(ValueError):
        <function>(invalid_input)

# Integration test
@pytest.mark.integration
def test_<feature>_integration():
    """Test <feature> end-to-end."""
    # Setup
    # Execute
    # Verify
    # Cleanup
```

**Run tests and show results:**
```bash
python -m pytest tests/<test_file>.py -v
```

### 4. Verification Phase
**Output**: Verification results

```bash
# Run all checks
python -m pytest -v
python -m black --check .
python ucop_cli.py workflow validate <workflow>
curl http://localhost:5555/docs
```

---

## Final Submission Format

```markdown
# Task Completion Report: <TASK-ID>

## Summary
<2-3 sentence summary of what was done>

## Files Changed
- `<file1>`: <description>
- `<file2>`: <description>

## Tests Added/Modified
- `<test_file1>`: <description>
- `<test_file2>`: <description>

## Test Results
```
<paste test output>
```

## Self-Review Results
<YES/NO answers from checklist>

## Verification
- [ ] All tests pass
- [ ] Code formatted with black
- [ ] Documentation updated
- [ ] API docs generated
- [ ] No regressions

## Documentation
- Report: `reports/<report_file>.md`
- User Docs: `docs/<doc_file>.md`
- Dev Docs: `development/<doc_file>.md`

---
Generated: <date>
Status: COMPLETE ✅
```

---

**Template Version**: 1.0
**Last Updated**: 2025-12-04
**Project**: Content Generator
**Enforcement**: Strict - No exceptions to hard rules
