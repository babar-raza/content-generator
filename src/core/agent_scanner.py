"""Agent Scanner for dynamic agent discovery and loading."""

import importlib.util
import inspect
import logging
import time
from pathlib import Path
from typing import Dict, List, Type, Optional
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Base class for all agents."""
    
    name: str = ""
    description: str = ""
    
    @abstractmethod
    def execute(self, *args, **kwargs):
        """Execute the agent's main functionality."""
        pass


class AgentScanner:
    """Scans and loads agent modules dynamically."""
    
    def __init__(self, agents_dir: str = "src/agents"):
        """Initialize the agent scanner.
        
        Args:
            agents_dir: Directory containing agent modules
        """
        self.agents_dir = Path(agents_dir)
        self.logger = logging.getLogger(__name__)
        self._cache: Optional[Dict[str, Type[BaseAgent]]] = None
        self._agent_files: List[Path] = []
        self._cache_time: float = 0
    
    def _scan_directory(self) -> List[Path]:
        """Scan directory for Python files.
        
        Returns:
            List of Python file paths
        """
        python_files = []
        
        if not self.agents_dir.exists():
            self.logger.warning(f"Agents directory not found: {self.agents_dir}")
            return python_files
        
        # Recursively find all .py files
        for file_path in self.agents_dir.rglob("*.py"):
            if file_path.name.startswith("__"):
                continue
            python_files.append(file_path)
        
        return python_files
    
    def _extract_agents(self, module) -> List[Type[BaseAgent]]:
        """Extract BaseAgent subclasses from a module.
        
        Args:
            module: Python module to inspect
            
        Returns:
            List of agent classes
        """
        agents = []
        
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Check if it's a subclass of BaseAgent but not BaseAgent itself
            if issubclass(obj, BaseAgent) and obj is not BaseAgent:
                agents.append(obj)
        
        return agents
    
    def _scan_file(self, file_path: Path) -> List[Type[BaseAgent]]:
        """Scan a single file for agent classes.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            List of agent classes found
        """
        try:
            spec = importlib.util.spec_from_file_location("module", file_path)
            if spec is None or spec.loader is None:
                self.logger.warning(f"Failed to load spec for {file_path}")
                return []
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return self._extract_agents(module)
        except Exception as e:
            self.logger.warning(f"Failed to load {file_path}: {e}")
            return []
    
    def _validate_agent(self, agent_class: Type[BaseAgent]) -> bool:
        """Validate that an agent has required attributes.
        
        Args:
            agent_class: Agent class to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check for required attributes
        if not hasattr(agent_class, 'name') or not agent_class.name:
            self.logger.warning(f"Agent {agent_class.__name__} missing 'name' attribute")
            return False
        
        if not hasattr(agent_class, 'description') or not agent_class.description:
            self.logger.warning(f"Agent {agent_class.__name__} missing 'description' attribute")
            return False
        
        if not hasattr(agent_class, 'execute'):
            self.logger.warning(f"Agent {agent_class.__name__} missing 'execute' method")
            return False
        
        return True
    
    def _cache_stale(self) -> bool:
        """Check if cache is stale based on file modification times.
        
        Returns:
            True if cache should be invalidated, False otherwise
        """
        if not self._agent_files:
            return True
        
        for file_path in self._agent_files:
            try:
                if file_path.exists() and file_path.stat().st_mtime > self._cache_time:
                    return True
            except OSError:
                # File might have been deleted
                return True
        
        # Check if new files were added
        current_files = set(self._scan_directory())
        cached_files = set(self._agent_files)
        if current_files != cached_files:
            return True
        
        return False
    
    def scan(self) -> Dict[str, Type[BaseAgent]]:
        """Scan for all available agents.
        
        Returns:
            Dictionary mapping agent names to agent classes
        """
        # Check if cache is valid
        if self._cache and not self._cache_stale():
            return self._cache
        
        agents_dict = {}
        
        # Get all Python files
        self._agent_files = self._scan_directory()
        
        # Scan each file
        for file_path in self._agent_files:
            agent_classes = self._scan_file(file_path)
            
            for agent_class in agent_classes:
                # Validate agent structure
                if not self._validate_agent(agent_class):
                    continue
                
                # Add to dictionary
                agent_name = agent_class.name
                if agent_name in agents_dict:
                    self.logger.warning(
                        f"Duplicate agent name '{agent_name}': "
                        f"{agent_class.__name__} conflicts with "
                        f"{agents_dict[agent_name].__name__}"
                    )
                    continue
                
                agents_dict[agent_name] = agent_class
                self.logger.info(f"Loaded agent: {agent_name}")
        
        # Cache results
        self._cache = agents_dict
        self._cache_time = time.time()
        
        return agents_dict
    
    def get_agent(self, name: str) -> Optional[Type[BaseAgent]]:
        """Get a specific agent by name.
        
        Args:
            name: Agent name
            
        Returns:
            Agent class or None if not found
        """
        agents = self.scan()
        return agents.get(name)
    
    def list_agents(self) -> List[str]:
        """List all available agent names.
        
        Returns:
            List of agent names
        """
        agents = self.scan()
        return list(agents.keys())
    
    def reload(self) -> Dict[str, Type[BaseAgent]]:
        """Force reload of all agents.
        
        Returns:
            Dictionary mapping agent names to agent classes
        """
        self._cache = None
        return self.scan()
