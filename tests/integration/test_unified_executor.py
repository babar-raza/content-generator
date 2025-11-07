"""Integration tests for UnifiedJobExecutor."""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.engine import UnifiedJobExecutor, JobConfig


class TestUnifiedJobExecutor:
    """Integration tests for unified executor."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        config_dir = Path(tempfile.mkdtemp())
        data_dir = Path(tempfile.mkdtemp())
        
        # Create required subdirectories
        (config_dir / "workflows.yaml").write_text("""
version: 1
profiles:
  test:
    order:
      - write_introduction
      - write_sections
""")
        
        yield config_dir, data_dir
        
        # Cleanup
        shutil.rmtree(config_dir)
        shutil.rmtree(data_dir)
    
    def test_executor_initialization(self, temp_dirs):
        """Test executor can be initialized."""
        config_dir, data_dir = temp_dirs

        # Mock the workflow compiler and related components to avoid dependencies
        import unittest.mock as mock
        with mock.patch('orchestration.workflow_compiler.WorkflowCompiler'), \
             mock.patch('orchestration.checkpoint_manager.CheckpointManager'), \
             mock.patch('orchestration.job_execution_engine.JobExecutionEngine'):

            executor = UnifiedJobExecutor(
                config_dir=config_dir,
                data_dir=data_dir
            )

            assert executor is not None
            assert executor.input_resolver is not None
            assert executor.context_merger is not None
            assert executor.completeness_gate is not None
    
    def test_job_config_creation(self):
        """Test job configuration can be created."""
        config = JobConfig(
            workflow="test_workflow",
            input="Python Classes",
            template="blog"
        )
        
        assert config.workflow == "test_workflow"
        assert config.input == "Python Classes"
        assert config.template == "blog"
    
    def test_job_config_with_extra_context(self):
        """Test job configuration with extra context."""
        config = JobConfig(
            workflow="test_workflow",
            input="Python Classes",
            extra_context=[
                {"type": "text", "content": "Custom context", "priority": 10}
            ]
        )
        
        assert len(config.extra_context) == 1
        assert config.extra_context[0]["content"] == "Custom context"
    
    def test_job_config_with_file_input(self):
        """Test job configuration with file input."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Content")
            temp_path = Path(f.name)
        
        try:
            config = JobConfig(
                workflow="test_workflow",
                input=temp_path
            )
            
            assert config.input == temp_path
        finally:
            temp_path.unlink()


class TestJobExecutionFlow:
    """Test complete job execution flow."""

    def test_input_resolution_topic(self):
        """Test topic input is resolved correctly."""
        import unittest.mock as mock
        with mock.patch('orchestration.workflow_compiler.WorkflowCompiler'), \
             mock.patch('orchestration.checkpoint_manager.CheckpointManager'), \
             mock.patch('orchestration.job_execution_engine.JobExecutionEngine'):

            executor = UnifiedJobExecutor()

            context = executor.input_resolver.resolve("Python Classes")

            assert context.primary_content == "Python Classes"
            assert context.metadata["input_mode"] == "topic"

    def test_context_merging(self):
        """Test context merging with multiple sources."""
        import unittest.mock as mock
        with mock.patch('orchestration.workflow_compiler.WorkflowCompiler'), \
             mock.patch('orchestration.checkpoint_manager.CheckpointManager'), \
             mock.patch('orchestration.job_execution_engine.JobExecutionEngine'):

            executor = UnifiedJobExecutor()

            merged = executor.context_merger.merge(
                extra_contexts=[{"type": "text", "content": "Extra", "priority": 10}],
                docs_context="Docs content"
            )

            assert "Extra" in merged
            assert "Docs content" in merged

    def test_completeness_validation(self):
        """Test completeness validation."""
        import unittest.mock as mock
        with mock.patch('orchestration.workflow_compiler.WorkflowCompiler'), \
             mock.patch('orchestration.checkpoint_manager.CheckpointManager'), \
             mock.patch('orchestration.job_execution_engine.JobExecutionEngine'):

            executor = UnifiedJobExecutor()

            # Valid content
            valid_content = """# Introduction
This is a comprehensive article with sufficient content.

## Section 1
More content here with enough words to pass validation.

## Section 2
Even more content to ensure we meet minimum requirements.

## Conclusion
Final thoughts on the topic.
"""

            is_valid, errors = executor.completeness_gate.validate(valid_content)
            assert is_valid, f"Validation failed: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
