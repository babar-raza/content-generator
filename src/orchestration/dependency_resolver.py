"""Dependency Resolver - Topological sorting for agent dependencies."""

import logging
from typing import Dict, List, Set, Optional
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class DependencyResolver:
    """Resolves agent dependencies using topological sort."""
    
    def __init__(self):
        """Initialize dependency resolver."""
        self._dependency_graph: Dict[str, List[str]] = defaultdict(list)
        self._reverse_graph: Dict[str, List[str]] = defaultdict(list)
        
    def add_dependency(self, agent_name: str, depends_on: str) -> None:
        """Add a dependency relationship.
        
        Args:
            agent_name: Name of the agent
            depends_on: Name of agent that agent_name depends on
        """
        if depends_on not in self._dependency_graph[agent_name]:
            self._dependency_graph[agent_name].append(depends_on)
        if agent_name not in self._reverse_graph[depends_on]:
            self._reverse_graph[depends_on].append(agent_name)
    
    def add_agent(self, agent_name: str, dependencies: List[str]) -> None:
        """Add an agent with its dependencies.
        
        Args:
            agent_name: Name of the agent
            dependencies: List of agent names this agent depends on
        """
        for dep in dependencies:
            self.add_dependency(agent_name, dep)
    
    def get_dependencies(self, agent_name: str) -> List[str]:
        """Get direct dependencies for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of agent names that agent_name directly depends on
        """
        return self._dependency_graph.get(agent_name, []).copy()
    
    def get_all_dependencies(self, agent_name: str) -> Set[str]:
        """Get all transitive dependencies for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Set of all agent names in dependency tree
        """
        visited = set()
        stack = [agent_name]
        
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            
            visited.add(current)
            deps = self._dependency_graph.get(current, [])
            stack.extend(deps)
        
        # Remove the agent itself from the result
        visited.discard(agent_name)
        return visited
    
    def get_dependents(self, agent_name: str) -> List[str]:
        """Get agents that depend on the given agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of agent names that depend on agent_name
        """
        return self._reverse_graph.get(agent_name, []).copy()
    
    def resolve_order(self, agent_names: List[str]) -> List[str]:
        """Resolve execution order using topological sort.
        
        Args:
            agent_names: List of agent names to order
            
        Returns:
            List of agent names in execution order (dependencies first)
            
        Raises:
            ValueError: If circular dependency detected
        """
        # Build subgraph for requested agents
        subgraph = {}
        in_degree = defaultdict(int)
        
        # Include all dependencies of requested agents
        all_agents = set(agent_names)
        for agent in agent_names:
            all_agents.update(self.get_all_dependencies(agent))
        
        # Build in-degree map and subgraph
        # in_degree[agent] = number of dependencies agent has
        for agent in all_agents:
            if agent not in subgraph:
                subgraph[agent] = []
            
            deps = self._dependency_graph.get(agent, [])
            for dep in deps:
                if dep in all_agents:
                    subgraph[agent].append(dep)
                    in_degree[agent] += 1  # Increment for the agent that has the dependency
        
        # Initialize queue with agents that have no dependencies
        queue = deque([agent for agent in all_agents if in_degree[agent] == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            # Reduce in-degree for dependents (agents that depend on current)
            for dependent in self._reverse_graph.get(current, []):
                if dependent in all_agents:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        # Check for cycles
        if len(result) != len(all_agents):
            missing = all_agents - set(result)
            raise ValueError(f"Circular dependency detected involving: {missing}")
        
        # Return only the requested agents in order
        return [agent for agent in result if agent in agent_names]
    
    def detect_cycles(self) -> Optional[List[str]]:
        """Detect if there are any circular dependencies.
        
        Returns:
            List of agent names forming a cycle, or None if no cycle exists
        """
        visited = set()
        rec_stack = set()
        
        def visit(agent: str, path: List[str]) -> Optional[List[str]]:
            if agent in rec_stack:
                # Found cycle - return the cycle path
                cycle_start = path.index(agent)
                return path[cycle_start:] + [agent]
            
            if agent in visited:
                return None
            
            visited.add(agent)
            rec_stack.add(agent)
            path.append(agent)
            
            for dep in self._dependency_graph.get(agent, []):
                cycle = visit(dep, path.copy())
                if cycle:
                    return cycle
            
            rec_stack.remove(agent)
            return None
        
        for agent in self._dependency_graph:
            if agent not in visited:
                cycle = visit(agent, [])
                if cycle:
                    return cycle
        
        return None
    
    def validate_dependencies(self, available_agents: Set[str]) -> Dict[str, List[str]]:
        """Validate that all dependencies are satisfied.
        
        Args:
            available_agents: Set of available agent names
            
        Returns:
            Dictionary mapping agent names to lists of missing dependencies
        """
        issues = {}
        
        for agent, deps in self._dependency_graph.items():
            missing = [dep for dep in deps if dep not in available_agents]
            if missing:
                issues[agent] = missing
        
        return issues
    
    def get_execution_groups(self) -> List[List[str]]:
        """Get agents grouped by execution level.
        
        Returns:
            List of agent name lists, where each sublist can be executed in parallel
        """
        in_degree = defaultdict(int)
        
        # Calculate in-degrees
        for agent, deps in self._dependency_graph.items():
            for dep in deps:
                in_degree[dep] += 1
        
        groups = []
        processed = set()
        
        while len(processed) < len(self._dependency_graph):
            # Find agents with all dependencies satisfied
            current_group = []
            for agent in self._dependency_graph:
                if agent not in processed:
                    deps = self._dependency_graph.get(agent, [])
                    if all(dep in processed for dep in deps):
                        current_group.append(agent)
            
            if not current_group:
                # No progress - must be a cycle
                remaining = set(self._dependency_graph.keys()) - processed
                raise ValueError(f"Circular dependency detected in: {remaining}")
            
            groups.append(current_group)
            processed.update(current_group)
        
        return groups
    
    def clear(self) -> None:
        """Clear all dependency information."""
        self._dependency_graph.clear()
        self._reverse_graph.clear()
    
    def to_dict(self) -> Dict[str, List[str]]:
        """Export dependency graph as dictionary.
        
        Returns:
            Dictionary mapping agent names to their dependencies
        """
        return dict(self._dependency_graph)
