"""Mesh Infrastructure Layer (v5_2)

Provides enhanced registry, bidding, flow control, caching, and fault tolerance.
"""

from .capability_registry import CapabilityRegistry
from .runtime_async import AsyncRuntimeManager, FairnessBudgeter, TaskInfo
from .negotiation import NegotiationManager, DependencyTracker
from .batch_aggregators import CrossAgentBatchAggregator, BatchProcessor
from .state_store import StateStore, StateWatcher
from .mesh_observer import MeshObserver, PerformanceAnalyzer, DeadlockDetector
from .cache.cache import LRUCache, CacheEntry

# Aliases for backwards compatibility
AsyncRuntime = AsyncRuntimeManager
AsyncExecutor = AsyncRuntimeManager
NegotiationEngine = NegotiationManager
BatchAggregator = CrossAgentBatchAggregator
CacheManager = LRUCache

__all__ = [
    'CapabilityRegistry',
    'AsyncRuntimeManager',
    'AsyncRuntime',  # Alias
    'AsyncExecutor',  # Alias
    'FairnessBudgeter',
    'TaskInfo',
    'NegotiationManager',
    'NegotiationEngine',  # Alias
    'DependencyTracker',
    'CrossAgentBatchAggregator',
    'BatchAggregator',  # Alias
    'BatchProcessor',
    'StateStore',
    'StateWatcher',
    'MeshObserver',
    'PerformanceAnalyzer',
    'DeadlockDetector',
    'LRUCache',
    'CacheManager',  # Alias
    'CacheEntry',
]

__version__ = '2.0.0'

