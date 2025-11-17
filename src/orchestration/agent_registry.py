"""Agent Registry for Mesh Orchestration

Provides service registry for agent discovery and capability-based routing.
Supports health-aware agent selection and dynamic registration.
"""

import logging
import threading
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class AgentHealth(Enum):
    """Agent health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class AgentRegistration:
    """Agent registration information"""
    agent_id: str
    agent_type: str
    capabilities: List[str]
    health_status: AgentHealth = AgentHealth.UNKNOWN
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_load: int = 0
    max_capacity: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'agent_id': self.agent_id,
            'agent_type': self.agent_type,
            'capabilities': self.capabilities,
            'health_status': self.health_status.value,
            'registered_at': self.registered_at.isoformat(),
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'current_load': self.current_load,
            'max_capacity': self.max_capacity,
            'metadata': self.metadata
        }


class AgentRegistry:
    """Registry for agent discovery and capability-based lookup
    
    Responsibilities:
    - Maintain registry of available agents
    - Support capability-based agent discovery
    - Track agent health and load
    - Provide thread-safe registration/lookup
    """
    
    def __init__(self):
        self._agents: Dict[str, AgentRegistration] = {}
        self._capability_index: Dict[str, Set[str]] = {}  # capability -> set of agent_ids
        self._lock = threading.RLock()
        logger.info("AgentRegistry initialized")
    
    def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register an agent in the registry
        
        Args:
            agent_id: Unique agent identifier
            agent_type: Type of agent (e.g., 'topic_identification')
            capabilities: List of capabilities this agent provides
            metadata: Optional metadata
            
        Returns:
            True if registration successful, False otherwise
        """
        with self._lock:
            try:
                # Create registration
                registration = AgentRegistration(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    capabilities=capabilities,
                    health_status=AgentHealth.HEALTHY,
                    metadata=metadata or {}
                )
                
                # Store in registry
                self._agents[agent_id] = registration
                
                # Index by capabilities
                for capability in capabilities:
                    if capability not in self._capability_index:
                        self._capability_index[capability] = set()
                    self._capability_index[capability].add(agent_id)
                
                logger.info(f"Registered agent: {agent_id} with capabilities: {capabilities}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to register agent {agent_id}: {e}")
                return False
    
    def deregister_agent(self, agent_id: str) -> bool:
        """Deregister an agent from the registry
        
        Args:
            agent_id: Agent identifier to deregister
            
        Returns:
            True if deregistration successful, False otherwise
        """
        with self._lock:
            if agent_id not in self._agents:
                logger.warning(f"Agent {agent_id} not found in registry")
                return False
            
            try:
                registration = self._agents[agent_id]
                
                # Remove from capability index
                for capability in registration.capabilities:
                    if capability in self._capability_index:
                        self._capability_index[capability].discard(agent_id)
                        if not self._capability_index[capability]:
                            del self._capability_index[capability]
                
                # Remove from registry
                del self._agents[agent_id]
                
                logger.info(f"Deregistered agent: {agent_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to deregister agent {agent_id}: {e}")
                return False
    
    def find_by_capability(self, capability: str, include_degraded: bool = False) -> List[AgentRegistration]:
        """Find agents by capability
        
        Args:
            capability: Capability to search for
            include_degraded: Whether to include degraded agents
            
        Returns:
            List of agent registrations with the capability, sorted by load
        """
        with self._lock:
            if capability not in self._capability_index:
                logger.debug(f"No agents found with capability: {capability}")
                return []
            
            agent_ids = self._capability_index[capability]
            agents = []
            
            for agent_id in agent_ids:
                registration = self._agents.get(agent_id)
                if not registration:
                    continue
                
                # Filter by health
                if registration.health_status == AgentHealth.HEALTHY:
                    agents.append(registration)
                elif include_degraded and registration.health_status == AgentHealth.DEGRADED:
                    agents.append(registration)
            
            # Sort by load (ascending) for load balancing
            agents.sort(key=lambda a: a.current_load)
            
            logger.debug(f"Found {len(agents)} agents for capability: {capability}")
            return agents
    
    def find_by_type(self, agent_type: str) -> Optional[AgentRegistration]:
        """Find agent by type
        
        Args:
            agent_type: Agent type to find
            
        Returns:
            Agent registration if found, None otherwise
        """
        with self._lock:
            for registration in self._agents.values():
                if registration.agent_type == agent_type:
                    return registration
            return None
    
    def get_agent(self, agent_id: str) -> Optional[AgentRegistration]:
        """Get agent registration by ID
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent registration if found, None otherwise
        """
        with self._lock:
            return self._agents.get(agent_id)
    
    def list_available(self, healthy_only: bool = True) -> List[AgentRegistration]:
        """List all available agents
        
        Args:
            healthy_only: Only return healthy agents
            
        Returns:
            List of agent registrations
        """
        with self._lock:
            if healthy_only:
                agents = [
                    reg for reg in self._agents.values()
                    if reg.health_status == AgentHealth.HEALTHY
                ]
            else:
                agents = list(self._agents.values())
            
            return sorted(agents, key=lambda a: a.agent_type)
    
    def update_health(self, agent_id: str, health_status: AgentHealth) -> bool:
        """Update agent health status
        
        Args:
            agent_id: Agent identifier
            health_status: New health status
            
        Returns:
            True if update successful, False otherwise
        """
        with self._lock:
            if agent_id not in self._agents:
                return False
            
            self._agents[agent_id].health_status = health_status
            self._agents[agent_id].last_heartbeat = datetime.now(timezone.utc)
            
            logger.debug(f"Updated health for {agent_id}: {health_status.value}")
            return True
    
    def update_load(self, agent_id: str, current_load: int) -> bool:
        """Update agent current load
        
        Args:
            agent_id: Agent identifier
            current_load: Current load value
            
        Returns:
            True if update successful, False otherwise
        """
        with self._lock:
            if agent_id not in self._agents:
                return False
            
            self._agents[agent_id].current_load = current_load
            return True
    
    def increment_load(self, agent_id: str) -> bool:
        """Increment agent load counter
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if increment successful, False otherwise
        """
        with self._lock:
            if agent_id not in self._agents:
                return False
            
            self._agents[agent_id].current_load += 1
            return True
    
    def decrement_load(self, agent_id: str) -> bool:
        """Decrement agent load counter
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if decrement successful, False otherwise
        """
        with self._lock:
            if agent_id not in self._agents:
                return False
            
            if self._agents[agent_id].current_load > 0:
                self._agents[agent_id].current_load -= 1
            return True
    
    def get_capabilities(self) -> List[str]:
        """Get list of all available capabilities
        
        Returns:
            List of capability names
        """
        with self._lock:
            return sorted(self._capability_index.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics
        
        Returns:
            Dictionary with registry stats
        """
        with self._lock:
            total_agents = len(self._agents)
            healthy_agents = sum(1 for a in self._agents.values() if a.health_status == AgentHealth.HEALTHY)
            total_capabilities = len(self._capability_index)
            
            return {
                'total_agents': total_agents,
                'healthy_agents': healthy_agents,
                'degraded_agents': sum(1 for a in self._agents.values() if a.health_status == AgentHealth.DEGRADED),
                'unhealthy_agents': sum(1 for a in self._agents.values() if a.health_status == AgentHealth.UNHEALTHY),
                'total_capabilities': total_capabilities,
                'avg_load': sum(a.current_load for a in self._agents.values()) / total_agents if total_agents > 0 else 0
            }
    
    def clear(self):
        """Clear all registrations (for testing)"""
        with self._lock:
            self._agents.clear()
            self._capability_index.clear()
            logger.info("Registry cleared")
