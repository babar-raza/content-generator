"""Ollama Model Detection and Management Utility."""

import subprocess
import logging
import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OllamaModel:
    """Represents an Ollama model."""
    name: str
    size: str
    modified: str
    capabilities: List[str]


class OllamaDetector:
    """Detects and manages Ollama models."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self._models_cache: Optional[List[OllamaModel]] = None
        
        # Model capability mappings
        self.model_capabilities = {
            "code": ["coder", "code", "qwen", "codellama", "deepseek-coder", "starcoder"],
            "content": ["mistral", "llama", "qwen", "gemma", "phi"],
            "topic": ["mistral", "llama", "gemma", "phi"],
            "research": ["llama", "mistral", "mixtral", "qwen"],
            "analysis": ["llama", "mistral", "qwen"]
        }
    
    def is_ollama_available(self) -> Tuple[bool, str]:
        """Check if Ollama is available and running.
        
        Returns:
            Tuple of (is_available, status_message)
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return True, f"Ollama running with {len(models)} model(s)"
            else:
                return False, f"Ollama API returned status {response.status_code}"
        except requests.ConnectionError:
            return False, "Ollama not running or connection refused"
        except requests.Timeout:
            return False, "Ollama connection timeout"
        except Exception as e:
            return False, f"Error checking Ollama: {str(e)}"
    
    def get_installed_models(self) -> List[OllamaModel]:
        """Get list of installed Ollama models.
        
        Returns:
            List of installed models
        """
        if self._models_cache is not None:
            return self._models_cache
        
        models = []
        
        # Try API first
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if response.status_code == 200:
                data = response.json()
                for model_data in data.get('models', []):
                    name = model_data.get('name', '')
                    capabilities = self._detect_capabilities(name)
                    models.append(OllamaModel(
                        name=name,
                        size=model_data.get('size', 'unknown'),
                        modified=model_data.get('modified_at', ''),
                        capabilities=capabilities
                    ))
                self._models_cache = models
                return models
        except Exception as e:
            logger.debug(f"API method failed, trying CLI: {e}")
        
        # Fallback to CLI
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                # Skip header
                for line in lines[1:]:
                    if line.strip():
                        parts = line.split()
                        if parts:
                            name = parts[0]
                            size = parts[1] if len(parts) > 1 else 'unknown'
                            modified = ' '.join(parts[2:]) if len(parts) > 2 else ''
                            capabilities = self._detect_capabilities(name)
                            models.append(OllamaModel(
                                name=name,
                                size=size,
                                modified=modified,
                                capabilities=capabilities
                            ))
                
                self._models_cache = models
        except Exception as e:
            logger.warning(f"Failed to get Ollama models: {e}")
        
        return models
    
    def _detect_capabilities(self, model_name: str) -> List[str]:
        """Detect capabilities based on model name.
        
        Args:
            model_name: Name of the model
            
        Returns:
            List of capability tags
        """
        name_lower = model_name.lower()
        capabilities = []
        
        for capability, keywords in self.model_capabilities.items():
            if any(keyword in name_lower for keyword in keywords):
                capabilities.append(capability)
        
        # If no specific capabilities detected, mark as general
        if not capabilities:
            capabilities.append("general")
        
        return capabilities
    
    def get_best_model_for_capability(self, capability: str) -> Optional[str]:
        """Get best model for a specific capability.
        
        Args:
            capability: Required capability (code, content, topic, etc.)
            
        Returns:
            Model name or None if no suitable model found
        """
        models = self.get_installed_models()
        
        if not models:
            return None
        
        # Filter models by capability
        suitable_models = [
            m for m in models 
            if capability in m.capabilities
        ]
        
        if not suitable_models:
            # Fallback to general models
            suitable_models = [
                m for m in models 
                if "general" in m.capabilities or "content" in m.capabilities
            ]
        
        if not suitable_models:
            # Last resort - return first available model
            return models[0].name
        
        # Return first suitable model (could be improved with ranking)
        return suitable_models[0].name
    
    def get_model_recommendations(self) -> Dict[str, List[str]]:
        """Get recommended models for each capability.
        
        Returns:
            Dictionary mapping capabilities to recommended model names
        """
        models = self.get_installed_models()
        recommendations = {}
        
        for capability in self.model_capabilities.keys():
            suitable = [
                m.name for m in models 
                if capability in m.capabilities
            ]
            if suitable:
                recommendations[capability] = suitable
        
        return recommendations
    
    def validate_model_config(self, config: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate model configuration against available models.
        
        Args:
            config: Dictionary of capability -> model_name mappings
            
        Returns:
            Tuple of (is_valid, list of warnings)
        """
        warnings = []
        models = self.get_installed_models()
        model_names = {m.name for m in models}
        
        if not models:
            return False, ["No Ollama models installed"]
        
        for capability, model_name in config.items():
            if model_name not in model_names:
                warnings.append(f"Model '{model_name}' for {capability} not found")
                # Suggest alternative
                alt = self.get_best_model_for_capability(capability)
                if alt:
                    warnings.append(f"  → Consider using '{alt}' instead")
        
        return len(warnings) == 0, warnings


# Global instance
_detector = None


def get_ollama_detector(base_url: str = "http://localhost:11434") -> OllamaDetector:
    """Get global OllamaDetector instance."""
    global _detector
    if _detector is None:
        _detector = OllamaDetector(base_url)
    return _detector


def check_ollama_setup(base_url: str = "http://localhost:11434") -> Dict[str, any]:
    """Comprehensive Ollama setup check.
    
    Returns:
        Dictionary with setup information
    """
    detector = get_ollama_detector(base_url)
    
    available, status = detector.is_ollama_available()
    models = detector.get_installed_models() if available else []
    recommendations = detector.get_model_recommendations() if available else {}
    
    return {
        "available": available,
        "status": status,
        "base_url": base_url,
        "models_count": len(models),
        "models": [
            {
                "name": m.name,
                "size": m.size,
                "capabilities": m.capabilities
            }
            for m in models
        ],
        "recommendations": recommendations
    }
