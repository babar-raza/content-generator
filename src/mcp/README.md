# MCP Module

## Overview

Model Context Protocol (MCP) implementation for standardized agent orchestration and external integration.

## Components

### `protocol.py`
Core MCP protocol implementation.

```python
class MCPProtocol:
    """MCP protocol handler"""
    async def handle_request(self, request: MCPRequest) -> MCPResponse
```

### `adapter.py`
Adapts UCOP agents to MCP interface.

```python
class MCPAdapter:
    """Adapts agents to MCP"""
    def wrap_agent(self, agent: Agent) -> MCPAgent
```

### `config_aware_executor.py`
MCP executor that respects system configuration.

```python
class ConfigAwareExecutor:
    """Config-aware MCP execution"""
    def execute(self, request: MCPRequest) -> MCPResponse
```

### `contracts.py`
MCP interface contracts and types.

```python
@dataclass
class MCPRequest:
    method: str
    params: Dict[str, Any]
    auth: Optional[Auth]

@dataclass
class MCPResponse:
    result: Optional[Dict]
    error: Optional[Error]
```

### `web_adapter.py`
Web-specific MCP adaptations for FastAPI integration.

## MCP Endpoints

### Workflow Endpoints
- `workflow.execute` - Execute a workflow
- `workflow.status` - Get execution status
- `workflow.checkpoint.list` - List checkpoints
- `workflow.checkpoint.restore` - Restore from checkpoint

### Agent Endpoints
- `agent.invoke` - Invoke specific agent
- `agent.list` - List available agents
- `agent.capabilities` - Get agent capabilities

### Real-Time Endpoints
- `realtime.subscribe` - Subscribe to updates
- `realtime.unsubscribe` - Unsubscribe from updates

## Usage

```python
from src.mcp.protocol import MCPProtocol

protocol = MCPProtocol()

# Execute workflow via MCP
response = await protocol.handle_request({
    'method': 'workflow.execute',
    'params': {
        'workflow_id': 'blog_generation',
        'inputs': {'source_file': 'article.md'}
    }
})
```

## Authentication

Supports API key authentication:

```python
request = MCPRequest(
    method='workflow.execute',
    auth={'type': 'api_key', 'key': 'your-key'},
    params={...}
)
```

## Error Handling

Standard error responses:

```json
{
  "error": {
    "code": "AGENT_TIMEOUT",
    "message": "Agent execution exceeded timeout",
    "details": {...}
  }
}
```

## Dependencies

- `src.engine` - Execution engine
- `src.orchestration` - Workflow management
- `fastapi` - Web integration
