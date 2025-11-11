"""Simple LRU Cache implementation."""

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Optional
import time

@dataclass
class CacheEntry:
    """Cache entry with value and metadata."""
    value: Any
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class LRUCache:
    """Simple Least Recently Used (LRU) cache."""
    
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.cache = OrderedDict()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from cache."""
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, value: Any) -> None:
        """Put value in cache."""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = CacheEntry(value=value)
        if len(self.cache) > self.capacity:
            # Remove least recently used
            self.cache.popitem(last=False)
    
    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()
    
    def __len__(self) -> int:
        return len(self.cache)
