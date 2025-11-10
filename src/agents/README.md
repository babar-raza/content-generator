# Agents Module

## Overview

This module contains 30+ specialized agents organized by function. Each agent is a self-contained unit that performs a specific task in the content generation pipeline.

## Organization

### Content Agents (`content/`)
Generate written content for blog posts.

- `outline_creation.py` - Creates structured content outlines from source material
- `introduction_writer.py` - Writes engaging introductions
- `section_writer.py` - Generates detailed content sections
- `conclusion_writer.py` - Crafts compelling conclusions
- `supplementary_content.py` - Adds FAQs, tips, and additional value
- `content_assembly.py` - Assembles all content pieces into final output

### SEO Agents (`seo/`)
Optimize content for search engines.

- `keyword_extraction.py` - Extracts relevant keywords from source
- `keyword_injection.py` - Strategically places keywords throughout content
- `seo_metadata.py` - Generates meta titles, descriptions, and tags

### Code Agents (`code/`)
Handle code generation and validation.

- `code_generation.py` - Creates working code examples
- `code_validation.py` - Validates code syntax and functionality
- `api_compliance.py` - Ensures code follows API specifications
- `license_validator.py` - Checks code licensing requirements

### Publishing Agents (`publishing/`)
Prepare content for publication.

- `frontmatter_enhanced.py` - Generates Hugo frontmatter with metadata
- `gist_upload.py` - Uploads code examples to GitHub Gists
- `slug_generation.py` - Creates SEO-friendly URLs

### Research Agents (`research/`)
Gather intelligence and insights.

- `trends_research.py` - Performs Google Trends keyword research
- `content_intelligence.py` - Analyzes semantic relationships and linking
- `competitor_analysis.py` - Studies top-ranking content

### Support Agents (`support/`)
Quality assurance and validation.

- `validation.py` - Validates content quality and completeness
- `quality_gate.py` - Enforces quality standards
- `error_recovery.py` - Handles failures and retries

### Ingestion Agents (`ingestion/`)
Load and parse input content.

- `kb_ingestion.py` - Parses knowledge base articles
- `document_parser.py` - Extracts text from various formats

## Agent Base Class

All agents inherit from `base.py` which provides:

```python
class Agent:
    def execute(self, input_data: Dict) -> Dict:
        """Standard execution interface"""
        pass
    
    def validate_input(self, input_data: Dict) -> bool:
        """Validate input data"""
        pass
    
    def validate_output(self, output: Dict) -> bool:
        """Validate output data"""
        pass
```

## Usage

```python
from src.agents.content.outline_creation import OutlineCreationAgent

agent = OutlineCreationAgent()
result = agent.execute({
    'source_content': 'Article content here...',
    'target_audience': 'developers'
})
```

## Agent Discovery

Agents are automatically discovered and registered by `src/orchestration/agent_scanner.py` based on:
- Class inheritance from `Agent`
- Presence in agent directories
- Metadata annotations

## Dependencies

Agents depend on:
- `src.core` - Core abstractions and utilities
- `src.engine` - Execution engine for context management
- LLM providers (Ollama, Gemini, OpenAI)
