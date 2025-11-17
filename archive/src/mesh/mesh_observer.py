"""
Mesh Observability System - Phase 10
Provides comprehensive monitoring, visualization, and debugging for the agent mesh.
"""

import time
import threading
import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple, NamedTuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import uuid

from src.core.contracts import FlowControlStatus, CapacityLevel
from src.core.config import Config

logger = logging.getLogger(__name__)


class AgentStatusType(Enum):
    """Agent execution status types"""
    IDLE = "idle"
    EXECUTING = "executing"
    WAITING = "waiting"
    BLOCKED = "blocked"
    OVERLOADED = "overloaded"
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class ExecutionSnapshot:
    """Snapshot of an agent's current execution state"""
    agent_id: str
    status: AgentStatusType
    current_capability: Optional[str] = None
    correlation_id: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    load: int = 0
    max_capacity: int = 1
    health_score: float = 1.0
    last_activity: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class WorkflowSnapshot:
    """Snapshot of a workflow's current state"""
    correlation_id: str
    goal: Optional[str] = None
    status: str = "in_progress"
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    completed_capabilities: Set[str] = field(default_factory=set)
    active_agents: Set[str] = field(default_factory=set)
    waiting_agents: Set[str] = field(default_factory=set)
    blocked_agents: Set[str] = field(default_factory=set)
    progress: float = 0.0
    estimated_completion: Optional[datetime] = None
    events_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class CapabilityTrace:
    """Execution trace for a specific capability"""
    capability: str
    agent_id: str
    correlation_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    status: str = "executing"  # executing, completed, failed, timed_out
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeadlockInfo:
    """Information about a detected deadlock"""
    deadlock_id: str
    correlation_id: str
    detected_at: datetime
    stuck_agents: List[str]
    blocked_capabilities: List[str]
    missing_dependencies: List[str]
    duration_stuck: float  # seconds
    confidence: float  # 0.0 to 1.0
    suggested_resolution: List[str]


@dataclass
class BottleneckInfo:
    """Information about performance bottlenecks"""
    capability: str
    agent_id: str
    avg_duration: float
    current_queue_size: int
    threshold_exceeded: bool
    impact_score: float  # 0.0 to 1.0
    suggested_optimizations: List[str]


