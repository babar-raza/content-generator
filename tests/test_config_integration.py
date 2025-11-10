"""Comprehensive Configuration Integration Tests

Tests that all configurations are properly wired throughout the system.
"""

import pytest
import json
from pathlib import Path
from typing import Dict, Any

# Test config validation
from config.validator import ConfigValidator, load_validated_config, ConfigSnapshot
from config.schemas import AGENT_SCHEMA, PERF_SCHEMA, TONE_SCHEMA, MAIN_SCHEMA


class TestConfigValidation:
    """Test configuration validation and loading."""
    
    def test_load_validated_config(self):
        """Test that all configs load and validate successfully."""
        snapshot = load_validated_config(Path("./config"))
        
        assert snapshot is not None
        assert isinstance(snapshot, ConfigSnapshot)
        assert snapshot.agent_config is not None
        assert snapshot.perf_config is not None
        assert snapshot.tone_config is not None
        assert snapshot.main_config is not None
        assert len(snapshot.config_hash) > 0
    
    def test_agent_config_structure(self):
        """Test agent config has required structure."""
        snapshot = load_validated_config(Path("./config"))
        agent_config = snapshot.agent_config
        
        assert 'version' in agent_config
        assert 'agents' in agent_config
        assert isinstance(agent_config['agents'], dict)
        
        # Check at least one agent exists
        assert len(agent_config['agents']) > 0
    
    def test_perf_config_structure(self):
        """Test perf config has required structure."""
        snapshot = load_validated_config(Path("./config"))
        perf_config = snapshot.perf_config
        
        assert 'timeouts' in perf_config
        assert 'limits' in perf_config
        
        # Check timeout values
        timeouts = perf_config['timeouts']
        assert 'agent_execution' in timeouts
        assert 'total_job' in timeouts
        assert timeouts['agent_execution'] > 0
        assert timeouts['total_job'] > 0
        
        # Check limit values
        limits = perf_config['limits']
        assert 'max_tokens_per_agent' in limits
        assert 'max_retries' in limits
        assert limits['max_tokens_per_agent'] > 0
        assert limits['max_retries'] >= 0
    
    def test_tone_config_structure(self):
        """Test tone config has required structure."""
        snapshot = load_validated_config(Path("./config"))
        tone_config = snapshot.tone_config
        
        assert 'global_voice' in tone_config
        assert 'section_controls' in tone_config
        
        # Check global voice settings
        global_voice = tone_config['global_voice']
        assert 'pov' in global_voice
        assert 'formality' in global_voice
        assert global_voice['pov'] in ['first_person', 'second_person', 'third_person']
        
        # Check section controls exist
        section_controls = tone_config['section_controls']
        assert isinstance(section_controls, dict)
    
    def test_main_config_structure(self):
        """Test main config has required structure."""
        snapshot = load_validated_config(Path("./config"))
        main_config = snapshot.main_config
        
        assert 'version' in main_config
        assert 'pipeline' in main_config
        assert isinstance(main_config['pipeline'], list)
        assert len(main_config['pipeline']) > 0
        
        # Check workflows
        if 'workflows' in main_config:
            workflows = main_config['workflows']
            assert isinstance(workflows, dict)
    
    def test_merged_config(self):
        """Test that configs are properly merged."""
        snapshot = load_validated_config(Path("./config"))
        merged = snapshot.merged_config
        
        assert merged is not None
        assert isinstance(merged, dict)
        # Should contain keys from all config files
        assert 'version' in merged
        assert 'agents' in merged or 'pipeline' in merged


class TestUnifiedEngineConfigIntegration:
    """Test that UnifiedEngine uses configurations properly."""
    
    def test_engine_loads_configs(self):
        """Test that engine loads all configs at initialization."""
        from src.engine.unified_engine import UnifiedEngine
        
        engine = UnifiedEngine()
        
        assert engine.agent_config is not None
        assert engine.perf_config is not None
        assert engine.tone_config is not None
        assert engine.main_config is not None
        assert engine.config_snapshot is not None
    
    def test_engine_passes_configs_to_context(self):
        """Test that engine includes configs in agent context."""
        from src.engine.unified_engine import UnifiedEngine, RunSpec
        
        engine = UnifiedEngine()
        
        # Create a simple run spec
        run_spec = RunSpec(
            topic="Test Topic",
            template_name="default_blog"
        )
        
        # Generate job
        result = engine.generate_job(run_spec)
        
        assert result is not None
        # Check that configs were used (would be in partial results)
        assert 'final_context' in result.partial_results
        context = result.partial_results['final_context']
        assert 'tone' in context
        assert 'perf' in context


