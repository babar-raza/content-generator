"""Mesh Executor for Dynamic Agent Orchestration

Implements mesh orchestration mode where agents can dynamically request services
from other agents on-demand, enabling flexible and adaptive workflows.
"""

import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field

from src.core import Config, EventBus, AgentEvent
from .agent_registry import AgentRegistry, AgentHealth
from .mesh_router import MeshRouter, RouteRequest, RouteResponse

logger = logging.getLogger(__name__)


@dataclass
class MeshExecutionContext:
    """Context for mesh execution"""
    job_id: str
    workflow_name: str
    initial_agent_id: str
    input_data: Dict[str, Any]
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    execution_trace: List[Dict[str, Any]] = field(default_factory=list)
    accumulated_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MeshExecutionResult:
    """Result of mesh workflow execution"""
    job_id: str
    success: bool
    execution_time: float
    total_hops: int
    agents_executed: List[str]
    final_output: Dict[str, Any]
    execution_trace: List[Dict[str, Any]]
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'job_id': self.job_id,
            'success': self.success,
            'execution_time': self.execution_time,
            'total_hops': self.total_hops,
            'agents_executed': self.agents_executed,
            'final_output': self.final_output,
            'execution_trace': self.execution_trace,
            'error': self.error,
            'metadata': self.metadata
        }


