"""Job management API routes."""

import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..models import (
    JobCreate,
    RunSpec,
    BatchJobCreate,
    JobResponse,
    BatchJobResponse,
    JobStatus,
    JobList,
    JobControl,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["jobs"])


# This will be injected by the app
_jobs_store = None
_executor = None


def set_jobs_store(store):
    """Set the jobs store for dependency injection."""
    global _jobs_store
    _jobs_store = store


def set_executor(executor):
    """Set the executor for dependency injection."""
    global _executor
    _executor = executor


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


@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    job: JobCreate,
    store=Depends(get_jobs_store),
    executor=Depends(get_executor)
):
    """Create a new job.
    
    Args:
        job: Job creation request
        
    Returns:
        JobResponse with job_id and status
    """
    try:
        # Generate job ID
        import uuid
        job_id = str(uuid.uuid4())
        
        # Create job entry
        job_data = {
            "job_id": job_id,
            "workflow_id": job.workflow_id,
            "inputs": job.inputs,
            "status": "created",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        # Store job
        store[job_id] = job_data
        
        # Submit to executor (non-blocking)
        try:
            # Use executor to start the job
            if hasattr(executor, 'submit_job'):
                executor.submit_job(job_id, job.workflow_id, job.inputs)
                job_data["status"] = "queued"
                store[job_id] = job_data
        except Exception as e:
            logger.error(f"Failed to submit job to executor: {e}")
            job_data["status"] = "failed"
            job_data["error"] = str(e)
            store[job_id] = job_data
        
        return JobResponse(
            job_id=job_id,
            status=job_data["status"],
            message="Job created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")


@router.post("/generate", response_model=JobResponse, status_code=201)
async def generate_content(
    spec: RunSpec,
    store=Depends(get_jobs_store),
    executor=Depends(get_executor)
):
    """Generate content using RunSpec (app_unified.py endpoint).
    
    Args:
        spec: Run specification with topic, template, etc.
        
    Returns:
        JobResponse with job_id and status
    """
    try:
        # Generate job ID
        import uuid
        job_id = str(uuid.uuid4())
        
        # Convert RunSpec to job inputs
        inputs = {
            "topic": spec.topic,
            "template": spec.template,
        }
        
        if spec.metadata:
            inputs["metadata"] = spec.metadata
        
        # Determine workflow
        workflow_id = spec.workflow or "default_blog"
        
        # Create job entry
        job_data = {
            "job_id": job_id,
            "workflow_id": workflow_id,
            "inputs": inputs,
            "config_overrides": spec.config_overrides,
            "status": "created",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        # Store job
        store[job_id] = job_data
        
        # Submit to executor
        try:
            if hasattr(executor, 'submit_job'):
                executor.submit_job(job_id, workflow_id, inputs, spec.config_overrides)
                job_data["status"] = "queued"
                store[job_id] = job_data
        except Exception as e:
            logger.error(f"Failed to submit job to executor: {e}")
            job_data["status"] = "failed"
            job_data["error"] = str(e)
            store[job_id] = job_data
        
        return JobResponse(
            job_id=job_id,
            status=job_data["status"],
            message=f"Content generation job created for topic: {spec.topic}"
        )
        
    except Exception as e:
        logger.error(f"Error creating generation job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create generation job: {str(e)}")


@router.post("/batch", response_model=BatchJobResponse, status_code=201)
async def create_batch_jobs(
    batch: BatchJobCreate,
    store=Depends(get_jobs_store),
    executor=Depends(get_executor)
):
    """Create multiple jobs in a batch (app_unified.py endpoint).
    
    Args:
        batch: Batch job creation request
        
    Returns:
        BatchJobResponse with batch_id and job_ids
    """
    try:
        import uuid
        
        # Generate batch ID
        batch_id = str(uuid.uuid4())
        job_ids = []
        
        # Create each job
        for job_input in batch.jobs:
            job_id = str(uuid.uuid4())
            job_ids.append(job_id)
            
            job_data = {
                "job_id": job_id,
                "workflow_id": batch.workflow_id,
                "inputs": job_input,
                "batch_id": batch_id,
                "batch_name": batch.batch_name,
                "status": "created",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            
            store[job_id] = job_data
            
            # Submit to executor
            try:
                if hasattr(executor, 'submit_job'):
                    executor.submit_job(job_id, batch.workflow_id, job_input)
                    job_data["status"] = "queued"
                    store[job_id] = job_data
            except Exception as e:
                logger.error(f"Failed to submit job {job_id} to executor: {e}")
                job_data["status"] = "failed"
                job_data["error"] = str(e)
                store[job_id] = job_data
        
        return BatchJobResponse(
            batch_id=batch_id,
            job_ids=job_ids,
            status="created",
            message=f"Batch of {len(job_ids)} jobs created"
        )
        
    except Exception as e:
        logger.error(f"Error creating batch jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create batch jobs: {str(e)}")


@router.get("/jobs", response_model=JobList)
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    store=Depends(get_jobs_store)
):
    """List all jobs with optional filtering.
    
    Args:
        status: Filter by job status
        limit: Maximum number of jobs to return
        offset: Offset for pagination
        
    Returns:
        JobList with jobs and total count
    """
    try:
        # Get all jobs
        all_jobs = list(store.values())
        
        # Filter by status if provided
        if status:
            all_jobs = [j for j in all_jobs if j.get("status") == status]
        
        # Sort by created_at (newest first)
        all_jobs.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
        
        # Apply pagination
        total = len(all_jobs)
        jobs_page = all_jobs[offset:offset + limit]
        
        # Convert to JobStatus models
        job_statuses = []
        for job in jobs_page:
            job_statuses.append(JobStatus(
                job_id=job["job_id"],
                status=job["status"],
                progress=job.get("progress"),
                current_stage=job.get("current_stage"),
                created_at=job.get("created_at"),
                updated_at=job.get("updated_at"),
                completed_at=job.get("completed_at"),
                error=job.get("error"),
                result=job.get("result"),
                metadata=job.get("metadata"),
            ))
        
        return JobList(jobs=job_statuses, total=total)
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(
    job_id: str,
    store=Depends(get_jobs_store)
):
    """Get status of a specific job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JobStatus with complete job information
    """
    try:
        if job_id not in store:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job = store[job_id]
        
        return JobStatus(
            job_id=job["job_id"],
            status=job["status"],
            progress=job.get("progress"),
            current_stage=job.get("current_stage"),
            created_at=job.get("created_at"),
            updated_at=job.get("updated_at"),
            completed_at=job.get("completed_at"),
            error=job.get("error"),
            result=job.get("result"),
            metadata=job.get("metadata"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get job: {str(e)}")


@router.post("/jobs/{job_id}/pause", response_model=JobControl)
async def pause_job(
    job_id: str,
    store=Depends(get_jobs_store),
    executor=Depends(get_executor)
):
    """Pause a running job (app_integrated.py endpoint).
    
    Args:
        job_id: Job identifier
        
    Returns:
        JobControl with action result
    """
    try:
        if job_id not in store:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job = store[job_id]
        current_status = job["status"]
        
        # Check if job can be paused
        if current_status not in ["running", "queued"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot pause job in status: {current_status}"
            )
        
        # Pause through executor
        try:
            if hasattr(executor, 'pause_job'):
                executor.pause_job(job_id)
            
            job["status"] = "paused"
            job["updated_at"] = datetime.now(timezone.utc)
            store[job_id] = job
            
        except Exception as e:
            logger.error(f"Executor failed to pause job {job_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to pause job: {str(e)}")
        
        return JobControl(
            job_id=job_id,
            action="pause",
            status="paused",
            message="Job paused successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to pause job: {str(e)}")


@router.post("/jobs/{job_id}/resume", response_model=JobControl)
async def resume_job(
    job_id: str,
    store=Depends(get_jobs_store),
    executor=Depends(get_executor)
):
    """Resume a paused job (app_integrated.py endpoint).
    
    Args:
        job_id: Job identifier
        
    Returns:
        JobControl with action result
    """
    try:
        if job_id not in store:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job = store[job_id]
        current_status = job["status"]
        
        # Check if job can be resumed
        if current_status != "paused":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume job in status: {current_status}"
            )
        
        # Resume through executor
        try:
            if hasattr(executor, 'resume_job'):
                executor.resume_job(job_id)
            
            job["status"] = "running"
            job["updated_at"] = datetime.now(timezone.utc)
            store[job_id] = job
            
        except Exception as e:
            logger.error(f"Executor failed to resume job {job_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to resume job: {str(e)}")
        
        return JobControl(
            job_id=job_id,
            action="resume",
            status="running",
            message="Job resumed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to resume job: {str(e)}")


@router.post("/jobs/{job_id}/cancel", response_model=JobControl)
async def cancel_job(
    job_id: str,
    store=Depends(get_jobs_store),
    executor=Depends(get_executor)
):
    """Cancel a job (app_integrated.py endpoint).
    
    Args:
        job_id: Job identifier
        
    Returns:
        JobControl with action result
    """
    try:
        if job_id not in store:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job = store[job_id]
        current_status = job["status"]
        
        # Check if job can be cancelled
        if current_status in ["completed", "cancelled", "failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job in status: {current_status}"
            )
        
        # Cancel through executor
        try:
            if hasattr(executor, 'cancel_job'):
                executor.cancel_job(job_id)
            
            job["status"] = "cancelled"
            job["updated_at"] = datetime.now(timezone.utc)
            job["completed_at"] = datetime.now(timezone.utc)
            store[job_id] = job
            
        except Exception as e:
            logger.error(f"Executor failed to cancel job {job_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")
        
        return JobControl(
            job_id=job_id,
            action="cancel",
            status="cancelled",
            message="Job cancelled successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.post("/jobs/{job_id}/archive", response_model=JobControl)
async def archive_job(
    job_id: str,
    store=Depends(get_jobs_store),
    executor=Depends(get_executor)
):
    """Archive a completed, failed, or cancelled job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JobControl with action result
    """
    try:
        if job_id not in store:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job = store[job_id]
        current_status = job["status"]
        
        # Check if job can be archived
        if current_status not in ["completed", "cancelled", "failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot archive job in status: {current_status}. Only completed, cancelled, or failed jobs can be archived."
            )
        
        # Archive through executor/storage
        try:
            if hasattr(executor, 'archive_job'):
                success = executor.archive_job(job_id)
            elif hasattr(executor, 'storage') and hasattr(executor.storage, 'archive_job'):
                success = executor.storage.archive_job(job_id)
            else:
                # Fallback: just update status in store
                job["status"] = "archived"
                job["archived_at"] = datetime.now(timezone.utc)
                job["updated_at"] = datetime.now(timezone.utc)
                store[job_id] = job
                success = True
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to archive job")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to archive job {job_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to archive job: {str(e)}")
        
        return JobControl(
            job_id=job_id,
            action="archive",
            status="archived",
            message="Job archived successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to archive job: {str(e)}")


@router.post("/jobs/{job_id}/unarchive", response_model=JobControl)
async def unarchive_job(
    job_id: str,
    store=Depends(get_jobs_store),
    executor=Depends(get_executor)
):
    """Unarchive an archived job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JobControl with action result
    """
    try:
        # Try to find job in store or load from archive
        job = None
        if job_id in store:
            job = store[job_id]
        elif hasattr(executor, 'storage') and hasattr(executor.storage, 'load_job'):
            # Load from archive
            job_state = executor.storage.load_job(job_id, check_archive=True)
            if job_state:
                job = job_state.metadata.to_dict()
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        current_status = job.get("status")
        
        # Check if job is archived
        if current_status != "archived":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot unarchive job in status: {current_status}. Only archived jobs can be unarchived."
            )
        
        # Unarchive through executor/storage
        try:
            if hasattr(executor, 'unarchive_job'):
                success = executor.unarchive_job(job_id)
            elif hasattr(executor, 'storage') and hasattr(executor.storage, 'unarchive_job'):
                success = executor.storage.unarchive_job(job_id)
                
                # Reload job after unarchiving
                if success:
                    job_state = executor.storage.load_job(job_id, check_archive=False)
                    if job_state:
                        job = job_state.metadata.to_dict()
                        store[job_id] = job
            else:
                # Fallback: restore status
                if job.get("error"):
                    job["status"] = "failed"
                elif job.get("completed_at"):
                    job["status"] = "completed"
                else:
                    job["status"] = "cancelled"
                
                job["updated_at"] = datetime.now(timezone.utc)
                store[job_id] = job
                success = True
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to unarchive job")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to unarchive job {job_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to unarchive job: {str(e)}")
        
        return JobControl(
            job_id=job_id,
            action="unarchive",
            status=job.get("status", "unknown"),
            message="Job unarchived successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unarchiving job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to unarchive job: {str(e)}")


@router.post("/jobs/{job_id}/retry", response_model=JobControl)
async def retry_job(
    job_id: str,
    store=Depends(get_jobs_store),
    executor=Depends(get_executor)
):
    """Retry a failed job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JobControl with action result
    """
    try:
        if job_id not in store:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        job = store[job_id]
        current_status = job["status"]
        
        # Check if job can be retried
        if current_status != "failed":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry job in status: {current_status}. Only failed jobs can be retried."
            )
        
        retry_count = job.get("retry_count", 0)
        max_retries = job.get("max_retries", 3)
        
        if retry_count >= max_retries:
            raise HTTPException(
                status_code=400,
                detail=f"Job has exceeded maximum retries ({max_retries})"
            )
        
        # Retry through executor
        try:
            if hasattr(executor, 'retry_job'):
                executor.retry_job(job_id)
            elif hasattr(executor, 'submit_job'):
                # Re-submit the job
                workflow_id = job.get("workflow_id")
                inputs = job.get("inputs", {})
                config_overrides = job.get("config_overrides")
                executor.submit_job(job_id, workflow_id, inputs, config_overrides)
            
            job["status"] = "retrying"
            job["retry_count"] = retry_count + 1
            job["updated_at"] = datetime.now(timezone.utc)
            job["error"] = None  # Clear previous error
            store[job_id] = job
            
        except Exception as e:
            logger.error(f"Executor failed to retry job {job_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retry job: {str(e)}")
        
        return JobControl(
            job_id=job_id,
            action="retry",
            status="retrying",
            message=f"Job retry initiated (attempt {retry_count + 1}/{max_retries})"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retry job: {str(e)}")
