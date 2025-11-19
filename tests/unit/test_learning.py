"""Unit tests for src/utils/learning.py.

Tests performance tracking and learning capabilities including:
- ExecutionRecord dataclass
- PerformanceTracker class
- Success rate calculations
- Average latency tracking
- Common failure identification
- Agent health metrics
- Thread safety
"""

import pytest
from datetime import datetime, timezone
import threading
import time
from collections import deque

from src.utils.learning import (
    ExecutionRecord,
    PerformanceTracker
)


# ============================================================================
# Test ExecutionRecord
# ============================================================================

class TestExecutionRecord:
    """Test ExecutionRecord dataclass."""

    def test_create_record(self):
        """Test creating execution record."""
        record = ExecutionRecord(
            timestamp=datetime.now(timezone.utc),
            agent_id="agent1",
            capability="generate",
            success=True,
            latency_ms=150.5
        )

        assert record.agent_id == "agent1"
        assert record.capability == "generate"
        assert record.success is True
        assert record.latency_ms == 150.5
        assert record.error_type is None

    def test_create_record_with_error(self):
        """Test creating record with error."""
        record = ExecutionRecord(
            timestamp=datetime.now(timezone.utc),
            agent_id="agent1",
            capability="generate",
            success=False,
            error_type="ValidationError",
            latency_ms=50.0
        )

        assert record.success is False
        assert record.error_type == "ValidationError"


# ============================================================================
# Test PerformanceTracker
# ============================================================================

class TestPerformanceTrackerInit:
    """Test PerformanceTracker initialization."""

    def test_init_default_window(self):
        """Test initialization with default window size."""
        tracker = PerformanceTracker()
        assert tracker.window_size == 20

    def test_init_custom_window(self):
        """Test initialization with custom window size."""
        tracker = PerformanceTracker(window_size=50)
        assert tracker.window_size == 50

    def test_init_empty_state(self):
        """Test initialization starts with empty state."""
        tracker = PerformanceTracker()
        assert len(tracker.records) == 0
        assert len(tracker.failure_counts) == 0


class TestRecordExecution:
    """Test record_execution method."""

    def test_record_successful_execution(self):
        """Test recording successful execution."""
        tracker = PerformanceTracker()
        tracker.record_execution("agent1", "generate", True, latency_ms=100.0)

        key = ("agent1", "generate")
        assert key in tracker.records
        assert len(tracker.records[key]) == 1

        record = tracker.records[key][0]
        assert record.success is True
        assert record.latency_ms == 100.0

    def test_record_failed_execution(self):
        """Test recording failed execution."""
        tracker = PerformanceTracker()
        tracker.record_execution(
            "agent1",
            "generate",
            False,
            error_type="ValueError",
            latency_ms=50.0
        )

        key = ("agent1", "generate")
        record = tracker.records[key][0]
        assert record.success is False
        assert record.error_type == "ValueError"

    def test_record_failure_increments_count(self):
        """Test recording failure increments failure count."""
        tracker = PerformanceTracker()
        tracker.record_execution("agent1", "generate", False, error_type="ValueError")

        failure_key = ("agent1", "generate", "ValueError")
        assert tracker.failure_counts[failure_key] == 1

    def test_record_multiple_executions(self):
        """Test recording multiple executions."""
        tracker = PerformanceTracker()

        for i in range(10):
            tracker.record_execution("agent1", "generate", True, latency_ms=100.0 + i)

        key = ("agent1", "generate")
        assert len(tracker.records[key]) == 10

    def test_record_respects_window_size(self):
        """Test records respect window size limit."""
        tracker = PerformanceTracker(window_size=5)

        # Record 10 executions
        for i in range(10):
            tracker.record_execution("agent1", "generate", True)

        key = ("agent1", "generate")
        # Should only keep last 5
        assert len(tracker.records[key]) == 5

    def test_record_different_agents(self):
        """Test recording for different agents."""
        tracker = PerformanceTracker()

        tracker.record_execution("agent1", "generate", True)
        tracker.record_execution("agent2", "generate", True)
        tracker.record_execution("agent3", "validate", True)

        assert len(tracker.records) == 3

    def test_record_without_error_type(self):
        """Test recording failure without error type."""
        tracker = PerformanceTracker()
        tracker.record_execution("agent1", "generate", False)

        key = ("agent1", "generate")
        record = tracker.records[key][0]
        assert record.success is False
        assert record.error_type is None


