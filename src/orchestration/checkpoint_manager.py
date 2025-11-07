# checkpoint_manager.py
"""Enhanced checkpoint management for UCOP agent workflows.

Provides pause/resume capabilities and state persistence for MCP-compliant agents.
"""

import json
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum
import logging
from src.core.contracts import AgentEvent

logger = logging.getLogger(__name__)


class CheckpointState(Enum):
    """Checkpoint execution states."""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CheckpointExecution:
    """Individual checkpoint execution record."""
    checkpoint_name: str
    agent_id: str
    correlation_id: str
    state: CheckpointState = CheckpointState.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_details: Optional[str] = None
    approval_required: bool = False
    approval_status: Optional[str] = None  # "pending", "approved", "denied"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckpointExecution':
        """Create from dictionary."""
        return cls(**data)


@dataclass 
class WorkflowExecution:
    """Complete workflow execution with checkpoints."""
    execution_id: str
    correlation_id: str
    workflow_name: str
    started_at: str
    current_checkpoint: Optional[str] = None
    state: str = "running"  # running, paused, completed, failed
    checkpoints: List[CheckpointExecution] = field(default_factory=list)
    global_data: Dict[str, Any] = field(default_factory=dict)
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['checkpoints'] = [cp.to_dict() for cp in self.checkpoints]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowExecution':
        """Create from dictionary."""
        checkpoints_data = data.pop('checkpoints', [])
        execution = cls(**data)
        execution.checkpoints = [CheckpointExecution.from_dict(cp) for cp in checkpoints_data]
        return execution


