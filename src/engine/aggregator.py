"""Output aggregator and completeness validator."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
import yaml

from .exceptions import IncompleteOutputError

logger = logging.getLogger(__name__)


@dataclass
class SectionRequirement:
    """Required section definition."""
    name: str
    agent: str
    required: bool = True
    min_count: Optional[int] = None
    min_words: Optional[int] = None


@dataclass
class TemplateSchema:
    """Template requirements schema."""
    template_name: str
    required_sections: List[SectionRequirement]
    min_word_count: int = 800
    max_word_count: int = 5000
    require_headings: bool = True
    
    @classmethod
    def from_yaml(cls, path: Path) -> 'TemplateSchema':
        """Load template schema from YAML."""
        with open(path) as f:
            data = yaml.safe_load(f)
        
        sections = [
            SectionRequirement(**s) for s in data.get('required_sections', [])
        ]
        
        validation = data.get('validation_rules', {})
        
        return cls(
            template_name=data['template_name'],
            required_sections=sections,
            min_word_count=validation.get('min_word_count', 800),
            max_word_count=validation.get('max_word_count', 5000),
            require_headings=validation.get('require_headings', True)
        )


@dataclass
class AggregatorReport:
    """Aggregation and validation report."""
    template: str
    complete: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sections: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    total_word_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "template": self.template,
            "complete": self.complete,
            "errors": self.errors,
            "warnings": self.warnings,
            "sections": self.sections,
            "total_word_count": self.total_word_count,
            "metadata": self.metadata
        }


class OutputAggregator:
    """Collects and validates all agent outputs."""
    
    def __init__(self, schema: TemplateSchema):
        self.schema = schema
        self.sections: Dict[str, Dict[str, Any]] = {}
        logger.info(f"OutputAggregator initialized for template: {schema.template_name}")
    
    def add_agent_output(self, agent_name: str, output: Dict[str, Any]):
        """Register output from an agent."""
        self.sections[agent_name] = output
        logger.debug(f"Added output from agent: {agent_name}")
    
    def validate_completeness(self) -> tuple[bool, List[str]]:
        """Check if all required sections are present."""
        errors = []
        
        for section in self.schema.required_sections:
            if not section.required:
                continue
            
            agent = section.agent
            
            # Check if agent ran
            if agent not in self.sections:
                errors.append(f"Missing section: {section.name} (agent {agent} did not run)")
                continue
            
            output = self.sections[agent]
            
            # Check if output has content
            content = output.get('content', '')
            if not content or len(content.strip()) < 10:
                errors.append(f"Empty section: {section.name} (from agent {agent})")
                continue
            
            # Check word count if specified
            if section.min_words:
                word_count = len(content.split())
                if word_count < section.min_words:
                    errors.append(
                        f"Section too short: {section.name} "
                        f"({word_count} words, minimum {section.min_words})"
                    )
        
        return len(errors) == 0, errors
    
    def validate_content(self, final_content: str) -> List[str]:
        """Validate final content against template rules."""
        warnings = []
        
        # Word count
        word_count = len(final_content.split())
        if word_count < self.schema.min_word_count:
            warnings.append(
                f"Content too short: {word_count} words "
                f"(minimum {self.schema.min_word_count})"
            )
        elif word_count > self.schema.max_word_count:
            warnings.append(
                f"Content too long: {word_count} words "
                f"(maximum {self.schema.max_word_count})"
            )
        
        # Headings
        if self.schema.require_headings:
            import re
            if not re.search(r'^#+\s', final_content, re.MULTILINE):
                warnings.append("No headings found in content")
        
        return warnings
    
    def generate_report(self, final_content: str = "") -> AggregatorReport:
        """Generate comprehensive execution report."""
        is_complete, errors = self.validate_completeness()
        warnings = self.validate_content(final_content) if final_content else []
        
        # Calculate section stats
        section_stats = {}
        total_words = 0
        
        for req_section in self.schema.required_sections:
            agent = req_section.agent
            
            if agent in self.sections:
                output = self.sections[agent]
                content = output.get('content', '')
                word_count = len(content.split())
                total_words += word_count
                
                section_stats[agent] = {
                    "present": True,
                    "word_count": word_count,
                    "status": output.get('status', 'unknown'),
                    "section_name": req_section.name
                }
            else:
                section_stats[agent] = {
                    "present": False,
                    "word_count": 0,
                    "status": "missing",
                    "section_name": req_section.name
                }
        
        return AggregatorReport(
            template=self.schema.template_name,
            complete=is_complete and len(warnings) == 0,
            errors=errors,
            warnings=warnings,
            sections=section_stats,
            total_word_count=total_words,
            metadata={
                "sections_present": sum(1 for s in section_stats.values() if s["present"]),
                "sections_required": len([s for s in self.schema.required_sections if s.required]),
                "sections_total": len(self.schema.required_sections)
            }
        )
    
    def fail_if_incomplete(self, final_content: str = ""):
        """Raise exception if output is incomplete."""
        report = self.generate_report(final_content)
        
        if not report.complete:
            error_msg = f"Output validation failed:\n"
            error_msg += "\n".join(f"  - {e}" for e in report.errors)
            if report.warnings:
                error_msg += "\n\nWarnings:\n"
                error_msg += "\n".join(f"  - {w}" for w in report.warnings)
            
            raise IncompleteOutputError(error_msg)
