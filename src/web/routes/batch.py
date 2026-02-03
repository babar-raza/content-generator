"""Batch processing API routes."""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch", tags=["batch"])


# This will be injected by the app
_executor = None
_jobs_store = None


def set_executor(executor):
    """Set the executor for dependency injection."""
    global _executor
    _executor = executor


def set_jobs_store(store):
    """Set the jobs store for dependency injection."""
    global _jobs_store
    _jobs_store = store


def get_executor():
    """Dependency to get executor (optional for batch jobs)."""
    return _executor


def get_jobs_store():
    """Dependency to get jobs store."""
    # Jobs store should always be available (at minimum an empty dict)
    if _jobs_store is None:
        logger.warning("Jobs store not initialized, using empty dict")
        return {}
    return _jobs_store


# Models
class BatchManifest(BaseModel):
    """Batch processing manifest."""
    workflow_id: str = Field(..., description="Workflow to use for all jobs")
    jobs: List[Dict[str, Any]] = Field(..., min_length=1, description="List of job inputs (min 1)")
    batch_name: Optional[str] = Field(default=None, description="Optional batch name")
    config_overrides: Optional[Dict[str, Any]] = Field(default=None, description="Config overrides")


class BatchSubmitResponse(BaseModel):
    """Response for batch submission."""
    batch_id: str
    job_ids: List[str]
    status: str
    message: str
    created_at: str


class BatchStatusResponse(BaseModel):
    """Response for batch status."""
    batch_id: str
    batch_name: Optional[str] = None
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    running_jobs: int
    queued_jobs: int
    status: str
    job_statuses: List[Dict[str, Any]]


class BatchResultsResponse(BaseModel):
    """Response for batch results."""
    batch_id: str
    results: List[Dict[str, Any]]
    total: int
    timestamp: str


@router.post("", response_model=BatchSubmitResponse, status_code=201)
async def submit_batch_job(
    manifest: BatchManifest,
    executor=Depends(get_executor),
    store=Depends(get_jobs_store)
):
    """Submit batch processing job (mirrors cmd_batch).

    Args:
        manifest: Batch job manifest with workflow and jobs

    Returns:
        BatchSubmitResponse with batch_id and job_ids

    CANONICAL ENDPOINT: POST /api/batch
    """
    try:
        # Generate batch ID
        batch_id = str(uuid.uuid4())
        job_ids = []
        
        # Create each job in the batch
        for job_input in manifest.jobs:
            job_id = str(uuid.uuid4())
            job_ids.append(job_id)
            
            # Create job entry
            job_data = {
                "job_id": job_id,
                "workflow_id": manifest.workflow_id,
                "inputs": job_input,
                "batch_id": batch_id,
                "batch_name": manifest.batch_name,
                "config_overrides": manifest.config_overrides,
                "status": "created",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            
            # Store job
            store[job_id] = job_data
            
            # Submit to executor (if available)
            if executor is not None:
                try:
                    if hasattr(executor, 'submit_job'):
                        executor.submit_job(
                            manifest.workflow_id,
                            job_input,
                            job_id
                        )
                        job_data["status"] = "queued"
                        store[job_id] = job_data
                except Exception as e:
                    logger.error(f"Failed to submit job {job_id} to executor: {e}")
                    job_data["status"] = "failed"
                    job_data["error"] = str(e)
                    store[job_id] = job_data
            else:
                # No executor in mock mode - job remains in "created" status
                job_data["status"] = "submitted"
                store[job_id] = job_data
        
        return BatchSubmitResponse(
            batch_id=batch_id,
            job_ids=job_ids,
            status="submitted",
            message=f"Batch job created with {len(job_ids)} jobs",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error submitting batch job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to submit batch job: {str(e)}")


@router.post("/jobs", response_model=BatchSubmitResponse, status_code=201)
async def submit_batch_job_legacy(
    manifest: BatchManifest,
    executor=Depends(get_executor),
    store=Depends(get_jobs_store)
):
    """Submit batch processing job (backward compatibility alias).

    This is an alias for POST /api/batch to maintain backward compatibility
    with tests and clients that POST to /api/batch/jobs.

    CANONICAL ENDPOINT: POST /api/batch
    """
    return await submit_batch_job(manifest, executor, store)


@router.get("/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str,
    store=Depends(get_jobs_store)
):
    """Get batch job status.

    Args:
        batch_id: Batch identifier

    Returns:
        BatchStatusResponse with job statuses
    """
    try:
        # Find all jobs in this batch
        batch_jobs = [
            job for job in store.values()
            if job.get("batch_id") == batch_id
        ]
        
        if not batch_jobs:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
        
        # Count by status
        total_jobs = len(batch_jobs)
        completed_jobs = sum(1 for j in batch_jobs if j.get("status") == "completed")
        failed_jobs = sum(1 for j in batch_jobs if j.get("status") == "failed")
        running_jobs = sum(1 for j in batch_jobs if j.get("status") == "running")
        queued_jobs = sum(1 for j in batch_jobs if j.get("status") in ["queued", "created"])
        
        # Determine overall batch status
        if completed_jobs == total_jobs:
            batch_status = "completed"
        elif failed_jobs == total_jobs:
            batch_status = "failed"
        elif running_jobs > 0 or queued_jobs > 0:
            batch_status = "running"
        else:
            batch_status = "partial"
        
        # Get batch name from first job
        batch_name = batch_jobs[0].get("batch_name")
        
        # Format job statuses
        job_statuses = [
            {
                "job_id": job["job_id"],
                "status": job["status"],
                "error": job.get("error"),
                "created_at": job.get("created_at").isoformat() if job.get("created_at") else None,
                "completed_at": job.get("completed_at").isoformat() if job.get("completed_at") else None,
            }
            for job in batch_jobs
        ]
        
        return BatchStatusResponse(
            batch_id=batch_id,
            batch_name=batch_name,
            total_jobs=total_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            running_jobs=running_jobs,
            queued_jobs=queued_jobs,
            status=batch_status,
            job_statuses=job_statuses
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch status {batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get batch status: {str(e)}")


@router.get("/{batch_id}/results", response_model=BatchResultsResponse)
async def get_batch_results(
    batch_id: str,
    store=Depends(get_jobs_store)
):
    """Get batch job results.
    
    Args:
        batch_id: Batch identifier
        
    Returns:
        BatchResultsResponse with all job results
    """
    try:
        # Find all jobs in this batch
        batch_jobs = [
            job for job in store.values()
            if job.get("batch_id") == batch_id
        ]
        
        if not batch_jobs:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
        
        # Collect results
        results = []
        for job in batch_jobs:
            result_entry = {
                "job_id": job["job_id"],
                "status": job["status"],
                "result": job.get("result"),
                "error": job.get("error"),
                "created_at": job.get("created_at").isoformat() if job.get("created_at") else None,
                "completed_at": job.get("completed_at").isoformat() if job.get("completed_at") else None,
            }
            results.append(result_entry)
        
        return BatchResultsResponse(
            batch_id=batch_id,
            results=results,
            total=len(results),
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch results {batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get batch results: {str(e)}")
