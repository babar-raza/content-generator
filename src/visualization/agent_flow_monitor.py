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
            'p95_latency_ms': statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else (max(latencies) if latencies else 0),
            'success_rate': (successes / len(windowed)) * 100 if windowed else 0,
            'failure_rate': (failures / len(windowed)) * 100 if windowed else 0,
            'total_operations': len(windowed)
        }
    
    def detect_anomalies(self, agent_id: str, current_latency: float) -> bool:
        """Detect if current performance is anomalous."""
        if agent_id not in self.agent_performance_history:
            return False
        
        history = list(self.agent_performance_history[agent_id])
        recent = history[-50:] if len(history) >= 50 else history
        
        if len(recent) < 5:
            return False
        
        latencies = [dp['latency_ms'] for dp in recent if dp.get('latency_ms')]
        if not latencies:
            return False
        
        mean_latency = sum(latencies) / len(latencies)
        std_dev = statistics.stdev(latencies) if len(latencies) >= 2 else 0
        
        # Anomaly if > 3 standard deviations from mean
        return abs(current_latency - mean_latency) > 3 * std_dev
    
    def predict_bottleneck(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Predict if an agent is likely to become a bottleneck."""
        summary = self.get_agent_performance_summary(agent_id, window_hours=1)
        
        if not summary:
            return None
        
        # Analyze latency trend
        metric_name = f"agent_{agent_id}_latency"
        if metric_name in self.metric_history:
            trend = self.analyze_trends(metric_name, window_hours=1)
            
            if trend and trend.trend_direction == 'degrading' and trend.change_rate > 20:
                return {
                    'agent_id': agent_id,
                    'prediction': 'likely_bottleneck',
                    'confidence': min(100, abs(trend.change_rate)),
                    'time_to_bottleneck_hours': 1.0 / (abs(trend.change_rate) / 100) if trend.change_rate != 0 else None,
                    'recommendation': 'Monitor closely and consider scaling'
                }
        
        return None
    
    def _prune_old_metrics(self, metric_name: str):
        """Remove metrics older than max_history_hours."""
        if metric_name not in self.metric_history:
            return
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.max_history_hours)
        history = self.metric_history[metric_name]
        
        while history and datetime.fromisoformat(history[0][0].replace('Z', '+00:00')) < cutoff_time:
            history.popleft()
    
    def generate_performance_report(self, window_hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {
            'report_time': datetime.now(timezone.utc).isoformat(),
            'window_hours': window_hours,
            'metric_trends': {},
            'agent_summaries': {},
            'anomalies_detected': []
        }
        
        # Analyze all metrics
        for metric_name in self.metric_history.keys():
            trend = self.analyze_trends(metric_name, window_hours=window_hours)
            if trend:
                report['metric_trends'][metric_name] = trend.to_dict()
        
        # Summarize agent performance
        for agent_id in self.agent_performance_history.keys():
            summary = self.get_agent_performance_summary(agent_id, window_hours=window_hours)
            if summary:
                report['agent_summaries'][agent_id] = summary
        
        return report


class AgentFlowMonitor:
    """Monitors and visualizes real-time agent data flows."""
    
    def __init__(self, max_flow_history: int = 1000):
        self.max_flow_history = max_flow_history
        
        # Data storage
        self.flows: deque = deque(maxlen=max_flow_history)
        self.agent_states: Dict[str, AgentState] = {}
        self.active_flows: Dict[str, DataFlow] = {}
        
        # Metrics
        self.metrics = FlowMetrics()
        self.flow_history: Dict[str, List[DataFlow]] = defaultdict(list)
        
        # Phase 3: Performance analytics
        self.performance_analytics = PerformanceAnalytics(max_history_hours=24)
        self.bottleneck_analyses: Dict[str, BottleneckAnalysis] = {}
        
        # Event callbacks
        self.flow_callbacks: List[Callable[[DataFlow], None]] = []
        self.agent_callbacks: List[Callable[[AgentState], None]] = []
        self.error_callbacks: List[Callable[[str, Exception], None]] = []
        
        # Monitoring state
        self._monitoring_active = False
        self._monitor_thread = None
        self._lock = threading.RLock()
        
        # Performance tracking
        self._flow_times: deque = deque(maxlen=100)
        self._data_volumes: deque = deque(maxlen=100)
    
    def start_monitoring(self):
        """Start the flow monitoring system."""
        with self._lock:
            if self._monitoring_active:
                return
            
            self._monitoring_active = True
            self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self._monitor_thread.start()
            logger.info("Agent flow monitoring started")
    
    def stop_monitoring(self):
        """Stop the flow monitoring system."""
        with self._lock:
            self._monitoring_active = False
            if self._monitor_thread:
                self._monitor_thread.join(timeout=1)
            logger.info("Agent flow monitoring stopped")
    
    def register_agent(self, agent_id: str, name: str, category: str):
        """Register an agent for monitoring."""
        with self._lock:
            self.agent_states[agent_id] = AgentState(
                agent_id=agent_id,
                name=name,
                category=category,
                last_activity=datetime.now(timezone.utc).isoformat()
            )
        logger.info(f"Registered agent {name} ({category}) for monitoring")
    
    def record_flow_start(
        self,
        source_agent: str,
        target_agent: str,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: str
    ) -> str:
        """Record the start of a data flow between agents."""
        flow_id = str(uuid.uuid4())
        
        # Calculate data size
        data_size = len(json.dumps(data, default=str).encode('utf-8'))
        
        flow = DataFlow(
            flow_id=flow_id,
            source_agent=source_agent,
            target_agent=target_agent,
            event_type=event_type,
            data=data,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id,
            status='active',
            data_size_bytes=data_size
        )
        
        with self._lock:
            self.flows.append(flow)
            self.active_flows[flow_id] = flow
            
            # Update agent states
            if source_agent in self.agent_states:
                self.agent_states[source_agent].status = 'busy'
                self.agent_states[source_agent].current_operation = f"sending to {target_agent}"
                self.agent_states[source_agent].output_data = data
                self.agent_states[source_agent].last_activity = flow.timestamp
                
            if target_agent in self.agent_states:
                self.agent_states[target_agent].status = 'waiting'
                self.agent_states[target_agent].input_data = data
                self.agent_states[target_agent].last_activity = flow.timestamp
        
        # Notify callbacks
        for callback in self.flow_callbacks:
            try:
                callback(flow)
            except Exception as e:
                logger.error(f"Flow callback error: {e}")
        
        # Update metrics
        self._update_metrics()
        
        return flow_id
    
    def record_flow_completion(
        self,
        flow_id: str,
        status: str = 'completed',
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        """Record the completion of a data flow."""
        with self._lock:
            if flow_id not in self.active_flows:
                logger.warning(f"Flow {flow_id} not found in active flows")
                return
            
            flow = self.active_flows[flow_id]
            start_time = datetime.fromisoformat(flow.timestamp.replace('Z', '+00:00'))
            end_time = datetime.now(timezone.utc)
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # Update flow
            flow.status = status
            flow.latency_ms = latency_ms
            if result_data:
                flow.data.update(result_data)
            if error_message:
                flow.metadata['error'] = error_message
            
            # Phase 3: Record performance analytics
            self.performance_analytics.record_agent_performance(
                agent_id=flow.target_agent,
                latency_ms=latency_ms,
                data_size_bytes=flow.data_size_bytes or 0,
                status=status,
                timestamp=end_time
            )
            
            # Record metric for trend analysis
            metric_name = f"agent_{flow.target_agent}_latency"
            self.performance_analytics.record_metric(metric_name, latency_ms, end_time)
            
            # Check for anomalies
            if self.performance_analytics.detect_anomalies(flow.target_agent, latency_ms):
                logger.warning(f"Performance anomaly detected for {flow.target_agent}: {latency_ms:.2f}ms")
                flow.metadata['anomaly'] = True
            
            # Track flow times for metrics
            self._flow_times.append(latency_ms)
            if flow.data_size_bytes:
                self._data_volumes.append(flow.data_size_bytes)
            
            # Update agent states
            if flow.target_agent in self.agent_states:
                agent_state = self.agent_states[flow.target_agent]
                agent_state.status = 'idle' if status == 'completed' else 'error'
                agent_state.current_operation = None
                agent_state.last_activity = end_time.isoformat()
                
                if status == 'failed':
                    agent_state.error_message = error_message
                
                # Update performance metrics
                agent_state.performance_metrics['last_latency_ms'] = latency_ms
                agent_state.performance_metrics['avg_latency_ms'] = (
                    agent_state.performance_metrics.get('avg_latency_ms', 0) * 0.9 + latency_ms * 0.1
                )
                
                # Notify callbacks
                for callback in self.agent_callbacks:
                    try:
                        callback(agent_state)
                    except Exception as e:
                        logger.error(f"Agent callback error: {e}")
            
            # Move to history
            self.flow_history[flow.correlation_id].append(flow)
            del self.active_flows[flow_id]
        
        # Update metrics
        self._update_metrics()
    
    def get_real_time_state(self) -> Dict[str, Any]:
        """Get current real-time state for visualization."""
        with self._lock:
            return {
                'agents': [state.to_dict() for state in self.agent_states.values()],
                'active_flows': [flow.to_dict() for flow in self.active_flows.values()],
                'recent_flows': [flow.to_dict() for flow in list(self.flows)[-20:]],
                'metrics': self.metrics.to_dict(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_flow_history(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get flow history for a specific correlation ID."""
        with self._lock:
            flows = self.flow_history.get(correlation_id, [])
            return [flow.to_dict() for flow in flows]
    
    def get_agent_performance(self, agent_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics for a specific agent."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        
        agent_flows = []
        with self._lock:
            for flows in self.flow_history.values():
                for flow in flows:
                    flow_time = datetime.fromisoformat(flow.timestamp.replace('Z', '+00:00')).timestamp()
                    if (flow.source_agent == agent_id or flow.target_agent == agent_id) and flow_time > cutoff_time:
                        agent_flows.append(flow)
        
        if not agent_flows:
            return {'error': 'No data available'}
        
        # Calculate metrics
        total_flows = len(agent_flows)
        completed_flows = sum(1 for f in agent_flows if f.status == 'completed')
        failed_flows = sum(1 for f in agent_flows if f.status == 'failed')
        
        latencies = [f.latency_ms for f in agent_flows if f.latency_ms]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        data_volumes = [f.data_size_bytes for f in agent_flows if f.data_size_bytes]
        total_data_mb = sum(data_volumes) / (1024 * 1024) if data_volumes else 0
        
        return {
            'agent_id': agent_id,
            'total_flows': total_flows,
            'success_rate': (completed_flows / total_flows) * 100 if total_flows > 0 else 0,
            'avg_latency_ms': avg_latency,
            'total_data_mb': total_data_mb,
            'flows_per_hour': total_flows / hours,
            'error_rate': (failed_flows / total_flows) * 100 if total_flows > 0 else 0
        }
    
    def detect_bottlenecks(self) -> List[Dict[str, Any]]:
        """Detect potential bottlenecks in the system with advanced analysis."""
        bottlenecks = []
        
        with self._lock:
            current_time = datetime.now(timezone.utc)
            
            # Phase 3: Enhanced bottleneck detection
            for agent_id, state in self.agent_states.items():
                # Get performance summary
                perf = self.get_agent_performance(agent_id, hours=1)
                
                if not isinstance(perf, dict):
                    continue
                
                # Check for high error rate
                error_rate = perf.get('error_rate', 0)
                if error_rate > 20:
                    bottleneck = BottleneckAnalysis(
                        bottleneck_id=f"bottleneck_{agent_id}_{int(time.time())}",
                        type='error_rate',
                        agent_id=agent_id,
                        severity='high' if error_rate > 50 else 'medium',
                        detected_at=current_time.isoformat(),
                        metrics={'error_rate': error_rate},
                        impact_assessment=f"High failure rate affecting reliability",
                        recommendations=[
                            'Review error logs for patterns',
                            'Check input data validation',
                            'Implement retry logic',
                            'Add circuit breaker pattern'
                        ],
                        historical_occurrences=self.bottleneck_analyses.get(f"{agent_id}_error_rate", {}).get('occurrences', 0)
                    )
                    bottlenecks.append(bottleneck.to_dict())
                    self.bottleneck_analyses[f"{agent_id}_error_rate"] = {
                        'last_seen': current_time.isoformat(),
                        'occurrences': bottleneck.historical_occurrences + 1
                    }
                
                # Check for high latency
                avg_latency = perf.get('avg_latency_ms', 0)
                if avg_latency > 5000:
                    # Analyze latency trend
                    metric_name = f"agent_{agent_id}_latency"
                    trend = self.performance_analytics.analyze_trends(metric_name, window_hours=1)
                    
                    severity = 'critical' if avg_latency > 10000 else 'high' if avg_latency > 7000 else 'medium'
                    
                    recommendations = [
                        'Profile agent execution to find slow operations',
                        'Consider caching frequently accessed data',
                        'Optimize database queries if applicable',
                        'Scale horizontally if possible'
                    ]
                    
                    if trend and trend.trend_direction == 'degrading':
                        recommendations.insert(0, f'Latency degrading at {abs(trend.change_rate):.1f}% per hour - urgent action needed')
                    
                    bottleneck = BottleneckAnalysis(
                        bottleneck_id=f"bottleneck_{agent_id}_{int(time.time())}",
                        type='latency',
                        agent_id=agent_id,
                        severity=severity,
                        detected_at=current_time.isoformat(),
                        metrics={
                            'avg_latency_ms': avg_latency,
                            'trend': trend.trend_direction if trend else 'unknown'
                        },
                        impact_assessment=f"High latency causing workflow delays",
                        recommendations=recommendations,
                        historical_occurrences=self.bottleneck_analyses.get(f"{agent_id}_latency", {}).get('occurrences', 0)
                    )
                    bottlenecks.append(bottleneck.to_dict())
                
                # Check for stuck agents
                if state.last_activity:
                    last_activity = datetime.fromisoformat(state.last_activity.replace('Z', '+00:00'))
                    idle_seconds = (current_time - last_activity).total_seconds()
                    
                    if idle_seconds > 300 and state.status == 'busy':
                        bottleneck = BottleneckAnalysis(
                            bottleneck_id=f"bottleneck_{agent_id}_{int(time.time())}",
                            type='stuck',
                            agent_id=agent_id,
                            severity='high',
                            detected_at=current_time.isoformat(),
                            metrics={'idle_seconds': idle_seconds},
                            impact_assessment=f"Agent stuck for {idle_seconds:.0f}s, blocking workflow",
                            recommendations=[
                                'Check for deadlocks or infinite loops',
                                'Review agent logs for errors',
                                'Consider implementing timeout mechanisms',
                                'Restart agent if necessary'
                            ],
                            historical_occurrences=0
                        )
                        bottlenecks.append(bottleneck.to_dict())
                
                # Check for low throughput
                flows_per_hour = perf.get('flows_per_hour', 0)
                if flows_per_hour < 10 and perf.get('total_flows', 0) > 5:  # Only if agent has processed some flows
                    bottleneck = BottleneckAnalysis(
                        bottleneck_id=f"bottleneck_{agent_id}_{int(time.time())}",
                        type='throughput',
                        agent_id=agent_id,
                        severity='medium',
                        detected_at=current_time.isoformat(),
                        metrics={'flows_per_hour': flows_per_hour},
                        impact_assessment=f"Low throughput may cause backlog",
                        recommendations=[
                            'Analyze processing bottlenecks',
                            'Consider parallel processing',
                            'Review resource allocation',
                            'Implement batch processing if applicable'
                        ],
                        historical_occurrences=0
                    )
                    bottlenecks.append(bottleneck.to_dict())
                
                # Phase 3: Predictive bottleneck detection
                prediction = self.performance_analytics.predict_bottleneck(agent_id)
                if prediction:
                    bottleneck = BottleneckAnalysis(
                        bottleneck_id=f"bottleneck_{agent_id}_{int(time.time())}",
                        type='predicted',
                        agent_id=agent_id,
                        severity='low',
                        detected_at=current_time.isoformat(),
                        metrics={
                            'confidence': prediction['confidence'],
                            'time_to_bottleneck_hours': prediction.get('time_to_bottleneck_hours', 0)
                        },
                        impact_assessment=f"Agent likely to become bottleneck soon",
                        recommendations=[prediction['recommendation']],
                        historical_occurrences=0
                    )
                    bottlenecks.append(bottleneck.to_dict())
        
        return bottlenecks
    
    def add_flow_callback(self, callback: Callable[[DataFlow], None]):
        """Add a callback for flow events."""
        self.flow_callbacks.append(callback)
    
    def add_agent_callback(self, callback: Callable[[AgentState], None]):
        """Add a callback for agent state changes."""
        self.agent_callbacks.append(callback)
    
    def _update_metrics(self):
        """Update performance metrics."""
        with self._lock:
            # Basic counts
            self.metrics.total_flows = len(self.flows)
            self.metrics.active_flows = len(self.active_flows)
            
            completed = sum(1 for flow in self.flows if flow.status == 'completed')
            failed = sum(1 for flow in self.flows if flow.status == 'failed')
            
            self.metrics.completed_flows = completed
            self.metrics.failed_flows = failed
            
            # Calculate rates
            total_processed = completed + failed
            if total_processed > 0:
                self.metrics.error_rate = (failed / total_processed) * 100
            
            # Average latency
            if self._flow_times:
                self.metrics.avg_latency_ms = sum(self._flow_times) / len(self._flow_times)
            
            # Data volume
            if self._data_volumes:
                self.metrics.data_volume_mb = sum(self._data_volumes) / (1024 * 1024)
            
            # Throughput (flows per minute in last window)
            recent_flows = [f for f in self.flows if f.status in ['completed', 'failed']]
            if recent_flows:
                # Calculate flows in last minute
                current_time = datetime.now(timezone.utc)
                minute_ago = current_time.timestamp() - 60
                
                recent_count = sum(1 for flow in recent_flows 
                                 if datetime.fromisoformat(flow.timestamp.replace('Z', '+00:00')).timestamp() > minute_ago)
                self.metrics.throughput_per_min = recent_count
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while self._monitoring_active:
            try:
                # Update metrics periodically
                self._update_metrics()
                
                # Detect and log bottlenecks
                bottlenecks = self.detect_bottlenecks()
                for bottleneck in bottlenecks:
                    logger.warning(f"Bottleneck detected: {bottleneck}")
                
                time.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                for callback in self.error_callbacks:
                    try:
                        callback("monitoring_loop", e)
                    except:
                        pass
    
    def get_performance_trends(self, agent_id: Optional[str] = None, window_hours: int = 1) -> Dict[str, Any]:
        """Get performance trends for agent(s)."""
        if agent_id:
            metric_name = f"agent_{agent_id}_latency"
            trend = self.performance_analytics.analyze_trends(metric_name, window_hours=window_hours)
            return {agent_id: trend.to_dict() if trend else None}
        
        # Get trends for all agents
        trends = {}
        with self._lock:
            for aid in self.agent_states.keys():
                metric_name = f"agent_{aid}_latency"
                trend = self.performance_analytics.analyze_trends(metric_name, window_hours=window_hours)
                if trend:
                    trends[aid] = trend.to_dict()
        
        return trends
    
    def get_historical_metrics(self, metric_name: str, window_hours: int = 24) -> List[Tuple[str, float]]:
        """Get historical metrics data."""
        if metric_name not in self.performance_analytics.metric_history:
            return []
        
        history = list(self.performance_analytics.metric_history[metric_name])
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        
        return [
            (ts, val) for ts, val in history
            if datetime.fromisoformat(ts.replace('Z', '+00:00')) >= cutoff_time
        ]
    
    def get_comprehensive_analytics(self, window_hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance analytics report."""
        return self.performance_analytics.generate_performance_report(window_hours=window_hours)
    
    def get_bottleneck_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get history of detected bottlenecks."""
        with self._lock:
            history = list(self.performance_analytics.bottleneck_history)
            return [b.to_dict() if hasattr(b, 'to_dict') else b for b in history[-limit:]]
    
    def export_flow_data(self, output_path: Path, correlation_id: Optional[str] = None):
        """Export flow data for analysis."""
        with self._lock:
            if correlation_id:
                flows_to_export = self.flow_history.get(correlation_id, [])
            else:
                # Export all flows
                flows_to_export = []
                for flow_list in self.flow_history.values():
                    flows_to_export.extend(flow_list)
                flows_to_export.extend(self.active_flows.values())
            
            export_data = {
                'metadata': {
                    'export_time': datetime.now(timezone.utc).isoformat(),
                    'correlation_id': correlation_id,
                    'total_flows': len(flows_to_export)
                },
                'flows': [flow.to_dict() for flow in flows_to_export],
                'agents': [state.to_dict() for state in self.agent_states.values()],
                'metrics': self.metrics.to_dict()
            }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Exported {len(flows_to_export)} flows to {output_path}")


# Global instance for easy access
_flow_monitor = AgentFlowMonitor()

def get_flow_monitor() -> AgentFlowMonitor:
    """Get the global flow monitor instance."""
    return _flow_monitor


def monitor_agent_execution(agent_id: str, agent_name: str, category: str):
    """Decorator to monitor agent execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_flow_monitor()
            
            # Register agent if not already registered
            if agent_id not in monitor.agent_states:
                monitor.register_agent(agent_id, agent_name, category)
            
            # Record execution start
            correlation_id = kwargs.get('correlation_id', str(uuid.uuid4()))
            flow_id = monitor.record_flow_start(
                source_agent='system',
                target_agent=agent_id,
                event_type='agent_execution',
                data={'function': func.__name__, 'args': str(args), 'kwargs': str(kwargs)},
                correlation_id=correlation_id
            )
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Record successful completion
                monitor.record_flow_completion(
                    flow_id=flow_id,
                    status='completed',
                    result_data={'result_type': type(result).__name__}
                )
                
                return result
                
            except Exception as e:
                # Record failure
                monitor.record_flow_completion(
                    flow_id=flow_id,
                    status='failed',
                    error_message=str(e)
                )
                raise
        
        return wrapper
    return decorator
