# src/web/dependencies.py
"""Dependency injection for FastAPI routes."""

from typing import Optional
from functools import lru_cache

from src.core import Config
from src.orchestration.job_execution_engine import JobExecutionEngine
from src.orchestration.workflow_compiler import WorkflowCompiler
from src.orchestration.checkpoint_manager import CheckpointManager


# Global instances (initialized once)
_config: Optional[Config] = None
_job_engine: Optional[JobExecutionEngine] = None
_workflow_compiler: Optional[WorkflowCompiler] = None
_checkpoint_manager: Optional[CheckpointManager] = None


def initialize_services():
    """Initialize global service instances."""
    global _config, _job_engine, _workflow_compiler, _checkpoint_manager
    
    if _config is None:
        _config = Config()
        try:
            _config.load_from_env()
        except Exception:
            pass  # Use defaults
    
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    
    if _workflow_compiler is None:
        try:
            _workflow_compiler = WorkflowCompiler()
        except Exception:
            _workflow_compiler = None
    
    if _job_engine is None and _workflow_compiler is not None and _checkpoint_manager is not None:
        try:
            _job_engine = JobExecutionEngine(_workflow_compiler, _checkpoint_manager)
            # Set config reference
            _job_engine.config = _config
        except Exception:
            _job_engine = None


@lru_cache()
def get_config() -> Config:
    """Get configuration instance (dependency)."""
    if _config is None:
        initialize_services()
    return _config


def get_job_engine() -> JobExecutionEngine:
    """Get job execution engine (dependency)."""
    if _job_engine is None:
        initialize_services()
    if _job_engine is None:
        raise RuntimeError("Job execution engine not available")
    return _job_engine


def get_workflow_compiler() -> WorkflowCompiler:
    """Get workflow compiler (dependency)."""
    if _workflow_compiler is None:
        initialize_services()
    if _workflow_compiler is None:
        raise RuntimeError("Workflow compiler not available")
    return _workflow_compiler


def get_checkpoint_manager() -> CheckpointManager:
    """Get checkpoint manager (dependency)."""
    if _checkpoint_manager is None:
        initialize_services()
    return _checkpoint_manager
# DOCGEN:LLM-FIRST@v4