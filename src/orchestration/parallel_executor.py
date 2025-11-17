# parallel_executor.py
"""Parallel agent execution engine for concurrent workflow steps.

Provides thread-safe parallel execution of independent agents to reduce
total workflow execution time using ThreadPoolExecutor for I/O-bound operations.
"""

import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, Future, as_completed, TimeoutError, wait, FIRST_COMPLETED
from dataclasses import dataclass
from datetime import datetime, timezone
import traceback

from src.core import Agent, AgentEvent

logger = logging.getLogger(__name__)


@dataclass
class ParallelGroup:
    """Group of agents that can execute in parallel."""
    name: str
    agents: List[str]
    timeout: float = 300.0  # 5 minutes default
    
    def __str__(self):
        return f"ParallelGroup({self.name}, {len(self.agents)} agents)"


class ThreadSafeState:
    """Thread-safe wrapper for shared workflow state."""
    
    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        self._state = initial_state or {}
        self._lock = threading.RLock()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Thread-safe get operation."""
        with self._lock:
            return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Thread-safe set operation."""
        with self._lock:
            self._state[key] = value
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Thread-safe bulk update operation."""
        with self._lock:
            self._state.update(updates)
    
    def get_all(self) -> Dict[str, Any]:
        """Get a copy of entire state."""
        with self._lock:
            return dict(self._state)
    
    def merge(self, other_state: Dict[str, Any]) -> None:
        """Merge another state dict into this state."""
        with self._lock:
            for key, value in other_state.items():
                if key in self._state and isinstance(self._state[key], dict) and isinstance(value, dict):
                    # Deep merge for nested dicts
                    self._state[key].update(value)
                else:
                    self._state[key] = value


class ParallelExecutor:
    """Executes agents in parallel when dependencies allow.
    
    Uses ThreadPoolExecutor for I/O-bound agent operations (LLM calls).
    Maintains thread-safe shared state and handles failures gracefully.
    """
    
    def __init__(
        self,
        max_workers: int = 3,
        group_timeout: float = 300.0,
        fail_fast: bool = False
    ):
        """Initialize parallel executor.
        
        Args:
            max_workers: Maximum number of concurrent agents
            group_timeout: Timeout for entire parallel group in seconds
            fail_fast: If True, cancel remaining agents on first failure
        """
        self.max_workers = max_workers
        self.group_timeout = group_timeout
        self.fail_fast = fail_fast
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        logger.info(
            f"ParallelExecutor initialized: max_workers={max_workers}, "
            f"timeout={group_timeout}s, fail_fast={fail_fast}"
        )
    
    def __del__(self):
        """Cleanup executor on deletion."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
    
    def execute_parallel(
        self,
        agent_configs: List[Dict[str, Any]],
        agent_factory: Any,
        shared_state: ThreadSafeState,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Execute multiple agents in parallel.
        
        Args:
            agent_configs: List of agent configuration dicts
            agent_factory: Factory to create agent instances
            shared_state: Thread-safe shared state
            context: Execution context
            
        Returns:
            List of execution results (ordered by agent_configs)
        """
        if not agent_configs:
            return []
        
        agent_types = [cfg.get('agent', cfg.get('id')) for cfg in agent_configs]
        start_time = time.time()
        logger.info(f"⚡ Starting parallel execution of {len(agent_types)} agents: {agent_types}")
        
        # Submit all agents to executor
        future_to_agent = {}
        for agent_config in agent_configs:
            future = self._executor.submit(
                self._execute_single_agent,
                agent_config=agent_config,
                agent_factory=agent_factory,
                shared_state=shared_state,
                context=context
            )
            agent_type = agent_config.get('agent', agent_config.get('id'))
            future_to_agent[future] = (agent_type, agent_config)
        
        # Collect results with timeout
        results = {}
        failed_agents = []
        completed_count = 0
        
        try:
            # Wait for all futures with timeout
            done_futures = set()
            remaining_futures = set(future_to_agent.keys())
            timeout_per_future = self.group_timeout / len(agent_configs) if agent_configs else self.group_timeout
            
            while remaining_futures:
                # Wait for the next batch of futures to complete
                done, remaining_futures = wait(
                    remaining_futures, 
                    timeout=timeout_per_future,
                    return_when=FIRST_COMPLETED
                )
                
                for future in done:
                    agent_type, agent_config = future_to_agent[future]
                    
                    try:
                        result = future.result(timeout=1.0)  # Short timeout since it should be done
                        results[agent_type] = result
                        completed_count += 1
                        
                        if result['status'] == 'failed':
                            failed_agents.append(agent_type)
                            logger.error(f"❌ Agent {agent_type} failed: {result.get('error')}")
                            
                            if self.fail_fast:
                                # Cancel remaining futures
                                logger.warning(f"Fail-fast enabled, cancelling {len(remaining_futures)} remaining agents")
                                for f in remaining_futures:
                                    f.cancel()
                                remaining_futures.clear()
                                break
                        else:
                            logger.info(
                                f"✓ Agent {agent_type} completed "
                                f"({completed_count}/{len(agent_types)}) "
                                f"in {result['execution_time']:.2f}s"
                            )
                    
                    except TimeoutError:
                        logger.error(f"⏱ Agent {agent_type} timed out")
                        results[agent_type] = {
                            'agent_id': agent_type,
                            'status': 'failed',
                            'error': 'Agent execution timed out',
                            'output_data': {},
                            'execution_time': timeout_per_future,
                            'llm_calls': 0,
                            'tokens_used': 0
                        }
                        failed_agents.append(agent_type)
                        future.cancel()
                    
                    except Exception as e:
                        logger.error(f"❌ Exception collecting result for {agent_type}: {e}", exc_info=True)
                        results[agent_type] = {
                            'agent_id': agent_type,
                            'status': 'failed',
                            'error': str(e),
                            'output_data': {},
                            'execution_time': 0.0,
                            'llm_calls': 0,
                            'tokens_used': 0
                        }
                        failed_agents.append(agent_type)
                
                done_futures.update(done)
        
        except TimeoutError:
            logger.error(f"⏱ Parallel group timed out after {self.group_timeout}s")
            # Cancel remaining futures
            for future in future_to_agent:
                if not future.done():
                    future.cancel()
            
            # Mark incomplete agents as failed
            for future, (agent_type, _) in future_to_agent.items():
                if agent_type not in results:
                    results[agent_type] = {
                        'agent_id': agent_type,
                        'status': 'failed',
                        'error': 'Group timeout exceeded',
                        'output_data': {},
                        'execution_time': self.group_timeout,
                        'llm_calls': 0,
                        'tokens_used': 0
                    }
                    failed_agents.append(agent_type)
        
        except Exception as e:
            logger.error(f"❌ Unexpected error during parallel execution: {e}", exc_info=True)
            # Mark all incomplete agents as failed
            for future, (agent_type, _) in future_to_agent.items():
                if agent_type not in results:
                    results[agent_type] = {
                        'agent_id': agent_type,
                        'status': 'failed',
                        'error': f'Parallel execution error: {str(e)}',
                        'output_data': {},
                        'execution_time': 0.0,
                        'llm_calls': 0,
                        'tokens_used': 0
                    }
                    failed_agents.append(agent_type)
        
        # Return results in original order
        ordered_results = []
        for agent_config in agent_configs:
            agent_type = agent_config.get('agent', agent_config.get('id'))
            ordered_results.append(results.get(agent_type, {
                'agent_id': agent_type,
                'status': 'failed',
                'error': 'No result received',
                'output_data': {},
                'execution_time': 0.0,
                'llm_calls': 0,
                'tokens_used': 0
            }))
        
        total_time = time.time() - start_time
        success_count = len(ordered_results) - len(failed_agents)
        
        logger.info(
            f"⚡ Parallel execution completed in {total_time:.2f}s: "
            f"{success_count}/{len(ordered_results)} succeeded, {len(failed_agents)} failed"
        )
        
        if len(ordered_results) > 1:
            # Calculate speedup metrics
            avg_agent_time = sum(r.get('execution_time', 0) for r in ordered_results) / len(ordered_results)
            sequential_estimate = avg_agent_time * len(ordered_results)
            speedup = sequential_estimate / total_time if total_time > 0 else 1.0
            logger.info(f"📊 Estimated speedup: {speedup:.2f}× (sequential: {sequential_estimate:.2f}s, parallel: {total_time:.2f}s)")
        
        return ordered_results
    
    def _execute_single_agent(
        self,
        agent_config: Dict[str, Any],
        agent_factory: Any,
        shared_state: ThreadSafeState,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single agent (runs in worker thread).
        
        Args:
            agent_config: Agent configuration
            agent_factory: Factory to create agent
            shared_state: Thread-safe shared state
            context: Execution context
            
        Returns:
            Execution result dict
        """
        agent_type = agent_config.get('agent', agent_config.get('id'))
        start_time = time.time()
        
        result = {
            'agent_id': agent_type,
            'status': 'running',
            'output_data': {},
            'execution_time': 0.0,
            'llm_calls': 0,
            'tokens_used': 0
        }
        
        try:
            # Create agent instance
            agent = agent_factory.create_agent(agent_type)
            
            if not agent:
                raise ValueError(f"Failed to create agent: {agent_type}")
            
            # Prepare input from shared state
            agent_input = self._prepare_agent_input(agent_type, shared_state, context)
            
            # Create event and execute
            event = AgentEvent(
                event_type=f"execute_{agent_type}",
                data=agent_input,
                source_agent="parallel_executor",
                correlation_id=context.get('job_id', 'unknown')
            )
            
            output_event = agent.execute(event)
            
            if output_event and output_event.data:
                result['output_data'] = output_event.data
                result['status'] = 'completed'
                
                # Update shared state (thread-safe)
                shared_state.update(output_event.data)
                
            else:
                result['status'] = 'failed'
                result['error'] = 'No output from agent'
        
        except Exception as e:
            logger.error(f"Agent {agent_type} execution failed: {e}", exc_info=True)
            result['status'] = 'failed'
            result['error'] = str(e)
            result['traceback'] = traceback.format_exc()
        
        finally:
            result['execution_time'] = time.time() - start_time
        
        return result
    
    def _prepare_agent_input(
        self,
        agent_type: str,
        shared_state: ThreadSafeState,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare input for agent from shared state.
        
        Args:
            agent_type: Type of agent
            shared_state: Thread-safe shared state
            context: Execution context
            
        Returns:
            Input dict for agent
        """
        # Get thread-safe copy of state
        state = shared_state.get_all()
        agent_input = dict(context.get('input_data', {}))
        
        # Agent-specific input preparation
        if agent_type == 'kb_ingestion':
            agent_input['topic'] = state.get('topic', '')
            agent_input['family'] = state.get('family', 'general')
            
        elif agent_type == 'api_ingestion':
            agent_input['topic'] = state.get('topic', '')
            agent_input['family'] = state.get('family', 'general')
            
        elif agent_type == 'blog_ingestion':
            agent_input['topic'] = state.get('topic', '')
            agent_input['family'] = state.get('family', 'general')
            
        elif agent_type == 'introduction_writer':
            agent_input['outline'] = state.get('outline', {})
            agent_input['topic'] = state.get('topic', '')
            
        elif agent_type == 'section_writer':
            agent_input['outline'] = state.get('outline', {})
            agent_input['topic'] = state.get('topic', '')
            
        elif agent_type == 'conclusion_writer':
            agent_input['outline'] = state.get('outline', {})
            agent_input['sections'] = state.get('sections', [])
            
        elif agent_type == 'keyword_extraction':
            agent_input['content'] = state.get('assembled_content', '')
            
        elif agent_type == 'seo_metadata':
            agent_input['title'] = state.get('title', '')
            agent_input['content'] = state.get('assembled_content', '')
            agent_input['keywords'] = state.get('keywords', [])
        
        return agent_input
    
    def identify_parallel_groups(
        self,
        steps: List[Dict[str, Any]],
        dependencies: Dict[str, Dict[str, List[str]]]
    ) -> List[Tuple[List[Dict[str, Any]], bool]]:
        """Identify which steps can run in parallel.
        
        Args:
            steps: List of workflow steps
            dependencies: Dependency map from config
            
        Returns:
            List of tuples (step_configs, is_parallel)
        """
        groups = []
        
        # Known parallel patterns
        parallel_patterns = {
            'ingestion': ['kb_ingestion', 'api_ingestion', 'blog_ingestion'],
            'content_writers': ['introduction_writer', 'section_writer', 'conclusion_writer'],
        }
        
        i = 0
        while i < len(steps):
            step = steps[i]
            agent_type = step.get('agent', step.get('id'))
            
            # Check if this agent starts a parallel group
            group_found = False
            for pattern_name, pattern_agents in parallel_patterns.items():
                if agent_type in pattern_agents:
                    # Collect all consecutive agents in this pattern
                    group_steps = []
                    j = i
                    while j < len(steps):
                        next_agent = steps[j].get('agent', steps[j].get('id'))
                        if next_agent in pattern_agents:
                            group_steps.append(steps[j])
                            j += 1
                        else:
                            break
                    
                    if len(group_steps) > 1:
                        # Found a parallel group
                        groups.append((group_steps, True))
                        i = j
                        group_found = True
                        break
            
            if not group_found:
                # Single agent, not parallel
                groups.append(([step], False))
                i += 1
        
        return groups
    
    def shutdown(self):
        """Shutdown the executor and cleanup resources."""
        logger.info("Shutting down ParallelExecutor")
        self._executor.shutdown(wait=True)
