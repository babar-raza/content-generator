"""Agent Health Monitoring - Track agent execution metrics and failures.

Provides real-time health monitoring for all agents with failure tracking
and performance metrics.
"""

import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import deque, defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ExecutionRecord:
    """Record of a single agent execution."""
    timestamp: str
    success: bool
    duration_ms: float
    job_id: str
    error: Optional[str] = None
    error_type: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None


class AgentHealthMonitor:
    """Monitor agent health and track execution metrics."""
    
    def __init__(self, window_size: int = 100):
        """Initialize health monitor.
        
        Args:
            window_size: Number of recent executions to track per agent
        """
        self.window_size = window_size
        self._lock = threading.RLock()
        
        # Execution history per agent (sliding window)
        self.execution_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        
        # Recent failures per agent (last 10)
        self.recent_failures: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10)
        )
        
        # Agent metadata
        self.agent_names: Dict[str, str] = {}
        
        # Job history per agent (last 100 jobs)
        self.agent_job_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        
        logger.info(f"AgentHealthMonitor initialized with window size {window_size}")
    
    def record_execution(
        self,
        agent_id: str,
        success: bool,
        duration_ms: float,
        job_id: str,
        agent_name: Optional[str] = None,
        error: Optional[str] = None,
        error_type: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None
    ):
        """Record an agent execution.
        
        Args:
            agent_id: Agent identifier
            success: Whether execution succeeded
            duration_ms: Execution duration in milliseconds
            job_id: Job identifier
            agent_name: Human-readable agent name
            error: Error message if failed
            error_type: Type of error
            input_data: Input data for the execution
            stack_trace: Full stack trace if available
        """
        with self._lock:
            # Store agent name
            if agent_name:
                self.agent_names[agent_id] = agent_name
            
            # Create execution record
            record = ExecutionRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=success,
                duration_ms=duration_ms,
                job_id=job_id,
                error=error,
                error_type=error_type,
                input_data=input_data,
                stack_trace=stack_trace
            )
            
            # Add to execution history
            self.execution_history[agent_id].append(record)
            
            # Track failures separately
            if not success and error:
                self.recent_failures[agent_id].append(record)
            
            # Record job usage
            self.record_agent_usage(
                agent_id=agent_id,
                job_id=job_id,
                status="completed" if success else "failed",
                duration=duration_ms / 1000.0,  # Convert to seconds
                timestamp=datetime.now(timezone.utc)
            )
            
            logger.debug(
                f"Recorded execution for {agent_id}: "
                f"success={success}, duration={duration_ms}ms"
            )
    
    def record_agent_usage(
        self,
        agent_id: str,
        job_id: str,
        status: str,
        duration: float,
        timestamp: datetime
    ):
        """Record agent usage in a job.
        
        Args:
            agent_id: Agent identifier
            job_id: Job identifier
            status: Job status (completed, failed, running)
            duration: Duration in seconds
            timestamp: Timestamp of usage
        """
        with self._lock:
            # Check if this job is already recorded (avoid duplicates)
            existing_jobs = [j['job_id'] for j in self.agent_job_history[agent_id]]
            
            if job_id not in existing_jobs or len(existing_jobs) == 0:
                self.agent_job_history[agent_id].append({
                    'job_id': job_id,
                    'status': status,
                    'duration': duration,
                    'timestamp': timestamp.isoformat()
                })
            else:
                # Update existing record
                for job_record in self.agent_job_history[agent_id]:
                    if job_record['job_id'] == job_id:
                        job_record['status'] = status
                        job_record['duration'] = duration
                        job_record['timestamp'] = timestamp.isoformat()
                        break
    
    def get_agent_job_history(
        self,
        agent_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get job history for an agent.
        
        Args:
            agent_id: Agent identifier
            limit: Maximum number of jobs to return
            
        Returns:
            List of job usage records
        """
        with self._lock:
            history = list(self.agent_job_history.get(agent_id, []))
            # Sort by timestamp (newest first)
            history.sort(key=lambda x: x['timestamp'], reverse=True)
            return history[:limit]
    
    def get_agent_health(self, agent_id: str) -> Dict[str, Any]:
        """Get health metrics for a specific agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Dictionary with health metrics
        """
        with self._lock:
            executions = list(self.execution_history.get(agent_id, []))
            
            if not executions:
                return {
                    "agent_id": agent_id,
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "last_execution_time": None,
                    "average_duration_ms": None,
                    "error_rate": 0.0,
                    "status": "unknown"
                }
            
            # Calculate metrics
            total = len(executions)
            successful = sum(1 for e in executions if e.success)
            failed = total - successful
            error_rate = failed / total if total > 0 else 0.0
            
            # Calculate average duration
            durations = [e.duration_ms for e in executions if e.duration_ms]
            avg_duration = sum(durations) / len(durations) if durations else None
            
            # Last execution time
            last_execution = executions[-1].timestamp if executions else None
            
            # Determine health status
            status = self._calculate_status(error_rate)
            
            return {
                "agent_id": agent_id,
                "total_executions": total,
                "successful_executions": successful,
                "failed_executions": failed,
                "last_execution_time": last_execution,
                "average_duration_ms": avg_duration,
                "error_rate": error_rate,
                "status": status
            }
    
    def get_all_agents_health(self) -> List[Dict[str, Any]]:
        """Get health metrics for all agents.
        
        Returns:
            List of health metrics for each agent
        """
        with self._lock:
            agent_ids = set(self.execution_history.keys())
            return [self.get_agent_health(agent_id) for agent_id in agent_ids]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary.
        
        Returns:
            Summary with counts by status
        """
        with self._lock:
            all_health = self.get_all_agents_health()
            
            summary = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_agents": len(all_health),
                "healthy_agents": sum(1 for h in all_health if h["status"] == "healthy"),
                "degraded_agents": sum(1 for h in all_health if h["status"] == "degraded"),
                "failing_agents": sum(1 for h in all_health if h["status"] == "failing"),
                "unknown_agents": sum(1 for h in all_health if h["status"] == "unknown"),
                "agents": all_health
            }
            
            return summary
    
    def get_agent_failures(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent failures for an agent.
        
        Args:
            agent_id: Agent identifier
            limit: Maximum number of failures to return
            
        Returns:
            List of failure details
        """
        with self._lock:
            failures = list(self.recent_failures.get(agent_id, []))
            
            # Return most recent failures first
            failures.reverse()
            failures = failures[:limit]
            
            return [
                {
                    "timestamp": f.timestamp,
                    "agent_id": agent_id,
                    "job_id": f.job_id,
                    "error_type": f.error_type or "unknown",
                    "error_message": f.error or "No error message",
                    "input_data": f.input_data,
                    "stack_trace": f.stack_trace
                }
                for f in failures
            ]
    
    def reset_agent_health(self, agent_id: str):
        """Reset health metrics for an agent.
        
        Args:
            agent_id: Agent identifier
        """
        with self._lock:
            if agent_id in self.execution_history:
                self.execution_history[agent_id].clear()
            if agent_id in self.recent_failures:
                self.recent_failures[agent_id].clear()
            if agent_id in self.agent_job_history:
                self.agent_job_history[agent_id].clear()
            
            logger.info(f"Reset health metrics for agent {agent_id}")
    
    def get_agent_name(self, agent_id: str) -> str:
        """Get human-readable name for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent name or agent_id if not found
        """
        return self.agent_names.get(agent_id, agent_id)
    
    def _calculate_status(self, error_rate: float) -> str:
        """Calculate health status based on error rate.
        
        Args:
            error_rate: Error rate (0-1)
            
        Returns:
            Health status: healthy, degraded, or failing
        """
        if error_rate < 0.05:  # Less than 5%
            return "healthy"
        elif error_rate < 0.20:  # 5-20%
            return "degraded"
        else:  # Greater than 20%
            return "failing"


# Global health monitor instance
_health_monitor = None


def get_health_monitor() -> AgentHealthMonitor:
    """Get or create the global health monitor instance.
    
    Returns:
        AgentHealthMonitor instance
    """
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = AgentHealthMonitor()
    return _health_monitor
