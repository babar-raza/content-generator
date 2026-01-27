"""Pytest configuration and shared fixtures for testing.

Sets up proper mocking for ChromaDB and sentence-transformers to enable
testing without installing these dependencies.

Supports dual-mode testing:
- Mock mode (default): Fast, deterministic, uses mocks
- Live mode (TEST_MODE=live): Real services, uses samples/ data
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import mocks before the actual modules
from tests.fixtures.mock_chromadb import create_mock_client, create_mock_embedding_model

# Import testing mode helper
from src.utils.testing_mode import is_live_mode, is_mock_mode, get_sample_data_path


def pytest_configure(config):
    """Configure pytest with module-level mocks."""
    # Skip mocking if in live mode
    if os.getenv('TEST_MODE', 'mock').lower() == 'live':
        return

    # Import the mock classes
    from tests.fixtures.mock_chromadb import MockChromaClient, MockSentenceTransformer

    # Mock chromadb module
    mock_chromadb = MagicMock()
    mock_chromadb.PersistentClient = MockChromaClient

    # Mock Settings
    mock_settings = MagicMock()
    mock_chromadb.config.Settings = mock_settings

    sys.modules['chromadb'] = mock_chromadb
    sys.modules['chromadb.config'] = mock_chromadb.config

    # Mock sentence_transformers
    mock_st = MagicMock()
    mock_st.SentenceTransformer = MockSentenceTransformer
    sys.modules['sentence_transformers'] = mock_st


@pytest.fixture(autouse=True)
def mock_chromadb_availability():
    """Ensure CHROMADB_AVAILABLE and SENTENCE_TRANSFORMERS_AVAILABLE are True."""
    with patch('src.services.services.CHROMADB_AVAILABLE', True):
        with patch('src.services.vectorstore.CHROMADB_AVAILABLE', True):
            with patch('src.services.vectorstore.SENTENCE_TRANSFORMERS_AVAILABLE', True):
                yield


@pytest.fixture(autouse=True)
def enforce_no_network_in_tests(monkeypatch):
    """Prevent accidental network calls in mock mode tests.

    Sets TEST_MODE=mock and ALLOW_NETWORK=0 unless explicitly overridden.
    Patches TrendReq to raise error if called in mock mode (leak detection).
    """
    # Only enforce in mock mode (not live tests)
    test_mode = os.getenv('TEST_MODE', 'mock').lower()

    if test_mode != 'live':
        # Set mock mode environment
        monkeypatch.setenv('TEST_MODE', 'mock')
        monkeypatch.delenv('ALLOW_NETWORK', raising=False)

        # Patch TrendReq to detect leaks
        from unittest.mock import MagicMock

        def _leak_detector(*args, **kwargs):
            raise RuntimeError(
                "TrendReq called in mock mode! This is a network leak. "
                "Either use TEST_MODE=live or fix the code to check TEST_MODE."
            )

        # Patch at import location (only if PYTRENDS_AVAILABLE)
        try:
            monkeypatch.setattr(
                'src.services.services.TrendReq',
                _leak_detector,
                raising=False
            )
        except AttributeError:
            # TrendReq might be None if pytrends not installed
            pass


@pytest.fixture(autouse=True)
def _isolation_reset(monkeypatch):
    """Reset all global state for test isolation.

    This fixture ensures every test starts with clean global state by:
    1. Resetting all singleton instances (ConfigValidator, monitors, etc)
    2. Clearing all module-level caches
    3. Removing leaked module mocks (like psutil)
    4. Running garbage collection

    Note: Does NOT set TEST_MODE - tests should set this explicitly if needed.
    E2E mock tests should set TEST_MODE=mock in their conftest or fixtures.
    """
    # Import and call reset_all before the test
    from src.testing.reset_state import reset_all
    reset_all()

    yield

    # Reset again after the test to ensure clean slate for next test
    reset_all()


# ============================================================================
# Integration Test Fixtures
# ============================================================================

@pytest.fixture
def test_config():
    """Provide test configuration."""
    from src.core.config import Config

    config = Config()
    config.test_mode = True
    return config


@pytest.fixture
def mock_executor():
    """Provide mock execution engine."""
    executor = MagicMock()
    executor.submit_job = MagicMock(return_value="job_123")
    executor.get_job = MagicMock(return_value={
        "id": "job_123",
        "status": "completed",
        "workflow": "test_workflow"
    })
    executor.list_jobs = MagicMock(return_value=[])
    executor.cancel_job = MagicMock(return_value=True)
    executor.pause_job = MagicMock(return_value=True)
    executor.resume_job = MagicMock(return_value=True)
    executor.event_bus = MagicMock()
    return executor


@pytest.fixture
def mock_registry():
    """Provide mock agent registry."""
    registry = MagicMock()
    registry.discover_agents = MagicMock(return_value=["TestAgent1", "TestAgent2"])
    registry.get_agent = MagicMock(return_value=MagicMock())
    registry.get_all_categories = MagicMock(return_value=["content", "seo", "code"])
    registry.get_agents_by_category = MagicMock(return_value=["TestAgent1"])
    return registry


@pytest.fixture(autouse=True)
def reset_route_globals():
    """Reset global state in route modules between tests for proper isolation."""
    yield
    # Cleanup after each test to prevent state leakage
    try:
        from src.web.routes import jobs, agents
        jobs._jobs_store = None
        jobs._executor = None
        agents._jobs_store = None
        agents._executor = None
        agents._agent_logs = {}
    except ImportError:
        # Modules might not be imported yet
        pass


@pytest.fixture
def mock_llm_service():
    """Provide mock LLM service."""
    from unittest.mock import AsyncMock

    service = MagicMock()
    service.generate = MagicMock(return_value='{"result": "test"}')
    service.generate_async = AsyncMock(return_value='{"result": "test"}')
    service.check_health = MagicMock(return_value={"ollama": "healthy"})
    return service


@pytest.fixture
def test_job_data():
    """Provide test job data."""
    return {
        "id": "job_123",
        "workflow": "test_workflow",
        "status": "pending",
        "input_file": "test_input.md",
        "output_dir": "test_output/",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }


@pytest.fixture
def test_checkpoint_data():
    """Provide test checkpoint data."""
    return {
        "checkpoint_id": "checkpoint_123",
        "job_id": "job_123",
        "step": "test_step",
        "state": {"data": "test"},
        "created_at": "2024-01-01T00:00:00"
    }


@pytest.fixture
def test_workflow():
    """Provide test workflow definition."""
    return {
        "id": "test_workflow",
        "name": "Test Workflow",
        "description": "Test workflow for testing",
        "steps": [
            {"id": "step1", "agent": "TestAgent1"},
            {"id": "step2", "agent": "TestAgent2"}
        ]
    }


@pytest.fixture
def mock_checkpoint_manager():
    """Provide mock checkpoint manager."""
    manager = MagicMock()
    manager.save_checkpoint = MagicMock(return_value="checkpoint_123")
    manager.restore_checkpoint = MagicMock(return_value={"data": "test"})
    manager.list_checkpoints = MagicMock(return_value=[])
    manager.delete_checkpoint = MagicMock(return_value=True)
    return manager


@pytest.fixture
def mock_workflow_compiler():
    """Provide mock workflow compiler."""
    compiler = MagicMock()
    compiler.compile = MagicMock(return_value=MagicMock())
    compiler.list_workflows = MagicMock(return_value=["workflow1", "workflow2"])
    compiler.get_workflow = MagicMock(return_value={"id": "workflow1", "name": "Workflow 1"})
    return compiler


@pytest.fixture
def temp_output_dir(tmp_path):
    """Provide temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture
