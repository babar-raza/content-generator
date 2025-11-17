# UCOP - Unified Content Operations Platform

A production-ready, autonomous content generation system powered by LangGraph workflows and 38 specialized agents. UCOP transforms knowledge base articles into SEO-optimized blog posts with automated validation, code generation, and multi-provider LLM integration.

## Overview

UCOP is an event-driven, microservice-oriented platform for intelligent content generation and transformation. Built on modern Python async patterns and the LangGraph orchestration framework, it provides both CLI and web-based interfaces for automating content workflows at scale.

### Key Features

- **38 Specialized Agents**: MCP-compliant agents organized into content, SEO, code, publishing, research, and support categories
- **Multi-LLM Support**: Intelligent fallback cascade across Ollama (local), Google Gemini, and OpenAI with automatic rate limiting
- **Event-Driven Architecture**: LangGraph workflows with checkpoint persistence, hot-reload, and dependency resolution
- **Real-Time Orchestration**: WebSocket-based job control, live monitoring, and visual workflow debugging
- **Production-Ready**: Comprehensive validation gates, error handling, retry logic, and performance optimization
- **Dual Interface**: Full-featured CLI (23 commands) and React-based web UI with MCP protocol endpoints
- **Extensible Design**: Plugin architecture for custom agents, templates, and workflows

## Quick Start

### Prerequisites

- **Python 3.8+** (3.10+ recommended)
- **Ollama** (optional, for local LLM inference) - Download from https://ollama.ai
- **Node.js 18+** (for web UI development)
- **Git** (for code management)

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd ucop

# 2. Run setup script
# Windows:
setup.bat

# Linux/Mac:
chmod +x setup.sh
./setup.sh

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys and settings

# 4. Verify installation
python ucop_cli.py --help
```

### First Run - CLI

```bash
# Generate a single blog post from a knowledge base article
python ucop_cli.py generate \
    --input kb_articles/example.md \
    --output output/ \
    --workflow blog_generation

# Process a batch of articles
python ucop_cli.py batch --manifest batch_config.json

# List available workflows
python ucop_cli.py viz workflows

# Monitor running jobs
python ucop_cli.py job list --status running
```

### First Run - Web UI

```bash
# Start the web server
python start_web.py

# Access the UI
# Open browser to http://localhost:8000

# The web UI provides:
# - Visual workflow editor with drag-and-drop agents
# - Real-time job monitoring
# - Agent status dashboard
# - Configuration inspector
# - Performance metrics
```

## Architecture Overview

UCOP follows a layered, event-driven architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI / Web UI                             │
│         (ucop_cli.py / FastAPI + React)                      │
├─────────────────────────────────────────────────────────────┤
│              Orchestration Layer                             │
│   (LangGraph, Job Execution, Checkpoints, Hot Reload)        │
├─────────────────────────────────────────────────────────────┤
│                  Agent Mesh (38 Agents)                      │
│  Content│SEO│Code│Publishing│Research│Support│Ingestion      │
├─────────────────────────────────────────────────────────────┤
│              Engine & Services Layer                         │
│  (Unified Engine, Templates, Validation, Slug Generation)    │
├─────────────────────────────────────────────────────────────┤
│              LLM Providers & Storage                         │
│   (Ollama│Gemini│OpenAI, ChromaDB, Embeddings, Gists)        │
└─────────────────────────────────────────────────────────────┘
```

**Data Flow**: Input → Ingestion → Planning → Content Generation → Code Generation (conditional) → SEO Optimization → Publishing → Validation → Output

## Documentation

### Core Documentation

- **[Architecture & Components](docs/architecture.md)** - System design, layers, and component interaction
- **[Getting Started](docs/getting-started.md)** - Detailed installation and configuration guide
- **[CLI Reference](docs/cli.md)** - Complete command-line interface documentation
- **[Web UI Guide](docs/web-ui.md)** - Web interface features and usage
- **[Configuration](docs/configuration.md)** - Environment variables, YAML configs, and settings

### Features & Workflows

- **[Workflows & Pipelines](docs/workflows.md)** - LangGraph workflow definitions and execution
- **[Agent Reference](docs/agents.md)** - All 38 agents with inputs, outputs, and capabilities
- **[MCP Endpoints](docs/mcp-endpoints.md)** - Model Context Protocol API reference
- **[Content Intelligence](docs/content-intelligence.md)** - Vector stores, semantic search, and embeddings

