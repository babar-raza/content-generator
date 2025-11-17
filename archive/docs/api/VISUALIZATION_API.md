# Visualization API Documentation

## Overview

The Visualization API provides REST and WebSocket endpoints for accessing workflow visualization, agent monitoring, and debugging features.

## Base URL

```
http://127.0.0.1:8000/api
```

## Endpoints

### Workflow Visualization

#### GET /visualization/workflows

List all available workflows.

**Response:**
```json
{
  "workflows": [
    {
      "workflow_id": "fast-draft",
      "name": "Fast Draft",
      "description": "Quick content generation workflow",
      "total_steps": 6
    }
  ],
  "total": 1
}
```

#### GET /visualization/workflows/{workflow_id}

Get workflow graph data for visualization.

**Parameters:**
- `workflow_id` (path): Workflow identifier

**Response:**
```json
{
  "profile_name": "fast-draft",
  "name": "Fast Draft",
  "description": "Quick content generation workflow",
  "nodes": [...],
  "edges": [...],
  "metadata": {...}
}
```

#### GET /visualization/workflows/{workflow_id}/render

Render workflow in DOT or JSON format.

**Parameters:**
- `workflow_id` (path): Workflow identifier
- `format` (query): Output format ('dot' or 'json')

**Response:**
```json
{
  "workflow_id": "fast-draft",
  "format": "json",
  "content": {...}
}
```

### Agent Monitoring

#### GET /monitoring/agents

Get execution metrics for all agents.

**Response:**
```json
{
  "agents": [
    {
      "agent_id": "research_agent",
      "total_executions": 10,
      "successful_executions": 9,
      "failed_executions": 1,
      "success_rate": 0.9,
      "avg_duration_ms": 1234.5,
      "last_execution": "2024-11-13T10:00:00Z",
      "current_status": "idle"
    }
  ],
  "total": 1
}
```

#### GET /monitoring/agents/{agent_id}

Get metrics for a specific agent.

**Parameters:**
- `agent_id` (path): Agent identifier

**Response:**
```json
{
  "agent_id": "research_agent",
  "total_executions": 10,
  "successful_executions": 9,
  "failed_executions": 1,
  "success_rate": 0.9,
  "avg_duration_ms": 1234.5,
  "recent_executions": [...]
}
```

#### WebSocket /ws/monitoring

Real-time monitoring updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws/monitoring');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

### System Monitoring

#### GET /monitoring/system

Get system resource metrics.

**Response:**
```json
{
  "cpu_percent": 45.2,
  "memory_percent": 62.8,
  "memory_available_mb": 4096.0,
  "memory_total_mb": 16384.0,
  "active_jobs": 3,
  "total_agents": 12,
  "uptime_seconds": 3600.0,
  "timestamp": "2024-11-13T10:00:00Z"
}
```

#### GET /monitoring/jobs/{job_id}/metrics

Get execution metrics for a specific job.

**Parameters:**
- `job_id` (path): Job identifier

**Response:**
```json
{
  "job_id": "abc123",
  "status": "running",
  "total_agents": 10,
  "completed_agents": 5,
  "failed_agents": 0,
  "total_flows": 15,
  "start_time": "2024-11-13T10:00:00Z",
  "duration_seconds": 120.5
}
```

### Debugging

#### POST /debug/breakpoints

Create a debugging breakpoint.

**Request:**
```json
{
  "agent_id": "research_agent",
  "event_type": "agent_start",
  "correlation_id": "job_123",
  "condition": "status == 'error'",
  "max_hits": 5
}
```

**Response:**
```json
{
  "breakpoint_id": "bp_123",
  "session_id": "debug_456",
  "agent_id": "research_agent",
  "event_type": "agent_start",
  "condition": "status == 'error'",
  "enabled": true,
  "hit_count": 0,
  "max_hits": 5,
  "created_at": "2024-11-13T10:00:00Z"
}
```

#### DELETE /debug/breakpoints/{breakpoint_id}

Remove a debugging breakpoint.

**Parameters:**
- `breakpoint_id` (path): Breakpoint identifier
- `session_id` (query, optional): Debug session ID

**Response:**
```json
{
  "message": "Breakpoint 'bp_123' removed successfully"
}
```

#### GET /debug/breakpoints

List active breakpoints.

**Parameters:**
- `session_id` (query, optional): Filter by session ID
- `enabled_only` (query, optional): Only return enabled breakpoints

**Response:**
```json
{
  "breakpoints": [
    {
      "breakpoint_id": "bp_123",
      "session_id": "debug_456",
      "agent_id": "research_agent",
      "event_type": "agent_start",
      "enabled": true,
      "hit_count": 0
    }
  ],
  "total": 1
}
```

#### POST /debug/step

Step through workflow execution.

**Request:**
```json
{
  "session_id": "debug_456",
  "action": "step"
}
```

**Response:**
```json
{
  "session_id": "debug_456",
  "status": "stepping",
  "current_step": "research_agent.agent_start",
  "message": "Step mode enabled for session 'debug_456'"
}
```

#### GET /debug/state/{job_id}

Get current debug state for a job.

**Parameters:**
- `job_id` (path): Job identifier

**Response:**
```json
{
  "job_id": "job_123",
  "session_id": "debug_456",
  "status": "paused",
  "current_step": "research_agent.agent_start",
  "step_history": [...],
  "variables": {...},
  "breakpoints": [...]
}
```

## Error Responses

All endpoints return standard error responses:

```json
{
  "detail": "Error message"
}
```

HTTP status codes:
- 200: Success
- 201: Created
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error
- 503: Service Unavailable

## Testing

### cURL Examples

```bash
# List workflows
curl http://127.0.0.1:8000/api/visualization/workflows

# Get workflow graph
curl http://127.0.0.1:8000/api/visualization/workflows/fast-draft

# Get agent metrics
curl http://127.0.0.1:8000/api/monitoring/agents

# Get system metrics
curl http://127.0.0.1:8000/api/monitoring/system

# Create breakpoint
curl -X POST http://127.0.0.1:8000/api/debug/breakpoints \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "test_agent", "event_type": "agent_start", "correlation_id": "test"}'

# List breakpoints
curl http://127.0.0.1:8000/api/debug/breakpoints

# WebSocket connection (wscat)
wscat -c ws://127.0.0.1:8000/ws/monitoring
```

### Python Test

```python
import requests

# Test workflow visualization
response = requests.get('http://127.0.0.1:8000/api/visualization/workflows')
print(response.json())

# Test agent metrics
response = requests.get('http://127.0.0.1:8000/api/monitoring/agents')
print(response.json())

# Test system metrics
response = requests.get('http://127.0.0.1:8000/api/monitoring/system')
print(response.json())
```