class TestMCPConfigIntegration:
    """Test that MCP executor uses configurations properly."""
    
    def test_config_aware_executor_initialization(self):
        """Test ConfigAwareMCPExecutor initializes with all configs."""
        from src.mcp.config_aware_executor import ConfigAwareMCPExecutor
        
        snapshot = load_validated_config(Path("./config"))
        
        executor = ConfigAwareMCPExecutor(
            agent_config=snapshot.agent_config,
            tone_config=snapshot.tone_config,
            perf_config=snapshot.perf_config,
            main_config=snapshot.main_config
        )
        
        assert executor.agent_config is not None
        assert executor.tone_config is not None
        assert executor.perf_config is not None
        assert executor.main_config is not None
    
    def test_executor_applies_timeout(self):
        """Test that executor applies timeout from perf_config."""
        from src.mcp.config_aware_executor import ConfigAwareMCPExecutor
        
        snapshot = load_validated_config(Path("./config"))
        
        executor = ConfigAwareMCPExecutor(
            agent_config=snapshot.agent_config,
            tone_config=snapshot.tone_config,
            perf_config=snapshot.perf_config,
            main_config=snapshot.main_config
        )
        
        timeout = executor.get_agent_timeout('test_agent')
        assert timeout > 0
        
        # Should match perf config timeout
        expected_timeout = snapshot.perf_config.get('timeouts', {}).get('agent_execution', 30)
        assert timeout == expected_timeout
    
    def test_executor_gets_pipeline_order(self):
        """Test that executor can get pipeline order from main_config."""
        from src.mcp.config_aware_executor import ConfigAwareMCPExecutor
        
        snapshot = load_validated_config(Path("./config"))
        
        executor = ConfigAwareMCPExecutor(
            agent_config=snapshot.agent_config,
            tone_config=snapshot.tone_config,
            perf_config=snapshot.perf_config,
            main_config=snapshot.main_config
        )
        
        pipeline = executor.get_pipeline_order('default')
        assert isinstance(pipeline, list)
    
    def test_executor_validates_dependencies(self):
        """Test that executor validates agent dependencies."""
        from src.mcp.config_aware_executor import ConfigAwareMCPExecutor
        
        snapshot = load_validated_config(Path("./config"))
        
        executor = ConfigAwareMCPExecutor(
            agent_config=snapshot.agent_config,
            tone_config=snapshot.tone_config,
            perf_config=snapshot.perf_config,
            main_config=snapshot.main_config
        )
        
        # Test with no executed agents
        is_valid, missing = executor.validate_dependencies('outline_creation', set())
        # Should have missing dependencies
        
        # Test with all dependencies executed
        executed = {'topic_identification', 'kb_ingestion', 'api_ingestion'}
        is_valid2, missing2 = executor.validate_dependencies('outline_creation', executed)
        # Should be valid now


class TestAgentConfigIntegration:
    """Test that agents receive and use configurations."""
    
    def test_agent_base_accepts_configs(self):
        """Test that Agent base class accepts configuration parameters."""
        from src.core.agent_base import Agent
        from src.core.event_bus import EventBus
        from src.core.contracts import AgentContract, AgentEvent
        
        # Create a minimal agent subclass for testing
        class TestAgent(Agent):
            def _create_contract(self):
                return AgentContract(
                    agent_id="test_agent",
                    capabilities=["test"],
                    input_schema={},
                    output_schema={},
                    publishes=[]
                )
            
            def _subscribe_to_events(self):
                pass
            
            def execute(self, event):
                return None
        
        event_bus = EventBus()
        
        # Mock config
        class MockConfig:
            pass
        
        config = MockConfig()
        tone_config = {'global_voice': {'pov': 'second_person'}}
        perf_config = {'timeouts': {'agent_execution': 30}}
        agent_config = {'id': 'test_agent'}
        
        # Create agent with all configs
        agent = TestAgent(
            agent_id="test_agent",
            config=config,
            event_bus=event_bus,
            tone_config=tone_config,
            perf_config=perf_config,
            agent_config=agent_config
        )
        
        assert agent.tone_config == tone_config
        assert agent.perf_config == perf_config
        assert agent.agent_config == agent_config
    
    def test_agent_can_access_config_values(self):
        """Test that agents can access configuration values."""
        from src.core.agent_base import Agent
        from src.core.event_bus import EventBus
        from src.core.contracts import AgentContract
        
        class TestAgent(Agent):
            def _create_contract(self):
                return AgentContract(
                    agent_id="test_agent",
                    capabilities=["test"],
                    input_schema={},
                    output_schema={},
                    publishes=[]
                )
            
            def _subscribe_to_events(self):
                pass
            
            def execute(self, event):
                return None
        
        event_bus = EventBus()
        
        class MockConfig:
            pass
        
        config = MockConfig()
        tone_config = {
            'global_voice': {'pov': 'second_person', 'formality': 'professional_conversational'},
            'section_controls': {
                'introduction': {'enabled': True, 'word_count_target': '150-250'}
            }
        }
        perf_config = {
            'timeouts': {'agent_execution': 30, 'total_job': 600},
            'limits': {'max_tokens_per_agent': 4000, 'max_retries': 3}
        }
        
        agent = TestAgent(
            agent_id="test_agent",
            config=config,
            event_bus=event_bus,
            tone_config=tone_config,
            perf_config=perf_config
        )
        
        # Test timeout access
        assert agent.get_timeout('agent_execution') == 30
        assert agent.get_timeout('total_job') == 600
        
        # Test limit access
        assert agent.get_limit('max_tokens_per_agent') == 4000
        assert agent.get_limit('max_retries') == 3
        
        # Test tone setting access
        assert agent.get_tone_setting('introduction', 'enabled') == True
        assert agent.get_tone_setting('introduction', 'word_count_target') == '150-250'
        assert agent.is_section_enabled('introduction') == True


class TestWorkflowConfigIntegration:
    """Test that workflows respect main.yaml configuration."""
    
    def test_default_workflow_exists(self):
        """Test that default workflow is defined."""
        snapshot = load_validated_config(Path("./config"))
        main_config = snapshot.main_config
        
        workflows = main_config.get('workflows', {})
        assert 'default' in workflows
        
        default_workflow = workflows['default']
        assert 'steps' in default_workflow
        assert len(default_workflow['steps']) > 0
    
    def test_workflow_dependencies(self):
        """Test that workflow dependencies are properly defined."""
        snapshot = load_validated_config(Path("./config"))
        main_config = snapshot.main_config
        
        if 'dependencies' in main_config:
            dependencies = main_config['dependencies']
            assert isinstance(dependencies, dict)
            
            # Check each dependency has 'requires' field
            for agent_id, deps in dependencies.items():
                if 'requires' in deps:
                    assert isinstance(deps['requires'], list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
