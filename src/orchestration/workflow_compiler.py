# workflow_compiler.py
"""YAML-to-LangGraph workflow compiler for UCOP.

Compiles workflow definitions into executable LangGraph DAGs while preserving 
existing agent logic and adding enhanced control capabilities.
"""

import yaml
import json
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging
try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    # Mock classes for when langgraph is not available
    class StateGraph:
        def __init__(self, *args, **kwargs):
            raise ImportError("LangGraph not available. Install with: pip install langgraph")
    
    class CompiledStateGraph:
        pass
    
    class MemorySaver:
        pass
    
    START = "start"
    END = "end"
import threading

from src.core.contracts import AgentEvent

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """Represents a single workflow step."""
    name: str
    agent_id: str
    capabilities: List[str]
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    conditions: Dict[str, Any] = field(default_factory=dict)
    retries: int = 3
    timeout: int = 300
    approval_required: bool = False
    parallel_group: Optional[str] = None


@dataclass  
class WorkflowDefinition:
    """Complete workflow definition."""
    name: str
    version: str
    description: str
    steps: List[WorkflowStep]
    global_inputs: Dict[str, Any] = field(default_factory=dict)
    global_outputs: Dict[str, Any] = field(default_factory=dict)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowState:
    """State management for workflow execution."""
    
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        self.data: Dict[str, Any] = initial_data or {}
        self.step_outputs: Dict[str, Any] = {}
        self.current_step: Optional[str] = None
        self.execution_id: str = ""
        self.correlation_id: str = ""
        self.paused: bool = False
        self.error: Optional[str] = None
        self.completed_steps: List[str] = []
        self.failed_steps: List[str] = []
        self._lock = threading.RLock()
    
    def update_step_output(self, step_name: str, output: Dict[str, Any]):
        """Update output for a specific step."""
        with self._lock:
            self.step_outputs[step_name] = output
            if step_name not in self.completed_steps:
                self.completed_steps.append(step_name)
    
    def set_current_step(self, step_name: str):
        """Set the currently executing step."""
        with self._lock:
            self.current_step = step_name
    
    def pause_execution(self):
        """Pause workflow execution."""
        with self._lock:
            self.paused = True
    
    def resume_execution(self):
        """Resume workflow execution."""
        with self._lock:
            self.paused = False
    
    def get_step_input(self, step_name: str, input_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Get input data for a step based on mapping."""
        with self._lock:
            inputs = {}
            
            for target_key, source_path in input_mapping.items():
                # Support dot notation: "step1.output.result"
                value = self._resolve_data_path(source_path)
                if value is not None:
                    inputs[target_key] = value
            
            return inputs
    
    def _resolve_data_path(self, path: str) -> Any:
        """Resolve data path like 'step1.output.result' or 'global.kb_path'."""
        parts = path.split('.')
        
        if parts[0] == 'global':
            current = self.data
            for part in parts[1:]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current
        
        elif parts[0] in self.step_outputs:
            current = self.step_outputs[parts[0]]
            for part in parts[1:]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current
        
        return None


class WorkflowCompiler:
    """Compiles YAML workflow definitions into LangGraph DAGs."""
    
    def __init__(self, registry, event_bus):
        self.registry = registry
        self.event_bus = event_bus
        self._compiled_workflows: Dict[str, CompiledStateGraph] = {}
        self._workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self._lock = threading.RLock()
        self.workflows = {}
        
    def _convert_format(self, data: Dict) -> Dict:
        """Convert v5.1 workflow format to current format."""
        dependencies = data.get('dependencies', {})
        profiles = data.get('profiles', {})
        
        workflows = {}
        
        for profile_name, profile_config in profiles.items():
            order = profile_config.get('order', [])
            skip = profile_config.get('skip', [])
            
            # Build steps from order, excluding skipped
            steps = {}
            for step_name in order:
                if step_name in skip:
                    continue
                    
                steps[step_name] = {
                    'agent': step_name,
                    'depends_on': dependencies.get(step_name, [])
                }
            
            workflows[f"blog_generation_{profile_name}"] = {
                'name': f"Blog Generation ({profile_name})",
                'description': profile_config.get('description', ''),
                'steps': steps,
                'config': {
                    'deterministic': profile_config.get('deterministic', False),
                    'max_retries': profile_config.get('max_retries', 3),
                    'llm': profile_config.get('llm', {})
                }
            }
        
        return workflows

    def load_workflows_from_file(self, workflow_file: Path):
        """Load workflow definitions from YAML file."""
        try:
            with open(workflow_file, 'r') as f:
                data = yaml.safe_load(f)
            
            # Check if v5.1 format (has 'dependencies' and 'profiles' keys)
            if 'dependencies' in data and 'profiles' in data:
                # Convert v5.1 format to current format
                workflows = self._convert_format(data)
            elif 'workflows' in data and isinstance(data['workflows'], dict):
                # Current format
                workflows = data['workflows']
            else:
                raise ValueError("Invalid workflow format")
            
            for name, definition in workflows.items():
                self.workflows[name] = definition
                logger.info(f"Loaded workflow: {name}")
                
        except Exception as e:
            logger.error(f"Failed to load workflows from {workflow_file}: {e}")
            raise

    def _parse_workflow_definition(self, name: str, config: Dict[str, Any]) -> WorkflowDefinition:
        """Parse workflow definition from YAML config."""
        steps = []
        
        for step_config in config.get('steps', []):
            step = WorkflowStep(
                name=step_config['name'],
                agent_id=step_config['agent'],
                capabilities=step_config.get('capabilities', []),
                inputs=step_config.get('inputs', {}),
                outputs=step_config.get('outputs', {}),
                conditions=step_config.get('when', {}),
                retries=step_config.get('retries', 3),
                timeout=step_config.get('timeout', 300),
                approval_required=step_config.get('approval_required', False),
                parallel_group=step_config.get('parallel_group')
            )
            steps.append(step)
        
        return WorkflowDefinition(
            name=name,
            version=config.get('version', '1.0'),
            description=config.get('description', ''),
            steps=steps,
            global_inputs=config.get('global_inputs', {}),
            global_outputs=config.get('global_outputs', {}),
            error_handling=config.get('error_handling', {}),
            metadata=config.get('metadata', {})
        )
    
    def compile_workflow(self, workflow_name: str) -> CompiledStateGraph:
        """Compile workflow definition into executable LangGraph."""
        with self._lock:
            if workflow_name in self._compiled_workflows:
                return self._compiled_workflows[workflow_name]
            
            workflow_def = self._workflow_definitions.get(workflow_name)
            if not workflow_def:
                raise ValueError(f"Workflow not found: {workflow_name}")
            
            # Create state graph
            graph = StateGraph(WorkflowState)
            
            # Add nodes for each step
            for step in workflow_def.steps:
                node_func = self._create_step_node(step, workflow_def)
                graph.add_node(step.name, node_func)
            
            # Add edges based on step dependencies
            self._add_workflow_edges(graph, workflow_def)
            
            # Add entry and exit points
            if workflow_def.steps:
                first_step = workflow_def.steps[0]
                graph.add_edge(START, first_step.name)
                
                # Find terminal steps (no outgoing edges)
                terminal_steps = self._find_terminal_steps(workflow_def)
                for step_name in terminal_steps:
                    graph.add_edge(step_name, END)
            
            # Compile with checkpointer for pause/resume
            checkpointer = MemorySaver()
            compiled = graph.compile(checkpointer=checkpointer)
            
            self._compiled_workflows[workflow_name] = compiled
            logger.info(f"Compiled workflow: {workflow_name}")
            return compiled
    
    def _create_step_node(self, step: WorkflowStep, workflow_def: WorkflowDefinition) -> Callable:
        """Create a LangGraph node function for a workflow step."""
        
        def step_node(state: WorkflowState) -> WorkflowState:
            """Execute workflow step."""
            logger.info(f"Executing step: {step.name}")
            
            # Check if paused
            if state.paused:
                logger.info(f"Workflow paused at step: {step.name}")
                return state
            
            state.set_current_step(step.name)
            
            try:
                # Get agent for this step
                agent = self.registry.get_agent(step.agent_id)
                if not agent:
                    raise ValueError(f"Agent not found: {step.agent_id}")
                
                # Prepare input data
                input_data = state.get_step_input(step.name, step.inputs)
                
                # Add global data
                input_data.update(state.data)
                
                # Create agent event
                event = AgentEvent(
                    event_type=f"execute_{step.capabilities[0]}" if step.capabilities else "execute",
                    data=input_data,
                    source_agent="workflow_compiler",
                    correlation_id=state.correlation_id
                )
                
                # Execute with retry logic
                result = None
                last_error = None
                
                for attempt in range(step.retries):
                    try:
                        result = agent.execute(event)
                        break
                    except Exception as e:
                        last_error = e
                        logger.warning(f"Step {step.name} attempt {attempt + 1} failed: {e}")
                        if attempt == step.retries - 1:
                            raise
                
                # Process result
                if result:
                    output_data = result.data
                    state.update_step_output(step.name, output_data)
                    
                    # Update global state based on output mapping
                    for global_key, step_output_path in step.outputs.items():
                        value = self._extract_output_value(output_data, step_output_path)
                        if value is not None:
                            state.data[global_key] = value
                
                logger.info(f"Completed step: {step.name}")
                return state
                
            except Exception as e:
                logger.error(f"Step {step.name} failed: {e}")
                state.failed_steps.append(step.name)
                state.error = str(e)
                
                # Handle error based on workflow error handling
                if workflow_def.error_handling.get('continue_on_error', False):
                    return state
                else:
                    raise
        
        return step_node
    
    def _add_workflow_edges(self, graph: StateGraph, workflow_def: WorkflowDefinition):
        """Add edges between workflow steps based on dependencies."""
        step_map = {step.name: step for step in workflow_def.steps}
        
        for i, step in enumerate(workflow_def.steps):
            # Simple linear progression for now
            if i < len(workflow_def.steps) - 1:
                next_step = workflow_def.steps[i + 1]
                
                # Add conditional edge if step has conditions
                if step.conditions:
                    condition_func = self._create_condition_function(step.conditions)
                    graph.add_conditional_edges(
                        step.name,
                        condition_func,
                        {
                            True: next_step.name,
                            False: END  # Skip to end if condition fails
                        }
                    )
                else:
                    graph.add_edge(step.name, next_step.name)
    
    def _create_condition_function(self, conditions: Dict[str, Any]) -> Callable:
        """Create condition function for conditional edges."""
        
        def condition_check(state: WorkflowState) -> bool:
            """Check if conditions are met."""
            for condition_key, expected_value in conditions.items():
                actual_value = state._resolve_data_path(condition_key)
                if actual_value != expected_value:
                    return False
            return True
        
        return condition_check
    
    def _find_terminal_steps(self, workflow_def: WorkflowDefinition) -> List[str]:
        """Find steps that don't lead to other steps."""
        # For now, assume last step is terminal
        if workflow_def.steps:
            return [workflow_def.steps[-1].name]
        return []
    
    def _extract_output_value(self, output_data: Dict[str, Any], path: str) -> Any:
        """Extract value from output data using dot notation path."""
        current = output_data
        for part in path.split('.'):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
    
    def get_workflow_definition(self, workflow_name: str) -> Optional[WorkflowDefinition]:
        """Get workflow definition by name."""
        with self._lock:
            return self._workflow_definitions.get(workflow_name)
    
    def list_workflows(self) -> List[str]:
        """List all available workflow names."""
        with self._lock:
            return list(self._workflow_definitions.keys())
    
    def validate_workflow(self, workflow_name: str) -> List[str]:
        """Validate workflow definition and return issues."""
        workflow_def = self._workflow_definitions.get(workflow_name)
        if not workflow_def:
            return [f"Workflow not found: {workflow_name}"]
        
        issues = []
        
        # Check if required agents exist
        for step in workflow_def.steps:
            agent = self.registry.get_agent(step.agent_id)
            if not agent:
                issues.append(f"Agent not found for step {step.name}: {step.agent_id}")
        
        # Check for circular dependencies (basic check)
        step_names = {step.name for step in workflow_def.steps}
        for step in workflow_def.steps:
            for input_path in step.inputs.values():
                if isinstance(input_path, str) and '.' in input_path:
                    referenced_step = input_path.split('.')[0]
                    if referenced_step in step_names:
                        # Could add more sophisticated cycle detection here
                        pass
        
        return issues


# Example workflow YAML structure
EXAMPLE_WORKFLOW_YAML = """
workflows:
  blog_generation:
    version: "1.0"
    description: "Complete blog post generation workflow"
    global_inputs:
      kb_path: "required"
      output_dir: "optional"
    
    steps:
      - name: ingest_kb
        agent: KBIngestionAgent
        capabilities: ["ingest_kb"]
        inputs:
          kb_path: "global.kb_path"
        outputs:
          kb_content: "kb_article_content"
        timeout: 120
        retries: 2
      
      - name: identify_topics
        agent: TopicIdentificationAgent
        capabilities: ["identify_blog_topics"]
        inputs:
          kb_article_content: "ingest_kb.kb_article_content"
        outputs:
          topics: "topics"
        approval_required: false
      
      - name: check_duplication
        agent: DuplicationCheckAgent
        capabilities: ["check_duplication"]
        inputs:
          topics: "identify_topics.topics"
        outputs:
          approved_topics: "approved_topics"
        when:
          "identify_topics.topics": "not_empty"
      
      - name: generate_content
        agent: ContentAssemblyAgent
        capabilities: ["assemble_content"]
        inputs:
          topics: "check_duplication.approved_topics"
          kb_content: "ingest_kb.kb_article_content"
        outputs:
          final_content: "content"
        approval_required: true
        timeout: 300
      
      - name: write_file
        agent: FileWriterAgent
        capabilities: ["write_file"]
        inputs:
          content: "generate_content.content"
          output_dir: "global.output_dir"
        outputs:
          file_path: "file_path"
    
    global_outputs:
      generated_file: "write_file.file_path"
      
    error_handling:
      continue_on_error: false
      max_retries: 3
      timeout_strategy: "fail_fast"

  quick_draft:
    version: "1.0"
    description: "Quick draft generation for testing"
    
    steps:
      - name: ingest_only
        agent: KBIngestionAgent
        capabilities: ["ingest_kb"]
        inputs:
          kb_path: "global.kb_path"
        outputs:
          content: "kb_article_content"
"""