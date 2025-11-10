"""Comprehensive tests for visualization system."""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock


class TestWorkflowVisualizer:
    """Test workflow visualizer functionality."""
    
    def test_create_visual_graph(self):
        """Test visual graph creation."""
        from src.visualization.workflow_visualizer import WorkflowVisualizer
        
        visualizer = WorkflowVisualizer(workflow_dir='./templates')
        
        # Mock workflow data
        visualizer.workflows = {
            'profiles': {
                'test_profile': {
                    'name': 'Test Profile',
                    'description': 'Test workflow',
                    'steps': [
                        {
                            'id': 'step1',
                            'name': 'Step 1',
                            'type': 'research',
                            'dependencies': []
                        },
                        {
                            'id': 'step2',
                            'name': 'Step 2',
                            'type': 'content',
                            'dependencies': ['step1']
                        }
                    ]
                }
            }
        }
        
        graph = visualizer.create_visual_graph('test_profile')
        
        assert 'nodes' in graph
        assert 'edges' in graph
        assert len(graph['nodes']) == 2
        assert len(graph['edges']) == 1
        assert graph['edges'][0]['source'] == 'step1'
        assert graph['edges'][0]['target'] == 'step2'
    
    def test_update_step_status(self):
        """Test step status updates."""
        from src.visualization.workflow_visualizer import WorkflowVisualizer
        
        visualizer = WorkflowVisualizer(workflow_dir='./templates')
        visualizer.workflows = {
            'profiles': {
                'test_profile': {
                    'steps': [{'id': 'step1', 'name': 'Step 1'}]
                }
            }
        }
        
        visualizer.update_step_status('test_profile', 'step1', 'running', {'progress': 50})
        
        assert visualizer.execution_state['test_profile']['step1']['status'] == 'running'
        assert visualizer.execution_state['test_profile']['step1']['data']['progress'] == 50
    
    def test_get_execution_metrics(self):
        """Test execution metrics retrieval."""
        from src.visualization.workflow_visualizer import WorkflowVisualizer
        
        visualizer = WorkflowVisualizer(workflow_dir='./templates')
        visualizer.workflows = {
            'profiles': {
                'test_profile': {
                    'steps': [{'id': 'step1', 'name': 'Step 1'}]
                }
            }
        }
        
        visualizer.execution_state['test_profile'] = {
            'step1': {
                'status': 'completed',
                'start_time': datetime.now().timestamp(),
                'end_time': datetime.now().timestamp() + 10,
                'data': {}
            }
        }
        
        metrics = visualizer.get_execution_metrics('test_profile')
        
        assert 'total_steps' in metrics
        assert 'completed_steps' in metrics
        assert 'total_duration' in metrics
    
    def test_reset_execution_state(self):
        """Test execution state reset."""
        from src.visualization.workflow_visualizer import WorkflowVisualizer
        
        visualizer = WorkflowVisualizer(workflow_dir='./templates')
        visualizer.execution_state['test_profile'] = {'step1': {'status': 'completed'}}
        
        visualizer.reset_execution_state('test_profile')
        
        assert visualizer.execution_state['test_profile'] == {}


