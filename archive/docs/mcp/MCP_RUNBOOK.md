# MCP Endpoint Handlers - Runbook

## Overview

Implementation of MCP (Model Context Protocol) endpoint handlers for UCOP.

All MCP operations go through a single POST endpoint: `/api/mcp`

## Quick Start

### 1. Start the server

```bash
python start_web.py
```

### 2. Test MCP endpoint

```bash
curl -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "agent.list",
    "params": {},
    "id": "req_1"
  }'
```

## Supported Methods

### workflow.execute

Execute a workflow.

**Request:**
```bash
curl -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "workflow.execute",
    "params": {
      "workflow_id": "fast-draft",
      "inputs": {
        "topic": "Understanding AI in 2025",
        "output_dir": "./output"
      },
      "checkpoint_enabled": true
    },
    "id": "req_1"
  }'
```

**Response:**
```json
{
  "result": {
    "job_id": "job_20250111_120000_001",
    "workflow_id": "fast-draft",
    "status": "running",
    "started_at": "2025-01-11T12:00:00",
    "uri": "ucop://job/job_20250111_120000_001"
  },
  "id": "req_1"
}
```

### workflow.status

Get workflow execution status.

**Request:**
```bash
curl -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "workflow.status",
    "params": {
      "job_id": "job_20250111_120000_001"
    },
    "id": "req_2"
  }'
```

**Response:**
```json
{
  "result": {
    "job_id": "job_20250111_120000_001",
    "status": "running",
    "workflow_name": "fast-draft",
    "progress": 45,
    "current_step": "write_sections",
    "pipeline": [
      {
        "id": "ingest_kb",
        "name": "Ingest KB",
        "status": "completed"
      },
      {
        "id": "write_sections",
        "name": "Write Sections",
        "status": "running"
      }
    ],
    "started_at": "2025-01-11T12:00:00",
    "uri": "ucop://job/job_20250111_120000_001"
  },
  "id": "req_2"
}
```

### workflow.checkpoint.list

List available checkpoints for a job.

**Request:**
```bash
curl -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "workflow.checkpoint.list",
    "params": {
      "job_id": "job_20250111_120000_001"
    },
    "id": "req_3"
  }'
```

**Response:**
```json
{
  "result": {
    "job_id": "job_20250111_120000_001",
    "checkpoints": [
      {
        "id": "checkpoint_step_5",
        "job_id": "job_20250111_120000_001",
        "step_id": "write_sections",
        "timestamp": "2025-01-11T12:05:00",
        "status": "completed",
        "uri": "ucop://checkpoint/checkpoint_step_5"
      },
      {
        "id": "checkpoint_step_3",
        "job_id": "job_20250111_120000_001",
        "step_id": "create_outline",
        "timestamp": "2025-01-11T12:03:00",
        "status": "completed",
        "uri": "ucop://checkpoint/checkpoint_step_3"
      }
    ]
  },
  "id": "req_3"
}
```

### workflow.checkpoint.restore

Restore workflow from a checkpoint.

**Request:**
```bash
curl -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "workflow.checkpoint.restore",
    "params": {
      "job_id": "job_20250111_120000_001",
      "checkpoint_id": "checkpoint_step_3"
    },
    "id": "req_4"
  }'
```

**Response:**
```json
{
  "result": {
    "job_id": "job_20250111_120000_001",
    "checkpoint_id": "checkpoint_step_3",
    "status": "restored",
    "restored_at": "2025-01-11T12:10:00",
    "checkpoint_step": "create_outline",
    "message": "Job restored from checkpoint successfully"
  },
  "id": "req_4"
}
```

### agent.invoke

Invoke an agent directly.

**Request:**
```bash
curl -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "agent.invoke",
    "params": {
      "agent_id": "topic_identification",
      "input": {
        "kb_path": "./data/kb",
        "min_topics": 3
      },
      "context": {
        "user": "analyst_1"
      }
    },
    "id": "req_5"
  }'
```

