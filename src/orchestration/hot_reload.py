"""Hot-reload configuration system for UCOP agents.

Monitors configuration files and reloads agents without system restart.
Thread-safe, debounced, with validation and rollback support.
"""

import hashlib
import json
import logging
import threading
import time
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


@dataclass
class ReloadEvent:
    """Event emitted when configuration is reloaded."""
    file_path: Path
    config_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error: Optional[str] = None
    changes_applied: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigSnapshot:
    """Snapshot of configuration for rollback."""
    file_path: Path
    content: Dict[str, Any]
    checksum: str
    timestamp: datetime = field(default_factory=datetime.now)


class ConfigValidator:
    """Validates configuration files before applying."""
    
    @staticmethod
    def validate_agents_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate agents configuration structure.
        
        Args:
            config: Agents configuration dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(config, dict):
            return False, "Config must be a dictionary"
        
        if 'agents' not in config:
            return False, "Missing 'agents' key in configuration"
        
        agents = config['agents']
        if not isinstance(agents, dict):
            return False, "'agents' must be a dictionary"
        
        # Validate each agent definition
        for agent_name, agent_def in agents.items():
            if not isinstance(agent_def, dict):
                return False, f"Agent '{agent_name}' definition must be a dictionary"
            
            # Check required fields
            if 'class' not in agent_def:
                return False, f"Agent '{agent_name}' missing 'class' field"
        
        return True, None
    
    @staticmethod
    def validate_workflows_config(config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate workflows configuration structure.
        
        Args:
            config: Workflows configuration dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(config, dict):
            return False, "Config must be a dictionary"
        
        if 'workflows' not in config:
            return False, "Missing 'workflows' key in configuration"
        
        workflows = config['workflows']
        if not isinstance(workflows, dict):
            return False, "'workflows' must be a dictionary"
        
        # Validate each workflow definition
        for workflow_name, workflow_def in workflows.items():
            if not isinstance(workflow_def, dict):
                return False, f"Workflow '{workflow_name}' definition must be a dictionary"
            
            # Check required fields
            if 'steps' not in workflow_def:
                return False, f"Workflow '{workflow_name}' missing 'steps' field"
            
            steps = workflow_def['steps']
            if not isinstance(steps, list):
                return False, f"Workflow '{workflow_name}' steps must be a list"
        
        return True, None


class ConfigChangeHandler(FileSystemEventHandler):
    """Handle configuration file changes with debouncing."""
    
    def __init__(self, hot_reload_monitor: 'HotReloadMonitor'):
        """Initialize change handler.
        
        Args:
            hot_reload_monitor: Parent monitor instance
        """
        self.monitor = hot_reload_monitor
        self.debounce_delay = 1.0  # 1 second debounce
        self._pending_changes: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._running = True
        
        # Start debounce processor thread
        self._debounce_thread = threading.Thread(
            target=self._process_pending_changes,
            daemon=True,
            name="ConfigDebounceThread"
        )
        self._debounce_thread.start()
    
    def on_modified(self, event) -> None:
        """Handle file modification events.
        
        Args:
            event: File system event
        """
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Only process YAML/JSON config files
        if file_path.suffix not in {'.yaml', '.yml', '.json'}:
            return
        
        # Check if file is in monitored paths
        if not self.monitor.is_monitored_file(file_path):
            return
        
        logger.info(f"Config file changed: {file_path}")
        
        with self._lock:
            self._pending_changes[str(file_path)] = time.time()
    
    def _process_pending_changes(self) -> None:
        """Process pending file changes with debouncing."""
        while self._running:
            time.sleep(0.1)  # Check every 100ms
            
            with self._lock:
                current_time = time.time()
                ready_files = []
                
                # Find files ready to process
                for file_path, change_time in list(self._pending_changes.items()):
                    if current_time - change_time >= self.debounce_delay:
                        ready_files.append(file_path)
                
                # Remove processed files from pending
                for file_path in ready_files:
                    del self._pending_changes[file_path]
            
            # Process ready files outside lock
            for file_path in ready_files:
                try:
                    self.monitor.reload_config_file(Path(file_path))
                except Exception as e:
                    logger.error(f"Failed to reload {file_path}: {e}", exc_info=True)
    
    def stop(self) -> None:
        """Stop the debounce processor thread."""
        self._running = False


class HotReloadMonitor:
    """Monitors and hot-reloads configuration files with validation and rollback.
    
    Features:
    - File watching with watchdog
    - 1-second debouncing
    - Validation before applying
    - Automatic rollback on errors
    - Thread-safe operations
    - Event bus notifications
    """
    
    def __init__(
        self,
        paths: List[Path],
        callback: Optional[Callable[[ReloadEvent], None]] = None,
        event_bus: Optional[Any] = None
    ):
        """Initialize hot reload monitor.
        
        Args:
            paths: List of file paths to monitor
            callback: Optional callback for reload events
            event_bus: Optional event bus for notifications
        """
        self.paths = [Path(p) for p in paths]
        self.callback = callback
        self.event_bus = event_bus
        
        self._observers: List[Observer] = []
        self._handler: Optional[ConfigChangeHandler] = None
        self._lock = threading.RLock()
        self._running = False
        
        # Configuration snapshots for rollback
        self._snapshots: Dict[str, ConfigSnapshot] = {}
        
        # Track last successful loads
        self._last_checksums: Dict[str, str] = {}
        
        # Reload callbacks by file pattern
        self._reload_callbacks: Dict[str, Callable[[Path, Dict[str, Any]], None]] = {}
        
        # Statistics
        self._reload_count = 0
        self._failed_reloads = 0
        self._last_reload_time: Optional[datetime] = None
        
        logger.info(f"HotReloadMonitor initialized for {len(self.paths)} paths")
    
    def register_callback(
        self,
        pattern: str,
        callback: Callable[[Path, Dict[str, Any]], None]
    ) -> None:
        """Register a callback for specific file patterns.
        
        Args:
            pattern: File pattern (e.g., 'agents.yaml', '*.json')
            callback: Callback function(path, config_data)
        """
        with self._lock:
            self._reload_callbacks[pattern] = callback
            logger.debug(f"Registered reload callback for pattern: {pattern}")
    
    def register_reload_callback(
        self,
        pattern: str,
        callback: Callable[[Path, Dict[str, Any]], None]
    ) -> None:
        """Alias for register_callback for backward compatibility.
        
        Args:
            pattern: File pattern (e.g., 'agents.yaml', '*.json')
            callback: Callback function(path, config_data)
        """
        self.register_callback(pattern, callback)
    
    def is_monitored_file(self, file_path: Path) -> bool:
        """Check if a file is being monitored.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file is monitored
        """
        file_path = file_path.resolve()
        for path in self.paths:
            path = path.resolve()
            if file_path == path or path.is_dir() and file_path.is_relative_to(path):
                return True
        return False
    
    def start(self) -> None:
        """Start watching configuration files."""
        with self._lock:
            if self._running:
                logger.warning("HotReloadMonitor already running")
                return
            
            # Create file system event handler
            self._handler = ConfigChangeHandler(self)
            
            # Setup observers for all paths
            monitored_dirs = set()
            for path in self.paths:
                if path.is_file():
                    watch_dir = path.parent
                elif path.is_dir():
                    watch_dir = path
                else:
                    logger.warning(f"Path does not exist: {path}")
                    continue
                
                if watch_dir in monitored_dirs:
                    continue
                
                observer = Observer()
                observer.schedule(self._handler, str(watch_dir), recursive=False)
                observer.start()
                
                self._observers.append(observer)
                monitored_dirs.add(watch_dir)
                logger.info(f"Started watching directory: {watch_dir}")
            
            self._running = True
            
            # Create initial snapshots
            for path in self.paths:
                if path.is_file():
                    try:
                        self._create_snapshot(path)
                    except Exception as e:
                        logger.warning(f"Failed to create initial snapshot for {path}: {e}")
            
            logger.info("HotReloadMonitor started successfully")
    
    def stop(self) -> None:
        """Stop watching configuration files."""
        with self._lock:
            if not self._running:
                return
            
            # Stop handler thread
            if self._handler:
                self._handler.stop()
            
            # Stop all observers
            for observer in self._observers:
                observer.stop()
            
            # Wait for observers to finish
            for observer in self._observers:
                observer.join(timeout=2.0)
            
            self._observers.clear()
            self._running = False
            
            logger.info("HotReloadMonitor stopped")
    
    def _compute_checksum(self, file_path: Path) -> str:
        """Compute checksum of file content.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA256 checksum hex string
        """
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def _create_snapshot(self, file_path: Path) -> ConfigSnapshot:
        """Create configuration snapshot for rollback.
        
        Args:
            file_path: Path to config file
            
        Returns:
            Configuration snapshot
        """
        config_data = self._load_config_file(file_path)
        checksum = self._compute_checksum(file_path)
        
        snapshot = ConfigSnapshot(
            file_path=file_path,
            content=deepcopy(config_data),
            checksum=checksum
        )
        
        with self._lock:
            self._snapshots[str(file_path)] = snapshot
        
        return snapshot
    
    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration file.
        
        Args:
            file_path: Path to config file
            
        Returns:
            Configuration dictionary
            
        Raises:
            ValueError: If file format is unsupported
            yaml.YAMLError: If YAML parsing fails
            json.JSONDecodeError: If JSON parsing fails
        """
        if file_path.suffix in {'.yaml', '.yml'}:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        elif file_path.suffix == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")
    
    def _validate_config(self, file_path: Path, config_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate configuration data.
        
        Args:
            file_path: Path to config file
            config_data: Configuration dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        file_name = file_path.name.lower()
        
        if 'agents.yaml' in file_name or 'agent' in file_name:
            return ConfigValidator.validate_agents_config(config_data)
        elif 'workflow' in file_name:
            return ConfigValidator.validate_workflows_config(config_data)
        else:
            # Generic validation - just check it's a dict
            if not isinstance(config_data, dict):
                return False, "Configuration must be a dictionary"
            return True, None
    
    def _rollback_config(self, file_path: Path) -> bool:
        """Rollback configuration to last known good state.
        
        Args:
            file_path: Path to config file
            
        Returns:
            True if rollback successful
        """
        snapshot_key = str(file_path)
        
        with self._lock:
            if snapshot_key not in self._snapshots:
                logger.error(f"No snapshot available for rollback: {file_path}")
                return False
            
            snapshot = self._snapshots[snapshot_key]
        
        try:
            logger.warning(f"Rolling back configuration: {file_path}")
            
            # Write snapshot content back to file
            if file_path.suffix in {'.yaml', '.yml'}:
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(snapshot.content, f, default_flow_style=False)
            elif file_path.suffix == '.json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(snapshot.content, f, indent=2)
            
            logger.info(f"Rollback successful: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed for {file_path}: {e}", exc_info=True)
            return False
    
    def _find_reload_callback(self, file_path: Path) -> Optional[Callable]:
        """Find appropriate reload callback for file.
        
        Args:
            file_path: Path to config file
            
        Returns:
            Callback function or None
        """
        with self._lock:
            file_name = file_path.name
            
            # Exact match
            if file_name in self._reload_callbacks:
                return self._reload_callbacks[file_name]
            
            # Pattern match
            import fnmatch
            for pattern, callback in self._reload_callbacks.items():
                if fnmatch.fnmatch(file_name, pattern):
                    return callback
                if fnmatch.fnmatch(str(file_path), pattern):
                    return callback
            
            return None
    
    def reload_config_file(self, file_path: Path) -> bool:
        """Reload a specific configuration file with validation and rollback.
        
        Args:
            file_path: Path to config file
            
        Returns:
            True if reload successful
        """
        start_time = time.time()
        event = ReloadEvent(
            file_path=file_path,
            config_type=self._get_config_type(file_path)
        )
        
        try:
            # Check if file has actually changed
            new_checksum = self._compute_checksum(file_path)
            
            with self._lock:
                old_checksum = self._last_checksums.get(str(file_path))
            
            if old_checksum == new_checksum:
                logger.debug(f"No changes detected in {file_path}, skipping reload")
                return True
            
            logger.info(f"Reloading configuration: {file_path}")
            
            # Load new configuration
            try:
                config_data = self._load_config_file(file_path)
            except Exception as e:
                raise ValueError(f"Failed to load config file: {e}") from e
            
            # Validate new configuration
            is_valid, error_msg = self._validate_config(file_path, config_data)
            if not is_valid:
                raise ValueError(f"Validation failed: {error_msg}")
            
            # Find and execute reload callback
            callback = self._find_reload_callback(file_path)
            if callback:
                try:
                    callback(file_path, config_data)
                    event.changes_applied['callback_executed'] = True
                except Exception as e:
                    raise RuntimeError(f"Callback execution failed: {e}") from e
            else:
                logger.warning(f"No reload callback registered for: {file_path}")
            
            # Update snapshot and checksum
            self._create_snapshot(file_path)
            
            with self._lock:
                self._last_checksums[str(file_path)] = new_checksum
                self._reload_count += 1
                self._last_reload_time = datetime.now()
            
            # Notify via event bus
            if self.event_bus:
                try:
                    from src.core.contracts import AgentEvent
                    reload_event = AgentEvent(
                        event_type="config.reloaded",
                        source_agent="hot_reload_monitor",
                        correlation_id="hot_reload",
                        data={
                            "file_path": str(file_path),
                            "config_type": event.config_type,
                            "reload_time": time.time() - start_time
                        }
                    )
                    self.event_bus.publish(reload_event)
                except Exception as e:
                    logger.warning(f"Failed to publish reload event: {e}")
            
            # Execute user callback
            if self.callback:
                try:
                    self.callback(event)
                except Exception as e:
                    logger.error(f"User callback failed: {e}", exc_info=True)
            
            logger.info(f"Successfully reloaded {file_path} in {time.time() - start_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload {file_path}: {e}", exc_info=True)
            
            # Update event with error
            event.success = False
            event.error = str(e)
            
            with self._lock:
                self._failed_reloads += 1
            
            # Attempt rollback
            rollback_success = self._rollback_config(file_path)
            if rollback_success:
                event.changes_applied['rollback'] = True
                logger.info(f"Configuration rolled back successfully: {file_path}")
            else:
                logger.error(f"Rollback failed: {file_path}")
            
            # Notify via event bus even on failure
            if self.event_bus:
                try:
                    from src.core.contracts import AgentEvent
                    error_event = AgentEvent(
                        event_type="config.reload_failed",
                        source_agent="hot_reload_monitor",
                        correlation_id="hot_reload",
                        data={
                            "file_path": str(file_path),
                            "error": str(e),
                            "rollback_success": rollback_success
                        }
                    )
                    self.event_bus.publish(error_event)
                except Exception as eb_error:
                    logger.warning(f"Failed to publish error event: {eb_error}")
            
            # Execute user callback with error
            if self.callback:
                try:
                    self.callback(event)
                except Exception as cb_error:
                    logger.error(f"User callback failed: {cb_error}", exc_info=True)
            
            return False
    
    def _get_config_type(self, file_path: Path) -> str:
        """Determine configuration type from file path.
        
        Args:
            file_path: Path to config file
            
        Returns:
            Configuration type string
        """
        file_name = file_path.name.lower()
        
        if 'agent' in file_name:
            return 'agents'
        elif 'workflow' in file_name:
            return 'workflows'
        elif 'model' in file_name:
            return 'models'
        elif 'policy' in file_name or 'policies' in file_name:
            return 'policies'
        elif 'cache' in file_name:
            return 'cache'
        else:
            return 'unknown'
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reload statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            return {
                'running': self._running,
                'monitored_paths': [str(p) for p in self.paths],
                'total_reloads': self._reload_count,
                'failed_reloads': self._failed_reloads,
                'success_rate': (
                    (self._reload_count - self._failed_reloads) / self._reload_count * 100
                    if self._reload_count > 0 else 100.0
                ),
                'last_reload_time': (
                    self._last_reload_time.isoformat()
                    if self._last_reload_time else None
                ),
                'snapshots': len(self._snapshots),
                'registered_callbacks': len(self._reload_callbacks)
            }
    
    def force_reload(self, file_path: Optional[Path] = None) -> None:
        """Force reload of configuration files.
        
        Args:
            file_path: Optional specific file to reload, or None for all
        """
        if file_path:
            files_to_reload = [file_path]
        else:
            files_to_reload = [p for p in self.paths if p.is_file()]
        
        logger.info(f"Force reloading {len(files_to_reload)} configuration files")
        
        for file in files_to_reload:
            try:
                self.reload_config_file(file)
            except Exception as e:
                logger.error(f"Failed to force reload {file}: {e}", exc_info=True)

__all__ = ['HotReloadMonitor', 'ReloadEvent', 'ConfigSnapshot', 'ConfigValidator']
