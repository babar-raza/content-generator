"""
Integration tests for MCP monitoring endpoints.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from src.mcp.traffic_logger import MCPTrafficLogger, set_traffic_logger
from src.mcp.handlers import route_request
from src.mcp.protocol import MCPRequest


@pytest.fixture
def mock_logger(tmp_path):
    """Create a mock traffic logger with temporary database."""
    db_path = str(tmp_path / "test_traffic.db")
    logger = MCPTrafficLogger(db_path=db_path, retention_days=7)
    set_traffic_logger(logger)
    return logger


@pytest.fixture
def mock_executor():
    """Create a mock executor."""
    executor = Mock()
    executor.job_engine = Mock()
    executor.job_engine._jobs = {}
    return executor


@pytest.mark.asyncio
async def test_route_request_logs_traffic(mock_logger, mock_executor):
    """Test that route_request logs traffic."""
    from src.mcp import handlers
    handlers.set_dependencies(mock_executor)
    
    # Create a request
    request = MCPRequest(
        method="agent.list",
        params={},
        id="test_req_001"
    )
    
    # Process request
    response = await route_request(request)
    
    # Verify traffic was logged
    messages = mock_logger.get_traffic(limit=10)
    assert len(messages) >= 1
    
    # Verify message details
    msg = messages[0]
    assert msg.message_type == "agent.list"
    assert msg.status in ["success", "error"]


@pytest.mark.asyncio
async def test_successful_request_logging(mock_logger, mock_executor):
    """Test that successful requests are logged correctly."""
    from src.mcp import handlers
    handlers.set_dependencies(mock_executor)
    
    # Mock successful agent list
    mock_executor.agents = []
    
    request = MCPRequest(
        method="agent.list",
        params={},
        id="test_req_002"
    )
    
    response = await route_request(request)
    
    # Check response
    assert response.error is None
    
    # Check logged traffic
    messages = mock_logger.get_traffic(limit=10)
    assert len(messages) >= 1
    
    msg = messages[0]
    assert msg.status == "success"
    assert msg.duration_ms is not None
    assert msg.duration_ms >= 0


@pytest.mark.asyncio
async def test_error_request_logging(mock_logger, mock_executor):
    """Test that error requests are logged correctly."""
    from src.mcp import handlers
    handlers.set_dependencies(mock_executor)
    
    # Create a request with invalid params (missing required field)
    request = MCPRequest(
        method="workflow.execute",
        params={},  # Missing workflow_id
        id="test_req_003"
    )
    
    response = await route_request(request)
    
    # Check response has error
    assert response.error is not None
    
    # Check logged traffic
    messages = mock_logger.get_traffic(limit=10)
    assert len(messages) >= 1
    
    msg = messages[0]
    assert msg.status == "error"
    assert msg.error is not None


@pytest.mark.asyncio
async def test_multiple_requests_logged(mock_logger, mock_executor):
    """Test that multiple requests are logged."""
    from src.mcp import handlers
    handlers.set_dependencies(mock_executor)
    
    mock_executor.agents = []
    
    # Send multiple requests
    for i in range(3):
        request = MCPRequest(
            method="agent.list",
            params={},
            id=f"test_req_{i}"
        )
        await route_request(request)
    
    # Verify all logged
    messages = mock_logger.get_traffic(limit=10)
    assert len(messages) >= 3


def test_traffic_endpoint_returns_messages(mock_logger):
    """Test that traffic endpoint returns messages."""
    # Add some test messages
    mock_logger.log_request(
        message_id="msg_001",
        message_type="workflow.execute",
        from_agent="client",
        to_agent="engine",
        request={"workflow_id": "test"}
    )
    mock_logger.log_response(
        message_id="msg_001",
        response={"job_id": "job_001"},
        status="success",
        duration_ms=100.0
    )
    
    # Retrieve traffic
    messages = mock_logger.get_traffic(limit=10)
    
    assert len(messages) == 1
    assert messages[0].id == "msg_001"


def test_metrics_endpoint_returns_stats(mock_logger):
    """Test that metrics endpoint returns statistics."""
    # Add test messages
    mock_logger.log_request("msg_1", "test", "client", "server", {})
    mock_logger.log_response("msg_1", {}, "success", 100.0)
    
    mock_logger.log_request("msg_2", "test", "client", "server", {})
    mock_logger.log_response("msg_2", {}, "error", 50.0, "Error")
    
    # Get metrics
    metrics = mock_logger.get_metrics()
    
    assert metrics['total_messages'] == 2
    assert metrics['error_count'] == 1
    assert metrics['avg_latency_ms'] > 0


def test_message_endpoint_returns_details(mock_logger):
    """Test that message endpoint returns detailed message."""
    # Add test message
    mock_logger.log_request(
        message_id="detailed_msg",
        message_type="workflow.execute",
        from_agent="client",
        to_agent="engine",
        request={"workflow_id": "test", "inputs": {"topic": "AI"}}
    )
    mock_logger.log_response(
        message_id="detailed_msg",
        response={"job_id": "job_123", "status": "running"},
        status="success",
        duration_ms=250.5
    )
    
    # Get specific message
    message = mock_logger.get_message("detailed_msg")
    
    assert message is not None
    assert message.id == "detailed_msg"
    assert message.request['workflow_id'] == "test"
    assert message.response['job_id'] == "job_123"
    assert message.duration_ms == 250.5


def test_export_endpoint_json(mock_logger):
    """Test exporting traffic as JSON."""
    # Add test messages
    mock_logger.log_request("exp_msg_1", "test", "client", "server", {})
    mock_logger.log_response("exp_msg_1", {}, "success", 100.0)
    
    # Export as JSON
    json_data = mock_logger.export_traffic(format='json')
    
    assert json_data
    assert 'exp_msg_1' in json_data


def test_export_endpoint_csv(mock_logger):
    """Test exporting traffic as CSV."""
    # Add test messages
    mock_logger.log_request("exp_msg_2", "test", "client", "server", {})
    mock_logger.log_response("exp_msg_2", {}, "success", 100.0)
    
    # Export as CSV
    csv_data = mock_logger.export_traffic(format='csv')
    
    assert csv_data
    assert 'id,timestamp' in csv_data
    assert 'exp_msg_2' in csv_data


def test_cleanup_endpoint_removes_old(mock_logger):
    """Test cleanup endpoint removes old records."""
    import sqlite3
    from datetime import datetime, timedelta
    
    # Add old message manually
    old_time = (datetime.now() - timedelta(days=10)).isoformat()
    conn = sqlite3.connect(mock_logger.db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO mcp_traffic 
        (id, timestamp, message_type, from_agent, to_agent, request)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('old_msg', old_time, 'test', 'client', 'server', '{}'))
    conn.commit()
    conn.close()
    
    # Add recent message
    mock_logger.log_request("new_msg", "test", "client", "server", {})
    
    # Cleanup
    deleted = mock_logger.cleanup_old()
    
    assert deleted == 1
    
    # Verify only recent message remains
    messages = mock_logger.get_traffic(limit=100)
    assert len(messages) == 1
    assert messages[0].id == "new_msg"
