# Visualization Module

## Overview

Visual debugging, monitoring, and workflow editing tools for the web UI.

## Components

### `workflow_visualizer.py`
Creates visual representations of workflows.

```python
class WorkflowVisualizer:
    """Workflow visualization"""
    def create_visual_graph(self, workflow: Workflow) -> Graph
    def get_execution_metrics(self, job_id: str) -> Metrics
```

### `workflow_debugger.py`
Interactive workflow debugging with breakpoints.

```python
class WorkflowDebugger:
    """Interactive debugging"""
    def set_breakpoint(self, step: str)
    def step_through(self, job_id: str)
    def inspect_state(self, job_id: str) -> WorkflowState
```

### `visual_api.py`
API endpoints for visual components.

```python
class VisualAPI:
    """Visualization API"""
    async def get_workflow_graph(self, workflow_id: str) -> Graph
    async def get_realtime_status(self, job_id: str) -> Status
```

### `agent_flow_monitor.py`
Monitors agent execution flow in real-time.

```python
class AgentFlowMonitor:
    """Real-time flow monitoring"""
    def track_agent(self, agent_id: str, state: AgentState)
    def get_flow_metrics(self) -> FlowMetrics
```

### `monitor.py`
General monitoring and metrics collection.

```python
class Monitor:
    """System monitoring"""
    def collect_metrics(self) -> SystemMetrics
    def alert(self, condition: str)
```

## Web UI Integration

The visualization module powers the web UI:

1. **Workflow Graph**: Interactive node-edge graphs
2. **Real-Time Updates**: WebSocket-based live updates
3. **Breakpoint Debugging**: Step-through execution
4. **Performance Metrics**: Flamegraphs and timelines

## Usage

### Create Workflow Visualization

```python
from src.visualization.workflow_visualizer import WorkflowVisualizer

visualizer = WorkflowVisualizer()
graph = visualizer.create_visual_graph('blog_generation')

# Graph structure:
# {
#   'nodes': [{'id': 'agent1', 'label': 'Agent 1', ...}],
#   'edges': [{'source': 'agent1', 'target': 'agent2', ...}]
# }
```

### Set Debug Breakpoint

```python
from src.visualization.workflow_debugger import WorkflowDebugger

debugger = WorkflowDebugger()
debugger.set_breakpoint(
    step='content_generation',
    condition='output.word_count < 500'
)
```

### Monitor Agent Flow

```python
from src.visualization.agent_flow_monitor import AgentFlowMonitor

monitor = AgentFlowMonitor()
metrics = monitor.get_flow_metrics()
```

## Visualization Formats

### Graph Format (Cytoscape.js compatible)

```json
{
  "nodes": [
    {
      "id": "agent1",
      "data": {
        "label": "Outline Agent",
        "status": "completed",
        "duration": 2.5
      }
    }
  ],
  "edges": [
    {
      "source": "agent1",
      "target": "agent2"
    }
  ]
}
```

## Dependencies

- `fastapi` - Web API
- `websockets` - Real-time updates
- `src.orchestration` - Workflow data
- `src.engine` - Execution metrics
