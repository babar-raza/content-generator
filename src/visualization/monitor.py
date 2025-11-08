"""
Visual Orchestration Monitor - Core monitoring system for UCOP workflows

Tracks agent execution, data flows, and provides real-time visibility
into workflow orchestration with MCP-compliant interfaces.
"""

import asyncio
import logging
from collections import deque, defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import threading

from ..mcp.protocol import (
    FlowEvent, FlowResource, ResourceStatus,
    create_resource_uri, ResourceType
)

logger = logging.getLogger(__name__)


@dataclass
class AgentMetrics:
    """Real-time agent performance metrics."""
    agent_id: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_duration_ms: int = 0
    avg_duration_ms: float = 0.0
    last_execution: Optional[datetime] = None
    current_status: ResourceStatus = ResourceStatus.PENDING
    execution_history: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def update_execution(self, duration_ms: int, success: bool):
        """Update metrics after an execution."""
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        
        self.total_duration_ms += duration_ms
        self.avg_duration_ms = self.total_duration_ms / self.total_executions
        self.last_execution = datetime.now(timezone.utc)
        
        self.execution_history.append({
            "timestamp": self.last_execution.isoformat(),
            "duration_ms": duration_ms,
            "success": success
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": (
                self.successful_executions / self.total_executions
                if self.total_executions > 0 else 0.0
            ),
            "avg_duration_ms": self.avg_duration_ms,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "current_status": self.current_status.value,
            "recent_executions": list(self.execution_history)
        }


