# langgraph_executor.py
"""LangGraph-based workflow execution engine.

Provides graph-based workflow execution with automatic checkpointing,
conditional branching, and parallel execution support.
"""

import logging
import time
import traceback
from typing import Dict, List, Any, Optional, Callable, Literal
from pathlib import Path
from datetime import datetime, timezone

try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    MemorySaver = None
    START = "start"
    END = "end"

from src.core import Config, EventBus, AgentEvent, Agent
from .langgraph_state import WorkflowState, AgentOutput
from .checkpoint_manager import CheckpointManager
from .production_execution_engine import AgentFactory

logger = logging.getLogger(__name__)


class LangGraphExecutor:
    """Executes workflows using LangGraph StateGraph.
    
    Converts sequential workflow definitions into LangGraph graphs with:
    - Type-safe state management
    - Automatic checkpointing
    - Conditional branching
    - Parallel node execution
    - Error recovery
    """
    
    def __init__(
        self,
        config: Config,
        workflow_steps: List[Dict[str, Any]],
        agent_factory: AgentFactory,
        checkpoint_manager: CheckpointManager
    ):
        """Initialize LangGraph executor.
        
        Args:
            config: System configuration
            workflow_steps: List of workflow step definitions
            agent_factory: Factory for creating agent instances
            checkpoint_manager: Checkpoint manager for state persistence
        """
        if not LANGGRAPH_AVAILABLE:
            raise ImportError(
                "LangGraph not available. Install with: pip install langgraph"
            )
        
        self.config = config
        self.workflow_steps = workflow_steps
        self.agent_factory = agent_factory
        self.checkpoint_manager = checkpoint_manager
        
        # Build the graph
        self.graph = None
        self.compiled_graph = None
        
        # Execution callbacks
        self.progress_callback: Optional[Callable] = None
        self.checkpoint_callback: Optional[Callable] = None
        
        logger.info(f"LangGraphExecutor initialized with {len(workflow_steps)} steps")
    
    def build_graph(self) -> StateGraph:
        """Build LangGraph StateGraph from workflow steps.
        
        Returns:
            StateGraph ready for compilation
        """
        # Create state graph
        graph = StateGraph(WorkflowState)
        
        # Group steps for parallel execution
        parallel_groups = self._identify_parallel_groups()
        
        # Add nodes for each agent
        for step_config in self.workflow_steps:
            agent_type = step_config.get('agent', step_config.get('id'))
            node_name = agent_type
            
            # Create node function for this agent
            node_func = self._create_agent_node(agent_type, step_config)
            graph.add_node(node_name, node_func)
            logger.debug(f"Added node: {node_name}")
        
        # Add edges based on workflow order and dependencies
        self._add_edges(graph, parallel_groups)
        
        # Set entry point
        if self.workflow_steps:
            first_agent = self.workflow_steps[0].get('agent', self.workflow_steps[0].get('id'))
            graph.set_entry_point(first_agent)
            logger.debug(f"Set entry point: {first_agent}")
        
        self.graph = graph
        return graph
    
    def compile_graph(self, checkpointer=None) -> Any:
        """Compile the graph for execution.
        
        Args:
            checkpointer: Optional LangGraph checkpointer (defaults to MemorySaver)
            
        Returns:
            Compiled graph
        """
        if not self.graph:
            self.build_graph()
        
        # Use memory checkpointer if none provided
        if checkpointer is None:
            checkpointer = MemorySaver()
        
        self.compiled_graph = self.graph.compile(checkpointer=checkpointer)
        logger.info("Graph compiled successfully")
        return self.compiled_graph
    
    def execute(
        self,
        input_data: Dict[str, Any],
        job_id: str,
        workflow_name: str = "default",
        progress_callback: Optional[Callable] = None,
        checkpoint_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute workflow using LangGraph.
        
        Args:
            input_data: Input parameters for workflow
            job_id: Unique job identifier
            workflow_name: Name of workflow being executed
            progress_callback: Optional callback for progress updates
            checkpoint_callback: Optional callback for checkpoint events
            
        Returns:
            Execution results with outputs and metrics
        """
        if not self.compiled_graph:
            self.compile_graph()
        
        self.progress_callback = progress_callback
        self.checkpoint_callback = checkpoint_callback
        
        # Initialize workflow state
        initial_state: WorkflowState = {
            'job_id': job_id,
            'workflow_name': workflow_name,
            'current_step': 0,
            'total_steps': len(self.workflow_steps),
            'completed_steps': [],
            'agent_outputs': {},
            'shared_state': {},
            'input_data': input_data,
            'llm_calls': 0,
            'tokens_used': 0,
            'start_time': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            logger.info(f"Starting LangGraph execution for job {job_id}")
            
            # Execute graph with checkpointing
            config = {"configurable": {"thread_id": job_id}}
            
            final_state = None
            for state in self.compiled_graph.stream(initial_state, config):
                # state is a dict with node name as key
                if isinstance(state, dict):
                    # Extract the actual state from the node output
                    for node_name, node_state in state.items():
                        if isinstance(node_state, dict) and 'job_id' in node_state:
                            final_state = node_state
                            
                            # Save checkpoint after each node
                            self._save_checkpoint(final_state, node_name)
                            
                            # Progress update
                            if progress_callback:
                                progress = (final_state['current_step'] / final_state['total_steps']) * 100
                                progress_callback(progress, f"Completed: {node_name}")
            
            if final_state is None:
                final_state = initial_state
            
            # Mark completion
            final_state['end_time'] = datetime.now(timezone.utc).isoformat()
            
            # Calculate duration
            start = datetime.fromisoformat(final_state['start_time'])
            end = datetime.fromisoformat(final_state['end_time'])
            final_state['total_duration'] = (end - start).total_seconds()
            
            logger.info(
                f"LangGraph execution completed | "
                f"Job: {job_id} | "
                f"Steps: {len(final_state['completed_steps'])} | "
                f"LLM calls: {final_state['llm_calls']}"
            )
            
            # Convert to format expected by job_execution_engine
            return self._format_results(final_state)
            
        except Exception as e:
            logger.error(f"LangGraph execution failed: {e}", exc_info=True)
            return {
                'error': str(e),
                'error_traceback': traceback.format_exc(),
                'agent_outputs': initial_state.get('agent_outputs', {}),
                'shared_state': initial_state.get('shared_state', {}),
                'llm_calls': initial_state.get('llm_calls', 0),
                'tokens_used': initial_state.get('tokens_used', 0)
            }
    
    def _create_agent_node(self, agent_type: str, step_config: Dict[str, Any]) -> Callable:
        """Create a node function for an agent.
        
        Args:
            agent_type: Type of agent
            step_config: Step configuration
            
        Returns:
            Node function that takes and returns WorkflowState
        """
        def agent_node(state: WorkflowState) -> WorkflowState:
            """Execute agent and update state."""
            start_time = time.time()
            logger.info(f"Executing agent node: {agent_type}")
            
            try:
                # Create agent instance
                agent = self.agent_factory.create_agent(agent_type)
                
                if not agent:
                    raise ValueError(f"Failed to create agent: {agent_type}")
                
                # Prepare input from state
                agent_input = self._prepare_agent_input(agent_type, state)
                
                # Track LLM calls before
                llm_calls_before = state['llm_calls']
                
                # Create event and execute agent
                event = AgentEvent(
                    event_type=f"execute_{agent_type}",
                    data=agent_input,
                    source_agent="langgraph_executor",
                    correlation_id=state['job_id']
                )
                
                output_event = agent.execute(event)
                
                # Update state with agent output
                if output_event and output_event.data:
                    state['agent_outputs'][agent_type] = {
                        'status': 'completed',
                        'output_data': output_event.data,
                        'execution_time': time.time() - start_time,
                        'llm_calls': 1,  # Estimated, actual tracking happens in service
                        'tokens_used': 0
                    }
                    
                    # Merge output into shared state
                    state['shared_state'].update(output_event.data)
                else:
                    raise ValueError(f"Agent {agent_type} returned no output")
                
                # Update progress
                state['current_step'] += 1
                state['completed_steps'].append(agent_type)
                
                # Update conditional flags
                if agent_type == 'code_generation' and 'code_blocks' in output_event.data:
                    state['code_generated'] = len(output_event.data.get('code_blocks', [])) > 0
                
                logger.info(f"Agent {agent_type} completed in {time.time() - start_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Agent {agent_type} failed: {e}", exc_info=True)
                
                # Record failure
                if 'errors' not in state:
                    state['errors'] = []
                if 'failed_agents' not in state:
                    state['failed_agents'] = []
                
                state['errors'].append({
                    'agent': agent_type,
                    'error': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                state['failed_agents'].append(agent_type)
                
                state['agent_outputs'][agent_type] = {
                    'status': 'failed',
                    'output_data': {},
                    'error': str(e),
                    'execution_time': time.time() - start_time,
                    'llm_calls': 0,
                    'tokens_used': 0
                }
            
            return state
        
        return agent_node
    
    def _prepare_agent_input(self, agent_type: str, state: WorkflowState) -> Dict[str, Any]:
        """Prepare input for an agent from workflow state.
        
        Args:
            agent_type: Type of agent
            state: Current workflow state
            
        Returns:
            Input dict for agent
        """
        agent_input = dict(state['input_data'])
        shared = state['shared_state']
        
        # Agent-specific input preparation (mirrors sequential mode)
        if agent_type == 'topic_identification':
            agent_input['topic'] = state['input_data'].get('topic', '')
            
        elif agent_type in ['kb_ingestion', 'api_ingestion', 'blog_ingestion']:
            agent_input['topic'] = shared.get('topic', '')
            agent_input['family'] = shared.get('family', 'general')
            
        elif agent_type == 'duplication_check':
            agent_input['topic'] = shared.get('topic', '')
            agent_input['title'] = shared.get('title', '')
            
        elif agent_type == 'outline_creation':
            agent_input['topic'] = shared.get('topic', '')
            agent_input['title'] = shared.get('title', '')
            
        elif agent_type == 'introduction_writer':
            agent_input['outline'] = shared.get('outline', {})
            agent_input['topic'] = shared.get('topic', '')
            
        elif agent_type == 'section_writer':
            agent_input['outline'] = shared.get('outline', {})
            agent_input['topic'] = shared.get('topic', '')
            
        elif agent_type == 'code_generation':
            agent_input['sections'] = shared.get('sections', [])
            agent_input['topic'] = shared.get('topic', '')
            
        elif agent_type == 'code_validation':
            agent_input['code_blocks'] = shared.get('code_blocks', [])
            
        elif agent_type == 'conclusion_writer':
            agent_input['outline'] = shared.get('outline', {})
            agent_input['sections'] = shared.get('sections', [])
            
        elif agent_type == 'keyword_extraction':
            agent_input['content'] = shared.get('assembled_content', '')
            
        elif agent_type == 'keyword_injection':
            agent_input['content'] = shared.get('assembled_content', '')
            agent_input['keywords'] = shared.get('keywords', [])
            
        elif agent_type == 'seo_metadata':
            agent_input['title'] = shared.get('title', '')
            agent_input['content'] = shared.get('assembled_content', '')
            agent_input['keywords'] = shared.get('keywords', [])
            
        elif agent_type == 'frontmatter':
            agent_input['metadata'] = shared.get('seo_metadata', {})
            
        elif agent_type == 'content_assembly':
            agent_input['intro'] = shared.get('intro', '')
            agent_input['sections'] = shared.get('sections', [])
            agent_input['conclusion'] = shared.get('conclusion', '')
            agent_input['code_blocks'] = shared.get('code_blocks', [])
            
        elif agent_type == 'link_validation':
            agent_input['content'] = shared.get('assembled_content', '')
            
        elif agent_type == 'file_writer':
            agent_input['frontmatter'] = shared.get('frontmatter', '')
            agent_input['content'] = shared.get('assembled_content', '')
            agent_input['topic'] = shared.get('topic', '')
        
        return agent_input
    
    def _identify_parallel_groups(self) -> Dict[str, List[str]]:
        """Identify steps that can run in parallel.
        
        Returns:
            Dict mapping group names to list of agent types
        """
        parallel_groups = {}
        
        # Common parallel patterns
        content_writers = []
        for step in self.workflow_steps:
            agent_type = step.get('agent', step.get('id'))
            if agent_type in ['introduction_writer', 'conclusion_writer']:
                content_writers.append(agent_type)
        
        if len(content_writers) > 1:
            parallel_groups['content_writers'] = content_writers
        
        return parallel_groups
    
    def _add_edges(self, graph: StateGraph, parallel_groups: Dict[str, List[str]]):
        """Add edges to graph based on workflow order and dependencies.
        
        Args:
            graph: StateGraph to add edges to
            parallel_groups: Identified parallel execution groups
        """
        prev_node = None
        
        for i, step_config in enumerate(self.workflow_steps):
            agent_type = step_config.get('agent', step_config.get('id'))
            
            if prev_node is None:
                # First node connects from START
                pass
            else:
                # Add conditional edge for code validation path
                if prev_node == 'code_generation':
                    # Conditional: if code generated, go to validation, else skip
                    graph.add_conditional_edges(
                        prev_node,
                        self._should_validate_code,
                        {
                            'validate': 'code_validation',
                            'skip': agent_type
                        }
                    )
                else:
                    # Regular sequential edge
                    graph.add_edge(prev_node, agent_type)
            
            prev_node = agent_type
        
        # Connect last node to END
        if prev_node:
            graph.add_edge(prev_node, END)
    
    def _should_validate_code(self, state: WorkflowState) -> Literal['validate', 'skip']:
        """Determine if code validation should run.
        
        Args:
            state: Current workflow state
            
        Returns:
            'validate' if code was generated, 'skip' otherwise
        """
        return 'validate' if state.get('code_generated', False) else 'skip'
    
    def _save_checkpoint(self, state: WorkflowState, node_name: str):
        """Save checkpoint to CheckpointManager.
        
        Args:
            state: Current workflow state
            node_name: Name of the node that just completed
        """
        try:
            checkpoint_state = {
                'workflow_name': state['workflow_name'],
                'current_step': state['current_step'],
                'shared_state': state['shared_state'],
                'agent_outputs': state['agent_outputs'],
                'llm_calls': state['llm_calls'],
                'tokens_used': state['tokens_used'],
                'completed_steps': state['completed_steps']
            }
            
            checkpoint_id = self.checkpoint_manager.save(
                job_id=state['job_id'],
                step=node_name,
                state=checkpoint_state
            )
            
            if self.checkpoint_callback:
                self.checkpoint_callback(node_name, checkpoint_state)
            
            logger.debug(f"Checkpoint saved: {checkpoint_id}")
            
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")
    
    def _format_results(self, state: WorkflowState) -> Dict[str, Any]:
        """Format workflow state into expected results structure.
        
        Args:
            state: Final workflow state
            
        Returns:
            Results dict compatible with sequential executor format
        """
        return {
            'workflow_name': state['workflow_name'],
            'agent_outputs': state['agent_outputs'],
            'shared_state': state['shared_state'],
            'llm_calls': state['llm_calls'],
            'tokens_used': state['tokens_used'],
            'total_duration': state.get('total_duration', 0),
            'completed_steps': state['completed_steps'],
            'errors': state.get('errors', []),
            'failed_agents': state.get('failed_agents', [])
        }
# DOCGEN:LLM-FIRST@v4