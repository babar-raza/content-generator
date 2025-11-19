---
title: "Workflows API Reference"
description: "Complete API reference for workflow management endpoints"
source_url: "https://example.com/api/workflows"
sample_type: "live_fixture"
apiVersion: "v2"
authentication: "Bearer token"
---

## List Workflows

`GET /api/workflows`

Returns all available workflow definitions.

**Response:**
```json
{
  "workflows": [
    {
      "id": "blog_post_generation",
      "name": "Blog Post Generation",
      "description": "Complete blog post with SEO optimization",
      "steps": 8,
      "avg_duration_seconds": 45
    },
    {
      "id": "api_documentation",
      "name": "API Documentation Generator",
      "description": "Generates API docs from OpenAPI specs",
      "steps": 5,
      "avg_duration_seconds": 30
    }
  ],
  "total": 2
}
```

## Get Workflow Details

`GET /api/workflows/{workflow_id}`

Returns detailed workflow definition including steps and dependencies.

**Response:**
```json
{
  "id": "blog_post_generation",
  "name": "Blog Post Generation",
  "version": 2,
  "steps": [
    {
      "id": "topic_identification",
      "agent": "research.topic_identification",
      "depends_on": [],
      "timeout_seconds": 10
    },
    {
      "id": "outline_creation",
      "agent": "content.outline_creation",
      "depends_on": ["topic_identification"],
      "timeout_seconds": 15
    },
    {
      "id": "section_writing",
      "agent": "content.section_writer",
      "depends_on": ["outline_creation"],
      "parallelism": 3,
      "timeout_seconds": 30
    }
  ],
  "checkpoints": {
    "enabled": true,
    "storage_path": ".checkpoints/blog_post",
    "keep_last": 10
  }
}
```

## Execute Workflow

`POST /api/workflows/{workflow_id}/execute`

Submits a new job to execute the specified workflow.

**Request Body:**
```json
{
  "input_params": {
    "topic": "Introduction to Agent Mesh",
    "kb_path": "samples/fixtures/kb/",
    "tone": "professional",
    "target_length": 1500
  },
  "execution_mode": "mesh",
  "checkpoint_mode": "checkpoint"
}
```

**Response:**
```json
{
  "job_id": "a7b3c9d2e1f4",
  "workflow_id": "blog_post_generation",
  "status": "pending",
  "created_at": "2025-01-15T14:30:00Z",
  "links": {
    "self": "/api/jobs/a7b3c9d2e1f4",
    "status": "/api/jobs/a7b3c9d2e1f4/status",
    "events": "/api/jobs/a7b3c9d2e1f4/events",
    "checkpoints": "/api/jobs/a7b3c9d2e1f4/checkpoints"
  }
}
```

## Validate Workflow

`POST /api/workflows/{workflow_id}/validate`

Validates workflow definition without executing.

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    "Agent 'section_writer' has high average latency (>20s)"
  ],
  "dependency_graph": {
    "nodes": 8,
    "edges": 9,
    "cycles": false
  }
}
```

## Error Responses

All error responses follow RFC7807 Problem Details format:

```json
{
  "type": "https://api.ucop.io/errors/workflow-not-found",
  "title": "Workflow Not Found",
  "status": 404,
  "detail": "Workflow 'invalid_id' does not exist",
  "instance": "/api/workflows/invalid_id",
  "trace_id": "7f8a9b0c1d2e3f4g"
}
```

## Rate Limits

- 100 requests per minute per API key
- 10 concurrent workflow executions per API key
- 429 Too Many Requests with `Retry-After` header

## Webhooks

Configure webhooks to receive workflow execution events:

```json
{
  "webhook_url": "https://your-app.com/webhooks/ucop",
  "events": ["workflow.completed", "workflow.failed"],
  "secret": "your-webhook-secret"
}
```

For implementation examples, see `samples/external/api_responses/` directory.
