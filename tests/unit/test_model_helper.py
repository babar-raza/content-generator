"""Tests for model_helper module."""

import pytest
from unittest.mock import Mock, patch
from src.utils.model_helper import (
    AgentModelHelper,
    initialize_model_helper,
    get_optimal_model,
    TaskType
)


class TestAgentModelHelper:
    """Tests for AgentModelHelper class."""
    
    def test_initialization_no_router(self):
        """Test initialization without router."""
        helper = AgentModelHelper()
        assert helper.router is None
    
    def test_initialization_with_router(self):
        """Test initialization with router."""
        mock_router = Mock()
        helper = AgentModelHelper(mock_router)
        assert helper.router is mock_router
    
    def test_get_optimal_model_no_router(self):
        """Test getting model when no router is set."""
        helper = AgentModelHelper()
        model = helper.get_optimal_model("task description")
        assert model == "llama2"  # default
    
    def test_get_optimal_model_custom_default(self):
        """Test getting model with custom default."""
        helper = AgentModelHelper()
        model = helper.get_optimal_model("task", default="custom-model")
        assert model == "custom-model"
    
    def test_get_optimal_model_with_router(self):
        """Test getting model with router."""
        mock_router = Mock()
        mock_router.recommend_model.return_value = "optimal-model"
        
        helper = AgentModelHelper(mock_router)
        model = helper.get_optimal_model("code generation task")
        
        assert model == "optimal-model"
        mock_router.recommend_model.assert_called_once()
    
    def test_get_optimal_model_router_returns_none(self):
        """Test fallback when router returns None."""
        mock_router = Mock()
        mock_router.recommend_model.return_value = None
        
        helper = AgentModelHelper(mock_router)
        model = helper.get_optimal_model("task", default="fallback")
        
        assert model == "fallback"
    
    def test_get_optimal_model_router_exception(self):
        """Test fallback when router raises exception."""
        mock_router = Mock()
        mock_router.recommend_model.side_effect = Exception("Router error")
        
        helper = AgentModelHelper(mock_router)
        model = helper.get_optimal_model("task", default="safe-model")
        
        assert model == "safe-model"
    
    def test_get_optimal_model_with_agent_name(self):
        """Test passing agent name to router."""
        mock_router = Mock()
        mock_router.recommend_model.return_value = "model"
        
        helper = AgentModelHelper(mock_router)
        helper.get_optimal_model("task", agent_name="TestAgent")
        
        mock_router.recommend_model.assert_called_with("task", "TestAgent")
    
    def test_get_optimal_model_without_agent_name(self):
        """Test calling without agent name."""
        mock_router = Mock()
        mock_router.recommend_model.return_value = "model"
        
        helper = AgentModelHelper(mock_router)
        helper.get_optimal_model("task")
        
        mock_router.recommend_model.assert_called_with("task", None)


class TestInitializeModelHelper:
    """Tests for initialize_model_helper function."""
    
    def test_initialize_without_router(self):
        """Test initializing without router."""
        with patch('src.utils.model_helper._global_helper', None):
            initialize_model_helper()
            
            from src.utils import model_helper
            assert model_helper._global_helper is not None
            assert isinstance(model_helper._global_helper, AgentModelHelper)
    
    def test_initialize_with_router(self):
        """Test initializing with router."""
        mock_router = Mock()
        
        with patch('src.utils.model_helper._global_helper', None):
            initialize_model_helper(mock_router)
            
            from src.utils import model_helper
            assert model_helper._global_helper.router is mock_router
    
    def test_initialize_multiple_times(self):
        """Test that initialization can be called multiple times."""
        mock_router1 = Mock()
        mock_router2 = Mock()
        
        initialize_model_helper(mock_router1)
        initialize_model_helper(mock_router2)
        
        from src.utils import model_helper
        assert model_helper._global_helper.router is mock_router2


