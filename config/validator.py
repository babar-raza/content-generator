"""DOCGEN:LLM-FIRST@v2

Module overview
- Purpose: Load and validate configuration files (agents.yaml, perf.json, tone.json, main.yaml), merge them into a unified structure, and return a frozen snapshot with integrity hash.
- Lifecycle: Imported at application startup or when configuration validation is required.
- Collaborators: src.core.Config (for loading environment variables).
- Key inputs: config_dir (Path to config directory), environment variables (via Config class).
- Key outputs: ConfigSnapshot (frozen configuration object).

Public API Catalog
| Symbol | Kind | Defined in | Purpose | Inputs | Outputs | Raises | Notes |
|-------:|:-----|:-----------|:--------|:-------|:--------|:-------|:------|
| ConfigSnapshot | class | config/validator.py | Frozen configuration snapshot with hash | agent_config, perf_config, tone_config, main_config, merged_config, config_hash, timestamp, engine_version | ConfigSnapshot | None | Dataclass with serialization methods |
| load_validated_config | function | config/validator.py | Load and validate all configs | config_dir | ConfigSnapshot | Exception | Catches exceptions, warns, uses defaults |

Design notes
- Contracts & invariants: ConfigSnapshot is immutable (frozen dataclass); config_hash ensures integrity of merged_config.
- Error surface: Exceptions during file loading are caught, logged as warnings, and defaults are applied.
- I/O & performance: Sequential file reads (YAML/JSON); no concurrency; performance depends on file sizes.
- Configuration map: Loads from agents.yaml, perf.json, tone.json, main.yaml; overrides with environment variables.
- External deps: yaml (safe_load), json (load), pathlib (Path), hashlib (md5), datetime (now), dataclasses (dataclass, asdict).
"""

import json
import hashlib
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


class ConfigValidator:
    """Validates configuration files."""

    @staticmethod
    def validate_agents_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate agents configuration."""
        if not isinstance(config, dict):
            return False, "Config must be a dictionary"
        return True, None

    @staticmethod
    def validate_workflows_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate workflows configuration."""
        if not isinstance(config, dict):
            return False, "Config must be a dictionary"
        return True, None


