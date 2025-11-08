"""Enhanced Visual API for Phase 3 - Advanced Debugging and Performance Analytics."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import json
import logging
import os
from pathlib import Path
import asyncio
import uuid

logger = logging.getLogger(__name__)


# Pydantic models for API requests
class StepStatusUpdate(BaseModel):
    status: str
    data: Optional[Dict[str, Any]] = None


class WorkflowExecutionRequest(BaseModel):
    profile_name: str
    parameters: Optional[Dict[str, Any]] = None


class BreakpointRequest(BaseModel):
    agent_id: str
    event_type: str
    condition: Optional[str] = None
    max_hits: Optional[int] = None


class ErrorAnalysisRequest(BaseModel):
    correlation_id: str
    agent_id: str
    error_type: str
    error_message: str
    context_data: Optional[Dict[str, Any]] = None


class VisualOrchestrationAPI:
    """Phase 3 API - Advanced Debugging and Performance Analytics."""
    
    def __init__(self, app: FastAPI, workflow_dir: str = './templates'):
        self.app = app
        self.workflow_dir = workflow_dir
        
        # Import here to avoid circular imports
        try:
            from .workflow_visualizer import WorkflowVisualizer
            self.workflow_visualizer = WorkflowVisualizer(workflow_dir=workflow_dir)
        except ImportError:
            logger.warning("Could not import WorkflowVisualizer, using mock")
            self.workflow_visualizer = None
        
        try:
            from .monitor import FlowMonitor
            self.flow_monitor = FlowMonitor()
            self.flow_monitor.start()
        except ImportError:
            logger.warning("Could not import FlowMonitor, using mock")
            self.flow_monitor = None
        
        # Phase 3: Workflow debugger
        try:
            from .workflow_debugger import get_workflow_debugger
            self.workflow_debugger = get_workflow_debugger()
        except ImportError:
            logger.warning("Could not import WorkflowDebugger, using mock")
            self.workflow_debugger = None
        
        # Phase 3: Agent flow monitor (with analytics)
        try:
            from .agent_flow_monitor import get_flow_monitor
            self.agent_flow_monitor = get_flow_monitor()
        except ImportError:
            logger.warning("Could not import AgentFlowMonitor, using mock")
            self.agent_flow_monitor = None
        
        # WebSocket connections
        self.websocket_connections: Dict[str, WebSocket] = {}
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register Phase 2 API routes."""
        
        # Workflow visualization endpoints
        @self.app.get("/api/workflows/profiles")
        async def list_workflow_profiles():
            """List available workflow profiles."""
            if not self.workflow_visualizer:
                return {"profiles": []}
            
            profiles = self.workflow_visualizer.workflows.get('profiles', {})
            return {
                "profiles": [
                    {
                        "id": profile_id,
                        "name": profile_data.get('name', profile_id),
                        "description": profile_data.get('description', ''),
                        "steps": len(profile_data.get('steps', []))
                    }
                    for profile_id, profile_data in profiles.items()
                ]
            }
        
        @self.app.get("/api/workflows/visual/{profile_name}")
        async def get_visual_workflow(profile_name: str):
            """Get visual workflow graph for React Flow."""
            if not self.workflow_visualizer:
                raise HTTPException(status_code=503, detail="Workflow visualizer not available")
            
            try:
                graph = self.workflow_visualizer.create_visual_graph(profile_name)
                return graph
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
        
        @self.app.put("/api/workflows/visual/{profile_name}/step/{step_id}/status")
        async def update_step_status(
            profile_name: str,
            step_id: str,
            update: StepStatusUpdate
        ):
            """Update step status and broadcast to WebSocket clients."""
            if not self.workflow_visualizer:
                raise HTTPException(status_code=503, detail="Workflow visualizer not available")
            
            try:
                self.workflow_visualizer.update_step_status(
                    profile_name,
                    step_id,
                    update.status,
                    update.data
                )
                
                # Broadcast update to WebSocket clients
                await self._broadcast_step_update(
                    profile_name,
                    step_id,
                    update.status,
                    update.data
                )
                
                return {"success": True, "profile": profile_name, "step": step_id}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/workflows/visual/{profile_name}/metrics")
        async def get_workflow_metrics(profile_name: str):
            """Get execution metrics for a workflow."""
            if not self.workflow_visualizer:
                raise HTTPException(status_code=503, detail="Workflow visualizer not available")
            
            try:
                metrics = self.workflow_visualizer.get_execution_metrics(profile_name)
                return metrics
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
        
        @self.app.post("/api/workflows/visual/{profile_name}/reset")
        async def reset_workflow_state(profile_name: str):
            """Reset execution state for a workflow."""
            if not self.workflow_visualizer:
                raise HTTPException(status_code=503, detail="Workflow visualizer not available")
            
            try:
                self.workflow_visualizer.reset_execution_state(profile_name)
                
                # Broadcast reset to WebSocket clients
                await self._broadcast_workflow_reset(profile_name)
                
                return {"success": True, "profile": profile_name}
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
        
        # Flow monitoring endpoints
        @self.app.get("/api/flows/realtime")
        async def get_realtime_flows():
            """Get real-time flow state."""
            if not self.flow_monitor:
                return {"active_flows": [], "agents": []}
            
            return {
                "active_flows": self.flow_monitor.get_active_flows(),
                "agents": self.flow_monitor.get_agent_states(),
                "timestamp": self._get_timestamp()
            }
        
        @self.app.get("/api/agents/status")
        async def get_agent_status():
            """Get status of all registered agents."""
            if not self.flow_monitor:
                return {"agents": []}
            
            return {
                "agents": self.flow_monitor.get_agent_states(),
                "total": self.flow_monitor.get_agent_count()
            }
        
        # Dashboard endpoints
        @self.app.get("/orchestration", response_class=HTMLResponse)
        async def serve_dashboard():
            """Serve the main orchestration dashboard."""
            dashboard_path = Path(__file__).parent / "orchestration_dashboard.html"
            
            if not dashboard_path.exists():
                raise HTTPException(status_code=404, detail="Dashboard not found")
            
            return FileResponse(dashboard_path)
        
        # WebSocket endpoint for real-time updates
        @self.app.websocket("/ws/workflow-updates")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time workflow updates."""
            await self._handle_websocket_connection(websocket)
        
        # Phase 3: Debugging endpoints
        @self.app.post("/api/debug/sessions")
        async def create_debug_session(correlation_id: str):
            """Create a new debug session."""
            if not self.workflow_debugger:
                raise HTTPException(status_code=503, detail="Workflow debugger not available")
            
            try:
                session_id = self.workflow_debugger.start_debug_session(correlation_id)
                return {
                    "session_id": session_id,
                    "correlation_id": correlation_id,
                    "status": "active"
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/debug/sessions/{session_id}")
        async def get_debug_session(session_id: str):
            """Get debug session details."""
            if not self.workflow_debugger:
                raise HTTPException(status_code=503, detail="Workflow debugger not available")
            
            if session_id not in self.workflow_debugger.debug_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            session = self.workflow_debugger.debug_sessions[session_id]
            return session.to_dict()
        
        @self.app.post("/api/debug/sessions/{session_id}/breakpoints")
        async def add_breakpoint(session_id: str, breakpoint: BreakpointRequest):
            """Add a breakpoint to a debug session."""
            if not self.workflow_debugger:
                raise HTTPException(status_code=503, detail="Workflow debugger not available")
            
            try:
                breakpoint_id = self.workflow_debugger.add_breakpoint(
                    session_id=session_id,
                    agent_id=breakpoint.agent_id,
                    event_type=breakpoint.event_type,
                    condition=breakpoint.condition,
                    max_hits=breakpoint.max_hits
                )
                return {
                    "breakpoint_id": breakpoint_id,
                    "session_id": session_id,
                    "agent_id": breakpoint.agent_id,
                    "event_type": breakpoint.event_type
                }
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/api/debug/sessions/{session_id}/breakpoints/{breakpoint_id}")
        async def remove_breakpoint(session_id: str, breakpoint_id: str):
            """Remove a breakpoint."""
            if not self.workflow_debugger:
                raise HTTPException(status_code=503, detail="Workflow debugger not available")
            
            try:
                self.workflow_debugger.remove_breakpoint(session_id, breakpoint_id)
                return {"success": True, "breakpoint_id": breakpoint_id}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/debug/sessions/{session_id}/step")
        async def step_next(session_id: str):
            """Step to next in debug session."""
            if not self.workflow_debugger:
                raise HTTPException(status_code=503, detail="Workflow debugger not available")
            
            try:
                self.workflow_debugger.step_next(session_id)
                return {"success": True, "session_id": session_id}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/debug/workflows/{correlation_id}/trace")
        async def get_workflow_trace(correlation_id: str):
            """Get execution trace for a workflow."""
            if not self.workflow_debugger:
                raise HTTPException(status_code=503, detail="Workflow debugger not available")
            
            try:
                trace = self.workflow_debugger.get_workflow_trace(correlation_id)
                return {"correlation_id": correlation_id, "trace": trace}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/debug/errors/analyze")
        async def analyze_error(request: ErrorAnalysisRequest):
            """Analyze an error and get suggestions."""
            if not self.workflow_debugger:
                raise HTTPException(status_code=503, detail="Workflow debugger not available")
            
            try:
                analysis = self.workflow_debugger.analyze_error(
                    correlation_id=request.correlation_id,
                    agent_id=request.agent_id,
                    error_type=request.error_type,
                    error_message=request.error_message,
                    context_data=request.context_data or {}
                )
                return analysis.to_dict()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/debug/workflows/{correlation_id}/optimizations")
        async def get_optimizations(correlation_id: str):
            """Get optimization suggestions for a workflow."""
            if not self.workflow_debugger:
                raise HTTPException(status_code=503, detail="Workflow debugger not available")
            
            try:
                suggestions = self.workflow_debugger.suggest_optimizations(correlation_id)
                return {"correlation_id": correlation_id, "suggestions": suggestions}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Phase 3: Performance analytics endpoints
        @self.app.get("/api/analytics/trends")
        async def get_performance_trends(agent_id: Optional[str] = None, window_hours: int = 1):
            """Get performance trends for agents."""
            if not self.agent_flow_monitor:
                return {"trends": {}}
            
            try:
                trends = self.agent_flow_monitor.get_performance_trends(agent_id, window_hours)
                return {"trends": trends, "window_hours": window_hours}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/analytics/metrics/{metric_name}")
        async def get_historical_metrics(metric_name: str, window_hours: int = 24):
            """Get historical metrics data."""
            if not self.agent_flow_monitor:
                return {"metrics": []}
            
            try:
                metrics = self.agent_flow_monitor.get_historical_metrics(metric_name, window_hours)
                return {
                    "metric_name": metric_name,
                    "window_hours": window_hours,
                    "data": metrics
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/analytics/comprehensive")
        async def get_comprehensive_analytics(window_hours: int = 24):
            """Get comprehensive performance analytics report."""
            if not self.agent_flow_monitor:
                return {"report": {}}
            
            try:
                report = self.agent_flow_monitor.get_comprehensive_analytics(window_hours)
                return report
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/analytics/bottlenecks")
        async def get_bottleneck_analysis():
            """Get current bottleneck analysis."""
            if not self.agent_flow_monitor:
                return {"bottlenecks": []}
            
            try:
                bottlenecks = self.agent_flow_monitor.detect_bottlenecks()
                return {"bottlenecks": bottlenecks, "timestamp": self._get_timestamp()}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/analytics/bottlenecks/history")
        async def get_bottleneck_history(limit: int = 50):
            """Get history of detected bottlenecks."""
            if not self.agent_flow_monitor:
                return {"history": []}
            
            try:
                history = self.agent_flow_monitor.get_bottleneck_history(limit)
                return {"history": history, "limit": limit}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        
        # System status endpoints
        @self.app.get("/api/system/status")
        async def get_system_status():
            """Get comprehensive system status."""
            status = {
                "device": self._get_device_status(),
                "ollama": self._get_ollama_status(),
                "cache": self._get_cache_status(),
                "visualization": {
                    "visualizer": self.workflow_visualizer is not None,
                    "monitor": self.flow_monitor is not None,
                    "debugger": self.workflow_debugger is not None,
                    "analytics": self.agent_flow_monitor is not None
                }
            }
            return status
        
        @self.app.get("/api/system/device")
        async def get_device_info():
            """Get device/GPU information."""
            return self._get_device_status()
        
        @self.app.get("/api/system/ollama")
        async def get_ollama_info():
            """Get Ollama configuration and models."""
            return self._get_ollama_status()
        
        @self.app.get("/api/system/cache")
        async def get_cache_info():
            """Get cache directory status."""
            return self._get_cache_status()
        
        # Health check
        @self.app.get("/api/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "phase": "phase3",
                "visualizer": self.workflow_visualizer is not None,
                "monitor": self.flow_monitor is not None,
                "debugger": self.workflow_debugger is not None,
                "analytics": self.agent_flow_monitor is not None,
                "websocket_connections": len(self.websocket_connections)
            }
    
    def _get_device_status(self) -> Dict[str, Any]:
        """Get current device status."""
        try:
            from src.engine.device import get_gpu_manager
            gpu_manager = get_gpu_manager()
            return {
                "device": gpu_manager.device,
                "reason": gpu_manager.detection_reason,
                "available": True
            }
        except Exception as e:
            return {
                "device": "cpu",
                "reason": f"Error: {str(e)}",
                "available": False
            }
    
    def _get_ollama_status(self) -> Dict[str, Any]:
        """Get Ollama status and models."""
        try:
            from src.utils.ollama_detector import check_ollama_setup
            import os
            
            ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            return check_ollama_setup(ollama_url)
        except Exception as e:
            return {
                "available": False,
                "status": f"Error: {str(e)}",
                "models": []
            }
    
    def _get_cache_status(self) -> Dict[str, Any]:
        """Get cache directory status."""
        from pathlib import Path
        
        cache_dirs = {
            "cache": Path("./cache"),
            "checkpoints": Path("./checkpoints"),
            "output": Path("./output")
        }
        
        status = {}
        for name, path in cache_dirs.items():
            status[name] = {
                "exists": path.exists(),
                "path": str(path),
                "writable": path.exists() and os.access(path, os.W_OK)
            }
        
        return status
    
    async def _handle_websocket_connection(self, websocket: WebSocket):
        """Handle WebSocket connection for real-time updates."""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.websocket_connections[connection_id] = websocket
        
        logger.info(f"WebSocket client connected: {connection_id} (total: {len(self.websocket_connections)})")
        
        try:
            # Send initial connection confirmation
            await websocket.send_json({
                "type": "connected",
                "connection_id": connection_id,
                "timestamp": self._get_timestamp()
            })
            
            while True:
                # Receive and process messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get('type') == 'subscribe':
                    profile_name = message.get('profile_name')
                    logger.info(f"Client {connection_id} subscribed to {profile_name}")
                    
                    # Send current workflow state
                    if self.workflow_visualizer and profile_name:
                        try:
                            graph = self.workflow_visualizer.create_visual_graph(profile_name)
                            await websocket.send_json({
                                "type": "workflow_state",
                                "data": graph,
                                "timestamp": self._get_timestamp()
                            })
                        except Exception as e:
                            logger.error(f"Error sending workflow state: {e}")
                
                elif message.get('type') == 'ping':
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": self._get_timestamp()
                    })
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
        finally:
            if connection_id in self.websocket_connections:
                del self.websocket_connections[connection_id]
    
    async def _broadcast_step_update(
        self,
        profile_name: str,
        step_id: str,
        status: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """Broadcast step update to all WebSocket clients."""
        message = {
            "type": "step_update",
            "profile_name": profile_name,
            "step_id": step_id,
            "status": status,
            "data": data or {},
            "timestamp": self._get_timestamp()
        }
        
        await self._broadcast_to_websockets(message)
    
    async def _broadcast_workflow_reset(self, profile_name: str):
        """Broadcast workflow reset to all WebSocket clients."""
        message = {
            "type": "workflow_reset",
            "profile_name": profile_name,
            "timestamp": self._get_timestamp()
        }
        
        await self._broadcast_to_websockets(message)
    
    async def _broadcast_to_websockets(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients."""
        if not self.websocket_connections:
            return
        
        disconnected = []
        
        for connection_id, websocket in list(self.websocket_connections.items()):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket {connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected:
            if connection_id in self.websocket_connections:
                del self.websocket_connections[connection_id]
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


def setup_visual_api(app: FastAPI, workflow_dir: str = './templates') -> VisualOrchestrationAPI:
    """Setup Phase 3 visual orchestration API with advanced debugging and analytics."""
    api = VisualOrchestrationAPI(app, workflow_dir=workflow_dir)
    logger.info("Phase 3 Visual Orchestration API initialized")
    return api
