"""Thread-safe LRU caching with TTL and memory limits for expensive operations."""
from functools import wraps
from collections import OrderedDict
import time
import threading
import hashlib
import pickle
import sys
from typing import Any, Callable, Optional, Tuple

class LRUCache:
    """Thread-safe LRU cache with TTL and memory management."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600, max_memory_mb: int = 500):
        """Initialize cache with size and memory limits.
        
        Args:
            max_size: Maximum number of entries
            ttl: Time-to-live in seconds
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.ttl = ttl
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: OrderedDict[str, Tuple[Any, float, int]] = OrderedDict()
        self.lock = threading.RLock()
        self.current_memory = 0
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def _get_size(self, value: Any) -> int:
        """Estimate memory size of value."""
        try:
            return sys.getsizeof(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))
        except Exception:
            return sys.getsizeof(value)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            value, timestamp, size = self.cache[key]
            
            # Check TTL
            if time.time() - timestamp > self.ttl:
                self._evict_entry(key)
                self.misses += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return value
    
    def set(self, key: str, value: Any) -> None:
        """Store value in cache with memory management.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self.lock:
            value_size = self._get_size(value)
            
            # Check if value is too large
            if value_size > self.max_memory_bytes:
                return
            
            # Remove old entry if exists
            if key in self.cache:
                self._evict_entry(key)
            
            # Evict entries if memory limit would be exceeded
            while (self.current_memory + value_size > self.max_memory_bytes and 
                   len(self.cache) > 0):
                oldest_key = next(iter(self.cache))
                self._evict_entry(oldest_key)
            
            # Evict entries if size limit exceeded
            while len(self.cache) >= self.max_size:
                oldest_key = next(iter(self.cache))
                self._evict_entry(oldest_key)
            
            # Add new entry
            self.cache[key] = (value, time.time(), value_size)
            self.current_memory += value_size
    
    def _evict_entry(self, key: str) -> None:
        """Remove entry from cache.
        
        Args:
            key: Key to evict
        """
        if key in self.cache:
            _, _, size = self.cache[key]
            del self.cache[key]
            self.current_memory -= size
            self.evictions += 1
    
    def clear(self) -> None:
        """Clear all entries from cache."""
        with self.lock:
            self.cache.clear()
            self.current_memory = 0
    
    def stats(self) -> dict:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0
            return {
                'size': len(self.cache),
                'memory_mb': self.current_memory / (1024 * 1024),
                'hits': self.hits,
                'misses': self.misses,
                'evictions': self.evictions,
                'hit_rate': hit_rate
            }


def cached(ttl: int = 3600, max_size: int = 1000, max_memory_mb: int = 500):
    """Decorator to cache function results with memory limits.
    
    Args:
        ttl: Time-to-live in seconds (default: 1 hour)
        max_size: Maximum cache entries (default: 1000)
        max_memory_mb: Maximum memory in MB (default: 500MB)
        
    Returns:
        Decorated function with caching
    """
    cache = LRUCache(max_size=max_size, ttl=ttl, max_memory_mb=max_memory_mb)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key using hash for stability
            key_parts = [func.__name__]
            
            # Hash args
            for arg in args:
                try:
                    if isinstance(arg, (str, int, float, bool, type(None))):
                        key_parts.append(str(arg))
                    else:
                        key_parts.append(hashlib.md5(
                            pickle.dumps(arg, protocol=pickle.HIGHEST_PROTOCOL)
                        ).hexdigest())
                except Exception:
                    key_parts.append(str(arg))
            
            # Hash kwargs
            for k, v in sorted(kwargs.items()):
                try:
                    if isinstance(v, (str, int, float, bool, type(None))):
                        key_parts.append(f"{k}={v}")
                    else:
                        key_parts.append(f"{k}={hashlib.md5(
                            pickle.dumps(v, protocol=pickle.HIGHEST_PROTOCOL)
                        ).hexdigest()}")
                except Exception:
                    key_parts.append(f"{k}={v}")
            
            key = ":".join(key_parts)
            
            # Check cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        
        # Attach cache for inspection
        wrapper.cache = cache
        return wrapper
    
    return decorator
