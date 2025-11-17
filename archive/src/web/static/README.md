# UCOP Visual Workflow Editor

React-based visual workflow editor for UCOP with drag-and-drop interface.

## Features

- 🎨 Visual workflow editor with React Flow
- 🔌 Drag-and-drop agent nodes
- 🔗 Connect agents with edges
- 📊 Real-time job status monitoring
- 📡 WebSocket integration for live updates
- 💾 Workflow save/load functionality
- 🔍 Node inspector for configuration
- 📝 Live log viewer

## Setup

```bash
# Install dependencies
npm install

# Development mode (with hot reload)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

## Development

The app runs on port 3000 by default and proxies API requests to the backend on port 8000.

## Production

1. Build the app:
   ```bash
   npm run build
   ```

2. The built files will be in `dist/` directory

3. Start the backend server which serves the static files:
   ```bash
   cd ../../..
   python start_web.py
   ```

4. Open http://localhost:8000 in your browser

## Architecture

- **React 18** - UI framework
- **TypeScript** - Type safety
- **React Flow** - Node-based editor
- **Zustand** - State management
- **Tailwind CSS** - Styling
- **Vite** - Build tool
- **Axios** - HTTP client

## Project Structure

```
src/
├── components/       # React components
│   ├── WorkflowEditor.tsx
│   ├── AgentPalette.tsx
│   ├── JobMonitor.tsx
│   ├── NodeInspector.tsx
│   └── LogViewer.tsx
├── api/             # API client
│   └── client.ts
├── websocket/       # WebSocket connection
│   └── connection.ts
├── hooks/           # Custom hooks
│   ├── useJobUpdates.ts
│   ├── useWorkflows.ts
│   └── useApi.ts
├── store/           # State management
│   └── workflowStore.ts
├── types/           # TypeScript types
│   └── index.ts
└── styles/          # Global styles
    └── index.css
```

## Usage

1. **Select Workflow Template**: Choose a pre-defined workflow from the dropdown
2. **Drag Agents**: Drag agents from the palette onto the canvas
3. **Connect Nodes**: Click and drag from one node to another to create connections
4. **Configure Nodes**: Click a node to see its properties in the inspector
5. **Create Job**: Enter a topic and click "Create Job" to start execution
6. **Monitor Progress**: Watch real-time updates in the job monitor and logs

## API Integration

The frontend communicates with the backend via:
- **REST API** - Job management, workflow templates, agent discovery
- **WebSocket** - Real-time job updates and log streaming
