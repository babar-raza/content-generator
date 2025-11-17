"""Mesh Router for Dynamic Agent Routing

Handles routing of agent requests based on capabilities, dependency resolution,
and circular dependency detection.
"""

import logging
import threading
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .agent_registry import AgentRegistry, AgentRegistration

logger = logging.getLogger(__name__)


@dataclass
class RouteRequest:
    """Request for agent routing"""
    request_id: str
    source_agent_id: str
    capability: str
    input_data: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RouteResponse:
    """Response from agent routing"""
    request_id: str
    target_agent_id: str
    target_agent_type: str
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """Circuit breaker for agent health management"""
    
    def __init__(self, failure_threshold: int = 3, timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self._failures: Dict[str, int] = {}
        self._last_failure: Dict[str, datetime] = {}
        self._lock = threading.Lock()
    
    def record_failure(self, agent_id: str):
        """Record a failure for an agent"""
        with self._lock:
            self._failures[agent_id] = self._failures.get(agent_id, 0) + 1
            self._last_failure[agent_id] = datetime.now(timezone.utc)
    
    def record_success(self, agent_id: str):
        """Record a success for an agent"""
        with self._lock:
            if agent_id in self._failures:
                self._failures[agent_id] = max(0, self._failures[agent_id] - 1)
    
    def is_open(self, agent_id: str) -> bool:
        """Check if circuit is open (agent should be avoided)"""
        with self._lock:
            if agent_id not in self._failures:
                return False
            
            failures = self._failures[agent_id]
            if failures < self.failure_threshold:
                return False
            
            # Check if timeout has elapsed
            last_failure = self._last_failure.get(agent_id)
            if last_failure:
                elapsed = (datetime.now(timezone.utc) - last_failure).total_seconds()
                if elapsed > self.timeout_seconds:
                    # Reset failures after timeout
                    self._failures[agent_id] = 0
                    return False
            
            return True


class MeshRouter:
    """Router for mesh orchestration
    
    Responsibilities:
    - Route requests to appropriate agents based on capabilities
    - Resolve agent dependencies
    - Detect circular dependencies
    - Manage circuit breaker for failed agents
    - Load balancing across available agents
    """
    
    def __init__(
        self,
        registry: AgentRegistry,
        max_hops: int = 10,
        routing_timeout_seconds: int = 5,
        enable_circuit_breaker: bool = True,
        failure_threshold: int = 3
    ):
        self.registry = registry
        self.max_hops = max_hops
        self.routing_timeout_seconds = routing_timeout_seconds
        self.enable_circuit_breaker = enable_circuit_breaker
        
        # Circuit breaker for health management
        self.circuit_breaker = CircuitBreaker(failure_threshold=failure_threshold) if enable_circuit_breaker else None
        
        # Execution tracking
        self._execution_path: List[str] = []
        self._hop_count = 0
        self._lock = threading.Lock()
        
        logger.info(f"MeshRouter initialized (max_hops={max_hops}, circuit_breaker={enable_circuit_breaker})")
    
    def route_to_agent(self, request: RouteRequest) -> RouteResponse:
        """Route a request to an appropriate agent
        
        Args:
            request: Route request with capability and input data
            
        Returns:
            Route response with target agent information
        """
        try:
            # Check hop count
            if self._hop_count >= self.max_hops:
                logger.error(f"Max hops ({self.max_hops}) exceeded for request {request.request_id}")
                return RouteResponse(
                    request_id=request.request_id,
                    target_agent_id="",
                    target_agent_type="",
                    success=False,
                    error=f"Maximum hop count ({self.max_hops}) exceeded"
                )
            
            # Find agents by capability
            agents = self.registry.find_by_capability(request.capability, include_degraded=False)
            
            if not agents:
                logger.warning(f"No agents found for capability: {request.capability}")
                return RouteResponse(
                    request_id=request.request_id,
                    target_agent_id="",
                    target_agent_type="",
                    success=False,
                    error=f"No agents available for capability: {request.capability}"
                )
            
            # Filter out agents with open circuit breakers
            if self.circuit_breaker:
                agents = [a for a in agents if not self.circuit_breaker.is_open(a.agent_id)]
                
                if not agents:
                    logger.warning(f"All agents for capability {request.capability} have open circuit breakers")
                    return RouteResponse(
                        request_id=request.request_id,
                        target_agent_id="",
                        target_agent_type="",
                        success=False,
                        error=f"All agents for capability {request.capability} are unavailable (circuit breaker)"
                    )
            
            # Select agent with lowest load
            selected_agent = agents[0]
            
            # Check for circular dependencies
            if self._would_create_cycle(selected_agent.agent_id, request.source_agent_id):
                logger.warning(f"Circular dependency detected: {selected_agent.agent_id} -> {request.source_agent_id}")
                
                # Try next agent
                if len(agents) > 1:
                    selected_agent = agents[1]
                    if self._would_create_cycle(selected_agent.agent_id, request.source_agent_id):
                        return RouteResponse(
                            request_id=request.request_id,
                            target_agent_id="",
                            target_agent_type="",
                            success=False,
                            error="Circular dependency detected in all available agents"
                        )
                else:
                    return RouteResponse(
                        request_id=request.request_id,
                        target_agent_id="",
                        target_agent_type="",
                        success=False,
                        error="Circular dependency detected"
                    )
            
            # Record in execution path
            with self._lock:
                self._execution_path.append(selected_agent.agent_id)
                self._hop_count += 1
            
            # Update agent load
            self.registry.increment_load(selected_agent.agent_id)
            
            logger.info(f"Routed request {request.request_id} to agent {selected_agent.agent_id}")
            
            return RouteResponse(
                request_id=request.request_id,
                target_agent_id=selected_agent.agent_id,
                target_agent_type=selected_agent.agent_type,
                success=True,
                metadata={
                    'hop_count': self._hop_count,
                    'agent_load': selected_agent.current_load
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to route request {request.request_id}: {e}", exc_info=True)
            return RouteResponse(
                request_id=request.request_id,
                target_agent_id="",
                target_agent_type="",
                success=False,
                error=str(e)
            )
    
    def _would_create_cycle(self, target_agent_id: str, source_agent_id: str) -> bool:
        """Check if routing to target would create a circular dependency
        
        Args:
            target_agent_id: Proposed target agent
            source_agent_id: Source agent making the request
            
        Returns:
            True if cycle would be created, False otherwise
        """
        with self._lock:
            # Simple cycle detection: check if target is already in execution path
            return target_agent_id in self._execution_path
    
    def resolve_dependencies(self, agent_id: str, dependencies: List[str]) -> List[str]:
        """Resolve agent dependencies in execution order
        
        Args:
            agent_id: Agent requiring dependencies
            dependencies: List of capability names needed
            
        Returns:
            Ordered list of agent IDs to execute
        """
        resolved: List[str] = []
        seen: Set[str] = set()
        
        def _resolve(capability: str):
            if capability in seen:
                return
            
            seen.add(capability)
            
            # Find agent for capability
            agents = self.registry.find_by_capability(capability)
            if not agents:
                logger.warning(f"No agent found for dependency: {capability}")
                return
            
            # Use first available agent
            agent = agents[0]
            
            # TODO: Could recursively resolve agent's own dependencies here
            # For now, just add the agent
            if agent.agent_id not in resolved:
                resolved.append(agent.agent_id)
        
        for dep in dependencies:
            _resolve(dep)
        
        return resolved
    
    def detect_cycles(self, graph: Dict[str, List[str]]) -> Optional[List[str]]:
        """Detect circular dependencies in agent dependency graph
        
        Args:
            graph: Dependency graph (agent_id -> list of dependent agent_ids)
            
        Returns:
            Cycle path if found, None otherwise
        """
        visited = set()
        rec_stack = set()
        path = []
        
        def _visit(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if _visit(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Cycle detected
                    cycle_start = path.index(neighbor)
                    return True
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if _visit(node):
                    return path
        
        return None
    
    def record_success(self, agent_id: str):
        """Record successful execution for circuit breaker
        
        Args:
            agent_id: Agent that succeeded
        """
        if self.circuit_breaker:
            self.circuit_breaker.record_success(agent_id)
        
        # Decrement load
        self.registry.decrement_load(agent_id)
    
    def record_failure(self, agent_id: str):
        """Record failed execution for circuit breaker
        
        Args:
            agent_id: Agent that failed
        """
        if self.circuit_breaker:
            self.circuit_breaker.record_failure(agent_id)
        
        # Decrement load
        self.registry.decrement_load(agent_id)
    
    def get_execution_trace(self) -> List[str]:
        """Get current execution trace
        
        Returns:
            List of agent IDs in execution order
        """
        with self._lock:
            return list(self._execution_path)
    
    def reset_execution_state(self):
        """Reset execution state for new workflow"""
        with self._lock:
            self._execution_path.clear()
            self._hop_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics
        
        Returns:
            Dictionary with router stats
        """
        with self._lock:
            return {
                'current_hop_count': self._hop_count,
                'execution_path_length': len(self._execution_path),
                'max_hops': self.max_hops,
                'circuit_breaker_enabled': self.enable_circuit_breaker
            }
