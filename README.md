# UCOP - Unified Content Operations Platform

A production-ready, autonomous content generation system powered by LangGraph workflows and 30+ specialized agents. UCOP transforms knowledge base articles into SEO-optimized blog posts with automated validation, code generation, and multi-provider LLM integration.

## Features

- **Autonomous Agent Mesh**: 30+ MCP-compliant agents for content generation, SEO optimization, and validation
- **Multi-LLM Support**: Ollama (local), Gemini, OpenAI with intelligent fallback and rate limiting
- **Event-Driven Architecture**: LangGraph workflows with checkpoint persistence and hot-reload
- **Real-Time Orchestration**: WebSocket-based job control, live monitoring, and visual debugging
- **Production-Ready**: Comprehensive validation, error handling, and performance optimization
- **CLI & Web UI**: Dual interfaces with full feature parity

## Quick Start

### Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys and settings

# 3. Run setup (initializes local models and checks system)
./setup.sh  # Linux/Mac
setup.bat   # Windows
```

### Basic Usage

**CLI Mode:**
```bash
# Generate a single blog post
python ucop_cli.py generate --input kb_article.md --output output/

# Process batch
python ucop_cli.py batch --manifest batch.json

# List available workflows
python ucop_cli.py viz workflows

# Monitor job execution
python ucop_cli.py job list
```

**Web UI Mode:**
```bash
# Start web server
python start_web.py

# Open browser to http://localhost:8000
# Access visual workflow editor, real-time monitoring, and job control
```

## Architecture

UCOP uses a layered architecture with event-driven orchestration:

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI / Web UI                          │
├─────────────────────────────────────────────────────────────┤
│              Orchestration & Job Execution                   │
│   (LangGraph Workflows, State Management, Checkpoints)       │
├─────────────────────────────────────────────────────────────┤
│                    Agent Mesh Layer                          │
│  (30+ Specialized Agents: Content, SEO, Code, Publishing)    │
├─────────────────────────────────────────────────────────────┤
│                   Engine & Services                          │
│   (Unified Engine, Template Registry, Validation Gates)      │
├─────────────────────────────────────────────────────────────┤
│                  LLM Providers & Storage                     │
│        (Ollama, Gemini, OpenAI, ChromaDB, Embeddings)        │
└─────────────────────────────────────────────────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for detailed information.

## Documentation

- **[Architecture Overview](docs/architecture.md)** - System design and component interaction
- **[Workflows](docs/workflows.md)** - LangGraph workflow definitions and agent orchestration
- **[MCP Endpoints](docs/mcp_endpoints.md)** - Model Context Protocol integration
- **[Visual Orchestration](docs/visual_orchestration.md)** - Web UI workflow editor and debugger
- **[CLI Reference](docs/cli.md)** - Complete command-line interface documentation
- **[Datastore](docs/datastore.md)** - Vector database and embedding management
- **[Agent Layers](docs/layers.md)** - Agent organization and specialization

## Agent Overview

UCOP includes 30+ specialized agents organized into layers:

### Content Agents
- **OutlineCreationAgent**: Generates structured content outlines
- **IntroductionWriterAgent**: Creates engaging introductions
- **SectionWriterAgent**: Writes detailed content sections
- **ConclusionWriterAgent**: Crafts compelling conclusions
- **SupplementaryContentAgent**: Adds FAQs, tips, and additional content

### SEO Agents
- **KeywordExtractionAgent**: Extracts relevant keywords from source
- **KeywordInjectionAgent**: Strategically places keywords
- **SEOMetadataAgent**: Generates titles, descriptions, and meta tags

### Code Agents
- **CodeGenerationAgent**: Creates working code examples
- **CodeValidationAgent**: Validates code against API specifications
- **GistUploadAgent**: Uploads code to GitHub Gists

### Publishing Agents
- **FrontmatterAgent**: Generates Hugo frontmatter with metadata
- **SlugGenerationAgent**: Creates SEO-friendly URLs

### Research & Support
- **TrendsResearchAgent**: Uses Google Trends for keyword research
- **ContentIntelligenceAgent**: Analyzes semantic relationships
- **ValidationAgent**: Ensures content quality and completeness

## Configuration

### Main Configuration (`config/main.yaml`)

```yaml
llm:
  providers:
    - ollama    # Local models (primary)
    - gemini    # Google Gemini (fallback)
    - openai    # OpenAI (fallback)
  
  models:
    ollama: "qwen2.5:14b"
    gemini: "gemini-1.5-pro"
    openai: "gpt-4o"

workflows:
  default_profile: "blog_generation"
  checkpoint_enabled: true
  hot_reload: true

vectorstore:
  provider: "chromadb"
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
```

### Agent Configuration (`config/agents.yaml`)

Defines all 30+ agents with their capabilities, dependencies, and LLM preferences. See file for complete configuration.

## MCP Endpoints

UCOP exposes MCP-compliant endpoints for agent orchestration:

- `workflow.execute` - Execute a workflow with given inputs
- `workflow.status` - Get execution status and metrics
- `workflow.checkpoint.list` - List available checkpoints
- `workflow.checkpoint.restore` - Restore from checkpoint
- `agent.invoke` - Invoke a specific agent directly
- `agent.list` - List all available agents
- `realtime.subscribe` - Subscribe to real-time updates

See [docs/mcp_endpoints.md](docs/mcp_endpoints.md) for complete API reference.

## Testing

```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
pytest tests/e2e/           # End-to-end tests

# Run with coverage
pytest --cov=src --cov-report=html

# Performance tests
pytest tests/performance/
```

## Development

### Project Structure

```
.
├── config/              # Configuration files
├── docs/               # Documentation
├── examples/           # Example inputs and workflows
├── src/
│   ├── agents/         # Agent implementations
│   ├── core/           # Core abstractions and utilities
│   ├── engine/         # Execution engine
│   ├── mcp/           # MCP protocol implementation
│   ├── mesh/          # Agent mesh coordination
│   ├── orchestration/  # Workflow orchestration
│   ├── services/       # Support services
│   ├── utils/         # Utility functions
│   ├── visualization/ # Visual debugging and monitoring
│   └── web/           # Web UI
├── templates/         # Content templates
├── tests/            # Test suites
├── tools/            # Development and maintenance tools
├── ucop_cli.py       # CLI entry point
└── start_web.py      # Web UI entry point
```

### Development Tools

```bash
# Validate system before deployment
python tools/pre_deploy_check.py

# Check production readiness
python tools/validate_production.py

# Run performance benchmarks
python tools/perf_runner.py

# Maintain and optimize project
python tools/maintain.py
```

## Performance

UCOP is optimized for production use:

- **Concurrent Execution**: Parallel agent execution with dependency resolution
- **Checkpoint Persistence**: Resume workflows from any point
- **Rate Limiting**: Automatic backoff and retry with multiple providers
- **Caching**: Template and embedding caching for faster execution
- **GPU Support**: Optional GPU acceleration for local models

See [docs/performance.md](docs/performance.md) for benchmarks and optimization guides.

## License

Copyright © 2024 Aspose.net. All rights reserved.

## Support

For issues, questions, or contributions:
- **Issues**: File issues in the project repository
- **Documentation**: See the [docs/](docs/) directory
- **Examples**: Check the [examples/](examples/) directory
