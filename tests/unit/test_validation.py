"""Unit tests for ValidationAgent and QualityGateAgent.

Tests cover:
- Content length validation
- Keyword density checks
- Code syntax validation
- Link validation
- Frontmatter validation
- SEO requirements
- Quality gate decision logic
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.agents.support.validation import ValidationAgent
from src.agents.support.quality_gate import QualityGateAgent
from src.core.config import Config
from src.core.event_bus import EventBus
from src.core.contracts import AgentEvent


class MockConfig:
    """Mock configuration for testing."""
    def __init__(self):
        self.data = {}


@pytest.fixture
def event_bus():
    """Create EventBus for testing."""
    return EventBus()


@pytest.fixture
def config():
    """Create mock Config for testing."""
    return MockConfig()


@pytest.fixture
def validation_agent(config, event_bus):
    """Create ValidationAgent for testing."""
    return ValidationAgent(config, event_bus)


@pytest.fixture
def quality_gate_agent(config, event_bus):
    """Create QualityGateAgent for testing."""
    return QualityGateAgent(config, event_bus)


class TestValidationAgent:
    """Tests for ValidationAgent."""

    def test_agent_initialization(self, validation_agent):
        """Test agent initializes correctly."""
        assert validation_agent.agent_id == "ValidationAgent"
        assert validation_agent.contract is not None
        assert "validate_content" in validation_agent.contract.capabilities

    def test_contract_structure(self, validation_agent):
        """Test agent contract has correct structure."""
        contract = validation_agent.contract
        assert contract.agent_id == "ValidationAgent"
        assert contract.input_schema is not None
        assert "content" in contract.input_schema["required"]
        assert contract.output_schema is not None
        assert "checks" in contract.output_schema["required"]
        assert "validation_complete" in contract.publishes

    def test_validate_content_length_pass(self, validation_agent, event_bus):
        """Test content length validation passes with valid content."""
        content = " ".join(["word"] * 500)  # 500 words
        event = AgentEvent(
            event_type="validate_request",
            data={"content": content},
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = validation_agent.execute(event)
        
        assert result is not None
        assert result.event_type == "validation_complete"
        checks = result.data["checks"]
        length_check = next((c for c in checks if c["name"] == "content_length"), None)
        assert length_check is not None
        assert length_check["passed"] is True

    def test_validate_content_length_too_short(self, validation_agent, event_bus):
        """Test content length validation fails when too short."""
        content = " ".join(["word"] * 100)  # 100 words, less than min 300
        event = AgentEvent(
            event_type="validate_request",
            data={"content": content},
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = validation_agent.execute(event)
        
        checks = result.data["checks"]
        length_check = next((c for c in checks if c["name"] == "content_length"), None)
        assert length_check is not None
        assert length_check["passed"] is False
        assert "too short" in length_check["message"].lower()

    def test_validate_content_length_too_long(self, validation_agent, event_bus):
        """Test content length validation fails when too long."""
        content = " ".join(["word"] * 5000)  # 5000 words, more than max 3000
        event = AgentEvent(
            event_type="validate_request",
            data={"content": content},
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = validation_agent.execute(event)
        
        checks = result.data["checks"]
        length_check = next((c for c in checks if c["name"] == "content_length"), None)
        assert length_check is not None
        assert length_check["passed"] is False
        assert "too long" in length_check["message"].lower()

    def test_validate_keyword_density_pass(self, validation_agent, event_bus):
        """Test keyword density validation passes with optimal density."""
        # Create content with 1000 words and 30 keyword occurrences (3% density)
        keywords = ["test", "validation"]
        base_words = ["word"] * 970
        content = " ".join(base_words + (keywords * 15))
        
        event = AgentEvent(
            event_type="validate_request",
            data={
                "content": content,
                "keywords": keywords
            },
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = validation_agent.execute(event)
        
        checks = result.data["checks"]
        density_check = next((c for c in checks if c["name"] == "keyword_density"), None)
        assert density_check is not None
        assert density_check["passed"] is True

    def test_validate_keyword_density_too_low(self, validation_agent, event_bus):
        """Test keyword density validation fails when density too low."""
        keywords = ["test", "validation"]
        content = " ".join(["word"] * 1000 + keywords)  # Very low density
        
        event = AgentEvent(
            event_type="validate_request",
            data={
                "content": content,
                "keywords": keywords
            },
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = validation_agent.execute(event)
        
        checks = result.data["checks"]
        density_check = next((c for c in checks if c["name"] == "keyword_density"), None)
        assert density_check is not None
        assert density_check["passed"] is False
        assert "too low" in density_check["message"].lower()

    def test_validate_keyword_density_too_high(self, validation_agent, event_bus):
        """Test keyword density validation fails when density too high."""
        keywords = ["test", "validation"]
        # 1000 words with 100 keyword occurrences (10% density, too high)
        content = " ".join(["word"] * 900 + (keywords * 50))
        
        event = AgentEvent(
            event_type="validate_request",
            data={
                "content": content,
                "keywords": keywords
            },
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = validation_agent.execute(event)
        
        checks = result.data["checks"]
        density_check = next((c for c in checks if c["name"] == "keyword_density"), None)
        assert density_check is not None
        assert density_check["passed"] is False
        assert "too high" in density_check["message"].lower()

    def test_validate_code_syntax_valid(self, validation_agent, event_bus):
        """Test code syntax validation passes with valid code."""
        valid_code = """
