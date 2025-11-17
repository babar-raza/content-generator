"""
Async Runtime Manager with Fairness Budgeting - Phase 9B

Provides centralized async loop management with per-correlation task limits
and fairness to prevent workflow starvation.
"""

import asyncio
import threading
import time
import logging
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import weakref

from src.core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class TaskInfo:
    """Information about a running task"""
    task_id: str
    correlation_id: str
    capability: str
    agent_id: str
    start_time: datetime = field(default_factory=datetime.now)
    priority: int = 5
    estimated_duration: float = 60.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelationBudget:
    """Budget tracking for a correlation ID"""
    correlation_id: str
    max_tasks: int
    current_tasks: int = 0
    total_submitted: int = 0
    total_completed: int = 0
    first_task_time: Optional[datetime] = None
    last_activity_time: datetime = field(default_factory=datetime.now)
    priority_boost: float = 1.0  # Fairness boost for starved correlations


class FairnessBudgeter:
    """
    Manages task budgets and fairness across correlations.
    
    Features:
    - Per-correlation task limits
    - Global task limits
    - Fairness boosting for starved correlations
    - Time-based budget recovery
    """
    
    def __init__(self, max_tasks_per_correlation: int = 20, global_max_tasks: int = 100):
        self.max_tasks_per_correlation = max_tasks_per_correlation
        self.global_max_tasks = global_max_tasks
        self.fairness_window = timedelta(seconds=Config.BUDGETER_FAIRNESS_WINDOW_S)
        
        # Budget tracking
        self.correlation_budgets: Dict[str, CorrelationBudget] = {}
        self.global_task_count = 0
        self.running_tasks: Dict[str, TaskInfo] = {}  # task_id -> TaskInfo
        
        # Fairness tracking
        self.starvation_queue: deque = deque()  # Correlations waiting for budget
        self.last_fairness_check = datetime.now()
        
        self.lock = threading.RLock()
        
        logger.info(f"FairnessBudgeter: max_per_correlation={max_tasks_per_correlation}, "
                   f"global_max={global_max_tasks}")
    
    def can_submit_task(self, correlation_id: str, priority: int = 5) -> bool:
        """Check if a task can be submitted given current budgets"""
        with self.lock:
            # Check global limit
            if self.global_task_count >= self.global_max_tasks:
                logger.debug(f"Global task limit reached: {self.global_task_count}/{self.global_max_tasks}")
                return False
            
            # Get or create correlation budget
            budget = self._get_or_create_budget(correlation_id)
            
            # Check correlation limit
            if budget.current_tasks >= budget.max_tasks:
                logger.debug(f"Correlation {correlation_id} at task limit: "
                           f"{budget.current_tasks}/{budget.max_tasks}")
                # Add to starvation queue for fairness tracking
                if correlation_id not in [item[0] for item in self.starvation_queue]:
                    self.starvation_queue.append((correlation_id, datetime.now(), priority))
                return False
            
            return True
    
    def submit_task(self, task_info: TaskInfo) -> bool:
        """Submit a task if budget allows"""
        with self.lock:
            if not self.can_submit_task(task_info.correlation_id, task_info.priority):
                return False
            
            # Reserve budget
            budget = self._get_or_create_budget(task_info.correlation_id)
            budget.current_tasks += 1
            budget.total_submitted += 1
            budget.last_activity_time = datetime.now()
            
            if budget.first_task_time is None:
                budget.first_task_time = datetime.now()
            
            self.global_task_count += 1
            self.running_tasks[task_info.task_id] = task_info
            
            logger.debug(f"Task submitted: {task_info.task_id} for {task_info.correlation_id} "
                        f"({budget.current_tasks}/{budget.max_tasks} correlation, "
                        f"{self.global_task_count}/{self.global_max_tasks} global)")
            
            return True
    
    def complete_task(self, task_id: str) -> None:
        """Mark a task as completed and release budget"""
        with self.lock:
            if task_id not in self.running_tasks:
                logger.warning(f"Completing unknown task: {task_id}")
                return
            
            task_info = self.running_tasks.pop(task_id)
            correlation_id = task_info.correlation_id
            
            # Release budget
            if correlation_id in self.correlation_budgets:
                budget = self.correlation_budgets[correlation_id]
                budget.current_tasks = max(0, budget.current_tasks - 1)
                budget.total_completed += 1
                budget.last_activity_time = datetime.now()
            
            self.global_task_count = max(0, self.global_task_count - 1)
            
            # Check if any starved correlations can now proceed
            self._process_starvation_queue()
            
            duration = (datetime.now() - task_info.start_time).total_seconds()
            logger.debug(f"Task completed: {task_id} for {correlation_id} in {duration:.2f}s")
    
    def apply_fairness_boost(self) -> None:
        """Apply fairness boosts to starved correlations"""
        with self.lock:
            now = datetime.now()
            
            # Only check fairness periodically
            if (now - self.last_fairness_check) < self.fairness_window:
                return
            
            self.last_fairness_check = now
            
            # Find correlations that have been waiting too long
            boost_candidates = []
            cutoff_time = now - self.fairness_window
            
            for correlation_id, wait_time, priority in list(self.starvation_queue):
                if wait_time < cutoff_time:
                    boost_candidates.append(correlation_id)
            
            # Apply boosts
            for correlation_id in boost_candidates:
                if correlation_id in self.correlation_budgets:
                    budget = self.correlation_budgets[correlation_id]
                    # Increase max tasks temporarily
                    boost_amount = min(5, self.max_tasks_per_correlation // 4)
                    budget.max_tasks = min(
                        self.max_tasks_per_correlation + boost_amount,
                        budget.max_tasks + boost_amount
                    )
                    budget.priority_boost = min(2.0, budget.priority_boost + 0.5)
                    
                    logger.info(f"Applied fairness boost to {correlation_id}: "
                              f"max_tasks={budget.max_tasks}, boost={budget.priority_boost}")
    
    def _get_or_create_budget(self, correlation_id: str) -> CorrelationBudget:
        """Get or create budget for correlation ID"""
        if correlation_id not in self.correlation_budgets:
            self.correlation_budgets[correlation_id] = CorrelationBudget(
                correlation_id=correlation_id,
                max_tasks=self.max_tasks_per_correlation
            )
        return self.correlation_budgets[correlation_id]
    
    def _process_starvation_queue(self) -> None:
        """Process the starvation queue to see if any can proceed"""
        processed = []
        
        while self.starvation_queue:
            correlation_id, wait_time, priority = self.starvation_queue.popleft()
            
            # Check if this correlation can now proceed
            if self.can_submit_task(correlation_id, priority):
                logger.debug(f"Starvation resolved for {correlation_id}")
                processed.append(correlation_id)
            else:
                # Put it back if still can't proceed
                self.starvation_queue.appendleft((correlation_id, wait_time, priority))
                break  # Stop processing since this one still can't proceed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get budgeter statistics"""
        with self.lock:
            return {
                "global_task_count": self.global_task_count,
                "global_max_tasks": self.global_max_tasks,
                "active_correlations": len(self.correlation_budgets),
                "starved_correlations": len(self.starvation_queue),
                "correlation_stats": {
                    cid: {
                        "current_tasks": budget.current_tasks,
                        "max_tasks": budget.max_tasks,
                        "total_submitted": budget.total_submitted,
                        "total_completed": budget.total_completed,
                        "priority_boost": budget.priority_boost
                    }
                    for cid, budget in self.correlation_budgets.items()
                }
            }


class AsyncRuntimeManager:
    """
    Centralized async runtime with fairness budgeting.
    
    Features:
    - Single event loop for all async operations
    - Fairness budgeting prevents correlation starvation
    - Graceful shutdown and cleanup
    - Performance monitoring
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.loop = None
        self.loop_thread = None
        self.budgeter = FairnessBudgeter(
            max_tasks_per_correlation=Config.BUDGETER_MAX_TASKS_PER_CORRELATION,
            global_max_tasks=Config.BUDGETER_GLOBAL_MAX_TASKS
        )
        self.shutdown_event = threading.Event()
        self.task_counter = 0
        self.task_counter_lock = threading.Lock()
        
        # Performance tracking
        self.submitted_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.start_time = datetime.now()
        
        self._start_loop()
        
        logger.info("AsyncRuntimeManager initialized")
    
    def _start_loop(self):
        """Start the async event loop in a separate thread"""
        self.loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.loop_thread.start()
        
        # Wait for loop to be ready
        while self.loop is None:
            time.sleep(0.01)
    
    def _run_loop(self):
        """Run the async event loop"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            # Schedule periodic fairness checks
            self.loop.create_task(self._fairness_monitor())
            
            # Run until shutdown
            self.loop.run_until_complete(self._wait_for_shutdown())
        except Exception as e:
            logger.error(f"AsyncRuntimeManager loop error: {e}")
        finally:
            self.loop.close()
    
    async def _fairness_monitor(self):
        """Periodic fairness monitoring"""
        while not self.shutdown_event.is_set():
            try:
                self.budgeter.apply_fairness_boost()
                await asyncio.sleep(Config.BUDGETER_FAIRNESS_WINDOW_S)
            except Exception as e:
                logger.error(f"Fairness monitor error: {e}")
                await asyncio.sleep(1.0)
    
    async def _wait_for_shutdown(self):
        """Wait for shutdown signal"""
        while not self.shutdown_event.is_set():
            await asyncio.sleep(0.1)
    
    def submit_task(self, coro: Awaitable, correlation_id: str, capability: str,
                   agent_id: str, priority: int = 5) -> Optional[asyncio.Future]:
        """
        Submit a task for async execution with fairness budgeting
        
        Returns:
            Future object if task was submitted, None if rejected
        """
        if not Config.ENABLE_OPT_PHASE9B:
            # Fallback to direct execution
            return None
        
        # Generate task ID
        with self.task_counter_lock:
            self.task_counter += 1
            task_id = f"task_{self.task_counter}_{int(time.time() * 1000)}"
        
        # Create task info
        task_info = TaskInfo(
            task_id=task_id,
            correlation_id=correlation_id,
            capability=capability,
            agent_id=agent_id,
            priority=priority
        )
        
        # Check budget
        if not self.budgeter.submit_task(task_info):
            logger.debug(f"Task rejected by budgeter: {task_id}")
            return None
        
        # Submit to loop
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._execute_with_cleanup(coro, task_id), 
                self.loop
            )
            
            self.submitted_tasks += 1
            logger.debug(f"Task submitted to runtime: {task_id}")
            return future
            
        except Exception as e:
            # Release budget on submission error
            self.budgeter.complete_task(task_id)
            logger.error(f"Failed to submit task {task_id}: {e}")
            return None
    
    async def _execute_with_cleanup(self, coro: Awaitable, task_id: str):
        """Execute a coroutine with automatic cleanup"""
        try:
            result = await coro
            self.completed_tasks += 1
            return result
        except Exception as e:
            self.failed_tasks += 1
            logger.error(f"Task {task_id} failed: {e}")
            raise
        finally:
            # Always release budget
            self.budgeter.complete_task(task_id)
    
    def shutdown(self):
        """Shutdown the runtime manager"""
        logger.info("Shutting down AsyncRuntimeManager")
        self.shutdown_event.set()
        
        if self.loop_thread and self.loop_thread.is_alive():
            self.loop_thread.join(timeout=5.0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get runtime statistics"""
        runtime_duration = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "runtime_duration_s": runtime_duration,
            "submitted_tasks": self.submitted_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "tasks_per_second": self.completed_tasks / max(runtime_duration, 1),
            "budgeter_stats": self.budgeter.get_stats()
        }


# Global runtime manager instance
_runtime_manager = None

def get_runtime_manager() -> AsyncRuntimeManager:
    """Get the global runtime manager instance"""
    global _runtime_manager
    if _runtime_manager is None:
        _runtime_manager = AsyncRuntimeManager()
    return _runtime_manager
