# Workflows & Pipelines

See the original documentation at `/home/claude/docs/workflows.md` for complete workflow documentation. Key points:

## Overview
- LangGraph-based workflow orchestration
- Parallel agent execution
- Checkpoint persistence
- Hot-reload support

## Main Workflows
1. **blog_generation**: Full blog post generation (default)
2. **code_only**: Code generation only
3. **quick_draft**: Quick content without SEO
4. **seo_only**: SEO optimization only

## Configuration
See `config/main.yaml` and `templates/workflows.yaml`

## Creating Custom Workflows
See [extensibility.md](extensibility.md)
