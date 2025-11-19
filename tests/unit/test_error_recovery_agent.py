"""
Unit tests for ErrorRecoveryAgent.

Tests the error recovery agent's ability to:
- Handle help requests from failing agents
- Find alternate agents by capability
- Propose alternate agent suggestions
- Validate input requirements
"""

import pytest
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.event_bus import EventBus, AgentEvent
from src.core.config import Config
from src.agents.support.error_recovery import ErrorRecoveryAgent


class MockAgentRegistry:
    """Mock agent registry for testing."""

    def __init__(self):
        self.agents = []

    def add_agent(self, agent_id: str, capabilities: list):
        """Add a mock agent to the registry."""
        mock_agent = Mock()
        mock_agent.agent_id = agent_id
        mock_agent.capabilities = capabilities
        self.agents.append(mock_agent)
        return mock_agent

    def find_agents_by_capability(self, capability: str):
        """Find agents with a specific capability."""
        return [agent for agent in self.agents if capability in agent.capabilities]


class TestErrorRecoveryAgentInitialization:
    """Tests for ErrorRecoveryAgent initialization."""

    def test_initialization(self):
        """Test agent initializes correctly."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        agent = ErrorRecoveryAgent(config, event_bus, registry)

        assert agent.agent_id == "ErrorRecoveryAgent"
        assert agent.registry == registry
        assert agent.config == config
        assert agent.event_bus == event_bus

    def test_contract_creation(self):
        """Test agent contract is created correctly."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        agent = ErrorRecoveryAgent(config, event_bus, registry)
        contract = agent._create_contract()

        assert contract.agent_id == "ErrorRecoveryAgent"
        assert "recover_errors" in contract.capabilities
        assert contract.input_schema["required"] == ["agent_id", "required_capabilities"]
        assert "help_response" in contract.publishes

    def test_event_subscription(self):
        """Test agent subscribes to help_request events."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        agent = ErrorRecoveryAgent(config, event_bus, registry)

        # Verify subscription was called
        event_bus.subscribe.assert_called_with("help_request", agent.execute)


class TestErrorRecoveryExecution:
    """Tests for ErrorRecoveryAgent execute method."""

    def test_execute_finds_alternate_agents(self):
        """Test execute finds alternate agents by capability."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        # Add agents to registry
        registry.add_agent("AgentA", ["capability1", "capability2"])
        registry.add_agent("AgentB", ["capability1"])
        registry.add_agent("AgentC", ["capability2"])

        agent = ErrorRecoveryAgent(config, event_bus, registry)

        # Create help request event
        event = AgentEvent(
            event_type="help_request",
            data={
                "agent_id": "AgentA",
                "required_capabilities": ["capability1"]
            },
            source_agent="AgentA",
            correlation_id="test-correlation"
        )

        result = agent.execute(event)

        assert result is not None
        assert result.event_type == "help_response"
        assert result.source_agent == "ErrorRecoveryAgent"
        assert result.correlation_id == "test-correlation"
        assert result.data["original_agent"] == "AgentA"
        assert "AgentB" in result.data["alternate_agents"]
        assert "AgentA" not in result.data["alternate_agents"]  # Should not include self

    def test_execute_multiple_capabilities(self):
        """Test execute handles multiple required capabilities."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        # Add agents with various capabilities
        registry.add_agent("AgentA", ["cap1"])
        registry.add_agent("AgentB", ["cap1", "cap2"])
        registry.add_agent("AgentC", ["cap2", "cap3"])
        registry.add_agent("AgentD", ["cap3"])

        agent = ErrorRecoveryAgent(config, event_bus, registry)

        event = AgentEvent(
            event_type="help_request",
            data={
                "agent_id": "AgentA",
                "required_capabilities": ["cap1", "cap2", "cap3"]
            },
            source_agent="AgentA",
            correlation_id="test-multi"
        )

        result = agent.execute(event)

        alternates = result.data["alternate_agents"]
        # Should find AgentB (cap1, cap2), AgentC (cap2, cap3), AgentD (cap3)
        assert len(alternates) >= 2  # At least B and C/D

    def test_execute_no_alternates_found(self):
        """Test execute when no alternate agents are available."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        # Add only the requesting agent
        registry.add_agent("AgentA", ["capability1"])

        agent = ErrorRecoveryAgent(config, event_bus, registry)

        event = AgentEvent(
            event_type="help_request",
            data={
                "agent_id": "AgentA",
                "required_capabilities": ["capability1"]
            },
            source_agent="AgentA",
            correlation_id="test-none"
        )

        result = agent.execute(event)

        assert result is not None
        assert result.data["alternate_agents"] == []
        assert "suggestion" in result.data


