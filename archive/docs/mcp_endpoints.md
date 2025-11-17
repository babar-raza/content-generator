# MCP Endpoints

## Overview

UCOP implements the Model Context Protocol (MCP) for standardized agent orchestration and external integration.

## Endpoint Reference

### Workflow Endpoints

#### `workflow.execute`

Execute a workflow with given inputs.

**Request:**
```json
{
  "method": "workflow.execute",
  "params": {
    "workflow_id": "blog_generation",
    "inputs": {
      "source_file": "kb_article.md",
      "target_keywords": ["python", "tutorial"]
    },
    "options": {
      "checkpoint_enabled": true,
      "parallel_execution": true
    }
  }
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "started_at": "2024-01-15T10:30:00Z"
}
```

#### `workflow.status`

Get execution status and metrics.

**Request:**
```json
{
  "method": "workflow.status",
  "params": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "current_step": "publishing",
  "completed_steps": ["ingestion", "outline", "content", "seo"],
  "outputs": { ... },
  "metrics": {
    "duration": 125.5,
    "tokens_used": 15420
  }
}
```

### Agent Endpoints

#### `agent.invoke`

Invoke a specific agent directly.

**Request:**
```json
{
  "method": "agent.invoke",
  "params": {
    "agent_id": "KeywordExtractionAgent",
    "input": {
      "content": "Article content here..."
    }
  }
}
```

**Response:**
```json
{
  "agent_id": "KeywordExtractionAgent",
  "output": {
    "keywords": ["python", "tutorial", "beginner"],
    "confidence": 0.89
  },
  "metrics": {
    "execution_time": 2.3,
    "tokens_used": 450
  }
}
```

#### `agent.list`

List all available agents with capabilities.

**Request:**
```json
{
  "method": "agent.list",
  "params": {
    "filter": {
      "category": "content"
    }
  }
}
```

**Response:**
```json
{
  "agents": [
    {
      "id": "OutlineCreationAgent",
      "category": "content",
      "capabilities": ["structure", "planning"],
      "inputs": ["source_content"],
      "outputs": ["outline"]
    }
  ]
}
```

### Checkpoint Endpoints

#### `checkpoint.list`

List available checkpoints for a job.

#### `checkpoint.restore`

Restore workflow from checkpoint.

#### `checkpoint.create`

Manually create a checkpoint.

### Real-Time Endpoints

#### `realtime.subscribe`

Subscribe to real-time updates via WebSocket.

**WebSocket Message:**
```json
{
  "type": "subscribe",
  "channels": ["job:550e8400", "agent:*"]
}
```

**Update Events:**
```json
{
  "type": "agent.completed",
  "data": {
    "agent_id": "OutlineCreationAgent",
    "job_id": "550e8400",
    "output": { ... }
  }
}
```

## Usage Examples

### Python Client

```python
from src.mcp.protocol import MCPClient

client = MCPClient()

# Execute workflow
result = await client.execute_workflow(
    workflow_id="blog_generation",
    inputs={"source_file": "input.md"}
)

# Monitor progress
async for update in client.stream_updates(result.job_id):
    print(f"Progress: {update.progress}%")
```

### CLI Integration

```bash
# MCP endpoints are used internally by CLI
python ucop_cli.py generate --input file.md

# Equivalent to:
# mcp.execute_workflow(workflow="blog_generation", inputs=...)
```

## Error Handling

MCP endpoints return standard error responses:

```json
{
  "error": {
    "code": "AGENT_TIMEOUT",
    "message": "Agent execution exceeded timeout",
    "details": {
      "agent_id": "CodeGenerationAgent",
      "timeout": 120
    }
  }
}
```

## Authentication

MCP endpoints support API key authentication:

```json
{
  "method": "workflow.execute",
  "auth": {
    "type": "api_key",
    "key": "your-api-key"
  },
  "params": { ... }
}
```
