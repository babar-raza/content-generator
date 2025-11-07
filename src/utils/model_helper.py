"""
Model Router Helper for Agents
Provides easy access to smart model routing for agents
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AgentModelHelper:
    """
    Helper class for agents to get optimal models for their tasks
    
    Usage in agents:
        from src.utils.model_helper import get_optimal_model
        
        # In your agent's process method:
        optimal_model = get_optimal_model(
            task="Generate Python code for data analysis",
            agent_name=self.name
        )
        
        response = llm_service.generate(
            prompt=prompt,
            model=optimal_model,
            provider="OLLAMA"
        )
    """
    
    def __init__(self, router=None):
        """
        Initialize with an optional router instance
        
        Args:
            router: OllamaModelRouter instance (optional)
        """
        self.router = router
    
    def get_optimal_model(
        self, 
        task: str, 
        agent_name: Optional[str] = None,
        default: str = "llama2"
    ) -> str:
        """
        Get the optimal model for a task
        
        Args:
            task: Description of the task
            agent_name: Name of the requesting agent
            default: Default model if routing fails
            
        Returns:
            Model name to use
        """
        if self.router:
            try:
                model = self.router.recommend_model(task, agent_name)
                if model:
                    return model
            except Exception as e:
                logger.warning(f"Model routing failed: {e}")
        
        return default


# Global helper instance (will be initialized by LLMService)
_global_helper: Optional[AgentModelHelper] = None


def initialize_model_helper(router=None):
    """Initialize the global model helper with a router"""
    global _global_helper
    _global_helper = AgentModelHelper(router)
    logger.info("Model helper initialized")


def get_optimal_model(
    task: str,
    agent_name: Optional[str] = None,
    default: str = "llama2"
) -> str:
    """
    Get the optimal model for a task (convenience function)
    
    Args:
        task: Description of the task
        agent_name: Name of the requesting agent
        default: Default model if routing fails
        
    Returns:
        Model name to use
        
    Example:
        from src.utils.model_helper import get_optimal_model
        
        model = get_optimal_model(
            task="Write blog content about Python",
            agent_name="ContentWriter"
        )
    """
    if _global_helper:
        return _global_helper.get_optimal_model(task, agent_name, default)
    return default


# Task type constants for easy reference
class TaskType:
    """Common task types for model selection"""
    CODE_GENERATION = "code generation"
    CODE_REVIEW = "code review and validation"
    CODE_DEBUG = "debug code"
    
    CONTENT_WRITING = "write content"
    BLOG_WRITING = "write blog article"
    SECTION_WRITING = "write content section"
    
    OUTLINE_CREATION = "create outline"
    INTRODUCTION = "write introduction"
    CONCLUSION = "write conclusion"
    
    API_VALIDATION = "validate API code"
    LICENSE_INJECTION = "inject license into code"
    
    CHAT = "conversational chat"
    QUICK_QUERY = "quick query"
    
    COMPLEX_ANALYSIS = "complex analysis"
    REASONING = "complex reasoning"


__all__ = [
    'AgentModelHelper',
    'initialize_model_helper',
    'get_optimal_model',
    'TaskType'
]
