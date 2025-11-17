"""
Unit tests for MCP Traffic Logger.
"""

import pytest
import os
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path

from src.mcp.traffic_logger import (
    MCPTrafficLogger,
    MCPMessage,
    get_traffic_logger,
    set_traffic_logger
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def logger(temp_db):
    """Create a traffic logger with temporary database."""
    return MCPTrafficLogger(db_path=temp_db, retention_days=7)


def test_logger_initialization(temp_db):
    """Test logger initializes correctly."""
    logger = MCPTrafficLogger(db_path=temp_db, retention_days=7)
    assert logger.db_path == temp_db
    assert logger.retention_days == 7
    assert Path(temp_db).exists()


def test_log_request(logger):
    """Test logging a request."""
    logger.log_request(
        message_id="test_001",
        message_type="workflow.execute",
        from_agent="mcp_client",
        to_agent="workflow_engine",
        request={"workflow_id": "test", "inputs": {}}
    )
    
    # Retrieve the message
    messages = logger.get_traffic(limit=10)
    assert len(messages) == 1
    assert messages[0].id == "test_001"
    assert messages[0].from_agent == "mcp_client"
    assert messages[0].to_agent == "workflow_engine"


def test_log_response(logger):
    """Test logging a response."""
    # Log request first
    logger.log_request(
        message_id="test_002",
        message_type="agent.invoke",
        from_agent="client",
        to_agent="agent1",
        request={"action": "test"}
    )
    
    # Log response
    logger.log_response(
        message_id="test_002",
        response={"result": "success"},
        status="success",
        duration_ms=123.45
    )
    
    # Retrieve and verify
    messages = logger.get_traffic(limit=10)
    assert len(messages) == 1
    msg = messages[0]
    assert msg.response == {"result": "success"}
    assert msg.status == "success"
    assert msg.duration_ms == 123.45


def test_log_error_response(logger):
    """Test logging an error response."""
    logger.log_request(
        message_id="test_003",
        message_type="workflow.execute",
        from_agent="client",
        to_agent="engine",
        request={}
    )
    
    logger.log_response(
        message_id="test_003",
        response={},
        status="error",
        duration_ms=50.0,
        error="Test error message"
    )
    
    messages = logger.get_traffic(limit=10)
    msg = messages[0]
    assert msg.status == "error"
    assert msg.error == "Test error message"


def test_get_traffic_with_filters(logger):
    """Test retrieving traffic with filters."""
    # Add multiple messages
    logger.log_request("msg_1", "workflow.execute", "client", "engine", {})
    logger.log_response("msg_1", {}, "success", 100.0)
    
    logger.log_request("msg_2", "agent.invoke", "client", "agent1", {})
    logger.log_response("msg_2", {}, "success", 200.0)
    
    logger.log_request("msg_3", "workflow.execute", "client", "engine", {})
    logger.log_response("msg_3", {}, "error", 150.0, "Test error")
    
    # Test agent_id filter
    messages = logger.get_traffic(agent_id="agent1")
    assert len(messages) == 1
    assert messages[0].to_agent == "agent1"
    
    # Test message_type filter
    messages = logger.get_traffic(message_type="workflow.execute")
    assert len(messages) == 2
    
    # Test status filter
    messages = logger.get_traffic(status="error")
    assert len(messages) == 1
    assert messages[0].status == "error"


def test_get_traffic_with_limit_offset(logger):
    """Test pagination with limit and offset."""
    # Add 10 messages
    for i in range(10):
        logger.log_request(f"msg_{i}", "test", "client", "server", {})
        logger.log_response(f"msg_{i}", {}, "success", 100.0)
    
    # Get first 5
    messages = logger.get_traffic(limit=5, offset=0)
    assert len(messages) == 5
    
    # Get next 5
    messages = logger.get_traffic(limit=5, offset=5)
    assert len(messages) == 5


def test_get_message(logger):
    """Test getting a specific message by ID."""
    logger.log_request("test_msg", "workflow.execute", "client", "engine", {"test": "data"})
    logger.log_response("test_msg", {"result": "ok"}, "success", 123.0)
    
    message = logger.get_message("test_msg")
    assert message is not None
    assert message.id == "test_msg"
    assert message.request == {"test": "data"}
    assert message.response == {"result": "ok"}
    
    # Test non-existent message
    message = logger.get_message("nonexistent")
    assert message is None


def test_get_metrics(logger):
    """Test getting traffic metrics."""
    # Add some test messages
    logger.log_request("msg_1", "workflow.execute", "client", "engine", {})
    logger.log_response("msg_1", {}, "success", 100.0)
    
    logger.log_request("msg_2", "workflow.execute", "client", "engine", {})
    logger.log_response("msg_2", {}, "success", 200.0)
    
    logger.log_request("msg_3", "agent.invoke", "client", "agent1", {})
    logger.log_response("msg_3", {}, "error", 50.0, "Error")
    
    metrics = logger.get_metrics()
    
    assert metrics['total_messages'] == 3
    assert metrics['avg_latency_ms'] == 116.67  # (100 + 200 + 50) / 3
    assert metrics['error_count'] == 1
    assert metrics['error_rate'] == pytest.approx(33.33, rel=0.1)
    assert 'client' in metrics['top_agents']
    assert 'workflow.execute' in metrics['by_type']
    assert metrics['by_type']['workflow.execute'] == 2


def test_cleanup_old(logger):
    """Test cleaning up old traffic."""
    # Add messages with old timestamp
    old_time = (datetime.now() - timedelta(days=10)).isoformat()
    
    # Manually insert old message
    import sqlite3
    conn = sqlite3.connect(logger.db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO mcp_traffic 
        (id, timestamp, message_type, from_agent, to_agent, request)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('old_msg', old_time, 'test', 'client', 'server', '{}'))
    conn.commit()
    conn.close()
    
    # Add recent message
    logger.log_request("new_msg", "test", "client", "server", {})
    
    # Cleanup old messages
    deleted = logger.cleanup_old()
    assert deleted == 1
    
    # Verify only recent message remains
    messages = logger.get_traffic(limit=100)
    assert len(messages) == 1
    assert messages[0].id == "new_msg"


def test_export_traffic_json(logger):
    """Test exporting traffic to JSON."""
    logger.log_request("msg_1", "test", "client", "server", {"data": "test"})
    logger.log_response("msg_1", {"result": "ok"}, "success", 100.0)
    
    json_data = logger.export_traffic(format='json')
    
    # Parse and verify
    data = json.loads(json_data)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['id'] == 'msg_1'


def test_export_traffic_csv(logger):
    """Test exporting traffic to CSV."""
    logger.log_request("msg_1", "test", "client", "server", {})
    logger.log_response("msg_1", {}, "success", 100.0)
    
    csv_data = logger.export_traffic(format='csv')
    
    # Verify CSV format
    lines = csv_data.strip().split('\n')
    assert len(lines) == 2  # Header + 1 data row
    assert 'id,timestamp,from_agent' in lines[0]
    assert 'msg_1' in lines[1]


def test_export_traffic_invalid_format(logger):
    """Test exporting with invalid format raises error."""
    logger.log_request("msg_1", "test", "client", "server", {})
    
    with pytest.raises(ValueError):
        logger.export_traffic(format='invalid')


def test_global_logger_singleton():
    """Test global logger is singleton."""
    logger1 = get_traffic_logger()
    logger2 = get_traffic_logger()
    assert logger1 is logger2


def test_set_traffic_logger(temp_db):
    """Test setting custom traffic logger."""
    custom_logger = MCPTrafficLogger(db_path=temp_db)
    set_traffic_logger(custom_logger)
    
    retrieved = get_traffic_logger()
    assert retrieved is custom_logger
