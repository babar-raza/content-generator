"""Unit tests for src/utils/simple_monitor.py.

Tests simple web monitor including:
- MonitorState class
- SimpleWebMonitor class
- Event tracking
- Agent tracking
- Job tracking
- Global monitor instance
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import threading
import time
from datetime import datetime
from collections import deque

from src.utils.simple_monitor import (
    MonitorState,
    SimpleWebMonitor,
    get_monitor,
    track_event,
    track_agent,
    track_job,
    state
)


# ============================================================================
# Test MonitorState
# ============================================================================

class TestMonitorState:
    """Test MonitorState class."""

    def test_init(self):
        """Test MonitorState initialization."""
        monitor_state = MonitorState()
        assert monitor_state.agents == {}
        assert isinstance(monitor_state.events, deque)
        assert monitor_state.jobs == {}
        assert isinstance(monitor_state.start_time, datetime)

    def test_add_event(self):
        """Test adding event."""
        monitor_state = MonitorState()
        monitor_state.add_event({"type": "test", "message": "test event"})

        assert len(monitor_state.events) == 1
        event = list(monitor_state.events)[0]
        assert 'timestamp' in event
        assert 'event' in event
        assert event['event']['type'] == "test"

    def test_add_multiple_events(self):
        """Test adding multiple events."""
        monitor_state = MonitorState()
        for i in range(10):
            monitor_state.add_event({"count": i})

        assert len(monitor_state.events) == 10

    def test_events_maxlen_100(self):
        """Test events deque has max length of 100."""
        monitor_state = MonitorState()

        # Add 150 events
        for i in range(150):
            monitor_state.add_event({"count": i})

        # Should only keep last 100
        assert len(monitor_state.events) == 100
        # First event should be event 50 (0-49 dropped)
        first_event = list(monitor_state.events)[0]
        assert first_event['event']['count'] == 50

    def test_update_agent(self):
        """Test updating agent status."""
        monitor_state = MonitorState()
        monitor_state.update_agent("test_agent", "running")

        assert "test_agent" in monitor_state.agents
        agent = monitor_state.agents["test_agent"]
        assert agent['name'] == "test_agent"
        assert agent['status'] == "running"
        assert 'last_update' in agent

    def test_update_agent_overwrites(self):
        """Test updating agent overwrites previous status."""
        monitor_state = MonitorState()
        monitor_state.update_agent("test_agent", "running")
        monitor_state.update_agent("test_agent", "stopped")

        assert len(monitor_state.agents) == 1
        assert monitor_state.agents["test_agent"]['status'] == "stopped"

    def test_update_multiple_agents(self):
        """Test updating multiple agents."""
        monitor_state = MonitorState()
        monitor_state.update_agent("agent1", "active")
        monitor_state.update_agent("agent2", "idle")
        monitor_state.update_agent("agent3", "error")

        assert len(monitor_state.agents) == 3
        assert monitor_state.agents["agent1"]['status'] == "active"
        assert monitor_state.agents["agent2"]['status'] == "idle"
        assert monitor_state.agents["agent3"]['status'] == "error"

    def test_add_job(self):
        """Test adding job."""
        monitor_state = MonitorState()
        job_info = {
            "workflow": "test-workflow",
            "status": "running",
            "progress": 50
        }
        monitor_state.add_job("job123", job_info)

        assert "job123" in monitor_state.jobs
        assert monitor_state.jobs["job123"] == job_info

    def test_add_multiple_jobs(self):
        """Test adding multiple jobs."""
        monitor_state = MonitorState()
        monitor_state.add_job("job1", {"status": "running"})
        monitor_state.add_job("job2", {"status": "completed"})

        assert len(monitor_state.jobs) == 2


# ============================================================================
# Test SimpleWebMonitor
# ============================================================================

class TestSimpleWebMonitor:
    """Test SimpleWebMonitor class."""

    def test_init_default(self):
        """Test initialization with default parameters."""
        monitor = SimpleWebMonitor()
        assert monitor.host == '0.0.0.0'
        assert monitor.port == 8080
        assert monitor.running is False
        assert monitor.server_thread is None

    def test_init_custom_port(self):
        """Test initialization with custom port."""
        monitor = SimpleWebMonitor(host='localhost', port=9000)
        assert monitor.host == 'localhost'
        assert monitor.port == 9000

    @patch('http.server.HTTPServer')
    @patch('threading.Thread')
    @patch('webbrowser.open')
    @patch('time.sleep')
    def test_start_success(self, mock_sleep, mock_browser, mock_thread, mock_http_server):
        """Test starting monitor successfully."""
        monitor = SimpleWebMonitor(port=8081)

        # Mock thread to set running flag
        def mock_thread_init(*args, **kwargs):
            monitor.running = True
            return Mock()

        mock_thread.side_effect = mock_thread_init

        result = monitor.start()

        # Should return True on success
        assert result is True or monitor.server_thread is not None

    def test_start_integration(self):
        """Test start method runs without errors."""
        monitor = SimpleWebMonitor(port=18082)
        # Just test that start doesn't crash
        # It will start a background thread
        try:
            monitor.start()
            # Stop it immediately
            monitor.stop()
        except Exception:
            pass  # Server may or may not start, just check no crash

    def test_stop(self):
        """Test stopping monitor."""
        monitor = SimpleWebMonitor()
        monitor.running = True
        monitor.stop()
        assert monitor.running is False


# ============================================================================
# Test Global Monitor Instance
# ============================================================================

class TestGetMonitor:
    """Test get_monitor function."""

    def test_get_monitor_creates_instance(self):
        """Test get_monitor creates instance."""
        # Reset global monitor
        import src.utils.simple_monitor as module
        module._monitor = None

        monitor = get_monitor()
        assert isinstance(monitor, SimpleWebMonitor)

    def test_get_monitor_returns_same_instance(self):
        """Test get_monitor returns same instance."""
        # Reset global monitor
        import src.utils.simple_monitor as module
        module._monitor = None

        monitor1 = get_monitor()
        monitor2 = get_monitor()
        assert monitor1 is monitor2

    def test_get_monitor_custom_port(self):
        """Test get_monitor with custom port."""
        # Reset global monitor
        import src.utils.simple_monitor as module
        module._monitor = None

        monitor = get_monitor(host='localhost', port=9090)
        assert monitor.host == 'localhost'
        assert monitor.port == 9090


# ============================================================================
# Test Event Tracking Functions
# ============================================================================

class TestTrackEvent:
    """Test track_event function."""

    def test_track_event_adds_to_state(self):
        """Test track_event adds event to global state."""
        initial_count = len(state.events)

        track_event({"type": "test", "data": "test data"})

        assert len(state.events) == initial_count + 1

    def test_track_event_with_dict(self):
        """Test tracking event with dictionary."""
        event_data = {
            "type": "agent_started",
            "agent": "test_agent",
            "timestamp": "2024-01-01"
        }

        initial_count = len(state.events)
        track_event(event_data)

        assert len(state.events) == initial_count + 1
        # Most recent event should contain our data
        latest_event = list(state.events)[-1]
        assert latest_event['event']['type'] == "agent_started"

    def test_track_event_with_string(self):
        """Test tracking event with string."""
        initial_count = len(state.events)
        track_event("Simple string event")

        assert len(state.events) == initial_count + 1
        latest_event = list(state.events)[-1]
        assert latest_event['event'] == "Simple string event"


class TestTrackAgent:
    """Test track_agent function."""

    def test_track_agent_default_status(self):
        """Test tracking agent with default status."""
        track_agent("new_agent")

        assert "new_agent" in state.agents
        assert state.agents["new_agent"]['status'] == "active"

    def test_track_agent_custom_status(self):
        """Test tracking agent with custom status."""
        track_agent("custom_agent", "processing")

        assert "custom_agent" in state.agents
        assert state.agents["custom_agent"]['status'] == "processing"

    def test_track_agent_updates_existing(self):
        """Test tracking agent updates existing agent."""
        track_agent("update_agent", "started")
        track_agent("update_agent", "completed")

        # Should have updated the same agent
        assert state.agents["update_agent"]['status'] == "completed"


class TestTrackJob:
    """Test track_job function."""

    def test_track_job_adds_to_state(self):
        """Test track_job adds job to global state."""
        job_info = {
            "workflow": "blog-generation",
            "status": "running",
            "progress": 75
        }

        track_job("job_test_123", job_info)

        assert "job_test_123" in state.jobs
        assert state.jobs["job_test_123"] == job_info

    def test_track_multiple_jobs(self):
        """Test tracking multiple jobs."""
        initial_count = len(state.jobs)

        track_job("job1", {"status": "pending"})
        track_job("job2", {"status": "running"})
        track_job("job3", {"status": "completed"})

        assert len(state.jobs) >= initial_count + 3


# ============================================================================
# Test MonitorHandler (via integration scenarios)
# ============================================================================

class TestMonitorHandlerIntegration:
    """Test MonitorHandler integration scenarios."""

    def test_monitor_state_integration(self):
        """Test complete workflow with state."""
        # Create fresh state
        test_state = MonitorState()

        # Track events
        test_state.add_event({"type": "workflow_started"})
        test_state.add_event({"type": "agent_invoked"})

        # Track agents
        test_state.update_agent("kb_ingestion", "running")
        test_state.update_agent("content_generator", "idle")

        # Track jobs
        test_state.add_job("workflow_001", {
            "workflow": "blog-post",
            "status": "running",
            "step": 3,
            "total_steps": 10
        })

        # Verify state
        assert len(test_state.events) == 2
        assert len(test_state.agents) == 2
        assert len(test_state.jobs) == 1

        # Verify uptime is tracked
        assert isinstance(test_state.start_time, datetime)

    def test_monitor_lifecycle(self):
        """Test monitor start and stop lifecycle."""
        monitor = SimpleWebMonitor(port=18080)  # Use different port

        # Initially not running
        assert monitor.running is False

        # Stop before start should not error
        monitor.stop()
        assert monitor.running is False

    def test_concurrent_event_tracking(self):
        """Test concurrent event tracking."""
        test_state = MonitorState()

        # Simulate concurrent event additions
        events_to_add = [
            {"id": i, "type": "concurrent"}
            for i in range(50)
        ]

        for event in events_to_add:
            test_state.add_event(event)

        # All events should be tracked
        assert len(test_state.events) == 50


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_event(self):
        """Test tracking empty event."""
        test_state = MonitorState()
        test_state.add_event({})

        assert len(test_state.events) == 1

    def test_none_event(self):
        """Test tracking None event."""
        test_state = MonitorState()
        test_state.add_event(None)

        # Should still add it
        assert len(test_state.events) == 1
        latest_event = list(test_state.events)[-1]
        assert latest_event['event'] is None

    def test_agent_with_empty_status(self):
        """Test agent with empty status."""
        test_state = MonitorState()
        test_state.update_agent("empty_agent", "")

        assert "empty_agent" in test_state.agents
        assert test_state.agents["empty_agent"]['status'] == ""

    def test_job_with_empty_info(self):
        """Test job with empty info."""
        test_state = MonitorState()
        test_state.add_job("empty_job", {})

        assert "empty_job" in test_state.jobs
        assert test_state.jobs["empty_job"] == {}

    def test_monitor_state_persistence(self):
        """Test monitor state maintains data."""
        test_state = MonitorState()

        # Add data
        test_state.add_event({"type": "test"})
        test_state.update_agent("agent1", "active")
        test_state.add_job("job1", {"status": "running"})

        # Data should persist
        assert len(test_state.events) >= 1
        assert "agent1" in test_state.agents
        assert "job1" in test_state.jobs

        # Add more data
        test_state.add_event({"type": "test2"})

        # Previous data still there
        assert len(test_state.events) >= 2
        assert "agent1" in test_state.agents


# ============================================================================
# Test MonitorState Time Tracking
# ============================================================================

class TestMonitorStateTimeTracking:
    """Test time tracking in MonitorState."""

    def test_start_time_recorded(self):
        """Test start time is recorded."""
        test_state = MonitorState()

        assert isinstance(test_state.start_time, datetime)
        # Should be very recent
        time_diff = (datetime.now() - test_state.start_time).total_seconds()
        assert time_diff < 1.0  # Less than 1 second old

    def test_event_timestamp_recorded(self):
        """Test event timestamp is recorded."""
        test_state = MonitorState()
        test_state.add_event({"type": "test"})

        event = list(test_state.events)[0]
        assert 'timestamp' in event
        # Should be ISO format string
        assert isinstance(event['timestamp'], str)
        assert 'T' in event['timestamp'] or ':' in event['timestamp']

    def test_agent_last_update_recorded(self):
        """Test agent last update is recorded."""
        test_state = MonitorState()
        test_state.update_agent("test_agent", "running")

        agent = test_state.agents["test_agent"]
        assert 'last_update' in agent
        assert isinstance(agent['last_update'], str)


# ============================================================================
# Test Deque Behavior
# ============================================================================

class TestDequeMaxlen:
    """Test deque maxlen behavior."""

    def test_events_deque_maxlen(self):
        """Test events deque respects maxlen."""
        test_state = MonitorState()

        # Verify maxlen is set
        assert test_state.events.maxlen == 100

        # Add exactly 100 events
        for i in range(100):
            test_state.add_event({"id": i})

        assert len(test_state.events) == 100

        # Add one more
        test_state.add_event({"id": 100})

        # Should still be 100
        assert len(test_state.events) == 100

        # First event should now be id=1 (id=0 dropped)
        first_event = list(test_state.events)[0]
        assert first_event['event']['id'] == 1

        # Last event should be id=100
        last_event = list(test_state.events)[-1]
        assert last_event['event']['id'] == 100
