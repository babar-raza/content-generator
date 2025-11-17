# Agent Reference

Complete reference for all 38 UCOP agents organized by category.

## Agent Categories

- [Content Generation](#content-generation-5-agents)
- [SEO Optimization](#seo-optimization-3-agents)
- [Code Generation](#code-generation-4-agents)
- [Publishing](#publishing-4-agents)
- [Research & Intelligence](#research--intelligence-6-agents)
- [Support & Validation](#support--validation-5-agents)
- [Ingestion](#ingestion-6-agents)

## Content Generation (5 Agents)

### OutlineCreationAgent

**Purpose**: Creates structured content outlines from source material

**Inputs**:
```json
{
  "kb_content": "string (source article content)",
  "current_topic": {
    "title": "string",
    "keywords": ["string"]
  }
}
```

**Outputs**:
```json
{
  "outline": {
    "title": "string",
    "sections": [
      {"heading": "string", "points": ["string"]}
    ]
  },
  "estimated_length": "number (words)"
}
```

**Configuration**:
- Model: qwen2.5:14b (default)
- Max runtime: 300s
- Max tokens: 4096

### IntroductionWriterAgent

**Purpose**: Writes engaging introduction paragraphs with hooks

**Inputs**:
```json
{
  "outline": "object",
  "tone": "string (professional|casual|technical)",
  "keywords": ["string"]
}
```

**Outputs**:
```json
{
  "introduction": "string (2-3 paragraphs)",
  "hook_type": "string (question|statistic|story)"
}
```

### SectionWriterAgent

**Purpose**: Writes detailed content for each outline section

**Inputs**:
```json
{
  "section": {"heading": "string", "points": ["string"]},
  "context": "object",
  "word_count_target": "number"
}
```

**Outputs**:
```json
{
  "content": "string (section content)",
  "word_count": "number"
}
```

**Special Features**: Can run in parallel for multiple sections

### ConclusionWriterAgent

**Purpose**: Creates compelling conclusions with CTAs

**Inputs**:
```json
{
  "full_content": "string",
  "main_points": ["string"],
  "cta_type": "string (optional)"
}
```

**Outputs**:
```json
{
  "conclusion": "string (1-2 paragraphs)",
  "cta": "string (call-to-action)"
}
```

### SupplementaryContentAgent

**Purpose**: Adds FAQs, tips, warnings, and additional resources

**Inputs**:
```json
{
  "main_content": "string",
  "topic": "string"
}
```

**Outputs**:
```json
{
  "faq": [{"question": "string", "answer": "string"}],
  "tips": ["string"],
  "warnings": ["string"],
  "resources": [{"title": "string", "url": "string"}]
}
```

## SEO Optimization (3 Agents)

### KeywordExtractionAgent

**Purpose**: Extracts relevant keywords from source content

**Inputs**:
```json
{
  "content": "string",
  "max_keywords": "number (default: 10)"
}
```

**Outputs**:
```json
{
  "keywords": [
    {"term": "string", "relevance": "number", "frequency": "number"}
  ],
  "primary_keyword": "string"
}
```

### KeywordInjectionAgent

**Purpose**: Strategically places keywords in content for SEO

**Inputs**:
```json
{
  "content": "string",
  "keywords": ["string"],
  "density_target": "number (default: 0.02)"
}
```

**Outputs**:
```json
{
  "optimized_content": "string",
  "keyword_density": {"keyword": "number"},
  "placements": "number"
}
```

### SEOMetadataAgent

**Purpose**: Generates meta titles, descriptions, and OpenGraph tags

**Inputs**:
```json
{
  "title": "string",
  "content": "string",
  "keywords": ["string"]
}
```

**Outputs**:
```json
{
  "meta_title": "string (50-60 chars)",
  "meta_description": "string (150-160 chars)",
  "og_title": "string",
  "og_description": "string",
  "og_image": "string (optional)"
}
```

## Code Generation (4 Agents)

### CodeGenerationAgent

**Purpose**: Creates working code examples from API documentation

**Inputs**:
```json
{
  "api_context": ["string (API docs)"],
  "language": "string (csharp|java|python|javascript)",
  "use_case": "string"
}
```

**Outputs**:
```json
{
  "code": "string",
  "language": "string",
  "explanation": "string",
  "imports": ["string"]
}
```

**Special Features**: Uses phi4:14b model (optimized for code)

### CodeValidationAgent

**Purpose**: Validates generated code against API specifications

**Inputs**:
```json
{
  "code": "string",
  "language": "string",
  "api_spec": "object"
}
```

**Outputs**:
```json
{
  "is_valid": "boolean",
  "errors": ["string"],
  "warnings": ["string"],
  "suggestions": ["string"]
}
```

### APIComplianceAgent

**Purpose**: Ensures code follows API best practices

**Inputs**:
```json
{
  "code": "string",
  "api_name": "string"
}
```

**Outputs**:
```json
{
  "compliant": "boolean",
  "issues": ["string"],
  "best_practices": ["string"]
}
```

### GistUploadAgent

**Purpose**: Uploads code samples to GitHub Gists

**Inputs**:
```json
{
  "code": "string",
  "filename": "string",
  "description": "string",
  "public": "boolean (default: true)"
}
```

**Outputs**:
```json
{
  "gist_id": "string",
  "url": "string",
  "html_url": "string"
}
```

**Requirements**: `GITHUB_TOKEN` environment variable

## Publishing (4 Agents)

### FrontmatterAgent

**Purpose**: Generates Hugo/Jekyll frontmatter with metadata

**Inputs**:
```json
{
  "title": "string",
  "metadata": "object",
  "keywords": ["string"],
  "categories": ["string"]
}
```

**Outputs**:
```yaml
---
title: "Blog Post Title"
date: "2025-11-17T10:30:00Z"
draft: false
slug: "blog-post-slug"
description: "Post description"
keywords: ["keyword1", "keyword2"]
categories: ["Category"]
tags: ["Tag1", "Tag2"]
---
```

### SlugGenerationAgent

**Purpose**: Creates SEO-friendly URL slugs

**Inputs**:
```json
{
  "title": "string",
  "max_length": "number (default: 60)"
}
```

**Outputs**:
```json
{
  "slug": "string (lowercase, hyphenated)",
  "alternatives": ["string"]
}
```

### ContentAssemblyAgent

**Purpose**: Combines all sections into final blog post

**Inputs**:
```json
{
  "frontmatter": "string",
  "introduction": "string",
  "sections": ["string"],
  "conclusion": "string",
  "supplementary": "object",
  "code_samples": ["object"]
}
```

**Outputs**:
```json
{
  "full_content": "string (complete blog post)",
  "word_count": "number",
  "structure": "object"
}
```

### FileWriterAgent

**Purpose**: Writes final content to disk with proper formatting

**Inputs**:
```json
{
  "content": "string",
  "output_path": "string",
  "format": "string (markdown|html)"
}
```

**Outputs**:
```json
{
  "file_path": "string",
  "bytes_written": "number",
  "success": "boolean"
}
```

## Research & Intelligence (6 Agents)

### TrendsResearchAgent

**Purpose**: Google Trends keyword research and analysis

**Inputs**:
```json
{
  "keywords": ["string"],
  "timeframe": "string (default: 'today 12-m')",
  "geo": "string (default: 'US')"
}
```

**Outputs**:
```json
{
  "interest_over_time": "object",
  "related_queries": ["string"],
  "trending_searches": ["string"],
  "recommendations": ["string"]
}
```

**Requirements**: Internet connection, pytrends library

### ContentIntelligenceAgent

**Purpose**: Analyzes semantic relationships and content quality

**Inputs**:
```json
{
  "content": "string",
  "reference_content": ["string (optional)"]
}
```

**Outputs**:
```json
{
  "readability_score": "number",
  "semantic_density": "number",
  "similar_content": ["object"],
  "quality_score": "number"
}
```

### TopicIdentificationAgent

**Purpose**: Discovers high-value topics from knowledge base

**Inputs**:
```json
{
  "kb_path": "string",
  "max_topics": "number (default: 50)"
}
```

**Outputs**:
```json
{
  "topics": [
    {
      "title": "string",
      "priority": "number",
      "source_file": "string",
      "keywords": ["string"]
    }
  ],
  "total_discovered": "number"
}
```

### DuplicationCheckAgent

**Purpose**: Detects duplicate or highly similar content

**Inputs**:
```json
{
  "current_topic": {
    "title": "string",
    "slug": "string"
  },
  "existing_content_dir": "string"
}
```

**Outputs**:
```json
{
  "duplication_check_passed": "boolean",
  "duplication_similarity": "number (0-1)",
  "duplication_reason": "string",
  "similar_files": ["string"]
}
```

### APISearchAgent

**Purpose**: Searches API documentation for code generation context

**Inputs**:
```json
{
  "query": "string",
  "api_name": "string"
}
```

**Outputs**:
```json
{
  "context_api": ["string (relevant API docs)"],
  "methods": ["string"],
  "examples": ["string"]
}
```

### BlogSearchAgent

**Purpose**: Finds relevant existing blog posts for context

**Inputs**:
```json
{
  "query": "string",
  "max_results": "number (default: 5)"
}
```

**Outputs**:
```json
{
  "context_blog": ["string"],
  "urls": ["string"],
  "summaries": ["string"]
}
```

## Support & Validation (5 Agents)

### ValidationAgent

**Purpose**: Comprehensive content quality and completeness checks

**Inputs**:
```json
{
  "content": "string",
  "requirements": "object (validation rules)"
}
```

**Outputs**:
```json
{
  "is_valid": "boolean",
  "errors": ["string"],
  "warnings": ["string"],
  "score": "number (0-100)"
}
```

### QualityGateAgent

**Purpose**: Enforces quality standards before publishing

**Inputs**:
```json
{
  "content": "string",
  "metadata": "object",
  "quality_threshold": "number (default: 80)"
}
```

**Outputs**:
```json
{
  "passed": "boolean",
  "quality_score": "number",
  "issues": ["string"],
  "recommendations": ["string"]
}
```

### LinkValidationAgent

**Purpose**: Validates all URLs in content are accessible

**Inputs**:
```json
{
  "content": "string",
  "timeout": "number (default: 10)"
}
```

**Outputs**:
```json
{
  "total_links": "number",
  "valid_links": "number",
  "invalid_links": ["string"],
  "broken_links": ["object"]
}
```

### CompletenessGateAgent

**Purpose**: Checks for required fields and sections

**Inputs**:
```json
{
  "content": "string",
  "required_sections": ["string"]
}
```

**Outputs**:
```json
{
  "complete": "boolean",
  "missing_sections": ["string"],
  "empty_sections": ["string"]
}
```

### HealthMonitorAgent

**Purpose**: Monitors agent health and performance

**Inputs**:
```json
{
  "agent_id": "string (optional, all agents if not specified)"
}
```

**Outputs**:
```json
{
  "agents": [
    {
      "id": "string",
      "status": "string (healthy|degraded|unhealthy)",
      "last_execution": "datetime",
      "success_rate": "number",
      "avg_duration": "number"
    }
  ]
}
```

## Ingestion (6 Agents)

### KBIngestionAgent

**Purpose**: Processes knowledge base articles

### DocsIngestionAgent

**Purpose**: Ingests product documentation

### APIIngestionAgent

**Purpose**: Parses API reference materials

### BlogIngestionAgent

**Purpose**: Processes existing blog posts

### TutorialIngestionAgent

**Purpose**: Handles tutorial content

### FormatExtractionAgent

**Purpose**: Extracts structured data from various formats

**All Ingestion Agents** have similar interfaces:

**Inputs**:
```json
{
  "path": "string (file or directory)",
  "recursive": "boolean (default: false)",
  "file_pattern": "string (default: '*.md')"
}
```

**Outputs**:
```json
{
  "files_processed": "number",
  "files_skipped": "number",
  "content": ["object"],
  "metadata": "object"
}
```

## Using Agents

### Via CLI

```bash
# Invoke single agent
python ucop_cli.py agent invoke outline_creation_agent \
  --input '{"kb_content": "...", "current_topic": {...}}'

# List all agents
python ucop_cli.py agent list

# Filter by category
python ucop_cli.py agent list --category content
```

### Via Python

```python
from src.mcp.handlers import handle_agent_invoke
import asyncio

async def test_agent():
    params = {
        "agent_id": "outline_creation_agent",
        "input": {
            "kb_content": "Article content here...",
            "current_topic": {
                "title": "My Topic",
                "keywords": ["python", "tutorial"]
            }
        }
    }
    
    result = await handle_agent_invoke(params)
    print(result['output'])

asyncio.run(test_agent())
```

### Via Web API

```bash
curl -X POST http://localhost:8000/mcp/request \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "agents/invoke",
    "params": {
      "agent_id": "outline_creation_agent",
      "input": {...}
    }
  }'
```

## Agent Configuration

All agents configured in `config/agents.yaml`. See [configuration.md](configuration.md) for details.

## Creating Custom Agents

See [extensibility.md](extensibility.md) for guide on creating custom agents.
