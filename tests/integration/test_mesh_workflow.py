"""Integration tests for mesh workflow execution."""

import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import Config
from src.core.event_bus import EventBus
from src.core.contracts import AgentEvent
from src.orchestration.mesh_executor import MeshExecutor
from src.orchestration.agent_registry import AgentRegistry


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, agent_id, agent_type, next_capability=None):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.next_capability = next_capability
    
    def execute(self, event: AgentEvent):
        """Mock execute that returns test data."""
        output_data = {
            'agent_executed': self.agent_type,
            'input_received': event.data
        }
        
        # If configured, request next agent
        if self.next_capability:
            output_data['_mesh_request_capability'] = self.next_capability
        
        return AgentEvent(
            event_type=f"{self.agent_type}.complete",
            source_agent=self.agent_id,
            correlation_id=event.correlation_id,
            data=output_data
        )


class MockAgentFactory:
    """Mock agent factory for testing."""
    
    def __init__(self):
        self.agents = {}
    
    def add_agent(self, agent_type, agent):
        """Add mock agent."""
        self.agents[agent_type] = agent
    
    def create_agent(self, agent_type):
        """Create agent instance."""
        return self.agents.get(agent_type)


class TestMeshWorkflowIntegration:
    """Integration tests for mesh workflow execution."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.event_bus = EventBus()
        self.agent_factory = MockAgentFactory()
    
    def test_simple_mesh_workflow(self):
        """Test simple mesh workflow with 2 agents."""
        # Create mock agents
        agent1 = MockAgent(
            "agent1_id",
            "topic_identification",
            next_capability="content_structuring"
        )
        agent2 = MockAgent(
            "agent2_id",
            "outline_creation",
            next_capability=None  # Final agent
        )
        
        self.agent_factory.add_agent("topic_identification", agent1)
        self.agent_factory.add_agent("outline_creation", agent2)
        
        # Create executor
        executor = MeshExecutor(
            config=self.config,
            event_bus=self.event_bus,
            agent_factory=self.agent_factory,
            max_hops=5
        )
        
        # Register agents manually
        executor.registry.register_agent(
            agent_id="agent1_id",
            agent_type="topic_identification",
            capabilities=["topic_discovery", "content_planning"],
            metadata={'instance': agent1}
        )
        executor.registry.register_agent(
            agent_id="agent2_id",
            agent_type="outline_creation",
            capabilities=["content_structuring", "outline_generation"],
            metadata={'instance': agent2}
        )
        
        # Execute workflow
        job_id = f"test_{uuid.uuid4().hex[:8]}"
        result = executor.execute_mesh_workflow(
            workflow_name="test_workflow",
            initial_agent_type="topic_identification",
            input_data={"test_input": "value"},
            job_id=job_id
        )
        
        # Verify result
        assert result.success is True
        assert result.total_hops == 2
        assert len(result.agents_executed) == 2
        assert "agent1_id" in result.agents_executed
        assert "agent2_id" in result.agents_executed
    
    def test_mesh_workflow_with_three_hops(self):
        """Test mesh workflow with 3 agent hops."""
        # Create chain of 3 agents
        agent1 = MockAgent("a1", "type1", next_capability="cap2")
        agent2 = MockAgent("a2", "type2", next_capability="cap3")
        agent3 = MockAgent("a3", "type3", next_capability=None)
        
        self.agent_factory.add_agent("type1", agent1)
        self.agent_factory.add_agent("type2", agent2)
        self.agent_factory.add_agent("type3", agent3)
        
        executor = MeshExecutor(
            config=self.config,
            event_bus=self.event_bus,
            agent_factory=self.agent_factory,
            max_hops=10
        )
        
        # Register agents
        executor.registry.register_agent("a1", "type1", ["cap1"], metadata={'instance': agent1})
        executor.registry.register_agent("a2", "type2", ["cap2"], metadata={'instance': agent2})
        executor.registry.register_agent("a3", "type3", ["cap3"], metadata={'instance': agent3})
        
        # Execute
        job_id = f"test_{uuid.uuid4().hex[:8]}"
        result = executor.execute_mesh_workflow(
            workflow_name="three_hop_test",
            initial_agent_type="type1",
            input_data={"start": "data"},
            job_id=job_id
        )
        
        # Verify
        assert result.success is True
        assert result.total_hops == 3
        assert len(result.execution_trace) == 3
    
    def test_mesh_workflow_agent_not_found(self):
        """Test workflow fails gracefully when agent not found."""
        executor = MeshExecutor(
            config=self.config,
            event_bus=self.event_bus,
            agent_factory=self.agent_factory,
            max_hops=5
        )
        
        # Try to execute with non-existent agent
        job_id = f"test_{uuid.uuid4().hex[:8]}"
        result = executor.execute_mesh_workflow(
            workflow_name="fail_test",
            initial_agent_type="non_existent_agent",
            input_data={},
            job_id=job_id
        )
        
        # Should fail gracefully
        assert result.success is False
        assert "not found" in result.error.lower()
    
    def test_mesh_workflow_max_hops_limit(self):
        """Test workflow stops at max hops limit."""
        # Create agents that always request next agent (infinite loop scenario)
        agent1 = MockAgent("a1", "type1", next_capability="cap2")
        agent2 = MockAgent("a2", "type2", next_capability="cap1")  # Points back to cap1
        
        self.agent_factory.add_agent("type1", agent1)
        self.agent_factory.add_agent("type2", agent2)
        
        executor = MeshExecutor(
            config=self.config,
            event_bus=self.event_bus,
            agent_factory=self.agent_factory,
            max_hops=3  # Low limit
        )
        
        # Register agents
        executor.registry.register_agent("a1", "type1", ["cap1"], metadata={'instance': agent1})
        executor.registry.register_agent("a2", "type2", ["cap2"], metadata={'instance': agent2})
        
        # Execute
        job_id = f"test_{uuid.uuid4().hex[:8]}"
        result = executor.execute_mesh_workflow(
            workflow_name="max_hop_test",
            initial_agent_type="type1",
            input_data={},
            job_id=job_id
        )
        
        # Should stop at max hops (prevent infinite loop)
        # Note: Due to cycle detection, this might fail before max hops
        assert result.total_hops <= 3
    
    def test_mesh_workflow_accumulates_data(self):
        """Test workflow accumulates data across agents."""
        # Create agents that add to accumulated data
        class DataAgent(MockAgent):
            def __init__(self, agent_id, agent_type, key_to_add, next_capability=None):
                super().__init__(agent_id, agent_type, next_capability)
                self.key_to_add = key_to_add
            
            def execute(self, event):
                # Add to accumulated data
                output_data = event.data.copy()
                output_data[self.key_to_add] = f"value_from_{self.agent_type}"
                output_data['agent_executed'] = self.agent_type
                
                if self.next_capability:
                    output_data['_mesh_request_capability'] = self.next_capability
                
                return AgentEvent(
                    event_type=f"{self.agent_type}.complete",
                    source_agent=self.agent_id,
                    correlation_id=event.correlation_id,
                    data=output_data
                )
        
        agent1 = DataAgent("a1", "type1", "key1", next_capability="cap2")
        agent2 = DataAgent("a2", "type2", "key2", next_capability=None)
        
        self.agent_factory.add_agent("type1", agent1)
        self.agent_factory.add_agent("type2", agent2)
        
        executor = MeshExecutor(
            config=self.config,
            event_bus=self.event_bus,
            agent_factory=self.agent_factory,
            max_hops=5
        )
        
        executor.registry.register_agent("a1", "type1", ["cap1"], metadata={'instance': agent1})
        executor.registry.register_agent("a2", "type2", ["cap2"], metadata={'instance': agent2})
        
        # Execute with initial data
        job_id = f"test_{uuid.uuid4().hex[:8]}"
        result = executor.execute_mesh_workflow(
            workflow_name="accumulate_test",
            initial_agent_type="type1",
            input_data={"initial": "data"},
            job_id=job_id
        )
        
        # Verify data accumulated
        assert result.success is True
        assert "initial" in result.final_output
        assert "key1" in result.final_output
        assert "key2" in result.final_output
        assert result.final_output["key1"] == "value_from_type1"
        assert result.final_output["key2"] == "value_from_type2"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
