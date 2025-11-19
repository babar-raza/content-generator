# Execution Engines

## Overview

UCOP uses **two complementary execution engines** that work together to orchestrate workflows and execute agents. This separation of concerns provides flexibility, maintainability, and clear boundaries between job management and agent execution.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              CLI / Web UI / API                      │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│         JobExecutionEngine (Orchestration)           │
│  • Job queue management                              │
│  • Status tracking & persistence                     │
│  • Checkpoint integration                            │
│  • Workflow compilation                              │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│      ProductionExecutionEngine (Agent Execution)     │
│  • Real agent instantiation                          │
│  • LLM service integration                           │
│  • NoMockGate validation                             │
│  • Mesh execution patterns                           │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│                 Agent Mesh (34 Agents)               │
│  Ingestion | Content | SEO | Code | Publishing       │
└─────────────────────────────────────────────────────┘
```

---

## JobExecutionEngine (Orchestration Layer)

**Purpose**: High-level job lifecycle management and workflow orchestration

**Location**: [src/orchestration/job_execution_engine.py](../src/orchestration/job_execution_engine.py)

### Responsibilities

- **Job Queue Management**: Maintains a priority queue of pending jobs
- **Persistence**: Uses `JobStorage` to save/restore job state
- **Status Tracking**: Tracks job states (pending, running, paused, completed, failed, cancelled)
- **Checkpoint Integration**: Works with `CheckpointManager` for resume/recovery
- **Workflow Compilation**: Uses `WorkflowCompiler` to create execution plans
- **Event Publishing**: Emits job lifecycle events via EventBus
- **Concurrency Control**: Manages max concurrent jobs

### Key Features

```python
class JobExecutionEngine:
    def __init__(
        self,
        compiler: WorkflowCompiler,
        registry: EnhancedAgentRegistry,
        event_bus: Optional[EventBus] = None,
        max_concurrent_jobs: int = 3,
        storage_dir: Optional[Path] = None,
        checkpoint_config: Optional[Dict[str, Any]] = None
    ):
        ...

    def submit_job(self, workflow_id: str, params: Dict[str, Any]) -> str:
        """Submit a new job to the queue"""

    def get_job_status(self, job_id: str) -> JobMetadata:
        """Get current job status"""

    def pause_job(self, job_id: str) -> bool:
        """Pause a running job"""

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending/running job"""
```

### State Model

Uses models from [src/orchestration/job_state.py](../src/orchestration/job_state.py):

- **JobStatus**: PENDING, RUNNING, PAUSED, RETRYING, COMPLETED, FAILED, CANCELLED, ARCHIVED
- **JobMetadata**: Job information (id, workflow_id, status, progress, timestamps)
- **JobState**: Complete job state including execution steps
- **StepExecution**: Individual step status and output

### Usage Example

```python
from src.orchestration import JobExecutionEngine, WorkflowCompiler
from src.orchestration import EnhancedAgentRegistry
from src.core import EventBus, Config

# Initialize
config = Config()
event_bus = EventBus()
registry = EnhancedAgentRegistry()
compiler = WorkflowCompiler(registry, event_bus)

engine = JobExecutionEngine(
    compiler=compiler,
    registry=registry,
    event_bus=event_bus,
    max_concurrent_jobs=3
)

# Submit a job
job_id = engine.submit_job(
    workflow_id="blog_generation",
    params={"topic": "AI in Healthcare"}
)

# Check status
status = engine.get_job_status(job_id)
print(f"Job {job_id}: {status.status}")
```

---

## ProductionExecutionEngine (Agent Execution Layer)

**Purpose**: Real agent execution with production services and validation

**Location**: [src/orchestration/production_execution_engine.py](../src/orchestration/production_execution_engine.py)

### Responsibilities

- **Agent Instantiation**: Creates real agent instances (not mocks)
- **Service Integration**: Wires up LLM, database, embeddings, trends services
- **NoMockGate Validation**: Ensures no mock services in production
- **Mesh Execution**: Integrates with `MeshExecutor` for service mesh patterns
- **Checkpoint Management**: Saves/restores execution state
- **Metrics Tracking**: Tracks execution time, LLM calls, tokens used
- **Progress Callbacks**: Provides real-time execution updates

### Key Features

```python
class ProductionExecutionEngine:
    def __init__(
        self,
        config: Config,
        event_bus: EventBus,
        checkpoint_manager: Optional[CheckpointManager] = None,
        progress_callback: Optional[Callable] = None
    ):
        ...

    def execute_workflow(
        self,
        workflow_definition: Dict[str, Any],
        initial_state: Dict[str, Any],
        checkpoint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a complete workflow with real agents"""

    def execute_agent(
        self,
        agent_id: str,
        input_data: Dict[str, Any]
    ) -> AgentExecutionResult:
        """Execute a single agent"""
