<<<<<<< Updated upstream
# src/orchestration/job_execution_engine_enhanced.py
=======
"""Async Job Execution Engine - Enhanced async version with better concurrency."""
>>>>>>> Stashed changes

"""Enhanced Job Execution Engine with graceful fallbacks, durable job persistence,
and zero-stacktrace failures when workflows are missing or empty."""

from __future__ import annotations

import threading
import uuid
<<<<<<< Updated upstream
import logging
import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Optional imports are wrapped where used:
# - src.engine.unified_engine (direct execution fallback)
# - production execution engine (if present)
=======
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

from src.core import EventBus, AgentEvent, Config

from .workflow_compiler import WorkflowCompiler
from .execution_plan import ExecutionPlan, ExecutionStep
from .job_state import JobState, JobMetadata, JobStatus, StepStatus, StepExecution
from .job_storage import JobStorage
from .enhanced_registry import EnhancedAgentRegistry
>>>>>>> Stashed changes

logger = logging.getLogger(__name__)


<<<<<<< Updated upstream
class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobExecution:
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
    error_details: Optional[str] = None
    execution_thread: Optional[threading.Thread] = None
    state: Optional[Any] = None  # reserved for engines that keep state
    metadata: Dict[str, Any] = field(default_factory=dict)
    batch_group_id: Optional[str] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
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
            "error_details": self.error_details,
            "metadata": self.metadata,
            "batch_group_id": self.batch_group_id,
            "logs": self.logs[-100:] if len(self.logs) > 100 else self.logs,
        }

    def add_log(self, level: str, message: str, details: Dict | None = None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "details": details or {},
        }
        self.logs.append(entry)
        jl = self.metadata.get("job_logger")
        if jl:
            log_fn = getattr(jl, level.lower(), jl.info)
            log_fn(message)


