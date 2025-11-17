"""DOCGEN:LLM-FIRST@v2

Module overview
- Purpose: Initializes the config package by importing and re-exporting configuration schemas and validation components for centralized access.
- Lifecycle: Imported automatically when the config package is used, typically during application initialization for configuration management.
- Collaborators: config.schemas, config.validator
- Key inputs: Configuration files (YAML/JSON formats), environment variables for overrides
- Key outputs: Validated configuration snapshots, JSON schemas for validation

Public API Catalog
| Symbol | Kind | Defined in | Purpose | Inputs | Outputs | Raises | Notes |
|-------:|:-----|:-----------|:--------|:-------|:--------|:-------|:------|
| AGENT_SCHEMA | Constant | config.schemas | JSON schema for agent configurations | None | Dict[str, Any] | None | Validates agent metadata and capabilities |
| PERF_SCHEMA | Constant | config.schemas | JSON schema for performance settings | None | Dict[str, Any] | None | Defines timeouts, limits, and batch processing rules |
| TONE_SCHEMA | Constant | config.schemas | JSON schema for tone and voice settings | None | Dict[str, Any] | None | Specifies POV, formality, and personality controls |
| MAIN_SCHEMA | Constant | config.schemas | JSON schema for main pipeline configuration | None | Dict[str, Any] | None | Validates pipeline steps and dependencies |
| ConfigValidator | Class | src.core.config_validator | Validates and merges configurations with defaults | config_dir (Path, optional) | ConfigValidator instance | None | Singleton pattern for global config access |
| ConfigSnapshot | Class | config.validator | Immutable snapshot of loaded configurations | agent_config, perf_config, tone_config, main_config, merged_config, config_hash, timestamp | ConfigSnapshot instance | None | Includes hash for change detection |
| load_validated_config | Function | config.validator | Loads and validates all configuration files | config_dir (Path, default="./config") | ConfigSnapshot | Exception (file loading/parsing errors) | Merges defaults, applies env overrides |

Design notes
- Contracts & invariants: Re-exports maintain original contracts from source modules; no additional invariants enforced.
- Error surface: No exceptions raised; errors from imported modules propagate unchanged.
- Concurrency: No concurrency mechanisms; thread-safe if underlying file operations are.
- I/O & performance: Involves file I/O via imported validator (YAML/JSON loading); performance depends on file sizes and parsing.
- Configuration map: Schemas define structured config maps for agents, performance, tone, and main settings.
- External deps: Depends on yaml and json libraries via config.validator for file parsing.
"""

from config.schemas import AGENT_SCHEMA, PERF_SCHEMA, TONE_SCHEMA, MAIN_SCHEMA
from config.validator import ConfigSnapshot, load_validated_config

__all__ = [
    "AGENT_SCHEMA",
    "PERF_SCHEMA", 
    "TONE_SCHEMA",
    "MAIN_SCHEMA",
    "ConfigSnapshot",
    "load_validated_config"
]
# DOCGEN:LLM-FIRST@v4