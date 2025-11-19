# Monitoring

## Overview

UCOP provides comprehensive monitoring capabilities including metrics collection, real-time visualization, logging, and alerting. This guide covers monitoring setup, metrics analysis, and troubleshooting.

## Metrics Collection

### Key Metrics

**System Metrics**:
- CPU usage per worker
- Memory utilization  
- Disk I/O
- Network throughput

**Application Metrics**:
- Job throughput (jobs/hour)
- Agent latency (p50, p95, p99)
- Error rates per agent
- LLM token usage
- Vector store query latency

**Business Metrics**:
- Content generation success rate
- Average time per blog post
- Agent success/failure ratio
- API call costs

### Prometheus Integration

Configure Prometheus scraping:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ucop'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

Metrics endpoint implementation:

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
job_counter = Counter('ucop_jobs_total', 'Total jobs processed')
agent_duration = Histogram('ucop_agent_duration_seconds', 'Agent execution time')
active_jobs = Gauge('ucop_active_jobs', 'Currently active jobs')

@app.get("/metrics")
async def metrics():
    return generate_latest()
```

### Grafana Dashboards

Import UCOP dashboard:

1. Navigate to Grafana
2. Import dashboard
3. Upload `monitoring/grafana_dashboard.json`
4. Configure data source (Prometheus)

Key panels:
- Job throughput timeline
- Agent performance heatmap
- Error rate by agent
- Resource utilization
- LLM token usage

## Logging

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages  
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical failures

### Structured Logging

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'job_id': getattr(record, 'job_id', None),
            'agent': getattr(record, 'agent', None)
        }
        return json.dumps(log_data)
```

### Log Aggregation

**ELK Stack Integration**:

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    paths:
      - /var/log/ucop/*.log
    json.keys_under_root: true

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "ucop-%{+yyyy.MM.dd}"
```

### Log Queries

Common log queries:

```bash
# View errors
grep ERROR /var/log/ucop/ucop.log

# Filter by job
grep "job_12345" /var/log/ucop/ucop.log

# Agent-specific logs
grep "agent.*code_generation" /var/log/ucop/ucop.log
```

## Real-Time Monitoring

### WebSocket Monitoring

Connect to live job monitoring:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/job/${jobId}');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'agent_started') {
        console.log(`Agent ${data.agent_id} started`);
    }
};
```

### CLI Monitoring

```bash
# Watch job progress
watch -n 2 python ucop_cli.py job list --status running

# Monitor agent health
watch -n 5 python ucop_cli.py agents health

# Tail logs
tail -f /var/log/ucop/ucop.log | grep ERROR
```

## Alerting

### Alert Rules

Example Prometheus alert rules:

```yaml
# alerts.yml
groups:
  - name: ucop
    rules:
      - alert: HighErrorRate
        expr: rate(ucop_errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
      
      - alert: SlowAgents
        expr: ucop_agent_duration_seconds{quantile="0.95"} > 600
        for: 10m
        annotations:
          summary: "Agents running slow"
```

### Notification Channels

Configure alerting:

```yaml
# alertmanager.yml
route:
  receiver: 'team-email'
  
receivers:
  - name: 'team-email'
    email_configs:
      - to: 'ops@example.com'
        from: 'alerts@example.com'
        
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/...'
        channel: '#ucop-alerts'
```

## Performance Monitoring

### Agent Performance

```bash
# View agent metrics
python ucop_cli.py viz metrics

# Identify bottlenecks
python ucop_cli.py viz bottlenecks --threshold 5000

# Show agent dependencies
python ucop_cli.py viz agents
```

### Database Performance

Monitor ChromaDB:

```python
# Query performance
with timer() as t:
    results = db.query(embedding, n_results=5)
logger.info(f"Query took {t.duration}ms")
```

## Health Checks

### Service Health

```python
@app.get("/health")
async def health_check():
    checks = {
        'ollama': check_ollama(),
        'chromadb': check_chromadb(),
        'disk': check_disk_space(),
        'memory': check_memory()
    }
    
    healthy = all(checks.values())
    status = 200 if healthy else 503
    
    return JSONResponse(
        content={'status': 'healthy' if healthy else 'unhealthy', 'checks': checks},
        status_code=status
    )
```

### Kubernetes Health Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

## Troubleshooting with Monitoring

### High Memory Usage

```bash
# Check memory by agent
python ucop_cli.py viz metrics --agent code_generation_node

# View memory timeline
# Check Grafana dashboard: Memory Usage panel
```

### Slow Performance

```bash
# Identify slow agents
python ucop_cli.py viz bottlenecks

# Check agent metrics
python ucop_cli.py viz metrics --period 7

# View execution trace
python ucop_cli.py viz debug --job job_12345
```

### Error Spikes

```bash
# View error logs
grep ERROR /var/log/ucop/ucop.log | tail -50

# Check agent failures
python ucop_cli.py agents failures --since today

# View agent health
python ucop_cli.py agents health
```

## Best Practices

1. **Monitor continuously**: Always-on monitoring in production
2. **Set baselines**: Establish normal performance metrics
3. **Alert on anomalies**: Configure alerts for deviations
4. **Log everything**: Comprehensive logging for debugging
5. **Regular reviews**: Weekly metric reviews
6. **Capacity planning**: Monitor trends for scaling
7. **Test alerts**: Verify alert rules work
8. **Document incidents**: Keep runbooks updated

---

*This documentation is part of the UCOP project. For more information, see the [main README](../README.md).*