```

### Service Integration

The engine automatically wires up production services:

```python
# Real services (no mocks)
self.llm_service = LLMService(config)
self.db_service = DatabaseService(config)
self.embedding_service = EmbeddingService(config)
self.gist_service = GistService(config)
self.link_checker = LinkChecker()
self.trends_service = TrendsService()

# Apply NoMockGate validation
NoMockGate.validate_all_services([
    self.llm_service,
    self.db_service,
    self.embedding_service,
    # ... other services
])
```

### AgentExecutionResult

```python
@dataclass
class AgentExecutionResult:
    agent_id: str
    status: AgentStatus  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    output_data: Dict[str, Any]
    error: Optional[str]
    execution_time: float
    llm_calls: int
    tokens_used: int
```

### Usage Example

```python
from src.orchestration.production_execution_engine import ProductionExecutionEngine
from src.core import Config, EventBus
from src.orchestration import CheckpointManager

config = Config()
config.load_from_env()
event_bus = EventBus()
checkpoint_manager = CheckpointManager()

engine = ProductionExecutionEngine(
    config=config,
    event_bus=event_bus,
    checkpoint_manager=checkpoint_manager,
    progress_callback=lambda agent, progress: print(f"{agent}: {progress}%")
)

# Execute a workflow
result = engine.execute_workflow(
    workflow_definition={
        "name": "blog_generation",
        "steps": [
            {"agent": "research_agent", "inputs": {"topic": "AI in Healthcare"}},
            {"agent": "content_agent", "inputs": {}},
            {"agent": "seo_agent", "inputs": {}}
        ]
    },
    initial_state={"topic": "AI in Healthcare"}
)
```

---

## Integration Pattern

The two engines work together in a layered approach:

### 1. Job Submission (CLI/Web → JobExecutionEngine)

```python
# User submits via CLI
ucop_cli.py generate blog "AI in Healthcare"
    ↓
# JobExecutionEngine queues the job
job_id = engine.submit_job("blog_generation", {"topic": "AI in Healthcare"})
    ↓
# JobExecutionEngine compiles workflow
plan = compiler.compile_workflow(workflow_definition)
```

### 2. Job Execution (JobExecutionEngine → ProductionExecutionEngine)

```python
# JobExecutionEngine starts execution
engine._execute_job_internal(job_id)
    ↓
# Creates or gets ProductionExecutionEngine
prod_engine = ProductionExecutionEngine(config, event_bus)
    ↓
# Delegates to production engine
result = prod_engine.execute_workflow(workflow_def, initial_state)
```

### 3. Agent Execution (ProductionExecutionEngine → Agents)

```python
# ProductionExecutionEngine executes each agent
for step in workflow_steps:
    result = prod_engine.execute_agent(step.agent_id, step.inputs)
    ↓
