"""Agent Flow Monitor - Real-time data flow visualization and debugging.

Tracks data inputs/outputs between agents and provides debugging capabilities.
Phase 3: Enhanced with performance analytics and historical trend analysis.
"""

import asyncio
import json
import logging
import time
import uuid
import statistics
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from collections import deque, defaultdict
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DataFlow:
    """Represents data flow between agents."""
    flow_id: str
    source_agent: str
    target_agent: str
    event_type: str
    data: Dict[str, Any]
    timestamp: str
    correlation_id: str
    status: str = 'active'  # 'active', 'completed', 'failed'
    latency_ms: Optional[float] = None
    data_size_bytes: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentState:
    """Current state of an agent."""
    agent_id: str
    name: str
    category: str
    status: str = 'idle'  # 'idle', 'busy', 'waiting', 'error'
    current_operation: Optional[str] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    last_activity: Optional[str] = None
    error_message: Optional[str] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FlowMetrics:
    """Performance metrics for data flows."""
    total_flows: int = 0
    active_flows: int = 0
    completed_flows: int = 0
    failed_flows: int = 0
    avg_latency_ms: float = 0.0
    throughput_per_min: float = 0.0
    error_rate: float = 0.0
    data_volume_mb: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceTrend:
    """Represents a performance trend over time."""
    metric_name: str
    time_series: List[Tuple[str, float]]  # (timestamp, value) pairs
    trend_direction: str  # 'improving', 'degrading', 'stable'
    change_rate: float  # Percentage change per hour
    prediction: Optional[float] = None  # Predicted next value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'metric_name': self.metric_name,
            'time_series': [(ts, val) for ts, val in self.time_series],
            'trend_direction': self.trend_direction,
            'change_rate': self.change_rate,
            'prediction': self.prediction
        }


