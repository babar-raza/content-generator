---
title: "Tutorial: Launching a LangGraph Workflow"
description: "Hands-on guide to compile and run LangGraph definitions locally."
source_url: "https://example.com/tutorials/langgraph-launch"
sample_type: "live_fixture"
difficulty: "moderate"
---

## Prerequisites
1. Python 3.11+
2. `pip install langgraph==0.2.*`
3. Access to `production_execution_engine.AgentFactory`

## Steps
1. **Compile Workflow** – run `workflow_compiler.compile('multi_agent_blog')` to produce an execution plan.
2. **Initialize Agent Mesh** – instantiate `ProductionExecutionEngine` with `AgentFactory(config, event_bus, services)`. Confirm `NoMockGate` passes.
3. **Execute and Monitor** – submit a job via `JobExecutionEngine.start_job(job_id)` and tail emitted events.

## Validation
- Ensure checkpoints appear under `.checkpoints/langgraph/multi_agent_blog`.
- Verify `samples/external/api_responses/search_api_sample.json` is referenced when mock search is enabled.
- Confirm manifests match the structure in `samples/manifests/job_success_manifest.json`.
