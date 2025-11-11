"""Fallback Orchestration Engine - Works without LangGraph dependency.

This provides basic orchestration capabilities when LangGraph is not available.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class WorkflowStep:
    """Represents a step in the workflow."""
    id: str
    agent: str
    depends_on: List[str] = field(default_factory=list)
    parallel: bool = False
    timeout: int = 300
    retry: int = 3
    optional: bool = False


@dataclass
class WorkflowState:
    """Workflow execution state."""
    job_id: str
    status: JobStatus
    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)


class FallbackOrchestrationEngine:
    """Fallback orchestration engine that works without LangGraph."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.workflows: Dict[str, List[WorkflowStep]] = {}
        self.jobs: Dict[str, WorkflowState] = {}
        self.agents: Dict[str, Callable] = {}
        self.checkpoints: Dict[str, Dict] = {}
        self.executor = ThreadPoolExecutor(max_workers=5)
        
    def register_workflow(self, workflow_id: str, steps: List[WorkflowStep]):
        """Register a workflow definition."""
        self.workflows[workflow_id] = steps
        logger.info(f"Registered workflow: {workflow_id} with {len(steps)} steps")
        
    def register_agent(self, agent_id: str, agent_func: Callable):
        """Register an agent function."""
        self.agents[agent_id] = agent_func
        logger.info(f"Registered agent: {agent_id}")
        
    def create_job(self, workflow_id: str, inputs: Dict[str, Any]) -> str:
        """Create a new job for workflow execution."""
        import uuid
        job_id = str(uuid.uuid4())
        
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
            
        state = WorkflowState(
            job_id=job_id,
            status=JobStatus.PENDING,
            context={"inputs": inputs, "workflow_id": workflow_id}
        )
        
        self.jobs[job_id] = state
        logger.info(f"Created job {job_id} for workflow {workflow_id}")
        return job_id
        
    async def execute_job(self, job_id: str) -> WorkflowState:
        """Execute a job asynchronously."""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
            
        state = self.jobs[job_id]
        workflow_id = state.context["workflow_id"]
        steps = self.workflows[workflow_id]
        
        state.status = JobStatus.RUNNING
        state.started_at = datetime.now()
        
        try:
            # Build dependency graph
            step_dict = {step.id: step for step in steps}
            completed = set()
            
            while len(completed) < len(steps):
                # Find steps ready to execute
                ready_steps = []
                for step in steps:
                    if step.id not in completed:
                        if all(dep in completed for dep in step.depends_on):
                            ready_steps.append(step)
                
                if not ready_steps:
                    logger.warning("No steps ready to execute - possible circular dependency")
                    break
                    
                # Execute ready steps
                if any(step.parallel for step in ready_steps):
                    # Parallel execution
                    await self._execute_parallel_steps(state, ready_steps)
                else:
                    # Sequential execution
                    for step in ready_steps:
                        await self._execute_step(state, step)
                        
                # Mark steps as completed
                for step in ready_steps:
                    if step.id not in state.failed_steps:
                        completed.add(step.id)
                        
                # Save checkpoint
                self._save_checkpoint(job_id, state)
                
            state.status = JobStatus.COMPLETED if not state.failed_steps else JobStatus.FAILED
            state.completed_at = datetime.now()
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            state.status = JobStatus.FAILED
            state.errors.append({"error": str(e), "timestamp": datetime.now().isoformat()})
            
        return state
        
    async def _execute_step(self, state: WorkflowState, step: WorkflowStep):
        """Execute a single workflow step."""
        logger.info(f"Executing step {step.id} with agent {step.agent}")
        state.current_step = step.id
        
        if step.agent not in self.agents:
            if step.optional:
                logger.warning(f"Optional agent {step.agent} not found, skipping")
                return
            else:
                raise ValueError(f"Agent {step.agent} not found")
                
        agent_func = self.agents[step.agent]
        
        # Prepare input from previous outputs
        input_data = state.context.get("inputs", {})
        if step.depends_on:
            for dep in step.depends_on:
                if dep in state.outputs:
                    input_data.update(state.outputs[dep])
                    
        # Execute with retry
        for attempt in range(step.retry):
            try:
                # Execute agent
                result = await self._run_agent_async(agent_func, input_data, step.timeout)
                
                # Store output
                state.outputs[step.id] = result
                state.completed_steps.append(step.id)
                logger.info(f"Step {step.id} completed successfully")
                return
                
            except Exception as e:
                logger.warning(f"Step {step.id} attempt {attempt + 1} failed: {e}")
                if attempt == step.retry - 1:
                    state.failed_steps.append(step.id)
                    state.errors.append({
                        "step": step.id,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
                    if not step.optional:
                        raise
                        
    async def _execute_parallel_steps(self, state: WorkflowState, steps: List[WorkflowStep]):
        """Execute multiple steps in parallel."""
        logger.info(f"Executing {len(steps)} steps in parallel")
        
        tasks = []
        for step in steps:
            task = self._execute_step(state, step)
            tasks.append(task)
            
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _run_agent_async(self, agent_func: Callable, input_data: Dict, timeout: int):
        """Run an agent function asynchronously with timeout."""
        loop = asyncio.get_event_loop()
        
        # Run in executor to avoid blocking
        future = loop.run_in_executor(self.executor, agent_func, input_data)
        
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Agent execution exceeded {timeout}s timeout")
            
    def _save_checkpoint(self, job_id: str, state: WorkflowState):
        """Save a checkpoint of the current state."""
        checkpoint = {
            "job_id": job_id,
            "state": {
                "status": state.status.value,
                "current_step": state.current_step,
                "completed_steps": state.completed_steps,
                "failed_steps": state.failed_steps,
                "outputs": state.outputs,
                "context": state.context,
                "errors": state.errors
            },
            "timestamp": datetime.now().isoformat()
        }
        
        self.checkpoints[job_id] = checkpoint
        
        # Also save to file if checkpoint dir is configured
        checkpoint_dir = self.config.get("checkpoint_dir")
        if checkpoint_dir:
            checkpoint_path = Path(checkpoint_dir) / f"{job_id}.json"
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            with open(checkpoint_path, 'w') as f:
                json.dump(checkpoint, f, indent=2)
                
    def restore_from_checkpoint(self, job_id: str) -> Optional[WorkflowState]:
        """Restore job state from checkpoint."""
        if job_id in self.checkpoints:
            checkpoint = self.checkpoints[job_id]
            state_data = checkpoint["state"]
            
            state = WorkflowState(
                job_id=job_id,
                status=JobStatus(state_data["status"]),
                current_step=state_data.get("current_step"),
                completed_steps=state_data["completed_steps"],
                failed_steps=state_data["failed_steps"],
                outputs=state_data["outputs"],
                context=state_data["context"],
                errors=state_data["errors"]
            )
            
            self.jobs[job_id] = state
            return state
            
        # Try loading from file
        checkpoint_dir = self.config.get("checkpoint_dir")
        if checkpoint_dir:
            checkpoint_path = Path(checkpoint_dir) / f"{job_id}.json"
            if checkpoint_path.exists():
                with open(checkpoint_path, 'r') as f:
                    checkpoint = json.load(f)
                    return self.restore_from_checkpoint(job_id)
                    
        return None
        
    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get the status of a job."""
        if job_id in self.jobs:
            return self.jobs[job_id].status
        return None
        
    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all jobs with their status."""
        return [
            {
                "job_id": job_id,
                "status": state.status.value,
                "workflow_id": state.context.get("workflow_id"),
                "started_at": state.started_at.isoformat() if state.started_at else None,
                "completed_at": state.completed_at.isoformat() if state.completed_at else None
            }
            for job_id, state in self.jobs.items()
        ]
        
    def cancel_job(self, job_id: str):
        """Cancel a running job."""
        if job_id in self.jobs:
            self.jobs[job_id].status = JobStatus.PAUSED
            logger.info(f"Job {job_id} cancelled")


# Example usage and testing
def example_agent_function(input_data: Dict) -> Dict:
    """Example agent that can be used for testing."""
    return {"result": f"Processed: {input_data.get('input', 'no input')}"}


def create_test_workflow():
    """Create a test workflow for demonstration."""
    steps = [
        WorkflowStep(id="step1", agent="agent1", depends_on=[]),
        WorkflowStep(id="step2", agent="agent2", depends_on=["step1"]),
        WorkflowStep(id="step3", agent="agent3", depends_on=["step1"], parallel=True),
        WorkflowStep(id="step4", agent="agent4", depends_on=["step2", "step3"])
    ]
    return steps


if __name__ == "__main__":
    # Test the fallback orchestration engine
    import asyncio
    
    async def test_engine():
        engine = FallbackOrchestrationEngine()
        
        # Register test agents
        for i in range(1, 5):
            engine.register_agent(f"agent{i}", example_agent_function)
            
        # Register workflow
        engine.register_workflow("test_workflow", create_test_workflow())
        
        # Create and execute job
        job_id = engine.create_job("test_workflow", {"input": "test data"})
        print(f"Created job: {job_id}")
        
        state = await engine.execute_job(job_id)
        print(f"Job completed with status: {state.status}")
        print(f"Outputs: {json.dumps(state.outputs, indent=2)}")
        
    asyncio.run(test_engine())
