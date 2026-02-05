"""Test configuration validation and loading."""

import pytest
import json
import yaml
import tempfile
from pathlib import Path

from src.core.config_validator import (
    get_config_validator,
    get_config,
    ConfigValidator,
    ValidationError
)


class TestConfigValidator:
    """Test configuration validation."""
    
    def test_load_all_configs_successfully(self):
        """Test that all configs load without errors."""
        
        validator = get_config_validator()
        configs = validator.load_and_validate_all()
        
        assert 'agent' in configs
        assert 'perf' in configs
        assert 'tone' in configs
    
    def test_agent_config_validation(self):
        """Test agent config validation."""
        
        validator = ConfigValidator()
        
        # Valid config
        valid_config = {
            'agents': {
                'test_agent': {
                    'enabled': True
                }
            },
            'workflows': {
                'default': {
                    'steps': ['test_agent']
                }
            }
        }
        
        result = validator.validate_agent_config(valid_config)
        assert result is not None
        assert 'agents' in result
    
    def test_agent_config_missing_required_field(self):
        """Test that missing required field raises error."""
        
        validator = ConfigValidator()
        
        # Missing 'agents' field
        invalid_config = {
            'workflows': {}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_agent_config(invalid_config)
        
        assert 'agents' in str(exc_info.value)
    
    def test_perf_config_with_defaults(self):
        """Test that performance config applies defaults."""
        
        validator = ConfigValidator()
        
        # Empty config
        config = {}
        
        result = validator.validate_perf_config(config)
        
        # Should have defaults applied
        assert 'timeouts' in result
        assert 'limits' in result
        assert 'batch' in result
        
        assert result['timeouts']['agent_execution'] == 30
        assert result['limits']['max_tokens_per_agent'] == 4000
    
    def test_perf_config_merges_with_defaults(self):
        """Test that partial config merges with defaults."""
        
        validator = ConfigValidator()
        
        # Partial config
        config = {
            'timeouts': {
                'agent_execution': 60  # Custom value
            }
        }
        
        result = validator.validate_perf_config(config)
        
        # Should have custom value
        assert result['timeouts']['agent_execution'] == 60
        
        # Should have defaults for missing values
        assert 'total_job' in result['timeouts']
        assert 'limits' in result
    
    def test_tone_config_validation(self):
        """Test tone config validation with defaults."""
        
        validator = ConfigValidator()
        
        # Minimal config
        config = {
            'global_voice': {
                'pov': 'first_person'
            },
            'section_controls': {}
        }
        
        result = validator.validate_tone_config(config)
        
        assert result is not None
        assert 'global_voice' in result
        assert result['global_voice']['pov'] == 'first_person'
    
    def test_get_config_singleton(self):
        """Test that get_config returns same instance."""
        
        config1 = get_config()
        config2 = get_config()
        
        # Should be same validated configs
        assert config1 is config2
    
    def test_config_caching(self):
        """Test that configs are cached after first load."""
        
        validator = get_config_validator()
        
        # First load
        configs1 = validator.get_validated_configs()
        
        # Second call should return cached
        configs2 = validator.get_validated_configs()
        
        assert configs1 is configs2


class TestConfigIntegration:
    """Test configuration integration with other components."""
    
    @pytest.mark.live
    def test_config_used_by_engine(self):
        """Test that engine loads and uses config."""

        from src.engine.unified_engine import get_engine

        engine = get_engine()

        # Should have configs loaded (config_snapshot is the main config object)
        assert engine.config_snapshot is not None
        assert engine.agent_config is not None
        assert engine.perf_config is not None
        assert engine.tone_config is not None
    
    def test_perf_config_has_required_fields(self):
        """Test that perf config has required runtime fields."""
        
        config = get_config()
        perf = config['perf']
        
        # Required fields for runtime
        assert 'timeouts' in perf
        assert 'limits' in perf
        assert 'batch' in perf
        
        # Specific required values
        assert perf['timeouts']['agent_execution'] > 0
        assert perf['limits']['max_tokens_per_agent'] > 0
        assert perf['limits']['max_steps'] > 0
    
    def test_tone_config_has_voice_settings(self):
        """Test that tone config has voice settings."""
        
        config = get_config()
        tone = config['tone']
        
        assert 'global_voice' in tone
        assert 'section_controls' in tone
        
        voice = tone['global_voice']
        assert 'pov' in voice
        assert 'formality' in voice


class TestConfigErrorHandling:
    """Test error handling in config validation."""
    
    def test_missing_config_file_error(self):
        """Test that missing config file raises appropriate error."""
        
        # Create validator with non-existent directory
        validator = ConfigValidator(Path('/nonexistent'))
        
        with pytest.raises(FileNotFoundError):
            validator.load_and_validate_all()
    
    def test_validation_error_has_context(self):
        """Test that validation errors include context."""
        
        validator = ConfigValidator()
        
        try:
            validator.validate_agent_config({})
        except ValidationError as e:
            assert e.field is not None
            assert e.message is not None
            assert e.config_file is not None
            assert 'agents.yaml' in e.config_file


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
# DOCGEN:LLM-FIRST@v4