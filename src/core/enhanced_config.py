"""Enhanced Configuration System - Loads all config files

This extends the existing config.py to properly load and respect:
- config/agents.yaml (agent pipeline and settings)
- config/perf.json (performance settings)
- config/tone.json (tone and style settings)
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceConfig:
    """Performance configuration from perf.json"""
    
    # Timeouts
    agent_execution_timeout: int = 30
    total_job_timeout: int = 600
    rag_query_timeout: int = 10
    template_render_timeout: int = 5
    
    # Limits
    max_tokens_per_agent: int = 4000
    max_steps: int = 50
    max_retries: int = 3
    max_context_size: int = 16000
    
    # Batch settings
    batch_enabled: bool = True
    batch_size: int = 5
    max_parallel: int = 3
    batch_window_ms: int = 150
    
    # Additional settings from original perf.json
    hot_paths: Dict[str, list] = field(default_factory=dict)
    prefetch_rules: Dict[str, list] = field(default_factory=dict)
    quorum_rules: Dict[str, Any] = field(default_factory=dict)
    batch_affinity: Dict[str, list] = field(default_factory=dict)
    tuning: Dict[str, Any] = field(default_factory=dict)
    observability: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceConfig':
        """Create from dictionary loaded from perf.json"""
        config = cls()
        
        # Load timeouts
        if 'timeouts' in data:
            timeouts = data['timeouts']
            config.agent_execution_timeout = timeouts.get('agent_execution', config.agent_execution_timeout)
            config.total_job_timeout = timeouts.get('total_job', config.total_job_timeout)
            config.rag_query_timeout = timeouts.get('rag_query', config.rag_query_timeout)
            config.template_render_timeout = timeouts.get('template_render', config.template_render_timeout)
        
        # Load limits
        if 'limits' in data:
            limits = data['limits']
            config.max_tokens_per_agent = limits.get('max_tokens_per_agent', config.max_tokens_per_agent)
            config.max_steps = limits.get('max_steps', config.max_steps)
            config.max_retries = limits.get('max_retries', config.max_retries)
            config.max_context_size = limits.get('max_context_size', config.max_context_size)
        
        # Load batch settings
        if 'batch' in data:
            batch = data['batch']
            config.batch_enabled = batch.get('enabled', config.batch_enabled)
            config.batch_size = batch.get('batch_size', config.batch_size)
            config.max_parallel = batch.get('max_parallel', config.max_parallel)
            config.batch_window_ms = batch.get('batch_window_ms', config.batch_window_ms)
        
        # Load additional settings
        config.hot_paths = data.get('hot_paths', {})
        config.prefetch_rules = data.get('prefetch_rules', {})
        config.quorum_rules = data.get('quorum_rules', {})
        config.batch_affinity = data.get('batch_affinity', {})
        config.tuning = data.get('tuning', {})
        config.observability = data.get('observability', {})
        
        return config


@dataclass
class AgentPipelineConfig:
    """Agent pipeline configuration from agents.yaml"""
    
    pipeline: list = field(default_factory=list)
    workflows: Dict[str, Any] = field(default_factory=dict)
    agents: Dict[str, Any] = field(default_factory=dict)
    dependencies: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentPipelineConfig':
        """Create from dictionary loaded from agents.yaml"""
        config = cls()
        config.pipeline = data.get('pipeline', [])
        config.workflows = data.get('workflows', {})
        config.agents = data.get('agents', {})
        config.dependencies = data.get('dependencies', {})
        return config


class EnhancedConfigManager:
    """Manager for all configuration files"""
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path('./config')
        self._perf_config: Optional[PerformanceConfig] = None
        self._agent_config: Optional[AgentPipelineConfig] = None
        self._tone_config: Optional[Dict[str, Any]] = None
        self._main_config: Optional[Dict[str, Any]] = None
        
    def load_all(self):
        """Load all configuration files"""
        self.load_performance_config()
        self.load_agent_config()
        self.load_tone_config()
        self.load_main_config()
        
    def load_performance_config(self) -> PerformanceConfig:
        """Load performance configuration from perf.json"""
        if self._perf_config is not None:
            return self._perf_config
            
        perf_file = self.config_dir / 'perf.json'
        if perf_file.exists():
            try:
                with open(perf_file, 'r') as f:
                    data = json.load(f)
                self._perf_config = PerformanceConfig.from_dict(data)
                logger.info("✓ Loaded performance config from perf.json")
            except Exception as e:
                logger.warning(f"Failed to load perf.json: {e}")
                self._perf_config = PerformanceConfig()
        else:
            logger.warning("perf.json not found, using defaults")
            self._perf_config = PerformanceConfig()
            
        return self._perf_config
    
    def load_agent_config(self) -> AgentPipelineConfig:
        """Load agent pipeline configuration from agents.yaml"""
        if self._agent_config is not None:
            return self._agent_config
            
        agents_file = self.config_dir / 'agents.yaml'
        if agents_file.exists():
            try:
                with open(agents_file, 'r') as f:
                    data = yaml.safe_load(f)
                self._agent_config = AgentPipelineConfig.from_dict(data)
                logger.info(f"✓ Loaded agent config: {len(self._agent_config.agents)} agents")
            except Exception as e:
                logger.warning(f"Failed to load agents.yaml: {e}")
                self._agent_config = AgentPipelineConfig()
        else:
            logger.warning("agents.yaml not found, using defaults")
            self._agent_config = AgentPipelineConfig()
            
        return self._agent_config
    
    def load_tone_config(self) -> Dict[str, Any]:
        """Load tone configuration from tone.json"""
        if self._tone_config is not None:
            return self._tone_config
            
        tone_file = self.config_dir / 'tone.json'
        if tone_file.exists():
            try:
                with open(tone_file, 'r') as f:
                    self._tone_config = json.load(f)
                logger.info("✓ Loaded tone config from tone.json")
            except Exception as e:
                logger.warning(f"Failed to load tone.json: {e}")
                self._tone_config = {}
        else:
            logger.warning("tone.json not found, using defaults")
            self._tone_config = {}
            
        return self._tone_config
    
    def load_main_config(self) -> Dict[str, Any]:
        """Load main pipeline configuration from main.yaml"""
        if self._main_config is not None:
            return self._main_config
            
        main_file = self.config_dir / 'main.yaml'
        if main_file.exists():
            try:
                with open(main_file, 'r') as f:
                    self._main_config = yaml.safe_load(f)
                logger.info("✓ Loaded main config from main.yaml")
            except Exception as e:
                logger.warning(f"Failed to load main.yaml: {e}")
                self._main_config = {}
        else:
            # Fall back to agents.yaml pipeline
            agent_config = self.load_agent_config()
            self._main_config = {
                'pipeline': agent_config.pipeline,
                'workflows': agent_config.workflows
            }
            
        return self._main_config
    
    @property
    def perf(self) -> PerformanceConfig:
        """Get performance config"""
        if self._perf_config is None:
            self.load_performance_config()
        return self._perf_config
    
    @property
    def agent(self) -> AgentPipelineConfig:
        """Get agent config"""
        if self._agent_config is None:
            self.load_agent_config()
        return self._agent_config
    
    @property
    def tone(self) -> Dict[str, Any]:
        """Get tone config"""
        if self._tone_config is None:
            self.load_tone_config()
        return self._tone_config
    
    @property
    def main(self) -> Dict[str, Any]:
        """Get main config"""
        if self._main_config is None:
            self.load_main_config()
        return self._main_config
    
    def get_pipeline_order(self, workflow: str = 'default') -> list:
        """Get pipeline order for a workflow"""
        main_config = self.load_main_config()
        
        # Try workflows first
        workflows = main_config.get('workflows', {})
        if workflow in workflows:
            return workflows[workflow].get('steps', [])
        
        # Fall back to main pipeline
        return main_config.get('pipeline', [])


# Global instance
_config_manager: Optional[EnhancedConfigManager] = None


def get_config_manager() -> EnhancedConfigManager:
    """Get global config manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = EnhancedConfigManager()
        _config_manager.load_all()
    return _config_manager


class EnhancedConfigLoader:
    """Loader for enhanced configuration with snapshot capability."""

    def __init__(self):
        self.manager = get_config_manager()

    def get_snapshot(self):
        """Get a snapshot of the current configuration."""
        from config.validator import load_validated_config
        return load_validated_config()
