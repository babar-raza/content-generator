"""Unit tests for engine components."""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.engine import (
    InputResolver, ContextSet,
    OutputAggregator, TemplateSchema, SectionRequirement,
    CompletenessGate, ContextMerger,
    AgentExecutionTracker, AgentRun
)
from src.engine.exceptions import *


class TestInputResolver:
    """Tests for InputResolver."""
    
    def test_topic_mode(self):
        """Test topic string input."""
        resolver = InputResolver()
        context = resolver.resolve("Python Classes")
        
        assert context.primary_content == "Python Classes"
        assert context.metadata["input_mode"] == "topic"
        assert "user_topic" in context.sources
    
    def test_file_mode(self):
        """Test single file input."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Content\n\nThis is a test.")
            temp_path = Path(f.name)
        
        try:
            resolver = InputResolver()
            context = resolver.resolve(temp_path)
            
            assert "Test Content" in context.primary_content
            assert context.metadata["input_mode"] == "file"
            assert str(temp_path) in context.sources
        finally:
            temp_path.unlink()
    
    def test_folder_mode(self):
        """Test folder input."""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            (temp_dir / "file1.md").write_text("# File 1\n\nContent 1")
            (temp_dir / "file2.md").write_text("# File 2\n\nContent 2")
            
            resolver = InputResolver()
            context = resolver.resolve(temp_dir)
            
            assert "File 1" in context.primary_content
            assert "File 2" in context.primary_content
            assert context.metadata["input_mode"] == "folder"
            assert context.metadata["file_count"] == 2
        finally:
            shutil.rmtree(temp_dir)
    
    def test_list_mode(self):
        """Test list of files input."""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            file1 = temp_dir / "file1.md"
            file2 = temp_dir / "file2.md"
            file1.write_text("# File 1")
            file2.write_text("# File 2")
            
            resolver = InputResolver()
            context = resolver.resolve([file1, file2])
            
            assert "File 1" in context.primary_content
            assert "File 2" in context.primary_content
            assert context.metadata["input_mode"] == "list"
            assert context.metadata["file_count"] == 2
        finally:
            shutil.rmtree(temp_dir)


class TestCompletenessGate:
    """Tests for CompletenessGate."""
    
    def test_empty_content_fails(self):
        """Test empty content fails validation."""
        gate = CompletenessGate()
        is_valid, errors = gate.validate("")
        
        assert not is_valid
        assert len(errors) > 0
    
    def test_short_content_fails(self):
        """Test short content fails validation."""
        gate = CompletenessGate()
        is_valid, errors = gate.validate("Short content")
        
        assert not is_valid
        assert any("too short" in e for e in errors)
    
    def test_placeholder_content_fails(self):
        """Test placeholder text fails validation."""
        gate = CompletenessGate()
        content = "# Article\n\nTODO: Write content here"
        is_valid, errors = gate.validate(content)
        
        assert not is_valid
        assert any("placeholder" in e.lower() for e in errors)
    
    def test_valid_content_passes(self):
        """Test valid content passes validation."""
        gate = CompletenessGate()
        content = """# Introduction

This is a comprehensive article about Python classes with sufficient content to meet all validation requirements. The article provides detailed information about object-oriented programming concepts in Python.

## What are Classes?

Classes are blueprints for creating objects in Python. They encapsulate data and behavior into reusable components that can be instantiated multiple times.

## How to Define Classes

You define classes using the class keyword followed by the class name. Class definitions typically include methods and attributes that define the behavior and state of objects created from the class.

## Class Methods and Attributes

Classes can have both instance methods and class methods. Instance methods operate on individual object instances, while class methods operate on the class itself.

## Inheritance and Polymorphism

Python supports inheritance, allowing classes to inherit properties and methods from parent classes. This enables code reuse and the creation of hierarchical class structures.

## Conclusion

Classes are fundamental to object-oriented programming in Python. Understanding classes is essential for writing maintainable and scalable Python code.
"""
        is_valid, errors = gate.validate(content)

        assert is_valid
        assert len(errors) == 0


class TestOutputAggregator:
    """Tests for OutputAggregator."""
    
    def test_missing_required_section_fails(self):
        """Test missing required section fails validation."""
        schema = TemplateSchema(
            template_name="test",
            required_sections=[
                SectionRequirement(name="intro", agent="write_introduction", required=True),
                SectionRequirement(name="body", agent="write_sections", required=True)
            ]
        )
        
        aggregator = OutputAggregator(schema)
        aggregator.add_agent_output("write_introduction", {"content": "Intro content"})
        # Missing write_sections
        
        is_complete, errors = aggregator.validate_completeness()
        
        assert not is_complete
        assert any("write_sections" in e for e in errors)
    
    def test_all_sections_present_passes(self):
        """Test all required sections present passes validation."""
        schema = TemplateSchema(
            template_name="test",
            required_sections=[
                SectionRequirement(name="intro", agent="write_introduction", required=True),
                SectionRequirement(name="body", agent="write_sections", required=True)
            ]
        )
        
        aggregator = OutputAggregator(schema)
        aggregator.add_agent_output("write_introduction", {"content": "Intro content"})
        aggregator.add_agent_output("write_sections", {"content": "Body content"})
        
        is_complete, errors = aggregator.validate_completeness()
        
        assert is_complete
        assert len(errors) == 0


class TestContextMerger:
    """Tests for ContextMerger."""
    
    def test_context_precedence(self):
        """Test context merging follows precedence."""
        merger = ContextMerger()
        
        result = merger.merge(
            extra_contexts=[{"type": "text", "content": "Extra context", "priority": 10}],
            api_context="API reference",
            blog_context="Blog posts",
            docs_context="Documentation"
        )
        
        # Extra should come first
        assert result.index("Extra context") < result.index("Documentation")
        assert result.index("Documentation") < result.index("Blog posts")
        assert result.index("Blog posts") < result.index("API reference")
    
    def test_empty_contexts(self):
        """Test merger handles empty contexts."""
        merger = ContextMerger()
        
        result = merger.merge()
        
        assert result == ""


class TestAgentExecutionTracker:
    """Tests for AgentExecutionTracker."""
    
    def test_record_agent_execution(self):
        """Test recording agent execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = AgentExecutionTracker("test_job", Path(temp_dir))
            
            run = tracker.record_start("test_agent", {"input": "test"})
            assert run.agent_name == "test_agent"
            assert run.status == "running"
            
            tracker.record_complete(run, {"output": "result"})
            assert run.status == "completed"
            assert run.duration_ms > 0
    
    def test_agent_runs_persisted(self):
        """Test agent runs are persisted to disk."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = AgentExecutionTracker("test_job", Path(temp_dir))
            
            run = tracker.record_start("test_agent", {"input": "test"})
            tracker.record_complete(run, {"output": "result"})
            
            # Check file exists
            agent_runs_file = Path(temp_dir) / "agent_runs.json"
            assert agent_runs_file.exists()
            
            # Load and verify
            tracker2 = AgentExecutionTracker("test_job", Path(temp_dir))
            tracker2.load()
            
            assert len(tracker2.runs) == 1
            assert tracker2.runs[0].agent_name == "test_agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
