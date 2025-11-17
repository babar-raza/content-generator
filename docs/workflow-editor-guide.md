# Workflow Editor Guide

## Overview

The Visual Workflow Editor provides an intuitive drag-and-drop interface for creating and managing agent-based workflows. It allows you to visually design complex workflows without writing YAML configuration files manually.

## Features

- **Visual Workflow Design**: Drag and drop agents onto a canvas to create workflows
- **Real-time Validation**: Instant feedback on workflow validity with error and warning messages
- **Node Configuration**: Edit agent parameters, inputs, outputs, and configuration
- **Connection Management**: Visually connect agents to define execution flow
- **Save/Load**: Persist workflows to YAML format and load them for editing
- **Test Run**: Validate workflows before deployment
- **Version Control**: Track workflow changes over time

## Getting Started

### Accessing the Editor

Navigate to `http://localhost:8080/workflow-editor` after starting the web server:

```bash
python start_web.py
```

### Creating a New Workflow

1. Click "New Workflow" or select "+ Create New" from the workflow dropdown
2. Enter a workflow name in the header
3. (Optional) Add a description
4. Start adding agents from the palette

### Adding Agents

1. **From the Agent Palette**: 
   - Browse agents by category (Ingestion, Research, Content, etc.)
   - Use the search box to filter agents
   - Drag an agent from the palette onto the canvas

2. **Agent Categories**:
   - 📥 **Ingestion**: KB ingestion, content extraction
   - 🔍 **Research**: Web search, source analysis
   - ✍️ **Content**: Outline creation, content writing
   - 💻 **Code**: Code analysis, code generation
   - 📊 **SEO**: Keyword research, optimization
   - 🚀 **Publishing**: Content validation, publishing

### Connecting Agents

1. Click and drag from the output handle (right side) of one agent
2. Connect to the input handle (left side) of another agent
3. The connection defines the execution order and data flow

### Editing Node Properties

Double-click on any agent node to open the Node Editor:

- **Display Name**: Custom label for the node
- **Agent**: Select the agent type
- **Action**: Specify agent action (e.g., "gather_sources", "create_outline")
- **Inputs**: Define input parameters (list)
- **Outputs**: Define output parameters (list)
- **Configuration**: JSON configuration for the agent
- **Parameters**: Additional parameters in JSON format

Example Configuration:
```json
{
  "model": "gemini-1.5-flash",
  "temperature": 0.7,
  "max_tokens": 2000
}
```

Example Parameters:
```json
{
  "format": "markdown",
  "include_sources": true
}
```

### Validation

The validation panel at the bottom shows:

- ✅ **Success**: Workflow is valid and ready to save/run
- ⚠️ **Warnings**: Issues that won't prevent execution but should be reviewed
  - Disconnected nodes
  - Missing recommended configurations
- ❌ **Errors**: Issues that must be fixed before saving/running
  - Circular dependencies
  - Missing agent assignments
  - Invalid node configurations

Common validation errors:

1. **Circular Dependencies**: When agents form a loop (A → B → C → A)
   - **Fix**: Reorganize the workflow to eliminate cycles

2. **Missing Agent ID**: When a node doesn't have an agent assigned
   - **Fix**: Double-click the node and select an agent

3. **Disconnected Nodes**: Nodes with no connections
   - **Fix**: Either connect the nodes or remove them

### Saving Workflows

1. Enter a workflow name and description (optional)
2. Ensure validation passes (no errors)
3. Click the "Save" button
4. Workflow is saved to `templates/workflows.yaml`

The workflow ID is automatically generated from the name (lowercase with underscores).

### Loading Existing Workflows

1. Use the workflow dropdown in the header
2. Select a workflow to load
3. The canvas will populate with the workflow's nodes and connections
4. Edit as needed and save

### Test Running

Before deploying a workflow:

1. Click "Test Run" button
2. The system validates the workflow structure
3. Provides feedback on potential issues
4. Does NOT execute agents (dry run)

## Workflow Structure

### Visual Format (JSON)

The editor works with a JSON representation:

```json
{
  "id": "my_workflow",
  "name": "My Workflow",
  "description": "A sample workflow",
  "nodes": [
    {
      "id": "node-1",
      "type": "default",
      "position": { "x": 100, "y": 100 },
      "data": {
        "label": "KB Ingestion",
        "agentId": "kb_ingestion",
        "config": {},
        "params": {}
      }
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "node-1",
      "target": "node-2"
    }
  ]
}
```

### Storage Format (YAML)

Workflows are stored in YAML format:

```yaml
workflows:
  my_workflow:
    name: "My Workflow"
    description: "A sample workflow"
    steps:
      - agent: kb_ingestion
        action: process
        inputs:
          - kb_path
        outputs:
          - processed_content
      - agent: outline_creation
        action: create_outline
        depends_on:
          - kb_ingestion
        inputs:
          - processed_content
        outputs:
          - outline
    metadata:
      category: custom
      version: "1.0"
```

## API Endpoints

### List Workflows
```http
GET /api/workflows/editor/list
```

Response:
```json
{
  "workflows": [
    {
      "id": "workflow_1",
      "name": "Workflow 1",
      "description": "...",
      "metadata": {}
    }
  ],
  "total": 1
}
```

