# Engine Module

## Overview

The execution engine coordinates agent execution, manages context, and handles resource allocation.

## Components

### `unified_engine.py`
Central execution coordinator that manages the entire content generation pipeline.

```python
class UnifiedEngine:
    """Main execution engine"""
    def execute(self, spec: RunSpec) -> JobResult
    def get_job_status(self, job_id: str) -> JobStatus
```

### `executor.py`
Low-level executor for running individual agents.

```python
class Executor:
    """Agent executor with retry logic"""
    def execute_agent(self, agent: Agent, input_data: Dict) -> Dict
```

### `context_merger.py`
Merges context from multiple sources for agent execution.

```python
class ContextMerger:
    """Intelligent context merging"""
    def merge(self, contexts: List[Dict]) -> Dict
```

### `input_resolver.py`
Resolves and validates inputs before execution.

```python
class InputResolver:
    """Input resolution and validation"""
    def resolve(self, input_spec: Dict) -> Dict
```

### `output_path_resolver.py`
Determines output file paths and structure.

```python
class OutputPathResolver:
    """Smart output path resolution"""
    def resolve(self, base_path: str, metadata: Dict) -> Path
```

### `aggregator.py`
Aggregates outputs from multiple agents.

```python
class OutputAggregator:
    """Combines agent outputs"""
    def aggregate(self, outputs: List[Dict]) -> Dict
```

### `completeness_gate.py`
Validates output completeness before finalization.

```python
class CompletenessGate:
    """Quality gate for outputs"""
    def check(self, output: Dict) -> ValidationResult
```

### `agent_tracker.py`
Tracks agent execution metrics and status.

```python
class AgentTracker:
    """Execution tracking and metrics"""
    def track(self, agent_id: str, metrics: Dict)
```

### `slug_service.py`
Generates SEO-friendly URL slugs.

```python
class SlugService:
    """SEO slug generation"""
    def generate(self, title: str) -> str
```

### Device Management (`device/`)

- `gpu_manager.py` - GPU detection and allocation for local models

## Usage

```python
from src.engine.unified_engine import get_engine, RunSpec

engine = get_engine()
result = engine.execute(RunSpec(
    workflow='blog_generation',
    inputs={'source_file': 'article.md'}
))
```

## Architecture

The engine follows a pipeline architecture:

```
Input → Resolver → Executor → Aggregator → Gate → Output
           ↓
      Context Merger
           ↓
      Agent Tracker
```

## Dependencies

- `src.agents` - Agent implementations
- `src.core` - Core abstractions
- `src.orchestration` - Workflow orchestration
