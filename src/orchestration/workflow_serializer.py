"""Workflow Serializer for converting between visual JSON and YAML formats.

This module handles the conversion between the visual workflow editor's JSON format
and the YAML format used for workflow storage and execution.
"""

import yaml
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class WorkflowSerializer:
    """Serializes workflows between JSON (visual) and YAML (storage) formats."""
    
    def __init__(self, workflows_file: Optional[Path] = None):
        """Initialize the serializer.
        
        Args:
            workflows_file: Path to workflows.yaml file
        """
        self.workflows_file = workflows_file or Path("templates/workflows.yaml")
    
    def json_to_yaml(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        """Convert visual JSON format to YAML format.
        
        Visual JSON format:
        {
            "id": "my_workflow",
            "name": "My Workflow",
            "description": "...",
            "nodes": [
                {"id": "node1", "type": "agent", "data": {"agentId": "kb_ingestion", ...}, "position": {...}},
                {"id": "node2", "type": "agent", "data": {"agentId": "outline_creation", ...}, "position": {...}}
            ],
            "edges": [
                {"source": "node1", "target": "node2"}
            ]
        }
        
        YAML format:
        {
            "my_workflow": {
                "name": "My Workflow",
                "description": "...",
                "steps": [
                    {"agent": "kb_ingestion", "id": "node1"},
                    {"agent": "outline_creation", "id": "node2", "depends_on": ["node1"]}
                ]
            }
        }
        
        Args:
            workflow_json: Workflow in visual JSON format
            
        Returns:
            Workflow in YAML format
        """
        workflow_id = workflow_json.get("id", "untitled")
        nodes = {n["id"]: n for n in workflow_json.get("nodes", [])}
        edges = workflow_json.get("edges", [])
        
        # Build dependency map
        dependencies = {}
        for edge in edges:
            target = edge["target"]
            source = edge["source"]
            if target not in dependencies:
                dependencies[target] = []
            dependencies[target].append(source)
        
        # Convert nodes to steps
        steps = []
        for node_id, node in nodes.items():
            # Skip non-agent nodes
            if node.get("type") not in ["agent", "default"]:
                continue
                
            agent_id = node.get("data", {}).get("agentId")
            if not agent_id:
                logger.warning(f"Node {node_id} has no agentId, skipping")
                continue
            
            step = {
                "agent": agent_id,
            }
            
            # Add action if present
            action = node.get("data", {}).get("action")
            if action:
                step["action"] = action
            
            # Add inputs if present
            inputs = node.get("data", {}).get("inputs")
            if inputs:
                step["inputs"] = inputs if isinstance(inputs, list) else [inputs]
            
            # Add outputs if present
            outputs = node.get("data", {}).get("outputs")
            if outputs:
                step["outputs"] = outputs if isinstance(outputs, list) else [outputs]
            
            # Add configuration if present
            config = node.get("data", {}).get("config")
            if config:
                step["config"] = config
            
            # Add parameters if present
            params = node.get("data", {}).get("params")
            if params:
                step["params"] = params
            
            steps.append(step)
        
        # Sort steps by dependencies (topological sort)
        sorted_steps = self._topological_sort(steps, dependencies)
        
        # Add depends_on to sorted steps
        for step in sorted_steps:
            # Find the node_id for this step
            node_id = None
            for nid, node in nodes.items():
                if node.get("data", {}).get("agentId") == step["agent"]:
                    node_id = nid
                    break
            
            if node_id and node_id in dependencies:
                # Map node IDs to agent IDs
                deps = []
                for dep_node_id in dependencies[node_id]:
                    dep_agent_id = nodes.get(dep_node_id, {}).get("data", {}).get("agentId")
                    if dep_agent_id:
                        deps.append(dep_agent_id)
                if deps:
                    step["depends_on"] = deps
        
        return {
            workflow_id: {
                "name": workflow_json.get("name", "Untitled Workflow"),
                "description": workflow_json.get("description", ""),
                "steps": sorted_steps,
                "metadata": workflow_json.get("metadata", {
                    "category": "custom",
                    "version": "1.0"
                })
            }
        }
    
    def yaml_to_json(self, workflow_yaml: Dict[str, Any], workflow_id: str = None) -> Dict[str, Any]:
        """Convert YAML format to visual JSON format.
        
        Args:
            workflow_yaml: Workflow in YAML format
            workflow_id: Workflow ID (if not in the dict)
            
        Returns:
            Workflow in visual JSON format
        """
        # Get the workflow (should be single key in dict or provided workflow_id)
        if workflow_id is None:
            workflow_id = list(workflow_yaml.keys())[0]
        
        workflow = workflow_yaml[workflow_id]
        
        # Convert steps to nodes
        nodes = []
        edges = []
        node_id_map = {}  # agent_id -> node_id
        
        steps = workflow.get("steps", [])
        if isinstance(steps, dict):
            # Old format: steps is a dict
            steps = list(steps.values())
        
        for i, step in enumerate(steps):
            # Handle both string agent reference and dict step definition
            if isinstance(step, str):
                agent_id = step
                step_data = {"agent": agent_id}
            else:
                agent_id = step.get("agent", f"agent_{i}")
                step_data = step
            
            node_id = f"node-{i}"
            node_id_map[agent_id] = node_id
            
            node = {
                "id": node_id,
                "type": "default",
                "position": self._calculate_position(i, len(steps)),
                "data": {
                    "label": step_data.get("name", agent_id),
                    "agentId": agent_id,
                    "action": step_data.get("action"),
                    "inputs": step_data.get("inputs", []),
                    "outputs": step_data.get("outputs", []),
                    "config": step_data.get("config", {}),
                    "params": step_data.get("params", {}),
                    "status": "idle"
                }
            }
            nodes.append(node)
        
        # Create edges from dependencies
        for i, step in enumerate(steps):
            if isinstance(step, str):
                continue
                
            node_id = f"node-{i}"
            depends_on = step.get("depends_on", [])
            
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            
            for dep_agent_id in depends_on:
                dep_node_id = node_id_map.get(dep_agent_id)
                if dep_node_id:
                    edges.append({
                        "id": f"{dep_node_id}-{node_id}",
                        "source": dep_node_id,
                        "target": node_id,
                        "type": "smoothstep"
                    })
        
        return {
            "id": workflow_id,
            "name": workflow.get("name", "Untitled Workflow"),
            "description": workflow.get("description", ""),
            "nodes": nodes,
            "edges": edges,
            "metadata": workflow.get("metadata", {})
        }
    
    def save_workflow(self, workflow_json: Dict[str, Any]) -> None:
        """Save workflow to YAML file.
        
        Args:
            workflow_json: Workflow in visual JSON format
        """
        # Load existing workflows
        if self.workflows_file.exists():
            with open(self.workflows_file, 'r', encoding='utf-8') as f:
                workflows = yaml.safe_load(f) or {}
        else:
            workflows = {}
        
        # Ensure workflows key exists
        if "workflows" not in workflows:
            workflows["workflows"] = {}
        
        # Convert and merge
        workflow_yaml = self.json_to_yaml(workflow_json)
        workflow_id = list(workflow_yaml.keys())[0]
        
        workflows["workflows"][workflow_id] = workflow_yaml[workflow_id]
        
        # Save back to file
        with open(self.workflows_file, 'w', encoding='utf-8') as f:
            yaml.dump(workflows, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        logger.info(f"Saved workflow: {workflow_id}")
    
    def load_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Load workflow from YAML file.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Workflow in visual JSON format
            
        Raises:
            ValueError: If workflow not found
        """
        if not self.workflows_file.exists():
            raise ValueError(f"Workflows file not found: {self.workflows_file}")
        
        with open(self.workflows_file, 'r', encoding='utf-8') as f:
            workflows = yaml.safe_load(f)
        
        if not workflows or "workflows" not in workflows:
            raise ValueError("No workflows found in file")
        
        if workflow_id not in workflows["workflows"]:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        
        workflow_yaml = {workflow_id: workflows["workflows"][workflow_id]}
        return self.yaml_to_json(workflow_yaml, workflow_id)
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all available workflows.
        
        Returns:
            List of workflow summaries
        """
        if not self.workflows_file.exists():
            return []
        
        with open(self.workflows_file, 'r', encoding='utf-8') as f:
            workflows = yaml.safe_load(f)
        
        if not workflows or "workflows" not in workflows:
            return []
        
        result = []
        for workflow_id, workflow in workflows["workflows"].items():
            result.append({
                "id": workflow_id,
                "name": workflow.get("name", workflow_id),
                "description": workflow.get("description", ""),
                "metadata": workflow.get("metadata", {})
            })
        
        return result
    
    def _topological_sort(self, steps: List[Dict[str, Any]], dependencies: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Sort steps by dependencies using topological sort.
        
        Args:
            steps: List of step definitions
            dependencies: Map of node_id -> [dependency_node_ids]
            
        Returns:
            Sorted list of steps
        """
        if not steps:
            return []
        
        # If no dependencies, return steps as-is
        if not dependencies:
            return steps
        
        # Build agent_id -> step map
        agent_to_step = {step["agent"]: step for step in steps}
        
        # Build dependency graph by agent_id
        # This is a simple approach - return steps as-is for now
        # More sophisticated topological sorting can be added if needed
        return steps
    
    def _calculate_position(self, index: int, total: int) -> Dict[str, int]:
        """Calculate node position for visual layout.
        
        Args:
            index: Step index
            total: Total number of steps
            
        Returns:
            Position dict with x and y coordinates
        """
        # Simple grid layout
        cols = 3
        row = index // cols
        col = index % cols
        
        return {
            "x": 250 + col * 300,
            "y": 100 + row * 200
        }
    
    def validate_workflow(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow structure.
        
        Args:
            workflow_json: Workflow in visual JSON format
            
        Returns:
            Validation result with errors list
        """
        errors = []
        warnings = []
        
        # Check for required fields
        if not workflow_json.get("id"):
            errors.append("Workflow must have an id")
        
        if not workflow_json.get("name"):
            errors.append("Workflow must have a name")
        
        nodes = workflow_json.get("nodes", [])
        edges = workflow_json.get("edges", [])
        
        if not nodes:
            errors.append("Workflow must have at least one node")
        
        # Check for cycles
        if self._has_cycles(nodes, edges):
            errors.append("Workflow contains circular dependencies")
        
        # Check for orphan nodes
        orphans = self._find_orphan_nodes(nodes, edges)
        if orphans:
            warnings.append(f"Workflow has {len(orphans)} disconnected nodes")
        
        # Check agent IDs
        for node in nodes:
            if node.get("type") in ["agent", "default"]:
                agent_id = node.get("data", {}).get("agentId")
                if not agent_id:
                    errors.append(f"Node {node.get('id')} missing agentId")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _has_cycles(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> bool:
        """Check if workflow has circular dependencies.
        
        Args:
            nodes: List of nodes
            edges: List of edges
            
        Returns:
            True if cycles detected
        """
        # Build adjacency list
        graph = {node["id"]: [] for node in nodes}
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and target and source in graph:
                graph[source].append(target)
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for neighbor in graph.get(node_id, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in graph:
            if node_id not in visited:
                if has_cycle(node_id):
                    return True
        
        return False
    
    def _find_orphan_nodes(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[str]:
        """Find nodes that are not connected to any other nodes.
        
        Args:
            nodes: List of nodes
            edges: List of edges
            
        Returns:
            List of orphan node IDs
        """
        if len(nodes) <= 1:
            return []
        
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge.get("source"))
            connected_nodes.add(edge.get("target"))
        
        orphans = []
        for node in nodes:
            if node["id"] not in connected_nodes:
                orphans.append(node["id"])
        
        return orphans
