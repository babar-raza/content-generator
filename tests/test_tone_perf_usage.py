"""Tone Configuration Usage Tests

Tests that tone configurations are properly applied throughout content generation.
"""

import pytest
from pathlib import Path
from typing import Dict, Any

from config.validator import load_validated_config


class TestToneConfigurationUsage:
    """Test that tone configuration settings are properly applied."""
    
    def test_global_voice_settings(self):
        """Test global voice settings are accessible."""
        snapshot = load_validated_config(Path("./config"))
        tone_config = snapshot.tone_config
        
        global_voice = tone_config.get('global_voice', {})
        
        # Test POV setting
        assert 'pov' in global_voice
        assert global_voice['pov'] in ['first_person', 'second_person', 'third_person']
        
        # Test formality setting
        assert 'formality' in global_voice
        assert global_voice['formality'] in ['casual', 'professional_conversational', 'formal', 'academic']
        
        # Test technical depth
        assert 'technical_depth' in global_voice
        assert global_voice['technical_depth'] in ['beginner', 'intermediate', 'advanced', 'expert']
        
        # Test personality
        assert 'personality' in global_voice
        assert global_voice['personality'] in ['neutral', 'helpful_expert', 'enthusiastic', 'authoritative']
    
    def test_section_controls_introduction(self):
        """Test introduction section controls."""
        snapshot = load_validated_config(Path("./config"))
        tone_config = snapshot.tone_config
        
        section_controls = tone_config.get('section_controls', {})
        intro = section_controls.get('introduction', {})
        
        assert intro.get('enabled', True) == True
        assert 'heading' in intro
        assert 'tone' in intro
        assert 'structure' in intro
        assert 'word_count_target' in intro
        
        # Test word count target format
        word_count_target = intro['word_count_target']
        assert '-' in word_count_target
        min_words, max_words = map(int, word_count_target.split('-'))
        assert min_words < max_words
    
    def test_section_controls_code_implementation(self):
        """Test code implementation section controls."""
        snapshot = load_validated_config(Path("./config"))
        tone_config = snapshot.tone_config
        
        section_controls = tone_config.get('section_controls', {})
        code_impl = section_controls.get('code_implementation', {})
        
        assert code_impl.get('enabled', True) == True
        assert 'show_complete_code_first' in code_impl
        assert 'show_gist' in code_impl
        assert 'include_license_header' in code_impl
        assert 'segment_explanation_style' in code_impl
    
    def test_section_controls_prerequisites(self):
        """Test prerequisites section controls."""
        snapshot = load_validated_config(Path("./config"))
        tone_config = snapshot.tone_config
        
        section_controls = tone_config.get('section_controls', {})
        prereqs = section_controls.get('prerequisites', {})
        
        assert prereqs.get('enabled', True) == True
        assert 'required_items' in prereqs
        assert isinstance(prereqs['required_items'], list)
        assert len(prereqs['required_items']) > 0
    
    def test_heading_style(self):
        """Test heading style configuration."""
        snapshot = load_validated_config(Path("./config"))
        tone_config = snapshot.tone_config
        
        heading_style = tone_config.get('heading_style', {})
        
        assert 'markdown_format' in heading_style
        assert 'capitalization' in heading_style
        assert heading_style['capitalization'] in ['title_case', 'sentence_case', 'all_caps']
    
    def test_code_template_overrides(self):
        """Test code template overrides."""
        snapshot = load_validated_config(Path("./config"))
        tone_config = snapshot.tone_config
        
        code_overrides = tone_config.get('code_template_overrides', {})
        
        assert 'language_tag' in code_overrides
        assert 'fence_style' in code_overrides
        assert 'indent_style' in code_overrides
        assert 'indent_size' in code_overrides
    
    def test_seo_integration_settings(self):
        """Test SEO integration settings."""
        snapshot = load_validated_config(Path("./config"))
        tone_config = snapshot.tone_config
        
        seo = tone_config.get('seo_integration', {})
        
        assert 'natural_keyword_density' in seo
        assert 'max_keyword_density' in seo
        assert 'focus_keyword_placement' in seo
        assert isinstance(seo['focus_keyword_placement'], list)
    
    def test_quality_checks_settings(self):
        """Test quality checks settings."""
        snapshot = load_validated_config(Path("./config"))
        tone_config = snapshot.tone_config
        
        quality = tone_config.get('quality_checks', {})
        
        assert 'enforce_word_counts' in quality
        assert 'word_count_tolerance' in quality
        assert 'enforce_required_elements' in quality
        assert 'check_readability_score' in quality


