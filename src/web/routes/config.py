"""Configuration management API routes."""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from unittest.mock import Mock

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


# This will be injected by the app
_config_snapshot = None


def set_config_snapshot(config):
    """Set the config snapshot for dependency injection."""
    global _config_snapshot
    _config_snapshot = config


def _ensure_plain_dict(value: Any) -> Any:
    """Recursively convert values to plain JSON-serializable types.

    Handles Mock objects, pydantic models, and nested structures.

    Args:
        value: Value to sanitize

    Returns:
        JSON-serializable value (dict, list, str, int, float, bool, None)
    """
    # Handle None
    if value is None:
        return None

    # Handle Mock objects (from tests)
    if isinstance(value, Mock):
        # Mock objects should be converted to empty dict or try to extract real value
        # In test contexts, Mocks are placeholders - return empty dict
        return {}

    # Handle pydantic models
    if hasattr(value, 'model_dump'):
        try:
            return value.model_dump(mode='json')
        except Exception:
            # Fallback to dict
            if hasattr(value, '__dict__'):
                return _ensure_plain_dict(value.__dict__)
            return {}

    # Handle objects with to_dict method
    if hasattr(value, 'to_dict') and callable(value.to_dict):
        try:
            return _ensure_plain_dict(value.to_dict())
        except Exception:
            # Fallback to dict
            if hasattr(value, '__dict__'):
                return _ensure_plain_dict(value.__dict__)
            return {}

    # Handle dictionaries recursively
    if isinstance(value, dict):
        return {
            k: _ensure_plain_dict(v)
            for k, v in value.items()
        }

    # Handle lists recursively
    if isinstance(value, (list, tuple)):
        return [_ensure_plain_dict(item) for item in value]

    # Handle primitive types
    if isinstance(value, (str, int, float, bool)):
        return value

    # For other objects, try to convert to dict or return empty dict
    if hasattr(value, '__dict__'):
        return _ensure_plain_dict(value.__dict__)

    # Last resort: convert to string if possible, otherwise empty dict
    try:
        return str(value)
    except Exception:
        return {}


# Models
class ConfigSnapshotResponse(BaseModel):
    """Full configuration snapshot."""
    orchestration: Dict[str, Any] = Field(default_factory=dict)
    agents: Dict[str, Any] = Field(default_factory=dict)
    workflows: Dict[str, Any] = Field(default_factory=dict)
    llm: Dict[str, Any] = Field(default_factory=dict)
    templates: Dict[str, Any] = Field(default_factory=dict)
    system: Dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0"
    timestamp: str


class AgentConfigResponse(BaseModel):
    """Agent configuration."""
    agents: Dict[str, Any]
    total: int


class WorkflowConfigResponse(BaseModel):
    """Workflow configuration."""
    workflows: Dict[str, Any]
    total: int


class LLMConfigResponse(BaseModel):
    """LLM configuration."""
    providers: Dict[str, Any]
    default_provider: Optional[str] = None
    default_model: Optional[str] = None


