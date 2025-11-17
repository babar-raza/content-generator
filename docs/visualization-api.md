# Visualization API Reference

## Overview

The Visualization API provides comprehensive endpoints for visualizing workflows, monitoring agents, analyzing performance, and debugging job execution. All visualization endpoints provide JSON responses suitable for client-side rendering.

**Base URL:** `/api/viz`

## Endpoints

### Workflows Visualization

#### GET /api/viz/workflows

List all available workflows.

**Parameters:**
- `format` (string, optional): Output format. Default: "json"

**Response:**
```json
{
  "profiles": [
    {
      "id": "default_blog",
      "name": "Default Blog Generation",
      "description": "Standard blog post generation workflow",
      "steps": 12
    }
  ]
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py viz workflows --format json
```

---

#### GET /api/viz/graph/{workflow_id}

Get workflow execution graph with nodes and edges.

**Parameters:**
- `workflow_id` (string, required): Workflow identifier
- `job_id` (string, optional): Job ID to overlay execution data

**Response:**
```json
{
  "nodes": [
    {
      "id": "outline_creation",
      "data": {
        "label": "Outline Creation",
        "type": "agent",
        "execution": {
          "status": "completed",
          "duration": 2.5
        }
      },
      "position": {"x": 100, "y": 100}
    }
  ],
  "edges": [
    {
      "id": "edge_1",
      "source": "outline_creation",
      "target": "content_generation"
    }
  ]
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py viz graph --profile default_blog --json
```

---

### System Metrics

#### GET /api/viz/metrics

Get system or workflow execution metrics.

**Parameters:**
- `workflow_id` (string, optional): Specific workflow to analyze
- `time_range` (string, optional): Time range (e.g., "24h", "7d"). Default: "24h"
- `granularity` (string, optional): Data point granularity (e.g., "1h", "5m"). Default: "1h"

**Response:**
```json
{
  "time_range": "24h",
  "granularity": "1h",
  "timestamp": "2024-01-15T10:30:00Z",
  "system": {
    "total_jobs": 45,
    "total_agents": 28,
    "active_flows": 12
  },
  "throughput": {
    "jobs_per_hour": 15,
    "agents_per_hour": 120
  },
  "performance": {
    "avg_job_duration": 45.2,
    "avg_agent_duration": 3.8
  }
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py viz metrics --format json
```

---

### Agent Monitoring

#### GET /api/viz/agents

Get agent status and execution metrics.

**Response:**
```json
{
  "agents": [
    {
      "name": "outline_creation",
      "status": "idle",
      "last_seen": "2024-01-15T10:29:00Z",
      "executions": 145,
      "avg_duration": 2.3,
      "success_rate": 0.98
    }
  ],
  "total": 28
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py viz agents --json
```

---

### Data Flows

#### GET /api/viz/flows

Get active data flows between agents.

**Parameters:**
- `workflow_id` (string, optional): Filter by workflow
- `job_id` (string, optional): Filter by job

**Response:**
```json
{
  "active_flows": [
    {
      "flow_id": "flow_123",
      "source": "outline_creation",
      "target": "content_generation",
      "status": "active",
      "data_size": 1024,
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "count": 12
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py viz flows --json
```

---

### Performance Analysis

#### GET /api/viz/bottlenecks

Analyze and identify performance bottlenecks.

**Parameters:**
- `workflow_id` (string, optional): Filter by workflow
- `threshold_seconds` (float, optional): Threshold for slow operations. Default: 5.0

**Response:**
```json
{
  "bottlenecks": [
    {
      "agent_id": "content_generation",
      "duration": 12.5,
      "type": "slow_agent",
      "threshold": 5.0,
      "occurrences": 23,
      "p95_duration": 15.2
    }
  ],
  "count": 3,
  "threshold_seconds": 5.0
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py viz bottlenecks --workflow default_blog
```

---

### Debug Visualization

#### GET /api/viz/debug/{job_id}

Get debug visualization data for a specific job.

**Parameters:**
- `job_id` (string, required): Job identifier

**Response:**
```json
{
  "job_id": "job_abc123",
  "timestamp": "2024-01-15T10:30:00Z",
  "session": {
    "session_id": "debug_xyz",
    "status": "active",
    "breakpoints": 3,
    "step_history": [
      {
        "step": "outline_creation",
        "timestamp": "2024-01-15T10:28:00Z",
        "status": "completed"
      }
    ]
  }
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py viz debug --action create --correlation-id job_abc123
```

---

## Integration Examples

### React Component Example

```typescript
import { useEffect, useState } from 'react';
import { apiClient } from '@/api/client';

function WorkflowVisualizer() {
  const [workflows, setWorkflows] = useState([]);

  useEffect(() => {
    apiClient.getWorkflowsViz().then(data => {
      setWorkflows(data.profiles);
    });
  }, []);

  return (
    <div>
      {workflows.map(workflow => (
        <div key={workflow.id}>
          <h3>{workflow.name}</h3>
          <p>{workflow.description}</p>
          <p>Steps: {workflow.steps}</p>
        </div>
      ))}
    </div>
  );
}
```

### Python Client Example

```python
import requests

# Get workflows
response = requests.get('http://localhost:8080/api/viz/workflows')
workflows = response.json()

# Get specific workflow graph
workflow_id = workflows['profiles'][0]['id']
graph_response = requests.get(
    f'http://localhost:8080/api/viz/graph/{workflow_id}'
)
graph = graph_response.json()

# Analyze bottlenecks
bottlenecks = requests.get(
    f'http://localhost:8080/api/viz/bottlenecks?workflow_id={workflow_id}'
).json()
```

---

## Performance Characteristics

All visualization endpoints are optimized for sub-100ms response times:

- **Workflows List:** < 50ms
- **Graph Generation:** < 80ms
- **Metrics Aggregation:** < 100ms
- **Bottleneck Analysis:** < 120ms

Response times measured under normal load (< 10 concurrent requests).

---

## Data Formats

### Graph Data Format

The graph format is compatible with React Flow and similar visualization libraries:

```typescript
interface GraphNode {
  id: string;
  data: {
    label: string;
    type: string;
    execution?: {
      status: string;
      duration: number;
    };
  };
  position: { x: number; y: number };
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}
```

### Metrics Format

Metrics follow a consistent structure:

```typescript
interface Metrics {
  timestamp: string;  // ISO 8601
  time_range: string;
  granularity: string;
  data: {
    [key: string]: number | string;
  };
}
```

---

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK`: Successful request
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error response format:
```json
{
  "detail": "Workflow 'invalid_id' not found"
}
```

---

## Rate Limiting

No rate limiting is currently enforced on visualization endpoints. For production deployments, consider implementing rate limiting at the reverse proxy level.

---

## Caching

Visualization endpoints support ETags and Last-Modified headers for client-side caching:

```http
GET /api/viz/workflows
If-None-Modified: Mon, 15 Jan 2024 10:00:00 GMT

Response: 304 Not Modified
```

---

## WebSocket Support

Real-time updates are available via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8080/api/ws/monitoring');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Real-time update:', update);
};
```

---

## See Also

- [Main API Reference](./web-api-reference.md)
- [Workflow Configuration](./workflow-config.md)
- [Agent Development Guide](./agent-development.md)
