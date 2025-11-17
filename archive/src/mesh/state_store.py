"""
Phase 4: Distributed State Store
Provides distributed state management with pub-sub for agent coordination
"""

import threading
import logging
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict, deque
import weakref
import copy

logger = logging.getLogger(__name__)


@dataclass
class StateChange:
    """Represents a state change event"""
    correlation_id: str
    key: str
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    change_type: str = "update"  # update, set, delete


class StateWatcher:
    """Wrapper for state change callbacks"""
    
    def __init__(self, callback: Callable[[StateChange], None], 
                 watcher_id: str, correlation_pattern: str = "*"):
        self.callback = callback
        self.watcher_id = watcher_id
        self.correlation_pattern = correlation_pattern
        self.active = True
        self.created_at = datetime.now()
    
    def matches_correlation(self, correlation_id: str) -> bool:
        """Check if watcher is interested in this correlation"""
        if self.correlation_pattern == "*":
            return True
        return self.correlation_pattern == correlation_id
    
    def notify(self, change: StateChange) -> None:
        """Notify watcher of change"""
        if not self.active:
            return
        
        try:
            self.callback(change)
        except Exception as e:
            logger.error(f"Error in state watcher {self.watcher_id}: {e}")
            # Deactivate problematic watchers
            self.active = False


