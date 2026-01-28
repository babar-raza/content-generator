#!/usr/bin/env bash
# Live E2E Test Runner - Enforces 100%
set -e

TIMESTAMP=${LIVE_E2E_TIMESTAMP:-$(TZ='Asia/Karachi' date +%Y%m%d-%H%M)}
export LIVE_E2E_TIMESTAMP=$TIMESTAMP
export LIVE_E2E_REPORT_DIR="live_e2e_ollama_fix"

echo "Live E2E Ollama Test - Timestamp: $TIMESTAMP"

# Prerequisites
curl -sf http://localhost:11434/api/tags > /dev/null || { echo "Ollama not running"; exit 1; }
docker version > /dev/null || { echo "Docker not available"; exit 1; }

# Run phases
python tools/live_e2e/data_fetch.py
python tools/run_live_ingestion.py
python tools/live_e2e/chroma_probe.py

echo "LIVE E2E TEST: PASS"
