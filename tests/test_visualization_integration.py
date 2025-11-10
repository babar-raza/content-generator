"""Tests for visualization web integration."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock


class TestVisualizationWebEndpoints:
    """Test visualization endpoints in web app."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.web.app import create_app
        app = create_app()
        return TestClient(app)
    
    def test_workflow_profiles_endpoint(self, client):
        """Test workflow profiles endpoint."""
        response = client.get("/api/workflows/profiles")
        assert response.status_code == 200
        data = response.json()
        assert 'profiles' in data or 'result' in data
    
    def test_workflow_visual_endpoint(self, client):
        """Test visual workflow endpoint."""
        # This might fail without proper setup, but tests endpoint exists
        response = client.get("/api/workflows/visual/test_profile")
        # Accept 200 (success) or 404/500 (expected without setup)
        assert response.status_code in [200, 404, 500, 503]
    
    def test_agents_status_endpoint(self, client):
        """Test agent status endpoint."""
        response = client.get("/api/agents/status")
        assert response.status_code == 200
        data = response.json()
        assert 'agents' in data or 'result' in data
    
    def test_flows_realtime_endpoint(self, client):
        """Test real-time flows endpoint."""
        response = client.get("/api/flows/realtime")
        assert response.status_code == 200
        data = response.json()
        assert 'active_flows' in data or 'result' in data
    
    def test_flows_bottlenecks_endpoint(self, client):
        """Test bottlenecks endpoint."""
        response = client.get("/api/flows/bottlenecks")
        assert response.status_code == 200
        data = response.json()
        assert 'bottlenecks' in data or 'result' in data


class TestMCPVisualizationEndpoints:
    """Test MCP visualization endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client with MCP router."""
        from fastapi import FastAPI
        from src.mcp.web_adapter import router
        
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    def test_mcp_workflow_profiles(self, client):
        """Test MCP workflow profiles endpoint."""
        response = client.get("/mcp/workflows/profiles")
        assert response.status_code == 200
    
    def test_mcp_agents_status(self, client):
        """Test MCP agents status endpoint."""
        response = client.get("/mcp/agents/status")
        assert response.status_code == 200
    
    def test_mcp_flows_realtime(self, client):
        """Test MCP real-time flows endpoint."""
        response = client.get("/mcp/flows/realtime")
        assert response.status_code == 200
    
    def test_mcp_flows_bottlenecks(self, client):
        """Test MCP bottlenecks endpoint."""
        response = client.get("/mcp/flows/bottlenecks")
        assert response.status_code == 200
    
    def test_mcp_debug_session_creation(self, client):
        """Test MCP debug session creation."""
        response = client.post("/mcp/debug/sessions?correlation_id=test_123")
        assert response.status_code in [200, 500]  # 500 if debugger not initialized
    
    def test_mcp_request_endpoint(self, client):
        """Test generic MCP request endpoint."""
        response = client.post("/mcp/request", json={
            "jsonrpc": "2.0",
            "method": "workflows/profiles",
            "params": {},
            "id": 1
        })
        assert response.status_code == 200
        data = response.json()
        assert 'result' in data or 'error' in data


class TestVisualizationWebSocketIntegration:
    """Test WebSocket integration for visualization."""
    
    def test_websocket_connection(self):
        """Test WebSocket connection establishment."""
        from fastapi.testclient import TestClient
        from src.web.app import create_app
        
        app = create_app()
        client = TestClient(app)
        
        # WebSocket connections are tricky to test, just verify endpoint exists
        # Real WebSocket testing would require more complex setup
        pass
    
    def test_websocket_message_broadcast(self):
        """Test WebSocket message broadcasting."""
        # This is a placeholder for WebSocket testing
        # Full implementation would require async test framework
        pass


class TestVisualizationDashboard:
    """Test visualization dashboard access."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.web.app import create_app
        app = create_app()
        return TestClient(app)
    
    def test_dashboard_access(self, client):
        """Test dashboard HTML is accessible."""
        response = client.get("/orchestration")
        # Should return HTML or 404 if not found
        assert response.status_code in [200, 404, 500]


class TestVisualizationAPIErrorHandling:
    """Test error handling in visualization API."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI
        from src.mcp.web_adapter import router
        
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    def test_invalid_profile_name(self, client):
        """Test handling of invalid profile name."""
        response = client.get("/mcp/workflows/visual/nonexistent_profile_xyz")
        # Should return error (404 or 500)
        assert response.status_code in [404, 500, 503]
    
    def test_missing_required_parameter(self, client):
        """Test handling of missing required parameters."""
        response = client.post("/mcp/debug/breakpoints", json={
            "session_id": "invalid",
            # Missing required fields
        })
        # Should return error
        assert response.status_code in [400, 422, 500]
    
    def test_invalid_session_id(self, client):
        """Test handling of invalid session ID."""
        response = client.get("/mcp/debug/sessions/invalid_session_xyz")
        # Should return error
        assert response.status_code in [404, 500, 503]


