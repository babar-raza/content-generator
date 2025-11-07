# UCOP Web UI

## Overview

The UCOP Web UI provides a real-time dashboard for monitoring and controlling blog generation jobs. It integrates directly with the job execution engine, allowing you to:

- **View all running jobs** - See jobs started from CLI or web
- **Pause/Resume jobs** - Full control over job execution
- **Step through execution** - Debugger-style stepping (into/over/out)
- **Real-time monitoring** - Live console output via WebSocket
- **Pipeline editing** - Add/remove agents dynamically (coming soon)
- **Agent monitoring** - View agent status and outputs

## Quick Start

### Standalone Mode

Start the web UI with integrated job execution engine:

```bash
python start_web_ui.py
```

Then visit: http://localhost:8080

### Integrated with CLI

Run jobs from CLI and monitor them in the web UI:

```bash
# Terminal 1: Start the main system with web UI
python src/main.py --topic "AI in Healthcare" --enable-orchestration --web-ui

# Terminal 2: Open browser to http://localhost:8080
# You'll see your job running in the dashboard
```

## Features

### Dashboard View

- **Jobs Tab**: List of all jobs with status, progress, and controls
- **Agents Tab**: Registered agents and their capabilities
- **Workflows Tab**: Available workflow templates

### Job Detail View

For each job, you can:

1. **Control Execution**
   - Pause: Stop execution at next checkpoint
   - Resume: Continue from paused state (with optional parameter changes)
   - Step: Execute one agent at a time (debugger mode)
   - Cancel: Terminate the job

2. **Monitor Pipeline**
   - Visual pipeline showing agent sequence
   - Color-coded status (pending, running, completed, failed)
   - Add/remove agents dynamically

3. **Live Output**
   - Real-time console showing agent outputs
   - Checkpoint notifications
   - Error messages
   - Agent transitions

4. **Agent Details**
   - Execution times
   - Output sizes
   - Status updates
   - View full outputs

## Architecture

```
┌─────────────┐
│   Browser   │
│  Dashboard  │
└──────┬──────┘
       │ HTTP/WebSocket
       │
┌──────▼──────────────────────────┐
│     FastAPI Web Server          │
│  - REST API endpoints           │
│  - WebSocket (/ws/mesh)         │
│  - Template rendering           │
└──────┬──────────────────────────┘
       │
┌──────▼──────────────────────────┐
│   Job Execution Engine          │
│  - Job lifecycle management     │
│  - Workflow compilation         │
│  - Checkpoint management        │
└──────┬──────────────────────────┘
       │
┌──────▼──────────────────────────┐
│     Job Controller              │
│  - Pause/Resume signals         │
│  - Step execution               │
│  - Parameter injection          │
└──────┬──────────────────────────┘
       │
┌──────▼──────────────────────────┐
│     Agent Execution             │
│  - Interruptible agents         │
│  - Checkpoint awareness         │
│  - Real-time event emission     │
└─────────────────────────────────┘
```

## API Endpoints

### Jobs

- `GET /api/jobs` - List all jobs
- `POST /api/jobs` - Create new job
- `GET /api/jobs/{id}` - Get job details
- `POST /api/jobs/{id}/pause` - Pause job
- `POST /api/jobs/{id}/resume` - Resume job
- `POST /api/jobs/{id}/step` - Step job execution
- `POST /api/jobs/{id}/cancel` - Cancel job

### Agents

- `GET /api/agents` - List registered agents

### Health

- `GET /health` - Service health check

### WebSocket

- `WS /ws/mesh?job={id}` - Real-time job updates

## WebSocket Events

Events sent from server to client:

```json
{
  "type": "NODE.START",
  "timestamp": "2024-11-04T12:00:00Z",
  "job_id": "abc123",
  "data": {
    "node_id": "topic_identification",
    "agent": "TopicIdentificationAgent"
  }
}
```

Event types:
- `RUN.START` - Job execution started
- `NODE.START` - Agent started
- `NODE.STDOUT` - Console output
- `NODE.CHECKPOINT` - Checkpoint reached
- `NODE.OUTPUT` - Agent completed with output
- `NODE.ERROR` - Error occurred
- `RUN.PAUSED` - Job paused
- `RUN.RESUMED` - Job resumed
- `RUN.FINISHED` - Job completed

## Configuration

The web UI uses the same configuration as the main UCOP system:

- Port: 8080 (configurable via environment)
- Job storage: ./jobs/
- Checkpoint storage: ./checkpoints/
- Templates: ./templates/

## Integration with CLI

Jobs started from the CLI are automatically available in the web UI. The shared job execution engine ensures:

1. **Unified state** - CLI and web see the same jobs
2. **Control from anywhere** - Pause a CLI job from the web UI
3. **Persistent jobs** - Jobs survive server restarts
4. **Real-time sync** - Changes propagate instantly

## Development

### Project Structure

```
src/web/
├── __init__.py              # Module exports
├── app.py                   # FastAPI application
├── templates/
│   ├── dashboard.html       # Main dashboard
│   └── job_detail.html      # Job detail view
└── static/
    ├── css/
    │   └── styles.css       # UI styling
    └── js/
        ├── dashboard.js     # Dashboard logic
        └── job_detail.js    # Job detail logic
```

### Adding New Features

1. **Add API endpoint** in `app.py`
2. **Update UI** in HTML/JS files
3. **Add WebSocket events** if needed
4. **Update this README**

## Troubleshooting

### Web UI shows no jobs

- Ensure the execution engine is initialized
- Check `/health` endpoint shows `engine_connected: true`
- Verify jobs directory exists: `./jobs/`

### WebSocket connection fails

- Check browser console for errors
- Ensure job ID is correct in URL
- Verify WebSocket is enabled on server

### Jobs not appearing from CLI

- Make sure CLI is using `--enable-orchestration` flag
- Verify both CLI and web use same jobs directory
- Check for errors in server logs

## Future Enhancements

- [ ] Dynamic pipeline editing
- [ ] Agent parameter tuning UI
- [ ] Workflow designer
- [ ] Performance metrics dashboard
- [ ] Job templates/presets
- [ ] Multi-user support
- [ ] Authentication/authorization

## Support

For issues or questions, check:
- Main documentation: `docs/USER_GUIDE.md`
- Architecture: `docs/ARCHITECTURE.md`
- Orchestration: `OPS_CONSOLE_GUIDE.md`