class VisualOrchestrationMonitor:
    """
    Core monitoring system for visual orchestration.
    
    Tracks:
    - Agent executions and performance
    - Data flow between agents
    - System-wide metrics
    - Bottleneck detection
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        
        # Agent tracking
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        
        # Flow tracking
        self.active_flows: Dict[str, List[FlowEvent]] = {}  # job_id -> flows
        self.flow_history: deque = deque(maxlen=10000)
        
        # Job tracking
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        
        # Callbacks for real-time updates
        self.event_callbacks: List[Callable] = []
        
        # Monitoring state
        self.monitoring_enabled = False
        self.start_time = datetime.now(timezone.utc)
        
        logger.info("Visual Orchestration Monitor initialized")
    
    # ========================================================================
    # Agent Management
    # ========================================================================
    
    def register_agent(
        self,
        agent_id: str,
        name: str,
        agent_type: str,
        capabilities: List[str] = None,
        metadata: Dict[str, Any] = None
    ):
        """Register an agent for monitoring."""
        with self._lock:
            self.registered_agents[agent_id] = {
                "id": agent_id,
                "name": name,
                "type": agent_type,
                "capabilities": capabilities or [],
                "metadata": metadata or {},
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "uri": create_resource_uri(ResourceType.AGENT, agent_id)
            }
            
            if agent_id not in self.agent_metrics:
                self.agent_metrics[agent_id] = AgentMetrics(agent_id=agent_id)
            
            logger.info(f"Agent registered: {agent_id} ({name})")
            self._emit_event("agent_registered", {"agent_id": agent_id})
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent."""
        with self._lock:
            if agent_id in self.registered_agents:
                del self.registered_agents[agent_id]
                logger.info(f"Agent unregistered: {agent_id}")
                self._emit_event("agent_unregistered", {"agent_id": agent_id})
    
    def update_agent_status(self, agent_id: str, status: ResourceStatus):
        """Update agent execution status."""
        with self._lock:
            if agent_id in self.agent_metrics:
                self.agent_metrics[agent_id].current_status = status
                self._emit_event("agent_status_changed", {
                    "agent_id": agent_id,
                    "status": status.value
                })
    
    def get_agent_metrics(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific agent."""
        with self._lock:
            metrics = self.agent_metrics.get(agent_id)
            return metrics.to_dict() if metrics else None
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents with their metrics."""
        with self._lock:
            agents = []
            for agent_id, agent_info in self.registered_agents.items():
                metrics = self.agent_metrics.get(agent_id)
                agent_data = agent_info.copy()
                if metrics:
                    agent_data["metrics"] = metrics.to_dict()
                agents.append(agent_data)
            return agents
    
    # ========================================================================
    # Flow Monitoring
    # ========================================================================
    
    def record_flow_event(
        self,
        job_id: str,
        source_agent: str,
        target_agent: str,
        event_type: str,
        data_size: int = 0,
        correlation_id: Optional[str] = None
    ) -> str:
        """Record a data flow event between agents."""
        with self._lock:
            event_id = f"flow_{len(self.flow_history)}"
            
            flow_event = FlowEvent(
                event_id=event_id,
                source_agent=source_agent,
                target_agent=target_agent,
                event_type=event_type,
                timestamp=datetime.now(timezone.utc),
                data_size=data_size,
                status=ResourceStatus.RUNNING
            )
            
            # Add to active flows
            if job_id not in self.active_flows:
                self.active_flows[job_id] = []
            self.active_flows[job_id].append(flow_event)
            
            # Add to history
            self.flow_history.append({
                "job_id": job_id,
                "event": flow_event.model_dump(),
                "correlation_id": correlation_id
            })
            
            self._emit_event("flow_event", {
                "job_id": job_id,
                "event_id": event_id,
                "source": source_agent,
                "target": target_agent
            })
            
            return event_id
    
    def complete_flow_event(
        self,
        job_id: str,
        event_id: str,
        duration_ms: int,
        status: ResourceStatus = ResourceStatus.COMPLETED
    ):
        """Mark a flow event as completed."""
        with self._lock:
            if job_id in self.active_flows:
                for event in self.active_flows[job_id]:
                    if event.event_id == event_id:
                        event.duration_ms = duration_ms
                        event.status = status
                        break
    
    def get_job_flows(self, job_id: str) -> Optional[FlowResource]:
        """Get all flows for a job."""
        with self._lock:
            if job_id not in self.active_flows:
                return None
            
            return FlowResource(
                uri=create_resource_uri(ResourceType.FLOW, job_id),
                job_id=job_id,
                correlation_id=job_id,
                events=self.active_flows[job_id],
                bottlenecks=self._detect_bottlenecks(job_id)
            )
    
    def _detect_bottlenecks(self, job_id: str) -> List[Dict[str, Any]]:
        """Detect bottlenecks in a job's data flow."""
        bottlenecks = []
        
        if job_id not in self.active_flows:
            return bottlenecks
        
        # Analyze flow events for delays
        events = self.active_flows[job_id]
        agent_times: Dict[str, List[int]] = defaultdict(list)
        
        for event in events:
            if event.duration_ms:
                agent_times[event.source_agent].append(event.duration_ms)
        
        # Find agents with high average durations
        avg_threshold = 0
        all_durations = []
        for times in agent_times.values():
            all_durations.extend(times)
        
        if all_durations:
            avg_threshold = sum(all_durations) / len(all_durations) * 2
        
        for agent_id, times in agent_times.items():
            avg_time = sum(times) / len(times)
            if avg_time > avg_threshold:
                bottlenecks.append({
                    "agent_id": agent_id,
                    "avg_duration_ms": avg_time,
                    "threshold_ms": avg_threshold,
                    "severity": "high" if avg_time > avg_threshold * 1.5 else "medium"
                })
        
        return bottlenecks
    
    # ========================================================================
    # Job Tracking
    # ========================================================================
    
    def track_job_start(
        self,
        job_id: str,
        workflow_name: str,
        input_params: Dict[str, Any]
    ):
        """Start tracking a job."""
        with self._lock:
            self.active_jobs[job_id] = {
                "job_id": job_id,
                "workflow_name": workflow_name,
                "input_params": input_params,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": ResourceStatus.RUNNING.value,
                "uri": create_resource_uri(ResourceType.JOB, job_id)
            }
            
            self._emit_event("job_started", {"job_id": job_id})
    
    def track_job_completion(
        self,
        job_id: str,
        status: ResourceStatus,
        result: Optional[Dict[str, Any]] = None
    ):
        """Track job completion."""
        with self._lock:
            if job_id in self.active_jobs:
                self.active_jobs[job_id]["status"] = status.value
                self.active_jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
                self.active_jobs[job_id]["result"] = result
                
                self._emit_event("job_completed", {
                    "job_id": job_id,
                    "status": status.value
                })
    
    def track_agent_execution(
        self,
        job_id: str,
        agent_id: str,
        duration_ms: int,
        success: bool
    ):
        """Track an agent execution."""
        with self._lock:
            if agent_id in self.agent_metrics:
                self.agent_metrics[agent_id].update_execution(duration_ms, success)
                
                self._emit_event("agent_executed", {
                    "job_id": job_id,
                    "agent_id": agent_id,
                    "duration_ms": duration_ms,
                    "success": success
                })
    
    # ========================================================================
    # Monitoring Control
    # ========================================================================
    
    def start_monitoring(self):
        """Enable monitoring."""
        self.monitoring_enabled = True
        self.start_time = datetime.now(timezone.utc)
        logger.info("Visual orchestration monitoring started")
    
    def stop_monitoring(self):
        """Disable monitoring."""
        self.monitoring_enabled = False
        logger.info("Visual orchestration monitoring stopped")
    
    def add_event_callback(self, callback: Callable):
        """Add callback for real-time events."""
        self.event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: Callable):
        """Remove event callback."""
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)
    
    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit event to all callbacks."""
        if not self.monitoring_enabled:
            return
        
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
    
    # ========================================================================
    # System Metrics
    # ========================================================================
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get overall system metrics."""
        with self._lock:
            total_executions = sum(m.total_executions for m in self.agent_metrics.values())
            total_success = sum(m.successful_executions for m in self.agent_metrics.values())
            
            return {
                "uptime_seconds": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
                "monitoring_enabled": self.monitoring_enabled,
                "registered_agents": len(self.registered_agents),
                "active_jobs": len(self.active_jobs),
                "total_executions": total_executions,
                "success_rate": (total_success / total_executions) if total_executions > 0 else 0.0,
                "flow_events_tracked": len(self.flow_history),
                "agents_with_metrics": len(self.agent_metrics)
            }
    
    def reset_metrics(self):
        """Reset all metrics (for testing)."""
        with self._lock:
            self.agent_metrics.clear()
            self.active_flows.clear()
            self.flow_history.clear()
            self.active_jobs.clear()
            logger.info("All metrics reset")


# Singleton instance
_monitor_instance: Optional[VisualOrchestrationMonitor] = None
_monitor_lock = threading.Lock()


def get_monitor() -> VisualOrchestrationMonitor:
    """Get the singleton monitor instance."""
    global _monitor_instance
    
    if _monitor_instance is None:
        with _monitor_lock:
            if _monitor_instance is None:
                _monitor_instance = VisualOrchestrationMonitor()
    
    return _monitor_instance
