---
title: "UCOP Agent Architecture Deep Dive"
description: "Detailed architecture documentation for agent mesh and orchestration"
source_url: "https://example.com/docs/architecture-deep-dive"
sample_type: "live_fixture"
product: "UCOP"
version: "2025.3"
category: "architecture"
---

## Agent Mesh Architecture

The UCOP agent mesh provides intelligent routing and dynamic agent composition for complex content generation workflows.

### Core Components

1. **AgentFactory** - Discovers and instantiates agents based on capability requirements
2. **MeshExecutor** - Routes requests through the agent mesh with circuit breaker protection
3. **EventBus** - Publishes `AgentEvent` instances for real-time monitoring
4. **CheckpointManager** - Persists workflow state for recovery and debugging

### Agent Communication

Agents communicate through structured events defined in `src/core/contracts.py`:

```python
@dataclass
class AgentEvent:
    event_type: str
    data: Dict[str, Any]
    source_agent: str
    correlation_id: str
    timestamp: datetime
    metadata: Dict[str, Any]
```

### Routing Strategies

- **Direct Routing**: Agent explicitly specified in workflow definition
- **Capability-Based**: Agent selected based on required capabilities
- **Mesh Routing**: Dynamic routing with hop limits and circuit breakers

### Circuit Breaker Pattern

The mesh executor implements circuit breaker logic to prevent cascading failures:

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Failures exceeded threshold, requests fail fast
- **HALF-OPEN**: Testing if service recovered

### Performance Tracking

The `PerformanceTracker` (from `src/utils/learning.py`) monitors:
- Success rates per agent/capability pair
- Average latency in milliseconds
- Common failure types
- Agent health metrics

### LangGraph Integration

When `use_langgraph=true` in config, workflows execute as LangGraph StateGraph:

```yaml
config:
  use_langgraph: true
  langgraph:
    checkpointing: true
    interrupt_before: ["qa_review"]
```

Benefits:
- Human-in-the-loop interrupts
- Persistent checkpoints via MemorySaver
- Visual graph representation
- Time-travel debugging

## Best Practices

1. **Capability Declaration**: Agents should declare capabilities in metadata
2. **Idempotent Operations**: Design agents to handle replay/retry safely
3. **Event Publishing**: Publish events at key execution milestones
4. **Error Context**: Include detailed context in error events
5. **Timeout Configuration**: Set realistic timeouts for LLM operations

## Testing Strategies

- **Mock Mode**: Fast unit tests with synthetic data
- **Live Mode**: E2E validation with real LLM services (`TEST_MODE=live`)
- **Sample Data**: Use `samples/fixtures/` for reproducible tests

## Deployment Considerations

- Configure `NoMockGate` to prevent mock content in production
- Set appropriate `max_hops` for mesh routing (default: 10)
- Enable telemetry mirroring for operational visibility
- Use checkpoint storage for long-running workflows

For implementation details, see `src/orchestration/production_execution_engine.py` and `src/orchestration/mesh_executor.py`.
