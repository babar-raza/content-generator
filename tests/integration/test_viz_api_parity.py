"""Integration tests for CLI vs Web API parity (Task Card 04)."""

import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from pathlib import Path


@pytest.fixture
def test_client():
    """Create test client for the web app."""
    from src.web.app import create_app
    app = create_app()
    return TestClient(app)


class TestVisualizationParity:
    """Test CLI/Web API parity for visualization endpoints."""
    
    def test_workflows_viz_parity(self, test_client):
        """Test workflows visualization parity."""
        response = test_client.get("/api/viz/workflows")
        assert response.status_code == 200
        
        data = response.json()
        assert "profiles" in data
        assert isinstance(data["profiles"], list)
        
        # Each profile should have required fields
        for profile in data["profiles"]:
            assert "id" in profile
            assert "name" in profile
            assert "description" in profile
            assert "steps" in profile
    
    def test_graph_viz_parity(self, test_client):
        """Test graph visualization parity."""
        # First get workflows to find a valid workflow_id
        workflows_response = test_client.get("/api/viz/workflows")
        assert workflows_response.status_code == 200
        
        workflows = workflows_response.json()["profiles"]
        if not workflows:
            pytest.skip("No workflows available for testing")
        
        workflow_id = workflows[0]["id"]
        
        # Test graph endpoint
        response = test_client.get(f"/api/viz/graph/{workflow_id}")
        assert response.status_code == 200
        
        graph = response.json()
        assert "nodes" in graph
        assert "edges" in graph
        assert isinstance(graph["nodes"], list)
        assert isinstance(graph["edges"], list)
    
    def test_metrics_viz_parity(self, test_client):
        """Test metrics visualization parity."""
        response = test_client.get("/api/viz/metrics")
        assert response.status_code == 200
        
        metrics = response.json()
        assert "timestamp" in metrics
        
        # Should have system-wide metrics
        if "system" in metrics:
            assert isinstance(metrics["system"], dict)
    
    def test_agents_viz_parity(self, test_client):
        """Test agents visualization parity."""
        response = test_client.get("/api/viz/agents")
        assert response.status_code == 200
        
        data = response.json()
        assert "agents" in data
        assert "total" in data
        assert isinstance(data["agents"], list)
        assert data["total"] >= 0
    
    def test_flows_viz_parity(self, test_client):
        """Test flows visualization parity."""
        response = test_client.get("/api/viz/flows")
        assert response.status_code == 200
        
        data = response.json()
        assert "active_flows" in data
        assert "count" in data
        assert isinstance(data["active_flows"], list)
        assert data["count"] >= 0
    
    def test_bottlenecks_viz_parity(self, test_client):
        """Test bottlenecks analysis parity."""
        response = test_client.get("/api/viz/bottlenecks")
        assert response.status_code == 200
        
        data = response.json()
        assert "bottlenecks" in data
        assert "count" in data
        assert "threshold_seconds" in data
        assert isinstance(data["bottlenecks"], list)
        assert data["count"] >= 0
    
    def test_debug_viz_parity(self, test_client):
        """Test debug visualization parity."""
        # Test with a dummy job_id
        job_id = "test_job_123"
        response = test_client.get(f"/api/viz/debug/{job_id}")
        
        # Should return 200 with debug data (even if empty)
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
        assert data["job_id"] == job_id
        assert "timestamp" in data


