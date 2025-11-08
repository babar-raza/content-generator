# Performance Tests

This repository includes **pytest-based** performance tests that avoid network/LLM calls,
produce machine-readable results, and summarize them to Markdown.

## How to run

```bash
# Optional: adjust iterations/warmup
export PERF_ITERS=15
export PERF_WARMUP=3

# Run only performance tests
python -m pytest -q tests/performance

# Results
cat reports/perf_results.json

# Summarize to Markdown
python tools/perf_report.py
type reports/perf_summary.md  # Windows
```

## What is measured

- **Web**: FastAPI endpoint (first healthy route) latency.
- **Engine**: `aggregator` merge throughput; `completeness_gate` evaluation time.
- **Core**: Model/route selection speed in `src.core.ollama` (network stubbed).
- **CLI**: `--help` responsiveness.

All tests are deterministic (`seed=42`) and will **skip** gracefully if an expected module/endpoint is not present.
