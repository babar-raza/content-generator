"""
Unit tests for QualityGateAgent.

Tests the quality gate agent's ability to:
- Aggregate validation results
- Apply severity-based scoring
- Determine pass/fail status
- Generate actionable suggestions
- Load and apply configuration
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.event_bus import EventBus, AgentEvent
from src.core.config import Config
from src.agents.support.quality_gate import QualityGateAgent


class TestQualityGateAgentInitialization:
    """Tests for QualityGateAgent initialization."""

    @patch('builtins.open', new_callable=mock_open, read_data='quality_gate:\n  thresholds:\n    critical_failures: 0\n    warnings: 5')
    @patch('pathlib.Path.exists', return_value=True)
    def test_initialization(self, mock_exists, mock_file):
        """Test agent initializes correctly."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        agent = QualityGateAgent(config, event_bus)

        assert agent.agent_id == "QualityGateAgent"
        assert agent.config == config
        assert agent.event_bus == event_bus
        assert agent.quality_config is not None

    @patch('pathlib.Path.exists', return_value=False)
    def test_initialization_with_default_config(self, mock_exists):
        """Test agent initializes with default config when file not found."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        agent = QualityGateAgent(config, event_bus)

        # Should use default config
        assert agent.quality_config is not None
        assert 'quality_gate' in agent.quality_config
        assert agent.quality_config['quality_gate']['thresholds']['critical_failures'] == 0

    def test_contract_creation(self):
        """Test agent contract is created correctly."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)
            contract = agent._create_contract()

        assert contract.agent_id == "QualityGateAgent"
        assert "enforce_quality" in contract.capabilities
        assert contract.input_schema["required"] == ["validation_results"]
        assert "quality_gate_decision" in contract.publishes

    def test_event_subscription(self):
        """Test agent subscribes to quality gate events."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        # Verify subscriptions were called
        assert event_bus.subscribe.call_count == 2
        event_bus.subscribe.assert_any_call("quality_gate_request", agent.execute)
        event_bus.subscribe.assert_any_call("validation_complete", agent.execute)


class TestQualityGateExecution:
    """Tests for QualityGateAgent execute method."""

    def test_execute_all_checks_pass(self):
        """Test execute when all validation checks pass."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        event = AgentEvent(
            event_type="quality_gate_request",
            data={
                "validation_results": {
                    "checks": [
                        {"name": "check1", "passed": True, "severity": "high", "message": "OK"},
                        {"name": "check2", "passed": True, "severity": "medium", "message": "OK"}
                    ]
                }
            },
            source_agent="ValidationAgent",
            correlation_id="test-pass"
        )

        result = agent.execute(event)

        assert result is not None
        assert result.event_type == "quality_gate_decision"
        assert result.data["passed"] is True
        assert result.data["score"] == 100.0
        assert len(result.data["passed_checks"]) == 2
        assert len(result.data["failures"]) == 0
        assert len(result.data["warnings"]) == 0

    def test_execute_with_failures(self):
        """Test execute when critical checks fail."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        event = AgentEvent(
            event_type="quality_gate_request",
            data={
                "validation_results": {
                    "checks": [
                        {"name": "check1", "passed": False, "severity": "critical", "message": "Failed"},
                        {"name": "check2", "passed": True, "severity": "medium", "message": "OK"}
                    ]
                }
            },
            source_agent="ValidationAgent",
            correlation_id="test-fail"
        )

        result = agent.execute(event)

        assert result.data["passed"] is False
        assert len(result.data["failures"]) == 1
        assert result.data["failures"][0]["severity"] == "critical"
        assert result.data["score"] < 100.0

    def test_execute_with_warnings(self):
        """Test execute with low-severity warnings."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        event = AgentEvent(
            event_type="quality_gate_request",
            data={
                "validation_results": {
                    "checks": [
                        {"name": "check1", "passed": True, "severity": "high", "message": "OK"},
                        {"name": "check2", "passed": False, "severity": "low", "message": "Warning"}
                    ]
                }
            },
            source_agent="ValidationAgent",
            correlation_id="test-warn"
        )

        result = agent.execute(event)

        assert len(result.data["warnings"]) == 1
        assert result.data["warnings"][0]["severity"] == "low"
        assert result.data["passed"] is True  # Low severity shouldn't fail gate

    def test_execute_exceeds_warning_threshold(self):
        """Test execute fails when warning count exceeds threshold."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        # Create 6 warnings (default threshold is 5)
        checks = [
            {"name": f"check{i}", "passed": False, "severity": "low", "message": f"Warning {i}"}
            for i in range(6)
        ]

        event = AgentEvent(
            event_type="quality_gate_request",
            data={"validation_results": {"checks": checks}},
            source_agent="ValidationAgent",
            correlation_id="test-threshold"
        )

        result = agent.execute(event)

        assert result.data["passed"] is False
        assert len(result.data["warnings"]) == 6


class TestQualityGateValidation:
    """Tests for QualityGateAgent input validation."""

    def test_execute_missing_checks(self):
        """Test execute raises ValueError when checks are missing."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        event = AgentEvent(
            event_type="quality_gate_request",
            data={"validation_results": {}},
            source_agent="ValidationAgent",
            correlation_id="test-missing"
        )

        with pytest.raises(ValueError) as exc_info:
            agent.execute(event)

        assert "checks is required" in str(exc_info.value)

    def test_execute_empty_checks(self):
        """Test execute raises ValueError when checks list is empty."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        event = AgentEvent(
            event_type="quality_gate_request",
            data={"validation_results": {"checks": []}},
            source_agent="ValidationAgent",
            correlation_id="test-empty"
        )

        with pytest.raises(ValueError) as exc_info:
            agent.execute(event)

        assert "checks is required" in str(exc_info.value)

    def test_execute_alternate_data_structure(self):
        """Test execute handles validation results at root level."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        # Data without validation_results wrapper
        event = AgentEvent(
            event_type="validation_complete",
            data={
                "checks": [
                    {"name": "check1", "passed": True, "severity": "high", "message": "OK"}
                ]
            },
            source_agent="ValidationAgent",
            correlation_id="test-alt"
        )

        result = agent.execute(event)

        assert result is not None
        assert result.data["passed"] is True


