"""
Local Caching Layer for Agent Performance Optimization - Phase 9A

Provides LRU cache with TTL, per-correlation namespaces, and decorators for
caching deterministic operations like RAG retrieval, API lookups, and template rendering.
"""

import asyncio
import functools
import hashlib
import logging
import threading
import time
from collections import OrderedDict
from time import monotonic
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with TTL"""
    value: Any
    timestamp: float
    ttl_s: float
    access_count: int = 0
    last_access: float = field(default_factory=monotonic)
    
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        return monotonic() - self.timestamp > self.ttl_s
    
    def touch(self) -> None:
        """Update access information"""
        self.access_count += 1
        self.last_access = monotonic()


class LRUCache:
    """
    Thread-safe LRU cache with TTL support and per-correlation namespaces
    
    Features:
    - LRU eviction when maxsize reached
    - TTL-based expiration
    - Per-correlation namespacing
    - Thread-safe operations
    - Hit/miss statistics
    """
    
    def __init__(self, maxsize: int = 1000, ttl_s: float = 300.0, clock: Callable = monotonic):
        self.maxsize = maxsize
        self.default_ttl_s = ttl_s
        self.clock = clock
        
        # Storage: namespace -> key -> CacheEntry
        self._namespaces: Dict[str, OrderedDict] = {}
        self._lock = threading.RLock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.expirations = 0
        
        logger.info(f"Initialized LRUCache: maxsize={maxsize}, ttl_s={ttl_s}")
    
    def _get_namespace(self, namespace: str) -> OrderedDict:
        """Get or create namespace"""
        if namespace not in self._namespaces:
            self._namespaces[namespace] = OrderedDict()
        return self._namespaces[namespace]
    
    def _make_key(self, key: Any) -> str:
        """Convert key to string for hashing"""
        if isinstance(key, str):
            return key
        elif isinstance(key, (tuple, list)):
            return str(hash(tuple(str(k) for k in key)))
        else:
            return str(hash(str(key)))
    
    def get(self, key: Any, namespace: str = "global", default: Any = None) -> Any:
        """
        Get value from cache
        
        Args:
            key: Cache key
            namespace: Cache namespace (typically correlation_id or "global")
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        with self._lock:
            ns = self._get_namespace(namespace)
            cache_key = self._make_key(key)
            
            if cache_key in ns:
                entry = ns[cache_key]
                
                # Check if expired
                if entry.is_expired():
                    del ns[cache_key]
                    self.expirations += 1
                    self.misses += 1
                    return default
                
                # Move to end (most recently used)
                ns.move_to_end(cache_key)
                entry.touch()
                self.hits += 1
                
                logger.debug(f"Cache HIT: {namespace}:{cache_key}")
                return entry.value
            
            self.misses += 1
            logger.debug(f"Cache MISS: {namespace}:{cache_key}")
            return default
    
    def set(self, key: Any, value: Any, namespace: str = "global", 
            ttl_s: Optional[float] = None) -> None:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            namespace: Cache namespace
            ttl_s: Time to live in seconds (uses default if None)
        """
        with self._lock:
            ns = self._get_namespace(namespace)
            cache_key = self._make_key(key)
            ttl = ttl_s if ttl_s is not None else self.default_ttl_s
            
            # Create entry
            entry = CacheEntry(
                value=value,
                timestamp=self.clock(),
                ttl_s=ttl
            )
            
            # Add to cache
            ns[cache_key] = entry
            ns.move_to_end(cache_key)
            
            # Check size limits and evict if necessary
            self._evict_if_needed(ns)
            
            logger.debug(f"Cache SET: {namespace}:{cache_key} (ttl={ttl}s)")
    
    def _evict_if_needed(self, ns: OrderedDict) -> None:
        """Evict oldest entries if namespace exceeds maxsize"""
        while len(ns) > self.maxsize:
            oldest_key = next(iter(ns))
            del ns[oldest_key]
            self.evictions += 1
            logger.debug(f"Cache EVICT: {oldest_key}")
    
    def invalidate(self, key: Any, namespace: str = "global") -> bool:
        """
        Remove specific key from cache
        
        Args:
            key: Cache key to remove
            namespace: Cache namespace
            
        Returns:
            True if key was found and removed
        """
        with self._lock:
            ns = self._get_namespace(namespace)
            cache_key = self._make_key(key)
            
            if cache_key in ns:
                del ns[cache_key]
                logger.debug(f"Cache INVALIDATE: {namespace}:{cache_key}")
                return True
            
            return False
    
    def invalidate_namespace(self, namespace: str) -> int:
        """
        Remove entire namespace from cache
        
        Args:
            namespace: Namespace to clear
            
        Returns:
            Number of entries removed
        """
        with self._lock:
            if namespace in self._namespaces:
                count = len(self._namespaces[namespace])
                del self._namespaces[namespace]
                logger.info(f"Cache INVALIDATE_NAMESPACE: {namespace} ({count} entries)")
                return count
            return 0
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries
        
        Returns:
            Number of entries removed
        """
        removed = 0
        with self._lock:
            for namespace, ns in list(self._namespaces.items()):
                expired_keys = [
                    key for key, entry in ns.items()
                    if entry.is_expired()
                ]
                
                for key in expired_keys:
                    del ns[key]
                    removed += 1
                    self.expirations += 1
                
                # Remove empty namespaces
                if not ns:
                    del self._namespaces[namespace]
        
        if removed > 0:
            logger.info(f"Cache cleanup: removed {removed} expired entries")
        
        return removed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_entries = sum(len(ns) for ns in self._namespaces.values())
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
            
            return {
                "maxsize": self.maxsize,
                "total_entries": total_entries,
                "namespaces": len(self._namespaces),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "evictions": self.evictions,
                "expirations": self.expirations
            }
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._namespaces.clear()
            logger.info("Cache cleared")


