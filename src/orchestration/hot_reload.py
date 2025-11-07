# hot_reload.py
"""Hot-reload configuration system for UCOP agents.

Monitors configuration files and reloads agents without system restart.
"""

import os
import time
import threading
import logging
from pathlib import Path
from typing import Dict, Callable, Optional, Any, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import yaml
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfigChangeHandler(FileSystemEventHandler):
    """Handle configuration file changes."""
    
    def __init__(self, hot_reload_manager: 'HotReloadManager'):
        self.manager = hot_reload_manager
        self.debounce_delay = 1.0  # Seconds to wait for file stabilization
        self._pending_changes: Dict[str, float] = {}
        self._lock = threading.Lock()
        
        # Start debounce processor
        self._debounce_thread = threading.Thread(target=self._process_pending_changes, daemon=True)
        self._debounce_thread.start()
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Only process config files
        if file_path.suffix not in {'.yaml', '.yml', '.json'}:
            return
            
        logger.info(f"Config file changed: {file_path}")
        
        with self._lock:
            self._pending_changes[str(file_path)] = time.time()
    
    def _process_pending_changes(self):
        """Process pending file changes with debouncing."""
        while True:
            time.sleep(0.5)  # Check every 500ms
            
            with self._lock:
                current_time = time.time()
                ready_files = []
                
                for file_path, change_time in self._pending_changes.items():
                    if current_time - change_time >= self.debounce_delay:
                        ready_files.append(file_path)
                
                # Process ready files
                for file_path in ready_files:
                    del self._pending_changes[file_path]
                    try:
                        self.manager._reload_config_file(Path(file_path))
                    except Exception as e:
                        logger.error(f"Failed to reload {file_path}: {e}")


class HotReloadManager:
    """Manages hot-reloading of configuration files."""
    
    def __init__(self, config_dir: Path, registry_callback: Optional[Callable] = None):
        self.config_dir = config_dir
        self.registry_callback = registry_callback
        self._observers: Dict[str, Observer] = {}
        self._reload_callbacks: Dict[str, Callable[[Path], None]] = {}
        self._lock = threading.RLock()
        
        # Track loaded configurations
        self._loaded_configs: Dict[str, Dict[str, Any]] = {}
        self._config_checksums: Dict[str, str] = {}
        
        self.setup_default_callbacks()
    
    def setup_default_callbacks(self):
        """Setup default reload callbacks for common config files."""
        self.register_callback('agents.yaml', self._reload_agents_config)
        self.register_callback('workflows.yaml', self._reload_workflows_config)
        self.register_callback('policies/*.json', self._reload_policies_config)
        self.register_callback('models.yaml', self._reload_models_config)
        self.register_callback('cache.yaml', self._reload_cache_config)
    
    def start_watching(self, directories: list[Path] | None = None):
        """Start watching configuration directories."""
        if directories is None:
            directories = [self.config_dir]
        
        for directory in directories:
            if not directory.exists():
                logger.warning(f"Config directory does not exist: {directory}")
                continue
                
            observer = Observer()
            handler = ConfigChangeHandler(self)
            observer.schedule(handler, str(directory), recursive=True)
            observer.start()
            
            self._observers[str(directory)] = observer
            logger.info(f"Started watching config directory: {directory}")
    
    def stop_watching(self):
        """Stop all file watchers."""
        for observer in self._observers.values():
            observer.stop()
            observer.join()
        self._observers.clear()
        logger.info("Stopped all config watchers")
    
    def register_callback(self, pattern: str, callback: Callable[[Path], None]):
        """Register a callback for specific file patterns."""
        with self._lock:
            self._reload_callbacks[pattern] = callback
    
    def _reload_config_file(self, file_path: Path):
        """Reload a specific configuration file."""
        logger.info(f"Reloading config file: {file_path}")
        
        try:
            # Validate file can be loaded
            if file_path.suffix in {'.yaml', '.yml'}:
                with open(file_path, 'r') as f:
                    config_data = yaml.safe_load(f)
            elif file_path.suffix == '.json':
                with open(file_path, 'r') as f:
                    config_data = json.load(f)
            else:
                logger.warning(f"Unknown config file type: {file_path}")
                return
            
            # Find matching callback
            callback = self._find_callback(file_path)
            if callback:
                callback(file_path)
                logger.info(f"Successfully reloaded: {file_path}")
            else:
                logger.warning(f"No callback registered for: {file_path}")
                
        except Exception as e:
            logger.error(f"Failed to reload {file_path}: {e}")
            # Could implement validation rollback here
    
    def _find_callback(self, file_path: Path) -> Optional[Callable]:
        """Find appropriate callback for file path."""
        with self._lock:
            file_name = file_path.name
            
            # Exact match
            if file_name in self._reload_callbacks:
                return self._reload_callbacks[file_name]
            
            # Pattern match
            for pattern, callback in self._reload_callbacks.items():
                if '*' in pattern:
                    import fnmatch
                    if fnmatch.fnmatch(str(file_path), pattern):
                        return callback
            
            return None
    
    def _reload_agents_config(self, file_path: Path):
        """Reload agents configuration."""
        try:
            with open(file_path, 'r') as f:
                agents_config = yaml.safe_load(f)
            
            logger.info(f"Reloaded {len(agents_config.get('agents', {}))} agent configurations")
            
            # Notify registry if callback provided
            if self.registry_callback:
                self.registry_callback('agents', agents_config)
                
        except Exception as e:
            logger.error(f"Failed to reload agents config: {e}")
    
    def _reload_workflows_config(self, file_path: Path):
        """Reload workflows configuration."""
        try:
            with open(file_path, 'r') as f:
                workflows_config = yaml.safe_load(f)
            
            logger.info(f"Reloaded {len(workflows_config.get('workflows', {}))} workflow configurations")
            
            if self.registry_callback:
                self.registry_callback('workflows', workflows_config)
                
        except Exception as e:
            logger.error(f"Failed to reload workflows config: {e}")
    
    def _reload_policies_config(self, file_path: Path):
        """Reload policy configuration."""
        try:
            with open(file_path, 'r') as f:
                policy_config = json.load(f)
            
            logger.info(f"Reloaded policy: {file_path.stem}")
            
            if self.registry_callback:
                self.registry_callback('policy', {file_path.stem: policy_config})
                
        except Exception as e:
            logger.error(f"Failed to reload policy config: {e}")
    
    def _reload_models_config(self, file_path: Path):
        """Reload models configuration."""
        try:
            with open(file_path, 'r') as f:
                models_config = yaml.safe_load(f)
            
            logger.info("Reloaded models configuration")
            
            if self.registry_callback:
                self.registry_callback('models', models_config)
                
        except Exception as e:
            logger.error(f"Failed to reload models config: {e}")
    
    def _reload_cache_config(self, file_path: Path):
        """Reload cache configuration."""
        try:
            with open(file_path, 'r') as f:
                cache_config = yaml.safe_load(f)
            
            logger.info("Reloaded cache configuration")
            
            if self.registry_callback:
                self.registry_callback('cache', cache_config)
                
        except Exception as e:
            logger.error(f"Failed to reload cache config: {e}")
    
    def force_reload_all(self):
        """Force reload all configuration files."""
        logger.info("Force reloading all configurations")
        
        config_files = []
        for suffix in ['.yaml', '.yml', '.json']:
            config_files.extend(self.config_dir.rglob(f"*{suffix}"))
        
        for config_file in config_files:
            try:
                self._reload_config_file(config_file)
            except Exception as e:
                logger.error(f"Failed to force reload {config_file}: {e}")
    
    def get_config_status(self) -> Dict[str, Any]:
        """Get status of all watched configurations."""
        status = {
            "watching_directories": list(self._observers.keys()),
            "registered_callbacks": list(self._reload_callbacks.keys()),
            "loaded_configs": len(self._loaded_configs),
            "last_reload": datetime.now().isoformat()
        }
        return status


