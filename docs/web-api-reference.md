# Web API Reference

## Overview

This document provides a complete reference for the UCOP Web API, including all endpoints added in Task Card 04 for CLI/Web API parity.

**Base URL:** `http://localhost:8080/api`

---

## Visualization Endpoints

### Workflows

- **GET /viz/workflows** - List all workflows
- **GET /viz/graph/{workflow_id}** - Get workflow graph
- **GET /viz/metrics** - Get system/workflow metrics
- **GET /viz/agents** - Get agent status
- **GET /viz/flows** - Get active data flows
- **GET /viz/bottlenecks** - Analyze performance bottlenecks
- **GET /viz/debug/{job_id}** - Get debug visualization

See [Visualization API Documentation](./visualization-api.md) for detailed information.

---

## Topics Discovery

### POST /topics/discover

Discover topics from content sources.

**Request Body:**
```json
{
  "kb_path": "/path/to/kb",
  "docs_path": "/path/to/docs",
  "content": "raw content text",
  "max_topics": 50,
  "min_confidence": 0.7
}
```

**Response:**
```json
{
  "status": "completed",
  "topics": [
    {
      "title": "Python Programming",
      "description": "Topics related to Python development",
      "confidence": 0.85
    }
  ],
  "total_discovered": 125,
  "after_dedup": 50,
  "max_topics": 50
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py discover-topics --kb /path/to/kb --max-topics 50
```

---

### GET /topics/list

List all discovered topics.

**Response:**
```json
{
  "topics": [],
  "total": 0,
  "message": "Topic listing requires vector store implementation"
}
```

---

### GET /topics/{topic_id}

Get details for a specific topic.

**Response:**
```json
{
  "detail": "Topic 'xyz' not found. Topic details require vector store implementation."
}
```

---

## Ingestion Endpoints

### POST /ingest/kb

Ingest knowledge base articles.

**Request Body:**
```json
{
  "path": "/path/to/kb"
}
```

**Response:**
```json
{
  "status": "completed",
  "type": "kb",
  "completed_at": "2024-01-15T10:30:00Z",
  "stats": {
    "files_processed": 150,
    "articles_indexed": 150
  }
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py ingest --kb /path/to/kb
```

---

### POST /ingest/docs

Ingest documentation files.

**Request Body:**
```json
{
  "path": "/path/to/docs"
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py ingest --docs /path/to/docs
```

---

### POST /ingest/api

Ingest API reference documentation.

**Request Body:**
```json
{
  "path": "/path/to/api"
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py ingest --api /path/to/api
```

---

### POST /ingest/blog

Ingest blog posts.

**Request Body:**
```json
{
  "path": "/path/to/blog"
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py ingest --blog /path/to/blog
```

---

### POST /ingest/tutorial

Ingest tutorial content.

**Request Body:**
```json
{
  "path": "/path/to/tutorials"
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py ingest --tutorial /path/to/tutorials
```

---

### POST /ingest/kb/upload

Upload and ingest KB articles.

**Request:** multipart/form-data with files

**Response:**
```json
{
  "status": "completed",
  "files_processed": 10
}
```

---

### GET /ingest/status

Get status of all ingestion operations.

**Response:**
```json
{
  "operations": [],
  "total": 0,
  "active": 0,
  "completed": 0,
  "failed": 0
}
```

---

## Configuration Endpoints

### GET /config/snapshot

Get complete configuration snapshot.

