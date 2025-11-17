"""Production Agent Execution Engine - Real Agent Orchestration with Ollama Calls

This module implements production-ready agent execution with:
- Real agent instantiation and execution
- Proper data flow between agents
- Error handling and retries
- NoMockGate validation
- Real-time progress tracking
- Checkpoint management
"""

import logging
import time
import json
import traceback
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import threading

from src.core import EventBus, AgentEvent, Agent, Config
from src.services.services import LLMService, DatabaseService, EmbeddingService, GistService, LinkChecker, TrendsService
from src.services.services_fixes import NoMockGate, apply_llm_service_fixes
from .checkpoint_manager import CheckpointManager
from .mesh_executor import MeshExecutor

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentExecutionResult:
    """Result of agent execution"""
    agent_id: str
    status: AgentStatus
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    llm_calls: int = 0
    tokens_used: int = 0


class AgentFactory:
    """Factory for creating and managing agent instances"""
    
    def __init__(self, config: Config, event_bus: EventBus, services: Dict[str, Any]):
        self.config = config
        self.event_bus = event_bus
        self.services = services
        self._agent_cache: Dict[str, Agent] = {}
        self._agent_modules: Dict[str, Any] = {}
        
        # Discover and import agent modules
        self._discover_agents()
    
    def _discover_agents(self):
        """Discover all agent modules"""
        agents_dir = Path(__file__).parent.parent / "agents"
        
        # Import agent modules by category
        categories = ['ingestion', 'research', 'content', 'code', 'seo', 'publishing', 'support']
        
        for category in categories:
            category_dir = agents_dir / category
            if not category_dir.exists():
                continue
            
            for agent_file in category_dir.glob("*.py"):
                if agent_file.name.startswith("_"):
                    continue
                
                module_name = f"src.agents.{category}.{agent_file.stem}"
                try:
                    module = __import__(module_name, fromlist=[''])
                    self._agent_modules[agent_file.stem] = module
                    logger.debug(f"Loaded agent module: {module_name}")
                except Exception as e:
                    logger.error(f"Failed to load agent module {module_name}: {e}")
    
    def create_agent(self, agent_type: str) -> Optional[Agent]:
        """Create an agent instance by type
        
        Args:
            agent_type: Agent type (e.g., 'topic_identification', 'section_writer')
            
        Returns:
            Agent instance or None if not found
        """
        # Check cache first
        if agent_type in self._agent_cache:
            return self._agent_cache[agent_type]
        
        # Find and instantiate agent class
        agent_instance = self._instantiate_agent(agent_type)
        
        if agent_instance:
            self._agent_cache[agent_type] = agent_instance
            logger.info(f"Created agent: {agent_type}")
        else:
            logger.error(f"Failed to create agent: {agent_type}")
        
        return agent_instance
    
    def _instantiate_agent(self, agent_type: str) -> Optional[Agent]:
        """Instantiate agent based on type"""
        # Map agent types to their class names
        agent_class_map = {
            'topic_identification': ('research', 'TopicIdentificationAgent'),
            'kb_ingestion': ('ingestion', 'KBIngestionAgent'),
            'api_ingestion': ('ingestion', 'APIIngestionAgent'),
            'blog_ingestion': ('ingestion', 'BlogIngestionAgent'),
            'duplication_check': ('research', 'DuplicationCheckAgent'),  # Fixed: research not support
            'outline_creation': ('content', 'OutlineCreationAgent'),
            'introduction_writer': ('content', 'IntroductionWriterAgent'),
            'section_writer': ('content', 'SectionWriterAgent'),
            'code_generation': ('code', 'CodeGenerationAgent'),
            'code_validation': ('code', 'CodeValidationAgent'),
            'code_splitting': ('code', 'CodeSplittingAgent'),  # Added
            'license_injection': ('code', 'LicenseInjectionAgent'),  # Added
            'conclusion_writer': ('content', 'ConclusionWriterAgent'),
            'keyword_extraction': ('seo', 'KeywordExtractionAgent'),
            'keyword_injection': ('seo', 'KeywordInjectionAgent'),
            'seo_metadata': ('seo', 'SEOMetadataAgent'),
            'frontmatter': ('publishing', 'FrontmatterAgent'),
            'content_assembly': ('content', 'ContentAssemblyAgent'),
            'link_validation': ('publishing', 'LinkValidationAgent'),  # Fixed: publishing not support
            'file_writer': ('publishing', 'FileWriterAgent'),
        }
        
        if agent_type not in agent_class_map:
            logger.warning(f"Unknown agent type: {agent_type}")
            return None
        
        category, class_name = agent_class_map[agent_type]
        module_name = f"src.agents.{category}.{agent_type}"
        
        try:
            # Import module
            module = __import__(module_name, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            
            # Determine required services for this agent
            agent_kwargs = {'config': self.config, 'event_bus': self.event_bus}
            
            # Add services based on agent requirements
            if hasattr(agent_class, '__init__'):
                import inspect
                sig = inspect.signature(agent_class.__init__)
                params = sig.parameters
                
                if 'llm_service' in params:
                    agent_kwargs['llm_service'] = self.services.get('llm')
                if 'db_service' in params:
                    agent_kwargs['db_service'] = self.services.get('database')
                if 'embedding_service' in params:
                    agent_kwargs['embedding_service'] = self.services.get('embedding')
                if 'gist_service' in params:
                    agent_kwargs['gist_service'] = self.services.get('gist')
                if 'link_checker' in params:
                    agent_kwargs['link_checker'] = self.services.get('link_checker')
                if 'trends_service' in params:
                    agent_kwargs['trends_service'] = self.services.get('trends')
            
            # Create instance
            return agent_class(**agent_kwargs)
            
        except Exception as e:
            logger.error(f"Failed to instantiate {class_name}: {e}", exc_info=True)
            return None


class ProductionExecutionEngine:
    """Production-ready agent execution engine with real Ollama calls"""
    
    def __init__(self, config: Config):
        self.config = config
        self.event_bus = EventBus()
        
        # Initialize services
        self.services = self._initialize_services()
        
        # Apply LLM service fixes (NoMockGate)
        if 'llm' in self.services:
            apply_llm_service_fixes(self.services['llm'].__class__)
            self.services['llm'].no_mock_gate = NoMockGate()
        
        # Initialize agent factory
        self.agent_factory = AgentFactory(config, self.event_bus, self.services)
        
        # Checkpoint manager
        self.checkpoint_manager = CheckpointManager(Path(config.checkpoint_dir))
        
        # Mesh executor (optional)
        self.mesh_executor = None
        mesh_config = getattr(config, 'mesh', {})
        if isinstance(mesh_config, dict) and mesh_config.get('enabled', False):
            max_hops = mesh_config.get('max_hops', 10)
            routing_timeout = mesh_config.get('routing_timeout_seconds', 5)
            circuit_breaker_config = mesh_config.get('circuit_breaker', {})
            enable_circuit_breaker = circuit_breaker_config.get('enabled', True) if isinstance(circuit_breaker_config, dict) else True
            
            self.mesh_executor = MeshExecutor(
                config=config,
                event_bus=self.event_bus,
                agent_factory=self.agent_factory,
                max_hops=max_hops,
                routing_timeout=routing_timeout,
                enable_circuit_breaker=enable_circuit_breaker
            )
            # Discover agents for mesh
            self.mesh_executor.discover_agents()
            logger.info(f"Mesh orchestration enabled with max_hops={max_hops}")
        
        # Execution state
        self._execution_state: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def _initialize_services(self) -> Dict[str, Any]:
        """Initialize all required services"""
        services = {}
        
        try:
            # LLM Service
            services['llm'] = LLMService(self.config)
            logger.info("✓ LLM Service initialized")
            
            # Database Service
            services['database'] = DatabaseService(self.config)
            logger.info("✓ Database Service initialized")
            
            # Embedding Service
            services['embedding'] = EmbeddingService(self.config)
            logger.info("✓ Embedding Service initialized")
            
            # Gist Service
            if self.config.github_token:
                services['gist'] = GistService(self.config.github_token)
                logger.info("✓ Gist Service initialized")
            
            # Link Checker
            services['link_checker'] = LinkChecker()
            logger.info("✓ Link Checker initialized")
            
            # Trends Service
            services['trends'] = TrendsService()
            logger.info("✓ Trends Service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}", exc_info=True)
            raise
        
        return services
    
    def execute_pipeline(
        self,
        workflow_name: str,
        steps: List[Dict[str, Any]],
        input_data: Dict[str, Any],
        job_id: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        checkpoint_callback: Optional[Callable[[str, Dict], None]] = None
    ) -> Dict[str, Any]:
        """Execute agent pipeline with real agent calls
        
        Args:
            workflow_name: Name of workflow being executed
            steps: List of step definitions
            input_data: Initial input data
            job_id: Job identifier
            progress_callback: Callback for progress updates (progress%, message)
            checkpoint_callback: Callback for checkpoint creation
            
        Returns:
            Final execution results with all agent outputs
        """
        logger.info(f"Starting pipeline execution: {workflow_name} (job_id: {job_id})")
        logger.info(f"Total steps: {len(steps)}")
        
        # Check if mesh mode is enabled
        use_mesh = getattr(self.config, 'use_mesh', False) or input_data.get('execution_mode') == 'mesh'
        
        if use_mesh and self.mesh_executor:
            # Mesh execution path
            try:
                initial_agent_type = input_data.get('initial_agent') or steps[0].get('agent', steps[0].get('id'))
                
                result = self.mesh_executor.execute_mesh_workflow(
                    workflow_name=workflow_name,
                    initial_agent_type=initial_agent_type,
                    input_data=input_data,
                    job_id=job_id,
                    progress_callback=progress_callback
                )
                
                # Convert mesh result to standard context format
                return {
                    'workflow_name': workflow_name,
                    'job_id': job_id,
                    'execution_mode': 'mesh',
                    'success': result.success,
                    'execution_time': result.execution_time,
                    'total_hops': result.total_hops,
                    'agents_executed': result.agents_executed,
                    'agent_outputs': result.final_output,
                    'shared_state': result.final_output,
                    'execution_trace': result.execution_trace,
                    'error': result.error,
                    'mesh_stats': result.metadata
                }
            except Exception as e:
                logger.error(f"Mesh execution failed: {e}. Falling back to sequential mode.", exc_info=True)
                use_mesh = False
        
        # Check if LangGraph mode is enabled
        use_langgraph = getattr(self.config, 'use_langgraph', False)
        
        if use_langgraph:
            # LangGraph execution path
            try:
                return self._execute_langgraph_pipeline(
                    workflow_name=workflow_name,
                    steps=steps,
                    input_data=input_data,
                    job_id=job_id,
                    progress_callback=progress_callback,
                    checkpoint_callback=checkpoint_callback
                )
            except Exception as e:
                logger.error(f"LangGraph execution failed: {e}. Falling back to sequential mode.")
                # Fall back to sequential mode
                use_langgraph = False
        
        # Initialize execution context
        context = {
            'workflow_name': workflow_name,
            'job_id': job_id,
            'input_data': input_data,
            'agent_outputs': {},
            'shared_state': {},
            'start_time': datetime.now(timezone.utc),
            'llm_calls': 0,
            'tokens_used': 0
        }
        
        # Try to restore from checkpoint
        checkpoint_data = self.checkpoint_manager.load_checkpoint(job_id)
        if checkpoint_data:
            logger.info(f"Resuming from checkpoint at step {checkpoint_data.get('current_step', 0)}")
            context.update(checkpoint_data)
        
        total_steps = len(steps)
        start_step = context.get('current_step', 0)
        
<<<<<<< Updated upstream
=======
        # Check if parallel execution is enabled
        use_parallel = self.parallel_executor is not None
        
>>>>>>> Stashed changes
        try:
            if use_parallel:
                # Parallel execution path
                self._execute_parallel_pipeline(
                    steps=steps,
                    context=context,
<<<<<<< Updated upstream
                    step_config=step_config
                )
                
                # Store result
                context['agent_outputs'][agent_type] = result
                context['llm_calls'] += result.llm_calls
                context['tokens_used'] += result.tokens_used
                
                # Check for failures
                if result.status == AgentStatus.FAILED:
                    logger.error(f"Agent {agent_type} failed: {result.error}")
                    context['error'] = result.error
                    context['failed_agent'] = agent_type
                    break
                
                # Create checkpoint
                context['current_step'] = step_num
                checkpoint_data = self._create_checkpoint(context)
                self.checkpoint_manager.save_checkpoint(job_id, checkpoint_data)
                
                if checkpoint_callback:
                    checkpoint_callback(agent_type, checkpoint_data)
                
                logger.info(
                    f"✓ Agent {agent_type} completed in {result.execution_time:.2f}s "
                    f"(LLM calls: {result.llm_calls})"
=======
                    job_id=job_id,
                    total_steps=total_steps,
                    start_step=start_step,
                    progress_callback=progress_callback,
                    checkpoint_callback=checkpoint_callback
                )
            else:
                # Sequential execution path (original)
                self._execute_sequential_pipeline(
                    steps=steps,
                    context=context,
                    job_id=job_id,
                    total_steps=total_steps,
                    start_step=start_step,
                    progress_callback=progress_callback,
                    checkpoint_callback=checkpoint_callback
>>>>>>> Stashed changes
                )
            
            # Final progress
            if progress_callback:
                progress_callback(100.0, "Pipeline completed")
            
            # Calculate execution stats
            context['end_time'] = datetime.now(timezone.utc)
            context['total_duration'] = (
                context['end_time'] - context['start_time']
            ).total_seconds()
            
            logger.info(
                f"Pipeline completed: {workflow_name} | "
                f"Duration: {context['total_duration']:.2f}s | "
                f"LLM calls: {context['llm_calls']} | "
                f"Tokens: {context['tokens_used']}"
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            context['error'] = str(e)
            context['error_traceback'] = traceback.format_exc()
            raise
    
    def _execute_agent(
        self,
        agent_type: str,
        context: Dict[str, Any],
        step_config: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Execute a single agent
        
        Args:
            agent_type: Type of agent to execute
            context: Execution context with shared state
            step_config: Step configuration
            
        Returns:
            AgentExecutionResult with execution details
        """
        start_time = time.time()
        result = AgentExecutionResult(agent_id=agent_type, status=AgentStatus.RUNNING)
        
        try:
            # Create agent instance
            agent = self.agent_factory.create_agent(agent_type)
            
            if not agent:
                result.status = AgentStatus.FAILED
                result.error = f"Failed to create agent: {agent_type}"
                return result
            
            # Prepare input data for agent
            agent_input = self._prepare_agent_input(agent_type, context)
            
            # Track LLM calls before execution
            llm_calls_before = getattr(self.services.get('llm'), '_call_count', 0)
            
            # Create and publish agent event
            event = AgentEvent(
                event_type=f"execute_{agent_type}",
                data=agent_input,
                source_agent="orchestrator",
                correlation_id=context['job_id']
            )
            
            # Execute agent
            logger.debug(f"Executing agent {agent_type} with input keys: {list(agent_input.keys())}")
            output_event = agent.execute(event)
            
            # Track LLM calls after execution
            llm_calls_after = getattr(self.services.get('llm'), '_call_count', 0)
            result.llm_calls = llm_calls_after - llm_calls_before
            
            # Validate output with NoMockGate
            if output_event and output_event.data:
                if hasattr(self.services.get('llm'), 'no_mock_gate'):
                    no_mock_gate = self.services['llm'].no_mock_gate
                    is_valid, reason = no_mock_gate.validate_response(output_event.data)
                    
                    if not is_valid:
                        result.status = AgentStatus.FAILED
                        result.error = f"NoMockGate validation failed: {reason}"
                        logger.error(f"Agent {agent_type} produced mock content: {reason}")
                        return result
            
            # Store output
            if output_event:
                result.output_data = output_event.data
                result.status = AgentStatus.COMPLETED
                
                # Update shared state
                context['shared_state'].update(output_event.data)
                
                logger.debug(f"Agent {agent_type} output keys: {list(output_event.data.keys())}")
            else:
                result.status = AgentStatus.FAILED
                result.error = "Agent returned no output"
            
        except Exception as e:
            logger.error(f"Agent {agent_type} execution failed: {e}", exc_info=True)
            result.status = AgentStatus.FAILED
            result.error = str(e)
        
        finally:
            result.execution_time = time.time() - start_time
        
        return result
    
    def _prepare_agent_input(self, agent_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input data for agent based on previous outputs
        
        Args:
            agent_type: Agent type
            context: Execution context
            
        Returns:
            Input data dictionary for agent
        """
        agent_input = {}
        
        # Include initial input data
        agent_input.update(context['input_data'])
        
        # Include shared state
        agent_input.update(context['shared_state'])
        
        # Add agent-specific context from previous outputs
        agent_outputs = context['agent_outputs']
        
        # Map dependencies for each agent type
        if agent_type == 'topic_identification':
            agent_input['topic'] = context['input_data'].get('topic', '')
        
        elif agent_type in ['kb_ingestion', 'api_ingestion', 'blog_ingestion']:
            if 'topic' in context['shared_state']:
                agent_input['topic'] = context['shared_state']['topic']
        
        elif agent_type == 'duplication_check':
            agent_input['context'] = context['shared_state'].get('context', [])
        
        elif agent_type == 'outline_creation':
            agent_input['topic'] = context['shared_state'].get('topic', '')
            agent_input['context'] = context['shared_state'].get('context', [])
        
        elif agent_type == 'introduction_writer':
            agent_input['outline'] = context['shared_state'].get('outline', {})
            agent_input['context'] = context['shared_state'].get('context', [])
        
        elif agent_type == 'section_writer':
            agent_input['outline'] = context['shared_state'].get('outline', {})
            agent_input['intro'] = context['shared_state'].get('intro', '')
            agent_input['context'] = context['shared_state'].get('context', [])
        
        elif agent_type == 'code_generation':
            agent_input['outline'] = context['shared_state'].get('outline', {})
            agent_input['api_context'] = context['shared_state'].get('api_context', [])
        
        elif agent_type == 'code_validation':
            agent_input['code_blocks'] = context['shared_state'].get('code_blocks', [])
            agent_input['api_context'] = context['shared_state'].get('api_context', [])
        
        elif agent_type == 'code_splitting':
            agent_input['code_blocks'] = context['shared_state'].get('code_blocks', [])
        
        elif agent_type == 'license_injection':
            agent_input['code_blocks'] = context['shared_state'].get('code_blocks', [])
        
        elif agent_type == 'conclusion_writer':
            agent_input['outline'] = context['shared_state'].get('outline', {})
            agent_input['sections'] = context['shared_state'].get('sections', [])
        
        elif agent_type == 'keyword_extraction':
            agent_input['content'] = context['shared_state'].get('assembled_content', '')
        
        elif agent_type == 'keyword_injection':
            agent_input['content'] = context['shared_state'].get('assembled_content', '')
            agent_input['keywords'] = context['shared_state'].get('keywords', [])
        
        elif agent_type == 'seo_metadata':
            agent_input['title'] = context['shared_state'].get('title', '')
            agent_input['content'] = context['shared_state'].get('assembled_content', '')
            agent_input['keywords'] = context['shared_state'].get('keywords', [])
        
        elif agent_type == 'frontmatter':
            agent_input['metadata'] = context['shared_state'].get('seo_metadata', {})
        
        elif agent_type == 'content_assembly':
            agent_input['intro'] = context['shared_state'].get('intro', '')
            agent_input['sections'] = context['shared_state'].get('sections', [])
            agent_input['conclusion'] = context['shared_state'].get('conclusion', '')
            agent_input['code_blocks'] = context['shared_state'].get('code_blocks', [])
        
        elif agent_type == 'link_validation':
            agent_input['content'] = context['shared_state'].get('assembled_content', '')
        
        elif agent_type == 'file_writer':
            agent_input['frontmatter'] = context['shared_state'].get('frontmatter', '')
            agent_input['content'] = context['shared_state'].get('assembled_content', '')
            agent_input['topic'] = context['shared_state'].get('topic', '')
        
        return agent_input
    
    def _execute_langgraph_pipeline(
        self,
        workflow_name: str,
        steps: List[Dict[str, Any]],
        input_data: Dict[str, Any],
        job_id: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        checkpoint_callback: Optional[Callable[[str, Dict], None]] = None
    ) -> Dict[str, Any]:
        """Execute pipeline using LangGraph.
        
        Args:
            workflow_name: Name of workflow being executed
            steps: List of step definitions
            input_data: Initial input data
            job_id: Job identifier
            progress_callback: Callback for progress updates
            checkpoint_callback: Callback for checkpoint creation
            
        Returns:
            Final execution results
        """
        try:
            from .langgraph_executor import LangGraphExecutor, LANGGRAPH_AVAILABLE
            
            if not LANGGRAPH_AVAILABLE:
                raise ImportError("LangGraph not installed")
            
            logger.info(f"Using LangGraph execution mode for workflow: {workflow_name}")
            
            # Create LangGraph executor
            executor = LangGraphExecutor(
                config=self.config,
                workflow_steps=steps,
                agent_factory=self.agent_factory,
                checkpoint_manager=self.checkpoint_manager
            )
            
            # Execute workflow
            results = executor.execute(
                input_data=input_data,
                job_id=job_id,
                workflow_name=workflow_name,
                progress_callback=progress_callback,
                checkpoint_callback=checkpoint_callback
            )
            
            logger.info(f"LangGraph execution completed for job {job_id}")
            return results
            
        except ImportError as e:
            logger.error(f"LangGraph not available: {e}")
            raise
        except Exception as e:
            logger.error(f"LangGraph execution error: {e}",             exc_info=True)
            raise
