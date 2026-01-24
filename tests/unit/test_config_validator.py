"""Tests for config_validator module."""

import pytest
import tempfile
import json
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open
from src.core.config_validator import (
    ValidationError,
    ConfigSchema,
    ConfigValidator,
    get_config_validator,
    get_config
)


class TestValidationError:
    """Tests for ValidationError class."""
    
    def test_validation_error_creation(self):
        """Test creating a ValidationError."""
        error = ValidationError(
            field="test_field",
            message="Test message",
            config_file="test.yaml"
        )
        assert error.field == "test_field"
        assert error.message == "Test message"
        assert error.config_file == "test.yaml"
    
    def test_validation_error_inheritance(self):
        """Test that ValidationError inherits from Exception."""
        error = ValidationError("field", "message", "file")
        assert isinstance(error, Exception)


class TestConfigSchema:
    """Tests for ConfigSchema class."""
    
    def test_agent_required_fields(self):
        """Test AGENT_REQUIRED constant."""
        assert 'agents' in ConfigSchema.AGENT_REQUIRED
        # Note: workflows are optional in agent config
    
    def test_perf_required_fields(self):
        """Test PERF_REQUIRED constant."""
        assert 'timeouts' in ConfigSchema.PERF_REQUIRED
        assert 'limits' in ConfigSchema.PERF_REQUIRED
        assert 'batch' in ConfigSchema.PERF_REQUIRED
    
    def test_perf_defaults(self):
        """Test PERF_DEFAULTS structure."""
        defaults = ConfigSchema.PERF_DEFAULTS
        assert 'timeouts' in defaults
        assert 'limits' in defaults
        assert 'batch' in defaults
        assert defaults['timeouts']['agent_execution'] == 30
        assert defaults['limits']['max_tokens_per_agent'] == 4000
        assert defaults['batch']['enabled'] is True
    
    def test_tone_required_fields(self):
        """Test TONE_REQUIRED constant."""
        assert 'global_voice' in ConfigSchema.TONE_REQUIRED
        assert 'section_controls' in ConfigSchema.TONE_REQUIRED
    
    def test_tone_defaults(self):
        """Test TONE_DEFAULTS structure."""
        defaults = ConfigSchema.TONE_DEFAULTS
        assert 'global_voice' in defaults
        assert defaults['global_voice']['pov'] == 'second_person'


