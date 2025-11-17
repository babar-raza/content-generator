"""Job Execution Engine for running workflow jobs."""

import logging
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import deque
from dataclasses import dataclass, field


class InvalidStateTransition(Exception):
    """Exception raised for invalid job state transitions."""
    pass


class JobState(Enum):
    """Job execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    def can_transition_to(self, new_state: 'JobState') -> bool:
        """Check if transition to new state is valid."""
        valid_transitions = {
            JobState.PENDING: {JobState.RUNNING, JobState.CANCELLED},
            JobState.RUNNING: {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED},
            JobState.COMPLETED: set(),
            JobState.FAILED: {JobState.PENDING},  # Allow retry
            JobState.CANCELLED: set()
        }
        return new_state in valid_transitions.get(self, set())


@dataclass
class Job:
    """Job representation."""
    id: str
    workflow_name: str
    steps: List[Dict[str, Any]]
    state: JobState = JobState.PENDING
    current_step: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    results: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3


class JobExecutionEngine:
    """Engine for executing workflow jobs."""
    
    def __init__(self, max_concurrent_jobs: int = 1):
        """Initialize the execution engine.
        
        Args:
            max_concurrent_jobs: Maximum number of concurrent jobs
        """
        self.max_concurrent_jobs = max_concurrent_jobs
        self.logger = logging.getLogger(__name__)
        
        # Job storage
        self.jobs: Dict[str, Job] = {}
        self.job_queue: deque = deque()
        
        # Execution state
        self.running = False
        self.current_job: Optional[Job] = None
        self.worker_thread: Optional[threading.Thread] = None
        
        # Thread safety
        self._state_lock = threading.RLock()
        
        # Callbacks
        self.step_callbacks: Dict[str, Callable] = {}
    
    def submit_job(self, job: Job) -> str:
        """Submit a job for execution.
        
        Args:
            job: Job to execute
            
        Returns:
            Job ID
        """
        with self._state_lock:
            self.jobs[job.id] = job
            self.job_queue.append(job.id)
        
        self.logger.info(f"Job {job.id} submitted to queue")
        
        # Start worker if not running
        if not self.running:
            self.start()
        
        return job.id
    
    def start(self):
        """Start the execution engine."""
        if self.running:
            self.logger.warning("Engine already running")
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.logger.info("Execution engine started")
    
    def stop(self, timeout: int = 30):
        """Stop the execution engine gracefully.
        
        Args:
            timeout: Maximum seconds to wait for current job to complete
        """
        self.logger.info("Initiating graceful shutdown...")
        self.running = False
        
        # Wait for current job to finish
        if self.current_job:
            self.logger.info(f"Waiting for job {self.current_job.id} to complete (max {timeout}s)...")
            
            for elapsed in range(timeout):
                if not self.current_job:
                    self.logger.info("Current job completed successfully")
                    break
                time.sleep(1)
            else:
                # Timeout reached, preserve current job state
                if self.current_job:
                    with self._state_lock:
                        self.logger.warning(
                            f"Job {self.current_job.id} did not complete within timeout. "
                            f"Preserving state at step {self.current_job.current_step}"
                        )
                        # Reset to pending for retry on restart
                        self.current_job.state = JobState.PENDING
                        self.current_job.updated_at = datetime.now()
                        # Re-queue the job
                        if self.current_job.id not in self.job_queue:
                            self.job_queue.appendleft(self.current_job.id)
        
        # Wait for worker thread to finish
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        
        self.logger.info("Execution engine stopped")
    
    def _worker_loop(self):
        """Main worker loop for job execution."""
        while self.running:
            try:
                job_to_execute = None
                
                # Get next job from queue with thread safety
                with self._state_lock:
                    if self.job_queue and not self.current_job:
                        job_id = self.job_queue.popleft()
                        job_to_execute = self.jobs.get(job_id)
                
                if job_to_execute:
                    self._execute_job(job_to_execute)
                else:
                    # No jobs, sleep briefly
                    time.sleep(0.1)
            
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
                time.sleep(1)
    
    def _execute_job(self, job: Job):
        """Execute a single job.
        
        Args:
            job: Job to execute
        """
        try:
            # Update job state to running with thread safety
            with self._state_lock:
                if not job.state.can_transition_to(JobState.RUNNING):
                    self.logger.warning(
                        f"Job {job.id} cannot transition from {job.state} to RUNNING"
                    )
                    return
                
                self.current_job = job
                job.state = JobState.RUNNING
                job.started_at = datetime.now()
                job.updated_at = datetime.now()
            
            self.logger.info(f"Starting job {job.id}")
            
            # Execute each step
            for step_idx, step in enumerate(job.steps):
                # Check if we should stop
                if not self.running:
                    self.logger.info(f"Job {job.id} interrupted at step {step_idx}")
                    return
                
                # Update current step with thread safety
                with self._state_lock:
                    job.current_step = step_idx
                    job.updated_at = datetime.now()
                
                self.logger.info(f"Job {job.id}: Executing step {step_idx}")
                
                # Execute step
                step_name = step.get('name', f'step_{step_idx}')
                result = self._execute_step(job, step)
                
                # Store step result
                with self._state_lock:
                    job.results[step_name] = result
            
            # Job completed successfully
            with self._state_lock:
                if not job.state.can_transition_to(JobState.COMPLETED):
                    self.logger.warning(
                        f"Job {job.id} cannot transition from {job.state} to COMPLETED"
                    )
                    return
                
                job.state = JobState.COMPLETED
                job.completed_at = datetime.now()
                job.updated_at = datetime.now()
            
            self.logger.info(f"Job {job.id} completed successfully")
        
        except Exception as e:
            # Handle job failure
            self.logger.error(f"Job {job.id} failed: {e}")
            
            with self._state_lock:
                job.error = str(e)
                job.updated_at = datetime.now()
                
                # Check if we should retry
                if job.retry_count < job.max_retries:
                    job.retry_count += 1
                    
                    if job.state.can_transition_to(JobState.PENDING):
                        job.state = JobState.PENDING
                        self.job_queue.append(job.id)
                        self.logger.info(
                            f"Job {job.id} queued for retry "
                            f"({job.retry_count}/{job.max_retries})"
                        )
                else:
                    if job.state.can_transition_to(JobState.FAILED):
                        job.state = JobState.FAILED
                        job.completed_at = datetime.now()
                        self.logger.error(
                            f"Job {job.id} failed permanently after {job.retry_count} retries"
                        )
        
        finally:
            # Clear current job with thread safety
            with self._state_lock:
                self.current_job = None
    
    def _execute_step(self, job: Job, step: Dict[str, Any]) -> Any:
        """Execute a single workflow step.
        
        Args:
            job: Current job
            step: Step configuration
            
        Returns:
            Step result
        """
        step_name = step.get('name', 'unnamed')
        agent_name = step.get('agent')
        
        # Get step callback
        if agent_name in self.step_callbacks:
            callback = self.step_callbacks[agent_name]
            
            # Execute callback with step inputs
            inputs = step.get('inputs', {})
            result = callback(inputs)
            
            return result
        else:
            raise ValueError(f"No callback registered for agent '{agent_name}'")
    
    def register_step_callback(self, agent_name: str, callback: Callable):
        """Register a callback for an agent.
        
        Args:
            agent_name: Name of the agent
            callback: Callback function to execute
        """
        self.step_callbacks[agent_name] = callback
        self.logger.info(f"Registered callback for agent '{agent_name}'")
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status dictionary or None
        """
        with self._state_lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            
            return {
                'id': job.id,
                'workflow_name': job.workflow_name,
                'state': job.state.value,
                'current_step': job.current_step,
                'total_steps': len(job.steps),
                'progress': (job.current_step / len(job.steps) * 100) if job.steps else 0,
                'created_at': job.created_at.isoformat(),
                'updated_at': job.updated_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'error': job.error,
                'retry_count': job.retry_count
            }
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if cancelled, False otherwise
        """
        with self._state_lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
            
            # Can only cancel pending or running jobs
            if job.state.can_transition_to(JobState.CANCELLED):
                job.state = JobState.CANCELLED
                job.updated_at = datetime.now()
                job.completed_at = datetime.now()
                
                # Remove from queue if pending
                if job_id in self.job_queue:
                    self.job_queue.remove(job_id)
                
                self.logger.info(f"Job {job_id} cancelled")
                return True
            
            self.logger.warning(
                f"Cannot cancel job {job_id} in state {job.state}"
            )
            return False
    
    def list_jobs(self, state: Optional[JobState] = None) -> List[Dict[str, Any]]:
        """List all jobs, optionally filtered by state.
        
        Args:
            state: Optional state filter
            
        Returns:
            List of job status dictionaries
        """
        with self._state_lock:
            jobs = []
            for job in self.jobs.values():
                if state is None or job.state == state:
                    # Build status dict inline to avoid nested lock
                    status = {
                        'id': job.id,
                        'workflow_name': job.workflow_name,
                        'state': job.state.value,
                        'current_step': job.current_step,
                        'total_steps': len(job.steps),
                        'progress': (job.current_step / len(job.steps) * 100) if job.steps else 0,
                        'created_at': job.created_at.isoformat(),
                        'updated_at': job.updated_at.isoformat(),
                        'started_at': job.started_at.isoformat() if job.started_at else None,
                        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                        'error': job.error,
                        'retry_count': job.retry_count
                    }
                    jobs.append(status)
            
            return jobs
    
    def get_queue_size(self) -> int:
        """Get the number of jobs in queue.
        
        Returns:
            Queue size
        """
        with self._state_lock:
            return len(self.job_queue)
    
    def clear_completed_jobs(self) -> int:
        """Clear completed and failed jobs from memory.
        
        Returns:
            Number of jobs cleared
        """
        with self._state_lock:
            to_remove = []
            for job_id, job in self.jobs.items():
                if job.state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
                    to_remove.append(job_id)
            
            for job_id in to_remove:
                del self.jobs[job_id]
            
            self.logger.info(f"Cleared {len(to_remove)} completed jobs")
            return len(to_remove)
