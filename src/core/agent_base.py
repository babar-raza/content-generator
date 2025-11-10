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

    def __init__(self, agent_id: str, config, event_bus: EventBus, enable_mesh: bool = False,
                 tone_config: Optional[Dict[str, Any]] = None,
                 perf_config: Optional[Dict[str, Any]] = None,
                 agent_config: Optional[Dict[str, Any]] = None):
        self.agent_id = agent_id
        self.config = config
        self.event_bus = event_bus
        self.enable_mesh = enable_mesh
        
        # Configuration support
        self.tone_config = tone_config or {}
        self.perf_config = perf_config or {}
        self.agent_config = agent_config or {}

        # Stats
        self.executions = 0
        self.failures = 0
        self.total_time = 0.0

        # Mesh features (optional)
        self._capability_registry = None
        self._current_load = 0
        self._max_capacity = self.perf_config.get('limits', {}).get('max_parallel', 3)

        # Contract & subscriptions
        self.contract = self._create_contract()
        self._subscribe_to_events()

        logger.info("Initialized %s (mesh=%s, tone=%s, perf=%s)", 
                   agent_id, enable_mesh, bool(tone_config), bool(perf_config))

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
    
    def get_timeout(self, timeout_type: str = 'agent_execution') -> float:
        """Get timeout value from perf_config."""
        return self.perf_config.get('timeouts', {}).get(timeout_type, 30.0)
    
    def get_limit(self, limit_type: str) -> int:
        """Get limit value from perf_config."""
        limits = self.perf_config.get('limits', {})
        return limits.get(limit_type, {
            'max_tokens_per_agent': 4000,
            'max_steps': 50,
            'max_retries': 3,
            'max_context_size': 16000
        }.get(limit_type, 0))
    
    def get_tone_setting(self, section: str, setting: str, default: Any = None) -> Any:
        """Get tone configuration setting for a specific section."""
        section_controls = self.tone_config.get('section_controls', {})
        section_config = section_controls.get(section, {})
        return section_config.get(setting, default)
    
    def is_section_enabled(self, section: str) -> bool:
        """Check if a section is enabled in tone config."""
        return self.get_tone_setting(section, 'enabled', True)


class SelfCorrectingAgent:
    """Mixin for self-correcting agents (from v5_1)."""
    def self_correct(self, result: Dict[str, Any], prompt: str, llm_service, max_attempts: int = 3) -> Dict[str, Any]:
        for _ in range(max_attempts):
            # Placeholder for validator + correction prompts
            return result
        return result


__all__ = ['Agent', 'SelfCorrectingAgent']
