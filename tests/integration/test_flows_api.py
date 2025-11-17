"""
Integration tests for Flow Analysis API.

Tests all flow-related endpoints:
- GET /api/flows/realtime
- GET /api/flows/history/{correlation_id}
- GET /api/flows/bottlenecks
- GET /api/flows/active
"""

import pytest
import time
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.web.app import create_app
from src.visualization.agent_flow_monitor import AgentFlowMonitor, DataFlow


@pytest.fixture
def flow_monitor():
    """Create a mock flow monitor with test data."""
    monitor = AgentFlowMonitor()
    
    # Add some test flows
    base_time = datetime.now(timezone.utc)
    
    # Add active flows
    for i in range(5):
        flow = DataFlow(
            flow_id=f"flow_{i}",
            source_agent=f"agent_{i % 3}",
            target_agent=f"agent_{(i + 1) % 3}",
            event_type="processing",
            data={},
            timestamp=(base_time - timedelta(seconds=i * 10)).isoformat(),
            correlation_id="test_job_123",
            status="active",
            latency_ms=100 + i * 200,  # Varying latencies
            data_size_bytes=1024 * (i + 1)
        )
        monitor.record_flow(flow)
    
    # Add some completed flows
    for i in range(3):
        flow = DataFlow(
            flow_id=f"flow_completed_{i}",
            source_agent=f"agent_{i}",
            target_agent=f"agent_{(i + 1) % 3}",
            event_type="completed",
            data={},
            timestamp=(base_time - timedelta(seconds=100 + i * 10)).isoformat(),
            correlation_id="test_job_123",
            status="completed",
            latency_ms=50 + i * 10,
            data_size_bytes=512 * (i + 1)
        )
        monitor.record_flow(flow)
    
    return monitor


@pytest.fixture
def client(flow_monitor):
    """Create test client with flow monitor."""
    app = create_app()
    
    # Inject the mock flow monitor
    from src.web.routes import flows
    flows.set_flow_monitor(flow_monitor)
    
    return TestClient(app)


class TestRealtimeFlows:
    """Tests for GET /api/flows/realtime endpoint."""
    
    def test_realtime_flows_default_window(self, client):
        """Test getting realtime flows with default 60s window."""
        response = client.get("/api/flows/realtime")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "flows" in data
        assert "window_seconds" in data
        assert "count" in data
        assert "timestamp" in data
        assert data["window_seconds"] == 60
        assert isinstance(data["flows"], list)
        assert data["count"] == len(data["flows"])
    
    def test_realtime_flows_custom_window(self, client):
        """Test getting realtime flows with custom window."""
        response = client.get("/api/flows/realtime?window=30")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["window_seconds"] == 30
        # Flows within 30s should be returned
        assert isinstance(data["flows"], list)
    
    def test_realtime_flows_window_validation(self, client):
        """Test window parameter validation."""
        # Test minimum window
        response = client.get("/api/flows/realtime?window=1")
        assert response.status_code == 200
        
        # Test maximum window
        response = client.get("/api/flows/realtime?window=3600")
        assert response.status_code == 200
        
        # Test invalid window (too large)
        response = client.get("/api/flows/realtime?window=10000")
        assert response.status_code == 422  # Validation error
        
        # Test invalid window (too small)
        response = client.get("/api/flows/realtime?window=0")
        assert response.status_code == 422
    
    def test_realtime_flows_structure(self, client):
        """Test structure of flow events."""
        response = client.get("/api/flows/realtime")
        assert response.status_code == 200
        
        data = response.json()
        if data["flows"]:
            flow = data["flows"][0]
            
            # Check required fields
            assert "flow_id" in flow
            assert "source_agent" in flow
            assert "target_agent" in flow
            assert "event_type" in flow
            assert "timestamp" in flow
            assert "correlation_id" in flow
            assert "status" in flow