class TestGetOptimalModelGlobal:
    """Tests for get_optimal_model global function."""
    
    def test_get_optimal_model_no_global_helper(self):
        """Test function when global helper is not initialized."""
        with patch('src.utils.model_helper._global_helper', None):
            model = get_optimal_model("task")
            assert model == "llama2"
    
    def test_get_optimal_model_with_global_helper(self):
        """Test function when global helper is initialized."""
        mock_helper = Mock()
        mock_helper.get_optimal_model.return_value = "global-model"
        
        with patch('src.utils.model_helper._global_helper', mock_helper):
            model = get_optimal_model("task description")
            
            assert model == "global-model"
            mock_helper.get_optimal_model.assert_called_once()
    
    def test_get_optimal_model_custom_default_global(self):
        """Test function with custom default."""
        with patch('src.utils.model_helper._global_helper', None):
            model = get_optimal_model("task", default="custom")
            assert model == "custom"
    
    def test_get_optimal_model_with_agent_name_global(self):
        """Test function with agent name."""
        mock_helper = Mock()
        mock_helper.get_optimal_model.return_value = "model"
        
        with patch('src.utils.model_helper._global_helper', mock_helper):
            get_optimal_model("task", agent_name="TestAgent")
            
            mock_helper.get_optimal_model.assert_called_with(
                "task", "TestAgent", "llama2"
            )
    
    def test_get_optimal_model_all_parameters(self):
        """Test function with all parameters."""
        mock_helper = Mock()
        mock_helper.get_optimal_model.return_value = "result"
        
        with patch('src.utils.model_helper._global_helper', mock_helper):
            model = get_optimal_model(
                task="complex task",
                agent_name="Agent1",
                default="fallback-model"
            )
            
            assert model == "result"
            mock_helper.get_optimal_model.assert_called_with(
                "complex task", "Agent1", "fallback-model"
            )


class TestTaskType:
    """Tests for TaskType constants."""
    
    def test_code_generation_constants(self):
        """Test code-related task type constants."""
        assert TaskType.CODE_GENERATION == "code generation"
        assert TaskType.CODE_REVIEW == "code review and validation"
        assert TaskType.CODE_DEBUG == "debug code"
    
    def test_content_writing_constants(self):
        """Test content writing task type constants."""
        assert TaskType.CONTENT_WRITING == "write content"
        assert TaskType.BLOG_WRITING == "write blog article"
        assert TaskType.SECTION_WRITING == "write content section"
    
    def test_outline_constants(self):
        """Test outline and structure task type constants."""
        assert TaskType.OUTLINE_CREATION == "create outline"
        assert TaskType.INTRODUCTION == "write introduction"
        assert TaskType.CONCLUSION == "write conclusion"
    
    def test_validation_constants(self):
        """Test validation task type constants."""
        assert TaskType.API_VALIDATION == "validate API code"
        assert TaskType.LICENSE_INJECTION == "inject license into code"
    
    def test_chat_constants(self):
        """Test chat-related task type constants."""
        assert TaskType.CHAT == "conversational chat"
        assert TaskType.QUICK_QUERY == "quick query"
    
    def test_analysis_constants(self):
        """Test analysis task type constants."""
        assert TaskType.COMPLEX_ANALYSIS == "complex analysis"
        assert TaskType.REASONING == "complex reasoning"
    
    def test_all_constants_are_strings(self):
        """Test that all constants are strings."""
        import inspect
        
        for name, value in inspect.getmembers(TaskType):
            if not name.startswith('_'):
                assert isinstance(value, str)


class TestIntegration:
    """Integration tests for model_helper module."""
    
    def test_full_workflow_no_router(self):
        """Test full workflow without router."""
        # Initialize without router
        with patch('src.utils.model_helper._global_helper', None):
            initialize_model_helper()
            
            # Get model
            model = get_optimal_model("task")
            
            assert model == "llama2"
    
    def test_full_workflow_with_router(self):
        """Test full workflow with router."""
        # Create mock router
        mock_router = Mock()
        mock_router.recommend_model.return_value = "best-model"
        
        # Initialize with router
        with patch('src.utils.model_helper._global_helper', None):
            initialize_model_helper(mock_router)
            
            # Get model
            model = get_optimal_model(TaskType.CODE_GENERATION, "CodeAgent")
            
            assert model == "best-model"
            mock_router.recommend_model.assert_called_once()
    
    def test_module_exports(self):
        """Test that module exports expected items."""
        from src.utils import model_helper
        
        assert 'AgentModelHelper' in model_helper.__all__
        assert 'initialize_model_helper' in model_helper.__all__
        assert 'get_optimal_model' in model_helper.__all__
        assert 'TaskType' in model_helper.__all__