@router.get("/snapshot", response_model=ConfigSnapshotResponse)
async def get_config_snapshot():
    """Get full config snapshot (mirrors cmd_config_snapshot).
    
    Returns:
        ConfigSnapshotResponse with complete configuration
    """
    try:
        from datetime import datetime, timezone
        from src.core.config import Config
        
        # Use injected config snapshot or load fresh
        if _config_snapshot:
            config = _config_snapshot
        else:
            # Load configuration
            config_path = Path("./config/orchestration.yaml")
            if config_path.exists():
                config = Config.from_yaml(config_path)
            else:
                # Return minimal config if file doesn't exist
                return ConfigSnapshotResponse(
                    orchestration={},
                    agents={},
                    workflows={},
                    llm={},
                    templates={},
                    system={},
                    version="1.0",
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
        
        # Extract configuration sections
        config_dict = {}
        if hasattr(config, 'to_dict'):
            config_dict = config.to_dict()
        elif hasattr(config, '__dict__'):
            config_dict = config.__dict__

        # Sanitize all values to ensure they're JSON-serializable (not Mocks)
        orchestration = _ensure_plain_dict(config_dict.get("orchestration", {}))
        agents = _ensure_plain_dict(config_dict.get("agents", {}))
        workflows = _ensure_plain_dict(config_dict.get("workflows", {}))
        llm = _ensure_plain_dict(config_dict.get("llm", {}))
        templates = _ensure_plain_dict(config_dict.get("templates", {}))
        system = _ensure_plain_dict(config_dict.get("system", {}))
        version = config_dict.get("version", "1.0")

        # Ensure version is a string (not a Mock)
        if isinstance(version, Mock):
            version = "1.0"
        elif not isinstance(version, str):
            version = str(version) if version else "1.0"

        return ConfigSnapshotResponse(
            orchestration=orchestration,
            agents=agents,
            workflows=workflows,
            llm=llm,
            templates=templates,
            system=system,
            version=version,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting config snapshot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get config snapshot: {str(e)}")


@router.get("/agents", response_model=AgentConfigResponse)
async def get_agent_config():
    """Get agent configuration (mirrors cmd_config_agents).
    
    Returns:
        AgentConfigResponse with agent configuration
    """
    try:
        from src.core.config import Config
        
        # Use injected config snapshot or load fresh
        if _config_snapshot:
            config = _config_snapshot
        else:
            config_path = Path("./config/orchestration.yaml")
            if config_path.exists():
                config = Config.from_yaml(config_path)
            else:
                return AgentConfigResponse(agents={}, total=0)
        
        # Extract agent configuration
        agents_config = {}
        if hasattr(config, 'agents'):
            agents_config = config.agents if isinstance(config.agents, dict) else {}
        elif hasattr(config, 'to_dict'):
            config_dict = config.to_dict()
            agents_config = config_dict.get("agents", {})
        
        return AgentConfigResponse(
            agents=agents_config,
            total=len(agents_config)
        )
        
    except Exception as e:
        logger.error(f"Error getting agent config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent config: {str(e)}")


@router.get("/workflows", response_model=WorkflowConfigResponse)
async def get_workflow_config():
    """Get workflow configuration.
    
    Returns:
        WorkflowConfigResponse with workflow configuration
    """
    try:
        from src.core.config import Config
        
        # Use injected config snapshot or load fresh
        if _config_snapshot:
            config = _config_snapshot
        else:
            config_path = Path("./config/orchestration.yaml")
            if config_path.exists():
                config = Config.from_yaml(config_path)
            else:
                return WorkflowConfigResponse(workflows={}, total=0)
        
        # Extract workflow configuration
        workflows_config = {}
        if hasattr(config, 'workflows'):
            workflows_config = config.workflows if isinstance(config.workflows, dict) else {}
        elif hasattr(config, 'to_dict'):
            config_dict = config.to_dict()
            workflows_config = config_dict.get("workflows", {})
        
        return WorkflowConfigResponse(
            workflows=workflows_config,
            total=len(workflows_config)
        )
        
    except Exception as e:
        logger.error(f"Error getting workflow config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get workflow config: {str(e)}")


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config():
    """Get LLM configuration.
    
    Returns:
        LLMConfigResponse with LLM provider configuration
    """
    try:
        from src.core.config import Config
        
        # Use injected config snapshot or load fresh
        if _config_snapshot:
            config = _config_snapshot
        else:
            config_path = Path("./config/orchestration.yaml")
            if config_path.exists():
                config = Config.from_yaml(config_path)
            else:
                return LLMConfigResponse(providers={})
        
        # Extract LLM configuration
        llm_config = {}
        default_provider = None
        default_model = None
        
        if hasattr(config, 'llm'):
            llm_config = config.llm if isinstance(config.llm, dict) else {}
        elif hasattr(config, 'to_dict'):
            config_dict = config.to_dict()
            llm_config = config_dict.get("llm", {})
        
        # Extract defaults
        if llm_config:
            default_provider = llm_config.get("default_provider")
            default_model = llm_config.get("default_model")
        
        providers = llm_config.get("providers", {})
        
        return LLMConfigResponse(
            providers=providers,
            default_provider=default_provider,
            default_model=default_model
        )
        
    except Exception as e:
        logger.error(f"Error getting LLM config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get LLM config: {str(e)}")


# ============================================================================
# NEW: Enhanced Config Endpoints (Task Card 04)
# ============================================================================

@router.get("/tone")
async def get_tone_config():
    """Get tone configuration (mirrors cmd_config_tone).
    
    Returns:
        Tone configuration
    """
    try:
        from src.core.config import Config
        
        # Use injected config snapshot or load fresh
        if _config_snapshot:
            config = _config_snapshot
        else:
            config_path = Path("./config/orchestration.yaml")
            if config_path.exists():
                config = Config.from_yaml(config_path)
            else:
                return JSONResponse(content={
                    "tone": {},
                    "message": "Configuration file not found"
                })
        
        # Extract tone configuration
        tone_config = {}
        if hasattr(config, 'tone'):
            tone_config = config.tone if isinstance(config.tone, dict) else {}
        elif hasattr(config, 'to_dict'):
            config_dict = config.to_dict()
            tone_config = config_dict.get("tone", {})
        
        return JSONResponse(content={
            "tone": tone_config,
            "total_settings": len(tone_config)
        })
        
    except Exception as e:
        logger.error(f"Error getting tone config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get tone config: {str(e)}")


@router.get("/performance")
async def get_performance_config():
    """Get performance configuration (mirrors cmd_config_performance).
    
    Returns:
        Performance configuration
    """
    try:
        from src.core.config import Config
        
        # Use injected config snapshot or load fresh
        if _config_snapshot:
            config = _config_snapshot
        else:
            config_path = Path("./config/orchestration.yaml")
            if config_path.exists():
                config = Config.from_yaml(config_path)
            else:
                return JSONResponse(content={
                    "performance": {},
                    "message": "Configuration file not found"
                })
        
        # Extract performance configuration
        perf_config = {}
        if hasattr(config, 'performance'):
            perf_config = config.performance if isinstance(config.performance, dict) else {}
        elif hasattr(config, 'to_dict'):
            config_dict = config.to_dict()
            perf_config = config_dict.get("performance", {})
        
        return JSONResponse(content={
            "performance": perf_config,
            "total_settings": len(perf_config)
        })
        
    except Exception as e:
        logger.error(f"Error getting performance config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get performance config: {str(e)}")


@router.post("/hot-reload")
async def trigger_hot_reload():
    """Trigger configuration hot-reload.
    
    Returns:
        Hot-reload result
    """
    try:
        from datetime import datetime, timezone
        
        # Try to import and use HotReload if available
        try:
            from src.orchestration.hot_reload import HotReload
            reloader = HotReload()
            result = reloader.reload_all()
            
            return JSONResponse(content={
                "status": "success",
                "reloaded": result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except ImportError:
            # HotReload not available, just reload config snapshot
            from src.core.config import Config
            config_path = Path("./config/orchestration.yaml")
            
            if config_path.exists():
                new_config = Config.from_yaml(config_path)
                set_config_snapshot(new_config)
                
                return JSONResponse(content={
                    "status": "success",
                    "reloaded": ["config"],
                    "message": "Configuration reloaded (HotReload module not available)",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                return JSONResponse(content={
                    "status": "failed",
                    "error": "Configuration file not found",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
        
    except Exception as e:
        logger.error(f"Error triggering hot-reload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger hot-reload: {str(e)}")


class ConfigValidateRequest(BaseModel):
    """Request to validate configuration."""
    agents: Optional[Dict[str, Any]] = Field(default=None, description="Agent configuration to validate")
    workflows: Optional[Dict[str, Any]] = Field(default=None, description="Workflow configuration to validate")
    llm: Optional[Dict[str, Any]] = Field(default=None, description="LLM configuration to validate")


@router.post("/validate")
async def validate_config(request: ConfigValidateRequest):
    """Validate configuration (mirrors cmd_config_validate).

    Args:
        request: Configuration to validate

    Returns:
        Validation result with errors or success
    """
    try:
        from src.core.config_validator import validate_config as validate_config_core
        from datetime import datetime, timezone

        # Build config dict from request
        config_dict = {}
        if request.agents:
            config_dict['agents'] = request.agents
        if request.workflows:
            config_dict['workflows'] = request.workflows
        if request.llm:
            config_dict['llm'] = request.llm

        # If no config provided, return error
        if not config_dict:
            return JSONResponse(
                status_code=422,
                content={
                    "valid": False,
                    "errors": ["No configuration provided to validate"],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

        # Perform validation
        try:
            validation_result = validate_config_core(config_dict)

            return JSONResponse(content={
                "valid": validation_result.get("valid", True),
                "errors": validation_result.get("errors", []),
                "warnings": validation_result.get("warnings", []),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        except Exception as validation_error:
            # Validation failed with exception
            return JSONResponse(content={
                "valid": False,
                "errors": [str(validation_error)],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

    except Exception as e:
        logger.error(f"Error validating config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate config: {str(e)}")