class ExecutionTimeline:
    """Timeline tracking for capability executions"""
    
    def __init__(self, max_entries: int = 1000):
        self.traces: Dict[str, CapabilityTrace] = {}  # trace_id -> trace
        self.by_capability: Dict[str, List[str]] = defaultdict(list)  # capability -> trace_ids
        self.by_correlation: Dict[str, List[str]] = defaultdict(list)  # correlation_id -> trace_ids
        self.by_agent: Dict[str, List[str]] = defaultdict(list)  # agent_id -> trace_ids
        self.max_entries = max_entries
        self.lock = threading.RLock()
        
    def start_trace(self, capability: str, agent_id: str, correlation_id: str,
                    input_data: Dict[str, Any] = None) -> str:
        """Start tracking a capability execution"""
        trace_id = f"{capability}_{agent_id}_{uuid.uuid4().hex[:8]}"
        
        trace = CapabilityTrace(
            capability=capability,
            agent_id=agent_id,
            correlation_id=correlation_id,
            start_time=datetime.now(),
            input_data=input_data or {},
            status="executing"
        )
        
        with self.lock:
            self.traces[trace_id] = trace
            self.by_capability[capability].append(trace_id)
            self.by_correlation[correlation_id].append(trace_id)
            self.by_agent[agent_id].append(trace_id)
            
            self._cleanup_old_traces()
        
        logger.debug(f"Started trace {trace_id} for {capability} on {agent_id}")
        return trace_id
    
    def end_trace(self, trace_id: str, status: str = "completed", 
                  output_data: Dict[str, Any] = None, error: str = None) -> None:
        """End a capability execution trace"""
        with self.lock:
            if trace_id not in self.traces:
                logger.warning(f"Trace {trace_id} not found for completion")
                return
            
            trace = self.traces[trace_id]
            trace.end_time = datetime.now()
            trace.duration = (trace.end_time - trace.start_time).total_seconds()
            trace.status = status
            trace.output_data = output_data or {}
            trace.error = error
        
        logger.debug(f"Ended trace {trace_id} with status {status} in {trace.duration:.2f}s")
    
    def get_traces_for_capability(self, capability: str) -> List[CapabilityTrace]:
        """Get all traces for a specific capability"""
        with self.lock:
            trace_ids = self.by_capability.get(capability, [])
            return [self.traces[tid] for tid in trace_ids if tid in self.traces]
    
    def get_traces_for_correlation(self, correlation_id: str) -> List[CapabilityTrace]:
        """Get all traces for a specific workflow"""
        with self.lock:
            trace_ids = self.by_correlation.get(correlation_id, [])
            return [self.traces[tid] for tid in trace_ids if tid in self.traces]
    
    def get_active_traces(self) -> List[CapabilityTrace]:
        """Get all currently executing traces"""
        with self.lock:
            return [trace for trace in self.traces.values() 
                   if trace.status == "executing"]
    
    def _cleanup_old_traces(self) -> None:
        """Remove old traces to prevent memory growth"""
        if len(self.traces) <= self.max_entries:
            return
        
        # Sort by start time and remove oldest
        trace_items = sorted(self.traces.items(), 
                           key=lambda x: x[1].start_time)
        
        to_remove = len(self.traces) - int(self.max_entries * 0.8)
        
        for trace_id, trace in trace_items[:to_remove]:
            # Remove from all indexes
            del self.traces[trace_id]
            
            self.by_capability[trace.capability] = [
                tid for tid in self.by_capability[trace.capability] 
                if tid != trace_id
            ]
            self.by_correlation[trace.correlation_id] = [
                tid for tid in self.by_correlation[trace.correlation_id]
                if tid != trace_id  
            ]
            self.by_agent[trace.agent_id] = [
                tid for tid in self.by_agent[trace.agent_id]
                if tid != trace_id
            ]