# Global cache instance
_global_cache = LRUCache()


def get_cache() -> LRUCache:
    """Get the global cache instance"""
    return _global_cache


# State change tracking for cache invalidation
_state_watchers: Dict[str, Set[str]] = {}  # key -> set of cache_keys_to_invalidate
_state_watchers_lock = threading.RLock()


def _add_state_watcher(state_key: str, cache_key: str) -> None:
    """Add a state watcher for cache invalidation"""
    with _state_watchers_lock:
        if state_key not in _state_watchers:
            _state_watchers[state_key] = set()
        _state_watchers[state_key].add(cache_key)


def invalidate_on_state_change(state_keys: List[str]) -> Callable:
    """
    Decorator to invalidate cache entries when state changes
    
    Args:
        state_keys: List of state keys that, when changed, should invalidate the cache
        
    Usage:
        @invalidate_on_state_change(["context_kb", "context_blog"])
        @cached_function("outline_cache", ttl_s=300)
        def create_outline(topic, context):
            return expensive_outline_creation(topic, context)
    """
    def decorator(func: Callable) -> Callable:
        # Register state watchers for this function
        func_name = f"{func.__module__}.{func.__name__}"
        for state_key in state_keys:
            _add_state_watcher(state_key, func_name)
        
        return func
    
    return decorator


def trigger_state_change_invalidation(state_key: str, correlation_id: str) -> None:
    """
    Trigger cache invalidation for functions watching a state key
    
    Args:
        state_key: The state key that changed
        correlation_id: The correlation ID for namespace-specific invalidation
    """
    with _state_watchers_lock:
        if state_key in _state_watchers:
            cache = get_cache()
            for func_name in _state_watchers[state_key]:
                # Invalidate all cache entries that start with this function name
                # We need to iterate through all namespaces and find matching keys
                _invalidate_function_cache(cache, func_name, correlation_id)
            
            logger.debug(f"Triggered cache invalidation for state_key={state_key}, "
                        f"correlation_id={correlation_id}")


def _invalidate_function_cache(cache: LRUCache, func_name: str, correlation_id: str) -> None:
    """Invalidate all cache entries for a specific function"""
    with cache._lock:
        # Check global namespace
        if "global" in cache._namespaces:
            global_ns = cache._namespaces["global"]
            keys_to_remove = [
                key for key in global_ns.keys() 
                if key.startswith(func_name) or key.startswith(f"{func_name}_")
            ]
            for key in keys_to_remove:
                if key in global_ns:
                    del global_ns[key]
                    logger.debug(f"Invalidated global cache key: {key}")
        
        # Check correlation-specific namespace
        if correlation_id in cache._namespaces:
            corr_ns = cache._namespaces[correlation_id]
            keys_to_remove = [
                key for key in corr_ns.keys() 
                if key.startswith(func_name) or key.startswith(f"{func_name}_")
            ]
            for key in keys_to_remove:
                if key in corr_ns:
                    del corr_ns[key]
                    logger.debug(f"Invalidated correlation cache key: {key}")


