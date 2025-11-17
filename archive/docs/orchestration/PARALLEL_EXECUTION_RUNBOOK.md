# Parallel Execution Runbook

## Overview
This system implements parallel agent execution to reduce total workflow execution time. Independent agents can run concurrently using ThreadPoolExecutor, achieving 2-3× speedup for parallelizable workloads.

## Quick Start

### Enable Parallel Execution
Edit `config/main.yaml`:
```yaml
workflows:
  enable_parallel_execution: true
  max_parallel_agents: 5  # Adjust based on system resources
```

### Run with Parallel Execution
```bash
# Sequential (default)
python ucop_cli.py generate --input test.md --output output/

# Parallel (after enabling in config)
python ucop_cli.py generate --input test.md --output output/
```

## Performance Testing

### Run Benchmarks
```bash
# Run all parallel execution tests
pytest tests/performance/test_parallel_speedup.py -v

# Run specific benchmark
pytest tests/performance/test_parallel_speedup.py::TestParallelExecutorBenchmark::test_benchmark_3_agents_parallel -v -s

# Run with timing
time pytest tests/performance/test_parallel_speedup.py::TestParallelSpeedup::test_parallel_execution_faster_than_sequential -v -s
```

### Expected Results
- **Speedup**: 2-3× for 3-5 agents
- **Efficiency**: 70-90% (accounting for overhead)
- **Parallel time**: ~(longest_agent_time + 0.2s overhead)
- **Sequential time**: sum of all agent times

## Configuration

### Main Configuration (`config/main.yaml`)
```yaml
workflows:
  # Enable/disable parallel execution
  enable_parallel_execution: true
  
  # Maximum concurrent agents
  # - Higher = more parallelism, more resource usage
  # - Lower = less parallelism, lower resource usage
  # Recommended: 3-5 for standard, 5-10 for high-end systems
  max_parallel_agents: 5
```

### Parallel Executor Parameters
When initializing `ParallelExecutor` programmatically:
```python
from src.orchestration.parallel_executor import ParallelExecutor

executor = ParallelExecutor(
    max_workers=5,          # Max concurrent agents
    group_timeout=300.0,    # Timeout for parallel group (seconds)
    fail_fast=False         # Cancel group on first failure
)
```

## Parallelizable Agent Groups

The system automatically identifies these parallel groups:

### Ingestion Agents (3 agents, ~30s total → ~10s parallel)
- `kb_ingestion` - Knowledge base ingestion
- `api_ingestion` - API documentation ingestion  
- `blog_ingestion` - Blog content ingestion

### Content Writers (3+ agents, varies by sections)
- `introduction_writer` - Write introduction
- `section_writer` (×N) - Write content sections
- `conclusion_writer` - Write conclusion

### Code Processing (2 agents)
- `code_generation` - Generate code examples
- `code_validation` - Validate generated code

## Performance Tuning

### Optimal max_parallel_agents

**System Profile**:
- **Low-end** (4 cores, 8GB RAM): `max_parallel_agents: 2-3`
- **Mid-range** (8 cores, 16GB RAM): `max_parallel_agents: 3-5`
- **High-end** (16+ cores, 32GB+ RAM): `max_parallel_agents: 5-10`

**Workload Profile**:
- **I/O-bound** (LLM calls, network): Higher values (5-10)
- **CPU-bound** (local processing): Match CPU cores
- **Memory-bound** (large models): Lower values (2-3)

### Monitoring Performance
```python
# Enable detailed logging
import logging
logging.getLogger('src.orchestration.parallel_executor').setLevel(logging.INFO)
```

Watch for these log messages:
```
⚡ Starting parallel execution of 3 agents: ['kb_ingestion', 'api_ingestion', 'blog_ingestion']
✓ Agent kb_ingestion completed (1/3) in 9.23s
✓ Agent api_ingestion completed (2/3) in 10.14s
✓ Agent blog_ingestion completed (3/3) in 8.91s
⚡ Parallel execution completed in 10.34s: 3/3 succeeded, 0 failed
📊 Estimated speedup: 2.73× (sequential: 28.28s, parallel: 10.34s)
```

## Benchmarking

### Measure Sequential Baseline
```bash
# Disable parallel execution
sed -i 's/enable_parallel_execution: true/enable_parallel_execution: false/' config/main.yaml

# Run and time
time python ucop_cli.py generate --input test.md --output output_seq/
# Note: Total time: XX.XXs
```

### Measure Parallel Performance
```bash
# Enable parallel execution
sed -i 's/enable_parallel_execution: false/enable_parallel_execution: true/' config/main.yaml

# Run and time
time python ucop_cli.py generate --input test.md --output output_par/
# Note: Total time: YY.YYs
```

### Calculate Speedup
```python
speedup = sequential_time / parallel_time
efficiency = (speedup / max_parallel_agents) * 100

print(f"Speedup: {speedup:.2f}×")
print(f"Efficiency: {efficiency:.1f}%")
print(f"Time saved: {sequential_time - parallel_time:.2f}s")
```

