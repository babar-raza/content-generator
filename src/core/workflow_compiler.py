"""Workflow Compiler for parsing and validating workflow definitions."""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import logging
from collections import defaultdict


class WorkflowCompiler:
    """Compiles YAML workflow definitions into executable DAGs."""
    
    def __init__(self, agent_registry: Optional[Dict] = None):
        """Initialize the workflow compiler.
        
        Args:
            agent_registry: Dictionary of available agents
        """
        self.agent_registry = agent_registry or {}
        self.logger = logging.getLogger(__name__)
        self._compiled_workflows: Dict[str, Dict] = {}
    
    def compile(self, workflow_path: Path) -> Dict[str, Any]:
        """Compile a workflow from YAML file.
        
        Args:
            workflow_path: Path to workflow YAML file
            
        Returns:
            Compiled workflow structure
            
        Raises:
            ValueError: If workflow is invalid
        """
        # Parse YAML
        workflow_data = self._parse_yaml(workflow_path)
        
        # Validate structure
        self._validate_structure(workflow_data)
        
        # Validate agent references
        self._validate_agents(workflow_data)
        
        # Build dependency graph
        dep_graph = self._build_dependency_graph(workflow_data)
        
        # Check for circular dependencies
        cycle = self._detect_cycles(dep_graph)
        if cycle:
            cycle_str = " -> ".join(cycle)
            raise ValueError(f"Workflow contains circular dependency: {cycle_str}")
        
        # Build execution DAG
        execution_dag = self._build_execution_dag(workflow_data, dep_graph)
        
        # Cache compiled workflow
        workflow_name = workflow_data.get('name', 'unnamed')
        self._compiled_workflows[workflow_name] = execution_dag
        
        return execution_dag
    
    def _parse_yaml(self, yaml_path: Path) -> Dict:
        """Parse YAML workflow file with line number tracking.
        
        Args:
            yaml_path: Path to YAML file
            
        Returns:
            Parsed workflow data
        """
        try:
            with open(yaml_path, 'r') as f:
                # Use custom loader to preserve line numbers
                class LineLoader(yaml.SafeLoader):
                    """Custom loader that tracks line numbers."""
                    pass
                
                def compose_node(parent, index):
                    # Get the line number
                    line = LineLoader.line
                    node = yaml.composer.Composer.compose_node(LineLoader, parent, index)
                    node.__line__ = line
                    return node
                
                # Attempt to track line numbers if possible
                try:
                    LineLoader.compose_node = compose_node
                    data = yaml.load(f, Loader=LineLoader)
                except:
                    # Fallback to standard loading
                    f.seek(0)
                    data = yaml.safe_load(f)
                
                return data
                
        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML syntax: {e}"
            # Extract line number if available
            if hasattr(e, 'problem_mark'):
                mark = e.problem_mark
                error_msg = f"Invalid YAML syntax at line {mark.line + 1}, column {mark.column + 1}: {e.problem}"
            raise ValueError(error_msg)
        except FileNotFoundError:
            raise ValueError(f"Workflow file not found: {yaml_path}")
    
    def _validate_structure(self, workflow_data: Dict) -> None:
        """Validate basic workflow structure.
        
        Args:
            workflow_data: Parsed workflow data
            
        Raises:
            ValueError: If structure is invalid
        """
        # Check required fields
        if not workflow_data:
            raise ValueError("Workflow file is empty or invalid")
        
        if 'name' not in workflow_data:
            raise ValueError("Workflow missing required field: 'name'")
        
        if not workflow_data['name'] or not isinstance(workflow_data['name'], str):
            raise ValueError("Workflow 'name' must be a non-empty string")
        
        if 'agents' not in workflow_data:
            raise ValueError("Workflow missing required field: 'agents'")
        
        if not isinstance(workflow_data['agents'], list):
            raise ValueError("'agents' field must be a list")
        
        if not workflow_data['agents']:
            raise ValueError("Workflow must contain at least one agent step")
        
        # Validate each agent step
        step_names = set()
        for idx, agent_step in enumerate(workflow_data['agents']):
            if not isinstance(agent_step, dict):
                raise ValueError(f"Agent step {idx} must be a dictionary")
            
            if 'name' not in agent_step:
                raise ValueError(f"Agent step {idx} missing 'name' field")
            
            step_name = agent_step['name']
            if not step_name or not isinstance(step_name, str):
                raise ValueError(f"Agent step {idx} 'name' must be a non-empty string")
            
            # Check for duplicate step names
            if step_name in step_names:
                raise ValueError(f"Duplicate step name '{step_name}' at position {idx}")
            step_names.add(step_name)
            
            if 'agent' not in agent_step:
                raise ValueError(f"Agent step '{step_name}' missing 'agent' field")
            
            if not isinstance(agent_step['agent'], str):
                raise ValueError(f"Agent step '{step_name}' 'agent' field must be a string")
    
    def _validate_agents(self, workflow_data: Dict) -> None:
        """Validate that all referenced agents exist.
        
        Args:
            workflow_data: Parsed workflow data
            
        Raises:
            ValueError: If agent references are invalid
        """
        for idx, agent_step in enumerate(workflow_data['agents']):
            agent_name = agent_step.get('agent')
            step_name = agent_step.get('name', f'step_{idx}')
            
            # Check if agent exists in registry
            if self.agent_registry and agent_name not in self.agent_registry:
                available = ", ".join(sorted(self.agent_registry.keys()))
                if available:
                    raise ValueError(
                        f"Step '{step_name}': Unknown agent '{agent_name}'. "
                        f"Available agents: {available}"
                    )
                else:
                    raise ValueError(
                        f"Step '{step_name}': Unknown agent '{agent_name}'. "
                        f"No agents available in registry"
                    )
    
    def _build_dependency_graph(self, workflow_data: Dict) -> Dict[str, List[str]]:
        """Build dependency graph from workflow.
        
        Args:
            workflow_data: Parsed workflow data
            
        Returns:
            Adjacency list representation of dependencies
        """
        graph = defaultdict(list)
        
        # Get all step names first for validation
        all_steps = {step['name'] for step in workflow_data['agents']}
        
        # Build graph from dependencies
        for agent_step in workflow_data['agents']:
            step_name = agent_step['name']
            depends_on = agent_step.get('depends_on', [])
            
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            
            if not isinstance(depends_on, list):
                raise ValueError(
                    f"Step '{step_name}' has invalid 'depends_on' field: must be string or list"
                )
            
            for dependency in depends_on:
                if not isinstance(dependency, str):
                    raise ValueError(
                        f"Step '{step_name}' dependency must be string, got {type(dependency).__name__}"
                    )
                
                # Validate dependency exists
                if dependency not in all_steps:
                    available = ", ".join(sorted(all_steps))
                    raise ValueError(
                        f"Step '{step_name}' depends on unknown step '{dependency}'. "
                        f"Available steps: {available}"
                    )
                
                # Check for self-dependency
                if dependency == step_name:
                    raise ValueError(f"Step '{step_name}' cannot depend on itself")
                
                # Add edge from dependency to dependent
                graph[dependency].append(step_name)
            
            # Ensure all nodes are in graph
            if step_name not in graph:
                graph[step_name] = []
        
        return dict(graph)
    
    def _detect_cycles(self, graph: Dict[str, List[str]]) -> Optional[List[str]]:
        """Detect circular dependencies in graph using DFS.
        
        Args:
            graph: Dependency graph
            
        Returns:
            List representing the cycle path if detected, None otherwise
        """
        visited = set()
        rec_stack = set()
        parent = {}
        
        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            """DFS helper with recursion stack tracking."""
            visited.add(node)
            rec_stack.add(node)
            current_path = path + [node]
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    parent[neighbor] = node
                    cycle = dfs(neighbor, current_path)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found a back edge - cycle detected
                    # Build the cycle path
                    cycle_start_idx = current_path.index(neighbor)
                    return current_path[cycle_start_idx:] + [neighbor]
            
            rec_stack.remove(node)
            return None
        
        # Check all nodes for cycles
        for node in graph:
            if node not in visited:
                cycle = dfs(node, [])
                if cycle:
                    return cycle
        
        return None
    
    def _build_execution_dag(
        self, 
        workflow_data: Dict, 
        dep_graph: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Build executable DAG from workflow and dependency graph.
        
        Args:
            workflow_data: Parsed workflow data
            dep_graph: Dependency graph
            
        Returns:
            Executable DAG structure
        """
        # Create step lookup
        steps = {}
        for agent_step in workflow_data['agents']:
            step_name = agent_step['name']
            steps[step_name] = {
                'agent': agent_step['agent'],
                'inputs': agent_step.get('inputs', {}),
                'outputs': agent_step.get('outputs', {}),
                'depends_on': agent_step.get('depends_on', [])
            }
        
        # Compute execution order using topological sort
        execution_order = self._topological_sort(dep_graph)
        
        # Build DAG
        dag = {
            'name': workflow_data['name'],
            'description': workflow_data.get('description', ''),
            'steps': steps,
            'execution_order': execution_order,
            'dependency_graph': dep_graph
        }
        
        return dag
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """Perform topological sort on dependency graph.
        
        Args:
            graph: Dependency graph
            
        Returns:
            List of nodes in topological order
        """
        # Calculate in-degree for each node
        in_degree = defaultdict(int)
        all_nodes = set(graph.keys())
        
        for node in graph:
            for neighbor in graph[node]:
                in_degree[neighbor] += 1
                all_nodes.add(neighbor)
        
        # Find nodes with no dependencies
        queue = [node for node in all_nodes if in_degree[node] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            # Reduce in-degree of neighbors
            for neighbor in graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check if all nodes were processed
        if len(result) != len(all_nodes):
            raise ValueError("Cycle detected in dependency graph")
        
        return result
    
    def get_compiled_workflow(self, name: str) -> Optional[Dict]:
        """Get a compiled workflow by name.
        
        Args:
            name: Workflow name
            
        Returns:
            Compiled workflow or None
        """
        return self._compiled_workflows.get(name)
    
    def list_workflows(self) -> List[str]:
        """List all compiled workflow names.
        
        Returns:
            List of workflow names
        """
        return list(self._compiled_workflows.keys())
    
    def validate_workflow(self, workflow_path: Path) -> bool:
        """Validate a workflow without compiling it.
        
        Args:
            workflow_path: Path to workflow YAML file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            self.compile(workflow_path)
            return True
        except Exception as e:
            self.logger.error(f"Workflow validation failed: {e}")
            return False
