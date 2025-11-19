---
template: default_blog
title: "Default Blog Template Sample"
description: "Reference layout used to render thought-leadership articles."
layout: article
reading_time_minutes: 7
sample_type: "template_sample"
sections:
  - id: overview
    title: "Executive Summary"
    components:
      - type: "markdown"
  - id: deep_dive
    title: "Technical Deep Dive"
    components:
      - type: "code"
      - type: "callout"
  - id: outcomes
    title: "Business Outcomes"
    components:
      - type: "list"
---

## Template Purpose
This sample mirrors the structure our blog renderers expect. It keeps descriptive IDs that map to `WorkflowCompiler` nodes so pipeline outputs can be slotted without rewrite.

## Data Contracts
- `context.topic` populates the title and hero summary.
- `context.research` feeds the `overview` block.
- `context.code_samples` injects fenced snippets during the `deep_dive` stage.

## Usage Notes
1. When agents omit a section, the renderer collapses the heading but preserves numbering.
2. CTA snippets arrive from `supplementary_content_node` and should be appended to `outcomes`.
3. This template assumes Markdown+frontmatter files written with UTF-8 + LF endings.
