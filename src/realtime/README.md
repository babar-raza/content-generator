# Realtime Module

## Overview

Real-time communication infrastructure for WebSocket-based updates and job control.

## Components

### `websocket.py`
WebSocket manager for real-time client communication.

```python
class WebSocketManager:
    """WebSocket connection management"""
    async def connect(self, websocket: WebSocket, client_id: str)
    async def disconnect(self, client_id: str)
    async def broadcast(self, message: Dict)
    async def send_to_client(self, client_id: str, message: Dict)
```

### `job_control.py`
Real-time job control operations.

```python
class JobController:
    """Real-time job control"""
    async def pause_job(self, job_id: str)
    async def resume_job(self, job_id: str)
    async def cancel_job(self, job_id: str)
    async def get_status(self, job_id: str) -> JobStatus
```

## Event Types

### Job Events
- `job.created` - New job created
- `job.started` - Job execution started
- `job.progress` - Progress update
- `job.completed` - Job completed
- `job.failed` - Job failed
- `job.paused` - Job paused
- `job.resumed` - Job resumed
- `job.cancelled` - Job cancelled

### Agent Events
- `agent.started` - Agent execution started
- `agent.completed` - Agent completed
- `agent.failed` - Agent failed
- `agent.output` - Agent output preview

### System Events
- `system.metrics` - System metrics update
- `system.alert` - System alert

## Usage

### Server Side

```python
from src.realtime.websocket import get_ws_manager

ws_manager = get_ws_manager()

# Broadcast to all clients
await ws_manager.broadcast({
    'type': 'job.progress',
    'job_id': job_id,
    'progress': 75
})

# Send to specific client
await ws_manager.send_to_client(client_id, {
    'type': 'job.completed',
    'job_id': job_id,
    'result': {...}
})
```

### Job Control

```python
from src.realtime.job_control import JobController

controller = JobController()

# Pause job
await controller.pause_job(job_id)

# Resume job
await controller.resume_job(job_id)

# Cancel job
await controller.cancel_job(job_id)
```

### Client Side (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
    // Subscribe to job updates
    ws.send(JSON.stringify({
        type: 'subscribe',
        channels: ['job:' + jobId]
    }));
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case 'job.progress':
            updateProgressBar(message.progress);
            break;
        case 'job.completed':
            showResult(message.result);
            break;
        case 'agent.completed':
            updateAgentStatus(message.agent_id);
            break;
    }
};

// Send command
ws.send(JSON.stringify({
    type: 'job.pause',
    job_id: jobId
}));
```

## Message Format

All WebSocket messages follow this format:

```json
{
  "type": "event.type",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "job_id": "...",
    "status": "...",
    ...
  }
}
```

## Connection Management

- Automatic reconnection on disconnect
- Heartbeat/ping-pong for keepalive
- Client identification and authentication
- Channel-based subscriptions

## Dependencies

- `websockets` - WebSocket protocol
- `fastapi` - WebSocket integration
- `src.orchestration` - Job management
- `asyncio` - Async operations