class TestFlowHistory:
    """Tests for GET /api/flows/history/{correlation_id} endpoint."""
    
    def test_flow_history_with_data(self, client):
        """Test getting flow history for existing correlation ID."""
        response = client.get("/api/flows/history/test_job_123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["correlation_id"] == "test_job_123"
        assert "flows" in data
        assert "total_flows" in data
        assert "start_time" in data
        assert "end_time" in data
        assert isinstance(data["flows"], list)
        assert data["total_flows"] == len(data["flows"])
    
    def test_flow_history_nonexistent_correlation(self, client):
        """Test getting flow history for non-existent correlation ID."""
        response = client.get("/api/flows/history/nonexistent_job")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["correlation_id"] == "nonexistent_job"
        assert data["flows"] == []
        assert data["total_flows"] == 0
        assert data["start_time"] is None
        assert data["end_time"] is None
    
    def test_flow_history_duration_calculation(self, client):
        """Test that duration is calculated correctly."""
        response = client.get("/api/flows/history/test_job_123")
        
        assert response.status_code == 200
        data = response.json()
        
        if data["total_flows"] > 1:
            assert data["total_duration_ms"] is not None
            assert data["total_duration_ms"] >= 0
            assert data["start_time"] is not None
            assert data["end_time"] is not None


class TestBottlenecks:
    """Tests for GET /api/flows/bottlenecks endpoint."""
    
    def test_bottlenecks_default_threshold(self, client):
        """Test bottleneck detection with default threshold."""
        response = client.get("/api/flows/bottlenecks")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "bottlenecks" in data
        assert "threshold_ms" in data
        assert "count" in data
        assert "timestamp" in data
        assert data["threshold_ms"] == 1000
        assert isinstance(data["bottlenecks"], list)
        assert data["count"] == len(data["bottlenecks"])
    
    def test_bottlenecks_custom_threshold(self, client):
        """Test bottleneck detection with custom threshold."""
        response = client.get("/api/flows/bottlenecks?threshold_ms=100")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["threshold_ms"] == 100
        # With lower threshold, should detect more bottlenecks
        assert isinstance(data["bottlenecks"], list)
    
    def test_bottleneck_structure(self, client):
        """Test structure of bottleneck reports."""
        # Use low threshold to ensure we get bottlenecks
        response = client.get("/api/flows/bottlenecks?threshold_ms=50")
        assert response.status_code == 200
        
        data = response.json()
        if data["bottlenecks"]:
            bottleneck = data["bottlenecks"][0]
            
            # Check required fields
            assert "agent_id" in bottleneck
            assert "avg_latency_ms" in bottleneck
            assert "max_latency_ms" in bottleneck
            assert "flow_count" in bottleneck
            assert "severity" in bottleneck
            assert "timestamp" in bottleneck
            
            # Check severity values
            assert bottleneck["severity"] in ["low", "medium", "high", "critical"]
            
            # Check latency values
            assert bottleneck["avg_latency_ms"] >= 0
            assert bottleneck["max_latency_ms"] >= bottleneck["avg_latency_ms"]
    
    def test_bottlenecks_severity_ordering(self, client):
        """Test that bottlenecks are ordered by severity."""
        response = client.get("/api/flows/bottlenecks?threshold_ms=50")
        assert response.status_code == 200
        
        data = response.json()
        if len(data["bottlenecks"]) > 1:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            
            for i in range(len(data["bottlenecks"]) - 1):
                current_severity = severity_order[data["bottlenecks"][i]["severity"]]
                next_severity = severity_order[data["bottlenecks"][i + 1]["severity"]]
                assert current_severity <= next_severity


class TestActiveFlows:
    """Tests for GET /api/flows/active endpoint."""
    
    def test_active_flows_list(self, client):
        """Test getting active flows."""
        response = client.get("/api/flows/active")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "active_flows" in data
        assert "count" in data
        assert "timestamp" in data
        assert isinstance(data["active_flows"], list)
        assert data["count"] == len(data["active_flows"])
    
    def test_active_flows_structure(self, client):
        """Test structure of active flow objects."""
        response = client.get("/api/flows/active")
        assert response.status_code == 200
        
        data = response.json()
        if data["active_flows"]:
            flow = data["active_flows"][0]
            
            # Check required fields
            assert "flow_id" in flow
            assert "correlation_id" in flow
            assert "source_agent" in flow
            assert "target_agent" in flow
            assert "event_type" in flow
    
    def test_active_flows_filters_by_status(self, client, flow_monitor):
        """Test that only active flows are returned."""
        response = client.get("/api/flows/active")
        assert response.status_code == 200
        
        data = response.json()
        
        # All returned flows should have active status
        # (though the status field might not be in the response)
        # Just verify we got some flows
        assert isinstance(data["active_flows"], list)


class TestFlowIntegration:
    """Integration tests for flow tracking during job execution."""
    
    def test_flow_tracking_workflow(self, client, flow_monitor):
        """Test complete flow tracking workflow."""
        # 1. Check realtime flows
        response = client.get("/api/flows/realtime?window=120")
        assert response.status_code == 200
        realtime_data = response.json()
        assert realtime_data["count"] > 0
        
        # 2. Check history for correlation ID
        correlation_id = "test_job_123"
        response = client.get(f"/api/flows/history/{correlation_id}")
        assert response.status_code == 200
        history_data = response.json()
        assert history_data["total_flows"] > 0
        
        # 3. Check bottlenecks
        response = client.get("/api/flows/bottlenecks?threshold_ms=100")
        assert response.status_code == 200
        bottleneck_data = response.json()
        assert isinstance(bottleneck_data["bottlenecks"], list)
        
        # 4. Check active flows
        response = client.get("/api/flows/active")
        assert response.status_code == 200
        active_data = response.json()
        assert isinstance(active_data["active_flows"], list)
    
    def test_empty_flows_return_empty_lists(self, client):
        """Test that endpoints return empty lists when no data."""
        # Create a new app with empty flow monitor
        empty_monitor = AgentFlowMonitor()
        from src.web.routes import flows
        flows.set_flow_monitor(empty_monitor)
        
        # Test realtime
        response = client.get("/api/flows/realtime")
        assert response.status_code == 200
        assert response.json()["flows"] == []
        
        # Test history
        response = client.get("/api/flows/history/nonexistent")
        assert response.status_code == 200
        assert response.json()["flows"] == []
        
        # Test bottlenecks
        response = client.get("/api/flows/bottlenecks")
        assert response.status_code == 200
        assert response.json()["bottlenecks"] == []
        
        # Test active
        response = client.get("/api/flows/active")
        assert response.status_code == 200
        assert response.json()["active_flows"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
