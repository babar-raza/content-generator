---
template: how_to_playbook
title: "How-To Template Sample"
description: "Step-focused layout for operational runbooks and tutorials."
layout: guide
sample_type: "template_sample"
frontmatter_contract:
  product: string
  version: string
  difficulty: enum(easy,moderate,advanced)
  prerequisites: list
---

## Template Anatomy
1. **Problem Statement** – short paragraph referencing the triggering incident or request.
2. **Environment Checklist** – tabular data derived from `context.infrastructure`.
3. **Procedure** – numbered list with embedded code fences; each step ties back to workflow state IDs so we can resume from checkpoints.
4. **Validation** – success criteria plus telemetry probes for observability.

## Sample Frontmatter
```yaml
title: "Runbook: Regenerate LangChain Embeddings"
description: "How to rebuild the embedding cache after schema drift."
product: "Knowledge Service"
version: "2025.3"
difficulty: "moderate"
prerequisites:
  - "Access to feature flag service"
  - "Ollama endpoint with llama3.2"
```

## Implementation Notes
- `context.extra_context` merges FAQ snippets into the Validation block.
- When used in live tests, the template pairs with fixtures inside `samples/fixtures/tutorials`.