class MeshExecutor:
    """Executor for mesh orchestration workflows
    
    Responsibilities:
    - Execute mesh workflows with dynamic agent discovery
    - Manage agent lifecycle and communication
    - Track execution trace and metrics
    - Handle errors and circuit breaking
    - Provide real-time progress updates
    """
    
    def __init__(
        self,
        config: Config,
        event_bus: EventBus,
        agent_factory,
        max_hops: int = 10,
        routing_timeout: int = 5,
        enable_circuit_breaker: bool = True
    ):
        self.config = config
        self.event_bus = event_bus
        self.agent_factory = agent_factory
        
        # Initialize registry and router
        self.registry = AgentRegistry()
        self.router = MeshRouter(
            registry=self.registry,
            max_hops=max_hops,
            routing_timeout_seconds=routing_timeout,
            enable_circuit_breaker=enable_circuit_breaker
        )
        
        # Execution state
        self._active_contexts: Dict[str, MeshExecutionContext] = {}
        
        logger.info(f"MeshExecutor initialized (max_hops={max_hops}, circuit_breaker={enable_circuit_breaker})")
    
    def discover_agents(self) -> List[Dict[str, Any]]:
        """Discover and register all available agents
        
        Returns:
            List of discovered agent information
        """
        logger.info("Discovering agents for mesh orchestration")
        
        # Agent type to capabilities mapping
        agent_capabilities = {
            'topic_identification': ['topic_discovery', 'content_planning'],
            'kb_ingestion': ['knowledge_base_processing', 'content_extraction'],
            'api_ingestion': ['api_documentation', 'technical_reference'],
            'blog_ingestion': ['blog_analysis', 'content_research'],
            'duplication_check': ['duplicate_detection', 'content_validation'],
            'outline_creation': ['content_structuring', 'outline_generation'],
            'introduction_writer': ['introduction_writing', 'content_creation'],
            'section_writer': ['section_writing', 'content_creation'],
            'code_generation': ['code_creation', 'example_generation'],
            'code_validation': ['code_verification', 'syntax_checking'],
            'conclusion_writer': ['conclusion_writing', 'content_creation'],
            'keyword_extraction': ['keyword_analysis', 'seo_research'],
            'keyword_injection': ['keyword_optimization', 'seo_enhancement'],
            'seo_metadata': ['metadata_generation', 'seo_optimization'],
            'frontmatter': ['frontmatter_creation', 'metadata_formatting'],
            'content_assembly': ['content_aggregation', 'document_assembly'],
            'link_validation': ['link_checking', 'url_validation'],
            'file_writer': ['file_output', 'document_publishing']
        }
        
        discovered = []
        
        for agent_type, capabilities in agent_capabilities.items():
            try:
                # Create agent instance to verify it exists
                agent = self.agent_factory.create_agent(agent_type)
                if not agent:
                    logger.warning(f"Could not create agent: {agent_type}")
                    continue
                
                # Register agent
                agent_id = f"{agent_type}_mesh_{uuid.uuid4().hex[:8]}"
                success = self.registry.register_agent(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    capabilities=capabilities,
                    metadata={
                        'discovered_at': datetime.now(timezone.utc).isoformat(),
                        'instance': agent
                    }
                )
                
                if success:
                    discovered.append({
                        'agent_id': agent_id,
                        'agent_type': agent_type,
                        'capabilities': capabilities
                    })
                    logger.info(f"Discovered and registered agent: {agent_type}")
                
            except Exception as e:
                logger.error(f"Failed to discover agent {agent_type}: {e}")
        
        logger.info(f"Agent discovery complete: {len(discovered)} agents registered")
        return discovered
    
    def execute_mesh_workflow(
        self,
        workflow_name: str,
        initial_agent_type: str,
        input_data: Dict[str, Any],
        job_id: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> MeshExecutionResult:
        """Execute a mesh workflow starting from initial agent
        
        Args:
            workflow_name: Name of the workflow
            initial_agent_type: Type of agent to start with
            input_data: Initial input data
            job_id: Job identifier
            progress_callback: Optional progress callback
            
        Returns:
            Mesh execution result
        """
        start_time = time.time()
        logger.info(f"Starting mesh workflow: {workflow_name} (job_id: {job_id})")
        
        # Reset router state
        self.router.reset_execution_state()
        
        # Find initial agent
        initial_registration = self.registry.find_by_type(initial_agent_type)
        if not initial_registration:
            error_msg = f"Initial agent not found: {initial_agent_type}"
            logger.error(error_msg)
            return MeshExecutionResult(
                job_id=job_id,
                success=False,
                execution_time=time.time() - start_time,
                total_hops=0,
                agents_executed=[],
                final_output={},
                execution_trace=[],
                error=error_msg
            )
        
        # Create execution context
        context = MeshExecutionContext(
            job_id=job_id,
            workflow_name=workflow_name,
            initial_agent_id=initial_registration.agent_id,
            input_data=input_data
        )
        self._active_contexts[job_id] = context
        
        # Progress update
        if progress_callback:
            progress_callback(0.0, f"Starting with agent: {initial_agent_type}")
        
        try:
            # Execute initial agent
            current_agent_id = initial_registration.agent_id
            current_data = input_data.copy()
            agents_executed = []
            
            # Main execution loop
            while current_agent_id and len(agents_executed) < self.router.max_hops:
                # Get agent
                registration = self.registry.get_agent(current_agent_id)
                if not registration:
                    logger.error(f"Agent not found in registry: {current_agent_id}")
                    break
                
                # Execute agent
                agent_result = self._execute_agent(
                    registration=registration,
                    input_data=current_data,
                    context=context
                )
                
                # Record execution
                agents_executed.append(current_agent_id)
                context.execution_trace.append({
                    'agent_id': current_agent_id,
                    'agent_type': registration.agent_type,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'success': agent_result.get('success', False),
                    'execution_time': agent_result.get('execution_time', 0.0)
                })
                
                # Update progress
                if progress_callback:
                    progress = (len(agents_executed) / self.router.max_hops) * 100
                    progress_callback(progress, f"Executed: {registration.agent_type}")
                
                # Check if agent succeeded
                if not agent_result.get('success', False):
                    logger.error(f"Agent execution failed: {current_agent_id}")
                    self.router.record_failure(current_agent_id)
                    break
                
                self.router.record_success(current_agent_id)
                
                # Accumulate output data
                output_data = agent_result.get('output_data', {})
                context.accumulated_data.update(output_data)
                
                # Check if agent requests another agent (via special key in output)
                next_capability = agent_result.get('request_capability')
                if not next_capability:
                    # Workflow complete
                    logger.info(f"Mesh workflow complete after {len(agents_executed)} hops")
                    break
                
                # Route to next agent
                route_request = RouteRequest(
                    request_id=str(uuid.uuid4()),
                    source_agent_id=current_agent_id,
                    capability=next_capability,
                    input_data=context.accumulated_data,
                    context={'job_id': job_id}
                )
                
                route_response = self.router.route_to_agent(route_request)
                
                if not route_response.success:
                    logger.error(f"Routing failed: {route_response.error}")
                    break
                
                # Continue with next agent
                current_agent_id = route_response.target_agent_id
                current_data = context.accumulated_data.copy()
            
            # Create result
            execution_time = time.time() - start_time
            
            result = MeshExecutionResult(
                job_id=job_id,
                success=True,
                execution_time=execution_time,
                total_hops=len(agents_executed),
                agents_executed=agents_executed,
                final_output=context.accumulated_data,
                execution_trace=context.execution_trace,
                metadata={
                    'workflow_name': workflow_name,
                    'router_stats': self.router.get_stats()
                }
            )
            
            logger.info(f"Mesh workflow completed: {workflow_name} in {execution_time:.2f}s")
            
            if progress_callback:
                progress_callback(100.0, "Workflow complete")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Mesh workflow execution failed: {e}"
            logger.error(error_msg, exc_info=True)
            
            return MeshExecutionResult(
                job_id=job_id,
                success=False,
                execution_time=execution_time,
                total_hops=len(context.execution_trace),
                agents_executed=[t['agent_id'] for t in context.execution_trace],
                final_output=context.accumulated_data,
                execution_trace=context.execution_trace,
                error=error_msg
            )
        
        finally:
            # Cleanup
            if job_id in self._active_contexts:
                del self._active_contexts[job_id]
    
    def _execute_agent(
        self,
        registration,
        input_data: Dict[str, Any],
        context: MeshExecutionContext
    ) -> Dict[str, Any]:
        """Execute a single agent
        
        Args:
            registration: Agent registration information
            input_data: Input data for agent
            context: Execution context
            
        Returns:
            Agent execution result
        """
        start_time = time.time()
        
        try:
            # Get agent instance from metadata
            agent = registration.metadata.get('instance')
            if not agent:
                # Create new instance if not cached
                agent = self.agent_factory.create_agent(registration.agent_type)
                if not agent:
                    return {
                        'success': False,
                        'error': f"Failed to create agent: {registration.agent_type}"
                    }
                registration.metadata['instance'] = agent
            
            # Create agent event
            event = AgentEvent(
                event_type=f"{registration.agent_type}.execute",
                source_agent="mesh_executor",
                correlation_id=context.job_id,
                data=input_data
            )
            
            # Execute agent
            result_event = agent.execute(event)
            
            execution_time = time.time() - start_time
            
            if result_event:
                return {
                    'success': True,
                    'output_data': result_event.data,
                    'execution_time': execution_time,
                    'request_capability': result_event.data.get('_mesh_request_capability')
                }
            else:
                return {
                    'success': False,
                    'error': "Agent returned no result",
                    'execution_time': execution_time
                }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Agent execution failed: {registration.agent_type}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'execution_time': execution_time
            }
    
    def get_mesh_trace(self, job_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get execution trace for a job
        
        Args:
            job_id: Job identifier
            
        Returns:
            Execution trace if found, None otherwise
        """
        context = self._active_contexts.get(job_id)
        if context:
            return context.execution_trace
        return None
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents
        
        Returns:
            List of agent information
        """
        agents = self.registry.list_available(healthy_only=False)
        return [
            {
                'agent_id': a.agent_id,
                'agent_type': a.agent_type,
                'capabilities': a.capabilities,
                'health': a.health_status.value,
                'load': a.current_load,
                'max_capacity': a.max_capacity
            }
            for a in agents
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get mesh executor statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            'registry_stats': self.registry.get_stats(),
            'router_stats': self.router.get_stats(),
            'active_contexts': len(self._active_contexts)
        }
