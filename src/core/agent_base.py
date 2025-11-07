"""Unified Agent Base Class

Combines Agent from v5_1 with optional mesh-aware features from v5_2.
"""

import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from .contracts import AgentEvent, AgentContract
from .event_bus import EventBus

logger = logging.getLogger(__name__)


class Agent(ABC):
    """Base agent class with optional mesh capabilities."""

    def __init__(self, agent_id: str, config, event_bus: EventBus, enable_mesh: bool = False):
        self.agent_id = agent_id
        self.config = config
        self.event_bus = event_bus
        self.enable_mesh = enable_mesh

        # Stats
        self.executions = 0
        self.failures = 0
        self.total_time = 0.0

        # Mesh features (optional)
        self._capability_registry = None
        self._current_load = 0
        self._max_capacity = 3

        # Contract & subscriptions
        self.contract = self._create_contract()
        self._subscribe_to_events()

        logger.info("Initialized %s (mesh=%s)", agent_id, enable_mesh)

    @abstractmethod
    def _create_contract(self) -> AgentContract:
        ...

    @abstractmethod
    def _subscribe_to_events(self):
        ...

    @abstractmethod
    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:
        ...

    def _track_execution(self, success: bool, duration: float):
        self.executions += 1
        if not success:
            self.failures += 1
        self.total_time += duration

    def get_stats(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "executions": self.executions,
            "failures": self.failures,
            "success_rate": 1.0 - (self.failures / max(self.executions, 1)),
            "avg_time": self.total_time / max(self.executions, 1),
            "total_time": self.total_time,
        }

    def register_with_mesh(self, capability_registry):
        if self.enable_mesh:
            self._capability_registry = capability_registry
            # Expecting registry.register_agent(agent_id, self, self.contract)
            try:
                capability_registry.register_agent(self.agent_id, self, self.contract)  # type: ignore[attr-defined]
                logger.info("%s registered with mesh", self.agent_id)
            except Exception as e:
                logger.warning("Mesh registration failed for %s: %s", self.agent_id, e)

    def increment_load(self):
        if self.enable_mesh:
            self._current_load += 1

    def decrement_load(self):
        if self.enable_mesh:
            self._current_load = max(0, self._current_load - 1)

    @property
    def current_load(self) -> int:
        return self._current_load if self.enable_mesh else 0

    @property
    def max_capacity(self) -> int:
        return self._max_capacity


class SelfCorrectingAgent:
    """Mixin for self-correcting agents (from v5_1)."""
    def self_correct(self, result: Dict[str, Any], prompt: str, llm_service, max_attempts: int = 3) -> Dict[str, Any]:
        for _ in range(max_attempts):
            # Placeholder for validator + correction prompts
            return result
        return result


__all__ = ['Agent', 'SelfCorrectingAgent']
