"""Debugging API routes for workflow inspection and control."""

import logging
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone

from ..models import (
    BreakpointCreateRequest,
    BreakpointResponse,
    BreakpointListResponse,
    DebugStepRequest,
    DebugStepResponse,
    DebugStateResponse,
    DebugSessionCreate,
    DebugSessionResponse,
    DebugSessionListResponse,
    StepResult,
    ExecutionTrace,
    ExecutionTraceEntry,
    ContinueRequest,
)
from ...visualization.workflow_debugger import WorkflowDebugger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/debug", tags=["debug"])

# Global debugger instance
_debugger = None


def get_debugger():
    """Get or create debugger instance."""
    global _debugger
    if _debugger is None:
        _debugger = WorkflowDebugger()
    return _debugger


# ============================================================================
# Session Management
# ============================================================================

@router.post("/sessions", response_model=DebugSessionResponse, status_code=201)
async def create_debug_session(request: DebugSessionCreate):
    """Create a new debug session for a job.
    
    Args:
        request: Session creation request with job_id
        
    Returns:
        DebugSessionResponse with session details
    """
    try:
        debugger = get_debugger()
        
        # Create debug session
        session_id = debugger.start_debug_session(request.job_id)
        session = debugger.debug_sessions[session_id]
        
        # Auto-pause if requested
        if request.auto_pause:
            session.status = 'paused'
        
        return DebugSessionResponse(
            session_id=session_id,
            job_id=request.job_id,
            status=session.status,
            started_at=session.started_at,
            breakpoint_count=len(session.breakpoints)
        )
    except Exception as e:
        logger.error(f"Error creating debug session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create debug session: {str(e)}")


@router.get("/sessions", response_model=DebugSessionListResponse)
async def list_debug_sessions(status: Optional[str] = Query(None, description="Filter by status")):
    """List all debug sessions.
    
    Args:
        status: Optional status filter
        
    Returns:
        DebugSessionListResponse with list of sessions
    """
    try:
        debugger = get_debugger()
        
        sessions = []
        for session_id, session in debugger.debug_sessions.items():
            if status and session.status != status:
                continue
            
            sessions.append(DebugSessionResponse(
                session_id=session_id,
                job_id=session.correlation_id,
                status=session.status,
                started_at=session.started_at,
                breakpoint_count=len(session.breakpoints)
            ))
        
        return DebugSessionListResponse(
            sessions=sessions,
            total=len(sessions)
        )
    except Exception as e:
        logger.error(f"Error listing debug sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list debug sessions: {str(e)}")


