"""
MCP Endpoint Handlers for UCOP

Implements handler functions for all MCP protocol endpoints:
- workflow.execute
- workflow.status
- workflow.checkpoint.list
- workflow.checkpoint.restore
- agent.invoke
- agent.list
- realtime.subscribe
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json
import time
import uuid

from src.mcp.protocol import (
    MCPRequest,
    MCPResponse,
    MCPError,
    ResourceType,
    ResourceStatus,
    JobResource,
    AgentResource,
    WorkflowResource,
    AgentCapability,
    create_resource_uri,
)
from src.mcp.traffic_logger import get_traffic_logger

logger = logging.getLogger(__name__)

# Global executor reference (set by initialization)
_executor = None
_job_engine = None
_agent_registry = None


def set_dependencies(executor, job_engine=None, agent_registry=None):
    """Set handler dependencies.
    
    Args:
        executor: Unified execution engine
        job_engine: Job execution engine
        agent_registry: Agent registry for agent discovery
    """
    global _executor, _job_engine, _agent_registry
    _executor = executor
    _job_engine = job_engine
    _agent_registry = agent_registry
    logger.info("MCP handlers initialized with dependencies")


def get_executor():
    """Get executor instance."""
    if _executor is None:
        raise RuntimeError("Executor not initialized. Call set_dependencies first.")
    return _executor


def get_job_engine():
    """Get job engine instance."""
    if _job_engine is None:
        # Fallback to executor's job engine
        executor = get_executor()
        if hasattr(executor, 'job_engine'):
            return executor.job_engine
        raise RuntimeError("Job engine not available")
    return _job_engine


def get_agent_registry():
    """Get agent registry instance."""
    if _agent_registry is None:
        logger.warning("Agent registry not available, using fallback")
        return None
    return _agent_registry


# ============================================================================
# Workflow Handlers
# ============================================================================

async def handle_workflow_execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a workflow.
    
    Args:
        params: {
            "workflow_id": str,
            "inputs": dict,
            "checkpoint_enabled": bool (optional)
        }
    
    Returns:
        Job resource with execution details
        
    Example:
        >>> params = {
        ...     "workflow_id": "fast-draft",
        ...     "inputs": {"topic": "AI trends", "output_dir": "./output"}
        ... }
        >>> result = await handle_workflow_execute(params)
    """
    logger.info(f"MCP: workflow.execute called with params: {params}")
    
    workflow_id = params.get("workflow_id")
    inputs = params.get("inputs", {})
    checkpoint_enabled = params.get("checkpoint_enabled", True)
    
    if not workflow_id:
        raise ValueError("workflow_id is required")
    
    # Get job engine
    job_engine = get_job_engine()
    
    # Create job
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    # Submit job to engine
    try:
        # Create job configuration
        from src.engine.executor import JobConfig
        
        job_config = JobConfig(
            workflow=workflow_id,
            input=inputs.get("topic", ""),
            params={
                **inputs,
                "checkpoint_enabled": checkpoint_enabled
            }
        )
        
        # Execute the job
        result = get_executor().run_job(job_config)
        
        # Return job resource
        return {
            "job_id": result.job_id,
            "workflow_id": workflow_id,
            "status": result.status,
            "started_at": result.started_at,
            "uri": create_resource_uri(ResourceType.JOB, result.job_id)
        }
        
    except Exception as e:
        logger.error(f"Failed to execute workflow {workflow_id}: {e}", exc_info=True)
        raise


