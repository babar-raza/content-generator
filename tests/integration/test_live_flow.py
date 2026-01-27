"""Integration tests for live flow monitoring via WebSocket

Tests the complete flow of real-time agent execution monitoring through WebSocket connections.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from fastapi import WebSocket
from fastapi.testclient import TestClient

from src.web.websocket_handlers import LiveFlowHandler, get_live_flow_handler, set_live_flow_handler
from src.core import EventBus, AgentEvent
from src.web.app import create_app


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.messages = []
        self.closed = False
        self.accepted = False
        
    async def accept(self):
        self.accepted = True
        
    async def send_json(self, data):
        if not self.closed:
            self.messages.append(data)
    
    async def send_text(self, text):
        if not self.closed:
            self.messages.append({"__text__": text})
    
    async def receive_text(self):
        # Simulate timeout for keep-alive
        await asyncio.sleep(0.1)
        raise asyncio.TimeoutError()
    
    def close(self):
        self.closed = True


@pytest.fixture
def event_bus():
    """Create event bus for testing"""
    return EventBus()


@pytest.fixture
def live_handler(event_bus):
    """Create live flow handler"""
    return LiveFlowHandler(event_bus=event_bus)


@pytest.fixture
def mock_websocket():
    """Create mock websocket"""
    return MockWebSocket()


@pytest.mark.live
@pytest.mark.asyncio
async def test_websocket_connection(live_handler, mock_websocket):
    """Test WebSocket connection establishment"""
    job_id = "test-job-123"
    
    # Start connection handler in background
    task = asyncio.create_task(live_handler.handle_connection(mock_websocket, job_id))
    
    # Give it time to accept and send initial message
    await asyncio.sleep(0.2)
    
    # Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify connection was accepted
    assert mock_websocket.accepted
    
    # Verify initial message was sent
    assert len(mock_websocket.messages) > 0
    initial_msg = mock_websocket.messages[0]
    assert initial_msg["type"] == "connected"
    assert initial_msg["job_id"] == job_id


@pytest.mark.live
@pytest.mark.asyncio
async def test_agent_started_event(live_handler, mock_websocket, event_bus):
    """Test agent_started event is broadcast via WebSocket"""
    job_id = "test-job-123"
    agent_id = "test_agent"
    
    # Start connection handler in background
    task = asyncio.create_task(live_handler.handle_connection(mock_websocket, job_id))
    await asyncio.sleep(0.1)
    
    # Publish agent started event
    event = AgentEvent(
        event_type="agent_started",
        data={"input_keys": ["topic"]},
        source_agent=agent_id,
        correlation_id=job_id,
        metadata={"job_id": job_id}
    )
    event_bus.publish(event)
    
    # Give it time to process
    await asyncio.sleep(0.1)
    
    # Cancel task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify message was sent
    agent_started_msgs = [m for m in mock_websocket.messages if m.get("type") == "agent_started"]
    assert len(agent_started_msgs) > 0
    
    msg = agent_started_msgs[0]
    assert msg["agent_id"] == agent_id
    assert msg["correlation_id"] == job_id


@pytest.mark.live
@pytest.mark.asyncio
async def test_agent_completed_event(live_handler, mock_websocket, event_bus):
    """Test agent_completed event is broadcast via WebSocket"""
    job_id = "test-job-123"
    agent_id = "test_agent"
    
    # Start connection handler in background
    task = asyncio.create_task(live_handler.handle_connection(mock_websocket, job_id))
    await asyncio.sleep(0.1)
    
    # Publish agent completed event
    event = AgentEvent(
        event_type="agent_completed",
        data={"result": "success"},
        source_agent=agent_id,
        correlation_id=job_id,
        metadata={
            "job_id": job_id,
            "duration": 2.5,
            "llm_calls": 3
        }
    )
    event_bus.publish(event)
    
    # Give it time to process
    await asyncio.sleep(0.1)
    
    # Cancel task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify message was sent
    completed_msgs = [m for m in mock_websocket.messages if m.get("type") == "agent_completed"]
    assert len(completed_msgs) > 0
    
    msg = completed_msgs[0]
    assert msg["agent_id"] == agent_id
    assert msg["duration"] == 2.5
    assert msg["output"] == {"result": "success"}


@pytest.mark.live
@pytest.mark.asyncio
async def test_agent_failed_event(live_handler, mock_websocket, event_bus):
    """Test agent_failed event is broadcast via WebSocket"""
    job_id = "test-job-123"
    agent_id = "test_agent"
    error_msg = "Test error"
    
    # Start connection handler in background
    task = asyncio.create_task(live_handler.handle_connection(mock_websocket, job_id))
    await asyncio.sleep(0.1)
    
    # Publish agent failed event
    event = AgentEvent(
        event_type="agent_failed",
        data={"error": error_msg},
        source_agent=agent_id,
        correlation_id=job_id,
        metadata={"job_id": job_id}
    )
    event_bus.publish(event)
    
    # Give it time to process
    await asyncio.sleep(0.1)
    
    # Cancel task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify message was sent
    failed_msgs = [m for m in mock_websocket.messages if m.get("type") == "agent_failed"]
    assert len(failed_msgs) > 0
    
    msg = failed_msgs[0]
    assert msg["agent_id"] == agent_id
    assert msg["error"] == error_msg


@pytest.mark.live
@pytest.mark.asyncio
async def test_data_flow_event(live_handler, mock_websocket, event_bus):
    """Test data_flow event is broadcast via WebSocket"""
    job_id = "test-job-123"
    
    # Start connection handler in background
    task = asyncio.create_task(live_handler.handle_connection(mock_websocket, job_id))
    await asyncio.sleep(0.1)
    
    # Publish data flow event
    event = AgentEvent(
        event_type="data_flow",
        data={"content": "test data"},
        source_agent="agent1",
        correlation_id=job_id,
        metadata={
            "job_id": job_id,
            "from_agent": "agent1",
            "to_agent": "agent2"
        }
    )
    event_bus.publish(event)
    
    # Give it time to process
    await asyncio.sleep(0.1)
    
    # Cancel task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify message was sent
    flow_msgs = [m for m in mock_websocket.messages if m.get("type") == "data_flow"]
    assert len(flow_msgs) > 0
    
    msg = flow_msgs[0]
    assert msg["from_agent"] == "agent1"
    assert msg["to_agent"] == "agent2"
    assert "data_size" in msg


@pytest.mark.live
@pytest.mark.asyncio
async def test_multiple_connections(live_handler, event_bus):
    """Test multiple WebSocket connections for same job"""
    job_id = "test-job-123"
    
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    # Start both connections
    task1 = asyncio.create_task(live_handler.handle_connection(ws1, job_id))
    task2 = asyncio.create_task(live_handler.handle_connection(ws2, job_id))
    await asyncio.sleep(0.1)
    
    # Publish event
    event = AgentEvent(
        event_type="agent_started",
        data={},
        source_agent="test_agent",
        correlation_id=job_id,
        metadata={"job_id": job_id}
    )
    event_bus.publish(event)
    
    await asyncio.sleep(0.1)
    
    # Cancel tasks
    task1.cancel()
    task2.cancel()
    try:
        await task1
    except asyncio.CancelledError:
        pass
    try:
        await task2
    except asyncio.CancelledError:
        pass
    
    # Both should have received the message
    assert len([m for m in ws1.messages if m.get("type") == "agent_started"]) > 0
    assert len([m for m in ws2.messages if m.get("type") == "agent_started"]) > 0


@pytest.mark.live
@pytest.mark.asyncio
async def test_connection_cleanup(live_handler, mock_websocket):
    """Test connection cleanup on disconnect"""
    job_id = "test-job-123"
    
    # Verify initial state
    assert live_handler.get_connection_count(job_id) == 0
    
    # Start connection
    task = asyncio.create_task(live_handler.handle_connection(mock_websocket, job_id))
    await asyncio.sleep(0.1)
    
    # Verify connection is tracked
    assert live_handler.get_connection_count(job_id) == 1
    
    # Cancel task (simulates disconnect)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    await asyncio.sleep(0.1)
    
    # Verify connection is cleaned up
    assert live_handler.get_connection_count(job_id) == 0


@pytest.mark.live
@pytest.mark.asyncio
async def test_event_filtering_by_job(live_handler, event_bus):
    """Test events are only sent to correct job connections"""
    job1 = "job-1"
    job2 = "job-2"
    
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    # Start connections for different jobs
    task1 = asyncio.create_task(live_handler.handle_connection(ws1, job1))
    task2 = asyncio.create_task(live_handler.handle_connection(ws2, job2))
    await asyncio.sleep(0.1)
    
    # Publish event for job1
    event = AgentEvent(
        event_type="agent_started",
        data={},
        source_agent="test_agent",
        correlation_id=job1,
        metadata={"job_id": job1}
    )
    event_bus.publish(event)
    
    await asyncio.sleep(0.1)
    
    # Cancel tasks
    task1.cancel()
    task2.cancel()
    try:
        await task1
        await task2
    except asyncio.CancelledError:
        pass
    
    # Only ws1 should have received the message
    ws1_agent_msgs = [m for m in ws1.messages if m.get("type") == "agent_started"]
    ws2_agent_msgs = [m for m in ws2.messages if m.get("type") == "agent_started"]
    
    assert len(ws1_agent_msgs) > 0
    assert len(ws2_agent_msgs) == 0


@pytest.mark.live
def test_global_handler_singleton():
    """Test global handler singleton pattern"""
    handler1 = get_live_flow_handler()
    handler2 = get_live_flow_handler()

    assert handler1 is handler2


@pytest.mark.live
def test_set_global_handler():
    """Test setting global handler"""
    custom_handler = LiveFlowHandler()
    set_live_flow_handler(custom_handler)

    retrieved = get_live_flow_handler()
    assert retrieved is custom_handler


@pytest.mark.live
@pytest.mark.asyncio
async def test_progress_update_event(live_handler, mock_websocket, event_bus):
    """Test progress_update event is broadcast via WebSocket"""
    job_id = "test-job-123"
    
    # Start connection handler
    task = asyncio.create_task(live_handler.handle_connection(mock_websocket, job_id))
    await asyncio.sleep(0.1)
    
    # Publish progress update event
    event = AgentEvent(
        event_type="progress_update",
        data={"progress": 50, "message": "Half done"},
        source_agent="orchestrator",
        correlation_id=job_id,
        metadata={"job_id": job_id}
    )
    event_bus.publish(event)
    
    await asyncio.sleep(0.1)
    
    # Cancel task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    # Verify message was sent
    progress_msgs = [m for m in mock_websocket.messages if m.get("type") == "progress_update"]
    assert len(progress_msgs) > 0
    
    msg = progress_msgs[0]
    assert msg["progress"] == 50
    assert msg["message"] == "Half done"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
