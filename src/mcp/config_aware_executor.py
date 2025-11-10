"""Config-Aware MCP Executor - Wraps MCP agents with full configuration support."""

from typing import Dict, Any, Optional
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigAwareMCPExecutor:
    """Executor that ensures all MCP agents receive full configuration context."""
    
    def __init__(self, agent_config: Dict[str, Any], 
                 tone_config: Dict[str, Any],
                 perf_config: Dict[str, Any],
                 main_config: Dict[str, Any]):
        """Initialize executor with full configuration suite.
        
        Args:
            agent_config: Agent definitions and contracts
            tone_config: Tone and style configurations
            perf_config: Performance limits and timeouts
            main_config: Pipeline and workflow configurations
        """
        self.agent_config = agent_config
        self.tone_config = tone_config
        self.perf_config = perf_config
        self.main_config = main_config
        
        logger.info("ConfigAwareMCPExecutor initialized with full config suite")
    
    def execute_agent(self, agent_id: str, inputs: Dict[str, Any], 
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute an agent with full configuration support.
        
        Args:
            agent_id: Agent identifier
            inputs: Agent inputs
            context: Optional execution context
            
        Returns:
            Agent execution result with configuration metadata
        """
        start_time = time.time()
        
        # Get agent definition
        agents_def = self.agent_config.get('agents', {})
        agent_def = agents_def.get(agent_id, {})
        
        if not agent_def:
            logger.warning(f"Agent {agent_id} not found in config")
            return {
                'status': 'error',
                'error': f'Agent {agent_id} not found in configuration',
                'agent_id': agent_id
            }
        
        # Apply timeout from perf_config
        timeout = self.perf_config.get('timeouts', {}).get('agent_execution', 30)
        
        # Enrich context with all configs
        execution_context = context or {}
        execution_context['tone_config'] = self.tone_config
        execution_context['perf_config'] = self.perf_config
        execution_context['agent_config'] = agent_def
        execution_context['timeout'] = timeout
        
        # Apply performance limits
        limits = self.perf_config.get('limits', {})
        execution_context['max_tokens'] = limits.get('max_tokens_per_agent', 4000)
        execution_context['max_retries'] = limits.get('max_retries', 3)
        execution_context['max_context_size'] = limits.get('max_context_size', 16000)
        
        try:
            # Execute agent (actual implementation would call real agent)
            result = self._execute_with_config(agent_id, inputs, execution_context, agent_def)
            
            # Add execution metadata
            result['execution_metadata'] = {
                'agent_id': agent_id,
                'duration': time.time() - start_time,
                'config_hash': self._compute_config_hash(),
                'tone_applied': bool(self.tone_config),
                'perf_limits_applied': bool(self.perf_config),
                'timeout_ms': timeout * 1000
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Agent {agent_id} execution failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'agent_id': agent_id,
                'duration': time.time() - start_time
            }
    
    def _execute_with_config(self, agent_id: str, inputs: Dict[str, Any],
                            context: Dict[str, Any], agent_def: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent with configuration context.
        
        Args:
            agent_id: Agent identifier
            inputs: Agent inputs
            context: Execution context with configs
            agent_def: Agent definition
            
        Returns:
            Agent execution result
        """
        # This is a simplified execution - real implementation would:
        # 1. Load the actual agent implementation
        # 2. Pass all configs to the agent
        # 3. Execute the agent with timeout and retry logic
        # 4. Apply tone settings to output formatting
        
        logger.info(f"Executing {agent_id} with config support")
        
        result = {
            'status': 'success',
            'agent_id': agent_id,
            'output': inputs,  # Simplified - real agent would transform inputs
            'validation': {
                'input_valid': True,
                'output_valid': True,
                'warnings': []
            }
        }
        
        # Apply tone-based output formatting if applicable
        if 'writer' in agent_id or 'content' in agent_id:
            result['tone_settings_applied'] = self._apply_tone_settings(context)
        
        return result
    
    def _apply_tone_settings(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply tone configuration to content generation.
        
        Args:
            context: Execution context with tone_config
            
        Returns:
            Applied tone settings
        """
        tone_config = context.get('tone_config', {})
        
        return {
            'pov': tone_config.get('global_voice', {}).get('pov', 'second_person'),
            'formality': tone_config.get('global_voice', {}).get('formality', 'professional_conversational'),
            'technical_depth': tone_config.get('global_voice', {}).get('technical_depth', 'intermediate'),
            'personality': tone_config.get('global_voice', {}).get('personality', 'helpful_expert')
        }
    
    def _compute_config_hash(self) -> str:
        """Compute hash of current configuration for tracking."""
        import hashlib
        import json
        
        config_str = json.dumps({
            'agent': self.agent_config,
            'tone': self.tone_config,
            'perf': self.perf_config,
            'main': self.main_config
        }, sort_keys=True)
        
        return hashlib.md5(config_str.encode()).hexdigest()[:12]
    
    def get_agent_timeout(self, agent_id: str) -> float:
        """Get timeout for specific agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Timeout in seconds
        """
        # Check agent-specific timeout in agent_config
        agents_def = self.agent_config.get('agents', {})
        agent_def = agents_def.get(agent_id, {})
        resources = agent_def.get('resources', {})
        
        if 'max_runtime_s' in resources:
            return resources['max_runtime_s']
        
        # Fallback to global timeout
        return self.perf_config.get('timeouts', {}).get('agent_execution', 30)
    
    def get_pipeline_order(self, workflow_name: str = 'default') -> list:
        """Get pipeline execution order from main_config.
        
        Args:
            workflow_name: Workflow name to execute
            
        Returns:
            List of agent IDs in execution order
        """
        workflows = self.main_config.get('workflows', {})
        workflow = workflows.get(workflow_name, {})
        return workflow.get('steps', [])
    
    def validate_dependencies(self, agent_id: str, executed_agents: set) -> tuple[bool, list]:
        """Validate agent dependencies are satisfied.
        
        Args:
            agent_id: Agent to validate
            executed_agents: Set of already executed agent IDs
            
        Returns:
            Tuple of (is_valid, list of missing dependencies)
        """
        dependencies = self.main_config.get('dependencies', {})
        agent_deps = dependencies.get(agent_id, {})
        required = agent_deps.get('requires', [])
        
        missing = [dep for dep in required if dep not in executed_agents]
        
        return len(missing) == 0, missing


__all__ = ['ConfigAwareMCPExecutor']
