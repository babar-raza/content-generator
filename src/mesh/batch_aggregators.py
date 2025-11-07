"""
Cross-Agent Batch Aggregator - Phase 9B

Aggregates identical API/RAG calls across agents and workflows,
providing efficient batching with fan-out of results.
"""

import asyncio
import threading
import time
import logging
import hashlib
from typing import Dict, List, Any, Optional, Callable, Awaitable, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import weakref
import json

from src.core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class BatchRequest:
    """A request that can be batched with others"""
    request_id: str
    correlation_id: str
    agent_id: str
    batch_key: str  # Identifies batchable requests
    operation: str  # e.g., "rag_query", "api_call", "template_render"
    params: Dict[str, Any]
    callback: Callable[[Any], None]
    timestamp: datetime = field(default_factory=datetime.now)
    timeout: float = 60.0


@dataclass
class BatchGroup:
    """A group of requests that will be batched together"""
    batch_key: str
    operation: str
    requests: List[BatchRequest] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    processing: bool = False
    max_size: int = 10
    window_ms: int = 200


class BatchProcessor:
    """Processes batches of similar requests"""
    
    def __init__(self, operation: str, batch_executor: Callable):
        self.operation = operation
        self.batch_executor = batch_executor
        self.processed_batches = 0
        self.total_requests = 0
        
    async def process_batch(self, batch_group: BatchGroup) -> None:
        """Process a batch of requests"""
        if not batch_group.requests:
            return
        
        logger.debug(f"Processing batch {batch_group.batch_key} with {len(batch_group.requests)} requests")
        
        try:
            # Extract parameters for batch execution
            batch_params = [req.params for req in batch_group.requests]
            
            # Execute batch
            batch_results = await self.batch_executor(batch_params)
            
            # Fan out results to individual callbacks
            for i, request in enumerate(batch_group.requests):
                try:
                    if i < len(batch_results):
                        request.callback(batch_results[i])
                    else:
                        # Handle case where batch returned fewer results
                        request.callback(None)
                except Exception as e:
                    logger.error(f"Error in callback for {request.request_id}: {e}")
            
            self.processed_batches += 1
            self.total_requests += len(batch_group.requests)
            
        except Exception as e:
            logger.error(f"Batch processing error for {batch_group.batch_key}: {e}")
            
            # Notify all requests of failure
            for request in batch_group.requests:
                try:
                    request.callback(None)
                except Exception as callback_error:
                    logger.error(f"Error in failure callback for {request.request_id}: {callback_error}")


