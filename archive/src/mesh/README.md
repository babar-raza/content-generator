# Mesh Module

## Overview

Agent mesh coordination for distributed, event-driven agent communication and state management.

## Components

### `state_store.py`
Distributed state management for agent mesh.

```python
class StateStore:
    """Distributed state store"""
    def get(self, key: str) -> Any
    def set(self, key: str, value: Any)
    def subscribe(self, key: str, callback: Callable)
```

### `capability_registry.py`
Registers and discovers agent capabilities.

```python
class CapabilityRegistry:
    """Agent capability registry"""
    def register(self, agent_id: str, capabilities: List[str])
    def find_agents(self, capability: str) -> List[str]
```

### `runtime_async.py`
Async runtime for agent mesh coordination.

```python
class AsyncRuntime:
    """Async mesh runtime"""
    async def start(self)
    async def dispatch(self, event: Event)
```

### `batch_aggregators.py`
Aggregates results from batch/parallel agent execution.

```python
class BatchAggregator:
    """Batch result aggregation"""
    def aggregate(self, results: List[Dict]) -> Dict
```

### `mesh_observer.py`
Observes and monitors mesh activity.

```python
class MeshObserver:
    """Mesh monitoring"""
    def on_event(self, event: Event)
    def get_metrics(self) -> Dict
```

### `negotiation.py`
Handles agent-to-agent negotiation and coordination.

```python
class Negotiator:
    """Agent negotiation"""
    def negotiate(self, agents: List[Agent], task: Task) -> Agent
```

## Event-Driven Architecture

The mesh uses an event-driven architecture where agents communicate via events:

```python
@dataclass
class Event:
    type: str
    source: str
    target: Optional[str]
    data: Dict
    timestamp: datetime
```

## Usage

```python
from src.mesh.runtime_async import AsyncRuntime
from src.mesh.state_store import StateStore

runtime = AsyncRuntime()
state = StateStore()

# Start mesh
await runtime.start()

# Dispatch event
await runtime.dispatch(Event(
    type='content.generate',
    source='orchestrator',
    data={'input': 'article.md'}
))
```

## Coordination Patterns

1. **Pub/Sub**: Agents subscribe to events and publish results
2. **Request/Reply**: Synchronous agent invocation
3. **Scatter/Gather**: Parallel execution with result aggregation
4. **Pipeline**: Sequential agent chaining

## Dependencies

- `asyncio` - Async runtime
- `src.agents` - Agent implementations
- `src.orchestration` - Workflow coordination
