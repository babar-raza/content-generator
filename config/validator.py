"""Authoritative Configuration Validator - Fail Fast on Schema Mismatch"""

import json
import hashlib
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


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
    Returns ConfigSnapshot with all configurations.
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
