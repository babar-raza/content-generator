"""Agent information and logging API routes."""

import re
import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query

from ..models import (
    AgentInfo,
    AgentList,
    AgentLogs,
    AgentLogEntry,
    AgentHealth,
    AgentHealthMetrics,
    HealthSummary,
    FailureReport,
    FailureList,
)
from ...orchestration.agent_health_monitor import get_health_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agents"])


# This will be injected by the app
_jobs_store = None
_executor = None
_agent_logs = {}


def set_jobs_store(store):
    """Set the jobs store for dependency injection."""
    global _jobs_store
    _jobs_store = store


def set_executor(executor):
    """Set the executor for dependency injection."""
    global _executor
    _executor = executor


def set_agent_logs(logs):
    """Set the agent logs storage."""
    global _agent_logs
    _agent_logs = logs


def get_jobs_store():
    """Dependency to get jobs store."""
    if _jobs_store is None:
        raise HTTPException(status_code=503, detail="Jobs store not initialized")
    return _jobs_store


def get_executor():
    """Dependency to get executor."""
    if _executor is None:
        raise HTTPException(status_code=503, detail="Executor not initialized")
    return _executor


def get_agent_logs():
    """Dependency to get agent logs."""
    return _agent_logs


# Secret patterns to redact
SECRET_PATTERNS = [
    (re.compile(r'(api[_-]?key|apikey)["\s:=]+([a-zA-Z0-9_-]+)', re.IGNORECASE), r'\1=***REDACTED***'),
    (re.compile(r'(token)["\s:=]+([a-zA-Z0-9_.-]+)', re.IGNORECASE), r'\1=***REDACTED***'),
    (re.compile(r'(password|passwd|pwd)["\s:=]+([^\s"\']+)', re.IGNORECASE), r'\1=***REDACTED***'),
    (re.compile(r'(secret)["\s:=]+([a-zA-Z0-9_-]+)', re.IGNORECASE), r'\1=***REDACTED***'),
    (re.compile(r'(authorization:?\s*)(bearer\s+[a-zA-Z0-9_.-]+)', re.IGNORECASE), r'\1Bearer ***REDACTED***'),
    (re.compile(r'(auth)["\s:=]+([a-zA-Z0-9_-]+)', re.IGNORECASE), r'\1=***REDACTED***'),
    (re.compile(r'(["\']?key["\']?:\s*["\'])([a-zA-Z0-9_-]+)', re.IGNORECASE), r'\1***REDACTED***'),
]


def redact_secrets(text: str) -> str:
    """Redact secrets from log text (app_unified.py utility).
    
    Args:
        text: Original text that may contain secrets
        
    Returns:
        Text with secrets redacted
    """
    if not text:
        return text
    
    redacted = text
    
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    
    return redacted


@router.get("/agents", response_model=AgentList)
async def list_agents(
    executor=Depends(get_executor)
):
    """List all available agents.
    
    Returns:
        AgentList with agent information
    """
    try:
        agents_data = []
        
        # Get agents from executor
        if hasattr(executor, 'get_agents'):
            agents = executor.get_agents()
            
            for agent in agents:
                agents_data.append(AgentInfo(
                    agent_id=agent.get("id", agent.get("name", "unknown")),
                    name=agent.get("name", "Unknown"),
                    type=agent.get("type", "unknown"),
                    description=agent.get("description"),
                    status=agent.get("status", "available"),
                    capabilities=agent.get("capabilities", []),
                    metadata=agent.get("metadata"),
                ))
        else:
            # Return empty list if executor doesn't support get_agents
            logger.warning("Executor does not support get_agents method")
        
        return AgentList(agents=agents_data, total=len(agents_data))
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@router.get("/agents/{agent_id}", response_model=AgentInfo)
async def get_agent(
    agent_id: str,
    executor=Depends(get_executor)
):
    """Get information about a specific agent.
    
    Args:
        agent_id: Agent identifier
        
    Returns:
        AgentInfo with agent details
    """
    try:
        # Get agent from executor
        if hasattr(executor, 'get_agent'):
            agent = executor.get_agent(agent_id)
            
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
            
            return AgentInfo(
                agent_id=agent.get("id", agent_id),
                name=agent.get("name", "Unknown"),
                type=agent.get("type", "unknown"),
                description=agent.get("description"),
                status=agent.get("status", "available"),
                capabilities=agent.get("capabilities", []),
                metadata=agent.get("metadata"),
            )
        else:
            raise HTTPException(status_code=501, detail="Agent lookup not supported")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")


