# workflow_compiler.py
"""YAML-to-LangGraph workflow compiler for UCOP.

Compiles workflow definitions into executable LangGraph DAGs while preserving 
existing agent logic and adding enhanced control capabilities.
"""

import yaml
import json
from typing import Dict, List, Optional, Any, Callable, Union
from typing_extensions import TypedDict
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone
import logging

# Try to import LangGraph components
HAS_LANGGRAPH = False
StateGraph = None
START = None
END = None
CompiledStateGraph = None
MemorySaver = None

try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.checkpoint.memory import MemorySaver
    HAS_LANGGRAPH = True
except ImportError:
    pass

# Try to import SqliteSaver from various possible locations
SQLITE_AVAILABLE = False
SqliteSaver = None

if HAS_LANGGRAPH:
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        SQLITE_AVAILABLE = True
    except ImportError:
        try:
            from langgraph.checkpoint.sqlite.aio import SqliteSaver as AsyncSqliteSaver
            # Use async version if sync not available
            SqliteSaver = AsyncSqliteSaver
            SQLITE_AVAILABLE = True
        except ImportError:
            try:
                from langgraph_checkpoint.sqlite import SqliteSaver
                SQLITE_AVAILABLE = True
            except ImportError:
                pass

import threading

from src.core.contracts import AgentEvent

logger = logging.getLogger(__name__)

if not HAS_LANGGRAPH:
    logger.warning("langgraph not available - workflow compilation features disabled")


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
    depends_on: List[str] = field(default_factory=list)


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


from typing_extensions import TypedDict

class WorkflowState(TypedDict, total=False):
    """Immutable workflow state for LangGraph.
    
    LangGraph automatically merges updates returned by nodes.
    Nodes should return only the fields they want to update.
    """
    # Input data (provided at workflow start)
    topic: Dict[str, Any]
    kb_path: str
    uploaded_files: List[str]
    
    # RAG context outputs
    context_kb: List[str]
    context_blog: List[str]
    context_api: List[str]
    kb_article_content: str
    kb_meta: Dict[str, Any]
    
    # Content generation outputs
    topics: List[Dict[str, Any]]
    outline: Dict[str, Any]
    introduction: str
    sections: List[str]
    conclusion: str
    supplementary: Dict[str, Any]
    assembled_content: str
    final_content: str
    
    # SEO outputs
    seo_metadata: Dict[str, Any]
    keywords: List[str]
    slug: str  # Added slug field for file writer
    
    # Final outputs
    markdown: str  # Final markdown content with frontmatter
    
    # Execution metadata
    execution_id: str
    correlation_id: str
    current_step: str
    completed_steps: List[str]
    failed_steps: List[str]
    step_details: Dict[str, Dict[str, Any]]  # Track agent inputs/outputs for UI
    error: Optional[str]
    
    # Configuration
    deterministic: bool
    max_retries: int


def create_initial_state(
    topic: str = "",
    kb_path: str = "",
    uploaded_files: Optional[List[str]] = None,
    **kwargs
) -> WorkflowState:
    """Create initial workflow state from input parameters."""
    return WorkflowState(
        topic={'title': topic, 'description': ''},
        kb_path=kb_path,
        uploaded_files=uploaded_files or [],
        context_kb=[],
        context_blog=[],
        context_api=[],
        kb_article_content="",
        kb_meta={},
        topics=[],
        outline={},
        introduction="",
        sections=[],
        conclusion="",
        supplementary={},
        assembled_content="",
        final_content="",
        seo_metadata={},
        keywords=[],
        slug="",
        markdown="",
        execution_id=kwargs.get('execution_id', ''),
        correlation_id=kwargs.get('correlation_id', ''),
        current_step="",
        completed_steps=[],
        failed_steps=[],
        step_details={},
        error=None,
        deterministic=kwargs.get('deterministic', False),
        max_retries=kwargs.get('max_retries', 3)
    )


