---
title: "Tutorial: Dual-Mode Testing with UCOP"
description: "Learn how to write and run tests in both mock and live modes"
source_url: "https://example.com/tutorials/dual-mode-testing"
sample_type: "live_fixture"
difficulty: "beginner"
duration: "15 minutes"
---

## Overview

UCOP supports two testing modes:
- **Mock Mode** (default): Fast, deterministic tests using mocks
- **Live Mode**: Real E2E tests with Ollama/Gemini and sample data

## Prerequisites

- Python 3.11+
- pytest installed: `pip install pytest pytest-cov`
- (Optional) Ollama running or `GEMINI_API_KEY` set for live mode

## Step 1: Write a Mock Mode Test

Create a fast unit test using mocks:

```python
# tests/unit/test_my_agent.py
import pytest
from unittest.mock import Mock, patch

def test_my_agent_mock():
    """Test agent with mocked LLM service."""
    with patch('src.services.services.LLMService') as mock_llm:
        mock_llm.return_value.generate.return_value = '{"title": "Test"}'

        # Test your agent
        result = my_agent.execute({})

        assert result['title'] == "Test"
```

Run it:
```bash
pytest tests/unit/test_my_agent.py -v
```

## Step 2: Write a Live Mode Test

Create an E2E test that uses real services:

```python
# tests/e2e/test_my_workflow.py
import pytest

pytestmark = pytest.mark.live  # Mark entire file as live

class TestMyWorkflow:
    def test_workflow_execution(
        self,
        skip_if_no_live_env,
        sample_kb_file,
        live_output_dir
    ):
        """Test workflow with real Ollama/Gemini."""
        from src.engine.unified_engine import get_engine

        # In live mode, returns ProductionExecutionEngine
        engine = get_engine()

        # Load sample data
        kb_content = sample_kb_file.read_text()
        assert len(kb_content) > 100

        # Execute workflow (real LLM calls)
        result = engine.execute_workflow(...)

        # Verify output
        assert result.status == "completed"

        # Write to reports/ directory
        output_file = live_output_dir / "test_output.md"
        output_file.write_text(result.artifact_content)
```

## Step 3: Run Tests in Mock Mode

Default mode, no environment variables needed:

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest --cov=src --cov-report=term tests/unit/

# Run specific test
pytest tests/unit/test_my_agent.py::test_my_agent_mock -v
```

Expected: Fast execution (seconds), all tests pass or skip.

## Step 4: Run Tests in Live Mode

Set `TEST_MODE=live` environment variable:

```bash
# Run live E2E tests
TEST_MODE=live pytest tests/e2e/ -v -s

# Run specific live test
TEST_MODE=live pytest tests/e2e/test_my_workflow.py -v -s

# With verbose output
TEST_MODE=live pytest tests/e2e/ -v -s --log-cli-level=INFO
```

Expected: Slower execution (minutes), real LLM calls, output in `reports/`.

## Step 5: Use Test Fixtures

UCOP provides convenient fixtures:

```python
def test_with_fixtures(
    test_mode,              # Current mode (MOCK or LIVE)
    skip_if_no_live_env,    # Skip if not in live mode
    samples_path,            # Path to samples/ directory
    sample_kb_file,         # Specific sample file
    live_output_dir         # Output directory
):
    from src.utils.testing_mode import is_live_mode

    if is_live_mode():
        # Real services available
        assert sample_kb_file.exists()
        assert "reports" in str(live_output_dir)
    else:
        # Mock mode
        assert live_output_dir != samples_path
```

## Step 6: Verify Engine Switching

Test that engine factory switches correctly:

```python
def test_engine_switching():
    """Verify engine switches based on TEST_MODE."""
    from src.engine.unified_engine import get_engine
    from src.utils.testing_mode import is_live_mode

    engine = get_engine()

    if is_live_mode():
        # Should be ProductionExecutionEngine
        assert hasattr(engine, 'agent_factory')
        assert hasattr(engine, 'test_mode')
        assert engine.test_mode is True
    else:
        # Should be UnifiedEngine (or ProductionEngine if already initialized)
        assert engine is not None
```

## Best Practices

1. **Write Mock Tests First** - Fast feedback loop during development
2. **Use Live Tests for Critical Paths** - Validate real integration
3. **Always Use `skip_if_no_live_env`** - Graceful degradation in CI
4. **Keep Live Tests Focused** - Test one workflow per test
5. **Use Sample Data** - Don't generate new data in tests

## Troubleshooting

**Live tests skip even with TEST_MODE=live:**
- Check `echo $TEST_MODE` outputs "live"
- Verify Ollama is running: `ollama list`
- Or check Gemini key: `echo $GEMINI_API_KEY`

**Import errors:**
- Run from project root
- Set `PYTHONPATH`: `export PYTHONPATH=$PWD:$PYTHONPATH`

**Tests too slow:**
- Run only unit tests: `pytest tests/unit/`
- Skip slow tests: `pytest -m "not slow"`

## Next Steps

- Read [Testing Guide](../../../docs/testing.md) for complete reference
- Explore sample data in `samples/fixtures/`
- Review existing tests in `tests/e2e/test_live_workflows.py`

For questions, see the troubleshooting section in `docs/testing.md`.
