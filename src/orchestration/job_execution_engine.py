# job_execution_engine.py
"""Job execution engine with live control capabilities for UCOP workflows.

Provides start, pause, resume, cancel, and real-time monitoring of workflow executions.
"""

import asyncio
import threading
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import json
from pathlib import Path

from .workflow_compiler import WorkflowCompiler, WorkflowState, WorkflowDefinition, create_initial_state
from .checkpoint_manager import CheckpointManager, CheckpointState

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobExecution:
    """Represents a job execution instance."""
    job_id: str
    workflow_name: str
    correlation_id: str
    status: JobStatus = JobStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    current_step: Optional[str] = None
    progress: float = 0.0
    input_params: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_thread: Optional[threading.Thread] = None
    state: Optional[WorkflowState] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    batch_group_id: Optional[str] = None  # NEW: for batch support
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "workflow_name": self.workflow_name,
            "correlation_id": self.correlation_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "current_step": self.current_step,
            "progress": self.progress,
            "input_params": self.input_params,
            "topic": self.input_params.get("topic", "Unknown"),
            "output_data": self.output_data,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "batch_group_id": self.batch_group_id,  # NEW
            "step_details": self.state.get('step_details', {}) if self.state else {}  # Agent execution details
        }


class JobExecutionEngine:
    """Manages job execution with live control capabilities."""
    
    def __init__(self, workflow_compiler: WorkflowCompiler, checkpoint_manager: CheckpointManager):
        self.workflow_compiler = workflow_compiler
        self.checkpoint_manager = checkpoint_manager
        
        # Job tracking
        self._jobs: Dict[str, JobExecution] = {}
        self._lock = threading.RLock()
        
        # Event callbacks
        self._status_callbacks: List[Callable[[JobExecution], None]] = []
        self._progress_callbacks: List[Callable[[str, float, str], None]] = []
        
        # Control channels
        self._control_events: Dict[str, asyncio.Event] = {}
        self._pause_requests: Dict[str, bool] = {}
        self._cancel_requests: Dict[str, bool] = {}
        
        # Monitoring
        self._monitor_thread = None
        self._monitor_running = False
        
        # Storage for persistence
        self.storage_dir = Path("./data/jobs")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self._load_persisted_jobs()

    def submit_job(self, workflow_name: str, input_params: Dict[str, Any], job_id: str = None) -> str:
        """Submit a new job for execution."""
        if job_id is None:
            job_id = str(uuid.uuid4())
        
        # Get workflow definition
        workflow_def = self.workflow_compiler.workflows.get(workflow_name)
        if not workflow_def:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        # Create job directories for artifacts and logs
        job_dir = self.storage_dir / job_id
        artifacts_dir = job_dir / "artifacts"
        logs_dir = job_dir / "logs"
        job_dir.mkdir(parents=True, exist_ok=True)
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create job execution
        correlation_id = str(uuid.uuid4())
        job = JobExecution(
            job_id=job_id,
            workflow_name=workflow_name,
            correlation_id=correlation_id,
            status=JobStatus.PENDING,
            started_at=datetime.now(timezone.utc).isoformat(),
            input_params=input_params,
            metadata={
                "artifacts_dir": str(artifacts_dir),
                "logs_dir": str(logs_dir)
            }
        )
        
        # Store pipeline from workflow definition for later access
        if workflow_def:
            steps = workflow_def.get('steps', {})
            pipeline = []
            for step_id, step_config in steps.items():
                pipeline.append({
                    "id": step_id,
                    "name": step_config.get("name", step_id),
                    "agent": step_config.get("agent", step_id),
                    "status": "pending"
                })
            job.metadata["pipeline"] = pipeline
        
        with self._lock:
            self._jobs[job_id] = job
        
        # Persist job
        self._persist_job(job)
        
        # Setup logging to file
        log_file = logs_dir / "job.log"
        
        # Start execution in background thread - use real workflow execution
        def execute():
            try:
                logger.info(f"[Job {job_id}] Starting execution")
                with open(log_file, 'a') as log:
                    log.write(f"[{datetime.now().isoformat()}] Execution started\n")
                
                # Initialize workflow state with proper structure
                try:
                    topic_str = input_params.get('topic', '')
                    if isinstance(topic_str, dict):
                        topic_dict = topic_str
                    else:
                        topic_dict = {'title': topic_str, 'description': ''}
                    
                    logger.info(f"[Job {job_id}] Creating initial state")
                    job.state = create_initial_state(
                        topic=topic_dict.get('title', '') if isinstance(topic_dict, dict) else str(topic_dict),
                        kb_path=input_params.get('kb_path', ''),
                        uploaded_files=input_params.get('uploaded_files', []),
                        execution_id=job_id,
                        correlation_id=correlation_id,
                        deterministic=input_params.get('deterministic', False),
                        max_retries=input_params.get('max_retries', 3)
                    )
                    logger.info(f"[Job {job_id}] Initial state created")
                except Exception as e:
                    logger.error(f"[Job {job_id}] Failed to create initial state: {e}", exc_info=True)
                    with open(log_file, 'a') as log:
                        log.write(f"[{datetime.now().isoformat()}] ERROR creating state: {e}\n")
                    raise
                
                # Update job to running
                job.status = JobStatus.RUNNING
                job.progress = 5.0
                job.current_step = "Initializing workflow"
                self._persist_job(job)
                self._notify_status_change(job)
                
                # Log to file
                with open(log_file, 'a') as log:
                    log.write(f"[{datetime.now().isoformat()}] Starting workflow: {workflow_name}\n")
                    log.write(f"[{datetime.now().isoformat()}] Topic: {topic_str}\n")
                
                # Compile workflow
                try:
                    logger.info(f"[Job {job_id}] Compiling workflow: {workflow_name}")
                    compiled_workflow = self.workflow_compiler.compile_workflow(workflow_name)
                    logger.info(f"[Job {job_id}] Workflow compiled successfully")
                except Exception as e:
                    logger.error(f"[Job {job_id}] Failed to compile workflow: {e}", exc_info=True)
                    with open(log_file, 'a') as log:
                        log.write(f"[{datetime.now().isoformat()}] ERROR compiling workflow: {e}\n")
                    raise
                
                # Execute workflow with streaming
                config = {"configurable": {"thread_id": job_id}}
                step_count = 0
                
                logger.info(f"[Job {job_id}] Starting workflow stream")
                with open(log_file, 'a') as log:
                    log.write(f"[{datetime.now().isoformat()}] Starting workflow stream\n")
                
                try:
                    for chunk in compiled_workflow.stream(job.state, config=config):
                        # Check for cancellation
                        if self._cancel_requests.get(job_id, False):
                            job.status = JobStatus.CANCELLED
                            job.error_message = "Job cancelled by user"
                            logger.info(f"[Job {job_id}] Cancelled by user")
                            break
                        
                        # Handle pause
                        while self._pause_requests.get(job_id, False):
                            time.sleep(0.5)
                        
                        # Update job state with chunk
                        if chunk:
                            # Merge chunk into job.state
                            for key, value in chunk.items():
                                if key in job.state:
                                    job.state[key] = value
                            
                            # Log and update progress
                            if 'current_step' in chunk:
                                step_count += 1
                                current_step = chunk['current_step']
                                job.current_step = current_step
                                
                                with open(log_file, 'a') as log:
                                    log.write(f"[{datetime.now().isoformat()}] Step {step_count}: {current_step}\n")
                                
                                # Calculate progress
                                completed_steps = len(job.state.get('completed_steps', []))
                                failed_steps = len(job.state.get('failed_steps', []))
                                total_steps = completed_steps + failed_steps + 1
                                job.progress = 10.0 + (completed_steps / max(total_steps, 1)) * 85.0
                                
                                logger.info(f"[Job {job_id}] progress: {job.progress:.1f}% - {current_step}")
                                
                                self._persist_job(job)
                                self._notify_progress(job_id, job.progress, current_step)
                    
                    logger.info(f"[Job {job_id}] Stream completed")
                    with open(log_file, 'a') as log:
                        log.write(f"[{datetime.now().isoformat()}] Stream completed\n")
                        
                except Exception as e:
                    logger.error(f"[Job {job_id}] Stream error: {e}", exc_info=True)
                    with open(log_file, 'a') as log:
                        log.write(f"[{datetime.now().isoformat()}] Stream ERROR: {e}\n")
                    raise
                
                # Get final state from LangGraph
                final_state = compiled_workflow.get_state(config)
                if final_state and hasattr(final_state, 'values'):
                    job.state = final_state.values
                
                # Save artifacts
                if job.status != JobStatus.CANCELLED:
                    if not job.state.get('error'):
                        job.status = JobStatus.COMPLETED
                        
                        # Save final content
                        try:
                            final_content = job.state.get('final_content', '') or job.state.get('assembled_content', '')
                            
                            if final_content:
                                # Save to artifacts directory
                                artifact_file = artifacts_dir / "_output.md"
                                with open(artifact_file, 'w', encoding='utf-8') as f:
                                    f.write(final_content)
                                
                                # Save to output directory
                                output_dir = Path(input_params.get('output_dir', './output'))
                                output_dir.mkdir(parents=True, exist_ok=True)
                                
                                # Get safe filename from slug or topic
                                slug = job.state.get('slug', '')
                                if slug and isinstance(slug, str):
                                    safe_topic = slug
                                elif isinstance(topic_dict, dict):
                                    title = topic_dict.get('title', 'untitled')
                                    # Sanitize title for filename
                                    safe_topic = title.replace(' ', '_').replace('/', '_').replace(':', '_').replace('\\', '_')
                                    safe_topic = ''.join(c for c in safe_topic if c.isalnum() or c in ('_', '-'))[:50]
                                    if not safe_topic:
                                        safe_topic = 'untitled'
                                else:
                                    safe_topic = str(topic_dict).replace(' ', '_').replace('/', '_')[:50]
                                
                                output_file = output_dir / f"{safe_topic}.md"
                                with open(output_file, 'w', encoding='utf-8') as f:
                                    f.write(final_content)
                                
                                logger.info(f"Created artifact: {artifact_file.name} (also saved to {output_file})")
                                with open(log_file, 'a') as log:
                                    log.write(f"[{datetime.now().isoformat()}] Artifact created: _output.md\n")
                            else:
                                logger.warning(f"No final content generated for job {job_id}")
                                with open(log_file, 'a') as log:
                                    log.write(f"[{datetime.now().isoformat()}] WARNING: No final content generated\n")
                        
                        except Exception as e:
                            logger.error(f"Failed to create artifacts: {e}")
                            with open(log_file, 'a') as log:
                                log.write(f"[{datetime.now().isoformat()}] ERROR creating artifacts: {e}\n")
                        
                        job.current_step = "Workflow completed"
                        job.progress = 100.0
                        logger.info(f"Job {job_id} completed successfully")
                        with open(log_file, 'a') as log:
                            log.write(f"[{datetime.now().isoformat()}] Workflow completed successfully\n")
                    else:
                        job.status = JobStatus.FAILED
                        job.error_message = job.state.get('error', 'Unknown error')
                        logger.error(f"[Job {job_id}] FAILED: {job.error_message}")
                        print(f"ERROR - Job {job_id} failed: {job.error_message}")
                        with open(log_file, 'a') as log:
                            log.write(f"[{datetime.now().isoformat()}] FAILED: {job.error_message}\n")
                
                job.completed_at = datetime.now(timezone.utc).isoformat()
            
            except Exception as e:
                import traceback
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc).isoformat()
                job.progress = max(job.progress, 5.0)
                logger.error(f"[Job {job_id}] EXCEPTION: {e}", exc_info=True)
                print(f"\n{'='*60}\nERROR - Job {job_id} EXCEPTION:\n{traceback.format_exc()}{'='*60}\n")
                
                with open(log_file, 'a') as log:
                    log.write(f"[{datetime.now().isoformat()}] EXCEPTION: {e}\n")
                    log.write(f"[{datetime.now().isoformat()}] Traceback:\n")
                    log.write(traceback.format_exc())
                    log.write("\n")
            
            finally:
                self._persist_job(job)
                self._notify_status_change(job)
        
        thread = threading.Thread(target=execute, daemon=True)
        job.execution_thread = thread
        thread.start()
        
        logger.info(f"Submitted job {job_id} for workflow {workflow_name}")
        return job_id

    def _notify_status_change(self, job: JobExecution):
        """Notify status change callbacks."""
        for callback in self._status_callbacks:
            try:
                callback(job)
            except Exception as e:
                logger.error(f"Status callback failed: {e}")

    def _notify_progress(self, job_id: str, progress: float, step: str):
        """Notify progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(job_id, progress, step)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")
                
    def start_monitoring(self):
        """Start the job monitoring thread."""
        if not self._monitor_running:
            self._monitor_running = True
            self._monitor_thread = threading.Thread(target=self._monitor_jobs, daemon=True)
            self._monitor_thread.start()
            logger.info("Started job monitoring")
    
    def stop_monitoring(self):
        """Stop the job monitoring thread."""
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Stopped job monitoring")
    
    def register_status_callback(self, callback: Callable[[JobExecution], None]):
        """Register callback for job status changes."""
        with self._lock:
            self._status_callbacks.append(callback)
    
    def register_progress_callback(self, callback: Callable[[str, float, str], None]):
        """Register callback for job progress updates."""
        with self._lock:
            self._progress_callbacks.append(callback)
    
    def start_job(
        self, 
        workflow_name: str, 
        input_params: Dict[str, Any],
        correlation_id: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> JobExecution:
        """Start a new job execution."""
        with self._lock:
            # Generate IDs
            job_id = job_id or f"job_{uuid.uuid4().hex[:8]}"
            correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:8]}"
            
            # Validate workflow exists
            workflow_def = self.workflow_compiler.get_workflow_definition(workflow_name)
            if not workflow_def:
                raise ValueError(f"Workflow not found: {workflow_name}")
            
            # Validate workflow
            validation_issues = self.workflow_compiler.validate_workflow(workflow_name)
            if validation_issues:
                raise ValueError(f"Workflow validation failed: {validation_issues}")
            
            # Create job directories for artifacts and logs
            job_dir = self.storage_dir / job_id
            artifacts_dir = job_dir / "artifacts"
            logs_dir = job_dir / "logs"
            job_dir.mkdir(parents=True, exist_ok=True)
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Create job execution
            job = JobExecution(
                job_id=job_id,
                workflow_name=workflow_name,
                correlation_id=correlation_id,
                input_params=input_params.copy(),
                started_at=datetime.now(timezone.utc).isoformat(),
                metadata={
                    "artifacts_dir": str(artifacts_dir),
                    "logs_dir": str(logs_dir)
                }
            )
            
            # Initialize workflow state
            job.state = create_initial_state(input_params.copy())
            job.state['execution_id'] = job_id
            job.state['correlation_id'] = correlation_id
            
            # Store job
            self._jobs[job_id] = job
            self._persist_job(job)
            
            # Initialize control events
            self._control_events[job_id] = asyncio.Event()
            self._pause_requests[job_id] = False
            self._cancel_requests[job_id] = False
            
            # Start execution in separate thread
            execution_thread = threading.Thread(
                target=self._execute_job_workflow,
                args=(job,),
                daemon=True
            )
            job.execution_thread = execution_thread
            execution_thread.start()
            
            # Update status
            self._update_job_status(job, JobStatus.RUNNING)
            
            logger.info(f"Started job: {job_id} for workflow: {workflow_name}")
            return job
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a running job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status != JobStatus.RUNNING:
                return False
            
            # Set pause request
            self._pause_requests[job_id] = True
            
            # Pause the workflow state
            if job.state:
                job.state['paused'] = True
            
            # Update status
            self._update_job_status(job, JobStatus.PAUSED)
            
            logger.info(f"Paused job: {job_id}")
            return True
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status != JobStatus.PAUSED:
                return False
            
            # Clear pause request
            self._pause_requests[job_id] = False
            
            # Resume the workflow state
            if job.state:
                job.state['paused'] = False
            
            # Signal control event
            if job_id in self._control_events:
                self._control_events[job_id].set()
            
            # Update status
            self._update_job_status(job, JobStatus.RUNNING)
            
            logger.info(f"Resumed job: {job_id}")
            return True
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job execution."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return False
            
            # Set cancel request
            self._cancel_requests[job_id] = True
            
            # Signal control event to wake up execution
            if job_id in self._control_events:
                self._control_events[job_id].set()
            
            # Update status
            self._update_job_status(job, JobStatus.CANCELLED)
            job.completed_at = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Cancelled job: {job_id}")
            return True
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current job status."""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.to_dict() if job else None
    
    def list_jobs(self, status_filter: Optional[JobStatus] = None) -> List[Dict[str, Any]]:
        """List jobs with optional status filter."""
        with self._lock:
            jobs = []
            for job in self._jobs.values():
                if status_filter is None or job.status == status_filter:
                    jobs.append(job.to_dict())
            return jobs
    
    def get_job_logs(self, job_id: str) -> List[Dict[str, Any]]:
        """Get execution logs for a job."""
        # In a real implementation, this would return structured logs
        # For now, return basic checkpoint history
        return self.checkpoint_manager.get_checkpoint_history(f"exec_{job_id}")
    
    def update_job_parameters(self, job_id: str, parameters: Dict[str, Any]) -> bool:
        """Update job parameters during execution."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status not in [JobStatus.RUNNING, JobStatus.PAUSED]:
                return False
            
            # Update job parameters
            job.input_params.update(parameters)
            
            # Update workflow state
            if job.state:
                data = job.state.get('data', {}).copy()
                data.update(parameters)
                job.state['data'] = data
            
            job.metadata["parameter_updates"] = job.metadata.get("parameter_updates", [])
            job.metadata["parameter_updates"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "parameters": parameters.copy()
            })
            
            self._persist_job(job)
            
            logger.info(f"Updated parameters for job: {job_id}")
            return True
    
    def _execute_job_workflow(self, job: JobExecution):
        """Execute workflow for a job in a separate thread."""
        log_file = None
        try:
            # Setup log file
            job_dir = self.storage_dir / job.job_id
            logs_dir = job_dir / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_file = logs_dir / "job.log"
            
            with open(log_file, 'a') as log:
                log.write(f"[{datetime.now().isoformat()}] Starting workflow: {job.workflow_name}\n")
                log.write(f"[{datetime.now().isoformat()}] Topic: {job.input_params.get('topic', 'N/A')}\n")
            
            # Compile workflow
            compiled_workflow = self.workflow_compiler.compile_workflow(job.workflow_name)
            
            # Create checkpoint execution
            checkpoint_execution = self.checkpoint_manager.start_workflow_execution(
                correlation_id=job.correlation_id,
                workflow_name=job.workflow_name,
                initial_data=job.input_params
            )
            
            # Execute workflow with control checks
            config = {"configurable": {"thread_id": job.job_id}}
            
            # Stream execution to handle pause/resume
            step_count = 0
            for chunk in compiled_workflow.stream(job.state, config=config):
                # Check for control requests
                if self._check_control_requests(job):
                    break
                
                # Log step progress
                if log_file and job.state and job.state.get('current_step'):
                    step_count += 1
                    with open(log_file, 'a') as log:
                        log.write(f"[{datetime.now().isoformat()}] Step {step_count}: {job.state.get('current_step')}\n")
                
                # Update progress
                self._update_job_progress(job, chunk)
            
            # Check final status
            if not self._cancel_requests.get(job.job_id, False):
                if job.state and not job.state.get('error'):
                    self._update_job_status(job, JobStatus.COMPLETED)
                    job.output_data = job.state.get('step_outputs', {}).copy()
                    
                    # Create artifacts from workflow outputs
                    try:
                        job_dir = self.storage_dir / job.job_id
                        artifacts_dir = job_dir / "artifacts"
                        artifacts_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Also create artifacts in the configured output directory
                        output_dir = Path(job.input_params.get('output_dir', './output'))
                        output_dir.mkdir(parents=True, exist_ok=True)
                        
                        topic = job.input_params.get('topic', 'Generated_Content')
                        
                        # Handle topic as dict or string and get safe filename
                        if isinstance(topic, dict):
                            title = topic.get('title', 'Generated_Content')
                            # Sanitize title for filename
                            safe_topic = title.replace(' ', '_').replace('/', '_').replace(':', '_').replace('\\', '_')
                            safe_topic = ''.join(c for c in safe_topic if c.isalnum() or c in ('_', '-'))[:50]
                            if not safe_topic:
                                safe_topic = 'Generated_Content'
                        else:
                            safe_topic = str(topic).replace(' ', '_').replace('/', '_').replace(':', '_').replace('\\', '_')
                            safe_topic = ''.join(c for c in safe_topic if c.isalnum() or c in ('_', '-'))[:50]
                            if not safe_topic:
                                safe_topic = 'Generated_Content'
                        
                        # Check if there's actual content to save
                        content_saved = False
                        
                        # Look for content in step outputs
                        for step_id, step_output in job.state.get('step_outputs', {}).items():
                            if isinstance(step_output, dict):
                                # Check for markdown content
                                if 'content' in step_output and isinstance(step_output['content'], str):
                                    # Save to artifacts directory
                                    artifact_file = artifacts_dir / f"{safe_topic}_output.md"
                                    with open(artifact_file, 'w') as f:
                                        f.write(step_output['content'])
                                    
                                    # Also save to output directory
                                    output_file = output_dir / f"{safe_topic}.md"
                                    with open(output_file, 'w') as f:
                                        f.write(step_output['content'])
                                    
                                    content_saved = True
                                    logger.info(f"Created artifact: {artifact_file.name} (also saved to {output_file})")
                                    break
                                
                                # Check for markdown field
                                elif 'markdown' in step_output and isinstance(step_output['markdown'], str):
                                    # Save to artifacts directory
                                    artifact_file = artifacts_dir / f"{safe_topic}_output.md"
                                    with open(artifact_file, 'w') as f:
                                        f.write(step_output['markdown'])
                                    
                                    # Also save to output directory
                                    output_file = output_dir / f"{safe_topic}.md"
                                    with open(output_file, 'w') as f:
                                        f.write(step_output['markdown'])
                                    
                                    content_saved = True
                                    logger.info(f"Created artifact: {artifact_file.name} (also saved to {output_file})")
                                    break
                        
                        # If no content found, create a summary artifact
                        if not content_saved:
                            summary_file = artifacts_dir / f"{safe_topic}_summary.json"
                            import json
                            with open(summary_file, 'w') as f:
                                json.dump({
                                    'job_id': job.job_id,
                                    'topic': topic,
                                    'workflow': job.workflow_name,
                                    'completed_at': datetime.now(timezone.utc).isoformat(),
                                    'steps_completed': list(job.state.get('step_outputs', {}).keys()),
                                    'note': 'Content artifacts would be generated by actual agent execution'
                                }, f, indent=2)
                            logger.info(f"Created summary artifact: {summary_file.name}")
                    
                    except Exception as e:
                        logger.error(f"Failed to create artifacts: {e}")
                    
                    # Log completion
                    if log_file:
                        with open(log_file, 'a') as log:
                            log.write(f"[{datetime.now().isoformat()}] Workflow completed successfully\n")
                else:
                    self._update_job_status(job, JobStatus.FAILED)
                    job.error_message = job.state.get('error') if job.state else "Unknown error"
                    
                    # Log failure
                    if log_file:
                        with open(log_file, 'a') as log:
                            log.write(f"[{datetime.now().isoformat()}] ERROR: {job.error_message}\n")
                
                job.completed_at = datetime.now(timezone.utc).isoformat()
            else:
                # Job was cancelled
                if log_file:
                    with open(log_file, 'a') as log:
                        log.write(f"[{datetime.now().isoformat()}] Job cancelled by user\n")
            
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
            total_steps = len(job.state.get('completed_steps', [])) + len(job.state.get('failed_steps', [])) + 1
            completed_steps = len(job.state.get('completed_steps', []))
            job.progress = min(1.0, completed_steps / total_steps) if total_steps > 0 else 0.0
            job.current_step = job.state.get('current_step')
            
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
            
        except Exception as e:
            logger.error(f"Failed to load persisted jobs: {e}")
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get execution engine statistics."""
        with self._lock:
            stats = {
                "total_jobs": len(self._jobs),
                "running_jobs": len([j for j in self._jobs.values() if j.status == JobStatus.RUNNING]),
                "paused_jobs": len([j for j in self._jobs.values() if j.status == JobStatus.PAUSED]),
                "completed_jobs": len([j for j in self._jobs.values() if j.status == JobStatus.COMPLETED]),
                "failed_jobs": len([j for j in self._jobs.values() if j.status == JobStatus.FAILED]),
                "cancelled_jobs": len([j for j in self._jobs.values() if j.status == JobStatus.CANCELLED]),
                "monitor_running": self._monitor_running,
                "registered_callbacks": {
                    "status": len(self._status_callbacks),
                    "progress": len(self._progress_callbacks)
                }
            }
            return stats
    
    def submit_batch(self, 
                    batch_config: List[Dict[str, Any]],
                    batch_group_id: str = None) -> List[str]:
        """Submit multiple jobs as a batch."""
        
        if batch_group_id is None:
            batch_group_id = f"batch-{uuid.uuid4()}"
        
        job_ids = []
        
        logger.info(f"Submitting batch {batch_group_id}: {len(batch_config)} jobs")
        
        for job_spec in batch_config:
            job_id = self.submit_job(
                workflow_name=job_spec['workflow'],
                input_params=job_spec.get('params', {})
            )
            
            # Associate with batch
            with self._lock:
                job = self._jobs.get(job_id)
                if job:
                    job.batch_group_id = batch_group_id
                    job_ids.append(job_id)
        
        logger.info(f"Batch {batch_group_id} submitted: {len(job_ids)} jobs")
        return job_ids
    
    def get_batch_status(self, batch_group_id: str) -> Dict[str, Any]:
        """Get status of all jobs in a batch."""
        with self._lock:
            batch_jobs = [
                job for job in self._jobs.values()
                if job.batch_group_id == batch_group_id
            ]
        
        if not batch_jobs:
            return {
                "batch_id": batch_group_id,
                "found": False,
                "total_jobs": 0
            }
        
        return {
            "batch_id": batch_group_id,
            "found": True,
            "total_jobs": len(batch_jobs),
            "completed": sum(1 for j in batch_jobs if j.status == JobStatus.COMPLETED),
            "failed": sum(1 for j in batch_jobs if j.status == JobStatus.FAILED),
            "running": sum(1 for j in batch_jobs if j.status == JobStatus.RUNNING),
            "paused": sum(1 for j in batch_jobs if j.status == JobStatus.PAUSED),
            "cancelled": sum(1 for j in batch_jobs if j.status == JobStatus.CANCELLED),
            "jobs": [j.to_dict() for j in batch_jobs]
        }