**Response:**
```json
{
  "result": {
    "agent_id": "topic_identification",
    "status": "completed",
    "output": {
      "topics": [
        "Machine Learning Trends",
        "Neural Networks",
        "AI Ethics"
      ]
    },
    "executed_at": "2025-01-11T12:15:00",
    "uri": "ucop://agent/topic_identification"
  },
  "id": "req_5"
}
```

### agent.list

List all available agents.

**Request:**
```bash
curl -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "agent.list",
    "params": {},
    "id": "req_6"
  }'
```

**Response:**
```json
{
  "result": {
    "agents": [
      {
        "id": "topic_identification",
        "name": "Topic Identification",
        "type": "research",
        "category": "research",
        "status": "idle",
        "uri": "ucop://agent/topic_identification",
        "capabilities": []
      },
      {
        "id": "kb_search",
        "name": "KB Search",
        "type": "research",
        "category": "research",
        "status": "idle",
        "uri": "ucop://agent/kb_search",
        "capabilities": []
      }
    ],
    "total": 28,
    "category_filter": null
  },
  "id": "req_6"
}
```

**Filter by category:**
```bash
curl -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "agent.list",
    "params": {
      "category": "research"
    },
    "id": "req_7"
  }'
```

### realtime.subscribe

Subscribe to real-time updates via WebSocket.

**Request:**
```bash
curl -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "realtime.subscribe",
    "params": {
      "job_id": "job_20250111_120000_001",
      "event_types": ["status", "progress", "log", "error"]
    },
    "id": "req_8"
  }'
```

**Response:**
```json
{
  "result": {
    "job_id": "job_20250111_120000_001",
    "subscription_id": "sub_job_20250111_120000_001_20250111_121000",
    "event_types": ["status", "progress", "log", "error"],
    "websocket_url": "ws://localhost:8000/ws/mesh?job=job_20250111_120000_001",
    "status": "ready",
    "message": "Connect to the WebSocket URL to receive real-time updates"
  },
  "id": "req_8"
}
```

**Connect to WebSocket:**
```bash
# Using wscat
wscat -c "ws://localhost:8000/ws/mesh?job=job_20250111_120000_001"

# Or using Python
import websocket
ws = websocket.WebSocket()
ws.connect("ws://localhost:8000/ws/mesh?job=job_20250111_120000_001")
message = ws.recv()
print(message)
```

## Error Responses

### Invalid Method

**Request:**
```json
{
  "method": "invalid.method",
  "params": {},
  "id": "req_error_1"
}
```

**Response:**
```json
{
  "error": {
    "code": -32601,
    "message": "Method not found: invalid.method"
  },
  "id": "req_error_1"
}
```

### Invalid Parameters

**Request:**
```json
{
  "method": "workflow.execute",
  "params": {},
  "id": "req_error_2"
}
```

**Response:**
```json
{
  "error": {
    "code": -32602,
    "message": "Invalid params: workflow_id is required"
  },
  "id": "req_error_2"
}
```

### Internal Error

**Response:**
```json
{
  "error": {
    "code": -32603,
    "message": "Internal error: Database connection failed"
  },
  "id": "req_error_3"
}
```

## Error Codes

Standard JSON-RPC 2.0 error codes:

- `-32600`: Invalid Request
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error
- `-32700`: Parse error

## Testing

### Run Tests

```bash
# Run all MCP tests
pytest tests/test_mcp_integration.py -v

# Run specific test class
pytest tests/test_mcp_integration.py::TestWorkflowExecute -v

# Run specific test
pytest tests/test_mcp_integration.py::TestWorkflowExecute::test_execute_workflow_success -v

# Run with coverage
pytest tests/test_mcp_integration.py --cov=src.mcp --cov-report=html
```

### Manual Testing

```bash
# List available methods
curl http://localhost:8000/api/mcp/methods

# Check MCP status
curl http://localhost:8000/api/mcp/status

# List agents
curl -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "agent.list", "params": {}, "id": "test_1"}'

# Execute workflow
curl -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "workflow.execute",
    "params": {
      "workflow_id": "fast-draft",
      "inputs": {"topic": "Test"}
    },
    "id": "test_2"
  }'
```

## Python Client Example

