"""Job Control System - Pause/Resume/Cancel functionality for UCOP."""

import asyncio
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class JobState(str, Enum):
    """Job execution states."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobControl:
    """Control signals for a running job."""
    job_id: str
    should_pause: bool = False
    should_cancel: bool = False
    should_step: bool = False
    step_mode: Optional[str] = None  # "into", "over", "out"
    new_params: Optional[Dict[str, Any]] = None
    checkpoint_name: Optional[str] = None
    
    def pause(self):
        """Request job pause."""
        self.should_pause = True
        self.should_cancel = False
    
    def resume(self):
        """Resume from pause."""
        self.should_pause = False
        self.should_step = False
    
    def cancel(self):
        """Request job cancellation."""
        self.should_cancel = True
    
    def step(self, mode: str = "into"):
        """Step execution (into/over/out)."""
        self.should_step = True
        self.step_mode = mode
    
    def set_params(self, params: Dict[str, Any]):
        """Inject new parameters at runtime."""
        if self.new_params is None:
            self.new_params = {}
        self.new_params.update(params)


class JobController:
    """Manages job control state."""
    
    def __init__(self):
        self.jobs: Dict[str, JobControl] = {}
        self.states: Dict[str, JobState] = {}
        self.state_history: Dict[str, list] = {}
    
    def create_job(self, job_id: str) -> JobControl:
        """Create control state for a new job."""
        control = JobControl(job_id=job_id)
        self.jobs[job_id] = control
        self.states[job_id] = JobState.PENDING
        self.state_history[job_id] = [{
            "state": JobState.PENDING,
            "timestamp": datetime.now().isoformat()
        }]
        logger.info(f"Created job control for {job_id}")
        return control
    
    def get_control(self, job_id: str) -> Optional[JobControl]:
        """Get control state for a job."""
        return self.jobs.get(job_id)
    
    def set_state(self, job_id: str, state: JobState):
        """Update job state."""
        if job_id in self.states:
            self.states[job_id] = state
            self.state_history[job_id].append({
                "state": state,
                "timestamp": datetime.now().isoformat()
            })
            logger.info(f"Job {job_id} state: {state}")
    
    def pause_job(self, job_id: str):
        """Pause a running job."""
        control = self.get_control(job_id)
        if control:
            control.pause()
            self.set_state(job_id, JobState.PAUSED)
            logger.info(f"Pausing job {job_id}")
    
    def resume_job(self, job_id: str, params: Optional[Dict[str, Any]] = None):
        """Resume a paused job."""
        control = self.get_control(job_id)
        if control:
            if params:
                control.set_params(params)
            control.resume()
            self.set_state(job_id, JobState.RUNNING)
            logger.info(f"Resuming job {job_id}")
    
    def cancel_job(self, job_id: str):
        """Cancel a running job."""
        control = self.get_control(job_id)
        if control:
            control.cancel()
            self.set_state(job_id, JobState.CANCELLED)
            logger.info(f"Cancelling job {job_id}")
    
    def step_job(self, job_id: str, mode: str = "into"):
        """Step job execution (debugger-style)."""
        control = self.get_control(job_id)
        if control:
            control.step(mode)
            logger.info(f"Stepping job {job_id} ({mode})")
    
    async def check_control(self, job_id: str, max_latency_s: float = 2.0) -> Dict[str, Any]:
        """
        Check control signals (RT-A1: honor within 2s).
        Returns: {"action": "pause"|"cancel"|"step"|"continue", "params": {...}}
        """
        control = self.get_control(job_id)
        if not control:
            return {"action": "continue"}
        
        if control.should_cancel:
            return {"action": "cancel"}
        
        if control.should_pause:
            self.set_state(job_id, JobState.PAUSED)
            # Wait until resumed
            while control.should_pause and not control.should_cancel:
                await asyncio.sleep(0.1)
            
            if control.should_cancel:
                return {"action": "cancel"}
            
            self.set_state(job_id, JobState.RUNNING)
            return {
                "action": "resume",
                "params": control.new_params or {}
            }
        
        if control.should_step:
            return {
                "action": "step",
                "mode": control.step_mode
            }
        
        return {"action": "continue"}


# Global controller
_controller = None


def get_controller() -> JobController:
    """Get the global job controller."""
    global _controller
    if _controller is None:
        _controller = JobController()
    return _controller


class InterruptibleAgent:
    """Base class for agents that support pause/resume."""
    
    def __init__(self, agent_id: str, job_id: str):
        self.agent_id = agent_id
        self.job_id = job_id
        self.controller = get_controller()
        self.control = self.controller.get_control(job_id)
        self.state: Dict[str, Any] = {}
    
    async def checkpoint(self, name: str):
        """Mark a checkpoint (safe point for pause/resume)."""
        logger.info(f"Agent {self.agent_id} at checkpoint: {name}")
        
        # Check for control signals
        result = await self.controller.check_control(self.job_id)
        
        if result["action"] == "cancel":
            raise asyncio.CancelledError("Job cancelled")
        
        if result["action"] == "resume":
            # Apply new parameters
            new_params = result.get("params", {})
            if new_params:
                self.apply_params(new_params)
        
        return result
    
    def apply_params(self, params: Dict[str, Any]):
        """Apply runtime parameter updates."""
        logger.info(f"Agent {self.agent_id} applying params: {params}")
        # Override in subclass
    
    def dump_state(self) -> Dict[str, Any]:
        """Dump agent state (RT-A2)."""
        return {
            "agent_id": self.agent_id,
            "job_id": self.job_id,
            "state": self.state,
            "timestamp": datetime.now().isoformat()
        }
    
    def load_state(self, state: Dict[str, Any]):
        """Load agent state for resume."""
        self.state = state.get("state", {})


# FastAPI endpoints (add to main or ops_console)
"""
from fastapi import APIRouter

router = APIRouter(prefix="/jobs")

@router.post("/{job_id}/pause")
async def pause_job(job_id: str):
    controller = get_controller()
    controller.pause_job(job_id)
    return {"status": "paused", "job_id": job_id}

@router.post("/{job_id}/resume")
async def resume_job(job_id: str, params: Dict[str, Any] = None):
    controller = get_controller()
    controller.resume_job(job_id, params)
    return {"status": "running", "job_id": job_id}

@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    controller = get_controller()
    controller.cancel_job(job_id)
    return {"status": "cancelled", "job_id": job_id}

@router.post("/{job_id}/step")
async def step_job(job_id: str, mode: str = "into"):
    controller = get_controller()
    controller.step_job(job_id, mode)
    return {"status": "stepping", "mode": mode}

@router.get("/{job_id}/status")
async def get_job_status(job_id: str):
    controller = get_controller()
    return {
        "job_id": job_id,
        "state": controller.states.get(job_id),
        "history": controller.state_history.get(job_id, [])
    }
"""
