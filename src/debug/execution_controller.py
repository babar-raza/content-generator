"""Execution Controller - Pause/Resume/Step control.

This module implements the ExecutionController (VIS-004), which:
- Pause/Resume execution via threading.Event
- Step Over (execute one agent, pause at next)
- Step Into (pause before LLM call within agent)
- Re-run (re-execute current agent with modified inputs)
- Input/prompt override injection

Thread Safety:
    All methods are thread-safe for concurrent access.

Author: Migration Implementation Agent
Created: 2025-12-18
Taskcard: VIS-004
"""

import logging
import threading
from typing import Any, Optional

from .models import ExecutionState, ExecutionStateStatus, StepMode

logger = logging.getLogger(__name__)


class ExecutionController:
    """Controller for execution pause/resume/step operations.

    The ExecutionController coordinates execution flow control:
    - Pause/Resume via threading.Event synchronization
    - Step modes (Over, Into) for granular control
    - Input/prompt overrides for edit-and-continue
    - Re-run capability for iterative debugging

    Example:
        >>> controller = ExecutionController()
        >>> controller.pause("job-123")
        >>> # Execution will pause at next checkpoint
        >>> controller.set_input_override("job-123", "agent1", {"topic": "New Topic"})
        >>> controller.resume("job-123")

    Thread Safety:
        All public methods are thread-safe.
    """

    def __init__(self):
        """Initialize execution controller."""
        self._pause_events: dict[str, threading.Event] = {}
        self._step_modes: dict[str, StepMode] = {}
        self._input_overrides: dict[str, dict[str, dict[str, Any]]] = {}
        self._prompt_overrides: dict[str, dict[str, str]] = {}
        self._states: dict[str, ExecutionState] = {}
        self._lock = threading.RLock()

        logger.info("ExecutionController initialized")

    def pause(self, job_id: str) -> None:
        """Pause execution at next checkpoint.

        Args:
            job_id: Job identifier

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> controller.pause("job-123")
            >>> state = controller.get_state("job-123")
            >>> # Will be PAUSED once execution reaches checkpoint
        """
        with self._lock:
            if job_id not in self._pause_events:
                self._pause_events[job_id] = threading.Event()
                # Start in paused state (clear the event)
                self._pause_events[job_id].clear()
            else:
                self._pause_events[job_id].clear()

            # Update state
            if job_id in self._states:
                self._states[job_id].status = ExecutionStateStatus.PAUSED

            logger.info(f"Paused execution for job {job_id}")

    def resume(self, job_id: str) -> None:
        """Resume paused execution.

        Args:
            job_id: Job identifier

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> controller.pause("job-123")
            >>> controller.resume("job-123")
            >>> state = controller.get_state("job-123")
            >>> # Will be RUNNING
        """
        with self._lock:
            if job_id not in self._pause_events:
                self._pause_events[job_id] = threading.Event()

            # Clear step mode
            self._step_modes[job_id] = StepMode.NONE

            # Resume execution
            self._pause_events[job_id].set()

            # Update state
            if job_id in self._states:
                self._states[job_id].status = ExecutionStateStatus.RUNNING
                self._states[job_id].paused_at = None

            logger.info(f"Resumed execution for job {job_id}")

    def step_over(self, job_id: str) -> None:
        """Execute one agent, then pause at next.

        Args:
            job_id: Job identifier

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> controller.step_over("job-123")
            >>> # Execution will run one agent then pause
        """
        with self._lock:
            self._step_modes[job_id] = StepMode.OVER

            if job_id not in self._pause_events:
                self._pause_events[job_id] = threading.Event()

            # Resume for one step
            self._pause_events[job_id].set()

            logger.info(f"Step over for job {job_id}")

    def step_into(self, job_id: str) -> None:
        """Pause at next LLM call within agent.

        Args:
            job_id: Job identifier

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> controller.step_into("job-123")
            >>> # Execution will pause at next LLM call
        """
        with self._lock:
            self._step_modes[job_id] = StepMode.INTO

            if job_id not in self._pause_events:
                self._pause_events[job_id] = threading.Event()

            # Resume for one step
            self._pause_events[job_id].set()

            logger.info(f"Step into for job {job_id}")

    def rerun_agent(
        self, job_id: str, agent_name: str, inputs: dict[str, Any]
    ) -> None:
        """Re-run current agent with modified inputs.

        This sets an input override and resumes execution.

        Args:
            job_id: Job identifier
            agent_name: Agent to re-run
            inputs: Modified inputs

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> controller.rerun_agent("job-123", "topic_identification",
            ...                       {"topic": "New Topic"})
        """
        with self._lock:
            self.set_input_override(job_id, agent_name, inputs)
            self.resume(job_id)

            logger.info(f"Re-running agent {agent_name} for job {job_id}")

    def set_input_override(
        self, job_id: str, agent_name: str, inputs: dict[str, Any]
    ) -> None:
        """Set input override for an agent.

        Args:
            job_id: Job identifier
            agent_name: Agent name
            inputs: Override inputs

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> controller.set_input_override("job-123", "agent1", {"topic": "Python"})
            >>> override = controller.get_input_override("job-123", "agent1")
            >>> assert override["topic"] == "Python"
        """
        with self._lock:
            if job_id not in self._input_overrides:
                self._input_overrides[job_id] = {}

            self._input_overrides[job_id][agent_name] = inputs

            logger.info(
                f"Set input override for agent {agent_name} in job {job_id}"
            )

    def set_prompt_override(
        self, job_id: str, agent_name: str, template: str
    ) -> None:
        """Set prompt template override for an agent.

        Args:
            job_id: Job identifier
            agent_name: Agent name
            template: Override prompt template

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> controller.set_prompt_override("job-123", "agent1", "New prompt: {topic}")
            >>> override = controller.get_prompt_override("job-123", "agent1")
            >>> assert "New prompt" in override
        """
        with self._lock:
            if job_id not in self._prompt_overrides:
                self._prompt_overrides[job_id] = {}

            self._prompt_overrides[job_id][agent_name] = template

            logger.info(
                f"Set prompt override for agent {agent_name} in job {job_id}"
            )

    def get_input_override(
        self, job_id: str, agent_name: str
    ) -> Optional[dict[str, Any]]:
        """Get input override for an agent.

        Args:
            job_id: Job identifier
            agent_name: Agent name

        Returns:
            Override inputs if set, None otherwise

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            if job_id not in self._input_overrides:
                return None
            return self._input_overrides[job_id].get(agent_name)

    def get_prompt_override(self, job_id: str, agent_name: str) -> Optional[str]:
        """Get prompt template override for an agent.

        Args:
            job_id: Job identifier
            agent_name: Agent name

        Returns:
            Override template if set, None otherwise

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            if job_id not in self._prompt_overrides:
                return None
            return self._prompt_overrides[job_id].get(agent_name)

    def clear_overrides(self, job_id: str) -> None:
        """Clear all overrides for a job.

        Args:
            job_id: Job identifier

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            if job_id in self._input_overrides:
                del self._input_overrides[job_id]
            if job_id in self._prompt_overrides:
                del self._prompt_overrides[job_id]

            logger.info(f"Cleared all overrides for job {job_id}")

    def get_state(self, job_id: str) -> ExecutionState:
        """Get current execution state.

        Args:
            job_id: Job identifier

        Returns:
            Current ExecutionState

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> state = controller.get_state("job-123")
            >>> assert state.job_id == "job-123"
        """
        with self._lock:
            if job_id not in self._states:
                self._states[job_id] = ExecutionState(
                    job_id=job_id,
                    status=ExecutionStateStatus.RUNNING,
                )

            return self._states[job_id]

    def update_state(self, state: ExecutionState) -> None:
        """Update execution state.

        Args:
            state: New execution state

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            self._states[state.job_id] = state
            logger.debug(
                f"Updated state for job {state.job_id}: "
                f"{state.status} @ {state.current_agent}"
            )

    def wait_if_paused(self, job_id: str, timeout: Optional[float] = None) -> bool:
        """Wait if execution is paused.

        This is called by the execution engine at checkpoints.

        Args:
            job_id: Job identifier
            timeout: Optional timeout in seconds

        Returns:
            True if resumed, False if timeout

        Thread Safety:
            This method is thread-safe and blocks until resumed.

        Example:
            >>> controller = ExecutionController()
            >>> controller.pause("job-123")
            >>> # In execution thread:
            >>> controller.wait_if_paused("job-123")  # Blocks until resume
        """
        with self._lock:
            if job_id not in self._pause_events:
                return True  # Not paused

            event = self._pause_events[job_id]

        # Wait outside the lock
        return event.wait(timeout=timeout)


    def is_paused(self, job_id: str) -> bool:
        """Check if a job is currently paused.

        Args:
            job_id: Job identifier

        Returns:
            True if job is paused, False otherwise

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> controller.pause("job-123")
            >>> assert controller.is_paused("job-123") is True
            >>> controller.resume("job-123")
            >>> assert controller.is_paused("job-123") is False
        """
        with self._lock:
            if job_id not in self._pause_events:
                return False
            # Event is cleared when paused, set when running
            return not self._pause_events[job_id].is_set()

    def get_step_mode(self, job_id: str) -> StepMode:
        """Get current step mode for a job.

        Args:
            job_id: Job identifier

        Returns:
            Current StepMode (NONE, OVER, or INTO)

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> controller.step_over("job-123")
            >>> assert controller.get_step_mode("job-123") == StepMode.OVER
        """
        with self._lock:
            return self._step_modes.get(job_id, StepMode.NONE)

    def should_pause(
        self, job_id: str, event_type: str, agent_name: str
    ) -> bool:
        """Check if execution should pause at this event.

        Unified pause check that handles:
        - Explicit pause requests
        - Step over mode (pause at agent_start)
        - Step into mode (pause at llm_start)

        Args:
            job_id: Job identifier
            event_type: Type of event ("agent_start", "llm_start", etc.)
            agent_name: Name of the agent

        Returns:
            True if execution should pause, False otherwise

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> controller.step_over("job-123")
            >>> # Should pause at agent start
            >>> assert controller.should_pause("job-123", "agent_start", "agent1") is True
        """
        with self._lock:
            # Check if explicitly paused
            if self.is_paused(job_id):
                return True

            step_mode = self._step_modes.get(job_id, StepMode.NONE)

            # Step over: pause at agent_start
            if step_mode == StepMode.OVER and event_type == "agent_start":
                self._step_modes[job_id] = StepMode.NONE
                self.pause(job_id)
                return True

            # Step into: pause at llm_start
            if step_mode == StepMode.INTO and event_type == "llm_start":
                self._step_modes[job_id] = StepMode.NONE
                self.pause(job_id)
                return True

            return False

    def wait_for_resume(
        self, job_id: str, timeout: Optional[float] = None
    ) -> bool:
        """Wait for job to be resumed.

        Blocks until the job is resumed or timeout expires.

        Args:
            job_id: Job identifier
            timeout: Optional timeout in seconds (None = wait forever)

        Returns:
            True if resumed, False if timeout

        Thread Safety:
            This method is thread-safe and blocks until resumed.

        Example:
            >>> controller = ExecutionController()
            >>> controller.pause("job-123")
            >>> # In execution thread:
            >>> resumed = controller.wait_for_resume("job-123", timeout=5.0)
            >>> if resumed:
            ...     print("Execution resumed")
            ... else:
            ...     print("Timeout waiting for resume")
        """
        return self.wait_if_paused(job_id, timeout=timeout)

    def clear_step_mode(self, job_id: str) -> None:
        """Clear step mode for a job.

        Resets the job to normal execution mode (no stepping).

        Args:
            job_id: Job identifier

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> controller.step_over("job-123")
            >>> controller.clear_step_mode("job-123")
            >>> assert controller.get_step_mode("job-123") == StepMode.NONE
        """
        with self._lock:
            self._step_modes[job_id] = StepMode.NONE
            logger.debug(f"Cleared step mode for job {job_id}")

    def get_all_paused_jobs(self) -> list[str]:
        """Get list of all paused jobs.

        Returns:
            List of job IDs that are currently paused

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> controller.pause("job-123")
            >>> controller.pause("job-456")
            >>> paused = controller.get_all_paused_jobs()
            >>> assert "job-123" in paused
            >>> assert "job-456" in paused
        """
        with self._lock:
            paused_jobs = []
            for job_id, event in self._pause_events.items():
                # Event is cleared when paused
                if not event.is_set():
                    paused_jobs.append(job_id)
            return paused_jobs

    def reset_job(self, job_id: str) -> None:
        """Reset job execution state.

        Clears pause state, step mode, and overrides for the job.
        Similar to cleanup() but resumes the job instead of cleaning up.

        Args:
            job_id: Job identifier

        Thread Safety:
            This method is thread-safe.

        Example:
            >>> controller = ExecutionController()
            >>> controller.pause("job-123")
            >>> controller.step_over("job-123")
            >>> controller.reset_job("job-123")
            >>> assert controller.is_paused("job-123") is False
            >>> assert controller.get_step_mode("job-123") == StepMode.NONE
        """
        with self._lock:
            # Resume if paused
            if job_id in self._pause_events:
                self._pause_events[job_id].set()
                del self._pause_events[job_id]

            # Clear step mode
            if job_id in self._step_modes:
                self._step_modes[job_id] = StepMode.NONE

            # Keep state and overrides (unlike cleanup)
            # This allows continuing execution with reset controls

            logger.info(f"Reset execution controls for job {job_id}")

    def cleanup(self, job_id: str) -> None:
        """Clean up all state for a job.

        Args:
            job_id: Job identifier

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            if job_id in self._pause_events:
                # Resume any waiting threads before cleanup
                self._pause_events[job_id].set()
                del self._pause_events[job_id]

            if job_id in self._step_modes:
                del self._step_modes[job_id]

            if job_id in self._input_overrides:
                del self._input_overrides[job_id]

            if job_id in self._prompt_overrides:
                del self._prompt_overrides[job_id]

            if job_id in self._states:
                del self._states[job_id]

            logger.info(f"Cleaned up execution state for job {job_id}")


__all__ = ["ExecutionController"]
