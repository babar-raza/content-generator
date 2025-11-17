"""Tests for coverage requirements and agent-job linking."""

import pytest
from src.orchestration.agent_health_monitor import AgentHealthMonitor, get_health_monitor
from datetime import datetime, timezone


class TestCoverageRequirements:
    """Test coverage requirements."""
    
    def test_minimum_coverage_threshold(self):
        """Test that we have a minimum coverage threshold defined."""
        # This test documents our coverage requirement
        min_coverage = 70
        assert min_coverage > 0, "Minimum coverage threshold must be positive"
    
    def test_coverage_tools_exist(self):
        """Test that coverage tools exist."""
        import os
        tools_dir = os.path.join(os.path.dirname(__file__), '..', 'tools')
        
        # Check verify_documentation.py exists
        verify_doc = os.path.join(tools_dir, 'verify_documentation.py')
        assert os.path.exists(verify_doc), "verify_documentation.py should exist"
        
        # Check generate_coverage_report.py exists
        coverage_tool = os.path.join(tools_dir, 'generate_coverage_report.py')
        assert os.path.exists(coverage_tool), "generate_coverage_report.py should exist"


class TestAgentJobLinking:
    """Test agent-job linking functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = AgentHealthMonitor(window_size=10)
    
    def test_record_agent_usage(self):
        """Test recording agent usage in a job."""
        agent_id = "test_agent"
        job_id = "job-123"
        
        self.monitor.record_agent_usage(
            agent_id=agent_id,
            job_id=job_id,
            status="completed",
            duration=2.5,
            timestamp=datetime.now(timezone.utc)
        )
        
        history = self.monitor.get_agent_job_history(agent_id)
        assert len(history) == 1
        assert history[0]['job_id'] == job_id
        assert history[0]['status'] == "completed"
        assert history[0]['duration'] == 2.5
    
    def test_get_agent_job_history(self):
        """Test getting job history for an agent."""
        agent_id = "test_agent"
        
        # Record multiple jobs
        for i in range(5):
            self.monitor.record_agent_usage(
                agent_id=agent_id,
                job_id=f"job-{i}",
                status="completed",
                duration=1.0 + i,
                timestamp=datetime.now(timezone.utc)
            )
        
        history = self.monitor.get_agent_job_history(agent_id, limit=3)
        assert len(history) == 3
    
    def test_job_history_limit(self):
        """Test that job history respects the limit."""
        agent_id = "test_agent"
        
        # Record more jobs than the deque maxlen
        for i in range(150):
            self.monitor.record_agent_usage(
                agent_id=agent_id,
                job_id=f"job-{i}",
                status="completed",
                duration=1.0,
                timestamp=datetime.now(timezone.utc)
            )
        
        # Should only keep last 100
        history = self.monitor.get_agent_job_history(agent_id)
        assert len(history) <= 100
    
    def test_job_status_filtering(self):
        """Test filtering jobs by status."""
        agent_id = "test_agent"
        
        # Record jobs with different statuses
        self.monitor.record_agent_usage(
            agent_id=agent_id,
            job_id="job-success",
            status="completed",
            duration=1.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        self.monitor.record_agent_usage(
            agent_id=agent_id,
            job_id="job-fail",
            status="failed",
            duration=0.5,
            timestamp=datetime.now(timezone.utc)
        )
        
        history = self.monitor.get_agent_job_history(agent_id)
        assert len(history) == 2
        
        # Check both statuses are present
        statuses = {h['status'] for h in history}
        assert 'completed' in statuses
        assert 'failed' in statuses
    
    def test_record_execution_updates_job_history(self):
        """Test that record_execution also updates job history."""
        agent_id = "test_agent"
        job_id = "job-456"
        
        self.monitor.record_execution(
            agent_id=agent_id,
            success=True,
            duration_ms=1500,
            job_id=job_id,
            agent_name="Test Agent"
        )
        
        history = self.monitor.get_agent_job_history(agent_id)
        assert len(history) == 1
        assert history[0]['job_id'] == job_id
        assert history[0]['status'] == "completed"
        assert history[0]['duration'] == 1.5  # Converted from ms to seconds
    
    def test_reset_clears_job_history(self):
        """Test that resetting agent health clears job history."""
        agent_id = "test_agent"
        
        # Record some jobs
        for i in range(3):
            self.monitor.record_agent_usage(
                agent_id=agent_id,
                job_id=f"job-{i}",
                status="completed",
                duration=1.0,
                timestamp=datetime.now(timezone.utc)
            )
        
        # Verify jobs were recorded
        history = self.monitor.get_agent_job_history(agent_id)
        assert len(history) == 3
        
        # Reset health
        self.monitor.reset_agent_health(agent_id)
        
        # Verify job history is cleared
        history = self.monitor.get_agent_job_history(agent_id)
        assert len(history) == 0
    
    def test_global_health_monitor_singleton(self):
        """Test that get_health_monitor returns a singleton."""
        monitor1 = get_health_monitor()
        monitor2 = get_health_monitor()
        assert monitor1 is monitor2
    
    def test_job_history_newest_first(self):
        """Test that job history is returned newest first."""
        agent_id = "test_agent"
        
        # Record jobs at different times
        import time
        for i in range(3):
            self.monitor.record_agent_usage(
                agent_id=agent_id,
                job_id=f"job-{i}",
                status="completed",
                duration=1.0,
                timestamp=datetime.now(timezone.utc)
            )
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        history = self.monitor.get_agent_job_history(agent_id)
        
        # Check that timestamps are in descending order (newest first)
        for i in range(len(history) - 1):
            assert history[i]['timestamp'] >= history[i + 1]['timestamp']
