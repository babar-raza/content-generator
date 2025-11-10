"""Integration Tests for Production Execution Engine

Tests real agent execution with Ollama integration
"""

import pytest
import os
import time
from pathlib import Path
from datetime import datetime
import logging

from src.core import Config
from src.orchestration.production_execution_engine import (
    ProductionExecutionEngine,
    AgentFactory,
    AgentStatus
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def config():
    """Create test configuration"""
    # Use environment variables or defaults
    return Config(
        llm_provider=os.getenv("LLM_PROVIDER", "OLLAMA"),
        ollama_topic_model=os.getenv("OLLAMA_MODEL", "llama2"),
        ollama_content_model=os.getenv("OLLAMA_MODEL", "llama2"),
        ollama_code_model=os.getenv("OLLAMA_MODEL", "codellama"),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        github_token=os.getenv("GITHUB_TOKEN", ""),
        output_dir="./test_output",
        checkpoint_dir="./test_checkpoints",
        cache_dir="./test_cache"
    )


@pytest.fixture
def production_engine(config):
    """Create production engine instance"""
    return ProductionExecutionEngine(config)


class TestAgentFactory:
    """Test agent factory functionality"""
    
    def test_factory_initialization(self, config, production_engine):
        """Test that factory initializes properly"""
        factory = production_engine.agent_factory
        assert factory is not None
        assert len(factory._agent_modules) > 0
        logger.info(f"Loaded {len(factory._agent_modules)} agent modules")
    
    def test_create_topic_identification_agent(self, production_engine):
        """Test creating topic identification agent"""
        agent = production_engine.agent_factory.create_agent('topic_identification')
        assert agent is not None
        assert hasattr(agent, 'execute')
        logger.info("✓ Topic identification agent created")
    
    def test_create_section_writer_agent(self, production_engine):
        """Test creating section writer agent"""
        agent = production_engine.agent_factory.create_agent('section_writer')
        assert agent is not None
        assert hasattr(agent, 'execute')
        logger.info("✓ Section writer agent created")
    
    def test_create_all_standard_agents(self, production_engine):
        """Test creating all standard agents"""
        standard_agents = [
            'topic_identification', 'kb_ingestion', 'api_ingestion',
            'outline_creation', 'introduction_writer', 'section_writer',
            'code_generation', 'conclusion_writer', 'content_assembly',
            'file_writer'
        ]
        
        created_count = 0
        for agent_type in standard_agents:
            try:
                agent = production_engine.agent_factory.create_agent(agent_type)
                if agent:
                    created_count += 1
                    logger.info(f"✓ Created {agent_type}")
            except Exception as e:
                logger.error(f"✗ Failed to create {agent_type}: {e}")
        
        assert created_count >= len(standard_agents) * 0.8, "At least 80% of agents should be created"


class TestProductionEngineServices:
    """Test service initialization"""
    
    def test_services_initialized(self, production_engine):
        """Test that all services are initialized"""
        assert 'llm' in production_engine.services
        assert 'database' in production_engine.services
        assert 'embedding' in production_engine.services
        logger.info("✓ Core services initialized")
    
    def test_llm_service_has_no_mock_gate(self, production_engine):
        """Test that NoMockGate is attached to LLM service"""
        llm_service = production_engine.services['llm']
        assert hasattr(llm_service, 'no_mock_gate')
        assert llm_service.no_mock_gate is not None
        logger.info("✓ NoMockGate attached to LLM service")


@pytest.mark.integration
class TestSimplePipeline:
    """Test simple pipeline execution with real Ollama calls"""
    
    def test_single_agent_execution(self, production_engine):
        """Test executing a single agent"""
        # Simple topic identification test
        steps = [
            {'id': 'topic_identification', 'agent': 'topic_identification'}
        ]
        
        input_data = {
            'topic': 'Python Classes'
        }
        
        progress_updates = []
        def progress_callback(progress, message):
            progress_updates.append((progress, message))
            logger.info(f"Progress: {progress:.1f}% - {message}")
        
        result = production_engine.execute_pipeline(
            workflow_name='test_single_agent',
            steps=steps,
            input_data=input_data,
            job_id='test_job_1',
            progress_callback=progress_callback
        )
        
        assert result is not None
        assert 'agent_outputs' in result
        assert 'topic_identification' in result['agent_outputs']
        assert result['llm_calls'] > 0, "Should have made at least one LLM call"
        
        # Check progress updates
        assert len(progress_updates) > 0
        assert progress_updates[-1][0] == 100.0
        
        logger.info(f"✓ Single agent test completed with {result['llm_calls']} LLM calls")
    
    def test_three_agent_pipeline(self, production_engine):
        """Test pipeline with topic → outline → intro"""
        steps = [
            {'id': 'topic_identification', 'agent': 'topic_identification'},
            {'id': 'outline_creation', 'agent': 'outline_creation'},
            {'id': 'introduction_writer', 'agent': 'introduction_writer'}
        ]
        
        input_data = {
            'topic': 'Python Decorators',
            'context': []  # Minimal context for faster test
        }
        
        result = production_engine.execute_pipeline(
            workflow_name='test_three_agents',
            steps=steps,
            input_data=input_data,
            job_id='test_job_2'
        )
        
        assert result is not None
        assert len(result['agent_outputs']) == 3
        assert result['llm_calls'] >= 3, "Should have made at least 3 LLM calls (one per agent)"
        
        # Check data flow
        assert 'topic' in result['shared_state']
        assert 'outline' in result['shared_state']
        assert 'intro' in result['shared_state']
        
        logger.info(
            f"✓ Three-agent pipeline completed | "
            f"LLM calls: {result['llm_calls']} | "
            f"Duration: {result.get('total_duration', 0):.2f}s"
        )


@pytest.mark.integration
@pytest.mark.slow
class TestFullPipeline:
    """Test full blog generation pipeline (slower tests)"""
    
    def test_minimal_blog_generation(self, production_engine):
        """Test minimal blog generation workflow"""
        # Minimal workflow for testing
        steps = [
            {'id': 'topic_identification', 'agent': 'topic_identification'},
            {'id': 'outline_creation', 'agent': 'outline_creation'},
            {'id': 'introduction_writer', 'agent': 'introduction_writer'},
            {'id': 'section_writer', 'agent': 'section_writer'},
            {'id': 'conclusion_writer', 'agent': 'conclusion_writer'},
            {'id': 'content_assembly', 'agent': 'content_assembly'},
        ]
        
        input_data = {
            'topic': 'Python List Comprehensions',
            'context': []
        }
        
        start_time = time.time()
        
        result = production_engine.execute_pipeline(
            workflow_name='test_minimal_blog',
            steps=steps,
            input_data=input_data,
            job_id='test_job_3'
        )
        
        duration = time.time() - start_time
        
        assert result is not None
        assert 'assembled_content' in result['shared_state']
        assert len(result['shared_state']['assembled_content']) > 100
        
        # Validate NoMockGate caught no issues
        assert 'error' not in result
        
        logger.info(
            f"✓ Minimal blog generation completed | "
            f"Duration: {duration:.2f}s | "
            f"LLM calls: {result['llm_calls']} | "
            f"Content length: {len(result['shared_state']['assembled_content'])} chars"
        )


class TestErrorHandling:
    """Test error handling and recovery"""
    
    def test_invalid_agent_type(self, production_engine):
        """Test handling of invalid agent type"""
        steps = [
            {'id': 'nonexistent_agent', 'agent': 'nonexistent_agent'}
        ]
        
        with pytest.raises(Exception):
            production_engine.execute_pipeline(
                workflow_name='test_invalid_agent',
                steps=steps,
                input_data={'topic': 'Test'},
                job_id='test_job_error_1'
            )
        
        logger.info("✓ Invalid agent type properly rejected")
    
    def test_missing_required_input(self, production_engine):
        """Test handling of missing required input"""
        steps = [
            {'id': 'outline_creation', 'agent': 'outline_creation'}
        ]
        
        # Missing topic and context
        input_data = {}
        
        result = production_engine.execute_pipeline(
            workflow_name='test_missing_input',
            steps=steps,
            input_data=input_data,
            job_id='test_job_error_2'
        )
        
        # Should handle gracefully
        assert result is not None
        logger.info("✓ Missing input handled gracefully")


class TestCheckpointing:
    """Test checkpoint functionality"""
    
    def test_checkpoint_creation(self, production_engine):
        """Test that checkpoints are created"""
        checkpoint_created = []
        
        def checkpoint_callback(agent_type, checkpoint_data):
            checkpoint_created.append(agent_type)
            logger.info(f"Checkpoint created for: {agent_type}")
        
        steps = [
            {'id': 'topic_identification', 'agent': 'topic_identification'},
            {'id': 'outline_creation', 'agent': 'outline_creation'}
        ]
        
        result = production_engine.execute_pipeline(
            workflow_name='test_checkpoint',
            steps=steps,
            input_data={'topic': 'Test Topic'},
            job_id='test_job_checkpoint',
            checkpoint_callback=checkpoint_callback
        )
        
        assert len(checkpoint_created) == 2
        logger.info(f"✓ {len(checkpoint_created)} checkpoints created")


class TestNoMockGateValidation:
    """Test NoMockGate validation"""
    
    def test_no_mock_gate_rejects_placeholders(self, production_engine):
        """Test that NoMockGate rejects mock/placeholder content"""
        no_mock_gate = production_engine.services['llm'].no_mock_gate
        
        # Test various mock patterns
        mock_texts = [
            "Your Optimized Title Here",
            "{{placeholder}}",
            "TODO: Add content here",
            "Lorem ipsum dolor sit amet",
            "...",
        ]
        
        for text in mock_texts:
            is_valid, reason = no_mock_gate.validate_response(text)
            assert not is_valid, f"Should reject mock text: {text}"
            logger.info(f"✓ Rejected mock text: {text[:30]}...")
    
    def test_no_mock_gate_accepts_real_content(self, production_engine):
        """Test that NoMockGate accepts real content"""
        no_mock_gate = production_engine.services['llm'].no_mock_gate
        
        real_content = """
        Python is a high-level programming language that emphasizes code readability.
        It supports multiple programming paradigms including procedural, object-oriented,
        and functional programming. Python's standard library is comprehensive and
        provides tools for various programming tasks.
        """
        
        is_valid, reason = no_mock_gate.validate_response(real_content)
        assert is_valid, f"Should accept real content, but rejected: {reason}"
        logger.info("✓ Accepted real content")


@pytest.mark.performance
class TestPerformance:
    """Performance benchmarks"""
    
    def test_agent_execution_speed(self, production_engine):
        """Test agent execution speed"""
        steps = [
            {'id': 'topic_identification', 'agent': 'topic_identification'}
        ]
        
        start_time = time.time()
        
        result = production_engine.execute_pipeline(
            workflow_name='test_speed',
            steps=steps,
            input_data={'topic': 'Quick Test'},
            job_id='test_job_speed'
        )
        
        duration = time.time() - start_time
        
        # Single agent should complete in reasonable time
        assert duration < 30, f"Single agent took too long: {duration:.2f}s"
        
        logger.info(f"✓ Single agent execution: {duration:.2f}s")


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v", "-m", "not slow", "--tb=short"])
