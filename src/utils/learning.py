"""Self-learning capabilities and performance tracking for agents.

Implements PerformanceTracker, SelfCorrectingAgent mixin, and help request broker."""

from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from datetime import datetime
import logging
from dataclasses import dataclass, field
from src.core.contracts import AgentEvent
from src.core.config import Config, FAILURE_STRATEGIES

logger = logging.getLogger(__name__)

@dataclass
class ExecutionRecord:
    """Record of an agent execution."""
    timestamp: datetime
    agent_id: str
    capability: str
    success: bool
    error_type: Optional[str] = None
    latency_ms: float = 0.0

class PerformanceTracker:
    """Tracks agent performance and identifies failure patterns."""

    def __init__(self, window_size: int = 20):
        """Initialize performance tracker.

        Args:
            window_size: Size of rolling window for metrics"""
        self.window_size = window_size
        self.records: Dict[Tuple[str, str], deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self.failure_counts: Dict[Tuple[str, str, str], int] = defaultdict(int)

    def record_execution(
        self,
        agent_id: str,
        capability: str,
        success: bool,
        error_type: Optional[str] = None,
        latency_ms: float = 0.0
    ):
        """Record an execution result.

        Args:
            agent_id: ID of the agent
            capability: Capability being executed
            success: Whether execution was successful
            error_type: Type of error if failed
            latency_ms: Execution latency in milliseconds"""
        key = (agent_id, capability)
        record = ExecutionRecord(
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            capability=capability,
            success=success,
            error_type=error_type,
            latency_ms=latency_ms
        )

        self.records[key].append(record)

        if not success and error_type:
            failure_key = (agent_id, capability, error_type)
            self.failure_counts[failure_key] += 1

        logger.debug(
            f"Recorded execution: {agent_id}/{capability} "
            f"success={success} error={error_type}"
        )

    def get_success_rate(self, agent_id: str, capability: str) -> float:
        """Get success rate for an agent/capability pair.

        Args:
            agent_id: ID of the agent
            capability: Capability to check

        Returns:
            Success rate (0.0 to 1.0)"""
        key = (agent_id, capability)
        records = self.records.get(key, [])

        if not records:
            return 1.0  # Assume healthy if no history

        successes = sum(1 for r in records if r.success)
        return successes / len(records)

    def get_average_latency(self, agent_id: str, capability: str) -> float:
        """Get average latency for an agent/capability pair.

        Args:
            agent_id: ID of the agent
            capability: Capability to check

        Returns:
            Average latency in milliseconds"""
        key = (agent_id, capability)
        records = self.records.get(key, [])

        if not records:
            return 0.0

        total_latency = sum(r.latency_ms for r in records)
        return total_latency / len(records)

    def get_common_failures(
        self,
        agent_id: str,
        capability: str,
        top_n: int = 3
    ) -> List[Tuple[str, int]]:
        """Get most common failure types for an agent/capability.

        Args:
            agent_id: ID of the agent
            capability: Capability to check
            top_n: Number of top failures to return

        Returns:
            List of (error_type, count) tuples"""
        # Get all failure counts for this agent/capability
        relevant_failures = [
            (error_type, count)
            for (aid, cap, error_type), count in self.failure_counts.items()
            if aid == agent_id and cap == capability
        ]

        # Sort by count descending
        relevant_failures.sort(key=lambda x: x[1], reverse=True)

        return relevant_failures[:top_n]

    def get_agent_health(self, agent_id: str) -> Dict[str, Any]:
        """Get health metrics for an agent across all capabilities.

        Args:
            agent_id: ID of the agent

        Returns:
            Health metrics dictionary"""
        capabilities = set(
            cap for (aid, cap) in self.records.keys() if aid == agent_id
        )

        health = {
            "agent_id": agent_id,
            "capabilities": {}
        }

        for capability in capabilities:
            health["capabilities"][capability] = {
                "success_rate": self.get_success_rate(agent_id, capability),
                "average_latency_ms": self.get_average_latency(agent_id, capability),
                "common_failures": self.get_common_failures(agent_id, capability)
            }

        return health

class SelfCorrectingAgent:
    """Mixin for agents with self-correction capabilities."""

    def __init__(self, *args, **kwargs):
        """Initialize self-correcting agent."""
        super().__init__(*args, **kwargs)
        self.performance_tracker: Optional[PerformanceTracker] = None
        self.retry_count = 0
        self.max_retries = 3

    def set_performance_tracker(self, tracker: PerformanceTracker):
        """Set performance tracker.

        Args:
            tracker: PerformanceTracker instance"""
        self.performance_tracker = tracker

    def execute_with_learning(
        self,
        event: AgentEvent,
        capability: str
    ) -> Optional[AgentEvent]:
        """Execute with self-learning and error recovery.

        Args:
            event: Triggering event
            capability: Capability being executed

        Returns:
            Result event or None"""
        start_time = datetime.utcnow()

        try:
            # Try primary execution
            result = self.execute(event)

            # Record success
            if self.performance_tracker:
                latency = (datetime.utcnow() - start_time).total_seconds() * 1000
                self.performance_tracker.record_execution(
                    agent_id=self.agent_id,
                    capability=capability,
                    success=True,
                    latency_ms=latency
                )

            return result

        except Exception as e:
            error_type = type(e).__name__

            # Record failure
            if self.performance_tracker:
                latency = (datetime.utcnow() - start_time).total_seconds() * 1000
                self.performance_tracker.record_execution(
                    agent_id=self.agent_id,
                    capability=capability,
                    success=False,
                    error_type=error_type,
                    latency_ms=latency
                )

            logger.error(
                f"Execution failed for {self.agent_id}/{capability}: {e}"
            )

            # Get common failures for this capability
            if self.performance_tracker:
                common_failures = self.performance_tracker.get_common_failures(
                    self.agent_id, capability
                )
                common_error_types = [f[0] for f in common_failures]

                # If this is a known error type, try alternative strategy
                if error_type in common_error_types:
                    logger.info(
                        f"Attempting alternative strategy for {error_type}"
                    )
                    result = self._try_alternative_strategies(
                        event, capability, error_type
                    )
                    if result:
                        return result

            # If still failing or unknown error, emit help request
            if self.retry_count < self.max_retries:
                self.retry_count += 1
                return self._emit_help_request(event, capability, error_type)

            # Max retries exceeded
            logger.error(
                f"Max retries exceeded for {self.agent_id}/{capability}"
            )
            raise

    def _try_alternative_strategies(
        self,
        event: AgentEvent,
        capability: str,
        error_type: str
    ) -> Optional[AgentEvent]:
        """Try alternative strategies for known failures.

        Args:
            event: Triggering event
            capability: Capability being executed
            error_type: Type of error that occurred

        Returns:
            Result event or None"""
        strategies = FAILURE_STRATEGIES.get(error_type, [])

        for strategy in strategies:
            action = strategy["action"]
            params = strategy["params"]

            logger.info(
                f"Trying alternative strategy: {action} for {error_type}"
            )

            try:
                result = self._apply_strategy(event, action, params)
                if result:
                    logger.info(f"Alternative strategy succeeded: {action}")
                    return result
            except Exception as e:
                logger.warning(f"Alternative strategy {action} failed: {e}")
                continue

        return None

    def _apply_strategy(
        self,
        event: AgentEvent,
        action: str,
        params: Dict[str, Any]
    ) -> Optional[AgentEvent]:
        """Apply a specific recovery strategy.

        Args:
            event: Triggering event
            action: Strategy action to apply
            params: Strategy parameters

        Returns:
            Result event or None"""
        if action == "increase_timeout":
            # Implement timeout increase logic
            # This would be handled by the LLMService
            return self.execute(event)

        elif action == "switch_provider":
            # Emit model selection request
            self.publish_event(
                "model_selection_request",
                {
                    "capability": self.contract.capabilities[0],
                    "context": event.data,
                    "preferred_provider": params.get("priority", [])[0]
                },
                event.correlation_id
            )
            return None

        elif action == "reduce_context":
            # Reduce context size
            modified_event = self._reduce_event_context(event, params["reduction"])
            return self.execute(modified_event)

        elif action == "enforce_json_mode":
            # This would be handled by LLMService
            return self.execute(event)

        elif action == "simplify_schema":
            # This would be handled by LLMService
            return self.execute(event)

        elif action == "exponential_backoff":
            # Handled by resilience layer
            return self.execute(event)

        elif action == "clarify_prompt":
            # Modify prompt for clarity
            return self.execute(event)

        elif action == "use_alternate_agent":
            # Request alternate agent via planner
            self.publish_event(
                "help_request",
                {
                    "agent_id": self.agent_id,
                    "required_capabilities": self.contract.capabilities,
                    "reason": "requesting_alternate_agent"
                },
                event.correlation_id
            )
            return None

        return None

    def _reduce_event_context(
        self,
        event: AgentEvent,
        reduction_factor: float
    ) -> AgentEvent:
        """Reduce context size in event data.

        Args:
            event: Original event
            reduction_factor: Factor to reduce by (0.0 to 1.0)

        Returns:
            Modified event with reduced context"""
        # Create a copy of event data
        modified_data = event.data.copy()

        # Reduce context fields
        for key in ['context', 'rag_context', 'kb_article_content']:
            if key in modified_data and isinstance(modified_data[key], str):
                original_length = len(modified_data[key])
                new_length = int(original_length * reduction_factor)
                modified_data[key] = modified_data[key][:new_length]
            elif key in modified_data and isinstance(modified_data[key], list):
                original_length = len(modified_data[key])
                new_length = int(original_length * reduction_factor)
                modified_data[key] = modified_data[key][:new_length]

        return AgentEvent(
            event_type=event.event_type,
            data=modified_data,
            source_agent=event.source_agent,
            correlation_id=event.correlation_id,
            metadata=event.metadata
        )

    def _emit_help_request(
        self,
        event: AgentEvent,
        capability: str,
        error_type: str
    ) -> None:
        """Emit help request event.

        Args:
            event: Original event
            capability: Capability that failed
            error_type: Type of error"""
        # Redact sensitive data
        redacted_data = self._redact_data(event.data)

        self.publish_event(
            "help_request",
            {
                "agent_id": self.agent_id,
                "required_capabilities": [capability],
                "error_type": error_type,
                "original_event_type": event.event_type,
                "redacted_data": redacted_data
            },
            event.correlation_id
        )

        return None

    def _redact_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive information from data.

        Args:
            data: Original data

        Returns:
            Redacted data"""
        redacted = {}

        for key, value in data.items():
            if isinstance(value, str) and len(value) > 200:
                # Truncate long strings
                redacted[key] = value[:200] + "...[truncated]"
            else:
                redacted[key] = value

        return redacted

# Unit tests
if __name__ == "__main__":
    import unittest

    class TestPerformanceTracker(unittest.TestCase):
        """Test PerformanceTracker functionality."""

        def setUp(self):
            """Set up test fixtures."""
            self.tracker = PerformanceTracker(window_size=5)

        def test_success_rate_calculation(self):
            """Test success rate calculation."""
            # Record some executions
            for i in range(5):
                success = i < 3  # 3 successes, 2 failures
                self.tracker.record_execution(
                    "test_agent",
                    "test_capability",
                    success,
                    None if success else "TestError"
                )

            success_rate = self.tracker.get_success_rate(
                "test_agent", "test_capability"
            )
            self.assertAlmostEqual(success_rate, 0.6)

        def test_common_failures(self):
            """Test common failure identification."""
            # Record failures
            for _ in range(3):
                self.tracker.record_execution(
                    "test_agent", "test_capability", False, "TimeoutError"
                )
            for _ in range(2):
                self.tracker.record_execution(
                    "test_agent", "test_capability", False, "JSONParseError"
                )

            common = self.tracker.get_common_failures(
                "test_agent", "test_capability", top_n=2
            )

            self.assertEqual(len(common), 2)
            self.assertEqual(common[0][0], "TimeoutError")
            self.assertEqual(common[0][1], 3)

    unittest.main()