# Integration with existing Config class
class HotReloadableConfig:
    """Wrapper for Config class to support hot-reloading."""
    
    def __init__(self, base_config, config_dir: Path):
        self.base_config = base_config
        self.hot_reload_manager = HotReloadManager(
            config_dir, 
            self._handle_config_reload
        )
        self._lock = threading.RLock()
    
    def _handle_config_reload(self, config_type: str, config_data: Dict[str, Any]):
        """Handle configuration reload events."""
        with self._lock:
            try:
                if config_type == 'agents':
                    self._reload_agents(config_data)
                elif config_type == 'workflows':
                    self._reload_workflows(config_data)
                elif config_type == 'models':
                    self._reload_models(config_data)
                elif config_type == 'cache':
                    self._reload_cache(config_data)
                elif config_type == 'policy':
                    self._reload_policies(config_data)
                    
                logger.info(f"Applied hot-reload for {config_type}")
                
            except Exception as e:
                logger.error(f"Failed to apply hot-reload for {config_type}: {e}")
    
    def _reload_agents(self, agents_config: Dict[str, Any]):
        """Apply agents configuration changes."""
        # Update agent-related config attributes
        if hasattr(self.base_config, 'agent_timeout'):
            self.base_config.agent_timeout = agents_config.get('default_timeout', 30)
        
        # Could trigger agent re-registration here
        logger.info("Applied agents configuration hot-reload")
    
    def _reload_workflows(self, workflows_config: Dict[str, Any]):
        """Apply workflows configuration changes."""
        # Update workflow-related attributes
        if hasattr(self.base_config, 'workflow'):
            # Re-parse workflow manifest
            logger.info("Applied workflows configuration hot-reload")
    
    def _reload_models(self, models_config: Dict[str, Any]):
        """Apply models configuration changes."""
        # Update model configurations
        model_mapping = models_config.get('agent_model_mapping', {})
        for agent_id, model_name in model_mapping.items():
            logger.info(f"Updated model for {agent_id}: {model_name}")
    
    def _reload_cache(self, cache_config: Dict[str, Any]):
        """Apply cache configuration changes."""
        # Update cache settings
        if 'ttl_defaults' in cache_config:
            logger.info("Updated cache TTL settings")
    
    def _reload_policies(self, policies_config: Dict[str, Any]):
        """Apply policy configuration changes."""
        # Update policy settings
        for policy_name, policy_data in policies_config.items():
            logger.info(f"Updated policy: {policy_name}")
    
    def start_hot_reload(self):
        """Start hot-reload monitoring."""
        self.hot_reload_manager.start_watching()
    
    def stop_hot_reload(self):
        """Stop hot-reload monitoring."""
        self.hot_reload_manager.stop_watching()
    
    def __getattr__(self, name):
        """Delegate attribute access to base config."""
        return getattr(self.base_config, name)