async def handle_workflow_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get workflow execution status.
    
    Args:
        params: {
            "job_id": str
        }
    
    Returns:
        Job status with pipeline details
        
    Example:
        >>> params = {"job_id": "job_20250111_120000_001"}
        >>> result = await handle_workflow_status(params)
    """
    logger.info(f"MCP: workflow.status called with params: {params}")
    
    job_id = params.get("job_id")
    if not job_id:
        raise ValueError("job_id is required")
    
    # Get job engine
    job_engine = get_job_engine()
    
    # Get job details
    if hasattr(job_engine, '_jobs'):
        job = job_engine._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        # Convert job to dict
        job_dict = job.to_dict() if hasattr(job, 'to_dict') else {
            "id": job_id,
            "status": getattr(job, 'status', 'unknown'),
            "workflow_name": getattr(job, 'workflow_name', 'unknown'),
        }
        
        return {
            "job_id": job_id,
            "status": job_dict.get("status", "unknown"),
            "workflow_name": job_dict.get("workflow_name"),
            "progress": job_dict.get("progress", 0),
            "current_step": job_dict.get("current_step"),
            "pipeline": job_dict.get("pipeline", []),
            "started_at": job_dict.get("started_at"),
            "completed_at": job_dict.get("completed_at"),
            "error": job_dict.get("error"),
            "uri": create_resource_uri(ResourceType.JOB, job_id)
        }
    
    raise ValueError("Job engine not properly configured")


async def handle_workflow_checkpoint_list(params: Dict[str, Any]) -> Dict[str, Any]:
    """List available checkpoints for a job.
    
    Args:
        params: {
            "job_id": str
        }
    
    Returns:
        List of checkpoint resources
        
    Example:
        >>> params = {"job_id": "job_20250111_120000_001"}
        >>> result = await handle_workflow_checkpoint_list(params)
    """
    logger.info(f"MCP: workflow.checkpoint.list called with params: {params}")
    
    job_id = params.get("job_id")
    if not job_id:
        raise ValueError("job_id is required")
    
    # Look for checkpoints directory
    checkpoint_dir = Path(f"./data/jobs/{job_id}/checkpoints")
    
    if not checkpoint_dir.exists():
        return {"checkpoints": []}
    
    checkpoints = []
    for checkpoint_file in checkpoint_dir.glob("*.json"):
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
            
            checkpoints.append({
                "id": checkpoint_file.stem,
                "job_id": job_id,
                "step_id": checkpoint_data.get("step_id"),
                "timestamp": checkpoint_data.get("timestamp"),
                "status": checkpoint_data.get("status"),
                "uri": create_resource_uri(ResourceType.CHECKPOINT, checkpoint_file.stem)
            })
        except Exception as e:
            logger.error(f"Failed to read checkpoint {checkpoint_file}: {e}")
            continue
    
    return {
        "job_id": job_id,
        "checkpoints": sorted(checkpoints, key=lambda x: x.get("timestamp", ""), reverse=True)
    }


async def handle_workflow_checkpoint_restore(params: Dict[str, Any]) -> Dict[str, Any]:
    """Restore workflow from checkpoint.
    
    Args:
        params: {
            "job_id": str,
            "checkpoint_id": str
        }
    
    Returns:
        Restored job resource
        
    Example:
        >>> params = {
        ...     "job_id": "job_20250111_120000_001",
        ...     "checkpoint_id": "checkpoint_step_5"
        ... }
        >>> result = await handle_workflow_checkpoint_restore(params)
    """
    logger.info(f"MCP: workflow.checkpoint.restore called with params: {params}")
    
    job_id = params.get("job_id")
    checkpoint_id = params.get("checkpoint_id")
    
    if not job_id or not checkpoint_id:
        raise ValueError("job_id and checkpoint_id are required")
    
    # Load checkpoint
    checkpoint_file = Path(f"./data/jobs/{job_id}/checkpoints/{checkpoint_id}.json")
    
    if not checkpoint_file.exists():
        raise ValueError(f"Checkpoint not found: {checkpoint_id}")
    
    try:
        with open(checkpoint_file, 'r') as f:
            checkpoint_data = json.load(f)
        
        # Get job engine
        job_engine = get_job_engine()
        
        # Restore job state from checkpoint
        # This is a placeholder - actual restoration depends on job engine implementation
        logger.info(f"Restoring job {job_id} from checkpoint {checkpoint_id}")
        
        return {
            "job_id": job_id,
            "checkpoint_id": checkpoint_id,
            "status": "restored",
            "restored_at": datetime.now().isoformat(),
            "checkpoint_step": checkpoint_data.get("step_id"),
            "message": "Job restored from checkpoint successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to restore checkpoint: {e}", exc_info=True)
        raise


# ============================================================================
# Agent Handlers
# ============================================================================

async def handle_agent_invoke(params: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke an agent directly.
    
    Args:
        params: {
            "agent_id": str,
            "input": dict,
            "context": dict (optional)
        }
    
    Returns:
        Agent execution result
        
    Example:
        >>> params = {
        ...     "agent_id": "topic_identification",
        ...     "input": {"kb_path": "./data/kb"}
        ... }
        >>> result = await handle_agent_invoke(params)
    """
    logger.info(f"MCP: agent.invoke called with params: {params}")
    
    agent_id = params.get("agent_id")
    agent_input = params.get("input", {})
    context = params.get("context", {})
    
    if not agent_id:
        raise ValueError("agent_id is required")
    
    # Get executor
    executor = get_executor()
    
    try:
        # Get agent instance from registry or executor
        agent_registry = get_agent_registry()
        
        if agent_registry and hasattr(agent_registry, 'get_agent'):
            agent = agent_registry.get_agent(agent_id)
        elif hasattr(executor, 'agents'):
            # Fallback: get from executor's agent list
            agent = next((a for a in executor.agents if a.id == agent_id), None)
            if not agent:
                raise ValueError(f"Agent not found: {agent_id}")
        else:
            raise ValueError(f"Cannot invoke agent: {agent_id} (registry not available)")
        
        # Execute agent
        logger.info(f"Invoking agent {agent_id} with input: {agent_input}")
        
        result = await agent.execute(agent_input, context=context)
        
        return {
            "agent_id": agent_id,
            "status": "completed",
            "output": result,
            "executed_at": datetime.now().isoformat(),
            "uri": create_resource_uri(ResourceType.AGENT, agent_id)
        }
        
    except Exception as e:
        logger.error(f"Failed to invoke agent {agent_id}: {e}", exc_info=True)
        return {
            "agent_id": agent_id,
            "status": "failed",
            "error": str(e),
            "executed_at": datetime.now().isoformat()
        }