```python
import requests

class MCPClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.request_id = 0
    
    def call(self, method, params=None):
        self.request_id += 1
        response = requests.post(
            f"{self.base_url}/api/mcp",
            json={
                "method": method,
                "params": params or {},
                "id": f"req_{self.request_id}"
            }
        )
        return response.json()
    
    def list_agents(self, category=None):
        params = {"category": category} if category else {}
        return self.call("agent.list", params)
    
    def execute_workflow(self, workflow_id, inputs):
        return self.call("workflow.execute", {
            "workflow_id": workflow_id,
            "inputs": inputs
        })
    
    def get_status(self, job_id):
        return self.call("workflow.status", {"job_id": job_id})

# Usage
client = MCPClient()

# List all agents
agents = client.list_agents()
print(f"Found {agents['result']['total']} agents")

# Execute workflow
result = client.execute_workflow("fast-draft", {"topic": "AI Trends"})
job_id = result["result"]["job_id"]
print(f"Started job: {job_id}")

# Check status
status = client.get_status(job_id)
print(f"Job status: {status['result']['status']}")
```

## Integration with Existing Systems

### FastAPI Integration

The MCP route is already integrated in `src/web/routes/mcp.py`.

To add to your FastAPI app:

```python
from fastapi import FastAPI
from src.web.routes.mcp import router as mcp_router
from src.mcp.protocol import MCPProtocol

app = FastAPI()
app.include_router(mcp_router)

# Initialize MCP protocol
from src.web.routes.mcp import set_protocol
protocol = MCPProtocol(executor=your_executor, job_engine=your_job_engine)
set_protocol(protocol)
```

### CLI Integration

```python
from src.mcp.protocol import MCPRequest, MCPProtocol

# Create protocol
protocol = MCPProtocol(executor=executor)

# Create request
request = MCPRequest(
    method="workflow.execute",
    params={"workflow_id": "fast-draft", "inputs": {"topic": "Test"}},
    id="cli_req_1"
)

# Handle request
response = await protocol.handle_request(request)

if response.error:
    print(f"Error: {response.error['message']}")
else:
    print(f"Result: {response.result}")
```

## Troubleshooting

### MCP endpoint returns 503

**Problem:** Protocol not initialized

**Solution:**
```python
from src.web.routes.mcp import set_protocol
from src.mcp.protocol import MCPProtocol

protocol = MCPProtocol(executor=executor)
set_protocol(protocol)
```

### Workflow execution fails

**Problem:** Executor not configured

**Solution:** Ensure executor is passed to MCPProtocol:
```python
protocol = MCPProtocol(
    executor=executor,
    job_engine=job_engine,
    agent_registry=registry
)
```

### Checkpoints not found

**Problem:** Checkpoint directory doesn't exist

**Solution:** Ensure data directory structure:
```bash
mkdir -p ./data/jobs/{job_id}/checkpoints
```

### Agent invoke fails

**Problem:** Agent not found in registry

**Solution:** Check agent discovery:
```bash
curl -X POST http://localhost:8000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "agent.list", "params": {}, "id": "1"}'
```

## Performance

- All handlers are async
- Minimal overhead (~1-2ms per request)
- Supports concurrent requests
- WebSocket for real-time updates

## Security

- No authentication implemented (add as needed)
- Input validation on all params
- Error messages sanitized
- Rate limiting recommended for production

## Monitoring

### Logging

All MCP calls are logged:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

Log format:
```
INFO:src.mcp.handlers:MCP: workflow.execute called with params: {...}
INFO:src.mcp.handlers:MCP: agent.list called with params: {...}
```

### Metrics

Track MCP metrics:
- Request count by method
- Error rate by method
- Response time per method

## Production Checklist

- [ ] Set up proper logging
- [ ] Add authentication
- [ ] Implement rate limiting
- [ ] Configure CORS
- [ ] Set up monitoring
- [ ] Add health checks
- [ ] Configure timeouts
- [ ] Set up backup for checkpoints
- [ ] Test error handling
- [ ] Document API for clients

## Support

For issues:
1. Check server logs
2. Verify protocol initialization
3. Test with curl
4. Run integration tests
5. Check this runbook
