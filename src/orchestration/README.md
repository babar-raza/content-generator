# Orchestration Module

## Overview

Workflow orchestration using LangGraph for stateful, multi-agent execution with checkpoints and hot-reload.

## Components

### `job_execution_engine.py`
Main job execution engine that manages workflow lifecycle.

```python
class JobExecutionEngine:
    """Workflow job execution"""
    def create_job(self, spec: JobSpec) -> str
    def execute_job(self, job_id: str)
    def get_status(self, job_id: str) -> JobStatus
```

### `production_execution_engine.py`
Production-optimized execution engine with enhanced reliability.

```python
class ProductionExecutionEngine:
    """Production-ready execution"""
    def execute(self, workflow: Workflow) -> Result
```

### `workflow_compiler.py`
Compiles workflow definitions into executable LangGraph graphs.

```python
class WorkflowCompiler:
    """Workflow compilation"""
    def compile(self, definition: WorkflowDefinition) -> Graph
```

### `workflow_state.py`
Manages workflow state and transitions.

```python
@dataclass
class WorkflowState:
    job_id: str
    current_step: str
    completed_steps: List[str]
    outputs: Dict[str, Any]
    errors: List[Error]
```

### `checkpoint_manager.py`
Manages workflow checkpoints for resume capability.

```python
class CheckpointManager:
    """Checkpoint management"""
    def save(self, job_id: str, state: WorkflowState)
    def restore(self, job_id: str, checkpoint: str) -> WorkflowState
```

### `hot_reload.py`
Enables live workflow updates without restart.

```python
class HotReloadMonitor:
    """Hot reload for workflows"""
    def watch(self, path: str)
    def on_change(self, callback: Callable)
```

### `monitor.py`
Monitors workflow execution and collects metrics.

```python
class WorkflowMonitor:
    """Execution monitoring"""
    def track(self, job_id: str, metrics: Dict)
    def get_metrics(self, job_id: str) -> Dict
```

### `ops_console.py`
Operations console for workflow management.

```python
class OpsConsole:
    """Workflow operations console"""
    def list_jobs(self) -> List[Job]
    def control_job(self, job_id: str, action: str)
```

### Agent Discovery

- `agent_scanner.py` - Scans and registers available agents
- `auto_discover_agents.py` - Automatic agent discovery
- `generate_agent_yaml.py` - Generates agent configuration
- `enhanced_registry.py` - Enhanced agent registry with capabilities

## Workflow Definition

Workflows are defined in YAML:

```yaml
workflows:
  blog_generation:
    steps:
      - id: ingestion
        agent: KBIngestionAgent
        
      - id: outline
        agent: OutlineCreationAgent
        depends_on: [ingestion]
        
      - id: content
        agents: [IntroWriter, SectionWriter, ConclusionWriter]
        depends_on: [outline]
        parallel: true
```

## Usage

```python
from src.orchestration.job_execution_engine import JobExecutionEngine
from src.orchestration.workflow_compiler import WorkflowCompiler

engine = JobExecutionEngine()
job_id = engine.create_job(JobSpec(
    workflow='blog_generation',
    inputs={'source': 'article.md'}
))

engine.execute_job(job_id)
status = engine.get_status(job_id)
```

## LangGraph Integration

Workflows are compiled to LangGraph graphs:

```python
from langgraph.graph import StateGraph

def compile_workflow(definition):
    graph = StateGraph(WorkflowState)
    
    for step in definition.steps:
        graph.add_node(step.id, create_agent_node(step.agent))
    
    for step in definition.steps:
        for dep in step.depends_on:
            graph.add_edge(dep, step.id)
    
    return graph.compile()
```

## Dependencies

- `langgraph` - Graph-based workflows
- `langchain-core` - LangChain integration
- `src.agents` - Agent implementations
- `src.engine` - Execution engine
