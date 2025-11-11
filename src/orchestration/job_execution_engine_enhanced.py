# src/orchestration/job_execution_engine_enhanced.py

"""Enhanced Job Execution Engine with graceful fallbacks, durable job persistence,
and zero-stacktrace failures when workflows are missing or empty."""

from __future__ import annotations

import threading
import uuid
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

logger = logging.getLogger(__name__)


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
            job_id=job_id,
            workflow_name=workflow_name,
            correlation_id=f"wf_{workflow_name}_{job_id[:8]}",
            status=JobStatus.PENDING,
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