### Operations & Development

- **[Deployment Guide](docs/deployment.md)** - Docker, production setup, and scaling
- **[Testing & QA](docs/testing.md)** - Unit, integration, E2E, and performance tests
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues, debugging, and solutions
- **[Performance Tuning](docs/performance.md)** - Optimization, caching, and resource management

### Advanced Topics

- **[Extensibility](docs/extensibility.md)** - Creating custom agents, workflows, and plugins
- **[Monitoring & Observability](docs/monitoring.md)** - Metrics, logging, and visualization
- **[Security](docs/security.md)** - API keys, validation, and best practices
- **[Design History & Legacy](docs/design-history.md)** - Historical decisions, deprecated features, and migrations

## Agent Overview

UCOP includes 38 specialized agents organized into functional categories:

### Content Generation (5 agents)
- **OutlineCreationAgent**: Structured content planning and section organization
- **IntroductionWriterAgent**: Engaging opening paragraphs with hooks
- **SectionWriterAgent**: Detailed body content for each outline section
- **ConclusionWriterAgent**: Compelling closings with CTAs
- **SupplementaryContentAgent**: FAQs, tips, warnings, and additional resources

### SEO Optimization (3 agents)
- **KeywordExtractionAgent**: Identifies relevant keywords from source content
- **KeywordInjectionAgent**: Strategic keyword placement for SEO
- **SEOMetadataAgent**: Generates meta titles, descriptions, and OpenGraph tags

### Code Generation (4 agents)
- **CodeGenerationAgent**: Creates working code examples from API docs
- **CodeValidationAgent**: Validates code against API specifications
- **APIComplianceAgent**: Ensures code follows API best practices
- **GistUploadAgent**: Uploads code samples to GitHub Gists

### Publishing (4 agents)
- **FrontmatterAgent**: Generates Hugo/Jekyll frontmatter with metadata
- **SlugGenerationAgent**: Creates SEO-friendly URL slugs
- **ContentAssemblyAgent**: Combines all sections into final output
- **FileWriterAgent**: Writes final content to disk

### Research & Intelligence (6 agents)
- **TrendsResearchAgent**: Google Trends keyword research and analysis
- **ContentIntelligenceAgent**: Semantic similarity and content relationships
- **TopicIdentificationAgent**: Discovers high-value topics from KB
- **DuplicationCheckAgent**: Detects duplicate/similar content
- **APISearchAgent**: Searches API documentation for code context
- **BlogSearchAgent**: Finds relevant blog posts for context

### Support & Validation (5 agents)
- **ValidationAgent**: Quality gates and completeness checks
- **QualityGateAgent**: Ensures output meets quality standards
- **LinkValidationAgent**: Validates URLs in content
- **CompletenessGateAgent**: Checks for required fields and sections
- **HealthMonitorAgent**: Monitors agent health and performance

### Ingestion (6 agents)
- **KBIngestionAgent**: Processes knowledge base articles
- **DocsIngestionAgent**: Ingests product documentation
- **APIIngestionAgent**: Parses API reference materials
- **BlogIngestionAgent**: Processes existing blog posts
- **TutorialIngestionAgent**: Handles tutorial content
- **FormatExtractionAgent**: Extracts structured data from various formats

## Configuration Quick Reference

### LLM Providers

```yaml
# config/main.yaml
llm:
  providers:
    - ollama    # Local models (primary)
    - gemini    # Google Gemini (fallback)
    - openai    # OpenAI (fallback)
  
  models:
    ollama: "qwen2.5:14b"
    gemini: "gemini-1.5-pro"
    openai: "gpt-4o"
  
  fallback_chain: true
  rate_limiting: true
```

### Workflow Settings

```yaml
workflows:
  default_profile: "blog_generation"
  checkpoint_enabled: true
  hot_reload: true
  parallel_execution: true
  max_parallel_agents: 5
```

### Vector Store

```yaml
vectorstore:
  provider: "chromadb"
  persist_directory: "./chroma_db"
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
```

## Testing

