"""Production Execution Tests - Validates real agent execution with Ollama calls

This test suite verifies:
1. Agent instantiation works correctly
2. Real LLM calls are made to Ollama
3. Data flows properly between agents
4. NoMockGate validation works
5. Production execution engine works end-to-end
"""

import pytest
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.core import Config, EventBus, AgentEvent
from src.orchestration.production_execution_engine import (
    ProductionExecutionEngine, 
    AgentFactory,
    AgentStatus,
    AgentExecutionResult
)
from src.services.services import LLMService
from src.services.services_fixes import NoMockGate


class TestNoMockGate:
    """Test NoMockGate validation"""
    
    def test_detects_mock_content(self):
        """NoMockGate should detect placeholder content"""
        gate = NoMockGate()
        
        # Test various mock patterns
        mock_strings = [
            "Your Optimized Title Here",
            "{{placeholder}}",
            "TODO: Add content",
            "Lorem ipsum dolor",
            "[PLACEHOLDER]",
            "Insert code here"
        ]
        
        for mock_str in mock_strings:
            assert gate.contains_mock(mock_str), f"Should detect mock: {mock_str}"
    
    def test_accepts_real_content(self):
        """NoMockGate should accept real content"""
        gate = NoMockGate()
        
        real_strings = [
            "# Understanding C# File Format Conversion\n\nThis comprehensive guide explains...",
            "The Aspose.Words API provides powerful functionality for document processing.",
            "In this section, we'll explore advanced features of the library."
        ]
        
        for real_str in real_strings:
            assert not gate.contains_mock(real_str), f"Should accept real content: {real_str[:50]}"
    
    def test_validates_dict_responses(self):
        """NoMockGate should validate dictionary responses"""
        gate = NoMockGate()
        
        mock_dict = {
            'title': 'Your Optimized Title Here',
            'description': 'Real content'
        }
        
        is_valid, reason = gate.validate_response(mock_dict)
        assert not is_valid
        assert 'mock content' in reason.lower()


class TestAgentFactory:
    """Test Agent Factory for proper agent instantiation"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        config = Config()
        config.llm_provider = "OLLAMA"
        config.ollama_base_url = "http://localhost:11434"
        config.ollama_topic_model = "llama3.2:latest"
        config.ollama_content_model = "llama3.2:latest"
        config.ollama_code_model = "codellama:latest"
        config.checkpoint_dir = "./checkpoints"
        config.cache_dir = "./cache"
        config.output_dir = "./output"
        return config
    
    @pytest.fixture
    def event_bus(self):
        """Create event bus"""
        return EventBus()
    
    @pytest.fixture
    def services(self, config):
        """Create mock services"""
        return {
            'llm': Mock(spec=LLMService),
            'database': Mock(),
            'embedding': Mock(),
            'gist': Mock(),
            'link_checker': Mock(),
            'trends': Mock()
        }
    
    def test_agent_factory_initialization(self, config, event_bus, services):
        """Agent factory should initialize properly"""
        factory = AgentFactory(config, event_bus, services)
        assert factory is not None
        assert factory.config == config
        assert factory.event_bus == event_bus
    
    def test_create_topic_identification_agent(self, config, event_bus, services):
        """Should create topic identification agent"""
        factory = AgentFactory(config, event_bus, services)
        agent = factory.create_agent('topic_identification')
        
        assert agent is not None
        assert agent.agent_id == "TopicIdentificationAgent"
    
    def test_create_section_writer_agent(self, config, event_bus, services):
        """Should create section writer agent"""
        factory = AgentFactory(config, event_bus, services)
        agent = factory.create_agent('section_writer')
        
        assert agent is not None
        assert agent.agent_id == "SectionWriterAgent"
    
    def test_agent_caching(self, config, event_bus, services):
        """Agents should be cached after creation"""
        factory = AgentFactory(config, event_bus, services)
        
        agent1 = factory.create_agent('topic_identification')
        agent2 = factory.create_agent('topic_identification')
        
        assert agent1 is agent2  # Same instance


class TestProductionExecutionEngine:
    """Test Production Execution Engine end-to-end"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        config = Config()
        config.llm_provider = "OLLAMA"
        config.ollama_base_url = "http://localhost:11434"
        config.ollama_topic_model = "llama3.2:latest"
        config.ollama_content_model = "llama3.2:latest"
        config.ollama_code_model = "codellama:latest"
        config.checkpoint_dir = "./checkpoints"
        config.cache_dir = "./cache"
        config.output_dir = "./output"
        config.github_token = None  # Optional
        return config
    
    @pytest.mark.skipif(not Path("/usr/bin/ollama").exists(), reason="Ollama not available")
    def test_engine_initialization(self, config):
        """Production engine should initialize with real services"""
        engine = ProductionExecutionEngine(config)
        
        assert engine is not None
        assert engine.event_bus is not None
        assert 'llm' in engine.services
        assert isinstance(engine.services['llm'], LLMService)
    
    @pytest.mark.skipif(not Path("/usr/bin/ollama").exists(), reason="Ollama not available")
    def test_simple_pipeline_execution(self, config):
        """Should execute a simple 2-step pipeline"""
        engine = ProductionExecutionEngine(config)
        
        # Define simple workflow
        steps = [
            {'id': 'topic_identification', 'agent': 'topic_identification'},
            {'id': 'outline_creation', 'agent': 'outline_creation'}
        ]
        
        input_data = {
            'topic': 'C# File Format Conversion with Aspose.Words',
            'kb_article_content': 'Sample KB content about file conversion...'
        }
        
        # Track progress
        progress_updates = []
        def track_progress(progress, message):
            progress_updates.append((progress, message))
        
        # Execute pipeline
        results = engine.execute_pipeline(
            workflow_name='test_workflow',
            steps=steps,
            input_data=input_data,
            job_id='test_job_001',
            progress_callback=track_progress
        )
        
        # Verify results
        assert results is not None
        assert 'agent_outputs' in results
        assert len(progress_updates) > 0
        assert results.get('llm_calls', 0) > 0  # Real LLM calls were made


