"""
Unit tests for ModelSelectionAgent.

Tests the model selection agent's ability to:
- Select appropriate models based on capability
- Handle Ollama detector integration
- Fallback to config defaults when needed
- Handle errors gracefully
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.event_bus import EventBus, AgentEvent
from src.core.config import Config
from src.agents.support.model_selection import ModelSelectionAgent


class TestModelSelectionAgentInitialization:
    """Tests for ModelSelectionAgent initialization."""

    def test_initialization(self):
        """Test agent initializes correctly."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        assert agent.agent_id == "ModelSelectionAgent"
        assert agent.performance_tracker == performance_tracker
        assert agent.config == config
        assert agent.event_bus == event_bus

    def test_contract_creation(self):
        """Test agent contract is created correctly."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)
        contract = agent._create_contract()

        assert contract.agent_id == "ModelSelectionAgent"
        assert "select_model" in contract.capabilities
        assert contract.input_schema["required"] == ["capability"]
        assert "model_selected" in contract.publishes

    def test_event_subscription(self):
        """Test agent subscribes to model_selection_request events."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        # Verify subscription was called
        event_bus.subscribe.assert_called_with("model_selection_request", agent.execute)


class TestModelSelectionWithOllamaDetector:
    """Tests for model selection using Ollama detector."""

    @patch('src.utils.ollama_detector.get_ollama_detector')
    def test_execute_with_available_ollama(self, mock_get_detector):
        """Test execute when Ollama is available."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        # Mock Ollama detector
        mock_detector = Mock()
        mock_detector.is_ollama_available.return_value = (True, "available")
        mock_detector.get_best_model_for_capability.return_value = "ollama-model-123"
        mock_get_detector.return_value = mock_detector

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        event = AgentEvent(
            event_type="model_selection_request",
            data={"capability": "generate_content"},
            source_agent="TestAgent",
            correlation_id="test-correlation"
        )

        result = agent.execute(event)

        assert result is not None
        assert result.event_type == "model_selected"
        assert result.data["model_name"] == "ollama-model-123"
        assert result.source_agent == "ModelSelectionAgent"
        assert result.correlation_id == "test-correlation"
        mock_detector.get_best_model_for_capability.assert_called_with("generate_content")

    @patch('src.utils.ollama_detector.get_ollama_detector')
    def test_execute_ollama_unavailable(self, mock_get_detector):
        """Test execute falls back to config when Ollama is unavailable."""
        config = Mock(spec=Config)
        config.ollama_code_model = "code-model"
        config.ollama_content_model = "content-model"
        config.ollama_topic_model = "topic-model"
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        # Mock Ollama detector as unavailable
        mock_detector = Mock()
        mock_detector.is_ollama_available.return_value = (False, "not available")
        mock_get_detector.return_value = mock_detector

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        event = AgentEvent(
            event_type="model_selection_request",
            data={"capability": "code"},
            source_agent="TestAgent",
            correlation_id="test-fallback"
        )

        result = agent.execute(event)

        assert result.data["model_name"] == "code-model"

    @patch('src.utils.ollama_detector.get_ollama_detector')
    def test_execute_detector_no_model_fallback(self, mock_get_detector):
        """Test execute falls back to config when detector returns no model."""
        config = Mock(spec=Config)
        config.ollama_code_model = "code-model"
        config.ollama_content_model = "content-model"
        config.ollama_topic_model = "topic-model"
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        # Mock Ollama detector available but no model for capability
        mock_detector = Mock()
        mock_detector.is_ollama_available.return_value = (True, "available")
        mock_detector.get_best_model_for_capability.return_value = None
        mock_get_detector.return_value = mock_detector

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        event = AgentEvent(
            event_type="model_selection_request",
            data={"capability": "validate"},
            source_agent="TestAgent",
            correlation_id="test-no-model"
        )

        result = agent.execute(event)

        assert result.data["model_name"] == "code-model"


class TestModelSelectionFallbackLogic:
    """Tests for model selection fallback logic."""

    @patch('src.utils.ollama_detector.get_ollama_detector')
    def test_code_capability_fallback(self, mock_get_detector):
        """Test fallback selects code model for code-related capabilities."""
        config = Mock(spec=Config)
        config.ollama_code_model = "code-model-v1"
        config.ollama_content_model = "content-model-v1"
        config.ollama_topic_model = "topic-model-v1"
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        mock_detector = Mock()
        mock_detector.is_ollama_available.return_value = (True, "available")
        mock_detector.get_best_model_for_capability.return_value = None
        mock_get_detector.return_value = mock_detector

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        # Test various code-related capabilities
        code_capabilities = ["code", "validate", "split", "code_review", "validate_syntax"]
        for capability in code_capabilities:
            event = AgentEvent(
                event_type="model_selection_request",
                data={"capability": capability},
                source_agent="TestAgent",
                correlation_id=f"test-{capability}"
            )
            result = agent.execute(event)
            assert result.data["model_name"] == "code-model-v1", f"Failed for capability: {capability}"

    @patch('src.utils.ollama_detector.get_ollama_detector')
    def test_content_capability_fallback(self, mock_get_detector):
        """Test fallback selects content model for content-related capabilities."""
        config = Mock(spec=Config)
        config.ollama_code_model = "code-model-v1"
        config.ollama_content_model = "content-model-v1"
        config.ollama_topic_model = "topic-model-v1"
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        mock_detector = Mock()
        mock_detector.is_ollama_available.return_value = (True, "available")
        mock_detector.get_best_model_for_capability.return_value = None
        mock_get_detector.return_value = mock_detector

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        # Test various content-related capabilities
        content_capabilities = ["content", "write", "generate", "write_blog", "generate_article"]
        for capability in content_capabilities:
            event = AgentEvent(
                event_type="model_selection_request",
                data={"capability": capability},
                source_agent="TestAgent",
                correlation_id=f"test-{capability}"
            )
            result = agent.execute(event)
            assert result.data["model_name"] == "content-model-v1", f"Failed for capability: {capability}"

    @patch('src.utils.ollama_detector.get_ollama_detector')
    def test_default_capability_fallback(self, mock_get_detector):
        """Test fallback selects topic model for other capabilities."""
        config = Mock(spec=Config)
        config.ollama_code_model = "code-model-v1"
        config.ollama_content_model = "content-model-v1"
        config.ollama_topic_model = "topic-model-v1"
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        mock_detector = Mock()
        mock_detector.is_ollama_available.return_value = (True, "available")
        mock_detector.get_best_model_for_capability.return_value = None
        mock_get_detector.return_value = mock_detector

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        # Test capabilities that don't match code or content
        other_capabilities = ["summarize", "analyze", "research", "keywords"]
        for capability in other_capabilities:
            event = AgentEvent(
                event_type="model_selection_request",
                data={"capability": capability},
                source_agent="TestAgent",
                correlation_id=f"test-{capability}"
            )
            result = agent.execute(event)
            assert result.data["model_name"] == "topic-model-v1", f"Failed for capability: {capability}"


class TestModelSelectionErrorHandling:
    """Tests for error handling in model selection."""

    @patch('src.utils.ollama_detector.get_ollama_detector')
    def test_execute_detector_exception(self, mock_get_detector):
        """Test execute handles detector exceptions gracefully."""
        config = Mock(spec=Config)
        config.ollama_code_model = "code-model"
        config.ollama_content_model = "content-model"
        config.ollama_topic_model = "topic-model"
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        # Mock detector raising exception
        mock_get_detector.side_effect = Exception("Detector failed")

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        event = AgentEvent(
            event_type="model_selection_request",
            data={"capability": "code"},
            source_agent="TestAgent",
            correlation_id="test-exception"
        )

        # Should not raise, should fallback to config
        result = agent.execute(event)
        assert result is not None
        assert result.data["model_name"] == "code-model"

    @patch('src.utils.ollama_detector.get_ollama_detector')
    def test_execute_empty_capability(self, mock_get_detector):
        """Test execute handles empty capability string."""
        config = Mock(spec=Config)
        config.ollama_topic_model = "topic-model"
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        mock_detector = Mock()
        mock_detector.is_ollama_available.return_value = (True, "available")
        mock_detector.get_best_model_for_capability.return_value = None
        mock_get_detector.return_value = mock_detector

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        event = AgentEvent(
            event_type="model_selection_request",
            data={"capability": ""},
            source_agent="TestAgent",
            correlation_id="test-empty"
        )

        result = agent.execute(event)
        # Should default to topic model
        assert result.data["model_name"] == "topic-model"

    @patch('src.utils.ollama_detector.get_ollama_detector')
    def test_execute_missing_capability(self, mock_get_detector):
        """Test execute handles missing capability field."""
        config = Mock(spec=Config)
        config.ollama_topic_model = "topic-model"
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        mock_detector = Mock()
        mock_detector.is_ollama_available.return_value = (True, "available")
        mock_detector.get_best_model_for_capability.return_value = None
        mock_get_detector.return_value = mock_detector

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        event = AgentEvent(
            event_type="model_selection_request",
            data={},
            source_agent="TestAgent",
            correlation_id="test-missing"
        )

        result = agent.execute(event)
        # Should default to topic model
        assert result.data["model_name"] == "topic-model"


class TestModelSelectionEdgeCases:
    """Tests for edge cases and special scenarios."""

    @patch('src.utils.ollama_detector.get_ollama_detector')
    def test_execute_case_insensitive_matching(self, mock_get_detector):
        """Test capability matching is case-insensitive."""
        config = Mock(spec=Config)
        config.ollama_code_model = "code-model"
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        mock_detector = Mock()
        mock_detector.is_ollama_available.return_value = (True, "available")
        mock_detector.get_best_model_for_capability.return_value = None
        mock_get_detector.return_value = mock_detector

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        # Test uppercase capability
        event = AgentEvent(
            event_type="model_selection_request",
            data={"capability": "CODE"},
            source_agent="TestAgent",
            correlation_id="test-upper"
        )

        result = agent.execute(event)
        assert result.data["model_name"] == "code-model"

    @patch('src.utils.ollama_detector.get_ollama_detector')
    def test_execute_preserves_correlation_id(self, mock_get_detector):
        """Test that correlation_id is preserved in response."""
        config = Mock(spec=Config)
        config.ollama_topic_model = "topic-model"
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        mock_detector = Mock()
        mock_detector.is_ollama_available.return_value = (True, "available")
        mock_detector.get_best_model_for_capability.return_value = "selected-model"
        mock_get_detector.return_value = mock_detector

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        correlation_id = "unique-correlation-67890"
        event = AgentEvent(
            event_type="model_selection_request",
            data={"capability": "test"},
            source_agent="TestAgent",
            correlation_id=correlation_id
        )

        result = agent.execute(event)
        assert result.correlation_id == correlation_id

    @patch('src.utils.ollama_detector.get_ollama_detector')
    def test_execute_passes_lowercase_to_detector(self, mock_get_detector):
        """Test that capability is passed to detector in lowercase."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        mock_detector = Mock()
        mock_detector.is_ollama_available.return_value = (True, "available")
        mock_detector.get_best_model_for_capability.return_value = "model"
        mock_get_detector.return_value = mock_detector

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        event = AgentEvent(
            event_type="model_selection_request",
            data={"capability": "GENERATE_CONTENT"},
            source_agent="TestAgent",
            correlation_id="test-lower"
        )

        agent.execute(event)

        # Verify detector was called with lowercase
        mock_detector.get_best_model_for_capability.assert_called_with("generate_content")

    @patch('src.utils.ollama_detector.get_ollama_detector')
    def test_execute_multiple_fallback_paths(self, mock_get_detector):
        """Test that all fallback paths work when Ollama is unavailable."""
        config = Mock(spec=Config)
        config.ollama_code_model = "code-model"
        config.ollama_content_model = "content-model"
        config.ollama_topic_model = "topic-model"
        event_bus = Mock(spec=EventBus)
        performance_tracker = Mock()

        # Test with Ollama unavailable
        mock_detector = Mock()
        mock_detector.is_ollama_available.return_value = (False, "unavailable")
        mock_get_detector.return_value = mock_detector

        agent = ModelSelectionAgent(config, event_bus, performance_tracker)

        # Test all three fallback paths
        test_cases = [
            ("code", "code-model"),
            ("content", "content-model"),
            ("other", "topic-model")
        ]

        for capability, expected_model in test_cases:
            event = AgentEvent(
                event_type="model_selection_request",
                data={"capability": capability},
                source_agent="TestAgent",
                correlation_id=f"test-{capability}"
            )
            result = agent.execute(event)
            assert result.data["model_name"] == expected_model, f"Failed for {capability}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