def cached_function(key_func: Union[str, Callable] = None, 
                   ttl_s: float = 300.0, 
                   maxsize: int = 1000,
                   scope: str = "correlation") -> Callable:
    """
    Decorator for caching function results
    
    Args:
        key_func: Function to generate cache key, or string for simple key
        ttl_s: Time to live in seconds
        maxsize: Maximum number of entries (ignored, uses global cache maxsize)
        scope: "correlation" or "global" - determines cache namespace
        
    Usage:
        @cached_function("rag_lookup", ttl_s=600, scope="global")
        def lookup_rag(query: str) -> Dict:
            return expensive_rag_lookup(query)
        
        @cached_function(lambda topic, context: f"outline_{hash((topic, context))}", ttl_s=300)
        def create_outline(topic: str, context: str) -> Dict:
            return expensive_outline_creation(topic, context)
    """
    def decorator(func: Callable) -> Callable:
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            if callable(key_func):
                cache_key = key_func(*args, **kwargs)
            elif isinstance(key_func, str):
                # When string key is provided, append args hash to make it unique
                arg_hash = hashlib.md5(str((args, kwargs)).encode()).hexdigest()[:8]
                cache_key = f"{key_func}_{arg_hash}"
            else:
                # Default: use function name and hash of args
                arg_hash = hashlib.md5(str((args, kwargs)).encode()).hexdigest()[:8]
                cache_key = f"{func.__name__}_{arg_hash}"
            
            # Determine namespace
            namespace = "global"
            if scope == "correlation":
                # Try to extract correlation_id from args/kwargs
                correlation_id = kwargs.get("correlation_id")
                if not correlation_id and args:
                    # Common pattern: correlation_id is second argument
                    if len(args) > 1 and isinstance(args[1], str):
                        correlation_id = args[1]
                
                if correlation_id:
                    namespace = correlation_id
            
            # Try to get from cache
            result = cache.get(cache_key, namespace)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                return result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func.__name__}: {cache_key}, executing...")
            result = func(*args, **kwargs)
            cache.set(cache_key, result, namespace, ttl_s)
            
            return result
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key (same logic as sync)
            if callable(key_func):
                cache_key = key_func(*args, **kwargs)
            elif isinstance(key_func, str):
                # When string key is provided, append args hash to make it unique
                arg_hash = hashlib.md5(str((args, kwargs)).encode()).hexdigest()[:8]
                cache_key = f"{key_func}_{arg_hash}"
            else:
                # Default: use function name and hash of args
                arg_hash = hashlib.md5(str((args, kwargs)).encode()).hexdigest()[:8]
                cache_key = f"{func.__name__}_{arg_hash}"
            
            # Determine namespace (same logic as sync)
            namespace = "global"
            if scope == "correlation":
                # Try to extract correlation_id from args/kwargs
                correlation_id = kwargs.get("correlation_id")
                if not correlation_id and args:
                    # Common pattern: correlation_id is second argument
                    if len(args) > 1 and isinstance(args[1], str):
                        correlation_id = args[1]
                
                if correlation_id:
                    namespace = correlation_id
            
            # Try to get from cache
            result = cache.get(cache_key, namespace)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                return result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func.__name__}: {cache_key}, executing...")
            result = await func(*args, **kwargs)  # Await the async function
            cache.set(cache_key, result, namespace, ttl_s)
            
            return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Cleanup thread for expired entries
def _start_cleanup_thread():
    """Start background thread to clean up expired cache entries"""
    def cleanup_loop():
        while True:
            try:
                time.sleep(60)  # Check every minute
                _global_cache.cleanup_expired()
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    logger.info("Started cache cleanup thread")


# Start cleanup thread on import
_start_cleanup_thread()