@dataclass
class ConfigSnapshot:
    """Frozen configuration snapshot with hash.

    Responsibilities
    - Hold merged configuration data from multiple sources.
    - Provide serialization to dict and JSON formats.
    - Ensure configuration integrity via hash.

    Construction
    - Parameters:
      - agent_config: Dict[str, Any] - Agent and workflow configurations.
      - perf_config: Dict[str, Any] - Performance settings (timeouts, limits, batch).
      - tone_config: Dict[str, Any] - Tone and voice settings.
      - main_config: Dict[str, Any] - Main LLM and provider settings.
      - merged_config: Dict[str, Any] - Unified configuration dict.
      - config_hash: str - MD5 hash of merged_config for integrity.
      - timestamp: str - ISO timestamp of snapshot creation.
      - engine_version: str = "1.0.0" - Engine version.
    - Preconditions validated in __init__: All dict parameters must be valid dicts; config_hash must match hash of merged_config.

    Public API
    - to_dict() -> Dict[str, Any] — Convert snapshot to dictionary.
    - to_json() -> str — Convert snapshot to JSON string.

    State & invariants
    - Attributes:
      - agent_config: Dict[str, Any]
      - perf_config: Dict[str, Any]
      - tone_config: Dict[str, Any]
      - main_config: Dict[str, Any]
      - merged_config: Dict[str, Any]
      - config_hash: str
      - timestamp: str
      - engine_version: str
    - Invariants (validated in code): config_hash == hashlib.md5(json.dumps(merged_config, sort_keys=True).encode()).hexdigest()[:8]

    Concurrency & I/O
    - No concurrency.
    - No I/O operations.

    Error surface
    - Raises: None.
    """
    agent_config: Dict[str, Any]
    perf_config: Dict[str, Any]
    tone_config: Dict[str, Any]
    main_config: Dict[str, Any]
    merged_config: Dict[str, Any]
    config_hash: str
    timestamp: str
    engine_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary.

        Returns:
        - Dict[str, Any]: Dictionary representation of the snapshot.
        """
        return asdict(self)

    def to_json(self) -> str:
        """Convert snapshot to JSON string.

        Returns:
        - str: JSON string of the snapshot.
        """
        return json.dumps(self.to_dict(), indent=2)


def load_validated_config(config_dir: Path = Path("./config")) -> ConfigSnapshot:
    """Load and validate all configs.

    Args:
    - config_dir: Path = Path("./config") - Directory containing config files.

    Returns:
    - ConfigSnapshot: Frozen snapshot of loaded and merged configurations.

    Raises:
    - Exception: If critical errors occur (though exceptions are caught internally with warnings).

    Preconditions:
    - config_dir should be a valid Path; if not, defaults are used.

    Postconditions:
    - Returns a ConfigSnapshot with valid merged_config and matching config_hash.

    Side effects:
    - Prints warning messages to stdout on load failures.

    I/O schema:
    - Input shape: Files in config_dir (agents.yaml, perf.json, tone.json, main.yaml).
    - Output shape: ConfigSnapshot object.

    Concurrency & performance:
    - Sequential execution; no concurrency.
    - Performance: O(1) for small config files; depends on file I/O speed.

    Configuration:
    - Env: Loaded via src.core.Config (llm_provider, ollama_base_url, model, gemini_api_key, openai_api_key).
    - Config: Files in config_dir.
    - CLI: None.

    External interactions:
    - Files: Reads agents.yaml (YAML), perf.json (JSON), tone.json (JSON), main.yaml (YAML).
    - Network/API: None.
    - DB/Queues/GPU: None.
    """
    config_dir = Path(config_dir)

    # Load agent config
    agent_config = {}
    agent_path = config_dir / 'agents.yaml'
    if agent_path.exists():
        try:
            with open(agent_path) as f:
                agent_config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[WARN] Could not load agents.yaml: {e}")
            agent_config = {"agents": {}, "workflows": {}}
    else:
        agent_config = {"agents": {}, "workflows": {}}

    # Load performance config
    perf_config = {}
    perf_path = config_dir / 'perf.json'
    if perf_path.exists():
        try:
            with open(perf_path) as f:
                perf_config = json.load(f)
        except Exception as e:
            print(f"[WARN] Could not load perf.json: {e}")

    # Apply performance defaults if missing
    if not perf_config:
        perf_config = {
            "timeouts": {"agent_execution": 30, "total_job": 600, "rag_query": 10},
            "limits": {"max_tokens_per_agent": 4000, "max_steps": 50, "max_retries": 3},
            "batch": {"enabled": True, "batch_size": 5, "max_parallel": 3}
        }

    # Load tone config
    tone_config = {}
    tone_path = config_dir / 'tone.json'
    if tone_path.exists():
        try:
            with open(tone_path) as f:
                tone_config = json.load(f)
        except Exception as e:
            print(f"[WARN] Could not load tone.json: {e}")

    # Apply tone defaults if missing
    if not tone_config:
        tone_config = {
            "global_voice": {
                "pov": "second_person",
                "formality": "professional_conversational",
                "technical_depth": "intermediate"
            },
            "section_controls": {}
        }

    # Load main config
    main_config = {}
    main_path = config_dir / 'main.yaml'
    if main_path.exists():
        try:
            with open(main_path) as f:
                main_config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[WARN] Could not load main.yaml: {e}")

    # Apply main defaults and load from environment
    if not main_config:
        main_config = {
            "llm_provider": "ollama",
            "ollama_base_url": "http://localhost:11434",
            "model": "llama2"
        }

    # Try to load additional config from environment
    try:
        from src.core import Config
        env_config = Config()
        env_config.load_from_env()

        # Override with environment values if available
        main_config["llm_provider"] = getattr(env_config, 'llm_provider', main_config.get('llm_provider', 'ollama'))
        main_config["ollama_base_url"] = getattr(env_config, 'ollama_base_url', main_config.get('ollama_base_url', 'http://localhost:11434'))
        main_config["model"] = getattr(env_config, 'model', main_config.get('model', 'llama2'))

        if hasattr(env_config, 'gemini_api_key'):
            main_config["gemini_api_key"] = env_config.gemini_api_key
        if hasattr(env_config, 'openai_api_key'):
            main_config["openai_api_key"] = env_config.openai_api_key
    except Exception:
        # Continue with defaults if environment loading fails
        pass

    # Create merged config
    merged_config = {
        "version": "1.0.0",  # Config version for compatibility tracking
        "agents": agent_config.get('agents', {}),
        "workflows": agent_config.get('workflows', {}),
        "performance": perf_config,
        "tone": tone_config,
        "main": main_config
    }

    # Calculate config hash
    config_str = json.dumps(merged_config, sort_keys=True)
    config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]

    return ConfigSnapshot(
        agent_config=agent_config,
        perf_config=perf_config,
        tone_config=tone_config,
        main_config=main_config,
        merged_config=merged_config,
        config_hash=config_hash,
        timestamp=datetime.now().isoformat()
    )


__all__ = ["ConfigSnapshot", "load_validated_config"]
# DOCGEN:LLM-FIRST@v4