def test_input_file(tmp_path):
    """Create test input file."""
    input_file = tmp_path / "test_input.md"
    input_file.write_text("""# Test Input

This is test input content for testing purposes.

## Section 1
Content for section 1.

## Section 2
Content for section 2.
""")
    return input_file


@pytest.fixture
def mock_websocket():
    """Provide mock WebSocket connection."""
    from unittest.mock import AsyncMock

    ws = AsyncMock()
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock(return_value='{"type": "ping"}')
    ws.receive_json = AsyncMock(return_value={"type": "ping"})
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def test_mcp_request():
    """Provide test MCP request."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }


@pytest.fixture
def test_template_data():
    """Provide test template data."""
    return {
        "id": "test_template",
        "name": "Test Template",
        "type": "blog",
        "schema": {
            "title": {"type": "string", "required": True},
            "content": {"type": "string", "required": True}
        },
        "example": {
            "title": "Test Title",
            "content": "Test Content"
        }
    }


@pytest.fixture
def test_agent_metadata():
    """Provide test agent metadata."""
    return {
        "name": "TestAgent",
        "category": "content",
        "capabilities": ["generate", "validate"],
        "inputs": {"topic": "string"},
        "outputs": {"content": "string"},
        "dependencies": []
    }


@pytest.fixture
def mock_config_snapshot():
    """Provide mock config snapshot."""
    return {
        "agents": {"TestAgent": {"enabled": True}},
        "workflows": {"test_workflow": {"steps": []}},
        "llm": {"provider": "ollama", "model": "llama2"},
        "database": {"type": "chromadb", "path": ":memory:"}
    }


@pytest.fixture
def mock_jobs_store():
    """Provide mock jobs store dictionary."""
    return {}


@pytest.fixture
def mock_agent_logs():
    """Provide mock agent logs dictionary."""
    return {}


@pytest.fixture
async def async_client():
    """Provide async HTTP client for FastAPI testing."""
    from httpx import AsyncClient
    from src.web.app import create_app

    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ============================================================================
# Dual-Mode Testing Fixtures
# ============================================================================

@pytest.fixture
def test_mode():
    """Provide current test mode (mock or live)."""
    from src.utils.testing_mode import get_test_mode
    return get_test_mode()


@pytest.fixture
def skip_if_no_live_env():
    """Skip test if live mode prerequisites are missing."""
    if not is_live_mode():
        pytest.skip("Not in live mode (TEST_MODE != live)")

    # Check for required environment variables in live mode
    required_env = []

    # Check for Ollama (optional but recommended)
    ollama_available = os.environ.get('OLLAMA_HOST') or os.path.exists('/usr/bin/ollama')

    # Check for Gemini key (optional)
    gemini_key = os.environ.get('GEMINI_API_KEY')

    if not ollama_available and not gemini_key:
        pytest.skip("Live mode requires either Ollama or GEMINI_API_KEY")


@pytest.fixture
def samples_path():
    """Provide path to samples/ directory for live mode tests."""
    return Path(get_sample_data_path())


@pytest.fixture
def sample_kb_file(samples_path):
    """Provide sample KB file for live mode tests."""
    kb_file = samples_path / "fixtures" / "kb" / "sample-kb-overview.md"
    if not kb_file.exists():
        pytest.skip(f"Sample KB file not found: {kb_file}")
    return kb_file


@pytest.fixture
def sample_workflow_config(samples_path):
    """Provide sample workflow config for live mode tests."""
    workflow_file = samples_path / "config" / "workflows" / "sample_workflow.yaml"
    if not workflow_file.exists():
        pytest.skip(f"Sample workflow not found: {workflow_file}")
    return workflow_file


@pytest.fixture
def live_output_dir(tmp_path):
    """Provide output directory for live mode test results."""
    if is_live_mode():
        # Use reports/ for live mode outputs
        output_dir = Path("reports") / "live_test_outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    else:
        # Use tmp_path for mock mode
        return tmp_path / "output"