class WorkflowCompiler:
    """Compiles YAML workflow definitions into LangGraph DAGs."""
    
    def __init__(self, registry, event_bus, checkpoint_dir: Path = None, websocket_manager=None):
        self.registry = registry
        self.event_bus = event_bus
        self.websocket_manager = websocket_manager
        self._compiled_workflows: Dict[str, Any] = {}
        self._workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self._lock = threading.RLock()
        self.workflows = {}
        self.enabled = HAS_LANGGRAPH
        
        if not HAS_LANGGRAPH:
            logger.warning("WorkflowCompiler initialized without langgraph - features disabled")
            self.checkpointer = None
            return
        
        # Initialize checkpointer
        if SQLITE_AVAILABLE and SqliteSaver is not None:
            try:
                if checkpoint_dir is None:
                    checkpoint_dir = Path("./data/checkpoints")
                checkpoint_dir.mkdir(parents=True, exist_ok=True)
                
                checkpoint_db = checkpoint_dir / "workflow_checkpoints.db"
                self.checkpointer = SqliteSaver.from_conn_string(str(checkpoint_db))
                logger.info(f"✓ SqliteSaver checkpointer: {checkpoint_db}")
            except Exception as e:
                logger.warning(f"SqliteSaver failed ({e}), using MemorySaver")
                self.checkpointer = MemorySaver()
        else:
            self.checkpointer = MemorySaver() if MemorySaver else None
            logger.info("✓ Using MemorySaver (install aiosqlite for persistent checkpoints)")
        
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
                # Store raw workflow dict
                self.workflows[name] = definition
                
                # Parse and store as WorkflowDefinition for compilation
                try:
                    workflow_def = self._parse_workflow_dict(name, definition)
                    self._workflow_definitions[name] = workflow_def
                    logger.info(f"Loaded workflow: {name}")
                except Exception as e:
                    logger.warning(f"Could not parse workflow {name}: {e}, storing as dict")
                
        except Exception as e:
            logger.error(f"Failed to load workflows from {workflow_file}: {e}")
            raise
    
    def _parse_workflow_dict(self, name: str, config: Dict[str, Any]) -> WorkflowDefinition:
        """Parse workflow dict (from converted format) into WorkflowDefinition."""
        steps = []
        
        # Handle steps as dict (from _convert_format)
        steps_dict = config.get('steps', {})
        if isinstance(steps_dict, dict):
            for step_name, step_config in steps_dict.items():
                step = WorkflowStep(
                    name=step_name,
                    agent_id=step_config.get('agent', step_name),
                    capabilities=[step_name],  # Use step name as capability
                    inputs={},
                    outputs={},
                    conditions={},
                    retries=config.get('config', {}).get('max_retries', 3),
                    timeout=300,
                    approval_required=False,
                    parallel_group=None,
                    depends_on=step_config.get('depends_on', [])
                )
                steps.append(step)
        # Handle steps as list (from traditional format)
        elif isinstance(steps_dict, list):
            for step_config in steps_dict:
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
                parallel_group=step_config.get('parallel_group'),
                depends_on=step_config.get('depends_on', [])
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
            
            # Compile with persistent checkpointer for pause/resume
            compiled = graph.compile(checkpointer=self.checkpointer)
            
            self._compiled_workflows[workflow_name] = compiled
            logger.info(f"Compiled workflow: {workflow_name}")
            return compiled
    
    def _create_step_node(self, step: WorkflowStep, workflow_def: WorkflowDefinition) -> Callable:
        """Create a LangGraph node function for a workflow step."""
        
        def step_node(state: WorkflowState) -> Dict[str, Any]:
            """Execute workflow step - returns STATE UPDATES only."""
            logger.info(f"Executing step: {step.name}")
            
            # Broadcast step start
            if self.websocket_manager:
                try:
                    import asyncio
                    from src.realtime.websocket import EventType
                    job_id = state.get('execution_id', '')
                    if job_id:
                        # Try to get running loop, if not available skip broadcast
                        try:
                            loop = asyncio.get_running_loop()
                            asyncio.create_task(
                                self.websocket_manager.broadcast(
                                    job_id,
                                    EventType.NODE_START,
                                    {'step': step.name, 'agent_id': step.agent_id}
                                )
                            )
                        except RuntimeError:
                            # No event loop running, skip broadcast
                            pass
                except Exception as e:
                    logger.debug(f"Could not broadcast step start: {e}")
            
            try:
                # Get agent for this step
                agent = self.registry.get_agent(step.agent_id)
                if not agent:
                    raise ValueError(f"Agent not found: {step.agent_id}")
                
                # Prepare input data from state
                input_data = self._prepare_agent_input(state, step)
                
                # Create agent event
                event = AgentEvent(
                    event_type=f"execute_{step.capabilities[0]}" if step.capabilities else "execute",
                    data=input_data,
                    source_agent="workflow_compiler",
                    correlation_id=state.get('correlation_id', '')
                )
                
                # Execute with retry logic
                result = None
                max_retries = state.get('max_retries', step.retries)
                
                for attempt in range(max_retries):
                    try:
                        result = agent.execute(event)
                        break
                    except Exception as e:
                        logger.warning(f"Step {step.name} attempt {attempt + 1}/{max_retries} failed: {e}")
                        if attempt == max_retries - 1:
                            raise
                
                # Return state updates (LangGraph will merge these)
                updates = {
                    'current_step': step.name,
                    'completed_steps': state.get('completed_steps', []) + [step.name]
                }
                
                # Track agent execution details for UI
                step_details = state.get('step_details', {}).copy()
                step_details[step.name] = {
                    'agent_id': step.agent_id,
                    'input': {k: str(v)[:200] if isinstance(v, (str, list, dict)) else v 
                             for k, v in input_data.items()},  # Truncate for display
                    'output': {k: str(v)[:200] if isinstance(v, (str, list, dict)) else v 
                              for k, v in (result.data if result else {}).items()},  # Truncate for display
                    'status': 'completed',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                updates['step_details'] = step_details
                
                # Map agent output to state fields
                if result and result.data:
                    updates.update(self._map_agent_output(step.name, result.data))
                
                # Broadcast step completion
                if self.websocket_manager:
                    try:
                        import asyncio
                        from src.realtime.websocket import EventType
                        job_id = state.get('execution_id', '')
                        if job_id:
                            # Try to get running loop, if not available skip broadcast
                            try:
                                loop = asyncio.get_running_loop()
                                asyncio.create_task(
                                    self.websocket_manager.broadcast(
                                        job_id,
                                        EventType.NODE_OUTPUT,
                                        {
                                            'step': step.name,
                                            'agent_id': step.agent_id,
                                            'status': 'completed',
                                            'details': step_details.get(step.name, {})
                                        }
                                    )
                                )
                            except RuntimeError:
                                # No event loop running, skip broadcast
                                pass
                    except Exception as e:
                        logger.debug(f"Could not broadcast step completion: {e}")
                
                logger.info(f"Completed step: {step.name}")
                return updates
                
            except Exception as e:
                logger.error(f"Step {step.name} failed: {e}", exc_info=True)
                
                failed_steps = state.get('failed_steps', []).copy()
                failed_steps.append(step.name)
                
                # Handle error based on workflow error handling
                if workflow_def.error_handling.get('continue_on_error', False):
                    return {
                        'failed_steps': failed_steps,
                        'error': str(e),
                        'current_step': step.name
                    }
                else:
                    raise
        
        return step_node
    
    def _prepare_agent_input(self, state: WorkflowState, step: WorkflowStep) -> Dict[str, Any]:
        """Prepare input data for agent from current state."""
        input_data = {}
        
        # Add all relevant state fields that the agent might need
        if state.get('topic'):
            input_data['topic'] = state['topic']
        if state.get('kb_path'):
            input_data['kb_path'] = state['kb_path']
        if state.get('uploaded_files'):
            input_data['uploaded_files'] = state['uploaded_files']
        if state.get('kb_article_content'):
            input_data['kb_article_content'] = state['kb_article_content']
        if state.get('kb_meta'):
            input_data['kb_meta'] = state['kb_meta']
        if state.get('context_kb'):
            input_data['context_kb'] = state['context_kb']
        if state.get('context_blog'):
            input_data['context_blog'] = state['context_blog']
        if state.get('context_api'):
            input_data['context_api'] = state['context_api']
        if state.get('topics'):
            input_data['topics'] = state['topics']
        if state.get('outline'):
            input_data['outline'] = state['outline']
        if state.get('introduction'):
            input_data['introduction'] = state['introduction']
        if state.get('sections'):
            input_data['sections'] = state['sections']
        if state.get('conclusion'):
            input_data['conclusion'] = state['conclusion']
        if state.get('supplementary'):
            input_data['supplementary'] = state['supplementary']
        if state.get('assembled_content'):
            input_data['assembled_content'] = state['assembled_content']
            # Also pass as 'content' for agents that expect that key
            input_data['content'] = state['assembled_content']
        elif state.get('final_content'):
            # If assembled_content is missing but final_content exists, use that
            input_data['content'] = state['final_content']
        if state.get('seo_metadata'):
            input_data['seo_metadata'] = state['seo_metadata']
        if state.get('keywords'):
            input_data['keywords'] = state['keywords']
        if state.get('slug'):
            input_data['slug'] = state['slug']
        if state.get('kb_article_content'):
            input_data['kb_article_content'] = state['kb_article_content']
        if state.get('kb_meta'):
            input_data['kb_meta'] = state['kb_meta']
        if state.get('markdown'):
            input_data['markdown'] = state['markdown']
        
        return input_data
    
    def _map_agent_output(self, step_name: str, output: Dict[str, Any]) -> Dict[str, Any]:
        """Map agent output to state field updates."""
        updates = {}
        
        # Map common output fields to state
        field_mappings = {
            'topics': 'topics',
            'outline': 'outline',
            'introduction': 'introduction',
            'sections': 'sections',
            'conclusion': 'conclusion',
            'supplementary': 'supplementary',
            'content': 'assembled_content',
            'final_content': 'final_content',
            'seo_metadata': 'seo_metadata',
            'slug': 'slug',
            'keywords': 'keywords',
            'context_kb': 'context_kb',
            'context_blog': 'context_blog',
            'context_api': 'context_api',
            'markdown': 'markdown',  # Map markdown explicitly
            'kb_article_content': 'kb_article_content',
            'kb_meta': 'kb_meta'
        }
        
        for output_key, state_key in field_mappings.items():
            if output_key in output:
                updates[state_key] = output[output_key]
        
        # Special handling: extract slug from seo_metadata if present
        if 'seo_metadata' in output and isinstance(output['seo_metadata'], dict):
            if 'slug' in output['seo_metadata'] and 'slug' not in updates:
                updates['slug'] = output['seo_metadata']['slug']
        
        return updates
    
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