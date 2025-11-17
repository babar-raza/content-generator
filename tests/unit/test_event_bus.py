"""Unit tests for src/core/event_bus.py - subscribe → publish → handler called once; unsubscribe works."""

import pytest
from unittest.mock import MagicMock, call

# Add src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.event_bus import EventBus
from src.core.contracts import AgentEvent


class TestEventBus:
    """Test EventBus subscribe/publish/unsubscribe functionality."""

    def setup_method(self):
        """Create fresh EventBus for each test."""
        self.bus = EventBus()

    def test_subscribe_and_publish(self):
        """Test basic subscribe → publish → handler called once."""
        # Create mock handler
        handler = MagicMock()

        # Subscribe to event
        self.bus.subscribe("test_event", handler)

        # Create test event
        event = AgentEvent(
            event_type="test_event",
            source_agent="test_agent",
            correlation_id="test-correlation",
            data={"key": "value"}
        )

        # Publish event
        self.bus.publish(event)

        # Verify handler was called once with correct event
        handler.assert_called_once_with(event)
        assert handler.call_count == 1

    def test_multiple_subscribers_same_event(self):
        """Test multiple subscribers to same event."""
        handler1 = MagicMock()
        handler2 = MagicMock()
        handler3 = MagicMock()

        # Subscribe multiple handlers
        self.bus.subscribe("test_event", handler1)
        self.bus.subscribe("test_event", handler2)
        self.bus.subscribe("test_event", handler3)

        # Create and publish event
        event = AgentEvent(
            event_type="test_event",
            source_agent="test_agent",
            correlation_id="test-correlation-2",
            data={"count": 42}
        )
        self.bus.publish(event)

        # All handlers should be called once
        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)
        handler3.assert_called_once_with(event)

    def test_unsubscribe_works(self):
        """Test that unsubscribe removes handler."""
        handler1 = MagicMock()
        handler2 = MagicMock()

        # Subscribe both
        self.bus.subscribe("test_event", handler1)
        self.bus.subscribe("test_event", handler2)

        # Unsubscribe handler1
        self.bus.unsubscribe("test_event", handler1)

        # Publish event
        event = AgentEvent(
            event_type="test_event",
            source_agent="test_agent",
            correlation_id="test-correlation-3",
            data={"test": True}
        )
        self.bus.publish(event)

        # Only handler2 should be called
        handler1.assert_not_called()
        handler2.assert_called_once_with(event)

    def test_unsubscribe_nonexistent_handler(self):
        """Test unsubscribing handler that was never subscribed."""
        handler1 = MagicMock()
        handler2 = MagicMock()

        # Subscribe only handler1
        self.bus.subscribe("test_event", handler1)

        # Try to unsubscribe handler2 (should not raise error)
        self.bus.unsubscribe("test_event", handler2)

        # Publish event - only handler1 should be called
        event = AgentEvent(event_type="test_event", source_agent="test_agent", correlation_id="test-corr", data={})
        self.bus.publish(event)

        handler1.assert_called_once_with(event)
        handler2.assert_not_called()

    def test_different_event_types_isolated(self):
        """Test that different event types are isolated."""
        handler1 = MagicMock()
        handler2 = MagicMock()

        # Subscribe to different events
        self.bus.subscribe("event_a", handler1)
        self.bus.subscribe("event_b", handler2)

        # Publish to event_a
        event_a = AgentEvent(event_type="event_a", source_agent="agent1", correlation_id="corr-a", data={})
        self.bus.publish(event_a)

        # Only handler1 should be called
        handler1.assert_called_once_with(event_a)
        handler2.assert_not_called()

        # Publish to event_b
        event_b = AgentEvent(event_type="event_b", source_agent="agent2", correlation_id="corr-b", data={})
        self.bus.publish(event_b)

        # Now handler2 should be called too
        handler2.assert_called_once_with(event_b)
        assert handler1.call_count == 1  # Still only once

    def test_no_subscribers_no_error(self):
        """Test publishing to event with no subscribers doesn't error."""
        event = AgentEvent(
            event_type="no_subscribers",
            source_agent="test_agent",
            correlation_id="test-corr",
            data={"test": "data"}
        )

        # Should not raise any exception
        self.bus.publish(event)

    def test_handler_exception_doesnt_break_others(self):
        """Test that one handler exception doesn't prevent others from running."""
        handler1 = MagicMock(side_effect=ValueError("Handler 1 failed"))
        handler2 = MagicMock()
        handler3 = MagicMock()

        # Subscribe all three
        self.bus.subscribe("test_event", handler1)
        self.bus.subscribe("test_event", handler2)
        self.bus.subscribe("test_event", handler3)

        # Publish event
        event = AgentEvent(event_type="test_event", source_agent="test_agent", correlation_id="test-corr", data={})
        self.bus.publish(event)

        # All handlers should be called despite handler1's exception
        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)
        handler3.assert_called_once_with(event)

    def test_event_history(self):
        """Test event history tracking."""
        # Create and publish events
        event1 = AgentEvent(event_type="event1", source_agent="agent1", correlation_id="corr-1", data={})
        event2 = AgentEvent(event_type="event2", source_agent="agent2", correlation_id="corr-2", data={})
        event3 = AgentEvent(event_type="event1", source_agent="agent3", correlation_id="corr-3", data={})

        self.bus.publish(event1)
        self.bus.publish(event2)
        self.bus.publish(event3)

        # Check history
        history = self.bus.get_history()
        assert len(history) == 3
        assert history[0] == event3  # Most recent first
        assert history[1] == event2
        assert history[2] == event1

        # Check filtered history
        event1_history = self.bus.get_history("event1")
        assert len(event1_history) == 2
        assert event1_history[0] == event3
        assert event1_history[1] == event1

    def test_event_history_limit(self):
        """Test event history respects max limit."""
        # Set small history limit
        self.bus._max_history = 2

        # Publish 3 events
        for i in range(3):
            event = AgentEvent(event_type=f"event{i}", source_agent=f"agent{i}", correlation_id=f"corr-{i}", data={})
            self.bus.publish(event)

        # Should only keep last 2
        history = self.bus.get_history()
        assert len(history) == 2
        assert history[0].event_type == "event2"
        assert history[1].event_type == "event1"

    def test_clear_history(self):
        """Test clearing event history."""
        # Add some events
        self.bus.publish(AgentEvent(event_type="test", source_agent="agent", correlation_id="corr-test", data={}))
        assert len(self.bus.get_history()) == 1

        # Clear history
        self.bus.clear_history()
        assert len(self.bus.get_history()) == 0

    def test_subscriber_count(self):
        """Test getting subscriber count for event types."""
        # Initially no subscribers
        assert self.bus.get_subscriber_count("test_event") == 0

        # Add subscribers
        self.bus.subscribe("test_event", MagicMock())
        assert self.bus.get_subscriber_count("test_event") == 1

        self.bus.subscribe("test_event", MagicMock())
        assert self.bus.get_subscriber_count("test_event") == 2

        # Different event type
        assert self.bus.get_subscriber_count("other_event") == 0

    def test_thread_safety(self):
        """Test that EventBus operations are thread-safe."""
        import threading
        import time

        results = []
        errors = []

        def add_subscriber(event_type, handler_id):
            try:
                handler = MagicMock()
                self.bus.subscribe(event_type, handler)
                results.append(f"subscribed_{handler_id}")
            except Exception as e:
                errors.append(e)

        def publish_event(event_type, event_id):
            try:
                event = AgentEvent(event_type=event_type, source_agent=f"agent_{event_id}", correlation_id=f"corr-{event_id}", data={})
                self.bus.publish(event)
                results.append(f"published_{event_id}")
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []

        # Subscribe threads
        for i in range(5):
            t = threading.Thread(target=add_subscriber, args=(f"event_{i}", i))
            threads.append(t)

        # Publish threads
        for i in range(3):
            t = threading.Thread(target=publish_event, args=(f"event_{i}", i))
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join(timeout=1.0)

        # Should have no errors (thread safety)
        assert len(errors) == 0, f"Thread safety errors: {errors}"

        # Should have results from all operations
        assert len(results) == 8  # 5 subscribes + 3 publishes

    def test_mesh_integration_setup(self):
        """Test mesh integration setup."""
        # Initially no mesh integration
        assert self.bus._capability_registry is None
        assert self.bus._mesh_observer is None
        assert self.bus.enable_mesh == False

        # Set up mesh integration
        mock_registry = MagicMock()
        mock_observer = MagicMock()

        self.bus.set_mesh_integration(mock_registry, mock_observer)

        assert self.bus._capability_registry == mock_registry
        assert self.bus._mesh_observer == mock_observer
        assert self.bus.enable_mesh == True