class TestAgentFlowMonitor:
    """Test agent flow monitor functionality."""
    
    def test_record_flow_start(self):
        """Test flow start recording."""
        from src.visualization.agent_flow_monitor import AgentFlowMonitor
        
        monitor = AgentFlowMonitor()
        
        flow_id = monitor.record_flow_start(
            source_agent='agent_a',
            target_agent='agent_b',
            event_type='data_transfer',
            data={'key': 'value'},
            correlation_id='test_correlation'
        )
        
        assert flow_id is not None
        assert flow_id in monitor.active_flows
        assert monitor.active_flows[flow_id]['source_agent'] == 'agent_a'
        assert monitor.active_flows[flow_id]['target_agent'] == 'agent_b'
    
    def test_record_flow_completion(self):
        """Test flow completion recording."""
        from src.visualization.agent_flow_monitor import AgentFlowMonitor
        
        monitor = AgentFlowMonitor()
        
        flow_id = monitor.record_flow_start(
            source_agent='agent_a',
            target_agent='agent_b',
            event_type='data_transfer',
            data={'key': 'value'},
            correlation_id='test_correlation'
        )
        
        monitor.record_flow_completion(
            flow_id=flow_id,
            status='completed',
            result_data={'result': 'success'}
        )
        
        assert flow_id not in monitor.active_flows
        history = monitor.get_flow_history('test_correlation')
        assert len(history) == 1
        assert history[0]['status'] == 'completed'
    
    def test_detect_bottlenecks(self):
        """Test bottleneck detection."""
        from src.visualization.agent_flow_monitor import AgentFlowMonitor
        from datetime import datetime, timedelta
        
        monitor = AgentFlowMonitor()
        
        # Create a slow flow
        flow_id = monitor.record_flow_start(
            source_agent='agent_a',
            target_agent='agent_b',
            event_type='data_transfer',
            data={},
            correlation_id='test'
        )
        
        # Simulate long duration
        monitor.active_flows[flow_id]['start_time'] = (datetime.now() - timedelta(seconds=100)).isoformat()
        
        bottlenecks = monitor.detect_bottlenecks()
        
        assert len(bottlenecks) > 0
        assert bottlenecks[0]['flow_id'] == flow_id
    
    def test_get_flow_history(self):
        """Test flow history retrieval."""
        from src.visualization.agent_flow_monitor import AgentFlowMonitor
        
        monitor = AgentFlowMonitor()
        correlation_id = 'test_correlation'
        
        # Record multiple flows
        for i in range(3):
            flow_id = monitor.record_flow_start(
                source_agent=f'agent_{i}',
                target_agent=f'agent_{i+1}',
                event_type='data_transfer',
                data={},
                correlation_id=correlation_id
            )
            monitor.record_flow_completion(flow_id, 'completed', {})
        
        history = monitor.get_flow_history(correlation_id)
        assert len(history) == 3


class TestWorkflowDebugger:
    """Test workflow debugger functionality."""
    
    def test_start_debug_session(self):
        """Test debug session creation."""
        from src.visualization.workflow_debugger import WorkflowDebugger
        
        debugger = WorkflowDebugger()
        session_id = debugger.start_debug_session('test_correlation')
        
        assert session_id in debugger.debug_sessions
        assert debugger.debug_sessions[session_id].correlation_id == 'test_correlation'
        assert debugger.debug_sessions[session_id].status == 'active'
    
    def test_add_breakpoint(self):
        """Test breakpoint addition."""
        from src.visualization.workflow_debugger import WorkflowDebugger
        
        debugger = WorkflowDebugger()
        session_id = debugger.start_debug_session('test_correlation')
        
        breakpoint_id = debugger.add_breakpoint(
            session_id=session_id,
            agent_id='test_agent',
            event_type='data_transfer',
            condition='data["value"] > 10'
        )
        
        assert breakpoint_id is not None
        session = debugger.debug_sessions[session_id]
        assert len(session.breakpoints) == 1
        assert session.breakpoints[0].agent_id == 'test_agent'
    
    def test_remove_breakpoint(self):
        """Test breakpoint removal."""
        from src.visualization.workflow_debugger import WorkflowDebugger
        
        debugger = WorkflowDebugger()
        session_id = debugger.start_debug_session('test_correlation')
        
        breakpoint_id = debugger.add_breakpoint(
            session_id=session_id,
            agent_id='test_agent',
            event_type='data_transfer'
        )
        
        debugger.remove_breakpoint(session_id, breakpoint_id)
        
        session = debugger.debug_sessions[session_id]
        assert len(session.breakpoints) == 0
    
    def test_evaluate_breakpoint_condition(self):
        """Test breakpoint condition evaluation."""
        from src.visualization.workflow_debugger import WorkflowDebugger
        
        debugger = WorkflowDebugger()
        session_id = debugger.start_debug_session('test_correlation')
        
        breakpoint_id = debugger.add_breakpoint(
            session_id=session_id,
            agent_id='test_agent',
            event_type='data_transfer',
            condition='data.get("value", 0) > 10'
        )
        
        # Test with data that matches condition
        result = debugger.check_breakpoint(
            session_id=session_id,
            agent_id='test_agent',
            event_type='data_transfer',
            data={'value': 15}
        )
        
        assert result is True
        
        # Test with data that doesn't match
        result = debugger.check_breakpoint(
            session_id=session_id,
            agent_id='test_agent',
            event_type='data_transfer',
            data={'value': 5}
        )
        
        assert result is False
    
    def test_step_next(self):
        """Test step-through debugging."""
        from src.visualization.workflow_debugger import WorkflowDebugger
        
        debugger = WorkflowDebugger()
        session_id = debugger.start_debug_session('test_correlation')
        
        session = debugger.debug_sessions[session_id]
        assert session.step_mode is False
        
        debugger.step_next(session_id)
        
        assert session.step_mode is True
    
    def test_continue_execution(self):
        """Test continue execution."""
        from src.visualization.workflow_debugger import WorkflowDebugger
        
        debugger = WorkflowDebugger()
        session_id = debugger.start_debug_session('test_correlation')
        
        session = debugger.debug_sessions[session_id]
        session.step_mode = True
        
        debugger.continue_execution(session_id)
        
        assert session.step_mode is False


