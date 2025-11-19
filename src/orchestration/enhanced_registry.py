# enhanced_registry.py
"""Enhanced agent registry with auto-discovery and MCP compliance.

Automatically discovers agents from existing codebase and maintains MCP contracts.
"""

import ast
import inspect
import importlib
import logging
from typing import Dict, List, Optional, Any, Type, Set
from pathlib import Path
import threading
import json
import time
from datetime import datetime, timezone

from src.mcp import MCPContract, MCPComplianceAdapter
from .hot_reload import HotReloadMonitor
from .checkpoint_manager import CheckpointManager
from src.core import Agent
from .agent_scanner import AgentScanner, AgentMetadata
from .dependency_resolver import DependencyResolver

logger = logging.getLogger(__name__)


class AgentDiscovery:
    """Discovers agents from Python modules and files."""
    
    def __init__(self, search_paths: List[Path]):
        self.search_paths = search_paths
        self._discovered_agents: Dict[str, Dict[str, Any]] = {}
    
    def discover_agents(self) -> List[Dict[str, Any]]:
        """Discover all agent classes in search paths."""
        discovered = []
        
        for search_path in self.search_paths:
            if search_path.is_file() and search_path.suffix == '.py':
                discovered.extend(self._discover_in_file(search_path))
            elif search_path.is_dir():
                for py_file in search_path.rglob("*.py"):
                    if not py_file.name.startswith("_"):
                        discovered.extend(self._discover_in_file(py_file))
        
        self._discovered_agents = {agent['class_name']: agent for agent in discovered}
        logger.info(f"Discovered {len(discovered)} agent classes")
        return discovered
    
    def _discover_in_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Discover agents in a specific Python file."""
        agents = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to find agent classes
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    agent_info = self._analyze_class_node(node, file_path)
                    if agent_info:
                        agents.append(agent_info)
        
        except Exception as e:
            logger.error(f"Failed to discover agents in {file_path}: {e}")
        
        return agents
    
    def _analyze_class_node(self, node: ast.ClassDef, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze a class node to determine if it's an agent."""
        # Check if class inherits from Agent
        is_agent = False
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'Agent':
                is_agent = True
                break
            elif isinstance(base, ast.Attribute) and base.attr == 'Agent':
                is_agent = True
                break
        
        if not is_agent:
            return None
        
        # Extract agent information
        agent_info = {
            'class_name': node.name,
            'file_path': str(file_path),
            'module_path': self._get_module_path(file_path),
            'capabilities': [],
            'contract_method': None,
            'subscribe_method': None,
            'dependencies': []
        }
        
        # Analyze methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name == '_create_contract':
                    agent_info['contract_method'] = True
                elif item.name == '_subscribe_to_events':
                    agent_info['subscribe_method'] = True
                elif item.name == '__init__':
                    agent_info['dependencies'] = self._extract_init_dependencies(item)
        
        # Extract capabilities from docstring or methods
        docstring = ast.get_docstring(node)
        if docstring:
            agent_info['description'] = docstring.split('\n')[0]
        
        return agent_info
    
    def _get_module_path(self, file_path: Path) -> str:
        """Convert file path to Python module path."""
        # Remove .py extension and convert path separators to dots
        try:
            relative_path = file_path.relative_to(Path.cwd())
        except ValueError:
            relative_path = file_path
        module_path = str(relative_path.with_suffix(''))
        return module_path.replace('/', '.').replace('\\', '.')
    
    def _extract_init_dependencies(self, init_node: ast.FunctionDef) -> List[str]:
        """Extract dependencies from __init__ method."""
        dependencies = []
        
        for arg in init_node.args.args[1:]:  # Skip 'self'
            if arg.arg in ['llm_service', 'database_service', 'embedding_service', 
                          'gist_service', 'trends_service', 'link_checker']:
                dependencies.append(arg.arg)
        
        return dependencies