class TestConfigValidator:
    """Tests for ConfigValidator class."""
    
    def test_initialization_default(self):
        """Test validator initialization with default config dir."""
        validator = ConfigValidator()
        assert validator.config_dir is not None
        assert validator._validated_configs == {}
    
    def test_initialization_custom_dir(self):
        """Test validator initialization with custom config dir."""
        custom_dir = Path("/custom/config")
        validator = ConfigValidator(custom_dir)
        assert validator.config_dir == custom_dir
    
    def test_validate_agent_config_valid(self):
        """Test validating valid agent config."""
        validator = ConfigValidator()
        config = {
            'agents': {
                'test_agent': {
                    'enabled': True,
                    'dependencies': []
                }
            },
            'workflows': {}
        }
        result = validator.validate_agent_config(config)
        assert result == config
    
    def test_validate_agent_config_missing_agents(self):
        """Test validation fails when agents field is missing."""
        validator = ConfigValidator()
        config = {'workflows': {}}
        
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_agent_config(config)
        
        assert exc_info.value.field == 'agents'
        assert 'missing' in exc_info.value.message.lower()
    
    def test_validate_agent_config_minimal(self):
        """Test validation passes with minimal config (only agents, no workflows).

        Workflows are optional in agent config.
        """
        validator = ConfigValidator()
        config = {'agents': {}}

        # Should not raise - workflows are optional
        result = validator.validate_agent_config(config)
        assert 'agents' in result
    
    def test_validate_agent_config_invalid_agents_type(self):
        """Test validation fails when agents is not a dict."""
        validator = ConfigValidator()
        config = {
            'agents': [],
            'workflows': {}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_agent_config(config)
        
        assert exc_info.value.field == 'agents'
        assert 'dictionary' in exc_info.value.message.lower()
    
    def test_validate_agent_config_adds_defaults(self):
        """Test that validation adds default enabled and dependencies."""
        validator = ConfigValidator()
        config = {
            'agents': {
                'agent1': {},
                'agent2': {'enabled': False}
            },
            'workflows': {}
        }
        
        result = validator.validate_agent_config(config)
        
        assert result['agents']['agent1']['enabled'] is True
        assert result['agents']['agent1']['dependencies'] == []
        assert result['agents']['agent2']['enabled'] is False
        assert result['agents']['agent2']['dependencies'] == []
    
    def test_validate_perf_config_valid(self):
        """Test validating valid performance config."""
        validator = ConfigValidator()
        config = {
            'timeouts': {
                'agent_execution': 30,
                'total_job': 600,
                'rag_query': 10
            },
            'limits': {
                'max_tokens_per_agent': 4000,
                'max_steps': 50,
                'max_retries': 3
            },
            'batch': {
                'enabled': True,
                'batch_size': 5,
                'max_parallel': 3
            }
        }
        
        result = validator.validate_perf_config(config)
        assert result['timeouts']['agent_execution'] == 30
    
    def test_validate_perf_config_applies_defaults(self):
        """Test that performance config applies defaults."""
        validator = ConfigValidator()
        config = {}
        
        result = validator.validate_perf_config(config)
        
        assert 'timeouts' in result
        assert 'limits' in result
        assert 'batch' in result
        assert result['timeouts']['agent_execution'] == 30
    
    def test_validate_perf_config_merges_partial(self):
        """Test that partial config is merged with defaults."""
        validator = ConfigValidator()
        config = {
            'timeouts': {
                'agent_execution': 60
            }
        }
        
        result = validator.validate_perf_config(config)
        
        assert result['timeouts']['agent_execution'] == 60
        assert result['timeouts']['total_job'] == 600
        assert 'limits' in result
        assert 'batch' in result
    
    def test_validate_perf_config_invalid_timeout(self):
        """Test validation fails with invalid timeout value."""
        validator = ConfigValidator()
        config = {
            'timeouts': {
                'agent_execution': 0,
                'total_job': 600
            },
            'limits': {
                'max_tokens_per_agent': 4000,
                'max_steps': 50
            },
            'batch': {}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_perf_config(config)
        
        assert exc_info.value.field == 'validation'
    
    def test_validate_perf_config_invalid_limits(self):
        """Test validation fails with invalid limit values."""
        validator = ConfigValidator()
        config = {
            'timeouts': {
                'agent_execution': 30,
                'total_job': 600
            },
            'limits': {
                'max_tokens_per_agent': -1,
                'max_steps': 50
            },
            'batch': {}
        }
        
        with pytest.raises(ValidationError):
            validator.validate_perf_config(config)
    
    def test_validate_tone_config_valid(self):
        """Test validating valid tone config."""
        validator = ConfigValidator()
        config = {
            'global_voice': {
                'pov': 'second_person',
                'formality': 'professional',
                'technical_depth': 'intermediate'
            },
            'section_controls': {}
        }
        
        result = validator.validate_tone_config(config)
        assert result['global_voice']['pov'] == 'second_person'
    
    def test_validate_tone_config_applies_defaults(self):
        """Test that tone config applies defaults."""
        validator = ConfigValidator()
        config = {
            'section_controls': {}
        }
        
        result = validator.validate_tone_config(config)
        
        assert 'global_voice' in result
        assert result['global_voice']['pov'] == 'second_person'
    
    def test_validate_tone_config_missing_required(self):
        """Test validation fails when required field is missing."""
        validator = ConfigValidator()
        config = {
            'global_voice': {}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_tone_config(config)
        
        assert exc_info.value.field == 'section_controls'
    
    def test_load_and_validate_all_success(self):
        """Test loading and validating all config files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # Create agent config
            agent_config = {
                'agents': {'test': {}},
                'workflows': {}
            }
            with open(config_dir / 'agents.yaml', 'w') as f:
                yaml.dump(agent_config, f)
            
            # Create perf config
            perf_config = ConfigSchema.PERF_DEFAULTS
            with open(config_dir / 'perf.json', 'w') as f:
                json.dump(perf_config, f)
            
            # Create tone config
            tone_config = {
                'global_voice': ConfigSchema.TONE_DEFAULTS['global_voice'],
                'section_controls': {}
            }
            with open(config_dir / 'tone.json', 'w') as f:
                json.dump(tone_config, f)
            
            validator = ConfigValidator(config_dir)
            configs = validator.load_and_validate_all()
            
            assert 'agent' in configs
            assert 'perf' in configs
            assert 'tone' in configs
    
    def test_load_and_validate_all_missing_agent_file(self):
        """Test loading fails when agent config file is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = ConfigValidator(Path(tmpdir))
            
            with pytest.raises(FileNotFoundError) as exc_info:
                validator.load_and_validate_all()
            
            assert 'agents.yaml' in str(exc_info.value)
    
    def test_load_and_validate_all_missing_perf_file(self):
        """Test loading fails when perf config file is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # Create only agent config
            agent_config = {
                'agents': {},
                'workflows': {}
            }
            with open(config_dir / 'agents.yaml', 'w') as f:
                yaml.dump(agent_config, f)
            
            validator = ConfigValidator(config_dir)
            
            with pytest.raises(FileNotFoundError) as exc_info:
                validator.load_and_validate_all()
            
            assert 'perf.json' in str(exc_info.value)
    
    def test_load_and_validate_all_missing_tone_file(self):
        """Test loading fails when tone config file is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # Create agent and perf configs
            agent_config = {
                'agents': {},
                'workflows': {}
            }
            with open(config_dir / 'agents.yaml', 'w') as f:
                yaml.dump(agent_config, f)
            
            perf_config = ConfigSchema.PERF_DEFAULTS
            with open(config_dir / 'perf.json', 'w') as f:
                json.dump(perf_config, f)
            
            validator = ConfigValidator(config_dir)
            
            with pytest.raises(FileNotFoundError) as exc_info:
                validator.load_and_validate_all()
            
            assert 'tone.json' in str(exc_info.value)
    
    def test_load_and_validate_all_caches_result(self):
        """Test that load_and_validate_all caches the result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # Create all config files
            agent_config = {
                'agents': {},
                'workflows': {}
            }
            with open(config_dir / 'agents.yaml', 'w') as f:
                yaml.dump(agent_config, f)
            
            perf_config = ConfigSchema.PERF_DEFAULTS
            with open(config_dir / 'perf.json', 'w') as f:
                json.dump(perf_config, f)
            
            tone_config = {
                'global_voice': ConfigSchema.TONE_DEFAULTS['global_voice'],
                'section_controls': {}
            }
            with open(config_dir / 'tone.json', 'w') as f:
                json.dump(tone_config, f)
            
            validator = ConfigValidator(config_dir)
            configs1 = validator.load_and_validate_all()
            
            assert validator._validated_configs == configs1
    
    def test_get_validated_configs_returns_cached(self):
        """Test get_validated_configs returns cached configs."""
        validator = ConfigValidator()
        cached_configs = {'agent': {}, 'perf': {}, 'tone': {}}
        validator._validated_configs = cached_configs
        
        result = validator.get_validated_configs()
        
        assert result == cached_configs
    
    def test_get_validated_configs_loads_if_not_cached(self):
        """Test get_validated_configs loads if not cached."""
        validator = ConfigValidator()
        
        with patch.object(validator, 'load_and_validate_all', return_value={'test': 'data'}) as mock_load:
            result = validator.get_validated_configs()
            
            mock_load.assert_called_once()
            assert result == {'test': 'data'}


class TestGlobalFunctions:
    """Tests for global functions."""
    
    def test_get_config_validator_singleton(self):
        """Test get_config_validator returns singleton instance."""
        # Reset global instance
        import src.core.config_validator
        src.core.config_validator._validator_instance = None
        
        validator1 = get_config_validator()
        validator2 = get_config_validator()
        
        assert validator1 is validator2
        assert isinstance(validator1, ConfigValidator)
    
    def test_get_config(self):
        """Test get_config function."""
        with patch('src.core.config_validator.get_config_validator') as mock_get_validator:
            mock_validator = mock_get_validator.return_value
            mock_validator.get_validated_configs.return_value = {
                'agent': {},
                'perf': {},
                'tone': {}
            }
            
            result = get_config()
            
            assert 'agent' in result
            assert 'perf' in result
            assert 'tone' in result
            mock_validator.get_validated_configs.assert_called_once()
