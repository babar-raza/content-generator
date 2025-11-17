# MCP Endpoints Reference

See original documentation at `/home/claude/docs/mcp_endpoints.md` for complete API reference.

## Endpoint Categories
- **Workflow Endpoints**: Execute, status, list
- **Agent Endpoints**: Invoke, list, health
- **Checkpoint Endpoints**: List, restore, create
- **Real-Time Endpoints**: WebSocket subscribe

## Usage
```bash
# Via CLI
python ucop_cli.py agent invoke <agent_id> --input <json>

# Via HTTP
curl -X POST http://localhost:8000/mcp/request \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "agents/invoke", "params": {...}}'
```

## Authentication
MCP endpoints support API key authentication in production.