class StateStore:
    """
    Distributed state store with pub-sub capabilities
    
    Provides:
    - Thread-safe key-value storage scoped by correlation ID
    - Pub-sub for state changes
    - Watch patterns for agents to react to state changes
    - History tracking for debugging
    """
    
    def __init__(self, max_history: int = 1000):
        # Storage: correlation_id -> key -> value
        self._data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Watchers: key -> List[StateWatcher]
        self._watchers: Dict[str, List[StateWatcher]] = defaultdict(list)
        self._global_watchers: List[StateWatcher] = []
        
        # History for debugging
        self._history: deque = deque(maxlen=max_history)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Metrics
        self._operation_count = 0
        self._watcher_count = 0
        
        logger.info("StateStore initialized")
    
    def set(self, correlation_id: str, key: str, value: Any) -> None:
        """
        Set a value in the state store
        
        Args:
            correlation_id: Workflow correlation ID
            key: State key
            value: Value to store
        """
        with self._lock:
            old_value = self._data[correlation_id].get(key)
            self._data[correlation_id][key] = copy.deepcopy(value)
            self._operation_count += 1
            
            # Create change event
            change = StateChange(
                correlation_id=correlation_id,
                key=key,
                old_value=old_value,
                new_value=value,
                change_type="set" if old_value is None else "update"
            )
            
            # Record in history
            self._history.append(change)
            
            # Notify watchers
            self._notify_watchers(change)
            
            logger.debug(f"StateStore.set: {correlation_id}.{key} = {type(value).__name__}")
    
    def get(self, correlation_id: str, key: str, default: Any = None) -> Any:
        """
        Get a value from the state store
        
        Args:
            correlation_id: Workflow correlation ID
            key: State key
            default: Default value if key doesn't exist
            
        Returns:
            Stored value or default
        """
        with self._lock:
            value = self._data.get(correlation_id, {}).get(key, default)
            # Return deep copy to prevent external modification
            return copy.deepcopy(value) if value is not None else default
    
    def has(self, correlation_id: str, key: str) -> bool:
        """
        Check if a key exists in the state store
        
        Args:
            correlation_id: Workflow correlation ID
            key: State key
            
        Returns:
            True if key exists
        """
        with self._lock:
            return key in self._data.get(correlation_id, {})
    
    def delete(self, correlation_id: str, key: str) -> bool:
        """
        Delete a key from the state store
        
        Args:
            correlation_id: Workflow correlation ID
            key: State key
            
        Returns:
            True if key was deleted, False if it didn't exist
        """
        with self._lock:
            if correlation_id not in self._data or key not in self._data[correlation_id]:
                return False
            
            old_value = self._data[correlation_id].pop(key)
            self._operation_count += 1
            
            # Create change event
            change = StateChange(
                correlation_id=correlation_id,
                key=key,
                old_value=old_value,
                new_value=None,
                change_type="delete"
            )
            
            # Record in history
            self._history.append(change)
            
            # Notify watchers
            self._notify_watchers(change)
            
            logger.debug(f"StateStore.delete: {correlation_id}.{key}")
            return True
    
    def get_all(self, correlation_id: str) -> Dict[str, Any]:
        """
        Get all state for a correlation ID
        
        Args:
            correlation_id: Workflow correlation ID
            
        Returns:
            Dictionary of all state for the correlation
        """
        with self._lock:
            return copy.deepcopy(self._data.get(correlation_id, {}))
    
    def get_all_correlations(self) -> List[str]:
        """
        Get all active correlation IDs (Phase 10: Observability)
        
        Returns:
            List of all correlation IDs with state data
        """
        with self._lock:
            return list(self._data.keys())
    
    def get_correlation_data(self, correlation_id: str) -> Dict[str, Any]:
        """
        Get comprehensive data for a correlation (Phase 10: Observability)
        
        Args:
            correlation_id: Workflow correlation ID
            
        Returns:
            Dictionary with correlation state and metadata
        """
        with self._lock:
            state_data = copy.deepcopy(self._data.get(correlation_id, {}))
            
            # Add metadata from history
            correlation_history = [
                change for change in self._history 
                if change.correlation_id == correlation_id
            ]
            
            # Calculate some useful metadata
            metadata = {
                "correlation_id": correlation_id,
                "state_keys": list(state_data.keys()),
                "state_data": state_data,
                "total_changes": len(correlation_history),
                "start_time": None,
                "last_activity": None,
                "completed_capabilities": set(),
                "required_capabilities": [],
                "events_count": 0,
                "error_count": 0,
                "last_error": None,
                "status": "in_progress"
            }
            
            if correlation_history:
                metadata["start_time"] = correlation_history[0].timestamp
                metadata["last_activity"] = correlation_history[-1].timestamp
                
                # Count events and errors
                for change in correlation_history:
                    if "event" in change.key or change.key.endswith("_complete"):
                        metadata["events_count"] += 1
                    if "error" in change.key or change.key.endswith("_failed"):
                        metadata["error_count"] += 1
                        metadata["last_error"] = str(change.new_value)
                    
                    # Track completed capabilities
                    if change.key.endswith("_complete") and change.new_value:
                        capability = change.key.replace("_complete", "")
                        metadata["completed_capabilities"].add(capability)
            
            # Infer status
            if state_data.get("workflow_complete"):
                metadata["status"] = "completed"
            elif state_data.get("workflow_failed"):
                metadata["status"] = "failed"
            elif metadata["error_count"] > 0:
                metadata["status"] = "error"
            
            # Try to extract goal/objective
            metadata["goal"] = state_data.get("goal") or state_data.get("objective") or state_data.get("task")
            
            return metadata
    
    def watch(self, key: str, callback: Callable[[StateChange], None], 
              watcher_id: str, correlation_pattern: str = "*") -> None:
        """
        Watch for changes to a specific key
        
        Args:
            key: Key to watch (or "*" for all keys)
            callback: Function to call when key changes
            watcher_id: Unique identifier for this watcher
            correlation_pattern: Correlation ID pattern to match ("*" for all)
        """
        with self._lock:
            watcher = StateWatcher(callback, watcher_id, correlation_pattern)
            
            if key == "*":
                self._global_watchers.append(watcher)
            else:
                self._watchers[key].append(watcher)
            
            self._watcher_count += 1
            
            logger.info(f"StateStore.watch: {watcher_id} watching {key} for {correlation_pattern}")
    
    def unwatch(self, key: str, watcher_id: str) -> bool:
        """
        Remove a watcher
        
        Args:
            key: Key that was being watched
            watcher_id: ID of watcher to remove
            
        Returns:
            True if watcher was found and removed
        """
        with self._lock:
            if key == "*":
                # Remove from global watchers
                for i, watcher in enumerate(self._global_watchers):
                    if watcher.watcher_id == watcher_id:
                        self._global_watchers.pop(i)
                        self._watcher_count -= 1
                        logger.info(f"StateStore.unwatch: removed global watcher {watcher_id}")
                        return True
            else:
                # Remove from key-specific watchers
                watchers = self._watchers.get(key, [])
                for i, watcher in enumerate(watchers):
                    if watcher.watcher_id == watcher_id:
                        watchers.pop(i)
                        self._watcher_count -= 1
                        logger.info(f"StateStore.unwatch: removed watcher {watcher_id} for {key}")
                        return True
            
            return False
    
    def _notify_watchers(self, change: StateChange) -> None:
        """
        Notify all relevant watchers of a state change
        
        Args:
            change: StateChange event to notify about
        """
        # Collect watchers to notify (outside of lock to prevent deadlock)
        watchers_to_notify = []
        
        # Global watchers
        for watcher in self._global_watchers:
            if watcher.active and watcher.matches_correlation(change.correlation_id):
                watchers_to_notify.append(watcher)
        
        # Key-specific watchers
        for watcher in self._watchers.get(change.key, []):
            if watcher.active and watcher.matches_correlation(change.correlation_id):
                watchers_to_notify.append(watcher)
        
        # Notify watchers outside of lock to prevent deadlock
        for watcher in watchers_to_notify:
            try:
                # Run in thread to not block
                threading.Thread(
                    target=watcher.notify,
                    args=(change,),
                    daemon=True
                ).start()
            except Exception as e:
                logger.error(f"Error starting notification thread: {e}")
    
    def cleanup_correlation(self, correlation_id: str) -> None:
        """
        Clean up all state for a correlation ID
        
        Args:
            correlation_id: Correlation ID to clean up
        """
        with self._lock:
            if correlation_id in self._data:
                del self._data[correlation_id]
                logger.info(f"StateStore.cleanup: removed all state for {correlation_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get state store statistics
        
        Returns:
            Dictionary of statistics
        """
        with self._lock:
            return {
                "correlations": len(self._data),
                "total_keys": sum(len(keys) for keys in self._data.values()),
                "operations": self._operation_count,
                "watchers": self._watcher_count,
                "history_size": len(self._history),
                "memory_usage": sum(
                    len(str(data)) for data in self._data.values()
                )
            }
    
    def get_history(self, correlation_id: Optional[str] = None, 
                   key: Optional[str] = None, limit: int = 100) -> List[StateChange]:
        """
        Get state change history
        
        Args:
            correlation_id: Filter by correlation ID (optional)
            key: Filter by key (optional)
            limit: Maximum number of changes to return
            
        Returns:
            List of StateChange objects
        """
        with self._lock:
            filtered_history = []
            
            for change in reversed(self._history):
                if correlation_id and change.correlation_id != correlation_id:
                    continue
                if key and change.key != key:
                    continue
                
                filtered_history.append(change)
                
                if len(filtered_history) >= limit:
                    break
            
            return list(reversed(filtered_history))


# Global state store instance
_global_state_store: Optional[StateStore] = None


def get_state_store() -> StateStore:
    """Get the global state store instance"""
    global _global_state_store
    if _global_state_store is None:
        _global_state_store = StateStore()
    return _global_state_store


def set_state_store(store: StateStore) -> None:
    """Set the global state store instance (for testing)"""
    global _global_state_store
    _global_state_store = store