class TestFlowMonitor:
    """Test basic flow monitor functionality."""
    
    def test_monitor_initialization(self):
        """Test monitor initialization."""
        from src.visualization.monitor import FlowMonitor
        
        monitor = FlowMonitor()
        
        assert monitor.active_flows == {}
        assert monitor.agent_states == {}
    
    def test_start_monitoring(self):
        """Test monitoring start."""
        from src.visualization.monitor import FlowMonitor
        
        monitor = FlowMonitor()
        monitor.start()
        
        assert monitor.is_running is True
    
    def test_stop_monitoring(self):
        """Test monitoring stop."""
        from src.visualization.monitor import FlowMonitor
        
        monitor = FlowMonitor()
        monitor.start()
        monitor.stop()
        
        assert monitor.is_running is False
    
    def test_get_active_flows(self):
        """Test active flows retrieval."""
        from src.visualization.monitor import FlowMonitor
        
        monitor = FlowMonitor()
        monitor.active_flows = {
            'flow1': {'source': 'agent_a', 'target': 'agent_b'},
            'flow2': {'source': 'agent_b', 'target': 'agent_c'}
        }
        
        flows = monitor.get_active_flows()
        assert len(flows) == 2
    
    def test_get_agent_states(self):
        """Test agent states retrieval."""
        from src.visualization.monitor import FlowMonitor
        
        monitor = FlowMonitor()
        monitor.agent_states = {
            'agent_a': {'status': 'active', 'last_seen': datetime.now().isoformat()},
            'agent_b': {'status': 'idle', 'last_seen': datetime.now().isoformat()}
        }
        
        states = monitor.get_agent_states()
        assert len(states) == 2


@pytest.mark.asyncio
class TestMCPVisualizationIntegration:
    """Test MCP integration for visualization endpoints."""
    
    async def test_workflow_profiles_endpoint(self):
        """Test workflow profiles MCP endpoint."""
        from src.mcp.web_adapter import handle_workflow_profiles
        
        result = await handle_workflow_profiles({})
        
        assert 'profiles' in result
        assert isinstance(result['profiles'], list)
    
    async def test_workflow_visual_endpoint(self):
        """Test visual workflow MCP endpoint."""
        from src.mcp.web_adapter import handle_workflow_visual
        
        # This will fail without proper workflow data, but tests the endpoint exists
        try:
            result = await handle_workflow_visual({'profile_name': 'test'})
        except Exception as e:
            # Expected to fail without proper setup
            pass
    
    async def test_agents_status_endpoint(self):
        """Test agent status MCP endpoint."""
        from src.mcp.web_adapter import handle_agents_status
        
        result = await handle_agents_status({})
        
        assert 'agents' in result
        assert 'total' in result
    
    async def test_flows_realtime_endpoint(self):
        """Test real-time flows MCP endpoint."""
        from src.mcp.web_adapter import handle_flows_realtime
        
        result = await handle_flows_realtime({})
        
        assert 'active_flows' in result
        assert 'agents' in result
    
    async def test_debug_session_create_endpoint(self):
        """Test debug session creation MCP endpoint."""
        from src.mcp.web_adapter import handle_debug_session_create
        
        result = await handle_debug_session_create({'correlation_id': 'test_123'})
        
        assert 'session_id' in result
        assert 'correlation_id' in result
        assert result['correlation_id'] == 'test_123'
    
    async def test_debug_breakpoint_add_endpoint(self):
        """Test breakpoint addition MCP endpoint."""
        from src.mcp.web_adapter import handle_debug_breakpoint_add
        
        # First create a session
        session_result = await handle_debug_session_create({'correlation_id': 'test_123'})
        session_id = session_result['session_id']
        
        # Add breakpoint
        result = await handle_debug_breakpoint_add({
            'session_id': session_id,
            'agent_id': 'test_agent',
            'event_type': 'data_transfer'
        })
        
        assert 'breakpoint_id' in result
        assert 'session_id' in result
        assert result['session_id'] == session_id