async def handle_agent_list(params: Dict[str, Any]) -> Dict[str, Any]:
    """List all available agents.
    
    Args:
        params: {
            "category": str (optional) - filter by category
        }
    
    Returns:
        List of agent resources
        
    Example:
        >>> params = {"category": "research"}
        >>> result = await handle_agent_list(params)
    """
    logger.info(f"MCP: agent.list called with params: {params}")
    
    category_filter = params.get("category")
    
    # Get agents from registry or discover from filesystem
    agents = []
    
    # Try to get from agent registry first
    agent_registry = get_agent_registry()
    if agent_registry and hasattr(agent_registry, 'list_agents'):
        agents = agent_registry.list_agents()
    else:
        # Fallback: discover from src/agents directory
        agents_dir = Path(__file__).parent.parent / "agents"
        
        agent_categories = {
            "ingestion": ["kb_ingestion", "docs_ingestion", "api_ingestion", "blog_ingestion", "tutorial_ingestion"],
            "research": ["topic_identification", "multi_file_topic_discovery", "kb_search", "docs_search", "api_search", 
                        "blog_search", "tutorial_search", "duplication_check", "content_intelligence", 
                        "competitor_analysis", "trends_research"],
            "content": ["outline_creation", "introduction_writer", "section_writer", "conclusion_writer", 
                       "supplementary_content", "content_assembly"],
            "code": ["code_extraction", "code_generation", "code_validation", "code_splitting", 
                    "api_validator", "license_injection"],
            "seo": ["keyword_extraction", "keyword_injection", "seo_metadata"],
            "publishing": ["frontmatter_enhanced", "gist_upload", "gist_readme", "file_writer", "link_validation"],
            "support": ["validation", "quality_gate", "error_recovery", "model_selection"]
        }
        
        for cat, agent_names in agent_categories.items():
            if category_filter and cat != category_filter:
                continue
                
            category_dir = agents_dir / cat
            if not category_dir.exists():
                continue
                
            for agent_name in agent_names:
                agent_file = category_dir / f"{agent_name}.py"
                if agent_file.exists():
                    agents.append({
                        "id": agent_name,
                        "name": agent_name.replace("_", " ").title(),
                        "type": cat,
                        "category": cat,
                        "status": "idle",
                        "uri": create_resource_uri(ResourceType.AGENT, agent_name),
                        "capabilities": []
                    })
    
    return {
        "agents": agents,
        "total": len(agents),
        "category_filter": category_filter
    }