class TestLLMServiceIntegration:
    """Test LLM Service makes real calls"""
    
    @pytest.fixture
    def config(self):
        config = Config()
        config.llm_provider = "OLLAMA"
        config.ollama_base_url = "http://localhost:11434"
        config.ollama_topic_model = "llama3.2:latest"
        config.cache_dir = "./cache"
        config.deterministic = False
        return config
    
    @pytest.mark.skipif(not Path("/usr/bin/ollama").exists(), reason="Ollama not available")
    def test_llm_service_generates_text(self, config):
        """LLM service should generate real text from Ollama"""
        llm_service = LLMService(config)
        
        prompt = "Write a single sentence about file format conversion."
        response = llm_service.generate(
            prompt=prompt,
            system_prompt="You are a technical writer.",
            json_mode=False,
            temperature=0.7
        )
        
        assert response is not None
        assert len(response) > 10
        assert isinstance(response, str)
        
        # Should not contain mock patterns
        gate = NoMockGate()
        assert not gate.contains_mock(response)


class TestEndToEndWorkflow:
    """Test complete workflow execution"""
    
    @pytest.fixture
    def config(self):
        config = Config()
        config.llm_provider = "OLLAMA"
        config.ollama_base_url = "http://localhost:11434"
        config.ollama_topic_model = "llama3.2:latest"
        config.ollama_content_model = "llama3.2:latest"
        config.checkpoint_dir = "./test_checkpoints"
        config.cache_dir = "./test_cache"
        config.output_dir = "./test_output"
        return config
    
    @pytest.mark.skipif(not Path("/usr/bin/ollama").exists(), reason="Ollama not available")
    @pytest.mark.slow
    def test_mini_blog_generation_workflow(self, config):
        """Test a mini blog generation workflow with real agents"""
        engine = ProductionExecutionEngine(config)
        
        # Mini workflow: identify topic → create outline → write intro
        steps = [
            {'id': 'topic_identification', 'agent': 'topic_identification'},
            {'id': 'outline_creation', 'agent': 'outline_creation'},
            {'id': 'introduction_writer', 'agent': 'introduction_writer'}
        ]
        
        input_data = {
            'topic': 'C# PDF to Word Conversion',
            'kb_article_content': '''
            # PDF to Word Conversion in C#
            
            This article explains how to convert PDF files to Word documents using Aspose.Words.
            The API provides simple methods for high-quality conversion while preserving formatting.
            '''
        }
        
        # Execute
        start_time = time.time()
        results = engine.execute_pipeline(
            workflow_name='mini_blog',
            steps=steps,
            input_data=input_data,
            job_id='test_mini_blog'
        )
        execution_time = time.time() - start_time
        
        # Verify real execution
        assert execution_time > 3.0  # Real LLM calls take time
        assert results.get('llm_calls', 0) >= 3  # At least one per agent
        assert 'agent_outputs' in results
        assert len(results['agent_outputs']) == 3
        
        # Verify each agent produced output
        assert 'topic_identification' in results['agent_outputs']
        assert 'outline_creation' in results['agent_outputs']
        assert 'introduction_writer' in results['agent_outputs']
        
        # Verify content quality with NoMockGate
        gate = NoMockGate()
        for agent_name, result in results['agent_outputs'].items():
            output_data = result.output_data if hasattr(result, 'output_data') else result.get('output_data', {})
            is_valid, reason = gate.validate_response(output_data)
            assert is_valid, f"Agent {agent_name} produced mock content: {reason}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
