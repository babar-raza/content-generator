"""Checkpoint Management API routes."""

import logging
import os
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import Response
from datetime import datetime

from ..models import (
    CheckpointList, CheckpointResponse, RestoreRequest,
    RestoreResponse, CleanupRequest, CleanupResponse, CheckpointMetadata
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/checkpoints", tags=["checkpoints"])

# Checkpoint manager instance (injected by app)
_checkpoint_manager = None
_executor = None


def set_checkpoint_manager(manager):
    """Set checkpoint manager for dependency injection."""
    global _checkpoint_manager
    _checkpoint_manager = manager


def set_executor(executor):
    """Set executor for job resumption."""
    global _executor
    _executor = executor


def get_checkpoint_manager():
    """Dependency to get checkpoint manager."""
    if _checkpoint_manager is None:
        try:
            from src.orchestration.checkpoint_manager import CheckpointManager
            checkpoint_dir = Path(os.getenv('CHECKPOINT_DIR', '.checkpoints'))
            manager = CheckpointManager(storage_path=checkpoint_dir)
            return manager
        except Exception as e:
            logger.error(f"Failed to initialize checkpoint manager: {e}")
            raise HTTPException(status_code=503, detail="Checkpoint manager not initialized")
    return _checkpoint_manager


def get_executor():
    """Dependency to get executor (optional for resume)."""
    return _executor


@router.get("", response_model=CheckpointList)
async def list_checkpoints(
    job_id: str = Query(..., description="Job ID to list checkpoints for (required)"),
    manager=Depends(get_checkpoint_manager)
):
    """List all checkpoints for a job.

    Args:
        job_id: Job identifier to list checkpoints for.

    Returns:
        CheckpointList with all checkpoints for the job
    """
    try:

        checkpoints_data = manager.list(job_id)

        # Convert to API models
        checkpoint_models = []
        for cp in checkpoints_data:
            checkpoint_models.append(CheckpointMetadata(
                checkpoint_id=cp.checkpoint_id,
                job_id=cp.job_id,
                step_name=cp.step_name,
                timestamp=cp.timestamp,
                workflow_version=cp.workflow_version,
                workflow_name=None,
                metadata=None
            ))

        return CheckpointList(
            job_id=job_id,
            checkpoints=checkpoint_models,
            total=len(checkpoint_models),
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing checkpoints for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list checkpoints: {str(e)}")


@router.get("/{checkpoint_id}", response_model=CheckpointResponse)
async def get_checkpoint(
    checkpoint_id: str,
    manager=Depends(get_checkpoint_manager)
):
    """Get details of a specific checkpoint.
    
    Args:
        checkpoint_id: Checkpoint identifier
        
    Returns:
        CheckpointResponse with full checkpoint metadata
    """
    try:
        # Parse checkpoint_id to extract job_id
        # Format is typically: step_name_timestamp
        # We need to search through jobs to find this checkpoint
        
        # Try to load checkpoint data from all job directories
        checkpoint_dir = manager.storage_path
        checkpoint_data = None
        job_id_found = None
        
        for job_dir in checkpoint_dir.iterdir():
            if job_dir.is_dir():
                checkpoint_file = job_dir / f"{checkpoint_id}.json"
                if checkpoint_file.exists():
                    import json
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        checkpoint_data = json.load(f)
                    job_id_found = job_dir.name
                    break
        
        if not checkpoint_data:
            raise HTTPException(status_code=404, detail=f"Checkpoint {checkpoint_id} not found")
        
        return CheckpointResponse(
            checkpoint_id=checkpoint_data.get("checkpoint_id", checkpoint_id),
            job_id=checkpoint_data.get("job_id", job_id_found),
            step_name=checkpoint_data.get("step_name", "unknown"),
            timestamp=checkpoint_data.get("timestamp", ""),
            workflow_version=checkpoint_data.get("workflow_version", "1.0"),
            workflow_name=checkpoint_data.get("workflow_name"),
            state_snapshot=checkpoint_data.get("state"),
            metadata=checkpoint_data.get("metadata")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting checkpoint {checkpoint_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get checkpoint: {str(e)}")


@router.post("/{checkpoint_id}/restore", response_model=RestoreResponse)
async def restore_checkpoint(
    checkpoint_id: str,
    request: RestoreRequest = RestoreRequest(),
    manager=Depends(get_checkpoint_manager),
    executor=Depends(get_executor)
):
    """Restore job from checkpoint.
    
    Args:
        checkpoint_id: Checkpoint identifier to restore
        request: Restore request with resume option
        
    Returns:
        RestoreResponse with restored state and job status
    """
    try:
        # Find the job_id for this checkpoint
        checkpoint_dir = manager.storage_path
        job_id_found = None
        
        for job_dir in checkpoint_dir.iterdir():
            if job_dir.is_dir():
                checkpoint_file = job_dir / f"{checkpoint_id}.json"
                if checkpoint_file.exists():
                    job_id_found = job_dir.name
                    break
        
        if not job_id_found:
            raise HTTPException(status_code=404, detail=f"Checkpoint {checkpoint_id} not found")
        
        # Restore the state
        try:
            state = manager.restore(job_id_found, checkpoint_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Checkpoint {checkpoint_id} not found")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        job_status = "restored"
        message = f"Checkpoint restored successfully"
        
        # If resume is requested, try to resume the job
        if request.resume:
            if executor and hasattr(executor, 'resume_job'):
                try:
                    executor.resume_job(job_id_found)
                    job_status = "resumed"
                    message = f"Checkpoint restored and job resumed successfully"
                except Exception as e:
                    logger.warning(f"Failed to resume job after restore: {e}")
                    job_status = "restored"
                    message = f"Checkpoint restored but failed to resume: {str(e)}"
            else:
                job_status = "restored"
                message = "Checkpoint restored (resume not supported by executor)"
        
        return RestoreResponse(
            checkpoint_id=checkpoint_id,
            job_id=job_id_found,
            state=state,
            job_status=job_status,
            message=message,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring checkpoint {checkpoint_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to restore checkpoint: {str(e)}")


@router.delete("/{checkpoint_id}", status_code=204)
async def delete_checkpoint(
    checkpoint_id: str,
    manager=Depends(get_checkpoint_manager)
):
    """Delete a specific checkpoint.
    
    Args:
        checkpoint_id: Checkpoint identifier to delete
        
    Returns:
        204 No Content on success
    """
    try:
        # Find the job_id for this checkpoint
        checkpoint_dir = manager.storage_path
        job_id_found = None
        
        for job_dir in checkpoint_dir.iterdir():
            if job_dir.is_dir():
                checkpoint_file = job_dir / f"{checkpoint_id}.json"
                if checkpoint_file.exists():
                    job_id_found = job_dir.name
                    break
        
        if not job_id_found:
            raise HTTPException(status_code=404, detail=f"Checkpoint {checkpoint_id} not found")
        
        # Delete the checkpoint
        manager.delete(job_id_found, checkpoint_id)
        
        return Response(status_code=204)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting checkpoint {checkpoint_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete checkpoint: {str(e)}")


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_checkpoints(
    request: CleanupRequest,
    manager=Depends(get_checkpoint_manager)
):
    """Cleanup old checkpoints for a job.
    
    Args:
        request: Cleanup request with job_id and keep_last count
        
    Returns:
        CleanupResponse with deleted and kept counts
    """
    try:
        if not request.job_id:
            raise HTTPException(status_code=400, detail="Missing required parameter: job_id")
        
        if request.keep_last < 1 or request.keep_last > 100:
            raise HTTPException(status_code=400, detail="keep_last must be between 1 and 100")
        
        # Get current checkpoint count
        checkpoints_before = manager.list(request.job_id)
        total_before = len(checkpoints_before)
        
        # Perform cleanup
        try:
            manager.cleanup(request.job_id, request.keep_last)
        except Exception as e:
            logger.error(f"Cleanup operation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Cleanup operation failed: {str(e)}")
        
        # Get checkpoint count after cleanup
        checkpoints_after = manager.list(request.job_id)
        total_after = len(checkpoints_after)
        
        deleted_count = total_before - total_after
        kept_count = total_after
        
        return CleanupResponse(
            job_id=request.job_id,
            deleted_count=deleted_count,
            kept_count=kept_count,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up checkpoints for job {request.job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cleanup checkpoints: {str(e)}")
