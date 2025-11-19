"""
Shared fixtures for HTTP endpoint testing.

Provides common fixtures for testing FastAPI routes including:
- Mock executors
- Sample data
- Test clients
- Mock stores
"""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def mock_executor():
    """Create a comprehensive mock executor for testing."""
    executor = Mock()

    # Mock job engine
    executor.job_engine = Mock()
    executor.job_engine._jobs = {}

    # Create proper job result mock with datetime objects
    job_result = Mock()
    job_result.job_id = "test_job_123"
    job_result.status = "running"
    job_result.started_at = datetime.now(timezone.utc)
    job_result.completed_at = None
    job_result.output_path = Path("./output")
    job_result.error = None

    # Mock methods with proper return values
    executor.run_job = Mock(return_value=job_result)
    executor.submit_job = Mock()
    executor.pause_job = Mock()
    executor.resume_job = Mock()
    executor.cancel_job = Mock()
    executor.get_status = Mock(return_value={"status": "healthy"})
    executor.get_workflows = Mock(return_value=[
        {
            "id": "test_workflow",
            "name": "Test Workflow",
            "description": "A test workflow",
            "agents": ["agent1", "agent2"],
            "metadata": {}
        }
    ])
    # get_workflow that returns None for nonexistent workflows
    def mock_get_workflow(workflow_id):
        if workflow_id == "test_workflow":
            return {
                "id": "test_workflow",
                "name": "Test Workflow",
                "description": "A test workflow",
                "agents": ["agent1", "agent2"],
                "metadata": {}
            }
        return None

    executor.get_workflow = Mock(side_effect=mock_get_workflow)

    # Mock get_agents for agent API tests
    executor.get_agents = Mock(return_value=[
        {
            "id": "TestAgent",
            "name": "Test Agent",
            "category": "content",
            "description": "A test agent",
            "capabilities": ["generate", "validate"],
            "metadata": {}
        }
    ])

    # Mock get_agent that returns None for nonexistent agents
    def mock_get_agent(agent_id):
        if agent_id == "TestAgent":
            return {
                "id": "TestAgent",
                "name": "Test Agent",
                "category": "content",
                "description": "A test agent",
                "capabilities": ["generate", "validate"],
                "metadata": {}
            }
        return None

    executor.get_agent = Mock(side_effect=mock_get_agent)

    return executor


@pytest.fixture
def mock_jobs_store():
    """Create a mock jobs store with sample data."""
    return {}


@pytest.fixture
def mock_agent_logs():
    """Create a mock agent logs store."""
    return {}


@pytest.fixture
def sample_job_data():
    """Create sample job data for testing."""
    return {
        "job_id": "test_job_123",
        "workflow_id": "test_workflow",
        "inputs": {"topic": "Test Topic"},
        "status": "running",
        "progress": 50,
        "current_stage": "outline",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "completed_at": None,
        "error": None,
        "result": None,
        "metadata": {"test": True}
    }


@pytest.fixture
def sample_job_result():
    """Create sample job result for mock executor."""
    from unittest.mock import Mock

    result = Mock()
    result.job_id = "test_job_123"
    result.status = "running"
    result.started_at = datetime.now(timezone.utc)
    result.completed_at = None
    result.output_path = Path("./output")
    result.error = None

    return result


@pytest.fixture
def sample_agent_data():
    """Create sample agent configuration data."""
    return {
        "agent_id": "TestAgent",
        "name": "Test Agent",
        "type": "test",
        "description": "Test agent for testing",
        "status": "available",
        "capabilities": ["testing", "mocking"],
        "metadata": {"version": "1.0"}
    }


@pytest.fixture
def sample_workflow_data():
    """Create sample workflow configuration data."""
    return {
        "workflow_id": "test_workflow",
        "name": "Test Workflow",
        "description": "Test workflow for testing",
        "agents": ["agent1", "agent2"],
        "metadata": {"version": "1.0"}
    }


@pytest.fixture
def test_app(mock_executor, mock_jobs_store, mock_agent_logs):
    """Create a test FastAPI app with all dependencies mocked."""
    from src.web.app import create_app
    
    app = create_app(executor=mock_executor, config_snapshot=None)
    
    # Inject mock stores
    from src.web.routes import jobs, agents
    jobs.set_jobs_store(mock_jobs_store)
    agents.set_jobs_store(mock_jobs_store)
    agents.set_agent_logs(mock_agent_logs)
    
    return app


@pytest.fixture
def client(test_app):
    """Create a test client for HTTP requests."""
    return TestClient(test_app)


@pytest.fixture
def auth_headers():
    """Create authentication headers for testing (if needed)."""
    return {
        "Authorization": "Bearer test_token",
        "Content-Type": "application/json"
    }


@pytest.fixture
def populated_jobs_store(mock_jobs_store, sample_job_data):
    """Create a jobs store pre-populated with test data."""
    # Add multiple jobs
    for i in range(5):
        job_id = f"test_job_{i}"
        job_data = sample_job_data.copy()
        job_data["job_id"] = job_id
        job_data["status"] = "completed" if i < 3 else "running"
        mock_jobs_store[job_id] = job_data
    
    return mock_jobs_store


@pytest.fixture
def mock_config_snapshot():
    """Create a mock configuration snapshot."""
    config = Mock()
    config.config_hash = "test_hash_123"
    config.timestamp = "2025-01-15T12:00:00Z"
    config.engine_version = "1.0.0"
    config.agent_config = {"agents": {}}
    config.main_config = {"workflows": {}}
    config.tone_config = {}
    config.perf_config = {}
    
    return config
