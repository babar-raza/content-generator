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
from src.core.config_validator import ConfigValidator


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




def load_validated_config(config_dir: Path = Path("./config")) -> ConfigSnapshot:
    """
    Main entry point: Load and validate all configs.
    Raises exceptions on any validation failure (fail-fast).
    """
    validator = ConfigValidator(config_dir)
    return validator.validate_and_load()


__all__ = ["ConfigValidator", "ConfigSnapshot", "load_validated_config"]
