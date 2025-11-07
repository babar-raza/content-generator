"""Agent execution tracker for I/O visibility."""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentRun:
    """Record of a single agent execution."""
    agent_name: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "running"
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class AgentExecutionTracker:
    """Tracks all agent executions for a job."""
    
    def __init__(self, job_id: str, storage_dir: Path = None):
        self.job_id = job_id
        self.runs: List[AgentRun] = []
        
        if storage_dir is None:
            storage_dir = Path(f"./data/jobs/{job_id}")
        
        self.storage_path = storage_dir / "agent_runs.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"AgentExecutionTracker initialized for job {job_id}")
    
    def record_start(self, agent_name: str, input_data: Dict[str, Any]) -> AgentRun:
        """Record agent start."""
        run = AgentRun(
            agent_name=agent_name,
            started_at=datetime.now(timezone.utc).isoformat(),
            status="running",
            input_data=input_data
        )
        
        self.runs.append(run)
        self._persist()
        
        logger.debug(f"Agent started: {agent_name}")
        return run
    
    def record_complete(self, run: AgentRun, output_data: Dict[str, Any]):
        """Record agent completion."""
        run.completed_at = datetime.now(timezone.utc).isoformat()
        run.status = "completed"
        run.output_data = output_data
        
        # Calculate duration
        started = datetime.fromisoformat(run.started_at)
        completed = datetime.fromisoformat(run.completed_at)
        run.duration_ms = (completed - started).total_seconds() * 1000
        
        self._persist()
        logger.debug(f"Agent completed: {run.agent_name} ({run.duration_ms:.0f}ms)")
    
    def record_error(self, run: AgentRun, error: str):
        """Record agent error."""
        run.completed_at = datetime.now(timezone.utc).isoformat()
        run.status = "failed"
        run.error = error
        
        # Calculate duration
        started = datetime.fromisoformat(run.started_at)
        completed = datetime.fromisoformat(run.completed_at)
        run.duration_ms = (completed - started).total_seconds() * 1000
        
        self._persist()
        logger.error(f"Agent failed: {run.agent_name} - {error}")
    
    def get_run(self, agent_name: str) -> Optional[AgentRun]:
        """Get most recent run for an agent."""
        for run in reversed(self.runs):
            if run.agent_name == agent_name:
                return run
        return None
    
    def get_all_runs(self) -> List[AgentRun]:
        """Get all agent runs."""
        return self.runs.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        total_runs = len(self.runs)
        completed = sum(1 for r in self.runs if r.status == "completed")
        failed = sum(1 for r in self.runs if r.status == "failed")
        running = sum(1 for r in self.runs if r.status == "running")
        
        total_duration = sum(r.duration_ms for r in self.runs if r.duration_ms > 0)
        
        return {
            "job_id": self.job_id,
            "total_runs": total_runs,
            "completed": completed,
            "failed": failed,
            "running": running,
            "total_duration_ms": total_duration,
            "agents": [r.agent_name for r in self.runs]
        }
    
    def _persist(self):
        """Save to disk."""
        try:
            data = {
                "job_id": self.job_id,
                "runs": [r.to_dict() for r in self.runs],
                "summary": self.get_summary()
            }
            
            self.storage_path.write_text(
                json.dumps(data, indent=2),
                encoding='utf-8'
            )
        except Exception as e:
            logger.error(f"Failed to persist agent runs: {e}")
    
    def load(self) -> bool:
        """Load from disk."""
        if not self.storage_path.exists():
            return False
        
        try:
            data = json.loads(self.storage_path.read_text(encoding='utf-8'))
            
            self.runs = [AgentRun(**r) for r in data.get('runs', [])]
            logger.info(f"Loaded {len(self.runs)} agent runs from disk")
            return True
        except Exception as e:
            logger.error(f"Failed to load agent runs: {e}")
            return False
