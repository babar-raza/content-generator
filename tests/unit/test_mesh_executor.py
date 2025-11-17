"""Unit tests for mesh orchestration components."""

import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.orchestration.agent_registry import AgentRegistry, AgentRegistration, AgentHealth
from src.orchestration.mesh_router import MeshRouter, RouteRequest, CircuitBreaker
from src.orchestration.mesh_executor import MeshExecutor


class TestAgentRegistry:
    """Test AgentRegistry functionality."""
    
    def setup_method(self):
        """Create fresh registry for each test."""
        self.registry = AgentRegistry()
    
    def test_register_agent(self):
        """Test agent registration."""
        success = self.registry.register_agent(
            agent_id="test_agent_1",
            agent_type="topic_identification",
            capabilities=["topic_discovery", "content_planning"]
        )
        
        assert success is True
        assert "test_agent_1" in self.registry._agents
        
        # Verify agent details
        agent = self.registry.get_agent("test_agent_1")
        assert agent is not None
        assert agent.agent_type == "topic_identification"
        assert "topic_discovery" in agent.capabilities
    
    def test_deregister_agent(self):
        """Test agent deregistration."""
        self.registry.register_agent(
            agent_id="test_agent_2",
            agent_type="section_writer",
            capabilities=["section_writing"]
        )
        
        success = self.registry.deregister_agent("test_agent_2")
        assert success is True
        assert self.registry.get_agent("test_agent_2") is None
    
    def test_find_by_capability(self):
        """Test finding agents by capability."""
        self.registry.register_agent(
            agent_id="agent_1",
            agent_type="type_a",
            capabilities=["cap_x", "cap_y"]
        )
        self.registry.register_agent(
            agent_id="agent_2",
            agent_type="type_b",
            capabilities=["cap_x", "cap_z"]
        )
        
        # Find agents with cap_x
        agents = self.registry.find_by_capability("cap_x")
        assert len(agents) == 2
        
        # Find agents with cap_z
        agents = self.registry.find_by_capability("cap_z")
        assert len(agents) == 1
        assert agents[0].agent_id == "agent_2"
        
        # Find non-existent capability
        agents = self.registry.find_by_capability("cap_not_exist")
        assert len(agents) == 0
    
    def test_find_by_capability_health_filter(self):
        """Test capability search filters unhealthy agents."""
        self.registry.register_agent(
            agent_id="healthy_agent",
            agent_type="type_a",
            capabilities=["cap_test"]
        )
        self.registry.register_agent(
            agent_id="unhealthy_agent",
            agent_type="type_b",
            capabilities=["cap_test"]
        )
        
        # Mark one agent unhealthy
        self.registry.update_health("unhealthy_agent", AgentHealth.UNHEALTHY)
        
        # Should only return healthy agent
        agents = self.registry.find_by_capability("cap_test")
        assert len(agents) == 1
        assert agents[0].agent_id == "healthy_agent"
        
        # With include_degraded, still should not include unhealthy
        agents = self.registry.find_by_capability("cap_test", include_degraded=True)
        assert len(agents) == 1
    
    def test_load_management(self):
        """Test agent load tracking."""
        self.registry.register_agent(
            agent_id="load_test_agent",
            agent_type="type_a",
            capabilities=["cap_1"]
        )
        
        # Initial load should be 0
        agent = self.registry.get_agent("load_test_agent")
        assert agent.current_load == 0
        
        # Increment load
        self.registry.increment_load("load_test_agent")
        agent = self.registry.get_agent("load_test_agent")
        assert agent.current_load == 1
        
        # Decrement load
        self.registry.decrement_load("load_test_agent")
        agent = self.registry.get_agent("load_test_agent")
        assert agent.current_load == 0
    
    def test_list_available(self):
        """Test listing available agents."""
        self.registry.register_agent("agent1", "type_a", ["cap1"])
        self.registry.register_agent("agent2", "type_b", ["cap2"])
        self.registry.update_health("agent2", AgentHealth.DEGRADED)
        
        # List healthy only
        agents = self.registry.list_available(healthy_only=True)
        assert len(agents) == 1
        
        # List all
        agents = self.registry.list_available(healthy_only=False)
        assert len(agents) == 2
    
    def test_get_stats(self):
        """Test registry statistics."""
        self.registry.register_agent("agent1", "type_a", ["cap1"])
        self.registry.register_agent("agent2", "type_b", ["cap2", "cap3"])
        
        stats = self.registry.get_stats()
        assert stats['total_agents'] == 2
        assert stats['healthy_agents'] == 2
        assert stats['total_capabilities'] == 3


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""
    
    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=60)
        
        # Circuit should be closed initially
        assert cb.is_open("agent1") is False
        
        # Record failures
        cb.record_failure("agent1")
        cb.record_failure("agent1")
        assert cb.is_open("agent1") is False  # Not yet open
        
        cb.record_failure("agent1")
        assert cb.is_open("agent1") is True  # Now open
    
    def test_circuit_resets_on_success(self):
        """Test circuit resets on successful execution."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=60)
        
        # Add some failures
        cb.record_failure("agent1")
        cb.record_failure("agent1")
        
        # Record success
        cb.record_success("agent1")
        
        # Failure count should decrease
        assert cb._failures.get("agent1", 0) == 1


class TestMeshRouter:
    """Test MeshRouter functionality."""
    
    def setup_method(self):
        """Create fresh router and registry for each test."""
        self.registry = AgentRegistry()
        self.router = MeshRouter(
            registry=self.registry,
            max_hops=10,
            routing_timeout_seconds=5,
            enable_circuit_breaker=True
        )
    
    def test_route_to_agent_success(self):
        """Test successful routing to agent."""
        # Register agent
        self.registry.register_agent(
            agent_id="target_agent",
            agent_type="section_writer",
            capabilities=["section_writing"]
        )
        
        # Create route request
        request = RouteRequest(
            request_id="req_1",
            source_agent_id="source_agent",
            capability="section_writing",
            input_data={"content": "test"}
        )
        
        # Route
        response = self.router.route_to_agent(request)
        
        assert response.success is True
        assert response.target_agent_id == "target_agent"
        assert response.target_agent_type == "section_writer"
    
    def test_route_to_agent_no_match(self):
        """Test routing when no agent matches capability."""
        request = RouteRequest(
            request_id="req_2",
            source_agent_id="source_agent",
            capability="non_existent_capability",
            input_data={}
        )
        
        response = self.router.route_to_agent(request)
        
        assert response.success is False
        assert "No agents available" in response.error
    
    def test_route_prevents_cycles(self):
        """Test cycle detection in routing."""
        # Register agents
        self.registry.register_agent("agent_a", "type_a", ["cap_a"])
        self.registry.register_agent("agent_b", "type_b", ["cap_b"])
        
        # Route to agent_a first
        request1 = RouteRequest(
            request_id="req_1",
            source_agent_id="source",
            capability="cap_a",
            input_data={}
        )
        response1 = self.router.route_to_agent(request1)
        assert response1.success is True
        
        # Try to route back to agent_a (would create cycle)
        request2 = RouteRequest(
            request_id="req_2",
            source_agent_id="agent_b",
            capability="cap_a",
            input_data={}
        )
        response2 = self.router.route_to_agent(request2)
        assert response2.success is False
        assert "Circular dependency" in response2.error
    
    def test_max_hops_exceeded(self):
        """Test max hops limit enforcement."""
        router = MeshRouter(
            registry=self.registry,
            max_hops=2,
            routing_timeout_seconds=5,
            enable_circuit_breaker=False
        )
        
        self.registry.register_agent("agent1", "type1", ["cap1"])
        self.registry.register_agent("agent2", "type2", ["cap2"])
        self.registry.register_agent("agent3", "type3", ["cap3"])
        
        # First hop
        req1 = RouteRequest("r1", "source", "cap1", {})
        resp1 = router.route_to_agent(req1)
        assert resp1.success is True
        
        # Second hop
        req2 = RouteRequest("r2", "agent1", "cap2", {})
        resp2 = router.route_to_agent(req2)
        assert resp2.success is True
        
        # Third hop (should fail)
        req3 = RouteRequest("r3", "agent2", "cap3", {})
        resp3 = router.route_to_agent(req3)
        assert resp3.success is False
        assert "Maximum hop count" in resp3.error
    
    def test_load_balancing(self):
        """Test agents are selected based on load."""
        # Register two agents with same capability
        self.registry.register_agent("agent_low_load", "type_a", ["cap_test"])
        self.registry.register_agent("agent_high_load", "type_b", ["cap_test"])
        
        # Set different loads
        self.registry.update_load("agent_low_load", 2)
        self.registry.update_load("agent_high_load", 5)
        
        # Route should select low load agent
        request = RouteRequest("req", "source", "cap_test", {})
        response = self.router.route_to_agent(request)
        
        assert response.success is True
        assert response.target_agent_id == "agent_low_load"


class TestMeshExecutor:
    """Test MeshExecutor functionality."""
    
    def setup_method(self):
        """Create mock components for testing."""
        self.config = MagicMock()
        self.event_bus = MagicMock()
        self.agent_factory = MagicMock()
    
    def test_executor_initialization(self):
        """Test mesh executor initializes correctly."""
        executor = MeshExecutor(
            config=self.config,
            event_bus=self.event_bus,
            agent_factory=self.agent_factory,
            max_hops=10
        )
        
        assert executor.registry is not None
        assert executor.router is not None
        assert executor.router.max_hops == 10
    
    def test_discover_agents(self):
        """Test agent discovery."""
        # Mock agent factory to return agent instances
        mock_agent = MagicMock()
        self.agent_factory.create_agent = MagicMock(return_value=mock_agent)
        
        executor = MeshExecutor(
            config=self.config,
            event_bus=self.event_bus,
            agent_factory=self.agent_factory
        )
        
        discovered = executor.discover_agents()
        
        # Should discover multiple agents
        assert len(discovered) > 0
        assert all('agent_id' in a for a in discovered)
        assert all('capabilities' in a for a in discovered)
    
    def test_list_agents(self):
        """Test listing registered agents."""
        executor = MeshExecutor(
            config=self.config,
            event_bus=self.event_bus,
            agent_factory=self.agent_factory
        )
        
        # Register test agent
        executor.registry.register_agent(
            agent_id="test_agent",
            agent_type="test_type",
            capabilities=["test_cap"]
        )
        
        agents = executor.list_agents()
        assert len(agents) == 1
        assert agents[0]['agent_id'] == "test_agent"
    
    def test_get_stats(self):
        """Test getting executor statistics."""
        executor = MeshExecutor(
            config=self.config,
            event_bus=self.event_bus,
            agent_factory=self.agent_factory
        )
        
        stats = executor.get_stats()
        assert 'registry_stats' in stats
        assert 'router_stats' in stats
        assert 'active_contexts' in stats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
