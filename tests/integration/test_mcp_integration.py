"""
MCP Integration Tests

Tests for all MCP protocol endpoints
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch):
    """Mock circular import dependencies."""
    # Mock visualization to avoid circular imports
    mock_viz = type('module', (), {
        'DebugBreakpoint': type('DebugBreakpoint', (), {}),
        'DebugSession': type('DebugSession', (), {})
    })
    monkeypatch.setitem(sys.modules, 'src.visualization.workflow_debugger', mock_viz)


def test_import_protocol():
    """Test protocol imports work."""
    from src.mcp.protocol import MCPRequest, MCPResponse, MCPProtocol
    assert MCPRequest is not None
    assert MCPResponse is not None
    assert MCPProtocol is not None


def test_import_handlers():
    """Test handler imports work."""
    from src.mcp.handlers import (
        handle_workflow_execute,
        handle_workflow_status,
        handle_agent_list
    )
    assert handle_workflow_execute is not None
    assert handle_workflow_status is not None
    assert handle_agent_list is not None


@pytest.mark.asyncio
async def test_mcp_request_structure():
    """Test MCP request structure."""
    from src.mcp.protocol import MCPRequest
    
    request = MCPRequest(
        method="workflow.execute",
        params={"workflow_id": "test"},
        id="req_1"
    )
    
    assert request.method == "workflow.execute"
    assert request.params == {"workflow_id": "test"}
    assert request.id == "req_1"


@pytest.mark.asyncio
async def test_mcp_response_structure():
    """Test MCP response structure."""
    from src.mcp.protocol import MCPResponse
    
    response = MCPResponse(
        result={"job_id": "test_job"},
        id="req_1"
    )
    
    assert response.result == {"job_id": "test_job"}
    assert response.error is None
    assert response.id == "req_1"


@pytest.mark.asyncio
async def test_mcp_error_response():
    """Test MCP error response structure."""
    from src.mcp.protocol import MCPResponse
    
    response = MCPResponse(
        error={"code": -32601, "message": "Method not found"},
        id="req_1"
    )
    
    assert response.result is None
    assert response.error is not None
    assert response.error["code"] == -32601


@pytest.mark.asyncio
async def test_workflow_execute_params_validation():
    """Test workflow execute parameter validation."""
    from src.mcp.handlers import handle_workflow_execute
    from unittest.mock import Mock
    from src.mcp.handlers import set_dependencies
    
    # Mock dependencies
    executor = Mock()
    executor.run_job = Mock()
    job_result = Mock()
    job_result.job_id = "test_job"
    job_result.status = "running"
    job_result.started_at = "2025-01-11T12:00:00"
    job_result.completed_at = None
    job_result.output_path = Path("./output")
    job_result.error = None
    executor.run_job.return_value = job_result
    
    job_engine = Mock()
    set_dependencies(executor=executor, job_engine=job_engine)
    
    # Test missing workflow_id
    with pytest.raises(ValueError, match="workflow_id is required"):
        await handle_workflow_execute({})


@pytest.mark.asyncio
async def test_workflow_status_params_validation():
    """Test workflow status parameter validation."""
    from src.mcp.handlers import handle_workflow_status
    from unittest.mock import Mock
    from src.mcp.handlers import set_dependencies
    
    # Mock dependencies
    executor = Mock()
    job_engine = Mock()
    job_engine._jobs = {}
    set_dependencies(executor=executor, job_engine=job_engine)
    
    # Test missing job_id
    with pytest.raises(ValueError, match="job_id is required"):
        await handle_workflow_status({})


@pytest.mark.asyncio
async def test_agent_invoke_params_validation():
    """Test agent invoke parameter validation."""
    from src.mcp.handlers import handle_agent_invoke
    from unittest.mock import Mock
    from src.mcp.handlers import set_dependencies
    
    # Mock dependencies
    executor = Mock()
    job_engine = Mock()
    set_dependencies(executor=executor, job_engine=job_engine)
    
    # Test missing agent_id
    with pytest.raises(ValueError, match="agent_id is required"):
        await handle_agent_invoke({})


@pytest.mark.asyncio
async def test_realtime_subscribe_params_validation():
    """Test realtime subscribe parameter validation."""
    from src.mcp.handlers import handle_realtime_subscribe
    from unittest.mock import Mock
    from src.mcp.handlers import set_dependencies
    
    # Mock dependencies
    executor = Mock()
    job_engine = Mock()
    set_dependencies(executor=executor, job_engine=job_engine)
    
    # Test missing job_id
    with pytest.raises(ValueError, match="job_id is required"):
        await handle_realtime_subscribe({})


@pytest.mark.asyncio
async def test_checkpoint_list_params_validation():
    """Test checkpoint list parameter validation."""
    from src.mcp.handlers import handle_workflow_checkpoint_list
    from unittest.mock import Mock
    from src.mcp.handlers import set_dependencies
    
    # Mock dependencies
    executor = Mock()
    job_engine = Mock()
    set_dependencies(executor=executor, job_engine=job_engine)
    
    # Test missing job_id
    with pytest.raises(ValueError, match="job_id is required"):
        await handle_workflow_checkpoint_list({})


@pytest.mark.asyncio
async def test_workflow_execute_success():
    """Test successful workflow execution."""
    from src.mcp.handlers import handle_workflow_execute, set_dependencies
    from unittest.mock import Mock
    
    # Setup mocks
    executor = Mock()
    job_result = Mock()
    job_result.job_id = "test_job_123"
    job_result.status = "running"
    job_result.started_at = "2025-01-11T12:00:00"
    job_result.completed_at = None
    job_result.output_path = Path("./output")
    job_result.error = None
    executor.run_job.return_value = job_result
    
    job_engine = Mock()
    set_dependencies(executor=executor, job_engine=job_engine)
    
    # Execute
    result = await handle_workflow_execute({
        "workflow_id": "fast-draft",
        "inputs": {"topic": "AI trends"}
    })
    
    # Verify
    assert "job_id" in result
    assert result["workflow_id"] == "fast-draft"
    assert result["status"] in ["running", "completed", "pending"]


@pytest.mark.asyncio
async def test_workflow_status_success():
    """Test successful workflow status retrieval."""
    from src.mcp.handlers import handle_workflow_status, set_dependencies
    from unittest.mock import Mock
    
    # Setup mocks
    executor = Mock()
    
    job = Mock()
    job.to_dict = Mock(return_value={
        "id": "test_job",
        "status": "running",
        "workflow_name": "fast-draft",
        "progress": 50,
        "current_step": "outline",
        "pipeline": [],
        "started_at": "2025-01-11T12:00:00",
        "completed_at": None,
        "error": None
    })
    
    job_engine = Mock()
    job_engine._jobs = {"test_job": job}
    
    set_dependencies(executor=executor, job_engine=job_engine)
    
    # Execute
    result = await handle_workflow_status({"job_id": "test_job"})
    
    # Verify
    assert result["job_id"] == "test_job"
    assert result["status"] == "running"
    assert "uri" in result


@pytest.mark.asyncio
async def test_agent_list_success():
    """Test successful agent listing."""
    from src.mcp.handlers import handle_agent_list, set_dependencies
    from unittest.mock import Mock
    
    # Setup mocks
    executor = Mock()
    job_engine = Mock()
    
    agents = [
        {"id": "agent1", "name": "Agent 1", "category": "research"},
        {"id": "agent2", "name": "Agent 2", "category": "content"}
    ]
    
    agent_registry = Mock()
    agent_registry.list_agents = Mock(return_value=agents)
    
    set_dependencies(executor=executor, job_engine=job_engine, agent_registry=agent_registry)
    
    # Execute
    result = await handle_agent_list({})
    
    # Verify
    assert "agents" in result
    assert "total" in result
    assert len(result["agents"]) == 2


@pytest.mark.asyncio
async def test_realtime_subscribe_success():
    """Test successful realtime subscription."""
    from src.mcp.handlers import handle_realtime_subscribe, set_dependencies
    from unittest.mock import Mock
    
    # Setup mocks
    executor = Mock()
    job_engine = Mock()
    set_dependencies(executor=executor, job_engine=job_engine)
    
    # Execute
    result = await handle_realtime_subscribe({
        "job_id": "test_job",
        "event_types": ["status", "progress"]
    })
    
    # Verify
    assert result["job_id"] == "test_job"
    assert "subscription_id" in result
    assert result["event_types"] == ["status", "progress"]
    assert "websocket_url" in result


@pytest.mark.asyncio
async def test_mcp_protocol_route_request():
    """Test MCP protocol request routing."""
    from src.mcp.protocol import MCPProtocol, MCPRequest
    from unittest.mock import Mock
    
    # Setup mocks
    executor = Mock()
    job_result = Mock()
    job_result.job_id = "test_job"
    job_result.status = "running"
    job_result.started_at = "2025-01-11T12:00:00"
    job_result.completed_at = None
    job_result.output_path = Path("./output")
    job_result.error = None
    executor.run_job.return_value = job_result
    
    job_engine = Mock()
    agent_registry = Mock()
    
    # Create protocol
    protocol = MCPProtocol(
        executor=executor,
        job_engine=job_engine,
        agent_registry=agent_registry
    )
    
    # Test valid method
    request = MCPRequest(
        method="agent.list",
        params={},
        id="req_1"
    )
    
    response = await protocol.handle_request(request)
    
    assert response.id == "req_1"
    # Response should either have result or error
    assert response.result is not None or response.error is not None


@pytest.mark.asyncio
async def test_mcp_protocol_invalid_method():
    """Test MCP protocol with invalid method."""
    from src.mcp.protocol import MCPProtocol, MCPRequest
    from unittest.mock import Mock
    
    # Setup mocks
    executor = Mock()
    job_engine = Mock()
    agent_registry = Mock()
    
    # Create protocol
    protocol = MCPProtocol(
        executor=executor,
        job_engine=job_engine,
        agent_registry=agent_registry
    )
    
    # Test invalid method
    request = MCPRequest(
        method="invalid.method",
        params={},
        id="req_error"
    )
    
    response = await protocol.handle_request(request)
    
    assert response.id == "req_error"
    assert response.error is not None
    assert response.error["code"] == -32601
    assert "Method not found" in response.error["message"]


@pytest.mark.asyncio
async def test_checkpoint_list_no_checkpoints():
    """Test checkpoint list when no checkpoints exist."""
    from src.mcp.handlers import handle_workflow_checkpoint_list, set_dependencies
    from unittest.mock import Mock
    
    # Setup mocks
    executor = Mock()
    job_engine = Mock()
    set_dependencies(executor=executor, job_engine=job_engine)
    
    # Execute
    result = await handle_workflow_checkpoint_list({"job_id": "test_job"})
    
    # Verify
    assert "checkpoints" in result
    assert isinstance(result["checkpoints"], list)


@pytest.mark.asyncio
async def test_web_routes_integration():
    """Test MCP web routes module can be imported."""
    from src.web.routes.mcp import router, mcp_endpoint
    
    assert router is not None
    assert mcp_endpoint is not None


@pytest.mark.asyncio
async def test_web_adapter_mounted():
    """Test that web_adapter router is properly imported and available."""
    from src.mcp.web_adapter import router, set_executor, get_executor

    assert router is not None
    # Router has no prefix - app adds /mcp prefix via include_router()
    assert router.prefix == ""
    assert set_executor is not None
    assert get_executor is not None


@pytest.mark.asyncio
async def test_all_mcp_endpoints_registered():
    """Test that all MCP endpoints are registered in the web_adapter router."""
    from src.mcp.web_adapter import router

    # Get all routes from the router (paths without prefix - app adds /mcp)
    routes = [route.path for route in router.routes]

    # Expected REST endpoints (relative paths - app adds /mcp prefix)
    expected_endpoints = [
        "/request",  # Main MCP protocol endpoint
        "/methods",  # List MCP methods
        "/status",  # MCP status
        "/jobs",  # Job management
        "/jobs/create",
        "/jobs/{job_id}",
        "/jobs/{job_id}/pause",
        "/jobs/{job_id}/resume",
        "/jobs/{job_id}/cancel",
        "/workflows",  # Workflow endpoints
        "/workflows/profiles",
        "/workflows/visual/{profile_name}",
        "/workflows/{profile_name}/metrics",
        "/workflows/{profile_name}/reset",
        "/agents",  # Agent endpoints
        "/agents/status",
        "/flows/realtime",  # Flow endpoints
        "/flows/history/{correlation_id}",
        "/flows/bottlenecks",
        "/debug/sessions",  # Debug endpoints
        "/debug/sessions/{session_id}",
        "/debug/breakpoints",
        "/debug/sessions/{session_id}/breakpoints/{breakpoint_id}",
        "/debug/sessions/{session_id}/step",
        "/debug/sessions/{session_id}/continue",
        "/debug/workflows/{workflow_id}/trace",
        "/config/snapshot",  # Config endpoints
        "/config/agents",
        "/config/workflows",
        "/config/tone",
        "/config/performance",
    ]

    # Check that all expected endpoints are present
    for endpoint in expected_endpoints:
        assert endpoint in routes, f"Expected endpoint {endpoint} not found in router"

    # Verify we have at least 30 routes
    assert len(routes) >= 30, f"Expected at least 30 routes, found {len(routes)}"


@pytest.mark.asyncio  
async def test_mcp_adapter_executor_initialization():
    """Test MCP adapter can be initialized with executor."""
    from src.mcp.web_adapter import set_executor, get_executor
    from unittest.mock import Mock
    
    # Create mock executor and config
    mock_executor = Mock()
    mock_config = Mock()
    mock_config.config_hash = "test_hash_12345"
    
    # Set executor
    set_executor(mock_executor, mock_config)
    
    # Verify executor can be retrieved
    executor = get_executor()
    assert executor is mock_executor


@pytest.mark.asyncio
async def test_mcp_status_endpoint():
    """Test /mcp/status endpoint structure."""
    from src.mcp.web_adapter import mcp_status, set_executor
    from unittest.mock import Mock
    
    # Test without executor
    status = await mcp_status()
    assert "status" in status
    assert "executor_initialized" in status
    assert "config_initialized" in status
    
    # Test with executor
    mock_executor = Mock()
    mock_executor.job_engine = Mock()
    mock_config = Mock()
    mock_config.config_hash = "abc123"
    
    set_executor(mock_executor, mock_config)
    
    status = await mcp_status()
    assert status["executor_initialized"] is True
    assert status["config_initialized"] is True
    assert "config_hash" in status


@pytest.mark.asyncio
async def test_mcp_methods_endpoint():
    """Test /mcp/methods endpoint returns method list."""
    from src.mcp.web_adapter import list_mcp_methods
    
    methods = await list_mcp_methods()
    
    assert "methods" in methods
    assert isinstance(methods["methods"], list)
    assert len(methods["methods"]) > 0
    
    # Check structure of first method
    first_method = methods["methods"][0]
    assert "name" in first_method
    assert "description" in first_method
    assert "params" in first_method


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
