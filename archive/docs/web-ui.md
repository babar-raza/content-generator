# Web UI Guide

## Overview
React-based web interface with visual workflow editor, real-time job monitoring, and MCP endpoints.

## Accessing the UI
```bash
python start_web.py
# Open http://localhost:8000
```

## Features
- **Visual Workflow Editor**: Drag-and-drop agent palette
- **Job Monitor**: Real-time status updates via WebSocket
- **Agent Dashboard**: View all 38 agents and their status
- **Configuration Inspector**: View current configuration
- **Performance Metrics**: System and agent metrics

## Known Issues
See [design-history.md](design-history.md) for current limitations:
- Some API endpoints unmounted (being fixed)
- Legacy UI components pending decision
- Monitoring dashboard in development

## Building from Source
```bash
cd src/web/static
npm install
npm run build
```