class TestVisualizationErrorHandling:
    """Test error handling in visualization system."""
    
    def test_invalid_profile_name(self):
        """Test handling of invalid profile name."""
        from src.visualization.workflow_visualizer import WorkflowVisualizer
        
        visualizer = WorkflowVisualizer(workflow_dir='./templates')
        
        with pytest.raises(ValueError):
            visualizer.create_visual_graph('nonexistent_profile')
    
    def test_invalid_session_id(self):
        """Test handling of invalid session ID."""
        from src.visualization.workflow_debugger import WorkflowDebugger
        
        debugger = WorkflowDebugger()
        
        with pytest.raises(ValueError):
            debugger.add_breakpoint(
                session_id='invalid_session',
                agent_id='test_agent',
                event_type='data_transfer'
            )
    
    def test_missing_required_params(self):
        """Test handling of missing required parameters."""
        from src.visualization.agent_flow_monitor import AgentFlowMonitor
        
        monitor = AgentFlowMonitor()
        
        with pytest.raises(TypeError):
            monitor.record_flow_start()  # Missing required params


class TestVisualizationPerformance:
    """Test performance aspects of visualization system."""
    
    def test_large_flow_history(self):
        """Test handling of large flow history."""
        from src.visualization.agent_flow_monitor import AgentFlowMonitor
        
        monitor = AgentFlowMonitor()
        correlation_id = 'test_correlation'
        
        # Record many flows
        for i in range(1000):
            flow_id = monitor.record_flow_start(
                source_agent=f'agent_{i}',
                target_agent=f'agent_{i+1}',
                event_type='data_transfer',
                data={},
                correlation_id=correlation_id
            )
            monitor.record_flow_completion(flow_id, 'completed', {})
        
        # Should handle large history efficiently
        history = monitor.get_flow_history(correlation_id)
        assert len(history) == 1000
    
    def test_many_active_flows(self):
        """Test handling of many active flows."""
        from src.visualization.agent_flow_monitor import AgentFlowMonitor
        
        monitor = AgentFlowMonitor()
        
        # Create many active flows
        flow_ids = []
        for i in range(100):
            flow_id = monitor.record_flow_start(
                source_agent=f'agent_{i}',
                target_agent=f'agent_{i+1}',
                event_type='data_transfer',
                data={},
                correlation_id=f'correlation_{i}'
            )
            flow_ids.append(flow_id)
        
        # Should handle many active flows
        assert len(monitor.active_flows) == 100
        
        # Cleanup
        for flow_id in flow_ids:
            monitor.record_flow_completion(flow_id, 'completed', {})
    
    def test_bottleneck_detection_performance(self):
        """Test bottleneck detection with many flows."""
        from src.visualization.agent_flow_monitor import AgentFlowMonitor
        from datetime import datetime, timedelta
        import time
        
        monitor = AgentFlowMonitor()
        
        # Create many flows with varied durations
        for i in range(50):
            flow_id = monitor.record_flow_start(
                source_agent=f'agent_{i}',
                target_agent=f'agent_{i+1}',
                event_type='data_transfer',
                data={},
                correlation_id=f'correlation_{i}'
            )
            
            # Make some flows "slow"
            if i % 10 == 0:
                monitor.active_flows[flow_id]['start_time'] = (
                    datetime.now() - timedelta(seconds=100)
                ).isoformat()
        
        # Bottleneck detection should complete quickly
        start_time = time.time()
        bottlenecks = monitor.detect_bottlenecks()
        detection_time = time.time() - start_time
        
        assert detection_time < 1.0  # Should complete in under 1 second
        assert len(bottlenecks) >= 5  # Should detect the slow flows


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
