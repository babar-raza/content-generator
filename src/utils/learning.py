"""Self-learning capabilities and performance tracking for agents.

Implements PerformanceTracker, SelfCorrectingAgent mixin, and help request broker."""

from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from datetime import datetime
import logging
from dataclasses import dataclass, field
from src.core.contracts import AgentEvent
from src.core.config import Config, FAILURE_STRATEGIES
from src.core.agent_base import SelfCorrectingAgent

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

