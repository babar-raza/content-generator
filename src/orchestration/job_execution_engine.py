"""Job Execution Engine - Manages job queue and execution lifecycle."""

import logging
import queue
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

from src.core import EventBus, AgentEvent, Config

from .workflow_compiler import WorkflowCompiler
from .execution_plan import ExecutionPlan, ExecutionStep
from .job_state import JobState, JobMetadata, JobStatus, StepStatus, StepExecution
from .job_storage import JobStorage
from .enhanced_registry import EnhancedAgentRegistry
from .checkpoint_manager import CheckpointManager

logger = logging.getLogger(__name__)


class JobExecutionEngine:
    """Manages job execution lifecycle with queue, persistence, and control operations."""
    
    def __init__(
        self,
        compiler: WorkflowCompiler,
        registry: EnhancedAgentRegistry,
        event_bus: Optional[EventBus] = None,
        config: Optional[Config] = None,
        max_concurrent_jobs: int = 3,
        storage_dir: Optional[Path] = None,
        checkpoint_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize job execution engine.
        
        Args:
            compiler: WorkflowCompiler for creating execution plans
            registry: EnhancedAgentRegistry for agent management
            event_bus: Event bus for emitting job events
            config: Configuration object for agent initialization
            max_concurrent_jobs: Maximum number of concurrent job executions
            storage_dir: Directory for job persistence (default: .jobs/)
            checkpoint_config: Checkpoint configuration (or loaded from config/checkpoints.yaml)
        """
        self.compiler = compiler
        self.registry = registry
        self.event_bus = event_bus or EventBus()
        self.config = config or Config()
        self.max_concurrent_jobs = max_concurrent_jobs
        
        # Job storage
        self.storage = JobStorage(base_dir=storage_dir)
        
        # Checkpoint configuration
        self.checkpoint_config = checkpoint_config or self._load_checkpoint_config()
        checkpoint_path = Path(self.checkpoint_config.get('storage_path', '.checkpoints'))
        self.checkpoint_manager = CheckpointManager(storage_path=checkpoint_path)
        self.checkpoint_keep_last = self.checkpoint_config.get('keep_last', 10)
        self.checkpoint_auto_cleanup = self.checkpoint_config.get('auto_cleanup', True)
        self.checkpoint_keep_after_completion = self.checkpoint_config.get('keep_after_completion', 5)
        
        # Job tracking
        self._jobs: Dict[str, JobState] = {}
        self._lock = threading.RLock()
        
        # Job queue
        self._job_queue: queue.Queue = queue.Queue()
        self._pending_jobs: Set[str] = set()
        
        # Control flags
        self._pause_requested: Dict[str, bool] = {}
        self._cancel_requested: Dict[str, bool] = {}
        self._running = False
        
        # Worker threads
        self._worker_threads: List[threading.Thread] = []
        
        # Load existing jobs on startup
        self._load_persisted_jobs()
    
    def _load_checkpoint_config(self) -> Dict[str, Any]:
        """Load checkpoint configuration from config file."""
        config_file = Path(__file__).parent.parent.parent / 'config' / 'checkpoints.yaml'
        if config_file.exists():
            try:
<<<<<<< Updated upstream
                job.status = JobStatus.RUNNING
                job.progress = 10.0
                job.current_step = "Initializing workflow"
                self._persist_job(job)
                self._notify_status_change(job)
                
                # Log to file
                with open(log_file, 'a') as log:
                    log.write(f"[{datetime.now().isoformat()}] Starting workflow: {workflow_name}\n")
                    log.write(f"[{datetime.now().isoformat()}] Topic: {input_params.get('topic', 'N/A')}\n")
                
                # Get workflow steps
                steps = workflow_def.get('steps', {})
                total_steps = len(steps)
                
                if total_steps == 0:
                    raise ValueError("Workflow has no steps defined")
                
                topic = input_params.get('topic', 'Generated Topic')
                kb_path = input_params.get('kb_path', '')
                
                logger.info(f"Executing workflow '{workflow_name}' for topic: {topic}")
                logger.info(f"Total steps: {total_steps}")
                
                # PRODUCTION EXECUTION - Real agent calls with Ollama
                from .production_execution_engine import ProductionExecutionEngine
                
                # Initialize production engine
                try:
                    prod_engine = ProductionExecutionEngine(self.config)
                    logger.info(f"✓ Production execution engine initialized for job {job_id}")
                except Exception as e:
                    logger.error(f"Failed to initialize production engine: {e}")
                    raise
                
                # Convert steps dict to list format
                steps_list = [
                    {
                        'id': step_id,
                        'agent': step_config.get('agent', step_id),
                        'name': step_config.get('name', step_id)
                    }
                    for step_id, step_config in steps.items()
                ]
                
                # Progress callback for real-time updates
                def progress_callback(progress: float, message: str):
                    job.progress = progress
                    job.current_step = message
                    self._persist_job(job)
                    self._notify_progress(job_id, progress, message)
                
                # Checkpoint callback for pipeline status updates
                def checkpoint_callback(agent_type: str, checkpoint_data: Dict):
                    # Update pipeline status
                    if "pipeline" in job.metadata:
                        for p in job.metadata["pipeline"]:
                            if p["agent"] == agent_type:
                                p["status"] = "completed"
                                break
                    
                    # Log to file
                    with open(log_file, 'a') as log:
                        log.write(
                            f"[{datetime.now().isoformat()}] Completed: {agent_type} | "
                            f"LLM calls: {checkpoint_data.get('llm_calls', 0)}\n"
                        )
                
                # Check for pause/cancel before each agent
                def should_continue():
                    if self._cancel_requests.get(job_id, False):
                        return False
                    while self._pause_requests.get(job_id, False):
                        time.sleep(0.5)
                    return True
                
                # Execute pipeline with real agents
                logger.info(f"Starting production pipeline execution for job {job_id}")
                
                execution_results = prod_engine.execute_pipeline(
                    workflow_name=workflow_name,
                    steps=steps_list,
                    input_data=input_params,
                    job_id=job_id,
                    progress_callback=progress_callback,
                    checkpoint_callback=checkpoint_callback
                )
                
                # Store execution results
                job.output_data = execution_results.get('agent_outputs', {})
                job.metadata['llm_calls'] = execution_results.get('llm_calls', 0)
                job.metadata['tokens_used'] = execution_results.get('tokens_used', 0)
                job.metadata['execution_time'] = execution_results.get('total_duration', 0)
                
                # Check for errors in execution
                if 'error' in execution_results:
                    job.status = JobStatus.FAILED
                    job.error_message = execution_results['error']
                    logger.error(f"Pipeline execution failed: {execution_results['error']}")
                    with open(log_file, 'a') as log:
                        log.write(f"[{datetime.now().isoformat()}] ERROR: {execution_results['error']}\n")
                    return
                
                logger.info(
                    f"✓ Pipeline completed successfully | "
                    f"Job: {job_id} | "
                    f"Duration: {execution_results.get('total_duration', 0):.2f}s | "
                    f"LLM calls: {execution_results.get('llm_calls', 0)}"
                )
                
                with open(log_file, 'a') as log:
                    log.write(f"[{datetime.now().isoformat()}] Pipeline execution completed\n")
                
                # Create artifacts from real agent outputs
                if job.status != JobStatus.CANCELLED:
                    topic = input_params.get('topic', 'Generated Topic')
                    safe_topic = topic.replace(' ', '_').replace('/', '_')
                    
                    # Get assembled content from agent outputs
                    assembled_content = execution_results.get('shared_state', {}).get('assembled_content', '')
                    frontmatter = execution_results.get('shared_state', {}).get('frontmatter', '')
                    
                    # Create output file with real content
                    if assembled_content:
                        artifact_file = artifacts_dir / f"{safe_topic}.md"
                        
                        # Combine frontmatter and content
                        full_content = frontmatter + "\n\n" + assembled_content if frontmatter else assembled_content
                        
                        with open(artifact_file, 'w', encoding='utf-8') as f:
                            f.write(full_content)
                        
                        logger.info(f"✓ Artifact written: {artifact_file}")
                        job.metadata['artifact_path'] = str(artifact_file)
                    
                    # Also save to configured output directory
                    if self.config.output_dir and assembled_content:
                        output_dir = Path(self.config.output_dir)
                        output_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Determine output format based on blog flag
                        if getattr(self.config, 'blog_output', False):
                            # Blog style: ./output/{slug}/index.md
                            slug = execution_results.get('shared_state', {}).get('slug', safe_topic.lower())
                            blog_dir = output_dir / slug
                            blog_dir.mkdir(parents=True, exist_ok=True)
                            output_file = blog_dir / "index.md"
                        else:
                            # Single file: ./output/{slug}.md
                            slug = execution_results.get('shared_state', {}).get('slug', safe_topic.lower())
                            output_file = output_dir / f"{slug}.md"
                        
                        # Write final output
                        full_content = frontmatter + "\n\n" + assembled_content if frontmatter else assembled_content
                        
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(full_content)
                        
                        logger.info(f"✓ Output written: {output_file}")
                        job.metadata['output_path'] = str(output_file)
                    output_dir = Path(input_params.get('output_dir', './output'))
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_file = output_dir / f"{safe_topic}.md"
                    with open(output_file, 'w') as f:
                        f.write(content)
                    
                    with open(log_file, 'a') as log:
                        log.write(f"[{datetime.now().isoformat()}] Artifact created: {artifact_file.name} (also saved to {output_file})\n")
                
                # Check if completed or cancelled
                if job.status != JobStatus.CANCELLED:
                    job.status = JobStatus.COMPLETED
                    job.current_step = "Workflow completed"
                    job.progress = 100.0
                    logger.info(f"Job {job_id} completed successfully")
                    
                    with open(log_file, 'a') as log:
                        log.write(f"[{datetime.now().isoformat()}] Workflow completed successfully\n")
                
                job.completed_at = datetime.now(timezone.utc).isoformat()
                
=======
                import yaml
                with open(config_file, 'r') as f:
                    data = yaml.safe_load(f)
                    return data.get('checkpoint', {})
>>>>>>> Stashed changes
            except Exception as e:
                logger.warning(f"Failed to load checkpoint config: {e}")
        return {}
    
    def _load_persisted_jobs(self) -> None:
        """Load persisted jobs from storage on startup."""
        try:
            jobs = self.storage.list_jobs()
            for metadata in jobs:
                job_state = self.storage.load_job(metadata.job_id)
                if job_state:
                    self._jobs[metadata.job_id] = job_state
                    
                    # Re-queue pending jobs
                    if metadata.status == JobStatus.PENDING:
                        self._pending_jobs.add(metadata.job_id)
                        self._job_queue.put(metadata.job_id)
            
<<<<<<< Updated upstream
        except Exception as e:
            logger.error(f"Job execution failed: {job.job_id}: {e}")
            self._update_job_status(job, JobStatus.FAILED)
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc).isoformat()
            
            # Log error
            if log_file:
                try:
                    with open(log_file, 'a') as log:
                        log.write(f"[{datetime.now().isoformat()}] EXCEPTION: {str(e)}\n")
                except:
                    pass
        
        finally:
            # Cleanup control events
            self._cleanup_job_controls(job.job_id)
            self._persist_job(job)
    
    def _check_control_requests(self, job: JobExecution) -> bool:
        """Check for pause/cancel requests during execution."""
        job_id = job.job_id
        
        # Check for cancellation
        if self._cancel_requests.get(job_id, False):
            logger.info(f"Job cancelled: {job_id}")
            return True
        
        # Check for pause
        if self._pause_requests.get(job_id, False):
            logger.info(f"Job paused: {job_id}")
            
            # Wait for resume signal
            control_event = self._control_events.get(job_id)
            if control_event:
                # Block until resumed or cancelled
                while self._pause_requests.get(job_id, False) and not self._cancel_requests.get(job_id, False):
                    time.sleep(0.1)
                
                # Clear the event for next use
                control_event.clear()
        
        return False
    
    def _update_job_status(self, job: JobExecution, status: JobStatus):
        """Update job status and notify callbacks."""
        old_status = job.status
        job.status = status
        
        if old_status != status:
            logger.info(f"Job {job.job_id} status: {old_status.value} -> {status.value}")
            
            # Notify callbacks
            for callback in self._status_callbacks:
                try:
                    callback(job)
                except Exception as e:
                    logger.error(f"Status callback failed: {e}")
    
    def _update_job_progress(self, job: JobExecution, chunk: Any):
        """Update job progress based on workflow chunk."""
        if job.state:
            total_steps = len(job.state.completed_steps) + len(job.state.failed_steps) + 1
            completed_steps = len(job.state.completed_steps)
            job.progress = min(1.0, completed_steps / total_steps) if total_steps > 0 else 0.0
            job.current_step = job.state.current_step
            
            # Notify progress callbacks
            for callback in self._progress_callbacks:
                try:
                    callback(job.job_id, job.progress, job.current_step or "")
                except Exception as e:
                    logger.error(f"Progress callback failed: {e}")
    
    def _cleanup_job_controls(self, job_id: str):
        """Clean up control structures for a job."""
        with self._lock:
            self._control_events.pop(job_id, None)
            self._pause_requests.pop(job_id, None)
            self._cancel_requests.pop(job_id, None)
    
    def _monitor_jobs(self):
        """Monitor job executions for cleanup and status updates."""
        while self._monitor_running:
            try:
                with self._lock:
                    completed_jobs = []
                    
                    for job_id, job in self._jobs.items():
                        # Check for dead threads
                        if (job.execution_thread and 
                            not job.execution_thread.is_alive() and 
                            job.status == JobStatus.RUNNING):
                            
                            logger.warning(f"Job thread died unexpectedly: {job_id}")
                            self._update_job_status(job, JobStatus.FAILED)
                            job.error_message = "Execution thread terminated unexpectedly"
                            job.completed_at = datetime.now(timezone.utc).isoformat()
                        
                        # Mark old completed jobs for potential cleanup
                        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                            if job.completed_at:
                                try:
                                    completed_time = datetime.fromisoformat(job.completed_at)
                                    age_hours = (datetime.now(timezone.utc) - completed_time).total_seconds() / 3600
                                    if age_hours > 24:  # Keep for 24 hours
                                        completed_jobs.append(job_id)
                                except Exception:
                                    pass
                    
                    # Clean up old jobs (optional)
                    for job_id in completed_jobs[:10]:  # Limit cleanup rate
                        logger.info(f"Cleaning up old job: {job_id}")
                        del self._jobs[job_id]
                        self._cleanup_job_controls(job_id)
                
            except Exception as e:
                logger.error(f"Job monitoring error: {e}")
            
            time.sleep(10)  # Monitor every 10 seconds
    
    def _persist_job(self, job: JobExecution):
        """Persist job to storage."""
        try:
            # Save to job's directory
            job_dir = self.storage_dir / job.job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            job_file = job_dir / "job.json"
            
            job_data = job.to_dict()
            # Remove non-serializable fields
            job_data.pop("execution_thread", None)
            job_data.pop("state", None)
            
            with open(job_file, 'w') as f:
                json.dump(job_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist job {job.job_id}: {e}")
    
    def _load_persisted_jobs(self):
        """Load persisted jobs from storage."""
        try:
            # Handle new structure (data/jobs/{job_id}/job.json)
            for job_dir in self.storage_dir.glob("*"):
                if job_dir.is_dir():
                    job_file = job_dir / "job.json"
                    if job_file.exists():
                        try:
                            with open(job_file, 'r') as f:
                                job_data = json.load(f)
                            
                            # Reconstruct job (without execution thread)
                            job = JobExecution(
                                job_id=job_data["job_id"],
                                workflow_name=job_data["workflow_name"],
                                correlation_id=job_data["correlation_id"],
                                status=JobStatus(job_data["status"]),
                                started_at=job_data.get("started_at"),
                                completed_at=job_data.get("completed_at"),
                                current_step=job_data.get("current_step"),
                                progress=job_data.get("progress", 0.0),
                                input_params=job_data.get("input_params", {}),
                                output_data=job_data.get("output_data", {}),
                                error_message=job_data.get("error_message"),
                                metadata=job_data.get("metadata", {})
                            )
                            
                            # Only load if not in terminal state or recent
                            if job.status in [JobStatus.RUNNING, JobStatus.PAUSED]:
                                # Mark as failed since we lost the execution thread
                                job.status = JobStatus.FAILED
                                job.error_message = "System restart - execution interrupted"
                                job.completed_at = datetime.now(timezone.utc).isoformat()
                            
                            self._jobs[job.job_id] = job
                            
                        except Exception as e:
                            logger.error(f"Failed to load job from {job_file}: {e}")
            
            # Also handle old structure (jobs/{job_id}.json) and migrate
            old_jobs_dir = Path("./jobs")
            if old_jobs_dir.exists():
                for job_file in old_jobs_dir.glob("*.json"):
                    try:
                        with open(job_file, 'r') as f:
                            job_data = json.load(f)
                        
                        job_id = job_data.get("job_id")
                        if job_id and job_id not in self._jobs:
                            # Migrate to new structure
                            new_job_dir = self.storage_dir / job_id
                            new_job_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Create directories
                            (new_job_dir / "artifacts").mkdir(exist_ok=True)
                            (new_job_dir / "logs").mkdir(exist_ok=True)
                            
                            # Copy job file
                            new_job_file = new_job_dir / "job.json"
                            with open(new_job_file, 'w') as f:
                                json.dump(job_data, f, indent=2)
                            
                            # Load the job
                            job = JobExecution(
                                job_id=job_data["job_id"],
                                workflow_name=job_data["workflow_name"],
                                correlation_id=job_data["correlation_id"],
                                status=JobStatus(job_data["status"]),
                                started_at=job_data.get("started_at"),
                                completed_at=job_data.get("completed_at"),
                                current_step=job_data.get("current_step"),
                                progress=job_data.get("progress", 0.0),
                                input_params=job_data.get("input_params", {}),
                                output_data=job_data.get("output_data", {}),
                                error_message=job_data.get("error_message"),
                                metadata=job_data.get("metadata", {})
                            )
                            
                            if job.status in [JobStatus.RUNNING, JobStatus.PAUSED]:
                                job.status = JobStatus.FAILED
                                job.error_message = "System restart - execution interrupted"
                                job.completed_at = datetime.now(timezone.utc).isoformat()
                            
                            self._jobs[job_id] = job
                            logger.info(f"Migrated job {job_id} to new structure")
                            
                    except Exception as e:
                        logger.error(f"Failed to migrate job from {job_file}: {e}")
            
            logger.info(f"Loaded {len(self._jobs)} persisted jobs")
=======
            logger.info(f"Loaded {len(jobs)} persisted jobs")
>>>>>>> Stashed changes
            
        except Exception as e:
            logger.error(f"Failed to load persisted jobs: {e}")
    
    def start(self) -> None:
        """Start the execution engine and worker threads."""
        if self._running:
            logger.warning("Engine already running")
            return
        
        self._running = True
        
        # Start worker threads
        for i in range(self.max_concurrent_jobs):
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"JobWorker-{i}",
                daemon=True
            )
            thread.start()
            self._worker_threads.append(thread)
        
        logger.info(f"Started {self.max_concurrent_jobs} job workers")
    
    def stop(self, timeout: float = 30.0) -> None:
        """Stop the execution engine.
        
        Args:
            timeout: Timeout for waiting for workers to finish
        """
        logger.info("Stopping job execution engine...")
        self._running = False
        
        # Wait for workers to finish
        for thread in self._worker_threads:
            thread.join(timeout=timeout / len(self._worker_threads))
        
        self._worker_threads.clear()
        logger.info("Job execution engine stopped")
    
    def _worker_loop(self) -> None:
        """Worker thread main loop."""
        while self._running:
            try:
                # Get job from queue with timeout
                try:
                    job_id = self._job_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Remove from pending set
                with self._lock:
                    self._pending_jobs.discard(job_id)
                
                # Execute job
                try:
                    self._execute_job(job_id)
                except Exception as e:
                    logger.error(f"Error executing job {job_id}: {e}", exc_info=True)
                    self._mark_job_failed(job_id, str(e))
                finally:
                    self._job_queue.task_done()
                    
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
    
    def submit_job(
        self,
        workflow_id: str,
        inputs: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> str:
        """Submit a new job for execution.
        
        Args:
            workflow_id: Workflow identifier to execute
            inputs: Input parameters for the workflow
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            Job ID (UUID)
        """
        job_id = str(uuid.uuid4())
        
        # Compile workflow
        try:
            plan = self.compiler.compile(workflow_id)
        except Exception as e:
            logger.error(f"Failed to compile workflow {workflow_id}: {e}")
            raise
        
        # Create job metadata
        metadata = JobMetadata(
            job_id=job_id,
            workflow_id=workflow_id,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            total_steps=len(plan.steps),
            correlation_id=correlation_id or job_id
        )
        
        # Create job state
        job_state = JobState(
            metadata=metadata,
            inputs=inputs,
            context={'execution_plan': plan.to_dict()}
        )
        
        # Initialize step executions
        for step in plan.steps:
            job_state.steps[step.agent_id] = StepExecution(agent_id=step.agent_id)
        
        # Store job
        with self._lock:
            self._jobs[job_id] = job_state
            self._pending_jobs.add(job_id)
        
        # Persist to disk
        self.storage.save_job(job_state)
        
        # Emit event
        self.event_bus.publish(AgentEvent(
            event_type="JobSubmitted",
            source_agent="JobExecutionEngine",
            correlation_id=job_state.metadata.correlation_id,
            data={
                'job_id': job_id,
                'workflow_id': workflow_id,
                'correlation_id': metadata.correlation_id
            }
        ))
        
        # Queue for execution
        self._job_queue.put(job_id)
        
        logger.info(f"Submitted job {job_id} for workflow {workflow_id}")
        
        return job_id
    
    def _execute_job(self, job_id: str) -> None:
        """Execute a job.
        
        Args:
            job_id: Job identifier
        """
        with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                logger.error(f"Job {job_id} not found")
                return
            
            # Mark as running
            job_state.metadata.status = JobStatus.RUNNING
            job_state.metadata.started_at = datetime.now()
        
        # Save state
        self.storage.save_job(job_state)
        
        # Emit event
        self.event_bus.publish(AgentEvent(
            event_type="JobStarted",
            source_agent="JobExecutionEngine",
            correlation_id=job_state.metadata.correlation_id,
            data={
                'job_id': job_id,
                'workflow_id': job_state.metadata.workflow_id
            }
        ))
        
        logger.info(f"Started executing job {job_id}")
        
        try:
            # Get execution plan
            plan_dict = job_state.context.get('execution_plan', {})
            plan = ExecutionPlan.from_dict(plan_dict)
            
            # Execute steps
            completed_steps = set()
            
            for step in plan.steps:
                # Check for pause
                if self._check_pause(job_id):
                    logger.info(f"Job {job_id} paused")
                    return
                
                # Check for cancel
                if self._check_cancel(job_id):
                    logger.info(f"Job {job_id} cancelled")
                    self._mark_job_cancelled(job_id)
                    return
                
                # Check if dependencies are completed
                if not all(dep in completed_steps for dep in step.dependencies):
                    logger.warning(f"Dependencies not met for step {step.agent_id}")
                    continue
                
                # Evaluate condition
                if step.condition and not step.evaluate_condition(job_state.outputs):
                    logger.info(f"Skipping step {step.agent_id} due to condition")
                    job_state.mark_step_skipped(step.agent_id)
                    completed_steps.add(step.agent_id)
                    continue
                
                # Execute step
                success = self._execute_step(job_id, job_state, step)
                
                if success:
                    completed_steps.add(step.agent_id)
                    
                    # Save checkpoint after successful step
                    self._save_checkpoint(job_id, job_state, step.agent_id, completed_steps)
                else:
                    # Handle failure based on configuration
                    if step.metadata.get('critical', False):
                        logger.error(f"Critical step {step.agent_id} failed, aborting job")
                        self._mark_job_failed(job_id, f"Critical step {step.agent_id} failed")
                        return
                    else:
                        logger.warning(f"Non-critical step {step.agent_id} failed, continuing")
                        completed_steps.add(step.agent_id)
                
                # Save state after each step
                self.storage.save_job(job_state)
            
            # Mark job as completed
            self._mark_job_completed(job_id)
            
        except Exception as e:
            logger.error(f"Job {job_id} execution failed: {e}", exc_info=True)
            self._mark_job_failed(job_id, str(e))
    
    def _execute_step(
        self,
        job_id: str,
        job_state: JobState,
        step: ExecutionStep
    ) -> bool:
        """Execute a single workflow step.
        
        Args:
            job_id: Job identifier
            job_state: Current job state
            step: Step to execute
            
        Returns:
            True if successful, False otherwise
        """
        agent_id = step.agent_id
        
        # Mark step as started
        job_state.mark_step_started(agent_id)
        
        # Emit event
        self.event_bus.publish(AgentEvent(
            event_type="StepStarted",
            source_agent=agent_id,
            correlation_id=job_state.metadata.correlation_id,
            data={
                'job_id': job_id,
                'agent_id': agent_id
            }
        ))
        
        logger.info(f"Executing step {agent_id} for job {job_id}")
        
        try:
            # Get agent from registry
            agent = self.registry.get_agent(
                agent_id,
                config=self.config,
                event_bus=self.event_bus
            )
            
            if not agent:
                raise ValueError(f"Agent {agent_id} not found in registry")
            
            # Prepare agent inputs
            agent_inputs = self._prepare_agent_inputs(job_state, step)
            
            # Execute agent with timeout
            start_time = time.time()
            
            try:
                # Call agent
                if hasattr(agent, 'run'):
                    result = agent.run(**agent_inputs)
                elif hasattr(agent, 'execute'):
                    result = agent.execute(**agent_inputs)
                else:
                    raise AttributeError(f"Agent {agent_id} has no run() or execute() method")
                
                elapsed = time.time() - start_time
                
                # Check timeout
                if step.timeout > 0 and elapsed > step.timeout:
                    raise TimeoutError(f"Step exceeded timeout of {step.timeout}s")
                
                # Store result in outputs
                if isinstance(result, dict):
                    job_state.outputs.update(result)
                else:
                    job_state.outputs[agent_id] = result
                
                # Mark step as completed
                job_state.mark_step_completed(agent_id, result if isinstance(result, dict) else {'result': result})
                
                # Emit event
                self.event_bus.publish(AgentEvent(
                    event_type="StepCompleted",
                    source_agent=agent_id,
                    correlation_id=job_state.metadata.correlation_id,
                    data={
                        'job_id': job_id,
                        'agent_id': agent_id,
                        'duration': elapsed
                    }
                ))
                
                logger.info(f"Step {agent_id} completed in {elapsed:.2f}s")
                
                return True
                
            except TimeoutError as e:
                logger.error(f"Step {agent_id} timed out: {e}")
                job_state.mark_step_failed(agent_id, str(e))
                return False
                
        except Exception as e:
            logger.error(f"Step {agent_id} failed: {e}", exc_info=True)
            job_state.mark_step_failed(agent_id, str(e))
            
            # Emit event
            self.event_bus.publish(AgentEvent(
                event_type="StepFailed",
                source_agent=agent_id,
                correlation_id=job_state.metadata.correlation_id,
                data={
                    'job_id': job_id,
                    'agent_id': agent_id,
                    'error': str(e)
                }
            ))
            
            # Check if retry is possible
            step_execution = job_state.steps.get(agent_id)
            if step_execution and step_execution.retry_count < step.retry:
                logger.info(f"Retrying step {agent_id} (attempt {step_execution.retry_count + 1}/{step.retry})")
                step_execution.retry_count += 1
                step_execution.status = StepStatus.PENDING
                return self._execute_step(job_id, job_state, step)
            
            return False
    
    def _prepare_agent_inputs(
        self,
        job_state: JobState,
        step: ExecutionStep
    ) -> Dict[str, Any]:
        """Prepare inputs for agent execution.
        
        Args:
            job_state: Current job state
            step: Step being executed
            
        Returns:
            Dictionary of agent inputs
        """
        inputs = {
            'config': self.config,
            **job_state.inputs,
            **job_state.outputs
        }
        
        # Add step-specific metadata
        inputs['_job_id'] = job_state.metadata.job_id
        inputs['_workflow_id'] = job_state.metadata.workflow_id
        inputs['_agent_id'] = step.agent_id
        
        return inputs
    
    def _save_checkpoint(
        self,
        job_id: str,
        job_state: JobState,
        step_name: str,
        completed_steps: Set[str]
    ) -> None:
        """Save checkpoint after step completion.
        
        Args:
            job_id: Job identifier
            job_state: Current job state
            step_name: Name of completed step
            completed_steps: Set of completed step IDs
        """
        try:
            # Prepare checkpoint state
            checkpoint_state = {
                'workflow_id': job_state.metadata.workflow_id,
                'workflow_name': job_state.metadata.workflow_id,
                'current_step': len(completed_steps),
                'completed_steps': list(completed_steps),
                'inputs': job_state.inputs,
                'outputs': job_state.outputs,
                'context': job_state.context,
                'steps': {
                    step_id: {
                        'status': step_exec.status.value,
                        'output': step_exec.output,
                        'started_at': step_exec.started_at.isoformat() if step_exec.started_at else None,
                        'completed_at': step_exec.completed_at.isoformat() if step_exec.completed_at else None,
                        'error': step_exec.error,
                        'retry_count': step_exec.retry_count
                    }
                    for step_id, step_exec in job_state.steps.items()
                },
                'metadata': {
                    'job_id': job_id,
                    'created_at': job_state.metadata.created_at.isoformat(),
                    'started_at': job_state.metadata.started_at.isoformat() if job_state.metadata.started_at else None,
                    'correlation_id': job_state.metadata.correlation_id
                }
            }
            
            # Save checkpoint
            checkpoint_id = self.checkpoint_manager.save(job_id, step_name, checkpoint_state)
            logger.debug(f"Checkpoint saved: {checkpoint_id} for job {job_id} at step {step_name}")
            
            # Cleanup old checkpoints
            self.checkpoint_manager.cleanup(job_id, keep_last=self.checkpoint_keep_last)
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint for job {job_id}: {e}")
    
    def restore_from_checkpoint(self, job_id: str, checkpoint_id: Optional[str] = None) -> bool:
        """Restore a job from checkpoint and resume execution.
        
        Args:
            job_id: Job identifier
            checkpoint_id: Specific checkpoint ID to restore, or None for latest
            
        Returns:
            True if restored successfully, False otherwise
        """
        try:
            # Get checkpoint ID
            if not checkpoint_id:
                checkpoint_id = self.checkpoint_manager.get_latest_checkpoint(job_id)
                if not checkpoint_id:
                    logger.error(f"No checkpoints found for job {job_id}")
                    return False
            
            # Restore checkpoint state
            checkpoint_state = self.checkpoint_manager.restore(job_id, checkpoint_id)
            
            # Recreate job state from checkpoint
            workflow_id = checkpoint_state.get('workflow_id')
            
            # Compile workflow
            plan = self.compiler.compile(workflow_id)
            
            # Create job metadata
            metadata = JobMetadata(
                job_id=job_id,
                workflow_id=workflow_id,
                status=JobStatus.PENDING,
                created_at=datetime.fromisoformat(checkpoint_state['metadata']['created_at']),
                total_steps=len(plan.steps),
                correlation_id=checkpoint_state['metadata']['correlation_id']
            )
            
            # Create job state
            job_state = JobState(
                metadata=metadata,
                inputs=checkpoint_state.get('inputs', {}),
                outputs=checkpoint_state.get('outputs', {}),
                context={
                    **checkpoint_state.get('context', {}),
                    'execution_plan': plan.to_dict(),
                    'restored_from_checkpoint': checkpoint_id,
                    'completed_steps': checkpoint_state.get('completed_steps', [])
                }
            )
            
            # Restore step executions
            steps_data = checkpoint_state.get('steps', {})
            for step_id, step_data in steps_data.items():
                step_exec = StepExecution(agent_id=step_id)
                step_exec.status = StepStatus(step_data.get('status', 'pending'))
                step_exec.output = step_data.get('output')
                step_exec.error = step_data.get('error')
                step_exec.retry_count = step_data.get('retry_count', 0)
                if step_data.get('started_at'):
                    step_exec.started_at = datetime.fromisoformat(step_data['started_at'])
                if step_data.get('completed_at'):
                    step_exec.completed_at = datetime.fromisoformat(step_data['completed_at'])
                job_state.steps[step_id] = step_exec
            
            # Add any missing steps from plan
            for step in plan.steps:
                if step.agent_id not in job_state.steps:
                    job_state.steps[step.agent_id] = StepExecution(agent_id=step.agent_id)
            
            # Store job
            with self._lock:
                self._jobs[job_id] = job_state
                self._pending_jobs.add(job_id)
            
            # Persist to disk
            self.storage.save_job(job_state)
            
            # Queue for execution
            self._job_queue.put(job_id)
            
            logger.info(f"Job {job_id} restored from checkpoint {checkpoint_id}")
            
            # Emit event
            self.event_bus.publish(AgentEvent(
                event_type="JobRestored",
                source_agent="JobExecutionEngine",
                correlation_id=job_state.metadata.correlation_id,
                data={
                    'job_id': job_id,
                    'checkpoint_id': checkpoint_id,
                    'workflow_id': workflow_id
                }
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore job {job_id} from checkpoint: {e}", exc_info=True)
            return False
    
    def _check_pause(self, job_id: str) -> bool:
        """Check if job is paused.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if paused, False otherwise
        """
        with self._lock:
            if self._pause_requested.get(job_id, False):
                job_state = self._jobs.get(job_id)
                if job_state:
                    job_state.metadata.status = JobStatus.PAUSED
                    self.storage.save_job(job_state)
                    
                    # Save checkpoint on pause
                    completed_steps = {
                        step_id for step_id, step_exec in job_state.steps.items()
                        if step_exec.status == StepStatus.COMPLETED
                    }
                    self._save_checkpoint(job_id, job_state, 'paused', completed_steps)
                return True
        return False
    
    def _check_cancel(self, job_id: str) -> bool:
        """Check if job cancellation is requested.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancelled, False otherwise
        """
        with self._lock:
            return self._cancel_requested.get(job_id, False)
    
    def _mark_job_completed(self, job_id: str) -> None:
        """Mark job as completed.
        
        Args:
            job_id: Job identifier
        """
        with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                return
            
            job_state.metadata.status = JobStatus.COMPLETED
            job_state.metadata.completed_at = datetime.now()
            job_state.metadata.progress = 1.0
        
        # Save state
        self.storage.save_job(job_state)
        
        # Handle checkpoint cleanup based on configuration
        if self.checkpoint_auto_cleanup:
            if self.checkpoint_keep_after_completion > 0:
                # Keep last N checkpoints after completion
                self.checkpoint_manager.cleanup(job_id, keep_last=self.checkpoint_keep_after_completion)
                logger.debug(f"Kept last {self.checkpoint_keep_after_completion} checkpoints for completed job {job_id}")
            else:
                # Delete all checkpoints
                self.checkpoint_manager.cleanup_job(job_id)
                logger.debug(f"Deleted all checkpoints for completed job {job_id}")
        
        # Emit event
        self.event_bus.publish(AgentEvent(
            event_type="JobCompleted",
            source_agent="JobExecutionEngine",
            correlation_id=job_state.metadata.correlation_id,
            data={
                'job_id': job_id,
                'workflow_id': job_state.metadata.workflow_id,
                'duration': (
                    job_state.metadata.completed_at - job_state.metadata.started_at
                ).total_seconds() if job_state.metadata.started_at else 0
            }
        ))
        
        logger.info(f"Job {job_id} completed successfully")
    
    def _mark_job_failed(self, job_id: str, error: str) -> None:
        """Mark job as failed.
        
        Args:
            job_id: Job identifier
            error: Error message
        """
        with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                return
            
            job_state.metadata.status = JobStatus.FAILED
            job_state.metadata.completed_at = datetime.now()
            job_state.metadata.error_message = error
        
        # Save state
        self.storage.save_job(job_state)
        
        # Emit event
        self.event_bus.publish(AgentEvent(
            event_type="JobFailed",
            source_agent="JobExecutionEngine",
            correlation_id=job_state.metadata.correlation_id,
            data={
                'job_id': job_id,
                'workflow_id': job_state.metadata.workflow_id,
                'error': error
            }
        ))
        
        logger.error(f"Job {job_id} failed: {error}")
    
    def _mark_job_cancelled(self, job_id: str) -> None:
        """Mark job as cancelled.
        
        Args:
            job_id: Job identifier
        """
        with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                return
            
            # Save checkpoint before cancellation
            completed_steps = {
                step_id for step_id, step_exec in job_state.steps.items()
                if step_exec.status == StepStatus.COMPLETED
            }
            if completed_steps:
                self._save_checkpoint(job_id, job_state, 'cancelled', completed_steps)
            
            job_state.metadata.status = JobStatus.CANCELLED
            job_state.metadata.completed_at = datetime.now()
            
            # Clear cancel flag
            self._cancel_requested.pop(job_id, None)
        
        # Save state
        self.storage.save_job(job_state)
        
        # Emit event
        self.event_bus.publish(AgentEvent(
            event_type="JobCancelled",
            source_agent="JobExecutionEngine",
            correlation_id=job_state.metadata.correlation_id,
            data={
                'job_id': job_id,
                'workflow_id': job_state.metadata.workflow_id
            }
        ))
        
        logger.info(f"Job {job_id} cancelled")
    
    def get_job_status(self, job_id: str) -> Optional[JobMetadata]:
        """Get current status of a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            JobMetadata if found, None otherwise
        """
        with self._lock:
            job_state = self._jobs.get(job_id)
            if job_state:
                return job_state.metadata
        
        # Try loading from storage
        job_state = self.storage.load_job(job_id)
        if job_state:
            with self._lock:
                self._jobs[job_id] = job_state
            return job_state.metadata
        
        return None
    
    def get_job_state(self, job_id: str) -> Optional[JobState]:
        """Get complete job state.
        
        Args:
            job_id: Job identifier
            
        Returns:
            JobState if found, None otherwise
        """
        with self._lock:
            job_state = self._jobs.get(job_id)
            if job_state:
                return job_state
        
        # Try loading from storage
        return self.storage.load_job(job_id)
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a running job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if pause requested, False if job not found or already completed
        """
        with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                logger.warning(f"Job {job_id} not found")
                return False
            
            if job_state.metadata.status not in [JobStatus.RUNNING, JobStatus.PENDING]:
                logger.warning(f"Cannot pause job {job_id} in state {job_state.metadata.status}")
                return False
            
            self._pause_requested[job_id] = True
        
        logger.info(f"Pause requested for job {job_id}")
        return True
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if resumed, False if job not found or not paused
        """
        with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                logger.warning(f"Job {job_id} not found")
                return False
            
            if job_state.metadata.status != JobStatus.PAUSED:
                logger.warning(f"Cannot resume job {job_id} in state {job_state.metadata.status}")
                return False
            
            # Clear pause flag
            self._pause_requested.pop(job_id, None)
            
            # Mark as pending and re-queue
            job_state.metadata.status = JobStatus.PENDING
            self._pending_jobs.add(job_id)
        
        # Save state
        self.storage.save_job(job_state)
        
        # Re-queue for execution
        self._job_queue.put(job_id)
        
        logger.info(f"Resumed job {job_id}")
        return True
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancellation requested, False if job not found or already completed
        """
        with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                logger.warning(f"Job {job_id} not found")
                return False
            
            if job_state.metadata.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                logger.warning(f"Cannot cancel job {job_id} in state {job_state.metadata.status}")
                return False
            
            if job_state.metadata.status == JobStatus.PENDING:
                # Remove from queue if not started
                self._pending_jobs.discard(job_id)
                self._mark_job_cancelled(job_id)
                return True
            
            self._cancel_requested[job_id] = True
        
        logger.info(f"Cancellation requested for job {job_id}")
        return True
    
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: Optional[int] = None
    ) -> List[JobMetadata]:
        """List jobs, optionally filtered by status.
        
        Args:
            status: Optional status filter
            limit: Optional limit on results
            
        Returns:
            List of job metadata
        """
        return self.storage.list_jobs(status=status, limit=limit)
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job from storage.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if deleted, False otherwise
        """
        with self._lock:
            # Remove from memory
            self._jobs.pop(job_id, None)
            self._pending_jobs.discard(job_id)
            self._pause_requested.pop(job_id, None)
            self._cancel_requested.pop(job_id, None)
        
        # Delete from storage
        return self.storage.delete_job(job_id)
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get engine statistics.
        
        Returns:
            Dictionary with engine stats
        """
        with self._lock:
            pending_count = len([
                j for j in self._jobs.values()
                if j.metadata.status == JobStatus.PENDING
            ])
            running_count = len([
                j for j in self._jobs.values()
                if j.metadata.status == JobStatus.RUNNING
            ])
            paused_count = len([
                j for j in self._jobs.values()
                if j.metadata.status == JobStatus.PAUSED
            ])
        
        storage_stats = self.storage.get_storage_stats()
        
        return {
            'running': self._running,
            'max_concurrent_jobs': self.max_concurrent_jobs,
            'worker_threads': len(self._worker_threads),
            'jobs_in_memory': len(self._jobs),
            'pending_jobs': pending_count,
            'running_jobs': running_count,
            'paused_jobs': paused_count,
            'queue_size': self._job_queue.qsize(),
            'storage': storage_stats
        }
