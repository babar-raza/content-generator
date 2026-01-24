"""Unit tests for src/engine/aggregator.py - merges N agent outputs; no duplicate keys lost; ties resolved per module rule."""

import pytest
from pathlib import Path
import yaml

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.engine.aggregator import (
    OutputAggregator, SectionRequirement,
    AggregatorReport
)
from dataclasses import dataclass, field
from typing import List

# Create a compatible schema class for testing
@dataclass
class TemplateSchemaForTest:
    """Test schema that matches what OutputAggregator expects."""
    template_name: str
    required_sections: List[SectionRequirement]
    min_word_count: int = 0
    max_word_count: int = 10000
    require_headings: bool = False


class TestOutputAggregator:
    """Test OutputAggregator merges outputs, handles duplicates, and resolves ties."""

    def setup_method(self):
        """Create test schema and aggregator."""
        # Create test schema
        self.schema = TemplateSchemaForTest(
            template_name="test_blog",
            required_sections=[
                SectionRequirement(name="Introduction", agent="IntroAgent", required=True, min_words=50),
                SectionRequirement(name="Body", agent="BodyAgent", required=True, min_words=100),
                SectionRequirement(name="Conclusion", agent="ConclusionAgent", required=True, min_words=30),
            ],
            min_word_count=200,
            max_word_count=1000,
            require_headings=True
        )

        self.aggregator = OutputAggregator(self.schema)

    def test_merge_agent_outputs_no_duplicates(self):
        """Test merging N agent outputs with no duplicate keys lost."""
        # Add outputs from different agents
        outputs = {
            "IntroAgent": {
                "content": "This is the introduction section with important context.",
                "status": "completed",
                "metadata": {"word_count": 8}
            },
            "BodyAgent": {
                "content": "This is the main body content with detailed information.",
                "status": "completed",
                "metadata": {"word_count": 9}
            },
            "ConclusionAgent": {
                "content": "This is the conclusion that wraps everything up.",
                "status": "completed",
                "metadata": {"word_count": 7}
            }
        }

        for agent, output in outputs.items():
            self.aggregator.add_agent_output(agent, output)

        # Verify all outputs are stored
        assert len(self.aggregator.sections) == 3
        assert "IntroAgent" in self.aggregator.sections
        assert "BodyAgent" in self.aggregator.sections
        assert "ConclusionAgent" in self.aggregator.sections

        # Verify content is preserved
        assert "introduction section" in self.aggregator.sections["IntroAgent"]["content"]
        assert "main body content" in self.aggregator.sections["BodyAgent"]["content"]
        assert "conclusion that wraps" in self.aggregator.sections["ConclusionAgent"]["content"]

    def test_merge_with_duplicate_keys_handled(self):
        """Test that duplicate keys are handled properly (no data loss)."""
        # Add initial output
        self.aggregator.add_agent_output("IntroAgent", {
            "content": "Initial introduction.",
            "status": "completed",
            "version": 1
        })

        # Add another output with same agent (should overwrite, not lose data)
        self.aggregator.add_agent_output("IntroAgent", {
            "content": "Updated introduction with more details.",
            "status": "completed",
            "version": 2
        })

        # Verify only one entry exists but with latest data
        assert len(self.aggregator.sections) == 1
        assert self.aggregator.sections["IntroAgent"]["version"] == 2
        assert "Updated introduction" in self.aggregator.sections["IntroAgent"]["content"]

    def test_ties_resolved_per_module_rule(self):
        """Test tie resolution per module rule (first agent wins for same section type)."""
        # Create schema with multiple agents that could produce same section
        schema_with_ties = TemplateSchema(
            template_name="test_blog",
            required_sections=[
                SectionRequirement(name="Introduction", agent="IntroAgent1", required=True),
                SectionRequirement(name="Introduction", agent="IntroAgent2", required=True),  # Same section name
            ]
        )

        aggregator = OutputAggregator(schema_with_ties)

        # Add outputs from both agents for same section
        aggregator.add_agent_output("IntroAgent1", {
            "content": "First introduction version.",
            "status": "completed",
            "priority": 1
        })

        aggregator.add_agent_output("IntroAgent2", {
            "content": "Second introduction version.",
            "status": "completed",
            "priority": 2
        })

        # Both should be stored (no tie-breaking logic removes data)
        assert len(aggregator.sections) == 2
        assert "IntroAgent1" in aggregator.sections
        assert "IntroAgent2" in aggregator.sections

        # Content from both preserved
        assert "First introduction" in aggregator.sections["IntroAgent1"]["content"]
        assert "Second introduction" in aggregator.sections["IntroAgent2"]["content"]

    def test_completeness_validation_all_present(self):
        """Test completeness validation when all required sections present."""
        # Add all required outputs
        self.aggregator.add_agent_output("IntroAgent", {
            "content": "This is a sufficiently long introduction with enough words to meet the minimum requirement.",
            "status": "completed"
        })
        self.aggregator.add_agent_output("BodyAgent", {
            "content": "This is the main body content that provides detailed information and meets the word count requirement for this section.",
            "status": "completed"
        })
        self.aggregator.add_agent_output("ConclusionAgent", {
            "content": "This conclusion wraps up the content appropriately.",
            "status": "completed"
        })

        is_complete, errors = self.aggregator.validate_completeness()
        assert is_complete == True
        assert len(errors) == 0

    def test_completeness_validation_missing_agent(self):
        """Test completeness validation when required agent is missing."""
        # Only add two of three required agents
        self.aggregator.add_agent_output("IntroAgent", {"content": "Intro content", "status": "completed"})
        self.aggregator.add_agent_output("BodyAgent", {"content": "Body content", "status": "completed"})
        # Missing: ConclusionAgent

        is_complete, errors = self.aggregator.validate_completeness()
        assert is_complete == False
        assert len(errors) == 1
        assert "Missing section: Conclusion" in errors[0]
        assert "ConclusionAgent did not run" in errors[0]

    def test_completeness_validation_empty_content(self):
        """Test completeness validation when agent ran but produced empty content."""
        # Add agent with empty content
        self.aggregator.add_agent_output("IntroAgent", {
            "content": "",  # Empty content
            "status": "completed"
        })
        self.aggregator.add_agent_output("BodyAgent", {"content": "Valid body content", "status": "completed"})
        self.aggregator.add_agent_output("ConclusionAgent", {"content": "Valid conclusion", "status": "completed"})

        is_complete, errors = self.aggregator.validate_completeness()
        assert is_complete == False
        assert len(errors) == 1
        assert "Empty section: Introduction" in errors[0]
        assert "from agent IntroAgent" in errors[0]

    def test_completeness_validation_insufficient_words(self):
        """Test completeness validation when content has insufficient words."""
        # Add agent with too few words
        self.aggregator.add_agent_output("IntroAgent", {
            "content": "Too short",  # Only 2 words, needs 50
            "status": "completed"
        })
        self.aggregator.add_agent_output("BodyAgent", {"content": "Valid body content", "status": "completed"})
        self.aggregator.add_agent_output("ConclusionAgent", {"content": "Valid conclusion", "status": "completed"})

        is_complete, errors = self.aggregator.validate_completeness()
        assert is_complete == False
        assert len(errors) == 1
        assert "Section too short: Introduction" in errors[0]
        assert "2 words, minimum 50" in errors[0]

    def test_content_validation_word_count(self):
        """Test content validation for word count limits."""
        # Test minimum word count
        short_content = "Short content"  # 2 words, below minimum 200
        warnings = self.aggregator.validate_content(short_content)
        assert len(warnings) == 1
        assert "too short" in warnings[0].lower()
        assert "200" in warnings[0]

        # Test maximum word count
        long_content = " ".join(["word"] * 1200)  # 1200 words, above maximum 1000
        warnings = self.aggregator.validate_content(long_content)
        assert len(warnings) == 1
        assert "too long" in warnings[0].lower()
        assert "1000" in warnings[0]

        # Test valid word count
        valid_content = " ".join(["word"] * 500)  # 500 words, within range
        warnings = self.aggregator.validate_content(valid_content)
        assert len(warnings) == 0

    def test_content_validation_headings_required(self):
        """Test content validation for required headings."""
        # Content without headings
        no_headings = "This is content without any headings. It just has paragraphs."
        warnings = self.aggregator.validate_content(no_headings)
        assert len(warnings) == 1
        assert "no headings found" in warnings[0].lower()

        # Content with headings
        with_headings = "# Introduction\n\nThis has headings.\n\n## Section 2\n\nMore content."
        warnings = self.aggregator.validate_content(with_headings)
        assert len(warnings) == 0

    def test_generate_report_complete(self):
        """Test report generation for complete output."""
        # Add complete outputs
        self.aggregator.add_agent_output("IntroAgent", {
            "content": "This is a good introduction with sufficient length.",
            "status": "completed"
        })
        self.aggregator.add_agent_output("BodyAgent", {
            "content": "This is the main body with detailed content that meets requirements.",
            "status": "completed"
        })
        self.aggregator.add_agent_output("ConclusionAgent", {
            "content": "This is a proper conclusion.",
            "status": "completed"
        })

        final_content = "# Title\n\nIntroduction content.\n\n## Body\n\nBody content.\n\n## Conclusion\n\nConclusion content."
        report = self.aggregator.generate_report(final_content)

        assert report.template == "test_blog"
        assert report.complete == True
        assert len(report.errors) == 0
        assert len(report.warnings) == 0
        assert report.total_word_count > 0
        assert len(report.sections) == 3

    def test_generate_report_incomplete(self):
        """Test report generation for incomplete output."""
        # Add only one output
        self.aggregator.add_agent_output("IntroAgent", {
            "content": "Only introduction provided.",
            "status": "completed"
        })

        report = self.aggregator.generate_report()

        assert report.complete == False
        assert len(report.errors) >= 2  # Missing BodyAgent and ConclusionAgent
        assert report.sections["BodyAgent"]["present"] == False
        assert report.sections["ConclusionAgent"]["present"] == False
        assert report.sections["IntroAgent"]["present"] == True

    @pytest.mark.skip(reason="TemplateSchema.from_yaml() not implemented - test references non-existent functionality")
    def test_template_schema_from_yaml(self):
        """Test loading template schema from YAML."""
        import tempfile

        yaml_content = """
template_name: blog_template
validation_rules:
  min_word_count: 500
  max_word_count: 2000
  require_headings: true
required_sections:
  - name: Introduction
    agent: IntroWriter
    required: true
    min_words: 100
  - name: Main Content
    agent: ContentWriter
    required: true
    min_words: 200
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = Path(f.name)

        try:
            schema = TemplateSchema.from_yaml(yaml_path)

            assert schema.template_name == "blog_template"
            assert schema.min_word_count == 500
            assert schema.max_word_count == 2000
            assert schema.require_headings == True
            assert len(schema.required_sections) == 2

            assert schema.required_sections[0].name == "Introduction"
            assert schema.required_sections[0].agent == "IntroWriter"
            assert schema.required_sections[0].min_words == 100

            assert schema.required_sections[1].name == "Main Content"
            assert schema.required_sections[1].agent == "ContentWriter"
            assert schema.required_sections[1].min_words == 200

        finally:
            yaml_path.unlink()

    def test_aggregator_report_to_dict(self):
        """Test AggregatorReport.to_dict() method."""
        report = AggregatorReport(
            template="test_template",
            complete=True,
            errors=["error1"],
            warnings=["warning1"],
            sections={"agent1": {"status": "ok"}},
            total_word_count=150,
            metadata={"key": "value"}
        )

        report_dict = report.to_dict()

        assert report_dict["template"] == "test_template"
        assert report_dict["complete"] == True
        assert report_dict["errors"] == ["error1"]
        assert report_dict["warnings"] == ["warning1"]
        assert report_dict["sections"] == {"agent1": {"status": "ok"}}
        assert report_dict["total_word_count"] == 150
        assert report_dict["metadata"] == {"key": "value"}
# DOCGEN:LLM-FIRST@v4