@router.get("/sessions/{session_id}", response_model=DebugStateResponse)
async def get_debug_session(session_id: str):
    """Get debug session state.
    
    Args:
        session_id: Debug session ID
        
    Returns:
        DebugStateResponse with session state
    """
    try:
        debugger = get_debugger()
        
        if session_id not in debugger.debug_sessions:
            raise HTTPException(status_code=404, detail=f"Debug session '{session_id}' not found")
        
        session = debugger.debug_sessions[session_id]
        
        return DebugStateResponse(
            job_id=session.correlation_id,
            session_id=session_id,
            status=session.status,
            current_step=session.current_step,
            step_history=session.step_history,
            variables=session.variables,
            breakpoints=[
                {
                    "breakpoint_id": bp.id,
                    "agent_id": bp.agent_id,
                    "event_type": bp.event_type,
                    "enabled": bp.enabled,
                    "hit_count": bp.hit_count,
                    "condition": bp.condition,
                    "max_hits": bp.max_hits
                }
                for bp in session.breakpoints
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting debug session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get debug session: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_debug_session(session_id: str):
    """End and delete a debug session.
    
    Args:
        session_id: Debug session ID
        
    Returns:
        Success message
    """
    try:
        debugger = get_debugger()
        
        if session_id not in debugger.debug_sessions:
            raise HTTPException(status_code=404, detail=f"Debug session '{session_id}' not found")
        
        # Remove all breakpoints for this session
        session = debugger.debug_sessions[session_id]
        for bp in list(session.breakpoints):
            if bp.id in debugger.active_breakpoints:
                del debugger.active_breakpoints[bp.id]
        
        # Remove session
        del debugger.debug_sessions[session_id]
        
        # Remove from step mode if active
        if session_id in debugger.step_mode_sessions:
            debugger.step_mode_sessions.remove(session_id)
        
        logger.info(f"Deleted debug session {session_id}")
        
        return {"message": f"Debug session '{session_id}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting debug session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete debug session: {str(e)}")


# ============================================================================
# Breakpoint Management (Session-scoped)
# ============================================================================

@router.post("/sessions/{session_id}/breakpoints", response_model=BreakpointResponse, status_code=201)
async def add_session_breakpoint(session_id: str, request: BreakpointCreateRequest):
    """Add a breakpoint to a debug session.
    
    Args:
        session_id: Debug session ID
        request: Breakpoint creation request
        
    Returns:
        BreakpointResponse with breakpoint details
    """
    try:
        debugger = get_debugger()
        
        if session_id not in debugger.debug_sessions:
            raise HTTPException(status_code=404, detail=f"Debug session '{session_id}' not found")
        
        # Add breakpoint to session
        breakpoint_id = debugger.add_breakpoint(
            session_id=session_id,
            agent_id=request.agent_id,
            event_type=request.event_type,
            condition=request.condition,
            max_hits=request.max_hits
        )
        
        breakpoint = debugger.active_breakpoints[breakpoint_id]
        
        return BreakpointResponse(
            breakpoint_id=breakpoint_id,
            session_id=session_id,
            agent_id=breakpoint.agent_id,
            event_type=breakpoint.event_type,
            condition=breakpoint.condition,
            enabled=breakpoint.enabled,
            hit_count=breakpoint.hit_count,
            max_hits=breakpoint.max_hits,
            created_at=datetime.now(timezone.utc)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding breakpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add breakpoint: {str(e)}")


@router.delete("/sessions/{session_id}/breakpoints/{breakpoint_id}")
async def remove_session_breakpoint(session_id: str, breakpoint_id: str):
    """Remove a breakpoint from a debug session.
    
    Args:
        session_id: Debug session ID
        breakpoint_id: Breakpoint ID
        
    Returns:
        Success message
    """
    try:
        debugger = get_debugger()
        
        if session_id not in debugger.debug_sessions:
            raise HTTPException(status_code=404, detail=f"Debug session '{session_id}' not found")
        
        # Remove breakpoint
        debugger.remove_breakpoint(session_id, breakpoint_id)
        
        return {"message": f"Breakpoint '{breakpoint_id}' removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing breakpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to remove breakpoint: {str(e)}")


# ============================================================================
# Step Control
# ============================================================================

@router.post("/sessions/{session_id}/step", response_model=StepResult)
async def step_debug_session(session_id: str):
    """Step to next breakpoint in debug session.
    
    Args:
        session_id: Debug session ID
        
    Returns:
        StepResult with step execution details
    """
    try:
        debugger = get_debugger()
        
        if session_id not in debugger.debug_sessions:
            raise HTTPException(status_code=404, detail=f"Debug session '{session_id}' not found")
        
        session = debugger.debug_sessions[session_id]
        
        # Enable step mode
        debugger.enable_step_mode(session_id)
        
        # Record step start time
        start_time = time.time()
        
        # Update session status
        session.status = 'stepping'
        
        # In a real implementation, this would trigger workflow execution
        # For now, we simulate stepping through
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Check if we hit a breakpoint
        breakpoint_hit = None
        if session.breakpoints:
            # Simulate hitting first enabled breakpoint
            for bp in session.breakpoints:
                if bp.enabled:
                    breakpoint_hit = bp.id
                    bp.hit_count += 1
                    session.status = 'paused'
                    break
        
        if not breakpoint_hit:
            session.status = 'completed'
        
        return StepResult(
            session_id=session_id,
            status=session.status,
            current_agent=session.current_step,
            next_agent=None,
            execution_time_ms=execution_time_ms,
            breakpoint_hit=breakpoint_hit
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stepping debug session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to step debug session: {str(e)}")


@router.post("/sessions/{session_id}/continue", response_model=StepResult)
async def continue_debug_session(session_id: str, request: ContinueRequest = ContinueRequest()):
    """Continue execution (optionally removing all breakpoints).
    
    Args:
        session_id: Debug session ID
        request: Continue request options
        
    Returns:
        StepResult with execution details
    """
    try:
        debugger = get_debugger()
        
        if session_id not in debugger.debug_sessions:
            raise HTTPException(status_code=404, detail=f"Debug session '{session_id}' not found")
        
        session = debugger.debug_sessions[session_id]
        
        # Remove breakpoints if requested
        if request.remove_breakpoints:
            for bp in list(session.breakpoints):
                if bp.id in debugger.active_breakpoints:
                    del debugger.active_breakpoints[bp.id]
            session.breakpoints.clear()
        
        # Disable step mode
        if session_id in debugger.step_mode_sessions:
            debugger.step_mode_sessions.remove(session_id)
        
        # Update status
        start_time = time.time()
        session.status = 'running'
        
        # Simulate completion
        execution_time_ms = (time.time() - start_time) * 1000
        session.status = 'completed'
        
        return StepResult(
            session_id=session_id,
            status=session.status,
            execution_time_ms=execution_time_ms
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error continuing debug session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to continue debug session: {str(e)}")


@router.get("/sessions/{session_id}/trace", response_model=ExecutionTrace)
async def get_execution_trace(session_id: str):
    """Get execution trace for a debug session.
    
    Args:
        session_id: Debug session ID
        
    Returns:
        ExecutionTrace with complete execution history
    """
    try:
        debugger = get_debugger()
        
        if session_id not in debugger.debug_sessions:
            raise HTTPException(status_code=404, detail=f"Debug session '{session_id}' not found")
        
        session = debugger.debug_sessions[session_id]
        
        # Build trace from step history
        entries = []
        for step in session.step_history:
            entries.append(ExecutionTraceEntry(
                timestamp=step.get('timestamp', datetime.now(timezone.utc).isoformat()),
                agent_id=step.get('agent_id', 'unknown'),
                event_type=step.get('event_type', 'unknown'),
                input_data=step.get('input_data'),
                output_data=step.get('output_data'),
                duration_ms=step.get('duration_ms'),
                error=step.get('error')
            ))
        
        start_time = None
        end_time = None
        if entries:
            start_time = entries[0].timestamp
            end_time = entries[-1].timestamp
        
        return ExecutionTrace(
            session_id=session_id,
            job_id=session.correlation_id,
            entries=entries,
            total_entries=len(entries),
            start_time=start_time,
            end_time=end_time
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get execution trace: {str(e)}")


# ============================================================================
# Legacy Breakpoint Management (kept for backwards compatibility)
# ============================================================================

@router.post("/breakpoints", response_model=BreakpointResponse, status_code=201)
async def create_breakpoint(request: BreakpointCreateRequest):
    """Set a debugging breakpoint.
    
    Args:
        request: Breakpoint creation request
        
    Returns:
        BreakpointResponse with breakpoint ID and details
    """
    try:
        debugger = get_debugger()
        
        # Create debug session if needed
        session_id = request.session_id
        if session_id not in debugger.debug_sessions:
            session_id = debugger.start_debug_session(
                request.correlation_id or f"session_{int(datetime.now().timestamp())}"
            )
        
        # Add breakpoint
        breakpoint_id = debugger.add_breakpoint(
            session_id=session_id,
            agent_id=request.agent_id,
            event_type=request.event_type,
            condition=request.condition,
            max_hits=request.max_hits
        )
        
        breakpoint = debugger.active_breakpoints[breakpoint_id]
        
        return BreakpointResponse(
            breakpoint_id=breakpoint_id,
            session_id=session_id,
            agent_id=breakpoint.agent_id,
            event_type=breakpoint.event_type,
            condition=breakpoint.condition,
            enabled=breakpoint.enabled,
            hit_count=breakpoint.hit_count,
            max_hits=breakpoint.max_hits,
            created_at=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Error creating breakpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create breakpoint: {str(e)}")


@router.delete("/breakpoints/{breakpoint_id}")
async def delete_breakpoint(breakpoint_id: str, session_id: Optional[str] = None):
    """Remove a debugging breakpoint.
    
    Args:
        breakpoint_id: Breakpoint identifier
        session_id: Optional session ID (if not provided, searches all sessions)
        
    Returns:
        Success message
    """
    try:
        debugger = get_debugger()
        
        # Find the session containing this breakpoint
        target_session_id = session_id
        if not target_session_id:
            for sid, session in debugger.debug_sessions.items():
                if any(bp.id == breakpoint_id for bp in session.breakpoints):
                    target_session_id = sid
                    break
        
        if not target_session_id:
            raise HTTPException(status_code=404, detail=f"Breakpoint '{breakpoint_id}' not found")
        
        if target_session_id not in debugger.debug_sessions:
            raise HTTPException(status_code=404, detail=f"Debug session '{target_session_id}' not found")
        
        # Remove breakpoint
        debugger.remove_breakpoint(target_session_id, breakpoint_id)
        
        return {"message": f"Breakpoint '{breakpoint_id}' removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting breakpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete breakpoint: {str(e)}")


@router.get("/breakpoints", response_model=BreakpointListResponse)
async def list_breakpoints(session_id: Optional[str] = None, enabled_only: bool = False):
    """List active breakpoints.
    
    Args:
        session_id: Optional session ID to filter by
        enabled_only: If True, only return enabled breakpoints
        
    Returns:
        BreakpointListResponse with list of breakpoints
    """
    try:
        debugger = get_debugger()
        
        breakpoints = []
        
        if session_id:
            # Get breakpoints for specific session
            if session_id not in debugger.debug_sessions:
                raise HTTPException(status_code=404, detail=f"Debug session '{session_id}' not found")
            
            session = debugger.debug_sessions[session_id]
            for bp in session.breakpoints:
                if enabled_only and not bp.enabled:
                    continue
                breakpoints.append({
                    "breakpoint_id": bp.id,
                    "session_id": session_id,
                    "agent_id": bp.agent_id,
                    "event_type": bp.event_type,
                    "condition": bp.condition,
                    "enabled": bp.enabled,
                    "hit_count": bp.hit_count,
                    "max_hits": bp.max_hits
                })
        else:
            # Get all breakpoints across all sessions
            for sid, session in debugger.debug_sessions.items():
                for bp in session.breakpoints:
                    if enabled_only and not bp.enabled:
                        continue
                    breakpoints.append({
                        "breakpoint_id": bp.id,
                        "session_id": sid,
                        "agent_id": bp.agent_id,
                        "event_type": bp.event_type,
                        "condition": bp.condition,
                        "enabled": bp.enabled,
                        "hit_count": bp.hit_count,
                        "max_hits": bp.max_hits
                    })
        
        # Sort by breakpoint_id for deterministic output
        breakpoints.sort(key=lambda x: x['breakpoint_id'])
        
        return BreakpointListResponse(
            breakpoints=breakpoints,
            total=len(breakpoints)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing breakpoints: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list breakpoints: {str(e)}")


# ============================================================================
# Step-through Debugging
# ============================================================================

@router.post("/step", response_model=DebugStepResponse)
async def debug_step(request: DebugStepRequest):
    """Step through workflow execution.
    
    Args:
        request: Debug step request
        
    Returns:
        DebugStepResponse with step result
    """
    try:
        debugger = get_debugger()
        
        if request.session_id not in debugger.debug_sessions:
            raise HTTPException(status_code=404, detail=f"Debug session '{request.session_id}' not found")
        
        # Enable step mode for this session
        debugger.enable_step_mode(request.session_id)
        
        session = debugger.debug_sessions[request.session_id]
        
        return DebugStepResponse(
            session_id=request.session_id,
            status="stepping",
            current_step=session.current_step,
            message=f"Step mode enabled for session '{request.session_id}'"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in debug step: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute debug step: {str(e)}")


@router.get("/state/{job_id}", response_model=DebugStateResponse)
async def get_debug_state(job_id: str):
    """Get current debug state for a job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        DebugStateResponse with current debug state
    """
    try:
        debugger = get_debugger()
        
        # Find session for this job
        session = None
        session_id = None
        for sid, sess in debugger.debug_sessions.items():
            if sess.correlation_id == job_id:
                session = sess
                session_id = sid
                break
        
        if not session:
            raise HTTPException(status_code=404, detail=f"No debug session found for job '{job_id}'")
        
        return DebugStateResponse(
            job_id=job_id,
            session_id=session_id,
            status=session.status,
            current_step=session.current_step,
            step_history=session.step_history,
            variables=session.variables,
            breakpoints=[
                {
                    "breakpoint_id": bp.id,
                    "agent_id": bp.agent_id,
                    "event_type": bp.event_type,
                    "enabled": bp.enabled,
                    "hit_count": bp.hit_count
                }
                for bp in session.breakpoints
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting debug state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get debug state: {str(e)}")


# ============================================================================
# NEW: System Diagnostics (Task Card 04)
# ============================================================================

@router.get("/system")
async def get_system_diagnostics():
    """Get comprehensive system diagnostics.
    
    Returns:
        System diagnostic data
    """
    try:
        from fastapi.responses import JSONResponse
        import psutil
        
        debugger = get_debugger()
        
        # Collect diagnostics
        diagnostics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents": _get_agent_diagnostics(),
            "workflows": _get_workflow_diagnostics(),
            "jobs": _get_job_diagnostics(debugger),
            "resources": _get_resource_usage(),
            "config": _get_config_status()
        }
        
        return JSONResponse(content=diagnostics)
    except Exception as e:
        logger.error(f"Error getting system diagnostics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get system diagnostics: {str(e)}")


@router.get("/agent/{agent_id}")
async def debug_agent(agent_id: str):
    """Get detailed agent debug info.
    
    Args:
        agent_id: Agent identifier
        
    Returns:
        Agent debug information
    """
    try:
        from fastapi.responses import JSONResponse
        
        # Try to get agent health monitor
        try:
            from src.orchestration.agent_health_monitor import AgentHealthMonitor
            monitor = AgentHealthMonitor()
            
            if hasattr(monitor, 'get_full_diagnostics'):
                diagnostics = monitor.get_full_diagnostics(agent_id)
            else:
                diagnostics = {
                    "agent_id": agent_id,
                    "status": "unknown",
                    "message": "Health monitor diagnostics not available"
                }
        except ImportError:
            diagnostics = {
                "agent_id": agent_id,
                "status": "unknown",
                "message": "Agent health monitor not available"
            }
        
        return JSONResponse(content=diagnostics)
    except Exception as e:
        logger.error(f"Error debugging agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to debug agent: {str(e)}")


@router.get("/job/{job_id}")
async def debug_job(job_id: str):
    """Get detailed job debug info.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Job debug information
    """
    try:
        from fastapi.responses import JSONResponse
        
        debugger = get_debugger()
        
        # Get full debug trace if available
        if hasattr(debugger, 'get_full_debug_trace'):
            debug_data = debugger.get_full_debug_trace(job_id)
        else:
            # Find debug session for this job
            debug_data = {
                "job_id": job_id,
                "sessions": []
            }
            
            for session_id, session in debugger.debug_sessions.items():
                if session.correlation_id == job_id:
                    debug_data["sessions"].append({
                        "session_id": session_id,
                        "status": session.status,
                        "current_step": session.current_step,
                        "breakpoint_count": len(session.breakpoints),
                        "step_history": session.step_history
                    })
        
        return JSONResponse(content=debug_data)
    except Exception as e:
        logger.error(f"Error debugging job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to debug job: {str(e)}")


@router.get("/performance")
async def get_performance_profile():
    """Get system performance profile.
    
    Returns:
        Performance profile data
    """
    try:
        from fastapi.responses import JSONResponse
        
        # Try to get monitor
        try:
            from src.orchestration.monitor import Monitor
            monitor = Monitor()
            
            if hasattr(monitor, 'get_performance_profile'):
                profile = monitor.get_performance_profile()
            else:
                # Build basic profile
                profile = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cpu": _get_cpu_profile(),
                    "memory": _get_memory_profile(),
                    "agents": _get_agent_performance(),
                    "jobs": _get_job_performance()
                }
        except ImportError:
            profile = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Monitor not available for performance profiling"
            }
        
        return JSONResponse(content=profile)
    except Exception as e:
        logger.error(f"Error getting performance profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get performance profile: {str(e)}")


# Helper functions for diagnostics

def _get_agent_diagnostics():
    """Get agent diagnostics."""
    try:
        from src.visualization.monitor import get_monitor
        monitor = get_monitor()
        agents = monitor.get_agent_states()
        
        return {
            "total": len(agents),
            "by_status": _count_by_status(agents),
            "agents": agents[:10]  # Limit to 10 for overview
        }
    except Exception as e:
        logger.warning(f"Could not get agent diagnostics: {e}")
        return {"total": 0, "error": str(e)}


def _get_workflow_diagnostics():
    """Get workflow diagnostics."""
    try:
        from src.visualization.workflow_visualizer import WorkflowVisualizer
        visualizer = WorkflowVisualizer()
        profiles = visualizer.workflows.get('profiles', {})
        
        return {
            "total": len(profiles),
            "workflows": list(profiles.keys())
        }
    except Exception as e:
        logger.warning(f"Could not get workflow diagnostics: {e}")
        return {"total": 0, "error": str(e)}


def _get_job_diagnostics(debugger):
    """Get job diagnostics."""
    return {
        "total_sessions": len(debugger.debug_sessions),
        "active_sessions": len([s for s in debugger.debug_sessions.values() if s.status == 'active']),
        "paused_sessions": len([s for s in debugger.debug_sessions.values() if s.status == 'paused'])
    }


def _get_resource_usage():
    """Get resource usage."""
    try:
        import psutil
        
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu,
            "memory_percent": memory.percent,
            "memory_used_mb": memory.used / (1024 * 1024),
            "memory_total_mb": memory.total / (1024 * 1024),
            "disk_percent": disk.percent,
            "disk_used_gb": disk.used / (1024 * 1024 * 1024),
            "disk_total_gb": disk.total / (1024 * 1024 * 1024)
        }
    except ImportError:
        return {"error": "psutil not available"}


def _get_config_status():
    """Get configuration status."""
    from pathlib import Path
    
    config_path = Path("./config/orchestration.yaml")
    
    return {
        "config_exists": config_path.exists(),
        "config_path": str(config_path),
        "config_readable": config_path.exists() and config_path.is_file()
    }


def _count_by_status(items):
    """Count items by status field."""
    counts = {}
    for item in items:
        status = item.get('status', 'unknown')
        counts[status] = counts.get(status, 0) + 1
    return counts


def _get_cpu_profile():
    """Get CPU profile."""
    try:
        import psutil
        return {
            "percent": psutil.cpu_percent(interval=0.1),
            "count": psutil.cpu_count(),
            "count_logical": psutil.cpu_count(logical=True)
        }
    except ImportError:
        return {"error": "psutil not available"}


def _get_memory_profile():
    """Get memory profile."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "percent": mem.percent,
            "used_mb": mem.used / (1024 * 1024),
            "available_mb": mem.available / (1024 * 1024),
            "total_mb": mem.total / (1024 * 1024)
        }
    except ImportError:
        return {"error": "psutil not available"}


def _get_agent_performance():
    """Get agent performance metrics."""
    try:
        from src.visualization.monitor import VisualOrchestrationMonitor
        monitor = VisualOrchestrationMonitor()
        
        perf = []
        for agent_id, metrics in getattr(monitor, 'agent_metrics', {}).items():
            if hasattr(metrics, 'to_dict'):
                perf.append(metrics.to_dict())
        
        return perf[:10]  # Limit to top 10
    except Exception as e:
        return {"error": str(e)}


def _get_job_performance():
    """Get job performance metrics."""
    try:
        from src.visualization.monitor import VisualOrchestrationMonitor
        monitor = VisualOrchestrationMonitor()
        
        jobs = []
        for job_id, job_data in getattr(monitor, 'active_jobs', {}).items():
            jobs.append({
                "job_id": job_id,
                "status": job_data.get('status', 'unknown'),
                "duration": job_data.get('duration_seconds', 0)
            })
        
        return jobs[:10]  # Limit to top 10
    except Exception as e:
        return {"error": str(e)}
