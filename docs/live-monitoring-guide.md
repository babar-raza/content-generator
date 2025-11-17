# Live Flow Monitoring Guide

## Overview

The Live Flow Monitoring system provides real-time visualization of agent execution during workflow runs. It uses WebSocket connections to stream execution events from the backend to the UI, enabling developers and operators to monitor job progress, debug issues, and understand system behavior.

## Architecture

### Components

1. **WebSocket Handler** (`src/web/websocket_handlers.py`)
   - Manages WebSocket connections for each job
   - Subscribes to event bus for execution events
   - Broadcasts events to connected clients

2. **Event Emission** (`src/orchestration/production_execution_engine.py`)
   - Emits events during agent execution lifecycle
   - Events: `agent_started`, `agent_completed`, `agent_failed`, `data_flow`

3. **React Components** (`src/web/static/src/components/live/`)
   - `LiveWorkflowCanvas`: Main visualization canvas
   - `AgentStatusIndicator`: Shows agent execution status
   - `DataFlowAnimation`: Animates data passing between agents
   - `ExecutionTimeline`: Timeline view of agent execution
   - `DataInspector`: Inspect agent input/output data

4. **WebSocket Client** (`src/web/static/src/websocket/liveFlow.ts`)
   - React hook for WebSocket connections
   - Handles reconnection and message parsing

## Usage

### Starting Live Monitoring

1. **Start the web server**:
   ```bash
   python start_web.py
   ```

2. **Navigate to Live Flow page**:
   ```
   http://127.0.0.1:8080/live-flow
   ```

3. **Select a job to monitor**:
   - Choose from active or queued jobs in the dropdown
   - The workflow visualization will update in real-time

### Monitoring Features

#### 1. Workflow Visualization
- **Visual nodes** for each agent in the workflow
- **Color-coded status**:
  - Gray: Pending
  - Blue: Running (with spinner)
  - Green: Completed
  - Red: Failed
- **Execution time** displayed for completed agents

#### 2. Data Flow Animation
- Green particles animate between agents
- Shows data passing in real-time
- Smooth cubic-bezier easing

#### 3. Execution Timeline
- Chronological list of agent executions
- Shows current running agent
- Displays duration for completed agents
- Progress indicators

#### 4. Data Inspector
- View input data for agents
- View output data when complete
- JSON viewer with syntax highlighting
- Error details for failed agents

### WebSocket Events

The system emits the following event types:

#### `connected`
Sent when WebSocket connection is established.
```json
{
  "type": "connected",
  "job_id": "job-123",
  "timestamp": "2024-11-17T10:30:00Z"
}
```

#### `agent_started`
Sent when an agent begins execution.
```json
{
  "type": "agent_started",
  "agent_id": "topic_identification",
  "timestamp": "2024-11-17T10:30:01Z",
  "correlation_id": "job-123"
}
```

#### `agent_completed`
Sent when an agent completes successfully.
```json
{
  "type": "agent_completed",
  "agent_id": "topic_identification",
  "output": { "topic": "Python Testing" },
  "duration": 2.5,
  "timestamp": "2024-11-17T10:30:03Z",
  "correlation_id": "job-123"
}
```

#### `agent_failed`
Sent when an agent fails.
```json
{
  "type": "agent_failed",
  "agent_id": "section_writer",
  "error": "Invalid input format",
  "timestamp": "2024-11-17T10:30:05Z",
  "correlation_id": "job-123"
}
```

#### `data_flow`
Sent when data passes between agents.
```json
{
  "type": "data_flow",
  "from_agent": "topic_identification",
  "to_agent": "kb_ingestion",
  "data_size": 245,
  "timestamp": "2024-11-17T10:30:04Z",
  "correlation_id": "job-123"
}
```

#### `progress_update`
Sent for overall progress updates.
```json
{
  "type": "progress_update",
  "progress": 50,
  "message": "Processing sections",
  "timestamp": "2024-11-17T10:30:06Z",
  "correlation_id": "job-123"
}
```

## Development

### Adding New Event Types

1. **Define event in execution engine**:
   ```python
   self.event_bus.publish(AgentEvent(
       event_type="my_custom_event",
       data={"key": "value"},
       source_agent="agent_name",
       correlation_id=job_id,
       metadata={"job_id": job_id}
   ))
   ```

