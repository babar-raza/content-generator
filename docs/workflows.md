# Workflows

## Overview

UCOP workflows are defined using LangGraph, a library for building stateful, multi-actor applications with LLMs. Workflows orchestrate agents in a directed graph where nodes represent agent execution and edges represent data flow.

## Workflow Profiles

### Blog Generation Profile

The primary workflow for converting KB articles to blog posts.

**Graph Structure:**
```
START → Ingestion → Outline → Content Generation → SEO → Publishing → END
                              ↓
                         Code Generation
                              ↓
                         Validation
```

**Agents Involved:**
1. `KBIngestionAgent` - Loads and parses source content
2. `OutlineCreationAgent` - Creates content structure
3. `IntroductionWriterAgent` - Writes introduction
4. `SectionWriterAgent` - Writes body sections (parallel)
5. `ConclusionWriterAgent` - Writes conclusion
6. `CodeGenerationAgent` - Creates code examples (conditional)
7. `CodeValidationAgent` - Validates code (conditional)
8. `KeywordExtractionAgent` - Extracts keywords
9. `KeywordInjectionAgent` - Injects keywords strategically
10. `SEOMetadataAgent` - Generates meta tags
11. `FrontmatterAgent` - Creates frontmatter
12. `GistUploadAgent` - Uploads code to GitHub (conditional)

**Conditional Logic:**
- Code generation only if source contains API examples
- Gist upload only if code was generated
- SEO optimization intensity based on target keyword density

### Research-Augmented Profile

Enhanced workflow with trend research and competitive analysis.

**Additional Agents:**
- `TrendsResearchAgent` - Google Trends keyword research
- `CompetitorAnalysisAgent` - Analyze top-ranking content
- `ContentGapAgent` - Identify missing topics

### Rapid Generation Profile

Streamlined workflow for quick content generation.

**Omitted Steps:**
- Deep research
- Code validation
- Multiple SEO passes

**Use Case:** Draft generation, internal documentation

## Workflow Configuration

Workflows are configured in `config/agents.yaml` and `templates/workflows.yaml`.

### Example Workflow Definition

```yaml
workflows:
  blog_generation:
    name: "Blog Post Generation"
    description: "Convert KB article to SEO-optimized blog post"
    
    steps:
      - id: "ingestion"
        agent: "KBIngestionAgent"
        timeout: 30
        retry: 2
        
      - id: "outline"
        agent: "OutlineCreationAgent"
        depends_on: ["ingestion"]
        timeout: 60
        
      - id: "content"
        agents:
          - "IntroductionWriterAgent"
          - "SectionWriterAgent"
          - "ConclusionWriterAgent"
        depends_on: ["outline"]
        parallel: true
        timeout: 300
        
      - id: "seo"
        agents:
          - "KeywordExtractionAgent"
          - "KeywordInjectionAgent"
          - "SEOMetadataAgent"
        depends_on: ["content"]
        timeout: 120
```

## State Management

### Workflow State Schema

```python
@dataclass
class WorkflowState:
    job_id: str
    input_data: Dict[str, Any]
    current_step: str
    completed_steps: List[str]
    outputs: Dict[str, Any]
    context: Dict[str, Any]
    errors: List[Dict[str, Any]]
    metrics: Dict[str, float]
```

### State Transitions

States flow through the graph with each agent reading from and writing to the state:

```python
def agent_node(state: WorkflowState) -> WorkflowState:
    # Agent reads from state
    input_data = state.outputs.get('previous_agent_output')
    
    # Agent executes
    result = agent.execute(input_data)
    
    # Agent writes to state
    state.outputs[agent.name] = result
    state.completed_steps.append(agent.name)
    
    return state
```

## Checkpointing

### Automatic Checkpoints

Checkpoints are saved after each step:

```python
checkpoint_manager.save(
    job_id=state.job_id,
    step=state.current_step,
    state=state.to_dict()
)
```