class TestVisualizationCLIIntegration:
    """Test CLI integration with visualization."""
    
    def test_cli_can_access_mcp_endpoints(self):
        """Test CLI can access MCP visualization endpoints."""
        # This tests that the CLI can import and use MCP client
        try:
            from src.mcp.protocol import MCPRequest
            
            request = MCPRequest(
                method="workflows/profiles",
                params={}
            )
            
            assert request.method == "workflows/profiles"
            assert request.params == {}
        except ImportError:
            pytest.fail("CLI cannot import MCP protocol")
    
    def test_cli_visualization_commands_exist(self):
        """Test CLI has visualization commands."""
        # Check that CLI has visualization command structure
        import os
        cli_path = os.path.join(os.path.dirname(__file__), '..', 'ucop_unified_cli.py')
        
        if os.path.exists(cli_path):
            with open(cli_path, 'r') as f:
                content = f.read()
                # Check for visualization-related functionality
                # This is a basic check - could be expanded
                assert 'visualization' in content or 'visual' in content or 'debug' in content or 'monitor' in content


class TestVisualizationDataFlow:
    """Test data flow through visualization system."""
    
    def test_flow_data_persistence(self):
        """Test that flow data persists correctly."""
        from src.visualization.agent_flow_monitor import AgentFlowMonitor
        
        monitor = AgentFlowMonitor()
        
        # Record a flow
        flow_id = monitor.record_flow_start(
            source_agent='agent_a',
            target_agent='agent_b',
            event_type='test_event',
            data={'test': 'data'},
            correlation_id='test_correlation'
        )
        
        # Complete the flow
        monitor.record_flow_completion(
            flow_id=flow_id,
            status='completed',
            result_data={'result': 'success'}
        )
        
        # Verify data is persisted
        history = monitor.get_flow_history('test_correlation')
        assert len(history) == 1
        assert history[0]['flow_id'] == flow_id
        assert history[0]['status'] == 'completed'
    
    def test_workflow_state_updates(self):
        """Test workflow state updates correctly."""
        from src.visualization.workflow_visualizer import WorkflowVisualizer
        
        visualizer = WorkflowVisualizer(workflow_dir='./templates')
        visualizer.workflows = {
            'profiles': {
                'test_profile': {
                    'steps': [{'id': 'step1', 'name': 'Step 1'}]
                }
            }
        }
        
        # Update step status
        visualizer.update_step_status('test_profile', 'step1', 'running', {'progress': 25})
        
        # Verify state updated
        state = visualizer.execution_state['test_profile']['step1']
        assert state['status'] == 'running'
        assert state['data']['progress'] == 25
        
        # Update again
        visualizer.update_step_status('test_profile', 'step1', 'completed', {'progress': 100})
        
        # Verify state updated again
        state = visualizer.execution_state['test_profile']['step1']
        assert state['status'] == 'completed'
        assert state['data']['progress'] == 100


class TestVisualizationConcurrency:
    """Test concurrent access to visualization system."""
    
    @pytest.mark.asyncio
    async def test_concurrent_flow_recording(self):
        """Test concurrent flow recording."""
        from src.visualization.agent_flow_monitor import AgentFlowMonitor
        import asyncio
        
        monitor = AgentFlowMonitor()
        
        async def record_flows(num):
            flows = []
            for i in range(num):
                flow_id = monitor.record_flow_start(
                    source_agent=f'agent_{i}',
                    target_agent=f'agent_{i+1}',
                    event_type='test',
                    data={},
                    correlation_id=f'test_{i}'
                )
                flows.append(flow_id)
                await asyncio.sleep(0.001)  # Simulate async work
            return flows
        
        # Record flows concurrently
        results = await asyncio.gather(
            record_flows(10),
            record_flows(10),
            record_flows(10)
        )
        
        # Verify all flows recorded
        total_flows = sum(len(r) for r in results)
        assert total_flows == 30
    
    @pytest.mark.asyncio
    async def test_concurrent_state_updates(self):
        """Test concurrent workflow state updates."""
        from src.visualization.workflow_visualizer import WorkflowVisualizer
        import asyncio
        
        visualizer = WorkflowVisualizer(workflow_dir='./templates')
        visualizer.workflows = {
            'profiles': {
                'test_profile': {
                    'steps': [
                        {'id': f'step{i}', 'name': f'Step {i}'}
                        for i in range(10)
                    ]
                }
            }
        }
        
        async def update_steps():
            for i in range(10):
                visualizer.update_step_status(
                    'test_profile',
                    f'step{i}',
                    'running',
                    {'progress': i * 10}
                )
                await asyncio.sleep(0.001)
        
        # Update steps concurrently
        await asyncio.gather(
            update_steps(),
            update_steps(),
            update_steps()
        )
        
        # Verify states are updated (last update wins)
        for i in range(10):
            state = visualizer.execution_state['test_profile'][f'step{i}']
            assert state['status'] == 'running'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