class TestQualityScoreCalculation:
    """Tests for quality score calculation."""

    def test_calculate_quality_score_all_pass(self):
        """Test quality score is 100 when all checks pass."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        checks = [
            {"name": "check1", "passed": True, "severity": "critical"},
            {"name": "check2", "passed": True, "severity": "high"},
            {"name": "check3", "passed": True, "severity": "medium"},
        ]

        score = agent._calculate_quality_score(checks)
        assert score == 100.0

    def test_calculate_quality_score_weighted(self):
        """Test quality score uses severity weights correctly."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        # One critical pass (1.0), one critical fail (0.0)
        checks = [
            {"name": "check1", "passed": True, "severity": "critical"},
            {"name": "check2", "passed": False, "severity": "critical"}
        ]

        score = agent._calculate_quality_score(checks)
        assert score == 50.0

    def test_calculate_quality_score_empty_checks(self):
        """Test quality score returns 0 for empty checks."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        score = agent._calculate_quality_score([])
        assert score == 0.0


class TestSuggestionGeneration:
    """Tests for suggestion generation."""

    def test_generate_suggestions_with_failures(self):
        """Test suggestions are generated for failures."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        failures = [
            {"name": "code_syntax", "severity": "critical", "message": "Syntax error", "details": {}}
        ]
        warnings = []

        suggestions = agent._generate_suggestions(failures, warnings)

        assert len(suggestions) > 0
        assert any("critical" in s.lower() for s in suggestions)

    def test_generate_suggestions_with_warnings(self):
        """Test suggestions include warning recommendations."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        failures = []
        warnings = [
            {"name": "link_validation", "severity": "low", "message": "Broken link", "details": {}}
        ]

        suggestions = agent._generate_suggestions(failures, warnings)

        assert len(suggestions) > 0
        assert any("warning" in s.lower() for s in suggestions)

    def test_suggest_content_length_too_short(self):
        """Test content length suggestion for short content."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        details = {"word_count": 100, "min_words": 300, "max_words": 1000}
        suggestion = agent._suggest_content_length(details)

        assert "200" in suggestion  # Should suggest adding 200 words
        assert "Add" in suggestion

    def test_suggest_content_length_too_long(self):
        """Test content length suggestion for long content."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        details = {"word_count": 1200, "min_words": 300, "max_words": 1000}
        suggestion = agent._suggest_content_length(details)

        assert "200" in suggestion  # Should suggest removing 200 words
        assert "Reduce" in suggestion

    def test_suggest_keyword_density_low(self):
        """Test keyword density suggestion for low density."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        details = {"density": 0.005}
        suggestion = agent._suggest_keyword_density(details)

        assert "Increase" in suggestion

    def test_suggest_keyword_density_high(self):
        """Test keyword density suggestion for high density."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        details = {"density": 0.08}
        suggestion = agent._suggest_keyword_density(details)

        assert "Reduce" in suggestion or "keyword stuffing" in suggestion.lower()

    def test_suggest_frontmatter_missing_fields(self):
        """Test frontmatter suggestion with missing fields."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        details = {"missing_fields": ["title", "date", "author"]}
        suggestion = agent._suggest_frontmatter(details)

        assert "title" in suggestion
        assert "date" in suggestion
        assert "author" in suggestion

    def test_suggest_seo_title_too_short(self):
        """Test SEO title suggestion for short title."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        details = {"length": 20, "min_length": 30, "max_length": 60}
        suggestion = agent._suggest_seo_title(details)

        assert "Lengthen" in suggestion
        assert "30" in suggestion

    def test_suggest_seo_description_too_long(self):
        """Test SEO description suggestion for long description."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        details = {"length": 180, "min_length": 120, "max_length": 160}
        suggestion = agent._suggest_seo_description(details)

        assert "Shorten" in suggestion
        assert "160" in suggestion


class TestQualityGateEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_execute_preserves_correlation_id(self):
        """Test that correlation_id is preserved in response."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        correlation_id = "unique-correlation-99999"
        event = AgentEvent(
            event_type="quality_gate_request",
            data={
                "validation_results": {
                    "checks": [
                        {"name": "check1", "passed": True, "severity": "high", "message": "OK"}
                    ]
                }
            },
            source_agent="ValidationAgent",
            correlation_id=correlation_id
        )

        result = agent.execute(event)
        assert result.correlation_id == correlation_id

    def test_execute_includes_statistics(self):
        """Test that response includes statistics."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        event = AgentEvent(
            event_type="quality_gate_request",
            data={
                "validation_results": {
                    "checks": [
                        {"name": "check1", "passed": True, "severity": "high", "message": "OK"},
                        {"name": "check2", "passed": False, "severity": "critical", "message": "Fail"}
                    ]
                }
            },
            source_agent="ValidationAgent",
            correlation_id="test-stats"
        )

        result = agent.execute(event)

        assert "statistics" in result.data
        assert result.data["statistics"]["total_checks"] == 2
        assert result.data["statistics"]["passed"] == 1
        assert result.data["statistics"]["failed"] == 1

    def test_execute_handles_missing_severity(self):
        """Test execute handles checks with missing severity field."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        event = AgentEvent(
            event_type="quality_gate_request",
            data={
                "validation_results": {
                    "checks": [
                        {"name": "check1", "passed": True, "message": "OK"}  # No severity
                    ]
                }
            },
            source_agent="ValidationAgent",
            correlation_id="test-missing-sev"
        )

        result = agent.execute(event)
        # Should default to medium and still work
        assert result is not None
        assert result.data["passed"] is True

    def test_execute_mixed_severities(self):
        """Test execute correctly categorizes mixed severity failures."""
        config = Mock(spec=Config)
        event_bus = Mock(spec=EventBus)

        with patch('pathlib.Path.exists', return_value=False):
            agent = QualityGateAgent(config, event_bus)

        event = AgentEvent(
            event_type="quality_gate_request",
            data={
                "validation_results": {
                    "checks": [
                        {"name": "check1", "passed": False, "severity": "critical", "message": "Critical"},
                        {"name": "check2", "passed": False, "severity": "high", "message": "High"},
                        {"name": "check3", "passed": False, "severity": "medium", "message": "Medium"},
                        {"name": "check4", "passed": False, "severity": "low", "message": "Low"}
                    ]
                }
            },
            source_agent="ValidationAgent",
            correlation_id="test-mixed"
        )

        result = agent.execute(event)

        # Critical and high should be failures
        assert len(result.data["failures"]) == 2
        # Medium and low should be warnings
        assert len(result.data["warnings"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
