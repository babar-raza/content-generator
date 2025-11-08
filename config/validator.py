"""Authoritative Configuration Validator - Fail Fast on Schema Mismatch"""

import json
import hashlib
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import jsonschema

from config.schemas import AGENT_SCHEMA, PERF_SCHEMA, TONE_SCHEMA, MAIN_SCHEMA


@dataclass
class ConfigSnapshot:
    """Frozen configuration snapshot with hash"""
    agent_config: Dict[str, Any]
    perf_config: Dict[str, Any]
    tone_config: Dict[str, Any]
    main_config: Dict[str, Any]
    merged_config: Dict[str, Any]
    config_hash: str
    timestamp: str
    engine_version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class ConfigValidator:
    """Validates and loads all configuration files with fail-fast behavior"""
    
    def __init__(self, config_dir: Path = Path("./config")):
        self.config_dir = config_dir
        self.agent_file = config_dir / "agents.yaml"
        self.perf_file = config_dir / "perf.json"
        self.tone_file = config_dir / "tone.json"
        self.main_file = config_dir / "main.yaml"
        
    def validate_and_load(self) -> ConfigSnapshot:
        """
        Validate and load all configs. Fail fast if any schema mismatch.
        Returns a frozen ConfigSnapshot with hash.
        """
        # Load and validate each config
        agent_config = self._load_and_validate_yaml(
            self.agent_file, AGENT_SCHEMA, "agents.yaml"
        )
        perf_config = self._load_and_validate_json(
            self.perf_file, PERF_SCHEMA, "perf.json"
        )
        tone_config = self._load_and_validate_json(
            self.tone_file, TONE_SCHEMA, "tone.json"
        )
        main_config = self._load_and_validate_yaml(
            self.main_file, MAIN_SCHEMA, "main.yaml"
        )
        
        # Deep merge configs
        merged = self._deep_merge(agent_config, perf_config, tone_config, main_config)
        
        # Compute hash
        config_hash = self._compute_hash(agent_config, perf_config, tone_config, main_config)
        
        # Create snapshot
        snapshot = ConfigSnapshot(
            agent_config=agent_config,
            perf_config=perf_config,
            tone_config=tone_config,
            main_config=main_config,
            merged_config=merged,
            config_hash=config_hash,
            timestamp=datetime.now().isoformat()
        )
        
        return snapshot
    
    def _load_and_validate_yaml(
        self, file_path: Path, schema: Dict, name: str
    ) -> Dict[str, Any]:
        """Load and validate YAML file"""
        if not file_path.exists():
            raise FileNotFoundError(f"Required config file not found: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse {name}: {e}")
        
        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.ValidationError as e:
            raise ValueError(
                f"Schema validation failed for {name}:\n"
                f"  Path: {'.'.join(str(p) for p in e.path)}\n"
                f"  Error: {e.message}"
            )
        
        return data
    
    def _load_and_validate_json(
        self, file_path: Path, schema: Dict, name: str
    ) -> Dict[str, Any]:
        """Load and validate JSON file"""
        if not file_path.exists():
            raise FileNotFoundError(f"Required config file not found: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse {name}: {e}")
        
        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.ValidationError as e:
            raise ValueError(
                f"Schema validation failed for {name}:\n"
                f"  Path: {'.'.join(str(p) for p in e.path)}\n"
                f"  Error: {e.message}"
            )
        
        return data
    
    def _deep_merge(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge multiple config dictionaries"""
        result = {}
        for config in configs:
            self._merge_into(result, config)
        return result
    
    def _merge_into(self, target: Dict, source: Dict):
        """Recursively merge source into target"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_into(target[key], value)
            else:
                target[key] = value
    
    def _compute_hash(self, *configs: Dict[str, Any]) -> str:
        """Compute SHA-256 hash of all configs"""
        hasher = hashlib.sha256()
        for config in configs:
            hasher.update(json.dumps(config, sort_keys=True).encode())
        return hasher.hexdigest()[:16]


def load_validated_config(config_dir: Path = Path("./config")) -> ConfigSnapshot:
    """
    Main entry point: Load and validate all configs.
    Raises exceptions on any validation failure (fail-fast).
    """
    validator = ConfigValidator(config_dir)
    return validator.validate_and_load()


__all__ = ["ConfigValidator", "ConfigSnapshot", "load_validated_config"]