### Get Workflow
```http
GET /api/workflows/editor/{workflow_id}
```

Response: Workflow in visual JSON format

### Save Workflow
```http
POST /api/workflows/editor/save
Content-Type: application/json

{
  "id": "my_workflow",
  "name": "My Workflow",
  "nodes": [...],
  "edges": [...]
}
```

Response:
```json
{
  "status": "success",
  "id": "my_workflow",
  "message": "Workflow saved successfully"
}
```

### Validate Workflow
```http
POST /api/workflows/editor/validate
Content-Type: application/json

{
  "id": "my_workflow",
  "name": "My Workflow",
  "nodes": [...],
  "edges": [...]
}
```

Response:
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

### Test Run Workflow
```http
POST /api/workflows/editor/test-run
Content-Type: application/json

{
  "id": "my_workflow",
  "name": "My Workflow",
  "nodes": [...],
  "edges": [...]
}
```

Response:
```json
{
  "status": "success",
  "message": "Workflow validation passed",
  "workflow_id": "my_workflow",
  "steps": 5
}
```

## Best Practices

### Workflow Design

1. **Start Simple**: Begin with a linear workflow and add complexity as needed
2. **Name Clearly**: Use descriptive names for workflows and nodes
3. **Document**: Add descriptions to explain workflow purpose
4. **Validate Often**: Check validation panel regularly while building

### Node Configuration

1. **Minimal Config**: Only add configuration that differs from defaults
2. **JSON Validation**: Ensure JSON is valid before saving
3. **Input/Output Clarity**: Clearly define what each node expects and produces

### Connection Best Practices

1. **Logical Flow**: Connect nodes in a logical execution order
2. **Avoid Cycles**: Ensure workflows are acyclic (no loops)
3. **Data Flow**: Consider what data each connection represents

### Performance

1. **Parallel Execution**: Nodes without dependencies can run in parallel
2. **Async Agents**: Prefer async agents for I/O-bound operations
3. **Resource Limits**: Be mindful of agent resource requirements

## Troubleshooting

### Workflow Won't Save

**Problem**: Save button is disabled
- **Check**: Validation panel for errors
- **Fix**: Resolve all validation errors
- **Check**: Workflow name is filled in
- **Fix**: Add a name to the workflow

### Agents Not Appearing

**Problem**: Agent palette is empty
- **Check**: Web server is running
- **Check**: Agent registry is properly initialized
- **Fix**: Restart the web server

### Connections Won't Create

**Problem**: Can't connect two nodes
- **Check**: Trying to connect from output (right) to input (left)
- **Check**: Not trying to connect a node to itself
- **Fix**: Verify connection direction

### Workflow Execution Fails

**Problem**: Test run or actual execution fails
- **Check**: All nodes have valid agent assignments
- **Check**: Agent contracts match connections
- **Fix**: Review agent input/output requirements

## Advanced Features

### Custom Agent Configuration

You can customize agent behavior per node:

```json
{
  "model": "gemini-1.5-pro",
  "temperature": 0.9,
  "max_retries": 5,
  "timeout": 600
}
```

### Conditional Execution

Use configuration to control execution:

```json
{
  "condition": {
    "field": "content_length",
    "operator": "greater_than",
    "value": 1000
  }
}
```

### Error Handling

Configure error handling per node:

```json
{
  "on_error": "continue",
  "fallback_agent": "fallback_content_agent",
  "max_retries": 3
}
```

## Integration with CLI

Workflows created in the editor can be used from the CLI:

```bash
# List workflows
python ucop_cli.py viz workflows

# Execute a workflow created in the editor
python ucop_cli.py generate \
  --input kb.md \
  --output output/ \
  --workflow my_workflow
```

## Keyboard Shortcuts

- **Delete**: Remove selected node or edge
- **Ctrl+Z**: Undo (browser-level)
- **Ctrl+S**: Save workflow
- **Escape**: Deselect all

## Support

For issues or questions:

1. Check the validation panel for guidance
2. Review this documentation
3. Check agent contracts and capabilities
4. Consult the main UCOP documentation

## Examples

### Example 1: Simple Blog Generation

```
[KB Ingestion] → [Outline Creation] → [Content Writing] → [SEO Optimization]
```

Steps:
1. Add KB Ingestion agent
2. Add Outline Creation agent
3. Connect KB Ingestion → Outline Creation
4. Add Content Writing agent
5. Connect Outline Creation → Content Writing
6. Add SEO Optimization agent
7. Connect Content Writing → SEO Optimization
8. Save as "simple_blog_workflow"

### Example 2: Research Pipeline

```
[Web Search]
    ↓
[Source Analysis]
    ↓
[Synthesis] ← [Expert Review]
    ↓
[Report Generation]
```

This workflow includes parallel paths and complex data flow.

### Example 3: Multi-Format Output

```
[Content Generation]
    ├→ [Markdown Formatter]
    ├→ [HTML Formatter]
    └→ [PDF Generator]
```

Parallel execution for multiple output formats.

## Changelog

### Version 1.0.0
- Initial release
- Visual workflow editor
- Drag-and-drop interface
- Real-time validation
- Save/load functionality
- Test run capability
- Full API support
