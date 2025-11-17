"""
Ollama Model Router Service
Intelligently routes tasks to the most appropriate Ollama model
Integrates with ModelMapper for cross-provider model mapping
"""

import subprocess
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModelCapability:
    """Defines capabilities and characteristics of a model"""
    name: str
    strengths: List[str]
    size: str  # small, medium, large
    speed: str  # fast, medium, slow
    specialization: List[str]
    context_window: int


class OllamaModelRouter:
    """Routes tasks to the most appropriate Ollama model"""
    
    # Model capability database
    MODEL_PROFILES = {
        "llama2": ModelCapability(
            name="llama2",
            strengths=["general", "conversation", "reasoning"],
            size="medium",
            speed="medium",
            specialization=["chat", "general_purpose", "content_writing"],
            context_window=4096
        ),
        "llama3": ModelCapability(
            name="llama3",
            strengths=["general", "reasoning", "instruction_following"],
            size="medium",
            speed="medium",
            specialization=["chat", "complex_reasoning", "general_purpose", "content_writing"],
            context_window=8192
        ),
        "llama3.2": ModelCapability(
            name="llama3.2",
            strengths=["general", "reasoning", "instruction_following", "efficiency"],
            size="medium",
            speed="fast",
            specialization=["chat", "complex_reasoning", "general_purpose", "content_writing"],
            context_window=8192
        ),
        "codellama": ModelCapability(
            name="codellama",
            strengths=["coding", "debugging", "code_generation"],
            size="medium",
            speed="medium",
            specialization=["programming", "code_review", "technical", "code_generation"],
            context_window=4096
        ),
        "mistral": ModelCapability(
            name="mistral",
            strengths=["reasoning", "instruction_following", "efficiency"],
            size="small",
            speed="fast",
            specialization=["quick_tasks", "general_purpose", "content_writing"],
            context_window=8192
        ),
        "mixtral": ModelCapability(
            name="mixtral",
            strengths=["complex_reasoning", "multilingual", "expert_tasks"],
            size="large",
            speed="medium",
            specialization=["advanced_reasoning", "multi_domain", "content_writing"],
            context_window=32768
        ),
        "phi": ModelCapability(
            name="phi",
            strengths=["reasoning", "efficiency", "math"],
            size="small",
            speed="fast",
            specialization=["quick_tasks", "math", "logic"],
            context_window=2048
        ),
        "neural-chat": ModelCapability(
            name="neural-chat",
            strengths=["conversation", "helpful_responses"],
            size="small",
            speed="fast",
            specialization=["chat", "customer_service", "content_writing"],
            context_window=4096
        ),
        "orca-mini": ModelCapability(
            name="orca-mini",
            strengths=["efficiency", "quick_responses"],
            size="small",
            speed="fast",
            specialization=["simple_tasks", "quick_queries"],
            context_window=2048
        ),
        "vicuna": ModelCapability(
            name="vicuna",
            strengths=["conversation", "detailed_responses"],
            size="medium",
            speed="medium",
            specialization=["chat", "detailed_explanations", "content_writing"],
            context_window=2048
        ),
        "deepseek-coder": ModelCapability(
            name="deepseek-coder",
            strengths=["coding", "code_completion", "debugging"],
            size="medium",
            speed="medium",
            specialization=["programming", "software_engineering", "code_generation"],
            context_window=16384
        ),
        "qwen": ModelCapability(
            name="qwen",
            strengths=["multilingual", "coding", "reasoning"],
            size="medium",
            speed="medium",
            specialization=["programming", "content_writing", "general_purpose"],
            context_window=8192
        ),
        "gemma": ModelCapability(
            name="gemma",
            strengths=["reasoning", "conversation", "safety"],
            size="small",
            speed="fast",
            specialization=["chat", "general_purpose", "content_writing"],
            context_window=8192
        ),
    }
    
    # Task keywords to model specializations mapping
    TASK_KEYWORDS = {
        # Code-related
        "code": ["programming", "code_review", "technical", "code_generation"],
        "programming": ["programming", "code_review", "technical"],
        "debug": ["programming", "code_review", "code_generation"],
        "python": ["programming", "technical", "code_generation"],
        "javascript": ["programming", "technical", "code_generation"],
        "api": ["programming", "technical"],
        "validation": ["code_review", "technical"],
        
        # Content writing
        "blog": ["content_writing", "general_purpose"],
        "article": ["content_writing", "general_purpose"],
        "write": ["content_writing", "general_purpose"],
        "content": ["content_writing", "general_purpose"],
        "section": ["content_writing", "general_purpose"],
        "outline": ["content_writing", "general_purpose"],
        "introduction": ["content_writing", "general_purpose"],
        "conclusion": ["content_writing", "general_purpose"],
        
        # Conversation & chat
        "chat": ["chat", "conversation"],
        "conversation": ["chat", "conversation"],
        "customer": ["customer_service", "chat"],
        
        # Analysis & reasoning
        "question": ["general_purpose", "chat"],
        "math": ["math", "logic", "complex_reasoning"],
        "reasoning": ["complex_reasoning", "advanced_reasoning"],
        "analysis": ["complex_reasoning", "advanced_reasoning"],
        "complex": ["complex_reasoning", "advanced_reasoning"],
        
        # Speed & simplicity
        "quick": ["quick_tasks", "simple_tasks"],
        "simple": ["quick_tasks", "simple_tasks"],
        "fast": ["quick_tasks"],
        
        # Other
        "translate": ["multilingual", "multi_domain"],
        "multilingual": ["multilingual", "multi_domain"],
        "long": ["advanced_reasoning", "multi_domain"],
        "explain": ["detailed_explanations", "general_purpose"],
        "creative": ["general_purpose", "chat", "content_writing"],
    }
    
    def __init__(self, enable_smart_routing: bool = True, default_model: Optional[str] = None):
        """
        Initialize the router
        
        Args:
            enable_smart_routing: If False, always returns default_model
            default_model: Model to use when routing is disabled or no match found
        """
        self.enable_smart_routing = enable_smart_routing
        self.default_model = default_model or "llama2"
        self.available_models = self._get_available_models()
        
        logger.info(f"OllamaModelRouter initialized with {len(self.available_models)} models")
        if not enable_smart_routing:
            logger.info(f"Smart routing DISABLED - always using: {self.default_model}")
        else:
            logger.info(f"Smart routing ENABLED - available models: {', '.join(self.available_models)}")
        
    def _get_available_models(self) -> List[str]:
        """Get list of currently installed Ollama models"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            
            # Parse the output to get model names
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            models = []
            for line in lines:
                if line.strip():
                    model_name = line.split()[0].split(':')[0]  # Get base name without tag
                    models.append(model_name)
            
            return models
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Could not fetch Ollama models: {e}")
            return []
    
    def analyze_task(self, task_description: str, agent_name: Optional[str] = None) -> Dict[str, any]:
        """Analyze task to determine requirements"""
        task_lower = task_description.lower()
        
        # Include agent name in analysis if provided
        if agent_name:
            task_lower = f"{agent_name} {task_lower}"
        
        analysis = {
            "detected_specializations": set(),
            "complexity": "medium",
            "requires_speed": False,
            "requires_long_context": False,
            "task_type": "general"
        }
        
        # Detect specializations from keywords
        for keyword, specializations in self.TASK_KEYWORDS.items():
            if keyword in task_lower:
                analysis["detected_specializations"].update(specializations)
        
        # Determine complexity
        if any(word in task_lower for word in ["complex", "detailed", "comprehensive", "in-depth"]):
            analysis["complexity"] = "high"
        elif any(word in task_lower for word in ["simple", "quick", "brief"]):
            analysis["complexity"] = "low"
        
        # Check if speed is important
        if any(word in task_lower for word in ["quick", "fast", "immediately"]):
            analysis["requires_speed"] = True
        
        # Check if long context is needed
        if any(word in task_lower for word in ["long", "document", "large", "extensive"]):
            analysis["requires_long_context"] = True
        
        return analysis
    
    def score_model(self, model_name: str, task_analysis: Dict) -> float:
        """Score how well a model matches the task requirements"""
        if model_name not in self.MODEL_PROFILES:
            return 0.0
        
        profile = self.MODEL_PROFILES[model_name]
        score = 0.0
        
        # Match specializations (highest weight)
        specialization_matches = len(
            set(profile.specialization) & task_analysis["detected_specializations"]
        )
        score += specialization_matches * 10
        
        # Complexity matching
        complexity_map = {"low": "small", "medium": "medium", "high": "large"}
        if profile.size == complexity_map.get(task_analysis["complexity"], "medium"):
            score += 5
        
        # Speed requirement
        if task_analysis["requires_speed"] and profile.speed == "fast":
            score += 5
        
        # Context window requirement
        if task_analysis["requires_long_context"] and profile.context_window >= 8192:
            score += 5
        
        # General capability bonus
        if "general_purpose" in profile.specialization and not task_analysis["detected_specializations"]:
            score += 3
        
        return score
    
    def recommend_model(
        self, 
        task_description: str, 
        agent_name: Optional[str] = None,
        fallback_to_default: bool = True
    ) -> Optional[str]:
        """
        Recommend the best model for a given task
        
        Args:
            task_description: Description of the task
            agent_name: Name of the agent requesting the model (helps with context)
            fallback_to_default: If True, returns default_model when no good match
            
        Returns:
            Model name or None if routing disabled and no default
        """
        # If routing disabled, return default
        if not self.enable_smart_routing:
            return self.default_model
        
        # If no models available, return default
        if not self.available_models:
            logger.warning("No Ollama models available, using default")
            return self.default_model if fallback_to_default else None
        
        task_analysis = self.analyze_task(task_description, agent_name)
        
        # Score all available models
        scored_models = []
        for model_name in self.available_models:
            if model_name in self.MODEL_PROFILES:
                score = self.score_model(model_name, task_analysis)
                scored_models.append((model_name, score))
        
        # Sort by score
        scored_models.sort(key=lambda x: x[1], reverse=True)
        
        if scored_models and scored_models[0][1] > 0:
            best_model = scored_models[0][0]
            best_score = scored_models[0][1]
            logger.debug(f"Selected model '{best_model}' (score: {best_score}) for task: {task_description[:50]}...")
            return best_model
        
        # No good match found
        if fallback_to_default:
            logger.debug(f"No optimal model found, using default: {self.default_model}")
            return self.default_model
        
        return None
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """Get detailed info about a specific model"""
        if model_name in self.MODEL_PROFILES:
            profile = self.MODEL_PROFILES[model_name]
            return {
                'name': profile.name,
                'strengths': profile.strengths,
                'size': profile.size,
                'speed': profile.speed,
                'specialization': profile.specialization,
                'context_window': profile.context_window
            }
        return None
    
    def list_available_models(self) -> List[str]:
        """List all available Ollama models"""
        return self.available_models
    
    def refresh_models(self):
        """Refresh the list of available models"""
        self.available_models = self._get_available_models()
        logger.info(f"Refreshed model list: {len(self.available_models)} models available")