**Response:**
```json
{
  "orchestration": {},
  "agents": {},
  "workflows": {},
  "llm": {},
  "templates": {},
  "system": {},
  "version": "1.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### GET /config/tone

Get tone configuration.

**Response:**
```json
{
  "tone": {
    "professional": true,
    "technical_depth": "advanced",
    "audience": "developers"
  },
  "total_settings": 3
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py config tone
```

---

### GET /config/performance

Get performance configuration.

**Response:**
```json
{
  "performance": {
    "parallel_agents": 5,
    "timeout_seconds": 300,
    "retry_attempts": 3
  },
  "total_settings": 3
}
```

**CLI Equivalent:**
```bash
python ucop_cli.py config performance
```

---

### POST /config/hot-reload

Trigger configuration hot-reload.

**Response:**
```json
{
  "status": "success",
  "reloaded": ["config", "workflows", "agents"],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Debug Endpoints

### GET /debug/system

Get comprehensive system diagnostics.

**Response:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "agents": {
    "total": 28,
    "by_status": {
      "idle": 20,
      "busy": 5,
      "error": 3
    }
  },
  "workflows": {
    "total": 5,
    "workflows": ["default_blog", "kb_processing"]
  },
  "jobs": {
    "total_sessions": 3,
    "active_sessions": 2,
    "paused_sessions": 1
  },
  "resources": {
    "cpu_percent": 45.2,
    "memory_percent": 62.8,
    "disk_percent": 35.1
  },
  "config": {
    "config_exists": true,
    "config_readable": true
  }
}
```

---

### GET /debug/agent/{agent_id}

Get detailed agent debug information.

**Response:**
```json
{
  "agent_id": "outline_creation",
  "status": "idle",
  "last_execution": {
    "timestamp": "2024-01-15T10:28:00Z",
    "duration": 2.3,
    "success": true
  },
  "health": {
    "total_executions": 145,
    "success_rate": 0.98,
    "avg_duration": 2.1
  }
}
```

---

### GET /debug/job/{job_id}

Get detailed job debug information.

**Response:**
```json
{
  "job_id": "job_abc123",
  "sessions": [
    {
      "session_id": "debug_xyz",
      "status": "active",
      "current_step": "content_generation",
      "breakpoint_count": 2,
      "step_history": [
        {
          "step": "outline_creation",
          "timestamp": "2024-01-15T10:28:00Z",
          "status": "completed"
        }
      ]
    }
  ]
}
```

---

### GET /debug/performance

Get system performance profile.

**Response:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "cpu": {
    "percent": 45.2,
    "count": 8,
    "count_logical": 16
  },
  "memory": {
    "percent": 62.8,
    "used_mb": 8192,
    "available_mb": 5120,
    "total_mb": 13312
  },
  "agents": [
    {
      "agent_id": "content_generation",
      "avg_execution_time": 3.8,
      "total_executions": 234
    }
  ],
  "jobs": [
    {
      "job_id": "job_abc123",
      "status": "running",
      "duration": 45.2
    }
  ]
}
```

---

## Agent Endpoints

### GET /agents

List all agents.

**Response:**
```json
{
  "agents": {
    "outline_creation": {
      "name": "Outline Creation",
      "description": "Creates blog post outlines",
      "type": "agent"
    }
  }
}
```

---

### GET /agents/{agent_id}

Get specific agent configuration.

**Response:**
```json
{
  "name": "Outline Creation",
  "description": "Creates blog post outlines",
  "type": "agent",
  "config": {
    "model": "gpt-4",
    "temperature": 0.7
  }
}
```

---

## Workflow Endpoints

### GET /workflows

List all workflows.

**Response:**
```json
{
  "workflows": {
    "default_blog": {
      "name": "Default Blog Generation",
      "steps": 12
    }
  }
}
```

---

### GET /workflows/{workflow_id}

Get specific workflow configuration.

**Response:**
```json
{
  "name": "Default Blog Generation",
  "steps": [
    {
      "id": "outline_creation",
      "agent": "outline_creation",
      "inputs": {}
    }
  ]
}
```

---

### POST /workflows

Create a new workflow.

**Request Body:**
```json
{
  "name": "My Workflow",
  "steps": []
}
```

---

### PUT /workflows/{workflow_id}

Update an existing workflow.

**Request Body:**
```json
{
  "name": "Updated Workflow",
  "steps": []
}
```

---

### DELETE /workflows/{workflow_id}

Delete a workflow.

**Response:**
```json
{
  "message": "Workflow 'my_workflow' deleted successfully"
}
```

---

## Job Endpoints

### POST /jobs

Create a new job.

**Request Body:**
```json
{
  "workflow_id": "default_blog",
  "inputs": {
    "topic": "Python Programming"
  },
  "config_overrides": {}
}
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "workflow_id": "default_blog",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### GET /jobs

List all jobs.

**Query Parameters:**
- `status` (string, optional): Filter by status
- `limit` (int, optional): Maximum number of jobs to return. Default: 100
- `offset` (int, optional): Offset for pagination. Default: 0

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "job_abc123",
      "workflow_id": "default_blog",
      "status": "running",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 145,
  "limit": 100,
  "offset": 0
}
```

---

### GET /jobs/{job_id}

Get job status and details.

**Response:**
```json
{
  "job_id": "job_abc123",
  "workflow_id": "default_blog",
  "status": "running",
  "progress": {
    "current_step": "content_generation",
    "total_steps": 12,
    "completed_steps": 6
  },
  "created_at": "2024-01-15T10:30:00Z",
  "started_at": "2024-01-15T10:30:05Z"
}
```

---

### POST /jobs/{job_id}/pause

Pause a running job.

**Response:**
```json
{
  "message": "Job 'job_abc123' paused successfully"
}
```

---

### POST /jobs/{job_id}/resume

Resume a paused job.

**Response:**
```json
{
  "message": "Job 'job_abc123' resumed successfully"
}
```

---

### POST /jobs/{job_id}/cancel

Cancel a job.

**Response:**
```json
{
  "message": "Job 'job_abc123' cancelled successfully"
}
```

---

## Error Responses

All endpoints return standard HTTP status codes and error responses:

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Status Codes:**
- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Authentication

Currently, no authentication is required. For production deployments, implement authentication at the reverse proxy level.

---

## Rate Limiting

No rate limiting is currently enforced. Consider implementing rate limiting for production deployments.

---

## Versioning

API version: **1.0.0**

The API follows semantic versioning. Breaking changes will increment the major version number.

---

## Client Libraries

### TypeScript/JavaScript

```typescript
import { apiClient } from '@/api/client';

// Get workflows
const workflows = await apiClient.getWorkflowsViz();

// Get metrics
const metrics = await apiClient.getVizMetrics();

// Discover topics
const topics = await apiClient.discoverTopicsAPI({
  content: "Sample text",
  max_topics: 10
});
```

### Python

```python
import requests

base_url = "http://localhost:8080/api"

# Get workflows
response = requests.get(f"{base_url}/viz/workflows")
workflows = response.json()

# Get metrics
response = requests.get(f"{base_url}/viz/metrics")
metrics = response.json()

# Discover topics
response = requests.post(f"{base_url}/topics/discover", json={
    "content": "Sample text",
    "max_topics": 10
})
topics = response.json()
```

---

## WebSocket Endpoints

### WS /ws/monitoring

Real-time monitoring updates.

**Message Format:**
```json
{
  "type": "agent_update",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "agent_id": "outline_creation",
    "status": "busy"
  }
}
```

---

## See Also

- [Visualization API Documentation](./visualization-api.md)
- [Workflow Configuration Guide](./workflow-config.md)
- [Agent Development Guide](./agent-development.md)