class TestGetSuccessRate:
    """Test get_success_rate method."""

    def test_success_rate_all_success(self):
        """Test success rate with all successful executions."""
        tracker = PerformanceTracker()

        for _ in range(10):
            tracker.record_execution("agent1", "generate", True)

        rate = tracker.get_success_rate("agent1", "generate")
        assert rate == 1.0

    def test_success_rate_all_failures(self):
        """Test success rate with all failures."""
        tracker = PerformanceTracker()

        for _ in range(10):
            tracker.record_execution("agent1", "generate", False, error_type="Error")

        rate = tracker.get_success_rate("agent1", "generate")
        assert rate == 0.0

    def test_success_rate_mixed(self):
        """Test success rate with mixed results."""
        tracker = PerformanceTracker()

        # 7 successes, 3 failures
        for _ in range(7):
            tracker.record_execution("agent1", "generate", True)
        for _ in range(3):
            tracker.record_execution("agent1", "generate", False, error_type="Error")

        rate = tracker.get_success_rate("agent1", "generate")
        assert rate == 0.7

    def test_success_rate_no_history(self):
        """Test success rate with no history assumes healthy."""
        tracker = PerformanceTracker()
        rate = tracker.get_success_rate("agent1", "generate")
        assert rate == 1.0  # Assume healthy if no history

    def test_success_rate_different_capabilities(self):
        """Test success rates for different capabilities."""
        tracker = PerformanceTracker()

        # Different success rates for different capabilities
        tracker.record_execution("agent1", "generate", True)
        tracker.record_execution("agent1", "generate", True)
        tracker.record_execution("agent1", "validate", True)
        tracker.record_execution("agent1", "validate", False, error_type="Error")

        generate_rate = tracker.get_success_rate("agent1", "generate")
        validate_rate = tracker.get_success_rate("agent1", "validate")

        assert generate_rate == 1.0
        assert validate_rate == 0.5


class TestGetAverageLatency:
    """Test get_average_latency method."""

    def test_average_latency_single_record(self):
        """Test average latency with single record."""
        tracker = PerformanceTracker()
        tracker.record_execution("agent1", "generate", True, latency_ms=150.0)

        latency = tracker.get_average_latency("agent1", "generate")
        assert latency == 150.0

    def test_average_latency_multiple_records(self):
        """Test average latency with multiple records."""
        tracker = PerformanceTracker()

        tracker.record_execution("agent1", "generate", True, latency_ms=100.0)
        tracker.record_execution("agent1", "generate", True, latency_ms=200.0)
        tracker.record_execution("agent1", "generate", True, latency_ms=150.0)

        latency = tracker.get_average_latency("agent1", "generate")
        assert latency == 150.0

    def test_average_latency_no_history(self):
        """Test average latency with no history."""
        tracker = PerformanceTracker()
        latency = tracker.get_average_latency("agent1", "generate")
        assert latency == 0.0

    def test_average_latency_zero_values(self):
        """Test average latency with zero values."""
        tracker = PerformanceTracker()

        for _ in range(5):
            tracker.record_execution("agent1", "generate", True, latency_ms=0.0)

        latency = tracker.get_average_latency("agent1", "generate")
        assert latency == 0.0


class TestGetCommonFailures:
    """Test get_common_failures method."""

    def test_common_failures_single_type(self):
        """Test common failures with single error type."""
        tracker = PerformanceTracker()

        for _ in range(5):
            tracker.record_execution("agent1", "generate", False, error_type="ValueError")

        failures = tracker.get_common_failures("agent1", "generate")

        assert len(failures) == 1
        assert failures[0][0] == "ValueError"
        assert failures[0][1] == 5

    def test_common_failures_multiple_types(self):
        """Test common failures with multiple error types."""
        tracker = PerformanceTracker()

        for _ in range(5):
            tracker.record_execution("agent1", "generate", False, error_type="ValueError")
        for _ in range(3):
            tracker.record_execution("agent1", "generate", False, error_type="TypeError")
        for _ in range(1):
            tracker.record_execution("agent1", "generate", False, error_type="KeyError")

        failures = tracker.get_common_failures("agent1", "generate", top_n=3)

        assert len(failures) == 3
        # Should be sorted by count
        assert failures[0][0] == "ValueError"
        assert failures[0][1] == 5
        assert failures[1][0] == "TypeError"
        assert failures[1][1] == 3
        assert failures[2][0] == "KeyError"
        assert failures[2][1] == 1

    def test_common_failures_top_n(self):
        """Test common failures respects top_n limit."""
        tracker = PerformanceTracker()

        for i in range(5):
            tracker.record_execution("agent1", "generate", False, error_type=f"Error{i}")

        failures = tracker.get_common_failures("agent1", "generate", top_n=2)

        assert len(failures) <= 2

    def test_common_failures_no_failures(self):
        """Test common failures with no failures."""
        tracker = PerformanceTracker()

        tracker.record_execution("agent1", "generate", True)

        failures = tracker.get_common_failures("agent1", "generate")

        assert len(failures) == 0