class EnhancedAgentRegistry:
    """Enhanced registry with MCP compliance and auto-discovery."""

    def __init__(self, config_dir: Path = Path("./config")):
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Enhanced components
        self.mcp_adapter = MCPComplianceAdapter(config_dir)
        self.hot_reload_manager = HotReloadMonitor([config_dir], self._handle_config_reload)
        self.checkpoint_manager = CheckpointManager(config_dir / "checkpoints")

        # Add AgentScanner and DependencyResolver
        self.agents_dir = Path("src/agents")
        self.scanner = AgentScanner()
        self.dependency_resolver = DependencyResolver()

        # Update AgentDiscovery to search in src/agents directory
        self.agent_discovery = AgentDiscovery([self.agents_dir] if self.agents_dir.exists() else [])

        # Registry state
        self.agents: Dict[str, Dict[str, Any]] = {}  # Simple agent registry
        self._agent_classes: Dict[str, type] = {}
        self._agent_metadata: Dict[str, AgentMetadata] = {}
        self._mcp_contracts: Dict[str, MCPContract] = {}
        self._agent_instances: Dict[str, Agent] = {}
        self._discovery_cache: Dict[str, Dict[str, Any]] = {}
        self._last_discovery: Optional[datetime] = None

        # Configuration
        self._auto_discovery_enabled = True
        self._auto_reload_enabled = True

        self._lock = threading.RLock()

        # Auto-discover agents on initialization
        self._discover_agents()
        self.discover_agents()
    
    def _discover_agents(self):
        """Auto-discover agents from src/agents directory."""
        agents_dir = Path("src/agents")
        
        if not agents_dir.exists():
            logger.warning(f"Agents directory {agents_dir} not found")
            return
        
        discovered_count = 0
        
        # Use rglob to find files in subdirectories too
        for agent_file in agents_dir.rglob("*.py"):
            # Skip __init__.py and base.py
            if agent_file.name in ["__init__.py", "base.py"]:
                continue
                
            # Extract agent name from filename (remove .py)
            agent_name = agent_file.stem
            
            if agent_name not in self.agents:
                # Create default agent entry
                self.agents[agent_name] = {
                    'id': agent_name,
                    'name': agent_name.replace('_', ' ').title(),
                    'type': 'workflow_agent',
                    'status': 'available',
                    'file': str(agent_file)
                }
                
                # Create MCP contract
                try:
                    contract = self.mcp_adapter.create_default_contract(
                        agent_id=agent_name,
                        agent_type="workflow_agent"
                    )
                    self._mcp_contracts[agent_name] = contract
                except Exception as e:
                    logger.warning(f"Failed to create contract for {agent_name}: {e}")
                
                discovered_count += 1
        
        logger.info(f"Discovered {discovered_count} agents from {agents_dir}")
    def get_all_agents(self) -> Dict[str, Any]:
        """Get all registered agents."""
        with self._lock:
            # Return as dict mapping agent_id to metadata
            return {name: metadata for name, metadata in self._agent_metadata.items()}
    
    def start_enhanced_registry(self):
        """Start enhanced registry features."""
        logger.info("Starting enhanced agent registry")
        
        # Perform AST-based discovery if enabled
        if self._auto_discovery_enabled:
            self.discover_and_register_agents()
        
        # Start hot-reload if enabled
        if self._auto_reload_enabled:
            self.hot_reload_manager.start_watching([Path("./"), self.config_dir])
        
        # Generate agents.yaml if it doesn't exist
        self._generate_agents_config()
        
        logger.info("Enhanced registry started successfully")
    
    def discover_and_register_agents(self) -> List[str]:
        """Discover agents using AST and register them with MCP contracts."""
        with self._lock:
            discovered_agents = self.agent_discovery.discover_agents()
            registered_ids = []
            
            for agent_info in discovered_agents:
                try:
                    # Import and instantiate agent class
                    agent_class = self._import_agent_class(agent_info)
                    if agent_class:
                        # Register with MCP compliance
                        agent_id = agent_info['class_name']
                        self._discovery_cache[agent_id] = agent_info
                        
                        # Update simple registry
                        if agent_id not in self.agents:
                            self.agents[agent_id] = {
                                'id': agent_id,
                                'name': agent_id.replace('_', ' ').title(),
                                'type': 'discovered_agent',
                                'status': 'available',
                                'class': agent_info['class_name'],
                                'module': agent_info['module_path']
                            }
                        
                        registered_ids.append(agent_id)
                        logger.info(f"Discovered and cached agent: {agent_id}")
                
                except Exception as e:
                    logger.error(f"Failed to process discovered agent {agent_info['class_name']}: {e}")
            
            self._last_discovery = datetime.now()
            return registered_ids
    
    def register_agent_instance(self, agent: Agent, auto_enhance: bool = True) -> MCPContract:
        """Register a live agent instance with MCP compliance."""
        with self._lock:
            # Create MCP contract
            mcp_contract = self.mcp_adapter.create_default_contract(
                agent_id=agent.agent_id,
                agent_type="instance_agent"
            )
            self._mcp_contracts[agent.agent_id] = mcp_contract
            self._agent_instances[agent.agent_id] = agent

            # Setup checkpoint integration
            self._integrate_agent_with_checkpoints(agent)

            logger.info(f"Registered agent instance with MCP: {agent.agent_id}")
            return mcp_contract
    
    def get_mcp_contract(self, agent_id: str) -> Optional[MCPContract]:
        """Get MCP contract for an agent."""
        with self._lock:
            return self._mcp_contracts.get(agent_id)
    
    def list_mcp_contracts(self) -> List[MCPContract]:
        """List all MCP contracts."""
        with self._lock:
            return list(self._mcp_contracts.values())
    
    def validate_all_contracts(self) -> Dict[str, List[str]]:
        """Validate all MCP contracts."""
        validation_results = {}
        
        with self._lock:
            for agent_id, contract in self._mcp_contracts.items():
                errors = contract.validate()
                if errors:
                    validation_results[agent_id] = errors
        
        return validation_results
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get comprehensive registry status."""
        with self._lock:
            return {
                "total_agents": len(self.agents),
                "mcp_compliant_agents": len(self._mcp_contracts),
                "discovered_agents": len(self._discovery_cache),
                "agent_instances": len(self._agent_instances),
                "last_discovery": self._last_discovery.isoformat() if self._last_discovery else None,
                "auto_discovery_enabled": self._auto_discovery_enabled,
                "auto_reload_enabled": self._auto_reload_enabled,
                "config_watchers": self.hot_reload_manager.get_config_status() if hasattr(self.hot_reload_manager, 'get_config_status') else {},
                "checkpoint_executions": len(self.checkpoint_manager.list_executions())
            }
    
    def force_rediscovery(self):
        """Force rediscovery of all agents."""
        logger.info("Forcing agent rediscovery")
        self._discover_agents()
        self.discover_and_register_agents()
        self._generate_agents_config()
    
    def _import_agent_class(self, agent_info: Dict[str, Any]) -> Optional[Type[Agent]]:
        """Import agent class from module path."""
        try:
            module = importlib.import_module(agent_info['module_path'])
            agent_class = getattr(module, agent_info['class_name'])
            
            # Verify it's a proper Agent subclass
            if inspect.isclass(agent_class) and issubclass(agent_class, Agent):
                return agent_class
            
        except Exception as e:
            logger.error(f"Failed to import {agent_info['class_name']}: {e}")
        
        return None
    
    def _integrate_agent_with_checkpoints(self, agent: Agent):
        """Integrate agent with checkpoint management."""
        # Add checkpoint awareness to agent execution
        if hasattr(agent, 'execute'):
            original_execute = agent.execute
            
            def checkpoint_aware_execute(event):
                """Execute with checkpoint integration."""
                # Create pre-execution checkpoint for critical operations
                critical_capabilities = ["write_file", "upload_gist", "generate_seo"]
                capability = event.event_type.replace("execute_", "")
                
                if capability in critical_capabilities:
                    try:
                        execution_id = f"exec_{event.correlation_id}"
                        checkpoint = self.checkpoint_manager.create_checkpoint(
                            execution_id=execution_id,
                            checkpoint_name=f"pre_{capability}",
                            agent_id=agent.agent_id,
                            input_data=event.data,
                            approval_required=True
                        )
                        
                        # Execute original
                        result = original_execute(event)
                        
                        # Complete checkpoint
                        self.checkpoint_manager.complete_checkpoint(
                            execution_id=execution_id,
                            checkpoint_name=f"pre_{capability}",
                            output_data=result.data if result else {},
                            success=True
                        )
                        
                        return result
                        
                    except Exception as e:
                        # Handle checkpoint failure
                        logger.error(f"Checkpoint-aware execution failed: {e}")
                        raise
                else:
                    return original_execute(event)
            
            agent.execute = checkpoint_aware_execute
    
    def _handle_config_reload(self, config_type: str, config_data: Dict[str, Any]):
        """Handle configuration reload events."""
        logger.info(f"Handling config reload: {config_type}")
        
        if config_type == 'agents':
            # Re-validate contracts after agent config changes
            validation_results = self.validate_all_contracts()
            if validation_results:
                logger.warning(f"Contract validation issues after reload: {validation_results}")
        
        elif config_type == 'workflows':
            # Update checkpoint manager with new workflow definitions
            logger.info("Updated workflow configurations")
    
    def _generate_agents_config(self):
        """Generate agents.yaml from discovered agents."""
        agents_config = {
            'agents': {},
            'discovery': {
                'last_run': datetime.now().isoformat(),
                'auto_discovery_enabled': self._auto_discovery_enabled
            }
        }
        
        # Add discovered agents
        for agent_id, agent_info in self.agents.items():
            contract = self._mcp_contracts.get(agent_id)
            
            agents_config['agents'][agent_id] = {
                'id': agent_id,
                'name': agent_info.get('name', agent_id),
                'type': agent_info.get('type', 'unknown'),
                'status': agent_info.get('status', 'unknown'),
                'mcp_compliant': agent_id in self._mcp_contracts,
                'auto_discovered': True
            }
        
        # Save to file
        config_file = self.config_dir / "agents.yaml"
        try:
            import yaml
            with open(config_file, 'w') as f:
                yaml.dump(agents_config, f, indent=2, default_flow_style=False)
            
            logger.info(f"Generated agents.yaml with {len(agents_config['agents'])} agents")
            
        except Exception as e:
            logger.error(f"Failed to generate agents.yaml: {e}")
    
    def export_mcp_registry(self) -> Dict[str, Any]:
        """Export complete MCP registry."""
        with self._lock:
            registry = {
                'version': '1.0',
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'agents': {}
            }
            
            for agent_id, contract in self._mcp_contracts.items():
                registry['agents'][agent_id] = contract.to_dict()
            
            return registry
    
    def stop_enhanced_registry(self):
        """Stop enhanced registry features."""
        logger.info("Stopping enhanced agent registry")

        if self._auto_reload_enabled:
            self.hot_reload_manager.stop_watching()

        # Cleanup checkpoint manager
        self.checkpoint_manager.cleanup_old_executions()

        logger.info("Enhanced registry stopped")

    def discover_agents(self) -> int:
        """Discover agents using the scanner.

        Returns:
            Count of discovered agents
        """
        with self._lock:
            # Use scanner to discover agents
            agents = self.scanner.discover(force_rescan=True)
            metadata = self.scanner.get_all_metadata()

            # Update internal state
            self._agent_metadata = metadata
            self._agent_classes = {name: None for name in metadata.keys()}

            # Add dependencies to resolver
            for name, meta in metadata.items():
                self.dependency_resolver.add_agent(name, meta.dependencies)

            return len(self._agent_classes)

    def get_agent(self, name: str, config: Optional[Any] = None, event_bus: Optional[Any] = None,
                  instantiate: bool = True) -> Optional[Any]:
        """Get agent class or instance.

        Args:
            name: Agent name
            config: Configuration object (required for instantiation)
            event_bus: Event bus (required for instantiation)
            instantiate: Whether to instantiate the agent

        Returns:
            Agent instance if config/event_bus provided, None otherwise
        """
        with self._lock:
            # If already instantiated, return instance
            if name in self._agent_instances:
                return self._agent_instances[name]

            # If no config or event_bus, return None (can't instantiate)
            if config is None or event_bus is None:
                return None

            # Get agent class
            agent_class = self._agent_classes.get(name)
            if agent_class is None:
                return None

            # Instantiate if requested
            if instantiate:
                try:
                    metadata = self._agent_metadata.get(name)
                    if metadata and len(metadata.dependencies) == 0:
                        # Simple agent with no dependencies
                        instance = agent_class(config, event_bus)
                        self._agent_instances[name] = instance
                        return instance
                except Exception as e:
                    logger.error(f"Failed to instantiate {name}: {e}")
                    return None

            return agent_class

    def get_dependencies(self, agent_name: str) -> List[str]:
        """Get dependencies for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            List of dependency names
        """
        metadata = self._agent_metadata.get(agent_name)
        if metadata:
            return metadata.dependencies
        return []

    def agents_by_category(self, category: str) -> List[AgentMetadata]:
        """Get agents by category.

        Args:
            category: Category name

        Returns:
            List of AgentMetadata objects
        """
        return self.scanner.get_agents_by_category(category)

    def get_agent_metadata(self, agent_name: str) -> Optional[AgentMetadata]:
        """Get metadata for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            AgentMetadata or None
        """
        return self._agent_metadata.get(agent_name)

    def get_all_categories(self) -> List[str]:
        """Get all categories.

        Returns:
            List of category names
        """
        return self.scanner.get_all_categories()

    def validate_dependencies(self, workflow: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """Validate dependencies.

        Args:
            workflow: Optional list of agent names to validate

        Returns:
            Dictionary of validation issues
        """
        available = set(self._agent_classes.keys())
        return self.dependency_resolver.validate_dependencies(available)

    def detect_cycles(self, workflow: Optional[List[str]] = None) -> Optional[List[str]]:
        """Detect circular dependencies.

        Args:
            workflow: Optional list of agent names to check

        Returns:
            List of agents forming a cycle, or None
        """
        return self.dependency_resolver.detect_cycles()

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics.

        Returns:
            Dictionary of statistics
        """
        categories = self.get_all_categories()
        agents_by_cat = {
            cat: len(self.agents_by_category(cat))
            for cat in categories
        }

        return {
            "total_agents": len(self._agent_classes),
            "categories": len(categories),
            "instantiated_agents": len(self._agent_instances),
            "agents_by_category": agents_by_cat
        }

    def clear_instances(self) -> None:
        """Clear cached agent instances."""
        with self._lock:
            self._agent_instances.clear()

    def rescan(self) -> int:
        """Force a rescan of agents.

        Returns:
            Count of discovered agents
        """
        return self.discover_agents()


