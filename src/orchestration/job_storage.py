"""Job Storage - Persist jobs to disk."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .job_state import JobState, JobMetadata, JobStatus

logger = logging.getLogger(__name__)


class JobStorage:
    """Manages persistent storage of job state."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize job storage.
        
        Args:
            base_dir: Base directory for job storage (default: .jobs/)
        """
        self.base_dir = base_dir or Path(".jobs")
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def get_job_dir(self, job_id: str) -> Path:
        """Get directory path for a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Path to job directory
        """
        job_dir = self.base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir
    
    def save_job(self, job_state: JobState) -> None:
        """Save job state to disk.
        
        Args:
            job_state: Job state to save
        """
        try:
            job_dir = self.get_job_dir(job_state.metadata.job_id)
            state_file = job_dir / "state.json"
            
            # Update timestamp
            job_state.metadata.updated_at = datetime.now()
            
            # Write state
            with open(state_file, 'w') as f:
                json.dump(job_state.to_dict(), f, indent=2)
            
            logger.debug(f"Saved job state: {job_state.metadata.job_id}")
            
        except Exception as e:
            logger.error(f"Failed to save job {job_state.metadata.job_id}: {e}")
            raise
    
    def load_job(self, job_id: str) -> Optional[JobState]:
        """Load job state from disk.
        
        Args:
            job_id: Job identifier
            
        Returns:
            JobState if found, None otherwise
        """
        try:
            job_dir = self.get_job_dir(job_id)
            state_file = job_dir / "state.json"
            
            if not state_file.exists():
                return None
            
            with open(state_file, 'r') as f:
                data = json.load(f)
            
            return JobState.from_dict(data)
            
        except Exception as e:
            logger.error(f"Failed to load job {job_id}: {e}")
            return None
    
    def delete_job(self, job_id: str) -> bool:
        """Delete job from storage.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            job_dir = self.get_job_dir(job_id)
            
            if not job_dir.exists():
                return False
            
            # Delete all files in job directory
            for file in job_dir.iterdir():
                file.unlink()
            
            # Delete directory
            job_dir.rmdir()
            
            logger.info(f"Deleted job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            return False
    
    def list_jobs(
        self, 
        status: Optional[JobStatus] = None,
        limit: Optional[int] = None
    ) -> List[JobMetadata]:
        """List all jobs, optionally filtered by status.
        
        Args:
            status: Optional status filter
            limit: Optional limit on number of results
            
        Returns:
            List of job metadata
        """
        jobs = []
        
        try:
            for job_dir in self.base_dir.iterdir():
                if not job_dir.is_dir():
                    continue
                
                state_file = job_dir / "state.json"
                if not state_file.exists():
                    continue
                
                try:
                    with open(state_file, 'r') as f:
                        data = json.load(f)
                    
                    metadata = JobMetadata.from_dict(data['metadata'])
                    
                    # Apply status filter
                    if status is None or metadata.status == status:
                        jobs.append(metadata)
                        
                except Exception as e:
                    logger.warning(f"Failed to load job metadata from {job_dir}: {e}")
            
            # Sort by created_at descending
            jobs.sort(key=lambda j: j.created_at, reverse=True)
            
            # Apply limit
            if limit:
                jobs = jobs[:limit]
            
            return jobs
            
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []
    
    def job_exists(self, job_id: str) -> bool:
        """Check if a job exists in storage.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if job exists, False otherwise
        """
        job_dir = self.get_job_dir(job_id)
        state_file = job_dir / "state.json"
        return state_file.exists()
    
    def save_job_output(self, job_id: str, output_name: str, content: str) -> None:
        """Save job output file.
        
        Args:
            job_id: Job identifier
            output_name: Name of output file
            content: File content
        """
        try:
            job_dir = self.get_job_dir(job_id)
            output_file = job_dir / output_name
            
            with open(output_file, 'w') as f:
                f.write(content)
            
            logger.debug(f"Saved output {output_name} for job {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to save output for job {job_id}: {e}")
    
    def load_job_output(self, job_id: str, output_name: str) -> Optional[str]:
        """Load job output file.
        
        Args:
            job_id: Job identifier
            output_name: Name of output file
            
        Returns:
            File content if found, None otherwise
        """
        try:
            job_dir = self.get_job_dir(job_id)
            output_file = job_dir / output_name
            
            if not output_file.exists():
                return None
            
            with open(output_file, 'r') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Failed to load output for job {job_id}: {e}")
            return None
    
    def get_storage_stats(self) -> Dict[str, int]:
        """Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        try:
            total_jobs = 0
            total_size = 0
            status_counts = {}
            
            for job_dir in self.base_dir.iterdir():
                if not job_dir.is_dir():
                    continue
                
                total_jobs += 1
                
                # Calculate directory size
                for file in job_dir.rglob('*'):
                    if file.is_file():
                        total_size += file.stat().st_size
                
                # Count by status
                state_file = job_dir / "state.json"
                if state_file.exists():
                    try:
                        with open(state_file, 'r') as f:
                            data = json.load(f)
                        
                        status = data['metadata']['status']
                        status_counts[status] = status_counts.get(status, 0) + 1
                    except Exception:
                        pass
            
            return {
                'total_jobs': total_jobs,
                'total_size_bytes': total_size,
                'status_counts': status_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {'total_jobs': 0, 'total_size_bytes': 0, 'status_counts': {}}
# DOCGEN:LLM-FIRST@v4