class CrossAgentBatchAggregator:
    """
    Aggregates identical requests across agents and workflows.
    
    Features:
    - Identifies batchable requests by content hash
    - Time-based batching windows
    - Size-based batch triggers
    - Fan-out of results to all requesters
    - Support for different operation types (RAG, API, etc.)
    """
    
    def __init__(self):
        self.enabled = Config.CROSS_AGENT_BATCHING_ENABLED
        self.window_ms = Config.CROSS_BATCH_WINDOW_MS
        self.max_batch_size = Config.CROSS_BATCH_MAX_SIZE
        
        # Active batch groups
        self.pending_batches: Dict[str, BatchGroup] = {}  # batch_key -> BatchGroup
        self.lock = threading.RLock()
        
        # Batch processors for different operations
        self.processors: Dict[str, BatchProcessor] = {}
        
        # Performance tracking
        self.total_requests = 0
        self.batched_requests = 0
        self.batch_hit_rate = 0.0
        
        # Background processor
        self.processor_task = None
        self.shutdown_event = threading.Event()
        
        if self.enabled:
            self._start_background_processor()
        
        logger.info(f"CrossAgentBatchAggregator: enabled={self.enabled}, "
                   f"window={self.window_ms}ms, max_size={self.max_batch_size}")
    
    def register_processor(self, operation: str, batch_executor: Callable) -> None:
        """Register a batch processor for an operation type"""
        self.processors[operation] = BatchProcessor(operation, batch_executor)
        logger.info(f"Registered batch processor for operation: {operation}")
    
    def submit_request(self, operation: str, params: Dict[str, Any], 
                      correlation_id: str, agent_id: str,
                      callback: Callable[[Any], None],
                      timeout: float = 60.0) -> bool:
        """
        Submit a request for potential batching
        
        Returns:
            True if request was submitted for batching, False if should execute immediately
        """
        if not self.enabled or operation not in self.processors:
            return False
        
        self.total_requests += 1
        
        # Generate batch key based on operation and parameters
        batch_key = self._generate_batch_key(operation, params)
        request_id = f"{operation}_{int(time.time() * 1000)}_{id(callback)}"
        
        request = BatchRequest(
            request_id=request_id,
            correlation_id=correlation_id,
            agent_id=agent_id,
            batch_key=batch_key,
            operation=operation,
            params=params,
            callback=callback,
            timeout=timeout
        )
        
        with self.lock:
            # Get or create batch group
            if batch_key not in self.pending_batches:
                self.pending_batches[batch_key] = BatchGroup(
                    batch_key=batch_key,
                    operation=operation,
                    max_size=self.max_batch_size,
                    window_ms=self.window_ms
                )
            
            batch_group = self.pending_batches[batch_key]
            
            # Don't add to already processing batches
            if batch_group.processing:
                return False
            
            batch_group.requests.append(request)
            self.batched_requests += 1
            
            # Check if we should trigger immediate processing
            should_process = (
                len(batch_group.requests) >= batch_group.max_size or
                self._is_batch_ready(batch_group)
            )
            
            if should_process:
                self._schedule_batch_processing(batch_key)
        
        logger.debug(f"Request {request_id} submitted for batching (key: {batch_key})")
        return True
    
    def _generate_batch_key(self, operation: str, params: Dict[str, Any]) -> str:
        """Generate a batch key for grouping similar requests"""
        
        # Define which parameters matter for batching by operation
        batch_significant_params = {
            "rag_query": ["domain", "query_type", "max_results"],
            "api_call": ["endpoint", "method", "headers"],
            "template_render": ["template_name", "format"],
            "code_analysis": ["language", "analysis_type"],
            "context_fetch": ["source_type", "filters"]
        }
        
        # Extract significant parameters
        significant = batch_significant_params.get(operation, [])
        filtered_params = {k: v for k, v in params.items() if k in significant}
        
        # Create stable hash
        param_str = json.dumps(filtered_params, sort_keys=True)
        hash_obj = hashlib.md5(f"{operation}:{param_str}".encode())
        
        return f"{operation}_{hash_obj.hexdigest()[:8]}"
    
    def _is_batch_ready(self, batch_group: BatchGroup) -> bool:
        """Check if a batch is ready for processing based on time"""
        age_ms = (datetime.now() - batch_group.created_at).total_seconds() * 1000
        return age_ms >= batch_group.window_ms
    
    def _schedule_batch_processing(self, batch_key: str) -> None:
        """Schedule a batch for processing"""
        if batch_key in self.pending_batches:
            batch_group = self.pending_batches[batch_key]
            batch_group.processing = True
            
            # Submit to background processor
            if self.processor_task:
                try:
                    asyncio.run_coroutine_threadsafe(
                        self._process_batch_group(batch_key),
                        asyncio.get_event_loop()
                    )
                except Exception as e:
                    logger.error(f"Failed to schedule batch processing: {e}")
                    # Reset processing flag
                    batch_group.processing = False
    
    async def _process_batch_group(self, batch_key: str) -> None:
        """Process a specific batch group"""
        with self.lock:
            if batch_key not in self.pending_batches:
                return
            
            batch_group = self.pending_batches.pop(batch_key)
        
        if not batch_group.requests:
            return
        
        operation = batch_group.operation
        if operation not in self.processors:
            logger.error(f"No processor for operation: {operation}")
            return
        
        processor = self.processors[operation]
        await processor.process_batch(batch_group)
    
    def _start_background_processor(self) -> None:
        """Start background processing for time-based batch triggers"""
        def background_processor():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._background_processor_loop())
            except Exception as e:
                logger.error(f"Background processor error: {e}")
        
        processor_thread = threading.Thread(target=background_processor, daemon=True)
        processor_thread.start()
    
    async def _background_processor_loop(self) -> None:
        """Background loop to process time-expired batches"""
        while not self.shutdown_event.is_set():
            try:
                # Check for expired batches
                expired_batches = []
                
                with self.lock:
                    for batch_key, batch_group in list(self.pending_batches.items()):
                        if not batch_group.processing and self._is_batch_ready(batch_group):
                            expired_batches.append(batch_key)
                            self._schedule_batch_processing(batch_key)
                
                if expired_batches:
                    logger.debug(f"Processing {len(expired_batches)} expired batches")
                
                # Sleep for a portion of the window time
                await asyncio.sleep(self.window_ms / 1000.0 / 4)
                
            except Exception as e:
                logger.error(f"Background processor loop error: {e}")
                await asyncio.sleep(1.0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregator statistics"""
        with self.lock:
            pending_count = len(self.pending_batches)
            pending_requests = sum(len(bg.requests) for bg in self.pending_batches.values())
        
        if self.total_requests > 0:
            self.batch_hit_rate = self.batched_requests / self.total_requests
        
        return {
            "enabled": self.enabled,
            "total_requests": self.total_requests,
            "batched_requests": self.batched_requests,
            "batch_hit_rate": self.batch_hit_rate,
            "pending_batches": pending_count,
            "pending_requests": pending_requests,
            "registered_operations": list(self.processors.keys()),
            "processor_stats": {
                op: {
                    "processed_batches": proc.processed_batches,
                    "total_requests": proc.total_requests
                }
                for op, proc in self.processors.items()
            }
        }
    
    def shutdown(self) -> None:
        """Shutdown the aggregator"""
        logger.info("Shutting down CrossAgentBatchAggregator")
        self.shutdown_event.set()


# Example batch executors for common operations

async def rag_query_batch_executor(batch_params: List[Dict[str, Any]]) -> List[Any]:
    """Example batch executor for RAG queries"""
    logger.debug(f"Executing RAG batch with {len(batch_params)} queries")
    
    # Simulate batch RAG execution
    # In real implementation, this would call the RAG system with all queries
    results = []
    for params in batch_params:
        # Mock result based on query
        query = params.get("query", "")
        result = {
            "query": query,
            "results": [f"Mock result for: {query[:50]}..."],
            "metadata": {"batch_processed": True}
        }
        results.append(result)
    
    # Simulate some processing time
    await asyncio.sleep(0.1)
    
    return results


async def api_call_batch_executor(batch_params: List[Dict[str, Any]]) -> List[Any]:
    """Example batch executor for API calls"""
    logger.debug(f"Executing API batch with {len(batch_params)} calls")
    
    # Simulate batch API execution
    results = []
    for params in batch_params:
        endpoint = params.get("endpoint", "unknown")
        result = {
            "endpoint": endpoint,
            "status": "success",
            "data": {"batch_processed": True, "timestamp": time.time()},
            "metadata": {"batch_size": len(batch_params)}
        }
        results.append(result)
    
    # Simulate network delay
    await asyncio.sleep(0.2)
    
    return results


async def template_render_batch_executor(batch_params: List[Dict[str, Any]]) -> List[Any]:
    """Example batch executor for template rendering"""
    logger.debug(f"Executing template batch with {len(batch_params)} renders")
    
    # Group by template for efficient processing
    template_groups = defaultdict(list)
    for i, params in enumerate(batch_params):
        template_name = params.get("template_name", "default")
        template_groups[template_name].append((i, params))
    
    results = [None] * len(batch_params)
    
    # Process each template group
    for template_name, items in template_groups.items():
        for index, params in items:
            # Mock template rendering
            context = params.get("context", {})
            rendered = f"Rendered {template_name} with context keys: {list(context.keys())}"
            results[index] = {
                "template": template_name,
                "rendered": rendered,
                "metadata": {"batch_processed": True}
            }
    
    await asyncio.sleep(0.05)  # Simulate rendering time
    
    return results


# Global batch aggregator instance
_batch_aggregator = None

def get_batch_aggregator() -> CrossAgentBatchAggregator:
    """Get the global batch aggregator instance"""
    global _batch_aggregator
    if _batch_aggregator is None:
        _batch_aggregator = CrossAgentBatchAggregator()
        
        # Register default batch executors
        _batch_aggregator.register_processor("rag_query", rag_query_batch_executor)
        _batch_aggregator.register_processor("api_call", api_call_batch_executor)
        _batch_aggregator.register_processor("template_render", template_render_batch_executor)
    
    return _batch_aggregator