## Troubleshooting

### Issue: No speedup observed
**Causes**:
- Not enough parallelizable agents in workflow
- System resource constraints (CPU, memory)
- Agents have dependencies preventing parallelism

**Solutions**:
1. Check log for "⚡ Starting parallel execution" messages
2. Verify `max_parallel_agents` > 1
3. Check workflow has parallelizable groups (ingestion, writers)
4. Monitor system resources during execution

### Issue: Agents timing out
**Causes**:
- `group_timeout` too low
- Individual agents taking longer than expected
- System overloaded

**Solutions**:
1. Increase `group_timeout` in ParallelExecutor
2. Reduce `max_parallel_agents` to lower system load
3. Check agent logs for performance issues

### Issue: Thread-safe state errors
**Causes**:
- Race conditions in shared state updates
- Improper state synchronization

**Solutions**:
1. Verify ThreadSafeState is used for shared state
2. Check agents properly use execute() return values
3. Review agent state update logic

### Issue: Lower than expected speedup
**Expected Behavior**:
- 3 agents: 2.5-2.8× speedup
- 5 agents: 3.0-4.0× speedup

**Causes**:
- System overhead (thread creation, context switching)
- Non-parallelizable dependencies
- I/O contention

**Solutions**:
1. Profile agent execution times: `pytest tests/performance/test_parallel_speedup.py -v -s`
2. Check for dependency chains limiting parallelism
3. Ensure LLM service supports concurrent calls
4. Monitor network bandwidth if using remote LLM

## Advanced Usage

### Custom Parallel Groups
Override default parallel group detection:
```python
from src.orchestration.parallel_executor import ParallelExecutor

executor = ParallelExecutor(max_workers=5)

# Define custom parallel groups
steps = [
    {'agent': 'custom_agent_1'},
    {'agent': 'custom_agent_2'},
    {'agent': 'custom_agent_3'},
]

dependencies = {}  # No dependencies = all can run in parallel
groups = executor.identify_parallel_groups(steps, dependencies)
```

### Fail-Fast Mode
Cancel remaining agents on first failure:
```python
executor = ParallelExecutor(max_workers=5, fail_fast=True)
```

**Use when**:
- Critical workflow where one failure means abort
- Want to save resources on failure
- Fast feedback is important

**Don't use when**:
- Want partial results even with failures
- Failures are expected and handled
- Other agents can provide fallback data

## Integration Examples

### With Production Execution Engine
```python
from src.orchestration.production_execution_engine import ProductionExecutionEngine
from src.core import Config

config = Config()
config.enable_parallel_execution = True
config.max_parallel_agents = 5

engine = ProductionExecutionEngine(config)
results = engine.execute_pipeline(
    workflow_name="default",
    steps=workflow_steps,
    input_data=input_data,
    job_id="test-job-123"
)
```

### Programmatic Usage
```python
from src.orchestration.parallel_executor import ParallelExecutor, ThreadSafeState

# Initialize
executor = ParallelExecutor(max_workers=5)
state = ThreadSafeState({'initial': 'state'})

# Execute parallel group
results = executor.execute_parallel(
    agent_configs=[
        {'agent': 'kb_ingestion'},
        {'agent': 'api_ingestion'},
        {'agent': 'blog_ingestion'},
    ],
    agent_factory=agent_factory,
    shared_state=state,
    context={'job_id': 'test'}
)

# Check results
for result in results:
    if result['status'] == 'completed':
        print(f"✓ {result['agent_id']}: {result['execution_time']:.2f}s")
    else:
        print(f"✗ {result['agent_id']}: {result['error']}")
```

## Best Practices

1. **Start Conservative**: Begin with `max_parallel_agents: 3` and increase based on results
2. **Monitor Resources**: Watch CPU, memory, network during parallel execution
3. **Test Thoroughly**: Run benchmark suite before production use
4. **Handle Failures**: Use fail_fast=False for resilient workflows
5. **Log Everything**: Enable INFO logging for parallel executor
6. **Measure Impact**: Always benchmark sequential vs parallel
7. **Profile Agents**: Identify slow agents that benefit most from parallelism

## Maintenance

### Regular Health Checks
```bash
# Weekly performance check
pytest tests/performance/test_parallel_speedup.py -v

# Monthly benchmark
pytest tests/performance/test_parallel_speedup.py::TestParallelExecutorBenchmark -v -s > benchmarks/$(date +%Y-%m-%d).txt
```

### Performance Regression Detection
If speedup drops below 2.0×:
1. Check system resources
2. Review recent agent changes
3. Verify LLM service performance
4. Check for new dependencies blocking parallelism

## References

- **Code**: `src/orchestration/parallel_executor.py`
- **Integration**: `src/orchestration/production_execution_engine.py`
- **Tests**: `tests/performance/test_parallel_speedup.py`
- **Config**: `config/main.yaml`
