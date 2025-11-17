# Visual Orchestration

## Overview

The UCOP Web UI provides visual tools for workflow creation, monitoring, and debugging.

## Workflow Editor

### Drag-and-Drop Interface

Create workflows visually by:
1. Dragging agents from the palette
2. Connecting agents with edges
3. Configuring agent parameters
4. Saving workflow definitions

### Agent Palette

Agents are organized by category:
- Content
- SEO
- Code
- Publishing
- Research
- Support

### Connection Rules

- Agents can only connect if output types match input types
- Circular dependencies are prevented
- Parallel execution is automatically detected

## Real-Time Monitoring

### Workflow Graph Visualization

- **Nodes**: Represent agents
- **Edges**: Represent data flow
- **Colors**: Indicate agent status
  - Gray: Pending
  - Blue: Running
  - Green: Completed
  - Red: Failed

### Live Updates

Updates stream via WebSocket:
- Agent start/completion
- Progress percentage
- Output previews
- Error notifications

### Metrics Dashboard

Real-time metrics display:
- Execution time per agent
- Token usage
- Success rates
- System resource utilization

## Debugging Tools

### Breakpoint System

Breakpoint system accessible via `/api/debug/breakpoints` endpoints. See `docs/api/VISUALIZATION_API.md` for API details.

Set breakpoints to pause execution at specific workflow steps and inspect state.

### Step-Through Execution

Execute workflow step-by-step:
1. Set initial breakpoint
2. Inspect state at each step
3. Manually trigger next step
4. Examine outputs

### State Inspector

View complete workflow state:
- Input data
- Intermediate outputs
- Agent context
- Error logs

### Log Viewer

Real-time log streaming:
- Filter by agent
- Filter by log level
- Search capabilities
- Export logs

## Performance Analysis

### Flamegraph View

**Planned feature.** Currently, execution metrics are available via `/api/monitoring/jobs/{job_id}/metrics`.

Will visualize execution time breakdown:
- Agent execution time
- LLM inference time
- Data transfer time
- Idle time

### Bottleneck Detection

**Planned feature.** Currently, manual analysis via monitoring endpoints.

Will automatically identify:
- Slow agents
- Resource constraints
- API rate limits
- Network issues

## Workflow Templates

### Built-In Templates

Pre-configured workflows:
- Blog Generation
- Documentation Creation
- Code Example Generation
- SEO Optimization

### Custom Templates

Save and share custom workflows:
1. Create workflow in editor
2. Test and validate
3. Save as template
4. Export for sharing

## Collaboration Features

### Workflow Sharing

Export workflows as JSON:
```bash
# Export from UI or CLI
python ucop_cli.py workflow export blog_generation > workflow.json
```

### Version Control

Track workflow changes:
- Automatic versioning
- Diff view
- Rollback capability

## Keyboard Shortcuts

- `Ctrl+S`: Save workflow
- `Ctrl+R`: Run workflow
- `Ctrl+D`: Toggle debug mode
- `F5`: Refresh graph
- `Space`: Pause/Resume execution