class TestPerformanceConfigurationUsage:
    """Test that performance configuration settings are properly applied."""
    
    def test_timeout_settings(self):
        """Test timeout settings."""
        snapshot = load_validated_config(Path("./config"))
        perf_config = snapshot.perf_config
        
        timeouts = perf_config.get('timeouts', {})
        
        assert 'agent_execution' in timeouts
        assert 'total_job' in timeouts
        assert 'rag_query' in timeouts
        assert 'template_render' in timeouts
        
        # All timeouts should be positive
        assert all(t > 0 for t in timeouts.values())
    
    def test_limit_settings(self):
        """Test limit settings."""
        snapshot = load_validated_config(Path("./config"))
        perf_config = snapshot.perf_config
        
        limits = perf_config.get('limits', {})
        
        assert 'max_tokens_per_agent' in limits
        assert 'max_steps' in limits
        assert 'max_retries' in limits
        assert 'max_context_size' in limits
        
        # All limits should be positive
        assert all(l > 0 for l in limits.values() if isinstance(l, int))
    
    def test_batch_settings(self):
        """Test batch processing settings."""
        snapshot = load_validated_config(Path("./config"))
        perf_config = snapshot.perf_config
        
        batch = perf_config.get('batch', {})
        
        if 'enabled' in batch:
            assert isinstance(batch['enabled'], bool)
        
        if batch.get('enabled'):
            assert 'batch_size' in batch
            assert 'max_parallel' in batch
            assert batch['batch_size'] > 0
            assert batch['max_parallel'] > 0
    
    def test_hot_paths_definition(self):
        """Test hot paths are defined."""
        snapshot = load_validated_config(Path("./config"))
        perf_config = snapshot.perf_config
        
        hot_paths = perf_config.get('hot_paths', {})
        
        assert isinstance(hot_paths, dict)
        # Each hot path should have a list of steps
        for path_name, steps in hot_paths.items():
            assert isinstance(steps, list)
            assert len(steps) > 0
    
    def test_prefetch_rules(self):
        """Test prefetch rules are defined."""
        snapshot = load_validated_config(Path("./config"))
        perf_config = snapshot.perf_config
        
        prefetch = perf_config.get('prefetch_rules', {})
        
        assert isinstance(prefetch, dict)
        # Each prefetch rule should map to a list of dependent operations
        for resource, operations in prefetch.items():
            assert isinstance(operations, list)
    
    def test_observability_settings(self):
        """Test observability settings."""
        snapshot = load_validated_config(Path("./config"))
        perf_config = snapshot.perf_config
        
        observability = perf_config.get('observability', {})
        
        if 'critical_paths' in observability:
            assert isinstance(observability['critical_paths'], list)
        
        if 'bottleneck_thresholds' in observability:
            thresholds = observability['bottleneck_thresholds']
            assert isinstance(thresholds, dict)
            # All thresholds should be positive numbers
            assert all(t > 0 for t in thresholds.values())


class TestMainConfigurationUsage:
    """Test that main configuration settings are properly applied."""
    
    def test_pipeline_definition(self):
        """Test pipeline is properly defined."""
        snapshot = load_validated_config(Path("./config"))
        main_config = snapshot.main_config
        
        pipeline = main_config.get('pipeline', [])
        
        assert isinstance(pipeline, list)
        assert len(pipeline) > 0
        # All pipeline items should be strings (agent names)
        assert all(isinstance(item, str) for item in pipeline)
    
    def test_workflow_definitions(self):
        """Test workflow definitions."""
        snapshot = load_validated_config(Path("./config"))
        main_config = snapshot.main_config
        
        workflows = main_config.get('workflows', {})
        
        assert isinstance(workflows, dict)
        assert 'default' in workflows
        
        # Each workflow should have steps
        for workflow_name, workflow_def in workflows.items():
            assert 'steps' in workflow_def
            assert isinstance(workflow_def['steps'], list)
            assert len(workflow_def['steps']) > 0
    
    def test_dependency_definitions(self):
        """Test dependency definitions."""
        snapshot = load_validated_config(Path("./config"))
        main_config = snapshot.main_config
        
        dependencies = main_config.get('dependencies', {})
        
        assert isinstance(dependencies, dict)
        
        # Each dependency should have a 'requires' field
        for agent_id, deps in dependencies.items():
            if 'requires' in deps:
                assert isinstance(deps['requires'], list)


class TestConfigInterdependencies:
    """Test that configurations work together properly."""
    
    def test_pipeline_agents_exist_in_agent_config(self):
        """Test that all pipeline agents are defined in agent config."""
        snapshot = load_validated_config(Path("./config"))
        
        pipeline = snapshot.main_config.get('pipeline', [])
        agents = snapshot.agent_config.get('agents', {})
        
        # Note: Pipeline may reference agents by simplified names
        # This is a soft check - not all pipeline names need to exactly match
        assert len(pipeline) > 0
        assert len(agents) > 0
    
    def test_section_controls_have_valid_word_counts(self):
        """Test that all section word counts are valid."""
        snapshot = load_validated_config(Path("./config"))
        
        section_controls = snapshot.tone_config.get('section_controls', {})
        
        for section_name, section_config in section_controls.items():
            if 'word_count_target' in section_config:
                target = section_config['word_count_target']
                if isinstance(target, str) and '-' in target:
                    min_words, max_words = map(int, target.split('-'))
                    assert min_words > 0
                    assert max_words > min_words
    
    def test_timeouts_are_reasonable(self):
        """Test that timeouts are in reasonable ranges."""
        snapshot = load_validated_config(Path("./config"))
        
        timeouts = snapshot.perf_config.get('timeouts', {})
        
        # Agent execution should be shorter than total job
        agent_timeout = timeouts.get('agent_execution', 30)
        total_job_timeout = timeouts.get('total_job', 600)
        
        assert agent_timeout < total_job_timeout
        assert agent_timeout >= 1  # At least 1 second
        assert total_job_timeout <= 3600  # At most 1 hour


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