```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/unit/              # Unit tests (~200 tests)
pytest tests/integration/       # Integration tests (~50 tests)
pytest tests/e2e/              # End-to-end tests (~15 tests)

# Run with coverage
pytest --cov=src --cov-report=html
# View coverage report at htmlcov/index.html

# Performance and load tests
pytest tests/performance/ -v

# Smoke tests (quick validation)
pytest tests/test_imports_smoke.py -v
```

## Development Workflow

### Project Structure

```
ucop/
├── config/                 # YAML configurations
│   ├── main.yaml          # Pipeline and workflow settings
│   ├── agents.yaml        # Agent definitions (38 agents)
│   ├── tone.json          # Content tone guidelines
│   ├── perf.json          # Performance benchmarks
│   └── validation.yaml    # Validation rules
├── docs/                   # Documentation (this folder)
├── examples/               # Example inputs and manifests
├── src/
│   ├── agents/            # Agent implementations
│   │   ├── content/       # Content generation agents
│   │   ├── seo/           # SEO optimization agents
│   │   ├── code/          # Code generation agents
│   │   ├── publishing/    # Publishing workflow agents
│   │   ├── research/      # Research and intelligence agents
│   │   ├── support/       # Support and validation agents
│   │   └── ingestion/     # Content ingestion agents
│   ├── core/              # Core abstractions and utilities
│   ├── engine/            # Execution engine and device management
│   ├── mcp/               # Model Context Protocol implementation
│   ├── orchestration/     # LangGraph workflows and job execution
│   ├── services/          # Support services (LLM, DB, embeddings, etc.)
│   ├── utils/             # Utility functions and helpers
│   ├── visualization/     # Visual debugging and monitoring
│   └── web/               # FastAPI backend + React frontend
├── templates/             # Content templates and prompts
├── tests/                 # Test suites
├── tools/                 # Development and maintenance tools
├── ucop_cli.py           # CLI entry point
└── start_web.py          # Web UI entry point
```

### Development Tools

```bash
# Pre-deployment validation
python tools/pre_deploy_check.py

# Production readiness check
python tools/validate_production.py

# Performance benchmarks
python tools/perf_runner.py

# Project maintenance (cleanup, optimization)
python tools/maintain.py

# Validate configuration
python tools/validate.py

# Check for missing documentation
python tools/missing_docs_audit.py
```

## Performance Characteristics

- **Throughput**: ~10-15 blog posts per hour (single worker)
- **Latency**: 3-8 minutes per blog post (depending on complexity)
- **Concurrency**: Up to 5 parallel agents per workflow
- **Token Usage**: 10,000-20,000 tokens per blog post (varies by model)
- **Memory**: ~2-4 GB per worker process
- **Checkpoint Overhead**: <5% performance impact

See [docs/performance.md](docs/performance.md) for detailed benchmarks and optimization guides.

## Production Status

**Current Status**: ⚠️ Beta - Active Development

**Known Limitations**:
- 27 implemented features not yet exposed via web API (CLI-only)
- React UI expects some unmounted endpoints (see [docs/design-history.md](docs/design-history.md))
- Limited monitoring dashboard (API exists, UI in development)
- Checkpoint management via CLI only (web API pending)

**Production Readiness**: Estimated 2-3 weeks to production-ready (see [gaps/UCOP_Executive_Summary.md](gaps/UCOP_Executive_Summary.md))

## Support & Contributing

### Getting Help

- **Documentation**: Start with [docs/getting-started.md](docs/getting-started.md)
- **Troubleshooting**: See [docs/troubleshooting.md](docs/troubleshooting.md)
- **Examples**: Check [examples/](examples/) directory
- **Issues**: File issues in the project repository

### Development Guidelines

- **Code Style**: Follow PEP 8, use Black formatter
- **Type Hints**: Required for all public APIs
- **Tests**: Maintain >70% coverage for new code
- **Documentation**: Update docs for any API changes
- **Commits**: Use conventional commits format

### Useful Resources

- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **MCP Protocol**: https://modelcontextprotocol.io
- **FastAPI**: https://fastapi.tiangolo.com
- **React Flow**: https://reactflow.dev

## License

Copyright © 2024 Aspose Pty Ltd. All rights reserved.

## Version History

- **v1.2.0** (Current) - LangGraph integration, 38 agents, MCP compliance
- **v1.1.0** - Web UI with visual workflow editor
- **v1.0.0** - Initial release with CLI interface

See [docs/design-history.md](docs/design-history.md) for complete version history and migration guides.
