# Performance Optimization

## Benchmarks
- **Throughput**: 10-15 blog posts/hour (single worker)
- **Latency**: 3-8 minutes/blog post
- **Token Usage**: 10K-20K tokens/post
- **Memory**: 2-4 GB/worker

## Optimization Strategies

### 1. Enable Caching
```yaml
caching:
  enabled: true
  ttl: 3600
```

### 2. Parallel Execution
```yaml
workflows:
  enable_parallel_execution: true
  max_parallel_agents: 10
```

### 3. Use Faster Models
```yaml
llm:
  models:
    ollama: "phi4:14b"  # Faster than qwen2.5:14b
```

### 4. GPU Acceleration
Ensure Ollama uses GPU for 3-5x speedup.

### 5. Optimize Resource Limits
```yaml
resources:
  max_memory_per_agent: 2048  # MB
  agent_timeout: 300          # Seconds
```

## Monitoring Performance
```bash
python tools/perf_runner.py
python ucop_cli.py viz bottlenecks
```
