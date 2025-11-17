# Mesh Orchestration Mode

## Overview

Mesh orchestration is a dynamic agent execution mode that enables agents to discover and request services from other agents on-demand. Unlike predefined workflow mode where agent execution order is fixed, mesh mode allows agents to adaptively determine which other agents they need based on runtime context.

## Key Concepts

### Agent Registry
Central registry that maintains information about all available agents, their capabilities, health status, and current load.

### Mesh Router
Routes agent service requests to appropriate agents based on capabilities, handles load balancing, prevents circular dependencies, and manages circuit breaking for failed agents.

### Capability-Based Discovery
Agents are discovered and selected based on declared capabilities rather than explicit agent IDs, enabling flexible and adaptive workflows.

### Dynamic Execution Flow
Instead of following a predefined sequence, agents request services from other agents as needed, creating a demand-driven execution graph.

## Architecture

```
┌─────────────────────────────────────────┐
│     MeshExecutor                         │
│  - execute_mesh_workflow()               │
│  - discover_agents()                     │
│  - list_agents()                         │
└─────────────┬───────────────────────────┘
              │
              ├──────> AgentRegistry
              │        - register_agent()
              │        - find_by_capability()
              │        - update_health()
              │        - update_load()
              │
              └──────> MeshRouter
                       - route_to_agent()
                       - detect_cycles()
                       - circuit_breaker
```

## Configuration

Enable mesh orchestration in `config/main.yaml`:

```yaml
# Mesh orchestration configuration
mesh:
  enabled: true
  max_hops: 10
  routing_timeout_seconds: 5
  discovery_method: "capability"
  circuit_breaker:
    enabled: true
    failure_threshold: 3
    timeout_seconds: 60
```

### Configuration Options

- **enabled**: Enable/disable mesh orchestration mode
- **max_hops**: Maximum number of agent hops allowed (prevents infinite loops)
- **routing_timeout_seconds**: Timeout for routing requests
- **discovery_method**: Agent discovery method ("capability" or "explicit")
- **circuit_breaker.enabled**: Enable circuit breaker for failed agents
- **circuit_breaker.failure_threshold**: Number of failures before circuit opens
- **circuit_breaker.timeout_seconds**: Time before circuit breaker resets

## CLI Usage

### Discover Agents

```bash
# Discover and list available agents
python ucop_cli.py mesh discover-agents

# JSON output
python ucop_cli.py mesh discover-agents --format json
```

### Execute Mesh Workflow

```bash
# Execute workflow starting with topic_identification agent
python ucop_cli.py mesh execute \
  --initial-agent topic_identification \
  --input tests/fixtures/sample_kb.md

# JSON output
python ucop_cli.py mesh execute \
  --initial-agent topic_identification \
  --input input.md \
  --format json
```

### List Registered Agents

```bash
# List all registered mesh agents
python ucop_cli.py mesh list-agents

# JSON output
python ucop_cli.py mesh list-agents --format json
```

### View Statistics

```bash
# View mesh orchestration statistics
python ucop_cli.py mesh stats

# JSON output
python ucop_cli.py mesh stats --format json
```

## Web API Endpoints

### List Mesh Agents
```
GET /api/mesh/agents
```

Response:
```json
{
  "agents": [
    {
      "agent_id": "topic_identification_mesh_abc123",
      "agent_type": "topic_identification",
      "capabilities": ["topic_discovery", "content_planning"],
      "health": "healthy",
      "load": 0,
      "max_capacity": 10
    }
  ],
  "total": 1
}
```

### Execute Mesh Workflow
```
POST /api/mesh/execute
```

Request:
```json
{
  "initial_agent": "topic_identification",
  "input_data": {
    "content": "Sample content",
    "context": {}
  },
  "workflow_name": "research_workflow"
}
```

Response:
```json
{
  "job_id": "mesh_abc123",
  "success": true,
  "execution_time": 12.5,
  "total_hops": 5,
  "agents_executed": ["agent1", "agent2", "agent3", "agent4", "agent5"],
  "final_output": {
    "result": "Final workflow output"
  },
  "execution_trace": [...]
}
```

### Get Execution Trace
```
GET /api/mesh/trace/{job_id}
```

Response:
```json
{
  "job_id": "mesh_abc123",
  "trace": [
    {
      "agent_id": "agent1",
      "agent_type": "topic_identification",
      "timestamp": "2025-01-15T10:30:00Z",
      "success": true,
      "execution_time": 2.3
    }
  ]
}
```

### Get Statistics
```
GET /api/mesh/stats
```

Response:
```json
{
  "registry_stats": {
    "total_agents": 18,
    "healthy_agents": 18,
    "degraded_agents": 0,
    "total_capabilities": 36,
    "avg_load": 0.5
  },
  "router_stats": {
    "current_hop_count": 0,
    "max_hops": 10,
    "circuit_breaker_enabled": true
  },
  "active_contexts": 0
}
```

## Agent Development for Mesh

### Declaring Capabilities

Agents can declare their capabilities by overriding `declare_capabilities()`:

```python
class TopicIdentificationAgent(Agent):
    def declare_capabilities(self) -> List[str]:
        return ["topic_discovery", "content_planning", "research_initiation"]
```

### Requesting Services from Other Agents

Agents can request services from other agents via mesh:

```python
def execute(self, event: AgentEvent) -> Optional[AgentEvent]:
    # Process initial data
    topics = self._identify_topics(event.data)
    
    # Need content structuring from another agent
    if self.enable_mesh:
        # Request service from agent with content_structuring capability
        structure_request = self.request_agent_service(
            capability="content_structuring",
            input_data={"topics": topics}
        )
        
        # Return with mesh request
        return AgentEvent(
            event_type=f"{self.agent_id}.complete",
            source_agent=self.agent_id,
            correlation_id=event.correlation_id,
            data={
                "topics": topics,
                "_mesh_request_capability": "content_structuring",
                "_mesh_request_data": {"topics": topics}
            }
        )
```

## Use Cases

### Research Workflows
Mesh mode is ideal for research-type tasks where the execution path depends on discovered information. For example:
1. Topic identification discovers multiple subtopics
2. Each subtopic may need different types of content (API docs, tutorials, examples)
3. Agents dynamically request appropriate services based on subtopic characteristics

### Adaptive Content Generation
Generate content that adapts based on available source material:
1. Start with content ingestion
2. Based on what's ingested, decide whether to generate code examples, diagrams, or tutorials
3. Dynamically route to appropriate content generators

### Fault Tolerance
Mesh mode with circuit breaker enables graceful degradation:
1. If an agent repeatedly fails, circuit breaker opens
2. Router selects alternative agents with same capability
3. Workflow continues with backup agents

## Performance Considerations

### Circuit Breaker
- Prevents cascading failures by stopping requests to failing agents
- Automatically resets after timeout period
- Configurable failure threshold

### Load Balancing
- Router selects agents with lowest current load
- Distributes work across available agent instances
- Prevents overwhelming individual agents

### Hop Limits
- max_hops prevents infinite loops
- Typical workflows should complete in 5-10 hops
- Adjust based on workflow complexity

## Comparison: Mesh vs Predefined Workflows

| Feature | Mesh Mode | Predefined Mode |
|---------|-----------|-----------------|
| Execution Order | Dynamic, demand-driven | Fixed, sequential |
| Agent Discovery | Capability-based | Predefined list |
| Flexibility | High - adapts to context | Low - fixed pipeline |
| Complexity | Higher - requires careful design | Lower - straightforward |
| Best For | Research, adaptive tasks | Production pipelines |
| Failure Handling | Circuit breaker, fallback | Retry with same agent |
| Performance Overhead | Routing overhead per hop | Minimal overhead |

## Troubleshooting

### Circular Dependency Detected
**Symptom**: Workflow fails with "Circular dependency detected"

**Cause**: Agent requests capability that would create a cycle in execution path

**Solution**: 
- Review agent logic to prevent requesting services that lead back to earlier agents
- Consider redesigning workflow to be more linear
- Check max_hops configuration

### Max Hops Exceeded
**Symptom**: Workflow stops with "Maximum hop count exceeded"

**Cause**: Workflow requires more hops than configured limit

**Solution**:
- Increase max_hops in configuration
- Review workflow for unnecessary intermediate steps
- Check for agents that repeatedly request services

### Agent Not Found
**Symptom**: Routing fails with "No agents available for capability"

**Cause**: No registered agent provides requested capability

**Solution**:
- Run `mesh discover-agents` to verify agents are registered
- Check agent capability declarations
- Verify mesh.enabled is true in config

### Circuit Breaker Open
**Symptom**: "All agents for capability X are unavailable (circuit breaker)"

**Cause**: All agents with capability have failed repeatedly

**Solution**:
- Check agent logs for failure reasons
- Reset circuit breaker after fixing underlying issues
- Review failure_threshold configuration

## Best Practices

1. **Start Simple**: Begin with predefined workflows, migrate to mesh for specific use cases
2. **Declare Capabilities Clearly**: Use descriptive capability names
3. **Handle Errors**: Agents should gracefully handle missing dependencies
4. **Monitor Performance**: Track hop counts and execution times
5. **Test Thoroughly**: Integration tests should cover multiple execution paths
6. **Document Workflows**: Map expected agent interactions
7. **Use Circuit Breaker**: Enable for production deployments
8. **Set Appropriate Limits**: Configure max_hops based on workflow complexity

## Examples

### Example 1: Simple Linear Workflow

```python
# Agent 1: Topic Identification
def execute(self, event):
    topics = self._find_topics(event.data)
    return self._request_next("content_structuring", {"topics": topics})

# Agent 2: Outline Creation
def execute(self, event):
    outline = self._create_outline(event.data["topics"])
    return self._request_next("section_writing", {"outline": outline})

# Agent 3: Section Writer
def execute(self, event):
    sections = self._write_sections(event.data["outline"])
    return self._complete({"sections": sections})  # No next agent
```

### Example 2: Conditional Branching

```python
def execute(self, event):
    content_type = self._analyze_content(event.data)
    
    if content_type == "technical":
        # Request code generation
        return self._request_next("code_creation", event.data)
    elif content_type == "tutorial":
        # Request tutorial structure
        return self._request_next("tutorial_generation", event.data)
    else:
        # Request general content
        return self._request_next("content_creation", event.data)
```

## Future Enhancements

- Agent capability versioning
- Multi-hop planning and optimization
- Agent result caching
- Distributed mesh across multiple nodes
- Visual workflow editor
- Real-time execution visualization
- Agent marketplace and discovery

## Related Documentation

- [Agent Development Guide](agents.md)
- [Configuration Reference](configuration.md)
- [CLI Reference](cli-reference.md)
- [Web API Documentation](web-ui.md)