2. **Subscribe in WebSocket handler**:
   ```python
   def __init__(self):
       # ... existing code
       self.event_bus.subscribe("my_custom_event", self._on_custom_event)
   
   def _on_custom_event(self, event: AgentEvent):
       job_id = event.metadata.get("job_id")
       if not job_id:
           return
       
       message = {
           "type": "my_custom_event",
           "data": event.data,
           # ... more fields
       }
       asyncio.create_task(self._broadcast(job_id, message))
   ```

3. **Handle in React component**:
   ```typescript
   useEffect(() => {
       if (!lastMessage) return;
       
       if (lastMessage.type === 'my_custom_event') {
           // Handle the event
           console.log('Custom event:', lastMessage);
       }
   }, [lastMessage]);
   ```

### Testing WebSocket Connections

Using `wscat`:
```bash
# Install wscat
npm install -g wscat

# Connect to live flow WebSocket
wscat -c ws://127.0.0.1:8080/ws/live-flow/job-123

# You'll receive events as they happen
```

Using Python:
```python
import asyncio
import websockets
import json

async def monitor_job(job_id):
    uri = f"ws://127.0.0.1:8080/ws/live-flow/{job_id}"
    
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            event = json.loads(message)
            print(f"Event: {event['type']}")
            print(json.dumps(event, indent=2))

asyncio.run(monitor_job("job-123"))
```

## Performance Considerations

### Event Emission Overhead

The live monitoring system adds minimal overhead to job execution:
- Event creation: < 0.1ms per event
- Event bus publish: < 0.5ms per event
- Total overhead: < 5% of execution time

### WebSocket Connection Limits

- Each job can have unlimited WebSocket connections
- Connections are cleaned up automatically on disconnect
- Reconnection with exponential backoff (max 10 attempts)

### Memory Usage

- Event history not stored in WebSocket handler
- Only active connections consume memory
- Approximately 10KB per active connection

## Troubleshooting

### Connection Refused
- Ensure web server is running
- Check firewall settings
- Verify port 8080 is not blocked

### Events Not Received
- Verify job is actually running
- Check job_id is correct
- Ensure event bus is initialized in executor
- Check browser console for WebSocket errors

### Slow Updates
- Check network latency
- Verify server performance
- Look for excessive event emission

### Disconnections
- Normal for long-running jobs (keep-alive ping/pong)
- Auto-reconnection should handle temporary issues
- Check server logs for errors

## Best Practices

1. **Use for development and debugging**: Live monitoring is best for development environments
2. **Monitor critical jobs**: Use for important production jobs to detect issues early
3. **Limit concurrent connections**: Don't open too many browser tabs monitoring same job
4. **Close connections**: Close browser tabs when done monitoring to free resources
5. **Check console**: Browser console shows WebSocket connection status and errors

## API Reference

### WebSocket Endpoint

```
ws://localhost:8080/ws/live-flow/{job_id}
```

**Parameters**:
- `job_id` (string): Job identifier to monitor

**Protocol**:
- Client connects to endpoint
- Server sends `connected` event
- Server sends execution events as they occur
- Client can send `ping` to test connection (server responds with `pong`)
- Connection closes when client disconnects or job completes

### React Hook

```typescript
import { useWebSocket } from '@/websocket/liveFlow';

const { socket, isConnected, lastMessage, sendMessage, disconnect } = useWebSocket(wsUrl);
```

**Returns**:
- `socket`: WebSocket instance
- `isConnected`: boolean indicating connection status
- `lastMessage`: Last received message
- `sendMessage`: Function to send message to server
- `disconnect`: Function to close connection

## Future Enhancements

Potential improvements for the live monitoring system:

1. **Replay capability**: Record and replay job executions
2. **Metrics dashboard**: Real-time performance metrics
3. **Alert system**: Notifications for failures or slow agents
4. **Filtering**: Filter events by agent or type
5. **Multiple job view**: Monitor multiple jobs simultaneously
6. **Export**: Export execution traces for analysis
7. **Annotations**: Add notes during monitoring
8. **Breakpoints**: Pause execution at specific agents (debug mode)

## Support

For issues or questions:
1. Check browser console for errors
2. Check server logs: `tail -f logs/web.log`
3. Review WebSocket connection in browser DevTools (Network tab)
4. Verify event emission in production_execution_engine.py

---

**Last Updated**: November 2024
**Version**: 1.0.0
