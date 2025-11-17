"""Unified Event Bus

Combines EventBus from v5_1 with optional mesh-aware hooks.
"""

import logging
import threading
from typing import Dict, List, Callable, Any, Optional
from collections import defaultdict

from .contracts import AgentEvent

logger = logging.getLogger(__name__)


class EventBus:
    """Thread-safe event bus for agent communication."""

    def __init__(self, enable_mesh: bool = False):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.RLock()
        self._event_history: List[AgentEvent] = []
        self._max_history = 1000
        self.enable_mesh = enable_mesh

        # Optional mesh integration
        self._capability_registry = None
        self._mesh_observer = None

    def subscribe(self, event_type: str, callback: Callable[[AgentEvent], Any]):
        with self._lock:
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[AgentEvent], Any]):
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def publish(self, event: AgentEvent):
        """Publish an event to all subscribers with full error handling."""
        with self._lock:
            # Add to history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
            
            # Get subscribers
            subscribers = self._subscribers.get(event.event_type, [])
            
            if not subscribers:
                logger.debug(f"No subscribers for {event.event_type}")
                return
            
            logger.debug(f"Publishing {event.event_type} to {len(subscribers)} subscribers")
        
        # Call subscribers (outside lock to prevent deadlock)
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event.event_type}: {e}")
                # Continue with other subscribers - don't break the chain
                continue
                
    def get_history(self, event_type: Optional[str] = None, limit: int = 100):
        with self._lock:
            if event_type:
                events = [e for e in self._event_history if e.event_type == event_type]
            else:
                events = list(self._event_history)
            return events[-limit:]

    def clear_history(self):
        with self._lock:
            self._event_history.clear()

    def set_mesh_integration(self, capability_registry, mesh_observer):
        self._capability_registry = capability_registry
        self._mesh_observer = mesh_observer
        self.enable_mesh = True
        logger.info("Mesh integration enabled")

    def get_subscriber_count(self, event_type: str) -> int:
        with self._lock:
            return len(self._subscribers.get(event_type, []))


__all__ = ['EventBus']
# DOCGEN:LLM-FIRST@v4