class JobExecutionEngineEnhanced:
    """Durably persists jobs and executes via:
       1) Production engine (if available)
       2) Workflow compiler (if available)
       3) Direct UnifiedEngine fallback (always available in this codebase)"""

    def __init__(self, workflow_compiler: Optional[Any], checkpoint_manager: Optional[Any],
                 verbose: bool = True, debug: bool = False):
        self.workflow_compiler = workflow_compiler
        self.checkpoint_manager = checkpoint_manager
        self.verbose = verbose
        self.debug = debug

        logger.setLevel(logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING))
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            h = logging.StreamHandler()
            h.setLevel(logger.level)
            h.setFormatter(logging.Formatter('[%(levelname)s] %(name)s: %(message)s'))
            logger.addHandler(h)

        self._jobs: Dict[str, JobExecution] = {}
        self._lock = threading.RLock()
        self._status_callbacks: List[Callable[[JobExecution], None]] = []
        self._progress_callbacks: List[Callable[[str, float, str], None]] = []

        # Persist under ./reports/jobs (telemetry, not user artifacts)
        self.storage_dir = Path("./reports/jobs")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Try to hold a Config if present (optional)
        self.config = None
        try:
            from src.core import Config   # type: ignore
            c = Config()
            c.load_from_env()
            self.config = c
            logger.info("[INIT] Engine config loaded")
        except Exception as e:
            logger.info(f"[INIT] Engine config not loaded: {e}")

        logger.info("[INIT] JobExecutionEngineEnhanced up")
        logger.info(f"       storage: {self.storage_dir}")

    # =========================
    # Job submission & execution
    # =========================

    def submit_job(self, workflow_name: str, input_params: Dict[str, Any], job_id: Optional[str] = None) -> str:
        job_id = job_id or str(uuid.uuid4())

        job_dir = self.storage_dir / job_id
        (job_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        (job_dir / "logs").mkdir(parents=True, exist_ok=True)

        # Per-job logger
        jl = logging.getLogger(f"job.{job_id[:8]}")
        jl.setLevel(logging.DEBUG)
        fh = logging.FileHandler(job_dir / "logs" / "job.log", mode="w", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        fh.setLevel(logging.DEBUG)
        jl.handlers.clear()
        jl.addHandler(fh)
        if self.verbose:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            ch.setFormatter(logging.Formatter(f"[JOB {job_id[:8]}] %(message)s"))
            jl.addHandler(ch)

        for line in [
            "=" * 80,
            "JOB EXECUTION LOG",
            "=" * 80,
            f"Job ID: {job_id}",
            f"Workflow: {workflow_name}",
            f"Started: {datetime.now(timezone.utc).isoformat()}",
            "Parameters:",
        ]:
            jl.info(line)
        for k, v in input_params.items():
            jl.info(f"  {k}: {v if isinstance(v, (str, int, float, bool)) else type(v).__name__}")
        jl.info("=" * 80)

        job = JobExecution(
=======
class AsyncJobExecutionEngine:
    """Async job execution engine with improved concurrency and performance."""
    
    def __init__(
        self,
        compiler: WorkflowCompiler,
        registry: EnhancedAgentRegistry,
        event_bus: Optional[EventBus] = None,
        config: Optional[Config] = None,
        max_concurrent_jobs: int = 5,
        storage_dir: Optional[Path] = None
    ):
        """Initialize async job execution engine.
        
        Args:
            compiler: WorkflowCompiler for creating execution plans
            registry: EnhancedAgentRegistry for agent management
            event_bus: Event bus for emitting job events
            config: Configuration object
            max_concurrent_jobs: Maximum concurrent job executions
            storage_dir: Directory for job persistence
        """
        self.compiler = compiler
        self.registry = registry
        self.event_bus = event_bus or EventBus()
        self.config = config or Config()
        self.max_concurrent_jobs = max_concurrent_jobs
        
        # Storage
        self.storage = JobStorage(base_dir=storage_dir)
        
        # Job tracking
        self._jobs: Dict[str, JobState] = {}
        self._lock = asyncio.Lock()
        
        # Job queue
        self._job_queue: asyncio.Queue = asyncio.Queue()
        self._pending_jobs: Set[str] = set()
        
        # Control events
        self._pause_events: Dict[str, asyncio.Event] = {}
        self._cancel_events: Dict[str, asyncio.Event] = {}
        
        # Worker tasks
        self._worker_tasks: List[asyncio.Task] = []
        self._running = False
    
    async def start(self) -> None:
        """Start the async execution engine."""
        if self._running:
            logger.warning("Engine already running")
            return
        
        self._running = True
        
        # Load persisted jobs
        await self._load_persisted_jobs()
        
        # Start worker tasks
        for i in range(self.max_concurrent_jobs):
            task = asyncio.create_task(
                self._worker_loop(),
                name=f"AsyncJobWorker-{i}"
            )
            self._worker_tasks.append(task)
        
        logger.info(f"Started {self.max_concurrent_jobs} async job workers")
    
    async def stop(self, timeout: float = 30.0) -> None:
        """Stop the execution engine.
        
        Args:
            timeout: Timeout for waiting for workers to finish
        """
        logger.info("Stopping async job execution engine...")
        self._running = False
        
        # Cancel all worker tasks
        for task in self._worker_tasks:
            task.cancel()
        
        # Wait for tasks to finish
        if self._worker_tasks:
            await asyncio.wait(self._worker_tasks, timeout=timeout)
        
        self._worker_tasks.clear()
        logger.info("Async job execution engine stopped")
    
    async def _load_persisted_jobs(self) -> None:
        """Load persisted jobs from storage."""
        try:
            jobs = self.storage.list_jobs()
            for metadata in jobs:
                job_state = self.storage.load_job(metadata.job_id)
                if job_state:
                    async with self._lock:
                        self._jobs[metadata.job_id] = job_state
                    
                    # Re-queue pending jobs
                    if metadata.status == JobStatus.PENDING:
                        self._pending_jobs.add(metadata.job_id)
                        await self._job_queue.put(metadata.job_id)
            
            logger.info(f"Loaded {len(jobs)} persisted jobs")
            
        except Exception as e:
            logger.error(f"Failed to load persisted jobs: {e}")
    
    async def _worker_loop(self) -> None:
        """Worker coroutine main loop."""
        while self._running:
            try:
                # Get job from queue
                try:
                    job_id = await asyncio.wait_for(
                        self._job_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Remove from pending set
                async with self._lock:
                    self._pending_jobs.discard(job_id)
                
                # Execute job
                try:
                    await self._execute_job(job_id)
                except Exception as e:
                    logger.error(f"Error executing job {job_id}: {e}", exc_info=True)
                    await self._mark_job_failed(job_id, str(e))
                finally:
                    self._job_queue.task_done()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
    
    async def submit_job(
        self,
        workflow_id: str,
        inputs: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> str:
        """Submit a new job for execution.
        
        Args:
            workflow_id: Workflow identifier
            inputs: Input parameters
            correlation_id: Optional correlation ID
            
        Returns:
            Job ID
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
>>>>>>> Stashed changes
            job_id=job_id,
            workflow_name=workflow_name,
            correlation_id=f"wf_{workflow_name}_{job_id[:8]}",
            status=JobStatus.PENDING,
<<<<<<< Updated upstream
            started_at=datetime.now(timezone.utc).isoformat(),
            input_params=input_params,
            metadata={
                "artifacts_dir": str(job_dir / "artifacts"),
                "logs_dir": str(job_dir / "logs"),
                "log_file": str(job_dir / "logs" / "job.log"),
                "job_logger": jl,
            },
        )
        job.add_log("INFO", "Job created", {"workflow": workflow_name})

        # Resolve workflow (profiles / direct / fallback)
        workflow_def = self._resolve_workflow_definition(workflow_name)
        pipeline = self._pipeline_from_workflow(workflow_def)
        job.metadata["workflow_def"] = workflow_def
        job.metadata["pipeline"] = pipeline

        jl.info(f"Pipeline has {len(pipeline)} steps")
        for step in pipeline:
            jl.debug(f"  - {step['id']}: {step['name']} ({step['agent']})")

        with self._lock:
            self._jobs[job_id] = job
        self._persist_job(job)

        # Execute in background
        t = threading.Thread(target=self._execute_job, args=(job,), daemon=True, name=f"job-{job_id[:8]}")
        job.execution_thread = t
        t.start()

        logger.info(f"[JOB QUEUED] Job {job_id} submitted successfully")
        return job_id

    # =========================
    # Internal helpers
    # =========================

    def _resolve_workflow_definition(self, workflow_name: str) -> Dict[str, Any]:
        """Try multiple sources. If nothing found, synthesize a minimal, valid pipeline."""
        # 1) Attempt via workflow_compiler (dict-like)
        try:
            if self.workflow_compiler and hasattr(self.workflow_compiler, "workflows"):
                wf = self.workflow_compiler.workflows
                # profiles container
                profiles = wf.get("profiles") if isinstance(wf, dict) else None
                if isinstance(profiles, dict) and workflow_name in profiles:
                    return profiles[workflow_name]
                # direct key
                if isinstance(wf, dict) and workflow_name in wf:
                    return wf[workflow_name]
        except Exception as e:
            logger.debug(f"workflow_compiler lookup failed: {e}")

        # 2) Look for a template and synthesize steps
        template_kind = None
        try:
            from src.core.template_registry import get_template_registry  # type: ignore
            reg = get_template_registry()
            tmpl = reg.get_template(workflow_name)
            if tmpl:
                template_kind = getattr(tmpl, "type", None)
        except Exception:
            pass

        steps: Dict[str, Dict[str, Any]] = {}

        # Minimal deterministic pipeline; agents must exist in your mesh
        # You can adjust agent names if your codebase uses different ones.
        steps["ingest"] = {"name": "Ingest", "agent": "kb_ingestion"}
        steps["plan"] = {"name": "Plan", "agent": "content_planner"}
        steps["generate"] = {"name": "Generate", "agent": "content_generator"}
        steps["validate"] = {"name": "Validate", "agent": "validator"}
        steps["persist"] = {"name": "Persist", "agent": "artifact_persist"}

        return {"name": workflow_name, "steps": steps, "synthesized": True, "template_kind": str(template_kind or "")}

    def _pipeline_from_workflow(self, workflow_def: Dict[str, Any]) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        steps = workflow_def.get("steps", {})
        # Steps may be dict or list; normalize to list of dicts with id/name/agent
        if isinstance(steps, dict):
            for sid, scfg in steps.items():
                if isinstance(scfg, dict):
                    out.append({"id": sid, "name": scfg.get("name", sid), "agent": scfg.get("agent", sid), "status": "pending"})
        elif isinstance(steps, list):
            for i, scfg in enumerate(steps, 1):
                if isinstance(scfg, dict):
                    sid = scfg.get("id") or scfg.get("name") or f"step_{i}"
                    out.append({"id": sid, "name": scfg.get("name", sid), "agent": scfg.get("agent", sid), "status": "pending"})
        return out

    def _execute_job(self, job: JobExecution):
        jl: logging.Logger = job.metadata.get("job_logger")  # type: ignore
        try:
            job.status = JobStatus.RUNNING
            job.current_step = "Initializing"
            job.progress = 5.0
            job.add_log("INFO", "Job execution started")
            self._persist_job(job)
            self._notify_status_change(job)

            pipeline: List[Dict[str, str]] = job.metadata.get("pipeline", [])
            if not pipeline:
                # Absolute last resort (should never happen—_resolve_workflow_definition builds one)
                msg = f"Workflow '{job.workflow_name}' has no steps defined"
                jl.warning(msg)
                job.add_log("WARNING", msg)
                self._finish_as_failed(job, msg, trace=None)
                return

            # Prefer production engine if available
            used_engine = "direct"
            results = None
            try:
                from .production_execution_engine import ProductionExecutionEngine  # type: ignore
                prod = ProductionExecutionEngine(self.config)
                used_engine = "production"
                jl.info("Production execution engine loaded")
                # Adapt minimal structure for production engine
                steps_list = [{"id": s["id"], "agent": s["agent"], "name": s["name"]} for s in pipeline]

                def progress_cb(pct: float, msg: str):
                    job.progress = pct
                    job.current_step = msg
                    job.add_log("INFO", f"{pct:.1f}% - {msg}")
                    self._persist_job(job)
                    self._notify_progress(job.job_id, pct, msg)

                def checkpoint_cb(agent_type: str, data: Dict[str, Any]):
                    job.add_log("INFO", f"Checkpoint: {agent_type}", data)
                    for s in job.metadata.get("pipeline", []):
                        if s["agent"] == agent_type and s.get("status") == "pending":
                            s["status"] = "completed"
                            break

                results = prod.execute_pipeline(
                    workflow_name=job.workflow_name,
                    steps=steps_list,
                    input_data=job.input_params,
                    job_id=job.job_id,
                    progress_callback=progress_cb,
                    checkpoint_callback=checkpoint_cb,
                )

            except Exception as e_prod:
                jl.info(f"Production engine unavailable: {e_prod}")
                # Try workflow compiler if present
                if self.workflow_compiler and hasattr(self.workflow_compiler, "compile_and_execute"):
                    try:
                        used_engine = "compiler"
                        job.current_step = "Compiling workflow"
                        job.progress = 20.0
                        self._persist_job(job)
                        results = self.workflow_compiler.compile_and_execute(
                            workflow_definition=job.metadata.get("workflow_def", {}),
                            input_data=job.input_params,
                            correlation_id=job.correlation_id,
                        )
                    except Exception as e_comp:
                        jl.info(f"Workflow compiler unavailable: {e_comp}")
                        results = self._direct_unified_engine(job, jl)
                        used_engine = "direct"
                else:
                    results = self._direct_unified_engine(job, jl)
                    used_engine = "direct"

            job.add_log("INFO", f"Used engine: {used_engine}")

            # Persist artifacts & results
            job.current_step = "Processing results"
            job.progress = max(job.progress, 80.0)
            self._persist_results(job, results, jl)

            job.status = JobStatus.COMPLETED
            job.current_step = "Completed"
            job.progress = 100.0
            job.completed_at = datetime.now(timezone.utc).isoformat()
            jl.info("[SUCCESS] Job completed successfully")
            job.add_log("INFO", "Job completed successfully")

        except Exception as e:
            # keep console clean; write trace to file
            trace = traceback.format_exc()
            self._finish_as_failed(job, str(e), trace=trace, write_trace=True)
            jl.error(f"[FAILURE] Job execution failed: {e}")
        finally:
            # Drop logger reference before persisting to avoid serialization issues
            if "job_logger" in job.metadata:
                del job.metadata["job_logger"]
            self._persist_job(job)
            self._notify_status_change(job)
            logger.info(f"[JOB END] Job {job.job_id} finished with status: {job.status.value}")

    def _direct_unified_engine(self, job: JobExecution, jl: logging.Logger):
        """Execute via UnifiedEngine directly — always available in this codebase."""
        try:
            from src.engine.unified_engine import get_engine, RunSpec  # type: ignore
        except Exception as e:
            jl.warning(f"Unified engine import failed: {e}")
            return {}

        run_spec = RunSpec(
            topic=job.input_params.get("topic"),
            template_name=job.input_params.get("template_name") or job.workflow_name,
            auto_topic=bool(job.input_params.get("auto_topic")),
            kb_path=job.input_params.get("kb_path"),
            docs_path=job.input_params.get("docs_path"),
            blog_path=job.input_params.get("blog_path"),
            api_path=job.input_params.get("api_path"),
            tutorial_path=job.input_params.get("tutorial_path"),
            output_dir=Path(job.input_params.get("output_dir") or "./output"),
        )

        jl.info("Executing via UnifiedEngine fallback")
        eng = get_engine()
        res = eng.generate_job(run_spec)

        # Normalize a dict for persistence
        out: Dict[str, Any] = {
            "status": getattr(res, "status", None).value if getattr(res, "status", None) else "completed",
            "assembled_content": getattr(res, "assembled_content", ""),
            "output_path": str(getattr(res, "output_path", "") or ""),
            "manifest_path": str(getattr(res, "manifest_path", "") or ""),
            "pipeline_order": getattr(res, "pipeline_order", []),
            "duration": getattr(res, "duration", 0),
            "error": getattr(res, "error", None),
        }
        return out

    def _persist_results(self, job: JobExecution, results: Any, jl: logging.Logger):
        job_dir = Path(self.storage_dir, job.job_id)
        artifacts_dir = job_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        if isinstance(results, dict):
            job.output_data = results
            # content
            content = results.get("assembled_content")
            if content:
                file_md = artifacts_dir / "output.md"
                file_md.write_text(content, encoding="utf-8")
                jl.info(f"Saved artifact: {file_md}")
                job.metadata["artifact_path"] = str(file_md)

            # output file path if exposed by unified engine
            out_path = results.get("output_path")
            if out_path:
                job.metadata["output_path"] = out_path

            # save results json
            (artifacts_dir / "results.json").write_text(json.dumps(self._make_serializable(results), indent=2), encoding="utf-8")
            jl.info(f"Saved results: {(artifacts_dir / 'results.json')}")

    def _finish_as_failed(self, job: JobExecution, message: str, trace: Optional[str], write_trace: bool = False):
        jl: logging.Logger = job.metadata.get("job_logger")  # type: ignore
        job.status = JobStatus.FAILED
        job.error_message = message
        job.error_details = None  # we store traceback in file if requested
        job.completed_at = datetime.now(timezone.utc).isoformat()
        job.progress = max(job.progress, 100.0)
        job.current_step = "Failed"
        job.add_log("ERROR", f"Job failed: {message}")

        if write_trace and trace:
            trace_path = Path(job.metadata.get("logs_dir", ".")) / "traceback.log"
            try:
                trace_path.write_text(trace, encoding="utf-8")
                jl.error(f"Trace written to {trace_path}")
            except Exception:
                pass

    # =========================
    # Persistence & callbacks
    # =========================

    def _make_serializable(self, obj: Any) -> Any:
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._make_serializable(x) for x in obj]
        if hasattr(obj, "to_dict"):
            try:
                return obj.to_dict()
            except Exception:
                return str(obj)
        return obj

    def _persist_job(self, job: JobExecution):
        job_file = self.storage_dir / job.job_id / "job.json"
        try:
            jf = job.to_dict()
            job_file.write_text(json.dumps(jf, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to persist job {job.job_id}: {e}")

    def _load_job(self, job_id: str) -> Optional[JobExecution]:
        job_file = self.storage_dir / job_id / "job.json"
        if not job_file.exists():
            return None
        try:
            data = json.loads(job_file.read_text(encoding="utf-8"))
            j = JobExecution(job_id=data["job_id"], workflow_name=data["workflow_name"], correlation_id=data["correlation_id"])
            j.status = JobStatus(data.get("status", "pending"))
            j.started_at = data.get("started_at")
            j.completed_at = data.get("completed_at")
            j.current_step = data.get("current_step")
            j.progress = data.get("progress", 0.0)
            j.input_params = data.get("input_params", {})
            j.output_data = data.get("output_data", {})
            j.error_message = data.get("error_message")
            j.error_details = data.get("error_details")
            j.metadata = data.get("metadata", {})
            j.logs = data.get("logs", [])
            return j
        except Exception as e:
            logger.error(f"Failed to load job {job_id}: {e}")
            return None

    def load_persisted_jobs(self):
        loaded = 0
        for d in self.storage_dir.iterdir():
            if d.is_dir():
                j = self._load_job(d.name)
                if j:
                    with self._lock:
                        self._jobs[j.job_id] = j
                    loaded += 1
        logger.info(f"Loaded {loaded} persisted jobs from {self.storage_dir}")

    def register_status_callback(self, cb: Callable[[JobExecution], None]):
        with self._lock:
            self._status_callbacks.append(cb)

    def register_progress_callback(self, cb: Callable[[str, float, str], None]):
        with self._lock:
            self._progress_callbacks.append(cb)

    def _notify_status_change(self, job: JobExecution):
        for cb in self._status_callbacks:
            try:
                cb(job)
            except Exception as e:
                logger.debug(f"status callback failed: {e}")

    def _notify_progress(self, job_id: str, progress: float, step: str):
        for cb in self._progress_callbacks:
            try:
                cb(job_id, progress, step)
            except Exception as e:
                logger.debug(f"progress callback failed: {e}")

    # =========================
    # Public getters/actions
    # =========================

    def get_job(self, job_id: str) -> Optional[JobExecution]:
        with self._lock:
            return self._jobs.get(job_id)

    def get_all_jobs(self) -> List[JobExecution]:
        with self._lock:
            return list(self._jobs.values())

    def get_job_logs(self, job_id: str) -> Optional[str]:
        j = self.get_job(job_id)
        if not j:
            return None
        fp = Path(j.metadata.get("log_file", ""))
        if fp.exists():
            return fp.read_text(encoding="utf-8")
        return None


# Singleton accessor
_engine_instance: Optional[JobExecutionEngineEnhanced] = None


def get_enhanced_engine(workflow_compiler=None, checkpoint_manager=None,
                        verbose: bool = True, debug: bool = False) -> JobExecutionEngineEnhanced:
    global _engine_instance
    if _engine_instance is None:
        if workflow_compiler is None or checkpoint_manager is None:
            raise ValueError("workflow_compiler and checkpoint_manager required for first initialization")
        _engine_instance = JobExecutionEngineEnhanced(workflow_compiler, checkpoint_manager, verbose=verbose, debug=debug)
        _engine_instance.load_persisted_jobs()
    return _engine_instance
=======
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
        
        # Initialize steps
        for step in plan.steps:
            job_state.steps[step.agent_id] = StepExecution(agent_id=step.agent_id)
        
        # Store job
        async with self._lock:
            self._jobs[job_id] = job_state
            self._pending_jobs.add(job_id)
        
        # Persist
        self.storage.save_job(job_state)
        
        # Emit event
        self.event_bus.publish(AgentEvent(
            event_type="JobSubmitted",
            source_agent="AsyncJobExecutionEngine",
            correlation_id=job_state.metadata.correlation_id if "job_state" in locals() else job_id,
            data={
                'job_id': job_id,
                'workflow_id': workflow_id,
                'correlation_id': metadata.correlation_id
            }
        ))
        
        # Queue
        await self._job_queue.put(job_id)
        
        logger.info(f"Submitted async job {job_id} for workflow {workflow_id}")
        
        return job_id
    
    async def _execute_job(self, job_id: str) -> None:
        """Execute a job asynchronously.
        
        Args:
            job_id: Job identifier
        """
        async with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                logger.error(f"Job {job_id} not found")
                return
            
            # Mark as running
            job_state.metadata.status = JobStatus.RUNNING
            job_state.metadata.started_at = datetime.now()
            
            # Create control events
            self._pause_events[job_id] = asyncio.Event()
            self._cancel_events[job_id] = asyncio.Event()
        
        # Save state
        self.storage.save_job(job_state)
        
        # Emit event
        self.event_bus.publish(AgentEvent(
            event_type="JobStarted",
            source_agent="AsyncJobExecutionEngine",
            correlation_id=job_state.metadata.correlation_id if "job_state" in locals() else job_id,
            data={
                'job_id': job_id,
                'workflow_id': job_state.metadata.workflow_id
            }
        ))
        
        logger.info(f"Started executing async job {job_id}")
        
        try:
            # Get execution plan
            plan_dict = job_state.context.get('execution_plan', {})
            plan = ExecutionPlan.from_dict(plan_dict)
            
            # Execute steps
            completed_steps = set()
            
            for step in plan.steps:
                # Check for pause
                if self._pause_events[job_id].is_set():
                    logger.info(f"Job {job_id} paused")
                    await self._mark_job_paused(job_id)
                    return
                
                # Check for cancel
                if self._cancel_events[job_id].is_set():
                    logger.info(f"Job {job_id} cancelled")
                    await self._mark_job_cancelled(job_id)
                    return
                
                # Check dependencies
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
                success = await self._execute_step(job_id, job_state, step)
                
                if success:
                    completed_steps.add(step.agent_id)
                else:
                    if step.metadata.get('critical', False):
                        logger.error(f"Critical step {step.agent_id} failed")
                        await self._mark_job_failed(job_id, f"Critical step {step.agent_id} failed")
                        return
                    else:
                        logger.warning(f"Non-critical step {step.agent_id} failed, continuing")
                        completed_steps.add(step.agent_id)
                
                # Save state
                self.storage.save_job(job_state)
            
            # Mark completed
            await self._mark_job_completed(job_id)
            
        except Exception as e:
            logger.error(f"Job {job_id} execution failed: {e}", exc_info=True)
            await self._mark_job_failed(job_id, str(e))
        finally:
            # Cleanup control events
            async with self._lock:
                self._pause_events.pop(job_id, None)
                self._cancel_events.pop(job_id, None)
    
    async def _execute_step(
        self,
        job_id: str,
        job_state: JobState,
        step: ExecutionStep
    ) -> bool:
        """Execute a single step asynchronously.
        
        Args:
            job_id: Job identifier
            job_state: Job state
            step: Step to execute
            
        Returns:
            True if successful
        """
        agent_id = step.agent_id
        
        # Mark started
        job_state.mark_step_started(agent_id)
        
        # Emit event
        self.event_bus.publish(AgentEvent(
            event_type="StepStarted",
            source_agent=agent_id,
            correlation_id=job_state.metadata.correlation_id if "job_state" in locals() else job_id,
            data={'job_id': job_id, 'agent_id': agent_id}
        ))
        
        logger.info(f"Executing async step {agent_id} for job {job_id}")
        
        try:
            # Get agent
            agent = self.registry.get_agent(
                agent_id,
                config=self.config,
                event_bus=self.event_bus
            )
            
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            # Prepare inputs
            agent_inputs = self._prepare_agent_inputs(job_state, step)
            
            # Execute
            start_time = asyncio.get_event_loop().time()
            
            try:
                # Call agent (sync for now, can be made async)
                if hasattr(agent, 'run'):
                    result = agent.run(**agent_inputs)
                elif hasattr(agent, 'execute'):
                    result = agent.execute(**agent_inputs)
                else:
                    raise AttributeError(f"Agent {agent_id} has no run() or execute() method")
                
                elapsed = asyncio.get_event_loop().time() - start_time
                
                # Check timeout
                if step.timeout > 0 and elapsed > step.timeout:
                    raise TimeoutError(f"Step exceeded timeout of {step.timeout}s")
                
                # Store result
                if isinstance(result, dict):
                    job_state.outputs.update(result)
                else:
                    job_state.outputs[agent_id] = result
                
                # Mark completed
                job_state.mark_step_completed(
                    agent_id,
                    result if isinstance(result, dict) else {'result': result}
                )
                
                # Emit event
                self.event_bus.publish(AgentEvent(
                    event_type="StepCompleted",
                    source_agent=agent_id,
                    correlation_id=job_state.metadata.correlation_id if "job_state" in locals() else job_id,
                    data={'job_id': job_id, 'agent_id': agent_id, 'duration': elapsed}
                ))
                
                logger.info(f"Async step {agent_id} completed in {elapsed:.2f}s")
                
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
                correlation_id=job_state.metadata.correlation_id if "job_state" in locals() else job_id,
                data={'job_id': job_id, 'agent_id': agent_id, 'error': str(e)}
            ))
            
            # Retry logic
            step_execution = job_state.steps.get(agent_id)
            if step_execution and step_execution.retry_count < step.retry:
                logger.info(f"Retrying step {agent_id} (attempt {step_execution.retry_count + 1}/{step.retry})")
                step_execution.retry_count += 1
                step_execution.status = StepStatus.PENDING
                return await self._execute_step(job_id, job_state, step)
            
            return False
    
    def _prepare_agent_inputs(
        self,
        job_state: JobState,
        step: ExecutionStep
    ) -> Dict[str, Any]:
        """Prepare agent inputs."""
        inputs = {
            'config': self.config,
            **job_state.inputs,
            **job_state.outputs
        }
        
        inputs['_job_id'] = job_state.metadata.job_id
        inputs['_workflow_id'] = job_state.metadata.workflow_id
        inputs['_agent_id'] = step.agent_id
        
        return inputs
    
    async def _mark_job_completed(self, job_id: str) -> None:
        """Mark job as completed."""
        async with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                return
            
            job_state.metadata.status = JobStatus.COMPLETED
            job_state.metadata.completed_at = datetime.now()
            job_state.metadata.progress = 1.0
        
        self.storage.save_job(job_state)
        
        self.event_bus.publish(AgentEvent(
            event_type="JobCompleted",
            source_agent="AsyncJobExecutionEngine",
            correlation_id=job_state.metadata.correlation_id if "job_state" in locals() else job_id,
            data={
                'job_id': job_id,
                'workflow_id': job_state.metadata.workflow_id,
                'duration': (
                    job_state.metadata.completed_at - job_state.metadata.started_at
                ).total_seconds() if job_state.metadata.started_at else 0
            }
        ))
        
        logger.info(f"Async job {job_id} completed")
    
    async def _mark_job_failed(self, job_id: str, error: str) -> None:
        """Mark job as failed."""
        async with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                return
            
            job_state.metadata.status = JobStatus.FAILED
            job_state.metadata.completed_at = datetime.now()
            job_state.metadata.error_message = error
        
        self.storage.save_job(job_state)
        
        self.event_bus.publish(AgentEvent(
            event_type="JobFailed",
            source_agent="AsyncJobExecutionEngine",
            correlation_id=job_state.metadata.correlation_id if "job_state" in locals() else job_id,
            data={
                'job_id': job_id,
                'workflow_id': job_state.metadata.workflow_id,
                'error': error
            }
        ))
        
        logger.error(f"Async job {job_id} failed: {error}")
    
    async def _mark_job_cancelled(self, job_id: str) -> None:
        """Mark job as cancelled."""
        async with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                return
            
            job_state.metadata.status = JobStatus.CANCELLED
            job_state.metadata.completed_at = datetime.now()
        
        self.storage.save_job(job_state)
        
        self.event_bus.publish(AgentEvent(
            event_type="JobCancelled",
            source_agent="AsyncJobExecutionEngine",
            correlation_id=job_state.metadata.correlation_id if "job_state" in locals() else job_id,
            data={'job_id': job_id, 'workflow_id': job_state.metadata.workflow_id}
        ))
        
        logger.info(f"Async job {job_id} cancelled")
    
    async def _mark_job_paused(self, job_id: str) -> None:
        """Mark job as paused."""
        async with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                return
            
            job_state.metadata.status = JobStatus.PAUSED
        
        self.storage.save_job(job_state)
        logger.info(f"Async job {job_id} paused")
    
    async def get_job_status(self, job_id: str) -> Optional[JobMetadata]:
        """Get job status."""
        async with self._lock:
            job_state = self._jobs.get(job_id)
            if job_state:
                return job_state.metadata
        
        job_state = self.storage.load_job(job_id)
        if job_state:
            async with self._lock:
                self._jobs[job_id] = job_state
            return job_state.metadata
        
        return None
    
    async def pause_job(self, job_id: str) -> bool:
        """Pause a job."""
        async with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                return False
            
            if job_state.metadata.status != JobStatus.RUNNING:
                return False
            
            # Set pause event
            if job_id in self._pause_events:
                self._pause_events[job_id].set()
                return True
        
        return False
    
    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        async with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                return False
            
            if job_state.metadata.status != JobStatus.PAUSED:
                return False
            
            job_state.metadata.status = JobStatus.PENDING
            self._pending_jobs.add(job_id)
        
        self.storage.save_job(job_state)
        await self._job_queue.put(job_id)
        
        logger.info(f"Resumed async job {job_id}")
        return True
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        async with self._lock:
            job_state = self._jobs.get(job_id)
            if not job_state:
                return False
            
            if job_state.metadata.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return False
            
            if job_state.metadata.status == JobStatus.PENDING:
                self._pending_jobs.discard(job_id)
                await self._mark_job_cancelled(job_id)
                return True
            
            # Set cancel event
            if job_id in self._cancel_events:
                self._cancel_events[job_id].set()
                return True
        
        return False
    
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: Optional[int] = None
    ) -> List[JobMetadata]:
        """List jobs."""
        return self.storage.list_jobs(status=status, limit=limit)
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job."""
        async with self._lock:
            self._jobs.pop(job_id, None)
            self._pending_jobs.discard(job_id)
            self._pause_events.pop(job_id, None)
            self._cancel_events.pop(job_id, None)
        
        return self.storage.delete_job(job_id)
    
    async def get_engine_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        async with self._lock:
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
            'worker_tasks': len(self._worker_tasks),
            'jobs_in_memory': len(self._jobs),
            'pending_jobs': pending_count,
            'running_jobs': running_count,
            'paused_jobs': paused_count,
            'queue_size': self._job_queue.qsize(),
            'storage': storage_stats
        }
>>>>>>> Stashed changes