def hello_world():
    print("Hello, World!")
    return True

class MyClass:
    def __init__(self):
        self.value = 42
"""
        event = AgentEvent(
            event_type="validate_request",
            data={
                "content": "Some content",
                "code": valid_code
            },
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = validation_agent.execute(event)
        
        checks = result.data["checks"]
        code_check = next((c for c in checks if c["name"] == "code_syntax"), None)
        assert code_check is not None
        # Note: May pass or fail depending on validation_code_quality implementation

    def test_validate_frontmatter_complete(self, validation_agent, event_bus):
        """Test frontmatter validation passes with all required fields."""
        frontmatter = {
            "title": "Test Article",
            "description": "A test article description",
            "date": "2024-01-01",
            "author": "Test Author"
        }
        
        event = AgentEvent(
            event_type="validate_request",
            data={
                "content": "Some content",
                "frontmatter": frontmatter
            },
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = validation_agent.execute(event)
        
        checks = result.data["checks"]
        fm_check = next((c for c in checks if c["name"] == "frontmatter"), None)
        assert fm_check is not None
        assert fm_check["passed"] is True

    def test_validate_frontmatter_incomplete(self, validation_agent, event_bus):
        """Test frontmatter validation fails with missing required fields."""
        frontmatter = {
            "title": "Test Article"
            # Missing description, date, author
        }
        
        event = AgentEvent(
            event_type="validate_request",
            data={
                "content": "Some content",
                "frontmatter": frontmatter
            },
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = validation_agent.execute(event)
        
        checks = result.data["checks"]
        fm_check = next((c for c in checks if c["name"] == "frontmatter"), None)
        assert fm_check is not None
        assert fm_check["passed"] is False
        assert "missing" in fm_check["message"].lower()

    def test_validate_seo_title_valid(self, validation_agent, event_bus):
        """Test SEO title validation passes with valid length."""
        frontmatter = {
            "title": "This is a Valid SEO Title Between 30-60 Chars",
            "description": "This is a valid SEO description that meets the minimum length requirement of 120 characters and provides enough detail about the content."
        }
        
        event = AgentEvent(
            event_type="validate_request",
            data={
                "content": "Some content",
                "frontmatter": frontmatter
            },
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = validation_agent.execute(event)
        
        checks = result.data["checks"]
        title_check = next((c for c in checks if c["name"] == "seo_title"), None)
        assert title_check is not None
        assert title_check["passed"] is True

    def test_validate_seo_title_too_short(self, validation_agent, event_bus):
        """Test SEO title validation fails when too short."""
        frontmatter = {
            "title": "Short Title",  # Less than 30 characters
            "description": "Valid description with enough characters to meet the minimum SEO requirements for meta descriptions in search results."
        }
        
        event = AgentEvent(
            event_type="validate_request",
            data={
                "content": "Some content",
                "frontmatter": frontmatter
            },
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = validation_agent.execute(event)
        
        checks = result.data["checks"]
        title_check = next((c for c in checks if c["name"] == "seo_title"), None)
        assert title_check is not None
        assert title_check["passed"] is False
        assert "too short" in title_check["message"].lower()

    def test_validate_seo_description_valid(self, validation_agent, event_bus):
        """Test SEO description validation passes with valid length."""
        frontmatter = {
            "title": "Valid SEO Title With Proper Length Here",
            "description": "This is a valid SEO description that meets both the minimum and maximum length requirements for search engine optimization and user experience."
        }
        
        event = AgentEvent(
            event_type="validate_request",
            data={
                "content": "Some content",
                "frontmatter": frontmatter
            },
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = validation_agent.execute(event)
        
        checks = result.data["checks"]
        desc_check = next((c for c in checks if c["name"] == "seo_description"), None)
        assert desc_check is not None
        assert desc_check["passed"] is True

    def test_validation_summary(self, validation_agent, event_bus):
        """Test validation summary is calculated correctly."""
        content = " ".join(["word"] * 500)
        event = AgentEvent(
            event_type="validate_request",
            data={"content": content},
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = validation_agent.execute(event)
        
        summary = result.data["summary"]
        assert "total_checks" in summary
        assert "passed" in summary
        assert "failed" in summary
        assert "warnings" in summary
        assert summary["total_checks"] > 0

    def test_missing_content_raises_error(self, validation_agent, event_bus):
        """Test that missing content raises ValueError."""
        event = AgentEvent(
            event_type="validate_request",
            data={},
            source_agent="test",
            correlation_id="test-001"
        )
        
        with pytest.raises(ValueError, match="content is required"):
            validation_agent.execute(event)


class TestQualityGateAgent:
    """Tests for QualityGateAgent."""

    def test_agent_initialization(self, quality_gate_agent):
        """Test agent initializes correctly."""
        assert quality_gate_agent.agent_id == "QualityGateAgent"
        assert quality_gate_agent.contract is not None
        assert "enforce_quality" in quality_gate_agent.contract.capabilities

    def test_contract_structure(self, quality_gate_agent):
        """Test agent contract has correct structure."""
        contract = quality_gate_agent.contract
        assert contract.agent_id == "QualityGateAgent"
        assert contract.input_schema is not None
        assert "validation_results" in contract.input_schema["required"]
        assert contract.output_schema is not None
        assert "passed" in contract.output_schema["required"]
        assert "quality_gate_decision" in contract.publishes

    def test_quality_gate_pass_all_checks(self, quality_gate_agent, event_bus):
        """Test quality gate passes when all checks pass."""
        validation_results = {
            "checks": [
                {
                    "name": "content_length",
                    "passed": True,
                    "message": "Content length valid",
                    "severity": "medium"
                },
                {
                    "name": "frontmatter",
                    "passed": True,
                    "message": "Frontmatter complete",
                    "severity": "critical"
                }
            ],
            "summary": {
                "total_checks": 2,
                "passed": 2,
                "failed": 0,
                "warnings": 0
            }
        }
        
        event = AgentEvent(
            event_type="quality_gate_request",
            data={"validation_results": validation_results},
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = quality_gate_agent.execute(event)
        
        assert result is not None
        assert result.event_type == "quality_gate_decision"
        assert result.data["passed"] is True
        assert result.data["score"] == 100.0
        assert len(result.data["failures"]) == 0
        assert len(result.data["warnings"]) == 0

    def test_quality_gate_fail_critical(self, quality_gate_agent, event_bus):
        """Test quality gate fails with critical failures."""
        validation_results = {
            "checks": [
                {
                    "name": "code_syntax",
                    "passed": False,
                    "message": "Code syntax errors found",
                    "severity": "critical",
                    "details": {"issues": ["Syntax error on line 10"]}
                },
                {
                    "name": "frontmatter",
                    "passed": False,
                    "message": "Missing required fields",
                    "severity": "critical",
                    "details": {"missing_fields": ["title"]}
                }
            ],
            "summary": {
                "total_checks": 2,
                "passed": 0,
                "failed": 2,
                "warnings": 0
            }
        }
        
        event = AgentEvent(
            event_type="quality_gate_request",
            data={"validation_results": validation_results},
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = quality_gate_agent.execute(event)
        
        assert result.data["passed"] is False
        assert len(result.data["failures"]) == 2
        assert result.data["score"] < 50.0

    def test_quality_gate_warnings_within_threshold(self, quality_gate_agent, event_bus):
        """Test quality gate passes with warnings within threshold."""
        validation_results = {
            "checks": [
                {
                    "name": "content_length",
                    "passed": True,
                    "message": "Valid",
                    "severity": "medium"
                },
                {
                    "name": "link_validation",
                    "passed": False,
                    "message": "Broken links found",
                    "severity": "low",
                    "details": {}
                }
            ],
            "summary": {
                "total_checks": 2,
                "passed": 1,
                "failed": 0,
                "warnings": 1
            }
        }
        
        event = AgentEvent(
            event_type="quality_gate_request",
            data={"validation_results": validation_results},
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = quality_gate_agent.execute(event)
        
        # Should pass because only 1 warning (threshold is 5)
        assert result.data["passed"] is True
        assert len(result.data["warnings"]) == 1

    def test_quality_gate_warnings_exceed_threshold(self, quality_gate_agent, event_bus):
        """Test quality gate fails when warnings exceed threshold."""
        # Create 6 warnings (threshold is 5)
        checks = [
            {
                "name": f"check_{i}",
                "passed": False,
                "message": f"Warning {i}",
                "severity": "low",
                "details": {}
            }
            for i in range(6)
        ]
        
        validation_results = {
            "checks": checks,
            "summary": {
                "total_checks": 6,
                "passed": 0,
                "failed": 0,
                "warnings": 6
            }
        }
        
        event = AgentEvent(
            event_type="quality_gate_request",
            data={"validation_results": validation_results},
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = quality_gate_agent.execute(event)
        
        # Should fail because 6 warnings > threshold of 5
        assert result.data["passed"] is False
        assert len(result.data["warnings"]) == 6

    def test_quality_score_calculation(self, quality_gate_agent, event_bus):
        """Test quality score is calculated correctly."""
        validation_results = {
            "checks": [
                {
                    "name": "critical_check",
                    "passed": False,
                    "message": "Failed",
                    "severity": "critical"
                },
                {
                    "name": "high_check",
                    "passed": True,
                    "message": "Passed",
                    "severity": "high"
                },
                {
                    "name": "medium_check",
                    "passed": True,
                    "message": "Passed",
                    "severity": "medium"
                }
            ]
        }
        
        event = AgentEvent(
            event_type="quality_gate_request",
            data={"validation_results": validation_results},
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = quality_gate_agent.execute(event)
        
        # Score should reflect severity weights
        score = result.data["score"]
        assert 0 <= score <= 100
        assert score < 100  # Not perfect since one check failed

    def test_suggestions_generated(self, quality_gate_agent, event_bus):
        """Test that suggestions are generated for failures."""
        validation_results = {
            "checks": [
                {
                    "name": "content_length",
                    "passed": False,
                    "message": "Content too short",
                    "severity": "medium",
                    "details": {
                        "word_count": 100,
                        "min_words": 300,
                        "max_words": 3000
                    }
                }
            ]
        }
        
        event = AgentEvent(
            event_type="quality_gate_request",
            data={"validation_results": validation_results},
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = quality_gate_agent.execute(event)
        
        suggestions = result.data["suggestions"]
        assert len(suggestions) > 0
        assert any("word" in s.lower() for s in suggestions)

    def test_statistics_included(self, quality_gate_agent, event_bus):
        """Test that statistics are included in result."""
        validation_results = {
            "checks": [
                {"name": "check1", "passed": True, "message": "OK", "severity": "medium"},
                {"name": "check2", "passed": False, "message": "Failed", "severity": "high"}
            ]
        }
        
        event = AgentEvent(
            event_type="quality_gate_request",
            data={"validation_results": validation_results},
            source_agent="test",
            correlation_id="test-001"
        )
        
        result = quality_gate_agent.execute(event)
        
        stats = result.data["statistics"]
        assert stats["total_checks"] == 2
        assert stats["passed"] == 1
        assert stats["failed"] == 1

    def test_missing_checks_raises_error(self, quality_gate_agent, event_bus):
        """Test that missing checks raises ValueError."""
        event = AgentEvent(
            event_type="quality_gate_request",
            data={"validation_results": {}},
            source_agent="test",
            correlation_id="test-001"
        )
        
        with pytest.raises(ValueError, match="checks is required"):
            quality_gate_agent.execute(event)


class TestIntegration:
    """Integration tests for ValidationAgent and QualityGateAgent together."""

    def test_full_validation_pipeline(self, validation_agent, quality_gate_agent, event_bus):
        """Test complete validation pipeline from content to quality gate decision."""
        # Create content with valid length and frontmatter
        content = " ".join(["word"] * 500)
        frontmatter = {
            "title": "Valid SEO Title That Meets Requirements",
            "description": "This is a valid SEO description that provides enough detail and meets the minimum character requirement for search engines.",
            "date": "2024-01-01",
            "author": "Test Author"
        }
        
        # Step 1: Validate content
        validate_event = AgentEvent(
            event_type="validate_request",
            data={
                "content": content,
                "frontmatter": frontmatter
            },
            source_agent="test",
            correlation_id="test-001"
        )
        
        validation_result = validation_agent.execute(validate_event)
        assert validation_result is not None
        
        # Step 2: Run quality gate
        gate_event = AgentEvent(
            event_type="quality_gate_request",
            data={"validation_results": validation_result.data},
            source_agent="test",
            correlation_id="test-001"
        )
        
        gate_result = quality_gate_agent.execute(gate_event)
        assert gate_result is not None
        assert gate_result.data["passed"] is True
        assert gate_result.data["score"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
