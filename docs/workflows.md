# Workflows

## Overview

UCOP workflows orchestrate agents to accomplish content generation tasks. Workflows can be predefined (YAML), dynamic (mesh), or visual (graph editor). All workflows support checkpoints, parallel execution, and error recovery.

## Workflow Concepts

### Workflow Definition

A workflow is a directed acyclic graph (DAG) of agents:

- **Nodes**: Agents that perform specific tasks
- **Edges**: Data flow between agents
- **State**: Accumulated data from agent outputs
- **Checkpoints**: Save points for resume/retry

### Workflow Types

#### 1. Predefined Workflows
**Definition**: YAML files in `config/main.yaml`  
**Use Case**: Production pipelines, repeatable tasks  
**Execution**: LangGraph or sequential engine

#### 2. Mesh Workflows
**Definition**: Dynamic agent discovery  
**Use Case**: Adaptive content generation, research  
**Execution**: Mesh executor with capability routing

#### 3. Visual Workflows
**Definition**: Drag-and-drop graph editor  
**Use Case**: Interactive design, prototyping  
**Execution**: Compiled to LangGraph

## Built-In Workflows

### Default Workflow (Full Blog Generation)

Complete blog post with SEO, code, and validation.

**Duration**: 5-8 minutes  
**Agents**: 18  
**Output**: Blog post with frontmatter, code, SEO metadata

**Steps**:
1. `topic_identification` - Extract topics from KB article
2. `kb_ingestion` - Ingest and create embeddings
3. `api_ingestion` - Load API documentation
4. `blog_ingestion` - Load existing blog posts
5. `duplication_check` - Check for duplicate content
6. `outline_creation` - Generate content outline
7. `introduction_writer` - Write introduction
8. `section_writer` - Write body sections
9. `code_generation` - Generate code examples
10. `code_validation` - Validate code quality
11. `conclusion_writer` - Write conclusion
12. `keyword_extraction` - Extract SEO keywords
13. `keyword_injection` - Inject keywords naturally
14. `seo_metadata` - Generate meta tags
15. `frontmatter` - Create Hugo/Jekyll frontmatter
16. `content_assembly` - Assemble all parts
17. `link_validation` - Validate URLs
18. `file_writer` - Write to disk

**Usage**:
```bash
python ucop_cli.py generate \
    --input input/kb/article.md \
    --workflow default
```

### Quick Draft Workflow

Fast content generation without SEO optimization.

**Duration**: 2-3 minutes  
**Agents**: 7  
**Output**: Basic blog post without SEO

**Steps**:
1. `topic_identification`
2. `kb_ingestion`
3. `outline_creation`
4. `section_writer`
5. `conclusion_writer`
6. `content_assembly`
7. `file_writer`

**Usage**:
```bash
python ucop_cli.py generate \
    --input input/kb/article.md \
    --workflow quick_draft
```

### Code Only Workflow

Generate code examples without blog content.

**Duration**: 3-4 minutes  
**Agents**: 8  
**Output**: Code files with README

**Steps**:
1. `topic_identification`
2. `api_ingestion`
3. `code_generation`
4. `code_validation`
5. `code_splitting`
6. `license_injection`
7. `gist_upload`
8. `file_writer`

**Usage**:
```bash
python ucop_cli.py generate \
    --input input/api/reference.md \
    --workflow code_only
```

## Workflow Execution

### Sequential Execution

Default execution mode - agents run one at a time.

**Configuration**:
```yaml
# config/main.yaml
workflows:
  enable_parallel_execution: false
```

**Advantages**:
- Predictable resource usage
- Easier to debug
- Lower memory footprint

**Disadvantages**:
- Slower execution
- No parallelization benefits

### Parallel Execution

Execute independent agents concurrently.

**Configuration**:
```yaml
# config/main.yaml
workflows:
  enable_parallel_execution: true
  max_parallel_agents: 5
```

**Parallel Groups**:
```python
# Agents that can run in parallel
parallel_groups = [
    ['kb_search_node', 'api_search_node', 'blog_search_node'],
    ['code_generation_node', 'supplementary_content_node']
]
```

**Advantages**:
- Faster execution (2-3x speedup)
- Better resource utilization

**Disadvantages**:
- Higher memory usage
- More complex debugging

### LangGraph Execution

Use LangGraph for workflow orchestration.

**Configuration**:
```yaml
# config/main.yaml
workflows:
  use_langgraph: true
```

**Features**:
- Automatic checkpointing
- State management
- Conditional branching
- Sub-graph support

**Advantages**:
- Built-in state persistence
- Advanced control flow
- Production-ready

**Disadvantages**:
- Additional dependency
- Learning curve

### Mesh Execution

Dynamic agent discovery and execution.

**Configuration**:
```yaml
# config/main.yaml
workflows:
  use_mesh: true

mesh:
  enabled: true
  max_hops: 10
  discovery_method: "capability"
```

**Features**:
- Agents discover each other
- Capability-based routing
- Adaptive workflows

**Use Cases**:
- Research tasks
- Complex reasoning
- Adaptive content generation