class DeadlockDetector:
    """Detects stuck workflows and potential deadlocks"""
    
    def __init__(self, stuck_threshold_seconds: float = 300.0):
        self.stuck_threshold = stuck_threshold_seconds
        self.detected_deadlocks: Dict[str, DeadlockInfo] = {}
        self.lock = threading.RLock()
        
    def analyze_workflows(self, workflow_snapshots: Dict[str, WorkflowSnapshot],
                         agent_snapshots: Dict[str, ExecutionSnapshot]) -> List[DeadlockInfo]:
        """Analyze workflows and agents for potential deadlocks"""
        deadlocks = []
        current_time = datetime.now()
        
        for correlation_id, workflow in workflow_snapshots.items():
            # Skip if workflow recently completed
            if workflow.status in ["completed", "failed"]:
                continue
            
            # Check if workflow has been stuck
            time_since_activity = (current_time - workflow.last_activity).total_seconds()
            
            if time_since_activity > self.stuck_threshold:
                deadlock = self._analyze_stuck_workflow(
                    workflow, agent_snapshots, time_since_activity
                )
                if deadlock:
                    deadlocks.append(deadlock)
        
        # Update detected deadlocks
        with self.lock:
            for deadlock in deadlocks:
                self.detected_deadlocks[deadlock.deadlock_id] = deadlock
        
        return deadlocks
    
    def _analyze_stuck_workflow(self, workflow: WorkflowSnapshot,
                               agent_snapshots: Dict[str, ExecutionSnapshot],
                               stuck_duration: float) -> Optional[DeadlockInfo]:
        """Analyze a specific stuck workflow"""
        
        # Find agents involved in this workflow
        involved_agents = workflow.active_agents | workflow.waiting_agents | workflow.blocked_agents
        
        # Analyze why agents are stuck
        stuck_agents = []
        blocked_capabilities = []
        missing_dependencies = []
        
        for agent_id in involved_agents:
            if agent_id not in agent_snapshots:
                continue
                
            agent = agent_snapshots[agent_id]
            
            if agent.status == AgentStatusType.WAITING:
                stuck_agents.append(agent_id)
                if agent.current_capability:
                    blocked_capabilities.append(agent.current_capability)
            elif agent.status == AgentStatusType.BLOCKED:
                stuck_agents.append(agent_id)
        
        # Calculate confidence based on multiple factors
        confidence = self._calculate_deadlock_confidence(
            workflow, stuck_agents, stuck_duration
        )
        
        if confidence < 0.5:  # Only report high-confidence deadlocks
            return None
        
        # Generate suggested resolutions
        suggestions = self._generate_deadlock_suggestions(
            workflow, stuck_agents, blocked_capabilities
        )
        
        deadlock_id = f"deadlock_{workflow.correlation_id}_{int(time.time())}"
        
        return DeadlockInfo(
            deadlock_id=deadlock_id,
            correlation_id=workflow.correlation_id,
            detected_at=datetime.now(),
            stuck_agents=stuck_agents,
            blocked_capabilities=blocked_capabilities,
            missing_dependencies=missing_dependencies,
            duration_stuck=stuck_duration,
            confidence=confidence,
            suggested_resolution=suggestions
        )
    
    def _calculate_deadlock_confidence(self, workflow: WorkflowSnapshot,
                                     stuck_agents: List[str], 
                                     stuck_duration: float) -> float:
        """Calculate confidence that this is a real deadlock"""
        confidence = 0.0
        
        # Base confidence from stuck duration
        if stuck_duration > self.stuck_threshold * 2:
            confidence += 0.4
        elif stuck_duration > self.stuck_threshold:
            confidence += 0.2
        
        # More agents stuck = higher confidence
        if len(stuck_agents) >= 3:
            confidence += 0.3
        elif len(stuck_agents) >= 2:
            confidence += 0.2
        elif len(stuck_agents) >= 1:
            confidence += 0.1
        
        # No recent progress
        time_since_activity = (datetime.now() - workflow.last_activity).total_seconds()
        if time_since_activity > stuck_duration * 0.8:
            confidence += 0.2
        
        # Error count suggests problems
        if workflow.error_count > 0:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _generate_deadlock_suggestions(self, workflow: WorkflowSnapshot,
                                     stuck_agents: List[str],
                                     blocked_capabilities: List[str]) -> List[str]:
        """Generate suggestions for resolving deadlock"""
        suggestions = []
        
        if stuck_agents:
            suggestions.append(f"Restart stuck agents: {', '.join(stuck_agents)}")
        
        if blocked_capabilities:
            suggestions.append(f"Check capability dependencies: {', '.join(blocked_capabilities)}")
        
        if workflow.error_count > 0:
            suggestions.append("Review recent errors for root cause")
        
        suggestions.extend([
            "Check if required data/context is available",
            "Verify network connectivity and external dependencies",
            "Consider manual intervention or workflow restart"
        ])
        
        return suggestions


