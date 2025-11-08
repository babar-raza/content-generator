"""Workflow Debugging Interface - Advanced debugging and troubleshooting tools.

Provides detailed inspection, step-through debugging, and error analysis capabilities.
"""

import json
import logging
import traceback
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, deque
import re

from .agent_flow_monitor import get_flow_monitor, DataFlow, AgentState

logger = logging.getLogger(__name__)


@dataclass
class DebugBreakpoint:
    """Represents a debugging breakpoint."""
    id: str
    agent_id: str
    event_type: str
    condition: Optional[str] = None  # Python expression to evaluate
    enabled: bool = True
    hit_count: int = 0
    max_hits: Optional[int] = None
    
    def should_trigger(self, data: Dict[str, Any]) -> bool:
        """Check if breakpoint should trigger."""
        if not self.enabled:
            return False
        
        if self.max_hits and self.hit_count >= self.max_hits:
            return False
        
        if self.condition:
            try:
                # Safe evaluation of condition
                return eval(self.condition, {"__builtins__": {}}, data)
            except Exception as e:
                logger.warning(f"Breakpoint condition error: {e}")
                return False
        
        return True


@dataclass
class DebugSession:
    """Represents an active debugging session."""
    session_id: str
    correlation_id: str
    started_at: str
    status: str = 'active'  # 'active', 'paused', 'completed'
    current_step: Optional[str] = None
    breakpoints: List[DebugBreakpoint] = field(default_factory=list)
    step_history: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ErrorAnalysis:
    """Analysis of workflow errors."""
    error_id: str
    correlation_id: str
    agent_id: str
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    suggested_fixes: List[str] = field(default_factory=list)
    similar_errors: List[str] = field(default_factory=list)
    severity: str = 'medium'  # 'low', 'medium', 'high', 'critical'
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WorkflowDebugger:
    """Advanced debugging and troubleshooting for workflows."""
    
    def __init__(self):
        self.flow_monitor = get_flow_monitor()
        
        # Debug sessions
        self.debug_sessions: Dict[str, DebugSession] = {}
        self.active_breakpoints: Dict[str, DebugBreakpoint] = {}
        
        # Error analysis
        self.error_patterns: Dict[str, List[str]] = {}
        self.error_history: deque = deque(maxlen=1000)
        self.resolution_suggestions: Dict[str, List[str]] = {}
        
        # Step-through debugging
        self.step_mode_sessions: Set[str] = set()
        
        # Initialize error patterns
        self._load_error_patterns()
        self._load_resolution_suggestions()
    
    def start_debug_session(self, correlation_id: str) -> str:
        """Start a new debugging session."""
        session_id = f"debug_{correlation_id}_{int(datetime.now().timestamp())}"
        
        session = DebugSession(
            session_id=session_id,
            correlation_id=correlation_id,
            started_at=datetime.now(timezone.utc).isoformat()
        )
        
        self.debug_sessions[session_id] = session
        logger.info(f"Started debug session {session_id} for correlation {correlation_id}")
        
        return session_id
    
    def add_breakpoint(
        self,
        session_id: str,
        agent_id: str,
        event_type: str,
        condition: Optional[str] = None,
        max_hits: Optional[int] = None
    ) -> str:
        """Add a breakpoint to a debug session."""
        if session_id not in self.debug_sessions:
            raise ValueError(f"Debug session {session_id} not found")
        
        breakpoint_id = f"bp_{agent_id}_{event_type}_{int(datetime.now().timestamp())}"
        
        breakpoint = DebugBreakpoint(
            id=breakpoint_id,
            agent_id=agent_id,
            event_type=event_type,
            condition=condition,
            max_hits=max_hits
        )
        
        self.debug_sessions[session_id].breakpoints.append(breakpoint)
        self.active_breakpoints[breakpoint_id] = breakpoint
        
        logger.info(f"Added breakpoint {breakpoint_id} for {agent_id}.{event_type}")
        return breakpoint_id
    
    def remove_breakpoint(self, session_id: str, breakpoint_id: str):
        """Remove a breakpoint."""
        if session_id in self.debug_sessions:
            session = self.debug_sessions[session_id]
            session.breakpoints = [bp for bp in session.breakpoints if bp.id != breakpoint_id]
        
        if breakpoint_id in self.active_breakpoints:
            del self.active_breakpoints[breakpoint_id]
        
        logger.info(f"Removed breakpoint {breakpoint_id}")
    
    def enable_step_mode(self, session_id: str):
        """Enable step-through debugging for a session."""
        self.step_mode_sessions.add(session_id)
        logger.info(f"Enabled step mode for session {session_id}")
    
    def disable_step_mode(self, session_id: str):
        """Disable step-through debugging for a session."""
        self.step_mode_sessions.discard(session_id)
        logger.info(f"Disabled step mode for session {session_id}")
    
    def step_next(self, session_id: str):
        """Continue to next step in debug session."""
        if session_id in self.debug_sessions:
            session = self.debug_sessions[session_id]
            session.status = 'active'
            logger.info(f"Stepping to next in session {session_id}")
    
    def check_breakpoints(
        self,
        agent_id: str,
        event_type: str,
        data: Dict[str, Any],
        correlation_id: str
    ) -> Optional[str]:
        """Check if any breakpoints should trigger."""
        # Find debug session for this correlation ID
        session_id = None
        for sid, session in self.debug_sessions.items():
            if session.correlation_id == correlation_id and session.status == 'active':
                session_id = sid
                break
        
        if not session_id:
            return None
        
        session = self.debug_sessions[session_id]
        
        # Check if in step mode
        if session_id in self.step_mode_sessions:
            session.status = 'paused'
            session.current_step = f"{agent_id}.{event_type}"
            session.variables.update(data)
            session.step_history.append({
                'agent_id': agent_id,
                'event_type': event_type,
                'data': data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            return session_id
        
        # Check breakpoints
        for breakpoint in session.breakpoints:
            if (breakpoint.agent_id == agent_id and 
                breakpoint.event_type == event_type and
                breakpoint.should_trigger(data)):
                
                breakpoint.hit_count += 1
                session.status = 'paused'
                session.current_step = f"{agent_id}.{event_type}"
                session.variables.update(data)
                session.step_history.append({
                    'agent_id': agent_id,
                    'event_type': event_type,
                    'data': data,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'breakpoint_id': breakpoint.id
                })
                
                logger.info(f"Breakpoint {breakpoint.id} hit in session {session_id}")
                return session_id
        
        return None
    
    def analyze_error(
        self,
        agent_id: str,
        error: Exception,
        context_data: Dict[str, Any],
        correlation_id: str
    ) -> ErrorAnalysis:
        """Analyze an error and provide debugging insights."""
        error_id = f"error_{agent_id}_{int(datetime.now().timestamp())}"
        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = traceback.format_exc()
        
        analysis = ErrorAnalysis(
            error_id=error_id,
            correlation_id=correlation_id,
            agent_id=agent_id,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            context_data=context_data
        )
        
        # Categorize severity
        analysis.severity = self._categorize_error_severity(error_type, error_message)
        
        # Find similar errors
        analysis.similar_errors = self._find_similar_errors(error_type, error_message)
        
        # Generate suggestions
        analysis.suggested_fixes = self._generate_fix_suggestions(error_type, error_message, context_data)
        
        # Store for future reference
        self.error_history.append(analysis)
        
        logger.error(f"Error analysis {error_id}: {error_type} in {agent_id}")
        return analysis
    
    def get_workflow_trace(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get detailed execution trace for a workflow."""
        flows = self.flow_monitor.get_flow_history(correlation_id)
        
        trace = []
        for flow in flows:
            trace.append({
                'timestamp': flow['timestamp'],
                'source_agent': flow['source_agent'],
                'target_agent': flow['target_agent'],
                'event_type': flow['event_type'],
                'status': flow['status'],
                'latency_ms': flow.get('latency_ms'),
                'data_size_bytes': flow.get('data_size_bytes'),
                'error': flow.get('metadata', {}).get('error')
            })
        
        return sorted(trace, key=lambda x: x['timestamp'])
    
    def get_agent_inspection_data(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed inspection data for an agent."""
        monitor_state = self.flow_monitor.get_real_time_state()
        agent_state = None
        
        for agent in monitor_state['agents']:
            if agent['agent_id'] == agent_id:
                agent_state = agent
                break
        
        if not agent_state:
            return {'error': 'Agent not found'}
        
        # Get recent flows involving this agent
        recent_flows = []
        for flow in monitor_state['recent_flows']:
            if flow['source_agent'] == agent_id or flow['target_agent'] == agent_id:
                recent_flows.append(flow)
        
        # Get performance metrics
        performance = self.flow_monitor.get_agent_performance(agent_id, hours=1)
        
        # Get recent errors
        recent_errors = [
            error.to_dict() for error in self.error_history
            if error.agent_id == agent_id
        ][-10:]  # Last 10 errors
        
        return {
            'agent_state': agent_state,
            'recent_flows': recent_flows,
            'performance': performance,
            'recent_errors': recent_errors,
            'inspection_timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_data_lineage(self, correlation_id: str, data_key: str) -> List[Dict[str, Any]]:
        """Trace data lineage for a specific data element."""
        flows = self.flow_monitor.get_flow_history(correlation_id)
        lineage = []
        
        for flow in flows:
            flow_data = flow.get('data', {})
            if self._data_contains_key(flow_data, data_key):
                lineage.append({
                    'timestamp': flow['timestamp'],
                    'source_agent': flow['source_agent'],
                    'target_agent': flow['target_agent'],
                    'event_type': flow['event_type'],
                    'data_value': self._extract_data_value(flow_data, data_key),
                    'transformation': flow.get('metadata', {}).get('transformation')
                })
        
        return sorted(lineage, key=lambda x: x['timestamp'])
    
    def suggest_optimizations(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Suggest workflow optimizations based on analysis."""
        trace = self.get_workflow_trace(correlation_id)
        suggestions = []
        
        # Identify slow steps
        slow_steps = [step for step in trace if step.get('latency_ms', 0) > 5000]
        if slow_steps:
            suggestions.append({
                'type': 'performance',
                'priority': 'high',
                'title': 'Slow Agent Execution Detected',
                'description': f"Found {len(slow_steps)} steps with latency > 5s",
                'affected_agents': [step['target_agent'] for step in slow_steps],
                'recommendation': 'Consider optimizing agent logic or adding caching'
            })
        
        # Identify data size issues
        large_data_steps = [step for step in trace if step.get('data_size_bytes', 0) > 1024*1024]  # > 1MB
        if large_data_steps:
            suggestions.append({
                'type': 'data_optimization',
                'priority': 'medium',
                'title': 'Large Data Transfers Detected',
                'description': f"Found {len(large_data_steps)} steps with data > 1MB",
                'affected_agents': [step['target_agent'] for step in large_data_steps],
                'recommendation': 'Consider data compression or streaming approaches'
            })
        
        # Identify error patterns
        failed_steps = [step for step in trace if step['status'] == 'failed']
        if len(failed_steps) > len(trace) * 0.1:  # > 10% failure rate
            suggestions.append({
                'type': 'reliability',
                'priority': 'critical',
                'title': 'High Failure Rate Detected',
                'description': f"{len(failed_steps)}/{len(trace)} steps failed",
                'recommendation': 'Review error handling and add retry mechanisms'
            })
        
        return suggestions
    
    def export_debug_report(self, session_id: str, output_path: Path):
        """Export comprehensive debug report."""
        if session_id not in self.debug_sessions:
            raise ValueError(f"Debug session {session_id} not found")
        
        session = self.debug_sessions[session_id]
        
        report = {
            'session': session.to_dict(),
            'workflow_trace': self.get_workflow_trace(session.correlation_id),
            'errors': [error.to_dict() for error in self.error_history 
                      if error.correlation_id == session.correlation_id],
            'optimizations': self.suggest_optimizations(session.correlation_id),
            'agent_states': {
                agent_id: self.get_agent_inspection_data(agent_id)
                for agent_id in set(
                    step['agent_id'] for step in session.step_history
                )
            },
            'export_metadata': {
                'exported_at': datetime.now(timezone.utc).isoformat(),
                'session_id': session_id,
                'correlation_id': session.correlation_id
            }
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Exported debug report to {output_path}")
    
    def _load_error_patterns(self):
        """Load common error patterns for classification."""
        self.error_patterns = {
            'connection_error': [
                r'connection.*refused',
                r'timeout',
                r'network.*unreachable',
                r'dns.*resolution.*failed'
            ],
            'validation_error': [
                r'invalid.*input',
                r'validation.*failed',
                r'schema.*mismatch',
                r'required.*field.*missing'
            ],
            'resource_error': [
                r'out.*of.*memory',
                r'disk.*full',
                r'cpu.*limit.*exceeded',
                r'rate.*limit.*exceeded'
            ],
            'auth_error': [
                r'unauthorized',
                r'access.*denied',
                r'authentication.*failed',
                r'invalid.*credentials'
            ]
        }
    
    def _load_resolution_suggestions(self):
        """Load resolution suggestions for common errors."""
        self.resolution_suggestions = {
            'connection_error': [
                'Check network connectivity',
                'Verify service endpoints',
                'Increase timeout values',
                'Add retry logic with exponential backoff'
            ],
            'validation_error': [
                'Validate input data format',
                'Check required fields',
                'Review data schemas',
                'Add input sanitization'
            ],
            'resource_error': [
                'Increase resource limits',
                'Optimize memory usage',
                'Add resource monitoring',
                'Implement resource pooling'
            ],
            'auth_error': [
                'Check API credentials',
                'Verify access permissions',
                'Refresh authentication tokens',
                'Review security policies'
            ]
        }
    
    def _categorize_error_severity(self, error_type: str, error_message: str) -> str:
        """Categorize error severity based on type and message."""
        critical_patterns = [
            r'fatal', r'critical', r'system.*failure', r'security.*breach'
        ]
        high_patterns = [
            r'failed.*to.*start', r'connection.*lost', r'data.*corruption'
        ]
        
        message_lower = error_message.lower()
        
        for pattern in critical_patterns:
            if re.search(pattern, message_lower):
                return 'critical'
        
        for pattern in high_patterns:
            if re.search(pattern, message_lower):
                return 'high'
        
        if error_type in ['Exception', 'RuntimeError', 'ValueError']:
            return 'medium'
        
        return 'low'
    
    def _find_similar_errors(self, error_type: str, error_message: str) -> List[str]:
        """Find similar errors in history."""
        similar = []
        
        for error in self.error_history:
            if error.error_type == error_type:
                # Simple similarity based on common words
                common_words = set(error_message.lower().split()) & set(error.error_message.lower().split())
                if len(common_words) >= 3:
                    similar.append(error.error_id)
            
            if len(similar) >= 5:  # Limit to 5 similar errors
                break
        
        return similar
    
    def _generate_fix_suggestions(
        self,
        error_type: str,
        error_message: str,
        context_data: Dict[str, Any]
    ) -> List[str]:
        """Generate fix suggestions based on error analysis."""
        suggestions = []
        
        # Pattern-based suggestions
        for pattern_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_message.lower()):
                    suggestions.extend(self.resolution_suggestions.get(pattern_type, []))
                    break
        
        # Context-based suggestions
        if 'api_key' in str(context_data).lower() and 'auth' in error_message.lower():
            suggestions.append('Verify API key configuration')
        
        if 'timeout' in error_message.lower():
            suggestions.append('Increase timeout configuration')
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:5]  # Limit to 5 suggestions
    
    def _data_contains_key(self, data: Dict[str, Any], key: str) -> bool:
        """Check if data contains a specific key (supports nested keys)."""
        if '.' in key:
            keys = key.split('.')
            current = data
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return False
            return True
        else:
            return key in data
    
    def _extract_data_value(self, data: Dict[str, Any], key: str) -> Any:
        """Extract value for a specific key (supports nested keys)."""
        if '.' in key:
            keys = key.split('.')
            current = data
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return None
            return current
        else:
            return data.get(key)


# Global instance for easy access
_debugger = WorkflowDebugger()

def get_workflow_debugger() -> WorkflowDebugger:
    """Get the global workflow debugger instance."""
    return _debugger