@dataclass
class BottleneckAnalysis:
    """Detailed analysis of a detected bottleneck."""
    bottleneck_id: str
    type: str  # 'latency', 'throughput', 'error_rate', 'resource'
    agent_id: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    detected_at: str
    metrics: Dict[str, float]
    impact_assessment: str
    recommendations: List[str]
    historical_occurrences: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceAnalytics:
    """Advanced performance analytics with historical trend analysis."""
    
    def __init__(self, max_history_hours: int = 24):
        self.max_history_hours = max_history_hours
        
        # Time-series data storage
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.agent_performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        
        # Trend analysis
        self.current_trends: Dict[str, PerformanceTrend] = {}
        
        # Bottleneck tracking
        self.bottleneck_history: deque = deque(maxlen=100)
        self.recurring_bottlenecks: Dict[str, int] = defaultdict(int)
    
    def record_metric(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """Record a metric value with timestamp."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        self.metric_history[metric_name].append((timestamp.isoformat(), value))
        
        # Prune old data
        self._prune_old_metrics(metric_name)
    
    def record_agent_performance(
        self,
        agent_id: str,
        latency_ms: float,
        data_size_bytes: int,
        status: str,
        timestamp: Optional[datetime] = None
    ):
        """Record agent performance data point."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        data_point = {
            'timestamp': timestamp.isoformat(),
            'latency_ms': latency_ms,
            'data_size_bytes': data_size_bytes,
            'status': status
        }
        
        self.agent_performance_history[agent_id].append(data_point)
    
    def analyze_trends(self, metric_name: str, window_hours: int = 1) -> Optional[PerformanceTrend]:
        """Analyze trend for a specific metric."""
        if metric_name not in self.metric_history:
            return None
        
        history = list(self.metric_history[metric_name])
        if len(history) < 3:
            return None
        
        # Filter to window
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        windowed_history = [
            (ts, val) for ts, val in history
            if datetime.fromisoformat(ts.replace('Z', '+00:00')) >= cutoff_time
        ]
        
        if len(windowed_history) < 2:
            return None
        
        # Calculate trend
        values = [val for _, val in windowed_history]
        timestamps = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts, _ in windowed_history]
        
        # Simple linear regression for trend
        n = len(values)
        if n < 2:
            return None
        
        time_deltas = [(timestamps[i] - timestamps[0]).total_seconds() / 3600 for i in range(n)]  # Hours
        
        # Calculate slope (change per hour)
        mean_time = sum(time_deltas) / n
        mean_value = sum(values) / n
        
        numerator = sum((time_deltas[i] - mean_time) * (values[i] - mean_value) for i in range(n))
        denominator = sum((time_deltas[i] - mean_time) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Determine trend direction
        if abs(slope) < 0.01:
            trend_direction = 'stable'
        elif slope > 0:
            trend_direction = 'degrading' if 'latency' in metric_name or 'error' in metric_name else 'improving'
        else:
            trend_direction = 'improving' if 'latency' in metric_name or 'error' in metric_name else 'degrading'
        
        # Simple prediction (linear extrapolation)
        last_time = time_deltas[-1]
        prediction = mean_value + slope * (last_time + 1)  # Predict 1 hour ahead
        
        trend = PerformanceTrend(
            metric_name=metric_name,
            time_series=windowed_history,
            trend_direction=trend_direction,
            change_rate=slope * 100,  # Percentage change per hour
            prediction=max(0, prediction)  # Don't predict negative values
        )
        
        self.current_trends[metric_name] = trend
        return trend
    
    def get_agent_performance_summary(
        self,
        agent_id: str,
        window_hours: int = 1
    ) -> Dict[str, Any]:
        """Get performance summary for an agent."""
        if agent_id not in self.agent_performance_history:
            return {}
        
        history = list(self.agent_performance_history[agent_id])
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        
        # Filter to window
        windowed = [
            dp for dp in history
            if datetime.fromisoformat(dp['timestamp'].replace('Z', '+00:00')) >= cutoff_time
        ]
        
        if not windowed:
            return {}
        
        latencies = [dp['latency_ms'] for dp in windowed if dp.get('latency_ms')]
        successes = sum(1 for dp in windowed if dp['status'] == 'completed')
        failures = sum(1 for dp in windowed if dp['status'] == 'failed')
        
        return {
            'agent_id': agent_id,
            'sample_count': len(windowed),
            'avg_latency_ms': sum(latencies) / len(latencies) if latencies else 0,
            'min_latency_ms': min(latencies) if latencies else 0,
            'max_latency_ms': max(latencies) if latencies else 0,
            'p50_latency_ms': statistics.median(latencies) if latencies else 0,
            'p95_latency_ms': (sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0),
            'success_count': successes,
            'failure_count': failures,
            'success_rate': successes / len(windowed) if len(windowed) > 0 else 0.0
        }


class AgentFlowMonitor:
    """Simple flow monitor for tracking agent execution."""
    
    def __init__(self):
        self.analytics = PerformanceAnalytics()
        self.active_flows: Dict[str, DataFlow] = {}
        self.agent_states: Dict[str, AgentState] = {}
        self.flows_by_correlation: Dict[str, List[DataFlow]] = defaultdict(list)
        logger.info("AgentFlowMonitor initialized")
    
    def record_flow(self, flow: DataFlow):
        """Record a data flow event."""
        self.active_flows[flow.flow_id] = flow
        
        # Store by correlation ID for history
        self.flows_by_correlation[flow.correlation_id].append(flow)
        
        # Record metrics
        if flow.latency_ms is not None:
            self.analytics.record_agent_performance(
                agent_id=flow.source_agent,
                latency_ms=flow.latency_ms,
                data_size_bytes=flow.data_size_bytes or 0,
                status=flow.status
            )
    
    def update_agent_state(self, agent_id: str, state: AgentState):
        """Update agent state."""
        self.agent_states[agent_id] = state
    
    def get_active_flows(self) -> List[DataFlow]:
        """Get all active flows."""
        return list(self.active_flows.values())
    
    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Get state for specific agent."""
        return self.agent_states.get(agent_id)
    
    def get_flows_by_correlation(self, correlation_id: str) -> List[DataFlow]:
        """Get all flows for a specific correlation ID (job/workflow).
        
        Args:
            correlation_id: Job ID or workflow execution ID
            
        Returns:
            List of DataFlow objects for the correlation ID
        """
        return self.flows_by_correlation.get(correlation_id, [])
    
    def detect_bottlenecks(self, threshold_ms: float = 1000) -> List[Dict[str, Any]]:
        """Detect performance bottlenecks based on latency threshold.
        
        Args:
            threshold_ms: Latency threshold in milliseconds
            
        Returns:
            List of bottleneck reports
        """
        bottlenecks = []
        agent_latencies: Dict[str, List[float]] = defaultdict(list)
        
        # Collect latencies per agent from active flows
        for flow in self.active_flows.values():
            if flow.latency_ms is not None:
                agent_latencies[flow.source_agent].append(flow.latency_ms)
        
        # Analyze each agent's performance
        for agent_id, latencies in agent_latencies.items():
            if not latencies:
                continue
            
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            
            # Determine if this is a bottleneck
            if avg_latency > threshold_ms:
                # Calculate severity
                if avg_latency > threshold_ms * 3:
                    severity = 'critical'
                elif avg_latency > threshold_ms * 2:
                    severity = 'high'
                elif avg_latency > threshold_ms * 1.5:
                    severity = 'medium'
                else:
                    severity = 'low'
                
                bottlenecks.append({
                    'agent_id': agent_id,
                    'avg_latency_ms': avg_latency,
                    'max_latency_ms': max_latency,
                    'flow_count': len(latencies),
                    'severity': severity,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
        
        # Sort by severity and latency
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        bottlenecks.sort(key=lambda x: (severity_order.get(x['severity'], 4), -x['avg_latency_ms']))
        
        return bottlenecks


# Global flow monitor instance
_flow_monitor_instance = None


def get_flow_monitor() -> AgentFlowMonitor:
    """Get or create the global flow monitor instance."""
    global _flow_monitor_instance
    if _flow_monitor_instance is None:
        _flow_monitor_instance = AgentFlowMonitor()
    return _flow_monitor_instance