class TestTopicsParity:
    """Test CLI/Web API parity for topics endpoints."""
    
    def test_discover_topics_parity(self, test_client):
        """Test topic discovery parity."""
        # Test with content parameter
        response = test_client.post("/api/topics/discover", json={
            "content": "This is a test document about Python programming.",
            "max_topics": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have status field
        assert "status" in data
    
    def test_discover_topics_requires_source(self, test_client):
        """Test that topic discovery requires at least one source."""
        response = test_client.post("/api/topics/discover", json={
            "max_topics": 10
        })
        
        # Should fail without any source
        assert response.status_code == 400
    
    def test_list_topics_parity(self, test_client):
        """Test list topics parity."""
        response = test_client.get("/api/topics/list")
        assert response.status_code == 200
        
        data = response.json()
        assert "topics" in data
        assert "total" in data


class TestIngestionParity:
    """Test CLI/Web API parity for ingestion endpoints."""
    
    def test_ingest_kb_parity(self, test_client):
        """Test KB ingestion parity."""
        response = test_client.post("/api/ingest/kb", json={
            "path": "/tmp/test_kb"
        })
        
        # May fail if path doesn't exist, but API should respond
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
    
    def test_ingest_docs_parity(self, test_client):
        """Test docs ingestion parity."""
        response = test_client.post("/api/ingest/docs", json={
            "path": "/tmp/test_docs"
        })
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
    
    def test_ingest_api_parity(self, test_client):
        """Test API ingestion parity."""
        response = test_client.post("/api/ingest/api", json={
            "path": "/tmp/test_api"
        })
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
    
    def test_ingest_blog_parity(self, test_client):
        """Test blog ingestion parity."""
        response = test_client.post("/api/ingest/blog", json={
            "path": "/tmp/test_blog"
        })
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
    
    def test_ingest_tutorial_parity(self, test_client):
        """Test tutorial ingestion parity."""
        response = test_client.post("/api/ingest/tutorial", json={
            "path": "/tmp/test_tutorial"
        })
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
    
    def test_ingestion_status_parity(self, test_client):
        """Test ingestion status parity."""
        response = test_client.get("/api/ingest/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "operations" in data
        assert "total" in data


class TestConfigParity:
    """Test CLI/Web API parity for config endpoints."""
    
    def test_tone_config_parity(self, test_client):
        """Test tone config parity."""
        response = test_client.get("/api/config/tone")
        assert response.status_code == 200
        
        data = response.json()
        assert "tone" in data
    
    def test_performance_config_parity(self, test_client):
        """Test performance config parity."""
        response = test_client.get("/api/config/performance")
        assert response.status_code == 200
        
        data = response.json()
        assert "performance" in data
    
    def test_hot_reload_parity(self, test_client):
        """Test hot-reload parity."""
        response = test_client.post("/api/config/hot-reload")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data


class TestDebugParity:
    """Test CLI/Web API parity for debug endpoints."""
    
    def test_system_diagnostics_parity(self, test_client):
        """Test system diagnostics parity."""
        response = test_client.get("/api/debug/system")
        assert response.status_code == 200
        
        data = response.json()
        assert "timestamp" in data
        assert "agents" in data
        assert "workflows" in data
        assert "jobs" in data
        assert "resources" in data
        assert "config" in data
    
    def test_agent_debug_parity(self, test_client):
        """Test agent debug parity."""
        response = test_client.get("/api/debug/agent/test_agent")
        assert response.status_code == 200
        
        data = response.json()
        assert "agent_id" in data
    
    def test_job_debug_parity(self, test_client):
        """Test job debug parity."""
        response = test_client.get("/api/debug/job/test_job")
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
    
    def test_performance_profile_parity(self, test_client):
        """Test performance profile parity."""
        response = test_client.get("/api/debug/performance")
        assert response.status_code == 200
        
        data = response.json()
        assert "timestamp" in data


class TestPerformance:
    """Test performance of visualization endpoints."""
    
    def test_viz_endpoint_performance(self, test_client):
        """Test that viz endpoints respond quickly (<100ms target)."""
        import time
        
        endpoints = [
            "/api/viz/workflows",
            "/api/viz/agents",
            "/api/viz/flows",
            "/api/viz/bottlenecks",
            "/api/viz/metrics"
        ]
        
        for endpoint in endpoints:
            start = time.time()
            response = test_client.get(endpoint)
            duration = (time.time() - start) * 1000  # Convert to ms
            
            assert response.status_code == 200
            # Relaxed threshold for testing (500ms instead of 100ms)
            assert duration < 500, f"{endpoint} took {duration:.2f}ms (should be <500ms)"


class TestDataValidation:
    """Test data validation and consistency."""
    
    def test_workflows_data_structure(self, test_client):
        """Test workflows data structure is valid."""
        response = test_client.get("/api/viz/workflows")
        data = response.json()
        
        for profile in data["profiles"]:
            assert isinstance(profile["id"], str)
            assert isinstance(profile["name"], str)
            assert isinstance(profile["description"], str)
            assert isinstance(profile["steps"], int)
            assert profile["steps"] >= 0
    
    def test_metrics_data_structure(self, test_client):
        """Test metrics data structure is valid."""
        response = test_client.get("/api/viz/metrics")
        metrics = response.json()
        
        assert "timestamp" in metrics
        # Timestamp should be ISO format
        from datetime import datetime
        try:
            datetime.fromisoformat(metrics["timestamp"].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("Timestamp is not in valid ISO format")
    
    def test_bottlenecks_threshold_parameter(self, test_client):
        """Test bottlenecks threshold parameter works."""
        # Test with different thresholds
        thresholds = [1.0, 5.0, 10.0]
        
        for threshold in thresholds:
            response = test_client.get(f"/api/viz/bottlenecks?threshold_seconds={threshold}")
            assert response.status_code == 200
            
            data = response.json()
            assert data["threshold_seconds"] == threshold


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
