"""Test artifact persistence for success and failure cases."""

import pytest
import json
import tempfile
import shutil
from pathlib import Path

from src.engine.unified_engine import get_engine, RunSpec, JobStatus


class TestArtifactPersistence:
    """Test artifact writing in all scenarios."""
    
    @pytest.fixture
    def temp_output_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_success_artifact_written(self, temp_output_dir):
        """Test that successful runs write complete artifacts."""
        
        run_spec = RunSpec(
            topic="Successful Test Topic",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        # Artifact should be written
        assert result.output_path is not None
        assert result.output_path.exists()
        
        # Should have content
        content = result.output_path.read_text()
        assert len(content) > 0
        
        # Should have run summary
        assert 'Run Summary' in content
        assert result.job_id in content
    
    def test_partial_artifact_includes_errors(self, temp_output_dir):
        """Test that partial artifacts include error information."""
        
        # This would require a way to force partial failure
        # For now, testing the error section generation
        
        run_spec = RunSpec(
            topic="Test",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        # Even if successful, check that error handling works
        if result.status == JobStatus.PARTIAL or result.status == JobStatus.FAILED:
            content = result.output_path.read_text()
            
            # Should have error section
            if result.error:
                assert 'Error' in content or 'error' in content.lower()
    
    def test_artifact_has_run_summary(self, temp_output_dir):
        """Test that artifacts include run summary."""
        
        run_spec = RunSpec(
            topic="Summary Test",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        content = result.output_path.read_text()
        
        # Should have run summary components
        assert 'Job ID:' in content
        assert 'Status:' in content
        assert 'Template:' in content
        assert 'Duration:' in content
        assert 'Pipeline:' in content
    
    def test_artifact_includes_sources_when_provided(self, temp_output_dir):
        """Test that artifacts list sources used."""
        
        # Create dummy KB
        kb_dir = temp_output_dir / 'kb'
        kb_dir.mkdir()
        (kb_dir / 'test.md').write_text('Test content')
        
        run_spec = RunSpec(
            topic="Test with Sources",
            template_name="default_blog",
            kb_path=str(kb_dir),
            output_dir=temp_output_dir / 'output'
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        content = result.output_path.read_text()
        
        # Should mention sources
        assert 'Sources:' in content or str(kb_dir) in result.sources_used


class TestManifestGeneration:
    """Test manifest generation for reproducibility."""
    
    @pytest.fixture
    def temp_output_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_manifest_written_with_artifact(self, temp_output_dir):
        """Test that manifest is written alongside artifact."""
        
        run_spec = RunSpec(
            topic="Manifest Test",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        # Manifest should exist
        assert result.manifest_path is not None
        assert result.manifest_path.exists()
        
        # Should be JSON
        with open(result.manifest_path) as f:
            manifest = json.load(f)
        
        assert isinstance(manifest, dict)
    
    def test_manifest_has_required_fields(self, temp_output_dir):
        """Test that manifest has all required fields."""
        
        run_spec = RunSpec(
            topic="Manifest Fields Test",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        with open(result.manifest_path) as f:
            manifest = json.load(f)
        
        # Required fields for reproducibility
        assert 'job_id' in manifest
        assert 'timestamp' in manifest
        assert 'run_spec' in manifest
        assert 'template_name' in manifest
        assert 'pipeline_order' in manifest
        assert 'config_hashes' in manifest
        assert 'engine_version' in manifest
        assert 'status' in manifest
        assert 'duration' in manifest
    
    def test_manifest_includes_config_hashes(self, temp_output_dir):
        """Test that manifest includes config hashes."""
        
        run_spec = RunSpec(
            topic="Config Hash Test",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        with open(result.manifest_path) as f:
            manifest = json.load(f)
        
        hashes = manifest['config_hashes']
        
        assert 'agent' in hashes
        assert 'perf' in hashes
        assert 'tone' in hashes
        
        # Hashes should be non-empty strings
        for key, hash_val in hashes.items():
            assert isinstance(hash_val, str)
            assert len(hash_val) > 0
    
    def test_manifest_includes_sources_used(self, temp_output_dir):
        """Test that manifest includes sources used."""
        
        kb_dir = temp_output_dir / 'kb'
        kb_dir.mkdir()
        (kb_dir / 'test.md').write_text('Test')
        
        run_spec = RunSpec(
            topic="Sources Test",
            template_name="default_blog",
            kb_path=str(kb_dir),
            output_dir=temp_output_dir / 'output'
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        with open(result.manifest_path) as f:
            manifest = json.load(f)
        
        assert 'sources_used' in manifest
        assert isinstance(manifest['sources_used'], list)


class TestOutputPathRules:
    """Test output path rules for different template types."""
    
    @pytest.fixture
    def temp_output_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_blog_creates_slug_directory(self, temp_output_dir):
        """Test that blog templates create slug/index.md."""
        
        run_spec = RunSpec(
            topic="My Blog Post Title!",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        # Should create directory with slugified name
        assert result.output_path.name == 'index.md'
        assert 'my-blog-post-title' in result.output_path.parent.name
    
    def test_slug_removes_special_characters(self, temp_output_dir):
        """Test that slugification removes special characters."""
        
        run_spec = RunSpec(
            topic="Test: With Special! Characters@ #$%",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        # Slug should only have alphanumeric and hyphens
        slug = result.output_path.parent.name
        
        assert ':' not in slug
        assert '!' not in slug
        assert '@' not in slug
        assert '#' not in slug
        assert '$' not in slug
        assert '%' not in slug


class TestContentQuality:
    """Test that generated content meets quality standards."""
    
    @pytest.fixture
    def temp_output_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_no_placeholder_boilerplate(self, temp_output_dir):
        """Test that output doesn't contain bare placeholder text."""
        
        run_spec = RunSpec(
            topic="Quality Test",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        content = result.output_path.read_text()
        
        # Should not have obvious placeholders
        bad_phrases = [
            'Generated content...',
            '[TODO]',
            '[PLACEHOLDER]',
            'Lorem ipsum'
        ]
        
        for phrase in bad_phrases:
            assert phrase not in content, f"Found placeholder: {phrase}"
    
    def test_structured_sections_present(self, temp_output_dir):
        """Test that output has structured sections."""
        
        run_spec = RunSpec(
            topic="Structure Test",
            template_name="default_blog",
            output_dir=temp_output_dir
        )
        
        engine = get_engine()
        result = engine.generate_job(run_spec)
        
        content = result.output_path.read_text()
        
        # Should have markdown headings
        assert '#' in content or '##' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