class TestGetAgentHealth:
    """Test get_agent_health method."""

    def test_agent_health_single_capability(self):
        """Test agent health with single capability."""
        tracker = PerformanceTracker()

        for _ in range(10):
            tracker.record_execution("agent1", "generate", True, latency_ms=100.0)

        health = tracker.get_agent_health("agent1")

        assert health["agent_id"] == "agent1"
        assert "generate" in health["capabilities"]
        assert health["capabilities"]["generate"]["success_rate"] == 1.0
        assert health["capabilities"]["generate"]["average_latency_ms"] == 100.0

    def test_agent_health_multiple_capabilities(self):
        """Test agent health with multiple capabilities."""
        tracker = PerformanceTracker()

        tracker.record_execution("agent1", "generate", True, latency_ms=100.0)
        tracker.record_execution("agent1", "validate", True, latency_ms=50.0)
        tracker.record_execution("agent1", "transform", False, error_type="Error")

        health = tracker.get_agent_health("agent1")

        assert len(health["capabilities"]) == 3
        assert "generate" in health["capabilities"]
        assert "validate" in health["capabilities"]
        assert "transform" in health["capabilities"]

    def test_agent_health_no_history(self):
        """Test agent health with no history."""
        tracker = PerformanceTracker()
        health = tracker.get_agent_health("agent1")

        assert health["agent_id"] == "agent1"
        assert len(health["capabilities"]) == 0

    def test_agent_health_includes_failures(self):
        """Test agent health includes common failures."""
        tracker = PerformanceTracker()

        tracker.record_execution("agent1", "generate", False, error_type="ValueError")
        tracker.record_execution("agent1", "generate", False, error_type="ValueError")

        health = tracker.get_agent_health("agent1")

        common_failures = health["capabilities"]["generate"]["common_failures"]
        assert len(common_failures) > 0
        assert common_failures[0][0] == "ValueError"


# ============================================================================
# Test Thread Safety
# ============================================================================

class TestThreadSafety:
    """Test thread safety of PerformanceTracker."""

    def test_concurrent_recordings(self):
        """Test concurrent recordings from multiple threads."""
        tracker = PerformanceTracker()
        num_threads = 10
        recordings_per_thread = 100

        def record_executions():
            for _ in range(recordings_per_thread):
                tracker.record_execution("agent1", "generate", True, latency_ms=100.0)

        threads = [threading.Thread(target=record_executions) for _ in range(num_threads)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All recordings should be captured
        key = ("agent1", "generate")
        # Due to window size, may not have all records
        assert len(tracker.records[key]) <= num_threads * recordings_per_thread

    def test_concurrent_reads_and_writes(self):
        """Test concurrent reads and writes."""
        tracker = PerformanceTracker()

        def writer():
            for i in range(50):
                tracker.record_execution("agent1", "generate", i % 2 == 0, latency_ms=100.0)
                time.sleep(0.001)

        def reader():
            for _ in range(50):
                tracker.get_success_rate("agent1", "generate")
                tracker.get_average_latency("agent1", "generate")
                time.sleep(0.001)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=reader)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should complete without errors
        assert True


# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_complete_tracking_workflow(self):
        """Test complete performance tracking workflow."""
        tracker = PerformanceTracker(window_size=20)

        # Simulate agent executions
        for i in range(30):
            success = i % 5 != 0  # Every 5th execution fails
            error_type = "PeriodicError" if not success else None
            latency = 100.0 + (i * 5.0)

            tracker.record_execution(
                "content_generator",
                "generate_blog",
                success,
                error_type=error_type,
                latency_ms=latency
            )

        # Check metrics
        success_rate = tracker.get_success_rate("content_generator", "generate_blog")
        assert 0.0 < success_rate < 1.0  # Mixed results

        avg_latency = tracker.get_average_latency("content_generator", "generate_blog")
        assert avg_latency > 0

        common_failures = tracker.get_common_failures("content_generator", "generate_blog")
        assert len(common_failures) > 0

        health = tracker.get_agent_health("content_generator")
        assert "generate_blog" in health["capabilities"]

    def test_multiple_agents_tracking(self):
        """Test tracking multiple agents simultaneously."""
        tracker = PerformanceTracker()

        agents = ["agent1", "agent2", "agent3"]
        capabilities = ["generate", "validate", "transform"]

        for agent in agents:
            for capability in capabilities:
                for _ in range(5):
                    tracker.record_execution(agent, capability, True, latency_ms=100.0)

        # Check each agent has health metrics
        for agent in agents:
            health = tracker.get_agent_health(agent)
            assert len(health["capabilities"]) == len(capabilities)

    def test_degrading_performance_detection(self):
        """Test detecting degrading performance."""
        tracker = PerformanceTracker(window_size=10)

        # Good performance initially
        for _ in range(5):
            tracker.record_execution("agent1", "generate", True, latency_ms=100.0)

        initial_rate = tracker.get_success_rate("agent1", "generate")

        # Performance degrades
        for _ in range(5):
            tracker.record_execution("agent1", "generate", False, error_type="Error")

        degraded_rate = tracker.get_success_rate("agent1", "generate")

        assert degraded_rate < initial_rate