### Manual Checkpoints

```bash
# Save checkpoint
python ucop_cli.py checkpoint save --job JOB_ID --name my_checkpoint

# List checkpoints
python ucop_cli.py checkpoint list --job JOB_ID

# Restore from checkpoint
python ucop_cli.py checkpoint restore --job JOB_ID --checkpoint my_checkpoint
```

## Parallel Execution

Agents without dependencies can execute in parallel:

```python
# Sequential
A → B → C → D

# Parallel
    ┌→ B →┐
A →→│→ C →│→→ E
    └→ D →┘
```

**Configuration:**
```yaml
- id: "parallel_content"
  agents: ["Agent1", "Agent2", "Agent3"]
  parallel: true
  max_concurrency: 3
```

## Error Handling

### Retry Strategy

```yaml
retry:
  max_attempts: 3
  backoff: exponential  # or 'linear', 'constant'
  initial_delay: 1
  max_delay: 60
```

### Fallback Agents

```yaml
- id: "content_generation"
  agent: "AdvancedContentAgent"
  fallback: "SimpleContentAgent"
  fallback_on:
    - timeout
    - rate_limit_error
```

### Error Recovery

```python
# On error, workflow can:
1. Retry the failed step
2. Fall back to alternative agent
3. Skip optional step
4. Pause for manual intervention
5. Fail with detailed context
```

## Hot Reload

Workflows can be updated without restarting the system:

```bash
# Enable hot reload
python ucop_cli.py config set workflows.hot_reload true

# Modify workflow definition
vim config/agents.yaml

# Workflows automatically reload on file change
```

## Performance Optimization

### Caching

```yaml
caching:
  enabled: true
  agents:
    - "KeywordExtractionAgent"
    - "SEOMetadataAgent"
  ttl: 3600  # 1 hour
  max_size: 1000  # items
```

### Timeouts

```yaml
timeouts:
  agent: 120        # seconds per agent
  workflow: 1800    # seconds per workflow
  step: 300        # seconds per step
```

### Resource Limits

```yaml
resources:
  max_parallel_agents: 5
  max_memory_per_agent: "2GB"
  max_tokens_per_request: 4000
```

## Monitoring

### Workflow Metrics

- Total execution time
- Per-agent execution time
- Token usage by agent
- Success/failure rates
- Cache hit rates

### Real-Time Monitoring

```bash
# Monitor active workflows
python ucop_cli.py job list --status running

# Watch specific job
python ucop_cli.py job watch JOB_ID

# View workflow metrics
python ucop_cli.py job metrics JOB_ID
```

### Web UI Monitoring

The web UI provides:
- Live workflow graph visualization
- Real-time agent status updates
- Performance metrics dashboard
- Error logs and debugging tools

## Custom Workflows

### Creating a Custom Workflow

1. Define workflow in `templates/workflows.yaml`:

```yaml
my_custom_workflow:
  name: "Custom Content Workflow"
  steps:
    - id: "step1"
      agent: "MyCustomAgent"
    - id: "step2"
      agent: "AnotherAgent"
      depends_on: ["step1"]
```

2. Register custom agents in `src/agents/`:

```python
from src.agents.base import Agent

class MyCustomAgent(Agent):
    def execute(self, input_data):
        # Agent logic
        return result
```

3. Use in CLI or Web UI:

```bash
python ucop_cli.py generate --workflow my_custom_workflow --input data.json
```

## Best Practices

1. **Keep agents focused**: Each agent should do one thing well
2. **Minimize state size**: Only pass necessary data between agents
3. **Use checkpoints**: Enable automatic checkpointing for long workflows
4. **Set appropriate timeouts**: Balance responsiveness with completion
5. **Monitor resource usage**: Track memory and token consumption
6. **Test workflows**: Use the test suite to validate workflow logic
7. **Document dependencies**: Clearly specify agent dependencies
8. **Handle errors gracefully**: Implement retry and fallback strategies