# REST API endpoints for registry management
class RegistryAPI:
    """REST API for enhanced registry management."""
    
    def __init__(self, registry: EnhancedAgentRegistry):
        self.registry = registry

    def get_agents(self) -> Dict[str, Any]:
        """GET /registry/agents - List all agents."""
        agents = self.registry.get_all_agents()
        return {
            'agents': agents,
            'total': len(agents)
        }

    def get_agent_contract(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """GET /registry/agents/{agent_id}/contract - Get agent contract."""
        contract = self.registry.get_mcp_contract(agent_id)
        return contract.to_dict() if contract else None

    def reload_registry(self) -> Dict[str, Any]:
        """POST /registry/reload - Force reload registry."""
        self.registry.force_rediscovery()
        return {"status": "reloaded", "timestamp": datetime.now().isoformat()}

    def validate_contracts(self) -> Dict[str, Any]:
        """POST /registry/validate - Validate all contracts."""
        validation_results = self.registry.validate_all_contracts()
        return {
            "validation_results": validation_results,
            "total_issues": sum(len(issues) for issues in validation_results.values())
        }

    def get_registry_status(self) -> Dict[str, Any]:
        """GET /registry/status - Get registry status."""
        return self.registry.get_registry_status()


# Singleton pattern for global registry access
_registry_instance: Optional[EnhancedAgentRegistry] = None
_registry_lock = threading.Lock()


def get_registry(config_dir: Optional[Path] = None) -> EnhancedAgentRegistry:
    """Get or create the global registry instance (singleton).

    Args:
        config_dir: Optional configuration directory path

    Returns:
        Global EnhancedAgentRegistry instance
    """
    global _registry_instance

    if _registry_instance is None:
        with _registry_lock:
            # Double-check locking pattern
            if _registry_instance is None:
                if config_dir is None:
                    config_dir = Path("config")
                _registry_instance = EnhancedAgentRegistry(config_dir)
                logger.info("Created global registry instance")

    return _registry_instance
