"""Configuration Validator - Schema validation and defaults for all config files."""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class ValidationError(Exception):
    """Configuration validation error."""
    field: str
    message: str
    config_file: str


@dataclass
class ConfigSchema:
    """Configuration schema definitions."""
    
    # Agent config required fields
    AGENT_REQUIRED = ['agents', 'workflows']
    
    # Performance config required fields
    PERF_REQUIRED = ['timeouts', 'limits', 'batch']
    PERF_DEFAULTS = {
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
    
    # Tone config required fields
    TONE_REQUIRED = ['global_voice', 'section_controls']
    TONE_DEFAULTS = {
        'global_voice': {
            'pov': 'second_person',
            'formality': 'professional_conversational',
            'technical_depth': 'intermediate'
        }
    }


class ConfigValidator:
    """Validates and merges configurations with defaults."""
    
    def __init__(self, config_dir: Path = None):
        """Initialize validator.
        
        Args:
            config_dir: Path to config directory (default: ./config)
        """
        self.config_dir = config_dir or Path(__file__).parent.parent.parent / 'config'
        self._validated_configs = {}
        
    def validate_agent_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate agent configuration.
        
        Args:
            config: Raw agent configuration
            
        Returns:
            Validated configuration
            
        Raises:
            ValidationError: If validation fails
        """
        for field in ConfigSchema.AGENT_REQUIRED:
            if field not in config:
                raise ValidationError(
                    field=field,
                    message=f"Required field '{field}' missing",
                    config_file='agents.yaml'
                )
        
        # Validate agent structure
        if not isinstance(config['agents'], dict):
            raise ValidationError(
                field='agents',
                message="'agents' must be a dictionary",
                config_file='agents.yaml'
            )
            
        # Validate each agent has required fields
        for agent_name, agent_def in config['agents'].items():
            if 'enabled' not in agent_def:
                agent_def['enabled'] = True
            if 'dependencies' not in agent_def:
                agent_def['dependencies'] = []
                
        return config
    
    def validate_perf_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate performance configuration with defaults.
        
        Args:
            config: Raw performance configuration
            
        Returns:
            Validated configuration with defaults applied
            
        Raises:
            ValidationError: If validation fails
        """
        # Apply defaults
        for section, defaults in ConfigSchema.PERF_DEFAULTS.items():
            if section not in config:
                config[section] = defaults.copy()
            else:
                # Merge with defaults
                for key, value in defaults.items():
                    if key not in config[section]:
                        config[section][key] = value
        
        # Validate required sections exist
        for field in ConfigSchema.PERF_REQUIRED:
            if field not in config:
                raise ValidationError(
                    field=field,
                    message=f"Required field '{field}' missing (even after defaults)",
                    config_file='perf.json'
                )
        
        # Validate numeric values
        try:
            assert config['timeouts']['agent_execution'] > 0
            assert config['timeouts']['total_job'] > 0
            assert config['limits']['max_tokens_per_agent'] > 0
            assert config['limits']['max_steps'] > 0
        except (KeyError, AssertionError) as e:
            raise ValidationError(
                field='validation',
                message=f"Invalid numeric values in performance config: {e}",
                config_file='perf.json'
            )
            
        return config
    
    def validate_tone_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tone configuration with defaults.
        
        Args:
            config: Raw tone configuration
            
        Returns:
            Validated configuration with defaults applied
            
        Raises:
            ValidationError: If validation fails
        """
        # Apply defaults
        for section, defaults in ConfigSchema.TONE_DEFAULTS.items():
            if section not in config:
                config[section] = defaults.copy()
            else:
                # Merge with defaults
                for key, value in defaults.items():
                    if key not in config[section]:
                        config[section][key] = value
        
        # Validate required sections
        for field in ConfigSchema.TONE_REQUIRED:
            if field not in config:
                raise ValidationError(
                    field=field,
                    message=f"Required field '{field}' missing",
                    config_file='tone.json'
                )
                
        return config
    
    def load_and_validate_all(self) -> Dict[str, Dict[str, Any]]:
        """Load and validate all configuration files.
        
        Returns:
            Dictionary with validated configs: {'agent': {...}, 'perf': {...}, 'tone': {...}}
            
        Raises:
            ValidationError: If any validation fails
            FileNotFoundError: If config files are missing
        """
        configs = {}
        
        # Load agent config
        agent_path = self.config_dir / 'agents.yaml'
        if not agent_path.exists():
            raise FileNotFoundError(f"Agent config not found: {agent_path}")
        
        with open(agent_path) as f:
            agent_config = yaml.safe_load(f)
        configs['agent'] = self.validate_agent_config(agent_config)
        
        # Load performance config
        perf_path = self.config_dir / 'perf.json'
        if not perf_path.exists():
            raise FileNotFoundError(f"Performance config not found: {perf_path}")
        
        with open(perf_path) as f:
            perf_config = json.load(f)
        configs['perf'] = self.validate_perf_config(perf_config)
        
        # Load tone config
        tone_path = self.config_dir / 'tone.json'
        if not tone_path.exists():
            raise FileNotFoundError(f"Tone config not found: {tone_path}")
        
        with open(tone_path) as f:
            tone_config = json.load(f)
        configs['tone'] = self.validate_tone_config(tone_config)
        
        # Cache validated configs
        self._validated_configs = configs
        
        return configs
    
    def get_validated_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get cached validated configs or load if not cached.
        
        Returns:
            Dictionary with validated configs
        """
        if not self._validated_configs:
            return self.load_and_validate_all()
        return self._validated_configs


# Global validator instance (singleton)
_validator_instance: Optional[ConfigValidator] = None


def get_config_validator() -> ConfigValidator:
    """Get global config validator instance.
    
    Returns:
        ConfigValidator instance
    """
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ConfigValidator()
    return _validator_instance


def get_config() -> Dict[str, Dict[str, Any]]:
    """Get validated configuration (source of truth for all config access).
    
    This is the single entry point for all configuration access.
    Both CLI and Web must use this function.
    
    Returns:
        Dictionary with validated configs: {'agent': {...}, 'perf': {...}, 'tone': {...}}
        
    Example:
        >>> config = get_config()
        >>> agent_config = config['agent']
        >>> perf_limits = config['perf']['limits']
        >>> tone_voice = config['tone']['global_voice']
    """
    return get_config_validator().get_validated_configs()
# DOCGEN:LLM-FIRST@v4