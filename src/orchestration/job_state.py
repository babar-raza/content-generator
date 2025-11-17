"""Job State Models and Enumerations."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from pathlib import Path


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Step execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepExecution:
    """Represents execution of a single workflow step."""
    agent_id: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    output: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'agent_id': self.agent_id,
            'status': self.status.value,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error,
            'output': self.output,
            'retry_count': self.retry_count,
            'duration_seconds': self.duration_seconds
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StepExecution':
        """Create from dictionary."""
        return cls(
            agent_id=data['agent_id'],
            status=StepStatus(data['status']),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            error=data.get('error'),
            output=data.get('output', {}),
            retry_count=data.get('retry_count', 0),
            duration_seconds=data.get('duration_seconds', 0.0)
        )


@dataclass
class JobMetadata:
    """Metadata for a job execution."""
    job_id: str
    workflow_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    progress: float = 0.0
    current_step: Optional[str] = None
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'job_id': self.job_id,
            'workflow_id': self.workflow_id,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'progress': self.progress,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'completed_steps': self.completed_steps,
            'failed_steps': self.failed_steps,
            'error_message': self.error_message,
            'correlation_id': self.correlation_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobMetadata':
        """Create from dictionary."""
        return cls(
            job_id=data['job_id'],
            workflow_id=data['workflow_id'],
            status=JobStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            progress=data.get('progress', 0.0),
            current_step=data.get('current_step'),
            total_steps=data.get('total_steps', 0),
            completed_steps=data.get('completed_steps', 0),
            failed_steps=data.get('failed_steps', 0),
            error_message=data.get('error_message'),
            correlation_id=data.get('correlation_id')
        )


@dataclass
class JobState:
    """Complete state of a job execution."""
    metadata: JobMetadata
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    steps: Dict[str, StepExecution] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metadata': self.metadata.to_dict(),
            'inputs': self.inputs,
            'outputs': self.outputs,
            'steps': {k: v.to_dict() for k, v in self.steps.items()},
            'context': self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobState':
        """Create from dictionary."""
        return cls(
            metadata=JobMetadata.from_dict(data['metadata']),
            inputs=data.get('inputs', {}),
            outputs=data.get('outputs', {}),
            steps={
                k: StepExecution.from_dict(v) 
                for k, v in data.get('steps', {}).items()
            },
            context=data.get('context', {})
        )
    
    def update_progress(self) -> None:
        """Update progress based on completed steps."""
        if self.metadata.total_steps > 0:
            self.metadata.progress = self.metadata.completed_steps / self.metadata.total_steps
        else:
            self.metadata.progress = 0.0
    
    def get_step(self, agent_id: str) -> Optional[StepExecution]:
        """Get step execution by agent ID."""
        return self.steps.get(agent_id)
    
    def mark_step_started(self, agent_id: str) -> None:
        """Mark a step as started."""
        if agent_id not in self.steps:
            self.steps[agent_id] = StepExecution(agent_id=agent_id)
        
        step = self.steps[agent_id]
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()
        self.metadata.current_step = agent_id
        self.metadata.updated_at = datetime.now()
    
    def mark_step_completed(self, agent_id: str, output: Dict[str, Any]) -> None:
        """Mark a step as completed."""
        if agent_id not in self.steps:
            return
        
        step = self.steps[agent_id]
        step.status = StepStatus.COMPLETED
        step.completed_at = datetime.now()
        step.output = output
        
        if step.started_at:
            duration = (step.completed_at - step.started_at).total_seconds()
            step.duration_seconds = duration
        
        self.metadata.completed_steps += 1
        self.metadata.updated_at = datetime.now()
        self.update_progress()
    
    def mark_step_failed(self, agent_id: str, error: str) -> None:
        """Mark a step as failed."""
        if agent_id not in self.steps:
            self.steps[agent_id] = StepExecution(agent_id=agent_id)
        
        step = self.steps[agent_id]
        step.status = StepStatus.FAILED
        step.completed_at = datetime.now()
        step.error = error
        
        if step.started_at:
            duration = (step.completed_at - step.started_at).total_seconds()
            step.duration_seconds = duration
        
        self.metadata.failed_steps += 1
        self.metadata.updated_at = datetime.now()
    
    def mark_step_skipped(self, agent_id: str) -> None:
        """Mark a step as skipped."""
        if agent_id not in self.steps:
            self.steps[agent_id] = StepExecution(agent_id=agent_id)
        
        step = self.steps[agent_id]
        step.status = StepStatus.SKIPPED
        self.metadata.updated_at = datetime.now()
# DOCGEN:LLM-FIRST@v4