@router.get("/jobs/{job_id}/logs/{agent_name}", response_model=AgentLogs)
async def get_job_agent_logs(
    job_id: str,
    agent_name: str,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    store=Depends(get_jobs_store),
    logs_store=Depends(get_agent_logs)
):
    """Get logs for a specific agent in a job (app_unified.py endpoint).
    
    Args:
        job_id: Job identifier
        agent_name: Agent name
        limit: Maximum number of log entries to return
        offset: Offset for pagination
        
    Returns:
        AgentLogs with log entries (secrets redacted)
    """
    try:
        # Check if job exists
        if job_id not in store:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Get logs for this job and agent
        log_key = f"{job_id}:{agent_name}"
        job_logs = logs_store.get(log_key, [])
        
        # Apply pagination
        total = len(job_logs)
        logs_page = job_logs[offset:offset + limit]
        
        # Convert to AgentLogEntry models and redact secrets
        log_entries = []
        for log in logs_page:
            # Redact secrets from message
            message = redact_secrets(log.get("message", ""))
            
            # Redact secrets from metadata if present
            metadata = log.get("metadata")
            if metadata and isinstance(metadata, dict):
                metadata = {
                    k: redact_secrets(str(v)) if isinstance(v, str) else v
                    for k, v in metadata.items()
                }
            
            log_entries.append(AgentLogEntry(
                timestamp=log.get("timestamp", datetime.now(timezone.utc)),
                level=log.get("level", "INFO"),
                agent_name=agent_name,
                message=message,
                metadata=metadata,
            ))
        
        return AgentLogs(
            job_id=job_id,
            agent_name=agent_name,
            logs=log_entries,
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting logs for job {job_id}, agent {agent_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent logs: {str(e)}")


@router.get("/agents/{agent_id}/logs", response_model=AgentLogs)
async def get_agent_logs(
    agent_id: str,
    job_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    logs_store=Depends(get_agent_logs)
):
    """Get logs for a specific agent across all jobs or for a specific job (app_unified.py endpoint).
    
    Args:
        agent_id: Agent identifier
        job_id: Optional job identifier to filter logs
        limit: Maximum number of log entries to return
        offset: Offset for pagination
        
    Returns:
        AgentLogs with log entries (secrets redacted)
    """
    try:
        # Collect logs for this agent
        all_logs = []
        
        if job_id:
            # Get logs for specific job
            log_key = f"{job_id}:{agent_id}"
            all_logs = logs_store.get(log_key, [])
        else:
            # Get logs from all jobs for this agent
            for key, logs in logs_store.items():
                if key.endswith(f":{agent_id}"):
                    all_logs.extend(logs)
        
        # Sort by timestamp (newest first)
        all_logs.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
        
        # Apply pagination
        total = len(all_logs)
        logs_page = all_logs[offset:offset + limit]
        
        # Convert to AgentLogEntry models and redact secrets
        log_entries = []
        for log in logs_page:
            # Redact secrets from message
            message = redact_secrets(log.get("message", ""))
            
            # Redact secrets from metadata if present
            metadata = log.get("metadata")
            if metadata and isinstance(metadata, dict):
                metadata = {
                    k: redact_secrets(str(v)) if isinstance(v, str) else v
                    for k, v in metadata.items()
                }
            
            log_entries.append(AgentLogEntry(
                timestamp=log.get("timestamp", datetime.now(timezone.utc)),
                level=log.get("level", "INFO"),
                agent_name=agent_id,
                message=message,
                metadata=metadata,
            ))
        
        return AgentLogs(
            job_id=job_id,
            agent_name=agent_id,
            logs=log_entries,
            total=total
        )
        
    except Exception as e:
        logger.error(f"Error getting logs for agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent logs: {str(e)}")


# ============================================================================
# Agent Health Monitoring
# ============================================================================

@router.get("/agents/health", response_model=HealthSummary)
async def get_agents_health_summary():
    """Get overall health summary for all agents.
    
    Returns:
        HealthSummary with metrics for all agents
    """
    try:
        monitor = get_health_monitor()
        summary = monitor.get_health_summary()
        
        return HealthSummary(
            timestamp=summary["timestamp"],
            total_agents=summary["total_agents"],
            healthy_agents=summary["healthy_agents"],
            degraded_agents=summary["degraded_agents"],
            failing_agents=summary["failing_agents"],
            unknown_agents=summary["unknown_agents"],
            agents=[
                AgentHealthMetrics(
                    agent_id=agent["agent_id"],
                    total_executions=agent["total_executions"],
                    successful_executions=agent["successful_executions"],
                    failed_executions=agent["failed_executions"],
                    last_execution_time=agent["last_execution_time"],
                    average_duration_ms=agent["average_duration_ms"],
                    error_rate=agent["error_rate"],
                    status=agent["status"]
                )
                for agent in summary["agents"]
            ]
        )
    except Exception as e:
        logger.error(f"Error getting agents health summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get health summary: {str(e)}")


@router.get("/agents/{agent_id}/health", response_model=AgentHealth)
async def get_agent_health(agent_id: str):
    """Get health metrics for a specific agent.
    
    Args:
        agent_id: Agent identifier
        
    Returns:
        AgentHealth with metrics and recent failures
    """
    try:
        monitor = get_health_monitor()
        
        # Get health metrics
        metrics = monitor.get_agent_health(agent_id)
        
        # Get recent failures
        failures = monitor.get_agent_failures(agent_id, limit=5)
        
        # Get agent name
        agent_name = monitor.get_agent_name(agent_id)
        
        return AgentHealth(
            agent_id=agent_id,
            name=agent_name,
            metrics=AgentHealthMetrics(
                agent_id=metrics["agent_id"],
                total_executions=metrics["total_executions"],
                successful_executions=metrics["successful_executions"],
                failed_executions=metrics["failed_executions"],
                last_execution_time=metrics["last_execution_time"],
                average_duration_ms=metrics["average_duration_ms"],
                error_rate=metrics["error_rate"],
                status=metrics["status"]
            ),
            recent_failures=failures
        )
    except Exception as e:
        logger.error(f"Error getting health for agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent health: {str(e)}")


@router.get("/agents/{agent_id}/failures", response_model=FailureList)
async def get_agent_failures(
    agent_id: str,
    limit: int = Query(default=10, le=100, description="Maximum number of failures to return")
):
    """Get recent failures for a specific agent.
    
    Args:
        agent_id: Agent identifier
        limit: Maximum number of failures to return
        
    Returns:
        FailureList with recent failure details
    """
    try:
        monitor = get_health_monitor()
        failures_data = monitor.get_agent_failures(agent_id, limit=limit)
        
        failures = [
            FailureReport(
                timestamp=f["timestamp"],
                agent_id=f["agent_id"],
                job_id=f["job_id"],
                error_type=f["error_type"],
                error_message=f["error_message"],
                input_data=f["input_data"],
                stack_trace=f["stack_trace"]
            )
            for f in failures_data
        ]
        
        return FailureList(
            agent_id=agent_id,
            failures=failures,
            total=len(failures)
        )
    except Exception as e:
        logger.error(f"Error getting failures for agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent failures: {str(e)}")


@router.post("/agents/{agent_id}/health/reset")
async def reset_agent_health(agent_id: str):
    """Reset health metrics for a specific agent.
    
    Args:
        agent_id: Agent identifier
        
    Returns:
        Success message
    """
    try:
        monitor = get_health_monitor()
        monitor.reset_agent_health(agent_id)
        
        return {
            "message": f"Health metrics reset for agent '{agent_id}'",
            "agent_id": agent_id
        }
    except Exception as e:
        logger.error(f"Error resetting health for agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset agent health: {str(e)}")


# ============================================================================
# Agent Job History
# ============================================================================

@router.get("/agents/{agent_id}/jobs")
async def get_agent_jobs(
    agent_id: str,
    limit: int = Query(default=50, le=100),
    status: Optional[str] = Query(default=None)
):
    """Get jobs that used this agent.
    
    Args:
        agent_id: Agent identifier
        limit: Maximum number of jobs to return
        status: Optional status filter (completed, failed, running)
        
    Returns:
        Job history for the agent
    """
    try:
        monitor = get_health_monitor()
        history = monitor.get_agent_job_history(agent_id, limit)
        
        # Filter by status if provided
        if status:
            history = [h for h in history if h['status'] == status]
        
        return {
            'agent_id': agent_id,
            'jobs': history,
            'total': len(history)
        }
    except Exception as e:
        logger.error(f"Error getting jobs for agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent jobs: {str(e)}")


@router.get("/agents/{agent_id}/activity")
async def get_agent_activity(
    agent_id: str,
    job_id: Optional[str] = Query(default=None)
):
    """Get agent activity, optionally filtered by job.
    
    Args:
        agent_id: Agent identifier
        job_id: Optional job ID to filter activity
        
    Returns:
        Agent activity records
    """
    try:
        monitor = get_health_monitor()
        
        if job_id:
            # Get activity for specific job
            history = monitor.get_agent_job_history(agent_id)
            activity = [h for h in history if h['job_id'] == job_id]
        else:
            # Get all activity
            activity = monitor.get_agent_job_history(agent_id)
        
        return {
            'agent_id': agent_id,
            'activity': activity,
            'total': len(activity)
        }
    except Exception as e:
        logger.error(f"Error getting activity for agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get agent activity: {str(e)}")
