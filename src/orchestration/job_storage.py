"""Job Storage - Persist jobs to disk."""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from .job_state import JobState, JobMetadata, JobStatus

logger = logging.getLogger(__name__)


class JobStorage:
    """Manages persistent storage of job state."""
    
    def __init__(self, base_dir: Optional[Path] = None, archive_dir: Optional[Path] = None):
        """Initialize job storage.
        
        Args:
            base_dir: Base directory for job storage (default: .jobs/)
            archive_dir: Directory for archived jobs (default: .jobs/archive/)
        """
        self.base_dir = base_dir or Path(".jobs")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.archive_dir = archive_dir or (self.base_dir / "archive")
        self.archive_dir.mkdir(parents=True, exist_ok=True)
    
    def get_job_dir(self, job_id: str, archived: bool = False) -> Path:
        """Get directory path for a specific job.
        
        Args:
            job_id: Job identifier
            archived: Whether to get archived job directory
            
        Returns:
            Path to job directory
        """
        base = self.archive_dir if archived else self.base_dir
        job_dir = base / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir
    
    def save_job(self, job_state: JobState) -> None:
        """Save job state to disk.
        
        Args:
            job_state: Job state to save
        """
        try:
            archived = job_state.metadata.status == JobStatus.ARCHIVED
            job_dir = self.get_job_dir(job_state.metadata.job_id, archived=archived)
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
    
    def load_job(self, job_id: str, check_archive: bool = True) -> Optional[JobState]:
        """Load job state from disk.
        
        Args:
            job_id: Job identifier
            check_archive: Whether to check archive if not found in main storage
            
        Returns:
            JobState if found, None otherwise
        """
        try:
            # Try main storage first
            job_dir = self.get_job_dir(job_id)
            state_file = job_dir / "state.json"
            
            if state_file.exists():
                with open(state_file, 'r') as f:
                    data = json.load(f)
                return JobState.from_dict(data)
            
            # Check archive if requested
            if check_archive:
                job_dir = self.get_job_dir(job_id, archived=True)
                state_file = job_dir / "state.json"
                
                if state_file.exists():
                    with open(state_file, 'r') as f:
                        data = json.load(f)
                    return JobState.from_dict(data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load job {job_id}: {e}")
            return None
    
    def delete_job(self, job_id: str, check_archive: bool = True) -> bool:
        """Delete job from storage.
        
        Args:
            job_id: Job identifier
            check_archive: Whether to check archive if not found in main storage
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            # Try main storage first
            job_dir = self.get_job_dir(job_id)
            
            if job_dir.exists() and (job_dir / "state.json").exists():
                shutil.rmtree(job_dir)
                logger.info(f"Deleted job: {job_id}")
                return True
            
            # Check archive if requested
            if check_archive:
                job_dir = self.get_job_dir(job_id, archived=True)
                
                if job_dir.exists() and (job_dir / "state.json").exists():
                    shutil.rmtree(job_dir)
                    logger.info(f"Deleted archived job: {job_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            return False
    
    def archive_job(self, job_id: str) -> bool:
        """Archive a job by moving it to archive directory.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if archived successfully, False otherwise
        """
        try:
            # Load job from main storage
            job_state = self.load_job(job_id, check_archive=False)
            if not job_state:
                logger.warning(f"Job {job_id} not found for archiving")
                return False
            
            # Update status and timestamp
            job_state.metadata.status = JobStatus.ARCHIVED
            job_state.metadata.archived_at = datetime.now()
            job_state.metadata.updated_at = datetime.now()
            
            # Save to archive
            self.save_job(job_state)
            
            # Delete from main storage
            main_job_dir = self.base_dir / job_id
            if main_job_dir.exists():
                shutil.rmtree(main_job_dir)
            
            logger.info(f"Archived job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to archive job {job_id}: {e}")
            return False
    
    def unarchive_job(self, job_id: str) -> bool:
        """Unarchive a job by moving it back to main storage.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if unarchived successfully, False otherwise
        """
        try:
            # Load job from archive
            job_state = self.load_job(job_id, check_archive=True)
            if not job_state or job_state.metadata.status != JobStatus.ARCHIVED:
                logger.warning(f"Archived job {job_id} not found")
                return False
            
            # Restore original status (completed/failed/cancelled)
            if job_state.metadata.error_message:
                job_state.metadata.status = JobStatus.FAILED
            elif job_state.metadata.completed_at:
                job_state.metadata.status = JobStatus.COMPLETED
            else:
                job_state.metadata.status = JobStatus.CANCELLED
            
            job_state.metadata.updated_at = datetime.now()
            
            # Move from archive to main storage
            archive_job_dir = self.archive_dir / job_id
            main_job_dir = self.base_dir / job_id
            
            if archive_job_dir.exists():
                shutil.move(str(archive_job_dir), str(main_job_dir))
            
            # Save updated state
            self.save_job(job_state)
            
            logger.info(f"Unarchived job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unarchive job {job_id}: {e}")
            return False
    
    def list_jobs(
        self, 
        status: Optional[JobStatus] = None,
        limit: Optional[int] = None,
        include_archived: bool = False
    ) -> List[JobMetadata]:
        """List all jobs, optionally filtered by status.
        
        Args:
            status: Optional status filter
            limit: Optional limit on number of results
            include_archived: Whether to include archived jobs
            
        Returns:
            List of job metadata
        """
        jobs = []
        
        try:
            # Get jobs from main storage
            for job_dir in self.base_dir.iterdir():
                if not job_dir.is_dir() or job_dir.name == "archive":
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
            
            # Get archived jobs if requested
            if include_archived:
                for job_dir in self.archive_dir.iterdir():
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
                        logger.warning(f"Failed to load archived job metadata from {job_dir}: {e}")
            
            # Sort by created_at descending
            jobs.sort(key=lambda j: j.created_at, reverse=True)
            
            # Apply limit
            if limit:
                jobs = jobs[:limit]
            
            return jobs
            
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []
    
    def cleanup_old_archives(self, days: int = 30) -> int:
        """Delete archived jobs older than specified days.
        
        Args:
            days: Number of days to keep archived jobs
            
        Returns:
            Number of jobs deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            for job_dir in self.archive_dir.iterdir():
                if not job_dir.is_dir():
                    continue
                
                state_file = job_dir / "state.json"
                if not state_file.exists():
                    continue
                
                try:
                    with open(state_file, 'r') as f:
                        data = json.load(f)
                    
                    archived_at_str = data['metadata'].get('archived_at')
                    if archived_at_str:
                        archived_at = datetime.fromisoformat(archived_at_str)
                        
                        if archived_at < cutoff_date:
                            shutil.rmtree(job_dir)
                            deleted_count += 1
                            logger.info(f"Deleted old archived job: {job_dir.name}")
                            
                except Exception as e:
                    logger.warning(f"Failed to process archived job {job_dir}: {e}")
            
            logger.info(f"Cleaned up {deleted_count} old archived jobs")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old archives: {e}")
            return 0
    
    def job_exists(self, job_id: str, check_archive: bool = True) -> bool:
        """Check if a job exists in storage.
        
        Args:
            job_id: Job identifier
            check_archive: Whether to check archive
            
        Returns:
            True if job exists, False otherwise
        """
        job_dir = self.get_job_dir(job_id)
        state_file = job_dir / "state.json"
        
        if state_file.exists():
            return True
        
        if check_archive:
            job_dir = self.get_job_dir(job_id, archived=True)
            state_file = job_dir / "state.json"
            return state_file.exists()
        
        return False
    
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
            total_archived = 0
            total_size = 0
            archived_size = 0
            status_counts = {}
            
            # Count main storage
            for job_dir in self.base_dir.iterdir():
                if not job_dir.is_dir() or job_dir.name == "archive":
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
            
            # Count archived storage
            for job_dir in self.archive_dir.iterdir():
                if not job_dir.is_dir():
                    continue
                
                total_archived += 1
                
                # Calculate directory size
                for file in job_dir.rglob('*'):
                    if file.is_file():
                        archived_size += file.stat().st_size
                
                status_counts['archived'] = status_counts.get('archived', 0) + 1
            
            return {
                'total_jobs': total_jobs,
                'total_archived': total_archived,
                'total_size_bytes': total_size,
                'archived_size_bytes': archived_size,
                'status_counts': status_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {
                'total_jobs': 0,
                'total_archived': 0,
                'total_size_bytes': 0,
                'archived_size_bytes': 0,
                'status_counts': {}
            }
# DOCGEN:LLM-FIRST@v4