# Agent executes with real services
agent = ResearchAgent(llm_service, db_service, ...)
output = agent.execute(inputs)
```

---

## Checkpoint Integration

Both engines integrate with the checkpoint system:

### JobExecutionEngine Checkpoints

- Saves job state (queue, status, metadata) to disk
- Enables resume on restart
- Location: `.jobs/` directory

```python
engine.save_checkpoint(job_id)
engine.restore_checkpoint(job_id)
```

### ProductionExecutionEngine Checkpoints

- Saves workflow execution state
- Enables resume from failure points
- Uses `CheckpointManager` for LangGraph state

```python
checkpoint_manager.save_checkpoint(
    workflow_id=workflow_id,
    state=current_state,
    metadata=execution_metadata
)
```

---

## Error Handling

### JobExecutionEngine

```python
# Automatic retry on failure
max_retries: int = 3
retry_delay: int = 5  # seconds

# Status transitions
RUNNING → FAILED → RETRYING → RUNNING → COMPLETED
```

### ProductionExecutionEngine

```python
# Per-agent error handling
try:
    result = agent.execute(inputs)
except Exception as e:
    return AgentExecutionResult(
        agent_id=agent_id,
        status=AgentStatus.FAILED,
        error=str(e)
    )
```

---

## Testing

### JobExecutionEngine Tests

```bash
# Unit tests (if available)
pytest tests/unit/test_job_execution_engine.py -v

# Integration tests
pytest tests/integration/test_jobs_routes.py -v
pytest tests/integration/test_workflows_routes.py -v
```

### ProductionExecutionEngine Tests

```bash
# E2E tests with real services
pytest tests/e2e/test_live_workflows.py -v

# Validation tests
python tools/validate_production.py
```

---

## Configuration

### JobExecutionEngine Config

```yaml
# config/jobs.yaml (optional)
max_concurrent_jobs: 3
storage_dir: .jobs/
enable_persistence: true
checkpoint_interval: 30  # seconds
```

### ProductionExecutionEngine Config

```yaml
# config/config.yaml or .env
OLLAMA_BASE_URL=http://localhost:11434
GEMINI_API_KEY=your-key-here
DATABASE_PATH=data/ucop.db
ENABLE_CHECKPOINT=true
```

---

## Migration Notes

### Previous Engines (Removed)

- **src/core/job_execution_engine.py**: Removed (unused, conflicting definitions)
- **src/orchestration/job_execution_engine_enhanced.py**: Removed (legacy, test-only)
- **src/orchestration/ops_console.py**: Removed (deprecated, broken imports)

These were consolidated into the two canonical engines described above.

### Import Updates

**Before:**
```python
from src.core.job_execution_engine import JobExecutionEngine  # ❌ Removed
from src.orchestration.job_execution_engine_enhanced import AsyncJobExecutionEngine  # ❌ Removed
```

**After:**
```python
from src.orchestration import JobExecutionEngine  # ✅ Correct
from src.orchestration.production_execution_engine import ProductionExecutionEngine  # ✅ Correct
```

---

## Best Practices

1. **Use JobExecutionEngine for job lifecycle management**
   - Job queueing, status tracking, persistence
   - CLI and Web API integrations

2. **Use ProductionExecutionEngine for agent execution**
   - Direct agent invocation
   - Validation and testing scripts
   - Mesh execution patterns

3. **Enable checkpoints for long-running workflows**
   ```python
   checkpoint_config = {"enabled": True, "interval": 30}
   ```

4. **Monitor job status via events**
   ```python
   event_bus.subscribe("job.started", on_job_started)
   event_bus.subscribe("job.completed", on_job_completed)
   event_bus.subscribe("job.failed", on_job_failed)
   ```

5. **Use NoMockGate in production**
   ```python
   # Ensures no mock services slip into production
   NoMockGate.validate_all_services(services)
   ```

---

## See Also

- [Architecture Overview](architecture.md)
- [Workflows](workflows.md)
- [Agents](agents.md)
- [Checkpointing](../config/checkpoints.yaml)
- [Configuration](configuration.md)
