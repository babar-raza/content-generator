# UCOP Visual Editor - Runbook

## Quick Start

```bash
# 1. Navigate to frontend directory
cd src/web/static

# 2. Install dependencies
npm install

# 3. Build production bundle
npm run build

# 4. Go back to project root
cd ../../..

# 5. Start the web server
python start_web.py

# 6. Open browser
# Navigate to: http://localhost:8000
```

## Prerequisites

- Python 3.8+
- Node.js 18+
- npm 9+

## Detailed Setup

### 1. Install Node Dependencies

```bash
cd src/web/static
npm install
```

This installs:
- React 18
- React Flow (node editor)
- Zustand (state management)
- Axios (HTTP client)
- TypeScript
- Vite (build tool)
- Tailwind CSS

### 2. Development Mode (Optional)

For development with hot reload:

```bash
npm run dev
```

This starts Vite dev server on http://localhost:3000 with:
- Hot module replacement
- API proxy to backend (port 8000)
- WebSocket proxy for live updates

### 3. Production Build

```bash
npm run build
```

Output:
- Creates `dist/` directory
- Bundles and minifies all assets
- Optimizes for production
- Generates source maps

Build artifacts:
```
dist/
├── index.html          # Main HTML file
├── assets/             # JS, CSS bundles
│   ├── index-[hash].js
│   └── index-[hash].css
└── vite.svg           # Favicon
```

### 4. Start Backend Server

```bash
cd ../../..  # Back to project root
python start_web.py
```

The server will:
- Initialize job execution engine
- Mount React app static files from `src/web/static/dist/`
- Serve API endpoints at `/api/*`
- Handle WebSocket connections at `/ws/*`
- Serve React app at `/`

### 5. Access the UI

Open browser to: **http://localhost:8000**

You should see:
- Agent palette on the left
- Workflow canvas in center
- Node inspector on top right
- Job monitor on bottom right
- Log viewer at bottom

## Features

### Visual Workflow Editor

1. **Select Workflow Template**
   - Choose from dropdown: `fast-draft` or `full`
   - Loads pre-configured agent pipeline

2. **Drag & Drop Agents**
   - Browse agent palette by category
   - Drag agents onto canvas
   - Position nodes freely

3. **Connect Agents**
   - Click and drag from one node to another
   - Creates data flow connections
   - Validates connection types

4. **Configure Nodes**
   - Click node to select
   - View/edit properties in inspector
   - Set agent parameters

5. **Create Job**
   - Enter topic in control panel
   - Click "Create Job"
   - Job starts executing immediately

6. **Monitor Execution**
   - Real-time status updates via WebSocket
   - Progress bar shows completion
   - Active nodes highlighted
   - Logs stream in bottom panel

### Job Controls

- **Pause** - Temporarily stop job execution
- **Resume** - Continue paused job
- **Cancel** - Stop job permanently
- **Refresh** - Manually update job list

### Real-time Updates

WebSocket connection provides:
- Job status changes
- Agent start/complete notifications
- Progress updates
- Log messages
- Error notifications

### Responsive Design

- Works on desktop and tablet
- Collapsible panels
- Adaptive layout
- Touch-friendly controls

## Troubleshooting

### React app not loading

**Problem**: Blank page or 404 errors

**Solution**:
```bash
cd src/web/static
npm run build
```

Ensure `dist/` directory exists with built files.

### WebSocket not connecting

**Problem**: "Offline" indicator in job monitor

**Causes**:
- Backend not running
- Wrong WebSocket URL
- Firewall blocking port 8000

**Solution**:
- Verify backend running: `curl http://localhost:8000/health`
- Check browser console for errors
- Test WebSocket: `wscat -c ws://localhost:8000/ws/mesh?job=test`

### Agents not loading

**Problem**: Empty agent palette

**Solution**:
- Check backend logs for agent discovery errors
- Verify agent files exist in `src/agents/`
- Test API: `curl http://localhost:8000/api/agents`

### Build errors

**Problem**: `npm run build` fails

**Common issues**:
- Node version < 18: Update Node.js
- Missing dependencies: Run `npm install`
- TypeScript errors: Check `src/` files for type issues

**Clean build**:
```bash
rm -rf node_modules dist
npm install
npm run build
```

### API errors

**Problem**: 503 Service Unavailable

**Cause**: Job execution engine not initialized

**Solution**:
- Check backend startup logs
- Verify database service running
- Ensure all dependencies installed

## Development Workflow

### Make Frontend Changes

1. Edit files in `src/web/static/src/`
2. For dev mode: `npm run dev` (auto-reload)
3. For production: `npm run build`
4. Refresh browser

### Test Changes

```bash
# Run UI contract tests
pytest tests/web/test_ui_contracts.py -v

# Type check
cd src/web/static
npx tsc --noEmit

# Lint
npm run lint
```

### Update Dependencies

```bash
cd src/web/static
npm update
npm audit fix
```

## File Structure

```
src/web/static/
├── package.json           # Dependencies
├── tsconfig.json          # TypeScript config
├── vite.config.ts         # Vite config
├── tailwind.config.js     # Tailwind config
├── index.html             # HTML template
├── src/
│   ├── main.tsx          # Entry point
│   ├── App.tsx           # Main app component
│   ├── components/       # React components
│   ├── api/              # API client
│   ├── websocket/        # WebSocket connection
│   ├── hooks/            # Custom React hooks
│   ├── store/            # Zustand store
│   ├── types/            # TypeScript types
│   └── styles/           # Global CSS
├── dist/                 # Build output (generated)
└── node_modules/         # Dependencies (generated)
```

## Production Deployment

### Build Optimization

The production build includes:
- Code splitting
- Tree shaking
- Minification
- Gzip compression
- Source maps

### Environment Variables

Create `.env.production`:
```
VITE_API_BASE_URL=/api
VITE_WS_URL=ws://localhost:8000/ws
```

### Serve Static Files

FastAPI serves built files from `dist/`:
- `GET /` → `index.html`
- `GET /assets/*` → JS/CSS bundles

### Performance

- Initial load: ~200KB gzipped
- React Flow: Lazy loaded
- WebSocket: Auto-reconnect
- API: Request deduplication

## API Reference

### REST Endpoints

- `GET /api/agents` - List all agents
- `GET /api/jobs` - List all jobs
- `POST /api/jobs` - Create new job
- `GET /api/jobs/{id}` - Get job details
- `POST /api/jobs/{id}/pause` - Pause job
- `POST /api/jobs/{id}/resume` - Resume job
- `POST /api/jobs/{id}/cancel` - Cancel job
- `GET /api/jobs/{id}/logs` - Get job logs

### WebSocket

Connect to: `ws://localhost:8000/ws/mesh?job={job_id}`

Message types:
- `status` - Job status changed
- `progress` - Agent progress update
- `log` - Log message
- `error` - Error occurred
- `agent_start` - Agent started
- `agent_complete` - Agent completed

## Support

For issues:
1. Check browser console for errors
2. Check backend logs
3. Verify API connectivity
4. Test WebSocket connection
5. Review this runbook

## Version Info

- React: 18.2.0
- React Flow: 11.10.4
- TypeScript: 5.3.3
- Vite: 5.0.11
- Tailwind: 3.4.1
