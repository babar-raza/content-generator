"""Batch processing for LLM requests with automatic timeout and flushing."""
from typing import List, Callable, Any, Optional, Dict
import asyncio
import time
from collections import defaultdict


class BatchProcessor:
    """Processes requests in batches for efficiency with automatic timeout."""
    
    def __init__(self, batch_size: int = 10, timeout: float = 1.0, max_wait: float = 5.0):
        """Initialize batch processor.
        
        Args:
            batch_size: Maximum batch size before auto-processing
            timeout: Time to wait for batch to fill (seconds)
            max_wait: Maximum time any item can wait (seconds)
        """
        self.batch_size = batch_size
        self.timeout = timeout
        self.max_wait = max_wait
        self.queue: List[tuple] = []
        self.lock = asyncio.Lock()
        self.processing = False
        self.batch_count = 0
        self._timeout_task: Optional[asyncio.Task] = None
    
    async def add(self, item: Any, priority: int = 0) -> Any:
        """Add item to batch and wait for result.
        
        Args:
            item: Item to process
            priority: Priority level (higher = processed sooner)
            
        Returns:
            Processing result
        """
        future = asyncio.Future()
        enqueue_time = time.time()
        
        async with self.lock:
            self.queue.append((item, future, priority, enqueue_time))
            # Sort by priority (descending) then enqueue time (ascending)
            self.queue.sort(key=lambda x: (-x[2], x[3]))
            
            # Start timeout task if not already running
            if self._timeout_task is None or self._timeout_task.done():
                self._timeout_task = asyncio.create_task(self._timeout_processor())
            
            # Process batch if full or max wait exceeded
            should_process = (
                len(self.queue) >= self.batch_size or
                any(time.time() - t >= self.max_wait for _, _, _, t in self.queue)
            )
            
            if should_process and not self.processing:
                asyncio.create_task(self._process_batch())
        
        return await future
    
    async def flush(self) -> None:
        """Force process all pending items."""
        async with self.lock:
            if self.queue and not self.processing:
                await self._process_batch()
    
    async def _timeout_processor(self):
        """Background task to process batches on timeout."""
        while True:
            await asyncio.sleep(self.timeout)
            async with self.lock:
                if self.queue and not self.processing:
                    asyncio.create_task(self._process_batch())
    
    async def _process_batch(self):
        """Process accumulated batch."""
        async with self.lock:
            if not self.queue or self.processing:
                return
            
            self.processing = True
            batch = self.queue[:self.batch_size]
            self.queue = self.queue[self.batch_size:]
        
        try:
            items = [item for item, _, _, _ in batch]
            futures = [future for _, future, _, _ in batch]
            
            # Process batch
            results = await self._execute_batch(items)
            
            # Set results
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)
            
            self.batch_count += 1
            
        except Exception as e:
            # Set exception on all futures
            for _, future, _, _ in batch:
                if not future.done():
                    future.set_exception(e)
        finally:
            async with self.lock:
                self.processing = False
    
    async def _execute_batch(self, items: List[Any]) -> List[Any]:
        """Override in subclass to implement batch processing.
        
        Args:
            items: List of items to process
            
        Returns:
            List of results (same length as items)
        """
        raise NotImplementedError("Subclass must implement _execute_batch")
    
    def stats(self) -> Dict[str, Any]:
        """Get batch processing statistics."""
        return {
            'queue_size': len(self.queue),
            'batches_processed': self.batch_count,
            'processing': self.processing
        }


class LLMBatchProcessor(BatchProcessor):
    """Specialized batch processor for LLM requests."""
    
    def __init__(
        self,
        llm_callable: Callable,
        batch_size: int = 5,
        timeout: float = 0.5,
        max_wait: float = 2.0
    ):
        """Initialize LLM batch processor.
        
        Args:
            llm_callable: Async function to call LLM (takes list of prompts)
            batch_size: Batch size (smaller for LLMs due to rate limits)
            timeout: Batch timeout
            max_wait: Maximum wait time
        """
        super().__init__(batch_size, timeout, max_wait)
        self.llm_callable = llm_callable
        self.prompt_cache: Dict[str, str] = {}
    
    async def _execute_batch(self, items: List[str]) -> List[str]:
        """Execute batch of LLM requests.
        
        Args:
            items: List of prompts
            
        Returns:
            List of responses
        """
        # Check cache first
        results = []
        uncached_items = []
        uncached_indices = []
        
        for i, prompt in enumerate(items):
            if prompt in self.prompt_cache:
                results.append(self.prompt_cache[prompt])
            else:
                uncached_items.append(prompt)
                uncached_indices.append(i)
                results.append(None)  # Placeholder
        
        # Process uncached items
        if uncached_items:
            try:
                if asyncio.iscoroutinefunction(self.llm_callable):
                    batch_results = await self.llm_callable(uncached_items)
                else:
                    # Wrap sync function
                    loop = asyncio.get_event_loop()
                    batch_results = await loop.run_in_executor(
                        None, self.llm_callable, uncached_items
                    )
                
                # Update cache and results
                for idx, result in zip(uncached_indices, batch_results):
                    results[idx] = result
                    self.prompt_cache[items[idx]] = result
                    
            except Exception as e:
                # Fill uncached results with error
                for idx in uncached_indices:
                    results[idx] = f"Error: {str(e)}"
        
        return results