class CheckpointManager:
    """Manages checkpoint execution and state persistence."""
    
    def __init__(self, storage_dir: Path = Path("./checkpoints")):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self._executions: Dict[str, WorkflowExecution] = {}
        self._checkpoint_callbacks: Dict[str, Callable] = {}
        self._approval_callbacks: Dict[str, Callable] = {}
        self._lock = threading.RLock()
        
        # Load persisted executions
        self._load_persisted_executions()
    
    def register_checkpoint_callback(self, checkpoint_name: str, callback: Callable):
        """Register a callback for checkpoint events."""
        with self._lock:
            self._checkpoint_callbacks[checkpoint_name] = callback
    
    def register_approval_callback(self, callback: Callable):
        """Register callback for approval requests."""
        with self._lock:
            self._approval_callbacks['default'] = callback
    
    def start_workflow_execution(
        self, 
        correlation_id: str, 
        workflow_name: str,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        """Start a new workflow execution."""
        with self._lock:
            execution_id = f"exec_{correlation_id}_{int(time.time())}"
            
            execution = WorkflowExecution(
                execution_id=execution_id,
                correlation_id=correlation_id,
                workflow_name=workflow_name,
                started_at=datetime.now(timezone.utc).isoformat(),
                global_data=initial_data or {}
            )
            
            self._executions[execution_id] = execution
            self._persist_execution(execution)
            
            logger.info(f"Started workflow execution: {execution_id}")
            return execution
    
    def create_checkpoint(
        self,
        execution_id: str,
        checkpoint_name: str,
        agent_id: str,
        input_data: Dict[str, Any],
        approval_required: bool = False
    ) -> CheckpointExecution:
        """Create a new checkpoint."""
        with self._lock:
            execution = self._executions.get(execution_id)
            if not execution:
                raise ValueError(f"Execution not found: {execution_id}")
            
            checkpoint = CheckpointExecution(
                checkpoint_name=checkpoint_name,
                agent_id=agent_id,
                correlation_id=execution.correlation_id,
                input_data=input_data,
                approval_required=approval_required,
                started_at=datetime.now(timezone.utc).isoformat()
            )
            
            # Handle approval requirement
            if approval_required:
                checkpoint.state = CheckpointState.PAUSED
                checkpoint.approval_status = "pending"
                execution.state = "paused"
                execution.current_checkpoint = checkpoint_name
                
                # Request approval
                self._request_approval(execution_id, checkpoint)
            else:
                checkpoint.state = CheckpointState.ACTIVE
                execution.current_checkpoint = checkpoint_name
            
            execution.checkpoints.append(checkpoint)
            self._persist_execution(execution)
            
            logger.info(f"Created checkpoint: {checkpoint_name} for {agent_id}")
            return checkpoint
    
    def complete_checkpoint(
        self,
        execution_id: str,
        checkpoint_name: str,
        output_data: Dict[str, Any],
        success: bool = True
    ) -> bool:
        """Complete a checkpoint."""
        with self._lock:
            execution = self._executions.get(execution_id)
            if not execution:
                return False
            
            # Find checkpoint
            checkpoint = None
            for cp in execution.checkpoints:
                if cp.checkpoint_name == checkpoint_name:
                    checkpoint = cp
                    break
            
            if not checkpoint:
                logger.error(f"Checkpoint not found: {checkpoint_name}")
                return False
            
            # Update checkpoint state
            checkpoint.output_data = output_data
            checkpoint.completed_at = datetime.now(timezone.utc).isoformat()
            checkpoint.state = CheckpointState.COMPLETED if success else CheckpointState.FAILED
            
            # Update execution state
            if success:
                execution.current_checkpoint = None
                if execution.state == "paused":
                    execution.state = "running"
            else:
                execution.state = "failed"
                checkpoint.error_details = output_data.get('error', 'Unknown error')
            
            self._persist_execution(execution)
            
            # Trigger callback
            callback = self._checkpoint_callbacks.get(checkpoint_name)
            if callback:
                try:
                    callback(checkpoint)
                except Exception as e:
                    logger.error(f"Checkpoint callback failed: {e}")
            
            logger.info(f"Completed checkpoint: {checkpoint_name} (success: {success})")
            return True
    
    def pause_execution(self, execution_id: str, checkpoint_name: str) -> bool:
        """Pause execution at a specific checkpoint."""
        with self._lock:
            execution = self._executions.get(execution_id)
            if not execution:
                return False
            
            execution.state = "paused"
            execution.current_checkpoint = checkpoint_name
            
            # Find and pause the checkpoint
            for checkpoint in execution.checkpoints:
                if checkpoint.checkpoint_name == checkpoint_name:
                    checkpoint.state = CheckpointState.PAUSED
                    break
            
            self._persist_execution(execution)
            logger.info(f"Paused execution {execution_id} at {checkpoint_name}")
            return True
    
    def resume_execution(self, execution_id: str) -> bool:
        """Resume a paused execution."""
        with self._lock:
            execution = self._executions.get(execution_id)
            if not execution or execution.state != "paused":
                return False
            
            execution.state = "running"
            
            # Resume current checkpoint
            if execution.current_checkpoint:
                for checkpoint in execution.checkpoints:
                    if (checkpoint.checkpoint_name == execution.current_checkpoint and 
                        checkpoint.state == CheckpointState.PAUSED):
                        checkpoint.state = CheckpointState.ACTIVE
                        break
            
            self._persist_execution(execution)
            logger.info(f"Resumed execution: {execution_id}")
            return True
    
    def approve_checkpoint(self, execution_id: str, checkpoint_name: str, approved: bool) -> bool:
        """Approve or deny a checkpoint requiring approval."""
        with self._lock:
            execution = self._executions.get(execution_id)
            if not execution:
                return False
            
            # Find checkpoint
            checkpoint = None
            for cp in execution.checkpoints:
                if cp.checkpoint_name == checkpoint_name:
                    checkpoint = cp
                    break
            
            if not checkpoint or not checkpoint.approval_required:
                return False
            
            # Update approval status
            checkpoint.approval_status = "approved" if approved else "denied"
            
            if approved:
                checkpoint.state = CheckpointState.ACTIVE
                execution.state = "running"
                logger.info(f"Approved checkpoint: {checkpoint_name}")
            else:
                checkpoint.state = CheckpointState.SKIPPED
                logger.info(f"Denied checkpoint: {checkpoint_name}")
            
            self._persist_execution(execution)
            return True
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get current execution status."""
        with self._lock:
            execution = self._executions.get(execution_id)
            if not execution:
                return None
            
            return {
                "execution_id": execution.execution_id,
                "correlation_id": execution.correlation_id,
                "workflow_name": execution.workflow_name,
                "state": execution.state,
                "current_checkpoint": execution.current_checkpoint,
                "started_at": execution.started_at,
                "completed_at": execution.completed_at,
                "total_checkpoints": len(execution.checkpoints),
                "completed_checkpoints": len([cp for cp in execution.checkpoints 
                                            if cp.state == CheckpointState.COMPLETED]),
                "failed_checkpoints": len([cp for cp in execution.checkpoints 
                                         if cp.state == CheckpointState.FAILED]),
                "pending_approvals": len([cp for cp in execution.checkpoints 
                                        if cp.approval_status == "pending"])
            }
    
    def list_executions(self, state_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all executions with optional state filter."""
        with self._lock:
            executions = []
            for execution in self._executions.values():
                if state_filter is None or execution.state == state_filter:
                    executions.append(self.get_execution_status(execution.execution_id))
            return executions
    
    def get_checkpoint_history(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get checkpoint history for an execution."""
        with self._lock:
            execution = self._executions.get(execution_id)
            if not execution:
                return []
            
            return [cp.to_dict() for cp in execution.checkpoints]
    
    def _request_approval(self, execution_id: str, checkpoint: CheckpointExecution):
        """Request approval for a checkpoint."""
        callback = self._approval_callbacks.get('default')
        if callback:
            try:
                callback(execution_id, checkpoint)
            except Exception as e:
                logger.error(f"Approval callback failed: {e}")
        else:
            logger.warning(f"No approval callback registered for {checkpoint.checkpoint_name}")
    
    def _persist_execution(self, execution: WorkflowExecution):
        """Persist execution to storage."""
        try:
            file_path = self.storage_dir / f"{execution.execution_id}.json"
            with open(file_path, 'w') as f:
                json.dump(execution.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist execution {execution.execution_id}: {e}")
    
    def _load_persisted_executions(self):
        """Load persisted executions from storage."""
        try:
            for file_path in self.storage_dir.glob("exec_*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    execution = WorkflowExecution.from_dict(data)
                    self._executions[execution.execution_id] = execution
                    
                except Exception as e:
                    logger.error(f"Failed to load execution from {file_path}: {e}")
                    
            logger.info(f"Loaded {len(self._executions)} persisted executions")
            
        except Exception as e:
            logger.error(f"Failed to load persisted executions: {e}")
    
    def cleanup_old_executions(self, max_age_days: int = 30):
        """Clean up old completed executions."""
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        
        with self._lock:
            to_remove = []
            for execution_id, execution in self._executions.items():
                if execution.state in ["completed", "failed"]:
                    try:
                        started_time = datetime.fromisoformat(execution.started_at).timestamp()
                        if started_time < cutoff_time:
                            to_remove.append(execution_id)
                    except Exception:
                        continue
            
            for execution_id in to_remove:
                del self._executions[execution_id]
                
                # Remove persisted file
                file_path = self.storage_dir / f"{execution_id}.json"
                if file_path.exists():
                    file_path.unlink()
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old executions")


# Integration helper for existing planner
def enhance_planner_with_checkpoints(planner, checkpoint_manager: CheckpointManager):
    """Enhance existing planner with checkpoint management."""
    
    original_execute_capability = planner._execute_capability
    
    def checkpoint_aware_execute_capability(capability: str, state):
        """Execute capability with checkpoint management."""
        # Create checkpoint
        checkpoint = checkpoint_manager.create_checkpoint(
            execution_id=f"exec_{state.correlation_id}",
            checkpoint_name=f"pre_{capability}",
            agent_id="planner",
            input_data={"capability": capability, "state_data": state.data},
            approval_required=capability in ["write_file", "upload_gist", "add_frontmatter"]
        )
        
        try:
            # Execute original logic
            result = original_execute_capability(capability, state)
            
            # Complete checkpoint on success
            checkpoint_manager.complete_checkpoint(
                execution_id=f"exec_{state.correlation_id}",
                checkpoint_name=f"pre_{capability}",
                output_data={"success": True, "result": "capability_executed"},
                success=True
            )
            
            return result
            
        except Exception as e:
            # Complete checkpoint on failure
            checkpoint_manager.complete_checkpoint(
                execution_id=f"exec_{state.correlation_id}",
                checkpoint_name=f"pre_{capability}",
                output_data={"success": False, "error": str(e)},
                success=False
            )
            raise
    
    # Replace method
    planner._execute_capability = checkpoint_aware_execute_capability
    planner.checkpoint_manager = checkpoint_manager
    
    return planner