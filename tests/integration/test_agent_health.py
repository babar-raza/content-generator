"""
Integration tests for Agent Health Monitoring API.

Tests all agent health endpoints:
- GET /api/agents/health
- GET /api/agents/{agent_id}/health
- GET /api/agents/{agent_id}/failures
- POST /api/agents/{agent_id}/health/reset
"""

import pytest
import time
from fastapi.testclient import TestClient
from unittest.mock import Mock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.web.app import create_app
from src.orchestration.agent_health_monitor import AgentHealthMonitor


@pytest.fixture
def health_monitor():
    """Create a health monitor for testing."""
    return AgentHealthMonitor(window_size=100)


@pytest.fixture
def client(health_monitor):
    """Create test client with health monitor."""
    app = create_app()
    
    # Inject the health monitor
    from src.orchestration import agent_health_monitor
    agent_health_monitor._health_monitor = health_monitor
    
    return TestClient(app)


class TestHealthSummary:
    """Tests for overall health summary endpoint."""
    
    def test_get_health_summary_empty(self, client):
        """Test health summary with no executions."""
        response = client.get("/api/agents/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "timestamp" in data
        assert data["total_agents"] == 0
        assert data["healthy_agents"] == 0
        assert data["degraded_agents"] == 0
        assert data["failing_agents"] == 0
        assert data["unknown_agents"] == 0
        assert "agents" in data
        assert len(data["agents"]) == 0
    
    def test_get_health_summary_with_agents(self, client, health_monitor):
        """Test health summary with agent executions."""
        # Record some executions
        health_monitor.record_execution(
            agent_id="agent1",
            success=True,
            duration_ms=100,
            job_id="job1",
            agent_name="Test Agent 1"
        )
        health_monitor.record_execution(
            agent_id="agent2",
            success=True,
            duration_ms=200,
            job_id="job2",
            agent_name="Test Agent 2"
        )
        
        response = client.get("/api/agents/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_agents"] == 2
        assert data["healthy_agents"] == 2  # 0% error rate
        assert len(data["agents"]) == 2
    
    def test_health_status_transitions(self, client, health_monitor):
        """Test health status changes based on error rate."""
        agent_id = "test_agent"
        
        # Start with all successes (healthy)
        for i in range(10):
            health_monitor.record_execution(
                agent_id=agent_id,
                success=True,
                duration_ms=100,
                job_id=f"job_{i}"
            )
        
        response = client.get("/api/agents/health")
        agents = {a["agent_id"]: a for a in response.json()["agents"]}
        assert agents[agent_id]["status"] == "healthy"
        
        # Add some failures (degraded: 5-20% error rate)
        for i in range(10, 15):  # 5 failures out of 15 total = 33%
            health_monitor.record_execution(
                agent_id=agent_id,
                success=False,
                duration_ms=100,
                job_id=f"job_{i}",
                error="Test error"
            )
        
        response = client.get("/api/agents/health")
        agents = {a["agent_id"]: a for a in response.json()["agents"]}
        assert agents[agent_id]["status"] == "failing"  # >20% error rate
        
        # Add more successes to bring it to degraded
        for i in range(15, 35):  # Now 5 failures out of 35 = 14%
            health_monitor.record_execution(
                agent_id=agent_id,
                success=True,
                duration_ms=100,
                job_id=f"job_{i}"
            )
        
        response = client.get("/api/agents/health")
        agents = {a["agent_id"]: a for a in response.json()["agents"]}
        assert agents[agent_id]["status"] == "degraded"  # 5-20% error rate


class TestAgentHealth:
    """Tests for specific agent health endpoint."""
    
    def test_get_agent_health_no_executions(self, client):
        """Test getting health for agent with no executions."""
        response = client.get("/api/agents/unknown_agent/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == "unknown_agent"
        assert data["metrics"]["total_executions"] == 0
        assert data["metrics"]["status"] == "unknown"
        assert data["recent_failures"] == []
    
    def test_get_agent_health_with_executions(self, client, health_monitor):
        """Test getting health for agent with executions."""
        agent_id = "test_agent"
        
        # Record successful executions
        for i in range(5):
            health_monitor.record_execution(
                agent_id=agent_id,
                success=True,
                duration_ms=100 + i * 10,
                job_id=f"job_{i}",
                agent_name="Test Agent"
            )
        
        # Record one failure
        health_monitor.record_execution(
            agent_id=agent_id,
            success=False,
            duration_ms=150,
            job_id="job_fail",
            error="Test error"
        )
        
        response = client.get(f"/api/agents/{agent_id}/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == agent_id
        assert data["name"] == "Test Agent"
        assert data["metrics"]["total_executions"] == 6
        assert data["metrics"]["successful_executions"] == 5
        assert data["metrics"]["failed_executions"] == 1
        assert data["metrics"]["error_rate"] == pytest.approx(1/6, rel=0.01)
        assert data["metrics"]["status"] == "degraded"  # 16.7% error rate
        assert "average_duration_ms" in data["metrics"]
        assert "last_execution_time" in data["metrics"]
        assert len(data["recent_failures"]) == 1
    
    def test_agent_health_metrics_accuracy(self, client, health_monitor):
        """Test accuracy of health metrics calculation."""
        agent_id = "metrics_test"
        
        # Record 100 executions with varying durations
        durations = []
        for i in range(100):
            duration = 100 + (i % 10) * 10
            durations.append(duration)
            health_monitor.record_execution(
                agent_id=agent_id,
                success=i % 10 != 0,  # Every 10th fails (10% error rate)
                duration_ms=duration,
                job_id=f"job_{i}",
                error="Error" if i % 10 == 0 else None
            )
        
        response = client.get(f"/api/agents/{agent_id}/health")
        data = response.json()
        
        assert data["metrics"]["total_executions"] == 100
        assert data["metrics"]["successful_executions"] == 90
        assert data["metrics"]["failed_executions"] == 10
        assert data["metrics"]["error_rate"] == 0.1
        assert data["metrics"]["status"] == "degraded"  # 10% error rate
        
        # Check average duration
        expected_avg = sum(durations) / len(durations)
        assert data["metrics"]["average_duration_ms"] == pytest.approx(expected_avg, rel=0.01)


class TestAgentFailures:
    """Tests for agent failures endpoint."""
    
    def test_get_failures_no_failures(self, client):
        """Test getting failures for agent with no failures."""
        response = client.get("/api/agents/test_agent/failures")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == "test_agent"
        assert data["failures"] == []
        assert data["total"] == 0
    
    def test_get_failures_with_failures(self, client, health_monitor):
        """Test getting failures for agent with recorded failures."""
        agent_id = "failing_agent"
        
        # Record some successful executions
        for i in range(5):
            health_monitor.record_execution(
                agent_id=agent_id,
                success=True,
                duration_ms=100,
                job_id=f"job_success_{i}"
            )
        
        # Record failures with details
        for i in range(3):
            health_monitor.record_execution(
                agent_id=agent_id,
                success=False,
                duration_ms=200,
                job_id=f"job_fail_{i}",
                error=f"Test error {i}",
                error_type="TestError",
                input_data={"test": f"data_{i}"},
                stack_trace=f"Stack trace {i}"
            )
        
        response = client.get(f"/api/agents/{agent_id}/failures")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == agent_id
        assert data["total"] == 3
        assert len(data["failures"]) == 3
        
        # Check first failure details
        failure = data["failures"][0]
        assert "timestamp" in failure
        assert failure["agent_id"] == agent_id
        assert failure["error_type"] == "TestError"
        assert "Test error" in failure["error_message"]
        assert failure["input_data"] is not None
        assert failure["stack_trace"] is not None
    
    def test_failures_limit(self, client, health_monitor):
        """Test failures limit parameter."""
        agent_id = "many_failures"
        
        # Record 20 failures
        for i in range(20):
            health_monitor.record_execution(
                agent_id=agent_id,
                success=False,
                duration_ms=100,
                job_id=f"job_{i}",
                error=f"Error {i}"
            )
        
        # Request only 5 failures
        response = client.get(f"/api/agents/{agent_id}/failures?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only get the 10 most recent (monitor limit)
        # But we requested 5
        assert len(data["failures"]) == 5
    
    def test_failures_most_recent_first(self, client, health_monitor):
        """Test that failures are returned most recent first."""
        agent_id = "ordered_failures"
        
        # Record failures with specific order
        for i in range(5):
            time.sleep(0.01)  # Small delay to ensure timestamp ordering
            health_monitor.record_execution(
                agent_id=agent_id,
                success=False,
                duration_ms=100,
                job_id=f"job_{i}",
                error=f"Error {i}"
            )
        
        response = client.get(f"/api/agents/{agent_id}/failures")
        data = response.json()
        
        # Most recent should be first
        failures = data["failures"]
        assert "Error 4" in failures[0]["error_message"]
        assert "Error 3" in failures[1]["error_message"]


class TestHealthReset:
    """Tests for health reset endpoint."""
    
    def test_reset_agent_health(self, client, health_monitor):
        """Test resetting health metrics for an agent."""
        agent_id = "reset_test"
        
        # Record some executions
        for i in range(10):
            health_monitor.record_execution(
                agent_id=agent_id,
                success=i % 2 == 0,
                duration_ms=100,
                job_id=f"job_{i}",
                error="Error" if i % 2 != 0 else None
            )
        
        # Verify agent has metrics
        response = client.get(f"/api/agents/{agent_id}/health")
        assert response.json()["metrics"]["total_executions"] == 10
        
        # Reset health
        reset_response = client.post(f"/api/agents/{agent_id}/health/reset")
        
        assert reset_response.status_code == 200
        data = reset_response.json()
        assert data["agent_id"] == agent_id
        assert "message" in data
        
        # Verify metrics are reset
        response = client.get(f"/api/agents/{agent_id}/health")
        assert response.json()["metrics"]["total_executions"] == 0
        assert response.json()["metrics"]["status"] == "unknown"
        
        # Verify failures are cleared
        failures_response = client.get(f"/api/agents/{agent_id}/failures")
        assert failures_response.json()["total"] == 0


class TestHealthIntegration:
    """Integration tests for complete health monitoring workflow."""
    
    def test_complete_health_workflow(self, client, health_monitor):
        """Test complete workflow from executions to health monitoring."""
        # 1. Start with no agents
        response = client.get("/api/agents/health")
        assert response.json()["total_agents"] == 0
        
        # 2. Simulate agent executions
        agents = ["agent1", "agent2", "agent3"]
        
        for agent_id in agents:
            # Each agent has different success rates
            if agent_id == "agent1":
                # Healthy: 2% error rate
                successes, failures = 98, 2
            elif agent_id == "agent2":
                # Degraded: 10% error rate
                successes, failures = 90, 10
            else:
                # Failing: 30% error rate
                successes, failures = 70, 30
            
            # Record successes
            for i in range(successes):
                health_monitor.record_execution(
                    agent_id=agent_id,
                    success=True,
                    duration_ms=100 + i,
                    job_id=f"{agent_id}_job_{i}",
                    agent_name=f"Agent {agent_id}"
                )
            
            # Record failures
            for i in range(failures):
                health_monitor.record_execution(
                    agent_id=agent_id,
                    success=False,
                    duration_ms=200 + i,
                    job_id=f"{agent_id}_fail_{i}",
                    error=f"Test error {i}",
                    error_type="TestError"
                )
        
        # 3. Check overall health summary
        summary_response = client.get("/api/agents/health")
        summary = summary_response.json()
        
        assert summary["total_agents"] == 3
        assert summary["healthy_agents"] == 1  # agent1
        assert summary["degraded_agents"] == 1  # agent2
        assert summary["failing_agents"] == 1  # agent3
        
        # 4. Check individual agent health
        agent1_response = client.get("/api/agents/agent1/health")
        agent1 = agent1_response.json()
        assert agent1["metrics"]["status"] == "healthy"
        assert agent1["metrics"]["error_rate"] < 0.05
        
        agent2_response = client.get("/api/agents/agent2/health")
        agent2 = agent2_response.json()
        assert agent2["metrics"]["status"] == "degraded"
        assert 0.05 <= agent2["metrics"]["error_rate"] < 0.20
        
        agent3_response = client.get("/api/agents/agent3/health")
        agent3 = agent3_response.json()
        assert agent3["metrics"]["status"] == "failing"
        assert agent3["metrics"]["error_rate"] >= 0.20
        
        # 5. Check failures for failing agent
        failures_response = client.get("/api/agents/agent3/failures")
        failures = failures_response.json()
        assert failures["total"] > 0
        assert len(failures["failures"]) <= 10  # Monitor keeps last 10
        
        # 6. Reset one agent's health
        client.post("/api/agents/agent3/health/reset")
        
        # 7. Verify reset
        reset_response = client.get("/api/agents/agent3/health")
        assert reset_response.json()["metrics"]["total_executions"] == 0
        
        # 8. Overall summary should reflect the reset
        final_summary = client.get("/api/agents/health").json()
        assert final_summary["failing_agents"] == 0
        assert final_summary["unknown_agents"] == 1  # agent3 is now unknown


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