class TestErrorRecoveryValidation:
    """Tests for ErrorRecoveryAgent input validation."""

    def test_execute_missing_agent_id(self):
        """Test execute raises ValueError when agent_id is missing."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        agent = ErrorRecoveryAgent(config, event_bus, registry)

        event = AgentEvent(
            event_type="help_request",
            data={"required_capabilities": ["cap1"]},
            source_agent="TestAgent",
            correlation_id="test-missing-id"
        )

        with pytest.raises(ValueError) as exc_info:
            agent.execute(event)

        assert "agent_id is required" in str(exc_info.value)

    def test_execute_empty_agent_id(self):
        """Test execute raises ValueError when agent_id is empty string."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        agent = ErrorRecoveryAgent(config, event_bus, registry)

        event = AgentEvent(
            event_type="help_request",
            data={
                "agent_id": "",
                "required_capabilities": ["cap1"]
            },
            source_agent="TestAgent",
            correlation_id="test-empty-id"
        )

        with pytest.raises(ValueError) as exc_info:
            agent.execute(event)

        assert "agent_id is required" in str(exc_info.value)

    def test_execute_missing_capabilities(self):
        """Test execute raises ValueError when required_capabilities is missing."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        agent = ErrorRecoveryAgent(config, event_bus, registry)

        event = AgentEvent(
            event_type="help_request",
            data={"agent_id": "AgentA"},
            source_agent="AgentA",
            correlation_id="test-missing-caps"
        )

        with pytest.raises(ValueError) as exc_info:
            agent.execute(event)

        assert "required_capabilities is required" in str(exc_info.value)

    def test_execute_empty_capabilities(self):
        """Test execute raises ValueError when required_capabilities is empty list."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        agent = ErrorRecoveryAgent(config, event_bus, registry)

        event = AgentEvent(
            event_type="help_request",
            data={
                "agent_id": "AgentA",
                "required_capabilities": []
            },
            source_agent="AgentA",
            correlation_id="test-empty-caps"
        )

        with pytest.raises(ValueError) as exc_info:
            agent.execute(event)

        assert "required_capabilities is required" in str(exc_info.value)


class TestErrorRecoveryEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_execute_duplicate_alternates_removed(self):
        """Test that duplicate alternate agents are removed from results."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        # Add agent with multiple capabilities
        registry.add_agent("AgentA", ["cap1"])
        registry.add_agent("AgentB", ["cap1", "cap2", "cap3"])

        agent = ErrorRecoveryAgent(config, event_bus, registry)

        event = AgentEvent(
            event_type="help_request",
            data={
                "agent_id": "AgentA",
                "required_capabilities": ["cap1", "cap2", "cap3"]
            },
            source_agent="AgentA",
            correlation_id="test-dedup"
        )

        result = agent.execute(event)

        alternates = result.data["alternate_agents"]
        # AgentB should appear only once, even though it matches 3 capabilities
        assert alternates.count("AgentB") == 1

    def test_execute_case_sensitive_capability_matching(self):
        """Test that capability matching is case-sensitive."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        registry.add_agent("AgentA", ["Capability1"])
        registry.add_agent("AgentB", ["capability1"])

        agent = ErrorRecoveryAgent(config, event_bus, registry)

        # Request with lowercase
        event = AgentEvent(
            event_type="help_request",
            data={
                "agent_id": "AgentA",
                "required_capabilities": ["capability1"]
            },
            source_agent="AgentA",
            correlation_id="test-case"
        )

        result = agent.execute(event)

        # Should only find AgentB
        assert "AgentB" in result.data["alternate_agents"]
        assert "AgentA" not in result.data["alternate_agents"]

    def test_execute_preserves_correlation_id(self):
        """Test that correlation_id is preserved in response."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        agent = ErrorRecoveryAgent(config, event_bus, registry)

        correlation_id = "unique-correlation-12345"
        event = AgentEvent(
            event_type="help_request",
            data={
                "agent_id": "AgentA",
                "required_capabilities": ["cap1"]
            },
            source_agent="AgentA",
            correlation_id=correlation_id
        )

        result = agent.execute(event)

        assert result.correlation_id == correlation_id

    def test_execute_includes_suggestion(self):
        """Test that response includes a suggestion message."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        registry = MockAgentRegistry()

        agent = ErrorRecoveryAgent(config, event_bus, registry)

        event = AgentEvent(
            event_type="help_request",
            data={
                "agent_id": "AgentA",
                "required_capabilities": ["cap1"]
            },
            source_agent="AgentA",
            correlation_id="test-suggestion"
        )

        result = agent.execute(event)

        assert "suggestion" in result.data
        assert isinstance(result.data["suggestion"], str)
        assert len(result.data["suggestion"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
