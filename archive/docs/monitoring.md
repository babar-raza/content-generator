# Monitoring & Observability

## Metrics
- Agent execution time
- LLM token usage
- Success/failure rates
- System resource utilization

## Logging
Structured logging with `structlog`:
```python
logger.info("Job completed", job_id=job_id, duration=duration)
```

## Visualization
```bash
# Workflow graphs
python ucop_cli.py viz workflows

# Performance metrics
python ucop_cli.py viz metrics

# Bottleneck analysis
python ucop_cli.py viz bottlenecks
```

## Integration
- **Prometheus**: `/metrics` endpoint
- **Grafana**: Dashboard templates available
- **ELK Stack**: JSON log format supported