## Creating Custom Workflows

### YAML Workflow Definition

Create a workflow in `config/main.yaml`:

```yaml
workflows:
  custom_tutorial:
    name: "Tutorial Generation"
    description: "Generate tutorial with step-by-step instructions"
    
    steps:
      # Ingestion
      - topic_identification
      - kb_ingestion
      - tutorial_ingestion
      - api_ingestion
      
      # Content generation
      - outline_creation
      - introduction_writer
      - section_writer
      
      # Code generation
      - code_generation
      - code_splitting
      - code_validation
      
      # Assembly
      - content_assembly
      - frontmatter
      - file_writer
    
    # Define dependencies
    dependencies:
      outline_creation:
        requires: [topic_identification, kb_ingestion]
      
      section_writer:
        requires: [outline_creation, tutorial_ingestion]
      
      code_generation:
        requires: [api_ingestion]
      
      content_assembly:
        requires: [section_writer, code_validation]
    
    # Parallel execution groups
    parallel_groups:
      - [kb_ingestion, tutorial_ingestion, api_ingestion]
      - [code_generation, introduction_writer]
```

### Programmatic Workflow Definition

Create workflows in Python:

```python
from src.orchestration.workflow_compiler import (
    WorkflowDefinition, WorkflowStep
)

# Define steps
steps = [
    WorkflowStep(
        name="ingest_kb",
        agent_id="ingest_kb_node",
        capabilities=["ingestion"],
        inputs={"kb_file_path": "input.md"},
        retries=3,
        timeout=300
    ),
    WorkflowStep(
        name="create_outline",
        agent_id="create_outline_node",
        capabilities=["content_generation"],
        inputs={"topic": "{{ingest_kb.current_topic}}"},
        retries=2,
        timeout=600
    )
]

# Create workflow definition
workflow = WorkflowDefinition(
    name="custom_workflow",
    version="1.0.0",
    description="Custom content generation",
    steps=steps,
    global_inputs={"config": config},
    error_handling={"on_error": "continue"}
)

# Compile and execute
from src.orchestration.workflow_compiler import WorkflowCompiler
compiler = WorkflowCompiler()
graph = compiler.compile(workflow)
result = graph.invoke({"input": data})
```

### Visual Workflow Creation

Create workflows in the web UI:

1. Navigate to "Workflow Editor"
2. Drag agents from palette to canvas
3. Connect agents with edges
4. Configure agent parameters
5. Add conditional logic
6. Save workflow
7. Execute

## Workflow State Management

### State Structure

```python
{
    "data": {
        "config": {...},
        "current_topic": {...}
    },
    "step_outputs": {
        "ingest_kb_node": {
            "current_topic": {...},
            "ingestion_metadata": {...}
        },
        "outline_creation_node": {
            "outline": {...}
        }
    },
    "current_step": "section_writer_node",
    "completed_steps": ["ingest_kb_node", "outline_creation_node"],
    "failed_steps": [],
    "execution_id": "job_12345",
    "correlation_id": "corr_67890"
}
```

### Accessing State

Agents access state through input parameters:

```python
def section_writer_node(state: WorkflowState) -> Dict:
    # Access previous outputs
    outline = state.step_outputs["outline_creation_node"]["outline"]
    topic = state.data["current_topic"]
    
    # Generate sections
    sections = generate_sections(outline, topic)
    
    # Return output
    return {"sections": sections}
```

### State Persistence

State is automatically persisted at checkpoints:

```python
# Before agent execution
checkpoint_manager.save_checkpoint(
    job_id=job.id,
    checkpoint_id=f"before_{agent_name}",
    state=workflow_state
)

# After agent execution
checkpoint_manager.save_checkpoint(
    job_id=job.id,
    checkpoint_id=f"after_{agent_name}",
    state=workflow_state
)
```

## Conditional Logic

### Conditional Branches

Execute different paths based on conditions:

```yaml
workflows:
  conditional_example:
    steps:
      - topic_identification
      - duplication_check
      
      # Conditional: skip if duplicate
      - name: outline_creation
        condition: "not is_duplicate"
      
      # Alternative path for duplicates
      - name: update_existing
        condition: "is_duplicate"
```

### Conditional Agent Execution

```python
def should_generate_code(state: WorkflowState) -> bool:
    """Determine if code generation is needed."""
    topic = state.data["current_topic"]
    has_api_context = bool(state.step_outputs.get("api_ingestion_node"))
    return topic.get("requires_code", False) and has_api_context

# Use in workflow
WorkflowStep(
    name="code_generation",
    agent_id="code_generation_node",
    condition=should_generate_code
)
```

## Error Handling

### Retry Logic

Agents automatically retry on failure:

```yaml
workflows:
  error_handling_example:
    steps:
      - name: code_generation
        agent_id: code_generation_node
        retries: 3  # Retry up to 3 times
        retry_delay: 60  # Wait 60s between retries
        timeout: 900  # 15 minute timeout
```

### Error Recovery

Recover from failures with fallback logic:

```yaml
workflows:
  fallback_example:
    steps:
      - name: code_generation
        agent_id: code_generation_node
        on_error: fallback_to_simple_code
      
      - name: fallback_to_simple_code
        agent_id: simple_code_generator
        condition: "code_generation_failed"
```

### Circuit Breaker

Prevent cascading failures:

```yaml
mesh:
  circuit_breaker:
    enabled: true
    failure_threshold: 3  # Open after 3 failures
    timeout_seconds: 60   # Stay open for 60s
    success_threshold: 2  # Close after 2 successes
```

## Checkpoints

### Automatic Checkpoints

Created before/after each agent:

```python
# Before agent
checkpoint_id = f"before_{agent_name}_{timestamp}"

# After agent
checkpoint_id = f"after_{agent_name}_{timestamp}"
```

### Manual Checkpoints

Create checkpoints programmatically:

```python
from src.orchestration.checkpoint_manager import CheckpointManager

checkpoint_manager = CheckpointManager()

# Save checkpoint
checkpoint_manager.save_checkpoint(
    job_id="job_12345",
    checkpoint_id="custom_checkpoint",
    state=workflow_state,
    metadata={"description": "Before long operation"}
)

# Restore from checkpoint
restored_state = checkpoint_manager.restore_checkpoint(
    checkpoint_id="custom_checkpoint"
)
```

### Checkpoint CLI

```bash
# List checkpoints
python ucop_cli.py checkpoint list --job job_12345

# Restore from checkpoint
python ucop_cli.py checkpoint restore --id checkpoint_67890

# Delete checkpoint
python ucop_cli.py checkpoint delete --id checkpoint_67890

# Cleanup old checkpoints
python ucop_cli.py checkpoint cleanup --days 7
```

## Workflow Monitoring

### Real-Time Monitoring

Monitor workflow execution via WebSocket:

```python
import asyncio
import websockets

async def monitor_workflow(job_id):
    uri = f"ws://localhost:8000/ws/job/{job_id}"
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            event = json.loads(message)
            
            if event["type"] == "agent_started":
                print(f"Agent started: {event['agent_id']}")
            elif event["type"] == "agent_completed":
                print(f"Agent completed: {event['agent_id']}")
            elif event["type"] == "workflow_completed":
                print("Workflow complete!")
                break

asyncio.run(monitor_workflow("job_12345"))
```

### Job Status

Check job status via CLI:

```bash
# List all jobs
python ucop_cli.py job list

# Get job details
python ucop_cli.py job get --id job_12345

# Filter by status
python ucop_cli.py job list --status running
python ucop_cli.py job list --status completed
python ucop_cli.py job list --status failed
```

### Visualization

Visualize workflow execution:

```bash
# Show workflow graph
python ucop_cli.py viz graph --workflow default

# Show execution trace
python ucop_cli.py viz debug --job job_12345

# Show bottlenecks
python ucop_cli.py viz bottlenecks --workflow default
```

## Performance Optimization

### Parallel Execution

Identify parallelizable agents:

```python
# Agents with no shared dependencies can run in parallel
parallel_groups = [
    ['kb_search_node', 'api_search_node', 'blog_search_node'],
    ['keyword_extraction_node', 'code_validation_node']
]
```

### Caching

Cache agent outputs to avoid re-execution:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_kb_search(query: str):
    return kb_search_node(query)
```

### Resource Limits

Tune agent resource limits:

```yaml
# config/agents.yaml
agents:
  code_generation_node:
    resources:
      max_memory_mb: 4096  # Increase for large codebases
      max_runtime_s: 900   # Allow longer execution
      max_tokens: 16384    # Increase token limit
```

## Best Practices

1. **Start Simple**: Begin with sequential execution, add parallelism later
2. **Use Checkpoints**: Enable automatic checkpointing for production
3. **Monitor Performance**: Track agent latencies, identify bottlenecks
4. **Handle Errors**: Add retry logic and fallback paths
5. **Validate Inputs**: Check agent inputs before execution
6. **Test Workflows**: Validate with small inputs before production
7. **Document Workflows**: Add descriptions and metadata
8. **Version Control**: Track workflow changes in git

## Troubleshooting

### Workflow Fails to Start

```bash
# Check workflow definition
python ucop_cli.py config workflows

# Validate workflow
python tools/validate.py

# Check agent availability
python ucop_cli.py agents list
```

### Agent Timeout

```bash
# Check agent logs
python ucop_cli.py agents logs --agent code_generation_node

# Increase timeout
# Edit config/agents.yaml:
max_runtime_s: 1800  # 30 minutes
```

### Checkpoint Issues

```bash
# List checkpoints
python ucop_cli.py checkpoint list --job job_12345

# Cleanup corrupted checkpoints
python ucop_cli.py checkpoint cleanup --days 0 --force
```

### Memory Issues

```bash
# Reduce parallel execution
# Edit config/main.yaml:
max_parallel_agents: 2

# Reduce agent memory limits
# Edit config/agents.yaml:
max_memory_mb: 1024
```

---

*This documentation is part of the UCOP project. For more information, see the [main README](../README.md).*