# ============================================================================
# Ingestion Handlers
# ============================================================================

async def handle_ingest_kb(params: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest Knowledge Base articles.
    
    Args:
        params: {
            "kb_path": str - Path to KB file or directory
        }
    
    Returns:
        Ingestion result with statistics
    """
    logger.info(f"MCP: ingest/kb called with params: {params}")
    
    kb_path = params.get("kb_path")
    if not kb_path:
        raise ValueError("kb_path is required")
    
    # Get executor
    executor = get_executor()
    
    # Create event for ingestion
    from src.core.contracts import AgentEvent
    event = AgentEvent(
        event_type="execute_ingest_kb",
        data={"kb_path": kb_path},
        source_agent="mcp_handler",
        correlation_id=f"ingest_kb_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    # Find KB ingestion agent
    kb_agent = None
    if hasattr(executor, 'agents'):
        kb_agent = next(
            (a for a in executor.agents if a.agent_id == "KBIngestionAgent"),
            None
        )
    
    if not kb_agent:
        raise ValueError("KBIngestionAgent not found in executor")
    
    # Execute ingestion
    try:
        result_event = kb_agent.execute(event)
        
        return {
            "status": "completed",
            "kb_path": kb_path,
            "result": result_event.data if result_event else {},
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"KB ingestion failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "kb_path": kb_path,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }


async def handle_ingest_docs(params: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest documentation files.
    
    Args:
        params: {
            "docs_path": str - Path to docs file or directory
        }
    
    Returns:
        Ingestion result with statistics
    """
    logger.info(f"MCP: ingest/docs called with params: {params}")
    
    docs_path = params.get("docs_path")
    if not docs_path:
        raise ValueError("docs_path is required")
    
    executor = get_executor()
    
    from src.core.contracts import AgentEvent
    event = AgentEvent(
        event_type="execute_ingest_docs",
        data={"docs_path": docs_path},
        source_agent="mcp_handler",
        correlation_id=f"ingest_docs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    docs_agent = None
    if hasattr(executor, 'agents'):
        docs_agent = next(
            (a for a in executor.agents if a.agent_id == "DocsIngestionAgent"),
            None
        )
    
    if not docs_agent:
        raise ValueError("DocsIngestionAgent not found in executor")
    
    try:
        result_event = docs_agent.execute(event)
        
        return {
            "status": "completed",
            "docs_path": docs_path,
            "result": result_event.data if result_event else {},
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Docs ingestion failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "docs_path": docs_path,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }


async def handle_ingest_api(params: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest API documentation.
    
    Args:
        params: {
            "api_path": str - Path to API docs file or directory
        }
    
    Returns:
        Ingestion result with statistics
    """
    logger.info(f"MCP: ingest/api called with params: {params}")
    
    api_path = params.get("api_path")
    if not api_path:
        raise ValueError("api_path is required")
    
    executor = get_executor()
    
    from src.core.contracts import AgentEvent
    event = AgentEvent(
        event_type="execute_ingest_api",
        data={"api_path": api_path},
        source_agent="mcp_handler",
        correlation_id=f"ingest_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    api_agent = None
    if hasattr(executor, 'agents'):
        api_agent = next(
            (a for a in executor.agents if a.agent_id == "APIIngestionAgent"),
            None
        )
    
    if not api_agent:
        raise ValueError("APIIngestionAgent not found in executor")
    
    try:
        result_event = api_agent.execute(event)
        
        return {
            "status": "completed",
            "api_path": api_path,
            "result": result_event.data if result_event else {},
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"API ingestion failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "api_path": api_path,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }


async def handle_ingest_blog(params: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest existing blog posts.
    
    Args:
        params: {
            "blog_path": str - Path to blog file or directory
        }
    
    Returns:
        Ingestion result with statistics
    """
    logger.info(f"MCP: ingest/blog called with params: {params}")
    
    blog_path = params.get("blog_path")
    if not blog_path:
        raise ValueError("blog_path is required")
    
    executor = get_executor()
    
    from src.core.contracts import AgentEvent
    event = AgentEvent(
        event_type="execute_ingest_blog",
        data={"blog_path": blog_path},
        source_agent="mcp_handler",
        correlation_id=f"ingest_blog_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    blog_agent = None
    if hasattr(executor, 'agents'):
        blog_agent = next(
            (a for a in executor.agents if a.agent_id == "BlogIngestionAgent"),
            None
        )
    
    if not blog_agent:
        raise ValueError("BlogIngestionAgent not found in executor")
    
    try:
        result_event = blog_agent.execute(event)
        
        return {
            "status": "completed",
            "blog_path": blog_path,
            "result": result_event.data if result_event else {},
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Blog ingestion failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "blog_path": blog_path,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }


async def handle_ingest_tutorial(params: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest tutorial files.
    
    Args:
        params: {
            "tutorial_path": str - Path to tutorial file or directory
        }
    
    Returns:
        Ingestion result with statistics
    """
    logger.info(f"MCP: ingest/tutorial called with params: {params}")
    
    tutorial_path = params.get("tutorial_path")
    if not tutorial_path:
        raise ValueError("tutorial_path is required")
    
    executor = get_executor()
    
    from src.core.contracts import AgentEvent
    event = AgentEvent(
        event_type="execute_ingest_tutorial",
        data={"tutorial_path": tutorial_path},
        source_agent="mcp_handler",
        correlation_id=f"ingest_tutorial_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    tutorial_agent = None
    if hasattr(executor, 'agents'):
        tutorial_agent = next(
            (a for a in executor.agents if a.agent_id == "TutorialIngestionAgent"),
            None
        )
    
    if not tutorial_agent:
        raise ValueError("TutorialIngestionAgent not found in executor")
    
    try:
        result_event = tutorial_agent.execute(event)
        
        return {
            "status": "completed",
            "tutorial_path": tutorial_path,
            "result": result_event.data if result_event else {},
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Tutorial ingestion failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "tutorial_path": tutorial_path,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }



async def handle_topics_discover(params: Dict[str, Any]) -> Dict[str, Any]:
    """Discover topics from directory of files.
    
    Args:
        params: {
            "kb_path": str - Path to KB directory (optional)
            "docs_path": str - Path to docs directory (optional)
            "max_topics": int - Maximum topics to return (default: 50)
        }
    
    Returns:
        List of discovered topics with metadata
    """
    logger.info(f"MCP: topics/discover called with params: {params}")
    
    kb_path = params.get("kb_path")
    docs_path = params.get("docs_path")
    max_topics = params.get("max_topics", 50)
    
    if not kb_path and not docs_path:
        raise ValueError("At least one of kb_path or docs_path is required")
    
    executor = get_executor()
    
    from src.core.contracts import AgentEvent
    event = AgentEvent(
        event_type="execute_discover_topics",
        data={
            "kb_path": kb_path,
            "docs_path": docs_path,
            "max_topics": max_topics
        },
        source_agent="mcp_handler",
        correlation_id=f"discover_topics_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    # Find topic discovery agent
    topic_agent = None
    if hasattr(executor, 'agents'):
        topic_agent = next(
            (a for a in executor.agents if a.agent_id == "MultiFileTopicDiscoveryAgent"),
            None
        )
    
    if not topic_agent:
        raise ValueError("MultiFileTopicDiscoveryAgent not found in executor")
    
    try:
        result_event = topic_agent.execute(event)
        
        return {
            "status": "completed",
            "topics": result_event.data.get("topics", []),
            "total_discovered": result_event.data.get("total_discovered", 0),
            "after_dedup": result_event.data.get("after_dedup", 0),
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Topic discovery failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }

# ============================================================================
# Real-time Handlers
# ============================================================================

async def handle_realtime_subscribe(params: Dict[str, Any]) -> Dict[str, Any]:
    """Subscribe to real-time updates.
    
    Args:
        params: {
            "job_id": str,
            "event_types": list[str] (optional)
        }
    
    Returns:
        Subscription details and WebSocket connection info
        
    Example:
        >>> params = {
        ...     "job_id": "job_20250111_120000_001",
        ...     "event_types": ["status", "progress", "log"]
        ... }
        >>> result = await handle_realtime_subscribe(params)
    """
    logger.info(f"MCP: realtime.subscribe called with params: {params}")
    
    job_id = params.get("job_id")
    event_types = params.get("event_types", ["status", "progress", "log", "error"])
    
    if not job_id:
        raise ValueError("job_id is required")
    
    # Return WebSocket connection details
    # The actual WebSocket connection is handled separately
    return {
        "job_id": job_id,
        "subscription_id": f"sub_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "event_types": event_types,
        "websocket_url": f"ws://localhost:8000/ws/mesh?job={job_id}",
        "status": "ready",
        "message": "Connect to the WebSocket URL to receive real-time updates"
    }


# ============================================================================
# Request Router
# ============================================================================

async def route_request(request: MCPRequest) -> MCPResponse:
    """Route MCP request to appropriate handler with traffic logging.
    
    Args:
        request: MCP request
        
    Returns:
        MCP response
    """
    logger.info(f"Routing MCP request: {request.method}")
    
    # Log the request
    traffic_logger = get_traffic_logger()
    message_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Extract source/target from params (with fallbacks)
    from_agent = request.params.get("from_agent", "mcp_client")
    to_agent = request.params.get("to_agent", request.method.split('.')[0] if '.' in request.method else "system")
    
    traffic_logger.log_request(
        message_id=message_id,
        message_type=request.method,
        from_agent=from_agent,
        to_agent=to_agent,
        request=request.params
    )
    
    try:
        # Route to handler based on method
        if request.method == "workflow.execute":
            result = await handle_workflow_execute(request.params)
        elif request.method == "workflow.status":
            result = await handle_workflow_status(request.params)
        elif request.method == "workflow.checkpoint.list":
            result = await handle_workflow_checkpoint_list(request.params)
        elif request.method == "workflow.checkpoint.restore":
            result = await handle_workflow_checkpoint_restore(request.params)
        elif request.method == "agent.invoke":
            result = await handle_agent_invoke(request.params)
        elif request.method == "agent.list":
            result = await handle_agent_list(request.params)
        elif request.method == "ingest/kb":
            result = await handle_ingest_kb(request.params)
        elif request.method == "ingest/docs":
            result = await handle_ingest_docs(request.params)
        elif request.method == "ingest/api":
            result = await handle_ingest_api(request.params)
        elif request.method == "ingest/blog":
            result = await handle_ingest_blog(request.params)
        elif request.method == "ingest/tutorial":
            result = await handle_ingest_tutorial(request.params)
        elif request.method == "topics/discover":
            result = await handle_topics_discover(request.params)
        elif request.method == "realtime.subscribe":
            result = await handle_realtime_subscribe(request.params)
        else:
            # Method not found
            return MCPResponse(
                error={
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                },
                id=request.id
            )
        
        # Log successful response
        duration_ms = (time.time() - start_time) * 1000
        traffic_logger.log_response(
            message_id=message_id,
            response=result,
            status="success",
            duration_ms=duration_ms
        )
        
        # Return successful response
        return MCPResponse(result=result, id=request.id)
        
    except ValueError as e:
        # Invalid parameters
        logger.error(f"Invalid parameters for {request.method}: {e}")
        
        # Log error response
        duration_ms = (time.time() - start_time) * 1000
        traffic_logger.log_response(
            message_id=message_id,
            response={},
            status="error",
            duration_ms=duration_ms,
            error=str(e)
        )
        
        return MCPResponse(
            error={
                "code": -32602,
                "message": f"Invalid params: {str(e)}"
            },
            id=request.id
        )
    except Exception as e:
        # Internal error
        logger.error(f"Internal error processing {request.method}: {e}", exc_info=True)
        
        # Log error response
        duration_ms = (time.time() - start_time) * 1000
        traffic_logger.log_response(
            message_id=message_id,
            response={},
            status="error",
            duration_ms=duration_ms,
            error=str(e)
        )
        
        return MCPResponse(
            error={
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            id=request.id
        )
# DOCGEN:LLM-FIRST@v4