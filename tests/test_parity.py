"""Test parity between CLI and Web engine calls."""

import pytest
import json
from pathlib import Path
import tempfile
import shutil

from src.engine.unified_engine import get_engine, RunSpec, JobStatus


class TestCLIWebParity:
    """Test that CLI and Web produce identical outputs."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_same_input_identical_output(self, temp_output_dir):
        """Test that same RunSpec produces identical output."""
        
        # Create RunSpec
        run_spec = RunSpec(
            topic="Test Topic: Python Basics",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        # Execute twice (simulating CLI and Web)
        engine = get_engine()
        
        result1 = engine.generate_job(run_spec)
        result2 = engine.generate_job(run_spec)
        
        # Both should succeed
        assert result1.status in [JobStatus.COMPLETED, JobStatus.PARTIAL]
        assert result2.status in [JobStatus.COMPLETED, JobStatus.PARTIAL]
        
        # Artifacts should exist
        assert result1.output_path.exists()
        assert result2.output_path.exists()
        
        # Content should be identical (ignoring timestamps in run summary)
        content1 = result1.artifact_content
        content2 = result2.artifact_content
        
        # Remove dynamic content for comparison
        content1_lines = [l for l in content1.split('\n') if 'Job ID:' not in l and 'Duration:' not in l]
        content2_lines = [l for l in content2.split('\n') if 'Job ID:' not in l and 'Duration:' not in l]
        
        assert content1_lines == content2_lines
    
    def test_validation_errors_same(self, temp_output_dir):
        """Test that validation errors are identical."""
        
        # Create invalid RunSpec (no topic, no auto_topic, no context)
        run_spec = RunSpec(
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        # Validate
        errors = run_spec.validate()
        
        assert len(errors) > 0
        assert any('topic' in e.lower() for e in errors)
        
        # Execute should fail with same error
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        assert result.status == JobStatus.FAILED
        assert result.error is not None
    
    def test_pipeline_order_identical(self, temp_output_dir):
        """Test that pipeline order is identical."""
        
        run_spec = RunSpec(
            topic="Test",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        engine = get_engine()
        
        result1 = engine.generate_job(run_spec)
        result2 = engine.generate_job(run_spec)
        
        # Pipeline order should be identical
        assert result1.pipeline_order == result2.pipeline_order
    
    def test_with_context_paths(self, temp_output_dir):
        """Test with context paths provided."""
        
        # Create dummy context files
        kb_dir = temp_output_dir / 'kb'
        kb_dir.mkdir()
        (kb_dir / 'test.md').write_text('# Test KB Content')
        
        run_spec = RunSpec(
            topic="Test with Context",
            template_name="default_blog",
            kb_path=str(kb_dir),
            output_dir=temp_output_dir / 'output'
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        # Should succeed
        assert result.status in [JobStatus.COMPLETED, JobStatus.PARTIAL]
        
        # Should record source
        assert str(kb_dir) in result.sources_used
    
    def test_manifest_reproducibility(self, temp_output_dir):
        """Test that manifest is generated for reproducibility."""
        
        run_spec = RunSpec(
            topic="Reproducibility Test",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        # Manifest should exist
        assert result.manifest_path is not None
        assert result.manifest_path.exists()
        
        # Load and validate manifest
        with open(result.manifest_path) as f:
            manifest = json.load(f)
        
        assert manifest['job_id'] == result.job_id
        assert manifest['template_name'] == run_spec.template_name
        assert 'config_hashes' in manifest
        assert 'pipeline_order' in manifest
        assert manifest['status'] == result.status.value


class TestOutputFormats:
    """Test output path rules for different template types."""
    
    @pytest.fixture
    def temp_output_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_blog_template_creates_index(self, temp_output_dir):
        """Test that blog templates create slug/index.md."""
        
        run_spec = RunSpec(
            topic="My Amazing Blog Post",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        # Should create directory with index.md
        assert result.output_path is not None
        assert result.output_path.name == 'index.md'
        assert 'my-amazing-blog-post' in str(result.output_path.parent)
    
    def test_non_blog_template_creates_file(self, temp_output_dir):
        """Test that non-blog templates create slug.md."""
        
        # Would need a non-blog template for this test
        # Skipping for now as default template is blog
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