class PerformanceAnalyzer:
    """Analyzes system performance and identifies bottlenecks"""
    
    def __init__(self):
        self.execution_history: deque = deque(maxlen=1000)
        self.capability_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.agent_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.lock = threading.RLock()
        
    def record_execution(self, trace: CapabilityTrace) -> None:
        """Record a completed execution for analysis"""
        if trace.duration is None:
            return
            
        with self.lock:
            self.execution_history.append(trace)
            self._update_capability_stats(trace)
            self._update_agent_stats(trace)
    
    def _update_capability_stats(self, trace: CapabilityTrace) -> None:
        """Update statistics for a capability"""
        capability = trace.capability
        
        if capability not in self.capability_stats:
            self.capability_stats[capability] = {
                'total_executions': 0,
                'total_duration': 0.0,
                'success_count': 0,
                'failure_count': 0,
                'durations': deque(maxlen=100)
            }
        
        stats = self.capability_stats[capability]
        stats['total_executions'] += 1
        stats['total_duration'] += trace.duration
        stats['durations'].append(trace.duration)
        
        if trace.status == "completed":
            stats['success_count'] += 1
        else:
            stats['failure_count'] += 1
    
    def _update_agent_stats(self, trace: CapabilityTrace) -> None:
        """Update statistics for an agent"""
        agent_id = trace.agent_id
        
        if agent_id not in self.agent_stats:
            self.agent_stats[agent_id] = {
                'total_executions': 0,
                'total_duration': 0.0,
                'success_count': 0,
                'failure_count': 0,
                'capabilities': set()
            }
        
        stats = self.agent_stats[agent_id]
        stats['total_executions'] += 1
        stats['total_duration'] += trace.duration
        stats['capabilities'].add(trace.capability)
        
        if trace.status == "completed":
            stats['success_count'] += 1
        else:
            stats['failure_count'] += 1
    
    def identify_bottlenecks(self, agent_snapshots: Dict[str, ExecutionSnapshot]) -> List[BottleneckInfo]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # Load bottleneck thresholds from config
        try:
            perf_hints = Config.load_perf_hints()
            thresholds = perf_hints.get("observability", {}).get("bottleneck_thresholds", {})
        except:
            thresholds = {}
        
        with self.lock:
            for capability, stats in self.capability_stats.items():
                if stats['total_executions'] < 3:  # Need some data
                    continue
                
                avg_duration = stats['total_duration'] / stats['total_executions']
                threshold = thresholds.get(capability, 10.0)  # Default 10s threshold
                
                if avg_duration > threshold:
                    # Find the agent currently executing this capability
                    executing_agent = None
                    queue_size = 0
                    
                    for agent_id, agent in agent_snapshots.items():
                        if (agent.current_capability == capability and 
                            agent.status == AgentStatusType.EXECUTING):
                            executing_agent = agent_id
                        elif agent.status == AgentStatusType.WAITING:
                            queue_size += 1
                    
                    if executing_agent:
                        impact_score = min(1.0, avg_duration / threshold)
                        
                        bottleneck = BottleneckInfo(
                            capability=capability,
                            agent_id=executing_agent,
                            avg_duration=avg_duration,
                            current_queue_size=queue_size,
                            threshold_exceeded=True,
                            impact_score=impact_score,
                            suggested_optimizations=self._generate_optimization_suggestions(
                                capability, avg_duration, queue_size
                            )
                        )
                        bottlenecks.append(bottleneck)
        
        return bottlenecks
    
    def _generate_optimization_suggestions(self, capability: str, 
                                         avg_duration: float, 
                                         queue_size: int) -> List[str]:
        """Generate optimization suggestions for bottlenecks"""
        suggestions = []
        
        if avg_duration > 10.0:
            suggestions.append("Optimize capability implementation")
            suggestions.append("Enable caching for deterministic operations")
        
        if queue_size > 5:
            suggestions.append("Add more agents with this capability")
            suggestions.append("Implement parallel execution")
        
        suggestions.extend([
            "Review resource allocation",
            "Check for external service delays",
            "Consider capability splitting or batching"
        ])
        
        return suggestions


class MeshObserver:
    """
    Central observability system for the agent mesh.
    Provides visualization, tracing, and debugging capabilities.
    """
    
    def __init__(self, event_bus=None, state_store=None, registry=None):
        self.event_bus = event_bus
        self.state_store = state_store
        self.registry = registry
        
        # Core components
        self.timeline = ExecutionTimeline()
        self.deadlock_detector = DeadlockDetector()
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Current state tracking
        self.agent_snapshots: Dict[str, ExecutionSnapshot] = {}
        self.workflow_snapshots: Dict[str, WorkflowSnapshot] = {}
        self.active_traces: Dict[str, str] = {}  # work_id -> trace_id
        
        # Configuration
        self.enabled = Config.TIMING_SPANS_ENABLED or Config.PERF_METRICS_ENABLED
        self.update_interval = 5.0  # seconds
        self.deadlock_check_interval = 30.0  # seconds
        
        # Threading
        self.lock = threading.RLock()
        self.monitoring_thread = None
        self.deadlock_thread = None
        self.running = False
        
        if self.enabled:
            self._start_monitoring()
        
        logger.info(f"MeshObserver initialized (enabled: {self.enabled})")
    
    def _start_monitoring(self) -> None:
        """Start background monitoring threads"""
        self.running = True
        
        # State monitoring thread
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        # Deadlock detection thread
        self.deadlock_thread = threading.Thread(
            target=self._deadlock_detection_loop, daemon=True)
        self.deadlock_thread.start()
        
        logger.info("Started MeshObserver background monitoring")
    
    def shutdown(self) -> None:
        """Shutdown the observer"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        if self.deadlock_thread:
            self.deadlock_thread.join(timeout=5.0)
        
        logger.info("MeshObserver shutdown complete")
    
    def _monitoring_loop(self) -> None:
        """Background loop for state monitoring"""
        while self.running:
            try:
                self._update_snapshots()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5.0)
    
    def _deadlock_detection_loop(self) -> None:
        """Background loop for deadlock detection"""
        while self.running:
            try:
                self._check_deadlocks()
                time.sleep(self.deadlock_check_interval)
            except Exception as e:
                logger.error(f"Error in deadlock detection: {e}")
                time.sleep(10.0)
    
    def _update_snapshots(self) -> None:
        """Update current state snapshots"""
        if not self.registry:
            return
        
        try:
            # Get current agent states
            agent_states = self.registry.get_all_agent_states()
            
            with self.lock:
                # Update agent snapshots
                for agent_id, agent_data in agent_states.items():
                    self.agent_snapshots[agent_id] = self._create_agent_snapshot(
                        agent_id, agent_data
                    )
                
                # Update workflow snapshots
                self._update_workflow_snapshots()
                
        except Exception as e:
            logger.error(f"Error updating snapshots: {e}")
    
    def _create_agent_snapshot(self, agent_id: str, 
                              agent_data: Dict[str, Any]) -> ExecutionSnapshot:
        """Create an agent execution snapshot"""
        # Determine agent status
        status = AgentStatusType.IDLE
        current_capability = None
        correlation_id = None
        progress = 0.0
        
        flow_status = agent_data.get('flow_status', 'available')
        current_load = agent_data.get('current_load', 0)
        health_score = agent_data.get('health_score', 1.0)
        
        if flow_status == 'overloaded':
            status = AgentStatusType.OVERLOADED
        elif current_load > 0:
            status = AgentStatusType.EXECUTING
            # Try to get current work details
            if 'current_work' in agent_data:
                work = agent_data['current_work']
                current_capability = work.get('capability')
                correlation_id = work.get('correlation_id')
                
                # Estimate progress based on time elapsed
                start_time = work.get('start_time')
                if start_time and isinstance(start_time, datetime):
                    elapsed = (datetime.now() - start_time).total_seconds()
                    estimated_duration = work.get('estimated_duration', 30.0)
                    progress = min(0.95, elapsed / estimated_duration)
        elif health_score < 0.5:
            status = AgentStatusType.FAILED
        
        return ExecutionSnapshot(
            agent_id=agent_id,
            status=status,
            current_capability=current_capability,
            correlation_id=correlation_id,
            progress=progress,
            load=current_load,
            max_capacity=agent_data.get('max_capacity', 1),
            health_score=health_score,
            last_activity=agent_data.get('last_activity', datetime.now()),
            metadata=agent_data
        )
    
    def _update_workflow_snapshots(self) -> None:
        """Update workflow snapshots from state store"""
        if not self.state_store:
            return
        
        # Get all active correlations
        try:
            correlations = self.state_store.get_all_correlations()
            
            for correlation_id in correlations:
                workflow_data = self.state_store.get_correlation_data(correlation_id)
                
                self.workflow_snapshots[correlation_id] = self._create_workflow_snapshot(
                    correlation_id, workflow_data
                )
                
        except Exception as e:
            logger.debug(f"Could not update workflow snapshots: {e}")
    
    def _create_workflow_snapshot(self, correlation_id: str,
                                 workflow_data: Dict[str, Any]) -> WorkflowSnapshot:
        """Create a workflow snapshot"""
        # Find agents working on this correlation
        active_agents = set()
        waiting_agents = set()
        blocked_agents = set()
        
        for agent_id, agent in self.agent_snapshots.items():
            if agent.correlation_id == correlation_id:
                if agent.status == AgentStatusType.EXECUTING:
                    active_agents.add(agent_id)
                elif agent.status == AgentStatusType.WAITING:
                    waiting_agents.add(agent_id)
                elif agent.status == AgentStatusType.BLOCKED:
                    blocked_agents.add(agent_id)
        
        # Calculate progress
        completed_capabilities = set(workflow_data.get('completed_capabilities', []))
        total_expected = len(workflow_data.get('required_capabilities', [])) or 10
        progress = len(completed_capabilities) / total_expected
        
        return WorkflowSnapshot(
            correlation_id=correlation_id,
            goal=workflow_data.get('goal'),
            status=workflow_data.get('status', 'in_progress'),
            start_time=workflow_data.get('start_time', datetime.now()),
            last_activity=workflow_data.get('last_activity', datetime.now()),
            completed_capabilities=completed_capabilities,
            active_agents=active_agents,
            waiting_agents=waiting_agents,
            blocked_agents=blocked_agents,
            progress=progress,
            events_count=workflow_data.get('events_count', 0),
            error_count=workflow_data.get('error_count', 0),
            last_error=workflow_data.get('last_error')
        )
    
    def _check_deadlocks(self) -> None:
        """Check for deadlocks and notify if found"""
        with self.lock:
            deadlocks = self.deadlock_detector.analyze_workflows(
                self.workflow_snapshots, self.agent_snapshots
            )
        
        for deadlock in deadlocks:
            logger.warning(f"Deadlock detected: {deadlock.deadlock_id} "
                         f"(confidence: {deadlock.confidence:.2f})")
            
            # Publish deadlock event if event bus available
            if self.event_bus:
                from src.core import AgentEvent
                self.event_bus.publish(AgentEvent(
                    event_type="deadlock_detected",
                    agent_id="mesh_observer",
                    correlation_id=deadlock.correlation_id,
                    data=asdict(deadlock)
                ))
    
    # ===== PUBLIC API =====
    
    def record_span(self, agent_id: str, capability: str, operation: str,
                   duration: float, metadata: Dict[str, Any] = None) -> None:
        """Record a timing span (called by agents)"""
        if not self.enabled:
            return
        
        # Create a simple trace for completed operations
        correlation_id = metadata.get('correlation_id', 'unknown') if metadata else 'unknown'
        
        trace = CapabilityTrace(
            capability=capability,
            agent_id=agent_id,
            correlation_id=correlation_id,
            start_time=datetime.now() - timedelta(seconds=duration),
            end_time=datetime.now(),
            duration=duration,
            status="completed" if not metadata.get('error') else "failed",
            error=metadata.get('error') if metadata else None,
            metadata=metadata or {}
        )
        
        self.performance_analyzer.record_execution(trace)
        
        logger.debug(f"Recorded span: {agent_id}.{capability}.{operation} = {duration:.2f}s")
    
    def start_capability_trace(self, capability: str, agent_id: str, 
                             correlation_id: str, input_data: Dict[str, Any] = None) -> str:
        """Start tracing a capability execution"""
        return self.timeline.start_trace(capability, agent_id, correlation_id, input_data)
    
    def end_capability_trace(self, trace_id: str, status: str = "completed",
                           output_data: Dict[str, Any] = None, error: str = None) -> None:
        """End a capability execution trace"""
        self.timeline.end_trace(trace_id, status, output_data, error)
        
        # Record for performance analysis
        if trace_id in self.timeline.traces:
            trace = self.timeline.traces[trace_id]
            if trace.duration:
                self.performance_analyzer.record_execution(trace)
    
    def visualize_state(self, correlation_id: str) -> Dict[str, Any]:
        """Get visualization data for a workflow"""
        with self.lock:
            workflow = self.workflow_snapshots.get(correlation_id)
            if not workflow:
                return {"error": f"Workflow {correlation_id} not found"}
            
            # Get involved agents
            involved_agents = {}
            for agent_id in (workflow.active_agents | workflow.waiting_agents | workflow.blocked_agents):
                if agent_id in self.agent_snapshots:
                    agent = self.agent_snapshots[agent_id]
                    involved_agents[agent_id] = {
                        "status": agent.status.value,
                        "current_capability": agent.current_capability,
                        "progress": agent.progress,
                        "load": f"{agent.load}/{agent.max_capacity}",
                        "health": agent.health_score
                    }
            
            return {
                "workflow": asdict(workflow),
                "agents": involved_agents,
                "traces": [asdict(trace) for trace in self.timeline.get_traces_for_correlation(correlation_id)]
            }
    
    def trace_capability(self, capability: str) -> Dict[str, Any]:
        """Get execution timeline for a specific capability"""
        traces = self.timeline.get_traces_for_capability(capability)
        
        return {
            "capability": capability,
            "total_executions": len(traces),
            "traces": [asdict(trace) for trace in traces[-50:]],  # Latest 50
            "stats": self.performance_analyzer.capability_stats.get(capability, {})
        }
    
    def detect_deadlocks(self) -> List[Dict[str, Any]]:
        """Get current deadlock information"""
        with self.lock:
            return [asdict(deadlock) for deadlock in 
                   self.deadlock_detector.detected_deadlocks.values()]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        bottlenecks = self.performance_analyzer.identify_bottlenecks(self.agent_snapshots)
        
        with self.lock:
            active_workflows = len([w for w in self.workflow_snapshots.values() 
                                 if w.status == "in_progress"])
            active_agents = len([a for a in self.agent_snapshots.values()
                               if a.status == AgentStatusType.EXECUTING])
            overloaded_agents = len([a for a in self.agent_snapshots.values()
                                   if a.status == AgentStatusType.OVERLOADED])
        
        return {
            "active_workflows": active_workflows,
            "active_agents": active_agents,
            "overloaded_agents": overloaded_agents,
            "detected_deadlocks": len(self.deadlock_detector.detected_deadlocks),
            "bottlenecks": [asdict(b) for b in bottlenecks],
            "timeline_traces": len(self.timeline.traces)
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        with self.lock:
            dashboard = {
                "timestamp": datetime.now().isoformat(),
                "summary": self.get_performance_summary(),
                "workflows": {},
                "agents": {},
                "deadlocks": self.detect_deadlocks(),
                "active_traces": len(self.timeline.get_active_traces())
            }
            
            # Add workflow details
            for correlation_id, workflow in self.workflow_snapshots.items():
                if workflow.status == "in_progress":
                    dashboard["workflows"][correlation_id] = {
                        "progress": workflow.progress,
                        "active_agents": len(workflow.active_agents),
                        "last_activity": workflow.last_activity.isoformat(),
                        "error_count": workflow.error_count
                    }
            
            # Add agent details
            for agent_id, agent in self.agent_snapshots.items():
                dashboard["agents"][agent_id] = {
                    "status": agent.status.value,
                    "current_capability": agent.current_capability,
                    "load": f"{agent.load}/{agent.max_capacity}",
                    "health": agent.health_score,
                    "progress": agent.progress if agent.current_capability else None
                }
        
        return dashboard


# ===== GLOBAL INSTANCE =====

_global_observer: Optional[MeshObserver] = None

def get_mesh_observer() -> Optional[MeshObserver]:
    """Get the global mesh observer instance"""
    return _global_observer

def set_mesh_observer(observer: MeshObserver) -> None:
    """Set the global mesh observer instance"""
    global _global_observer
    _global_observer = observer

def initialize_mesh_observer(event_bus=None, state_store=None, registry=None) -> MeshObserver:
    """Initialize and set the global mesh observer"""
    observer = MeshObserver(event_bus, state_store, registry)
    set_mesh_observer(observer)
    return observer
