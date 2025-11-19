# Architecture

## Overview

UCOP is an event-driven, microservice-oriented platform for intelligent content generation. Built on LangGraph orchestration framework with 34 specialized agents, it provides a layered architecture supporting CLI, web interfaces, and programmatic access.

## System Architecture

### Architectural Layers

```
┌─────────────────────────────────────────────────────────────┐
│                   Interface Layer                            │
│         CLI (ucop_cli.py) | Web UI (FastAPI + React)        │
├─────────────────────────────────────────────────────────────┤
│                 Orchestration Layer                          │
│  LangGraph Workflows | Mesh Executor | Job Engine           │
│  Hot Reload | Checkpoint Manager | Parallel Executor        │
├─────────────────────────────────────────────────────────────┤
│                   Agent Mesh (34 Agents)                     │
│  Ingestion | Content | SEO | Code | Publishing | Research   │
├─────────────────────────────────────────────────────────────┤
│              Engine & Services Layer                         │
│  Templates | Validation | LLM Services | Database            │
│  Embeddings | Gist Service | Link Checker | Trends           │
├─────────────────────────────────────────────────────────────┤
│              Storage & External Services                     │
│  ChromaDB | Ollama | Gemini | OpenAI | GitHub | Filesystem  │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Interface Layer

#### CLI Interface (`ucop_cli.py`)
- 40+ commands across 7 categories
- Supports generation, jobs, config, agents, checkpoints, visualization, mesh
- Direct access to all system capabilities
- JSON input/output for automation

#### Web Interface (`start_web.py`)
- FastAPI backend with RESTful API
- React frontend with visual workflow editor
- WebSocket support for real-time monitoring
- MCP protocol endpoints

### 2. Orchestration Layer

#### LangGraph Executor
**Purpose**: Execute agents in directed acyclic graphs  
**Features**:
- State management with checkpoints
- Conditional branching
- Parallel execution
- Error recovery

**Location**: `src/orchestration/langgraph_executor.py`

#### Job Execution Engine
**Purpose**: Manage job lifecycle and execution  
**Features**:
- Job queuing and scheduling
- Status tracking (pending, running, completed, failed)
- Checkpoint persistence for resume/retry
- Resource monitoring

**Location**: `src/orchestration/job_execution_engine.py`

#### Mesh Executor
**Purpose**: Dynamic agent discovery and execution  
**Features**:
- On-demand agent invocation
- Capability-based routing
- Service mesh patterns
- Adaptive workflows

**Location**: `src/orchestration/mesh_executor.py`

#### Hot Reload System
**Purpose**: Update agents and workflows without restart  
**Features**:
- File system watching
- Dynamic module reloading
- Configuration refresh
- Zero-downtime updates

**Location**: `src/orchestration/hot_reload.py`

#### Checkpoint Manager
**Purpose**: State persistence and recovery  
**Features**:
- Automatic checkpoint creation
- Manual checkpoint save/restore
- Checkpoint cleanup and pruning
- Resume from failure points

**Location**: `src/orchestration/checkpoint_manager.py`

#### Parallel Executor
**Purpose**: Execute independent agents concurrently  
**Features**:
- Automatic dependency resolution
- Resource-aware scheduling
- Configurable concurrency limits
- Error isolation

**Location**: `src/orchestration/parallel_executor.py`

### 3. Agent Mesh

#### Agent Base Classes

**Agent** (`src/core/agent_base.py`)
- Base class for all agents
- Contract definition and enforcement
- Event subscription/publishing
- Lifecycle management

**SelfCorrectingAgent** (`src/utils/learning.py`)
- Extends Agent with retry logic
- Validation and error recovery
- Learning from failures
- Adaptive behavior

#### Agent Registry
**Purpose**: Track and discover agents  
**Features**:
- Auto-discovery at startup
- Health monitoring
- Capability indexing
- Dynamic loading

**Location**: `src/orchestration/agent_registry.py`

#### Event Bus
**Purpose**: Agent communication backbone  
**Features**:
- Publish/subscribe pattern
- Event filtering
- Correlation tracking
- Async delivery

**Location**: `src/core/event_bus.py`

### 4. Services Layer

#### LLM Service
**Purpose**: Multi-provider LLM access  
**Providers**: Ollama (local), Google Gemini, OpenAI  
**Features**:
- Automatic fallback chain
- Rate limiting
- Token counting
- JSON mode with schema enforcement

**Location**: `src/services/llm_service.py`

#### Database Service
**Purpose**: Vector store and embeddings  
**Technology**: ChromaDB  
**Features**:
- Document ingestion
- Semantic similarity search
- Collection management
- Metadata filtering

**Location**: `src/services/database_service.py`

#### Embedding Service
**Purpose**: Text vectorization  
**Model**: sentence-transformers/all-MiniLM-L6-v2  
**Features**:
- Batch processing
- Caching
- Dimensionality reduction
- Similarity computation

**Location**: `src/services/embedding_service.py`

#### Gist Service
**Purpose**: GitHub Gist integration  
**Features**:
- Upload code snippets
- README generation
- URL validation
- Error handling

**Location**: `src/services/gist_service.py`

#### Link Checker
**Purpose**: URL validation  
**Features**:
- HTTP HEAD requests
- Timeout handling
- Retry logic
- Status code validation

**Location**: `src/services/link_checker.py`

#### Trends Service
**Purpose**: Google Trends integration  
**Features**:
- Keyword research
- Trend analysis
- Regional data
- Time series queries

**Location**: `src/services/trends_service.py`

### 5. Template System

#### Template Registry
**Purpose**: Manage content templates  
**Types**:
- Blog templates
- Code templates
- Documentation templates
- Prompt templates
- Schema definitions

**Location**: `src/core/template_registry.py`

#### Schema Definitions
**Purpose**: JSON schemas for validation  
**Schemas**:
- Outline schema
- Topic schema
- Code block schema
- Frontmatter schema
- Metadata schema

**Location**: `config/schemas.py`

### 6. Utility Modules

#### Content Utils
**Purpose**: Text processing and manipulation  
**Functions**:
- Markdown parsing and generation
- Code block extraction
- Deduplication
- Keyword injection
- License insertion

**Location**: `src/utils/content_utils.py`

#### Tone Utils
**Purpose**: Content style and tone  
**Functions**:
- Tone configuration loading
- Section prompt enhancement
- Heading generation
- Style enforcement

**Location**: `src/utils/tone_utils.py`

#### Validation Utils
**Purpose**: Content quality checking  
**Functions**:
- Code quality validation
- API compliance checking
- Completeness gates
- Link validation

**Location**: `src/utils/validation_utils.py`

## Data Flow

### Standard Blog Generation Workflow

```
1. Ingestion
   ├── ingest_kb_node → Read KB article, create embeddings
   └── Store in ChromaDB

2. Topic Discovery
   ├── identify_topics_node → Extract topics from KB
   └── topic_prep_node → Prepare topic for processing

3. Context Gathering
   ├── kb_search_node → Search KB for context
   ├── blog_search_node → Search existing blogs
   ├── api_search_node → Search API docs
   └── check_duplication_node → Check for duplicates

4. Content Generation
   ├── create_outline_node → Generate outline
   ├── introduction_writer_node → Write intro
   ├── section_writer_node → Write sections
   ├── conclusion_writer_node → Write conclusion
   └── supplementary_content_node → Generate FAQ/tips

5. Code Generation (conditional)
   ├── code_generation_node → Generate C# code
   ├── code_validation_node → Validate code
   ├── license_injection_node → Add license header
   ├── gist_readme_node → Create Gist README
   └── gist_upload_node → Upload to GitHub

6. SEO Optimization
   ├── keyword_extraction_node → Extract keywords
   ├── keyword_injection_node → Inject keywords
   └── seo_metadata_node → Generate metadata

7. Assembly & Publishing
   ├── content_assembly_node → Assemble all parts
   ├── frontmatter_node → Add frontmatter
   ├── link_validation_node → Validate URLs
   └── write_file_node → Write to disk
```

## Orchestration Modes

### 1. Predefined Workflow Mode
**Use Case**: Standard, repeatable content generation  
**Execution**: Linear DAG with conditional branches  
**Benefits**: Predictable, testable, production-ready  
**Configuration**: YAML workflow definitions

### 2. Mesh Mode
**Use Case**: Dynamic, adaptive workflows  
**Execution**: Agents discover and invoke each other  
**Benefits**: Flexible, intelligent routing  
**Configuration**: Agent capabilities and registry

### 3. Visual Workflow Mode
**Use Case**: Interactive workflow design  
**Execution**: User-designed graph visualization  
**Benefits**: No-code interface, real-time feedback  
**Configuration**: Drag-and-drop canvas in web UI

## Configuration System

### Configuration Files

**`config/main.yaml`**
- LLM provider settings
- Workflow defaults
- Vector store configuration
- System-wide parameters

**`config/agents.yaml`**
- Agent definitions (34 agents)
- Input/output contracts
- Resource limits
- Capabilities

**`config/tone.json`**
- Content style guidelines
- Section templates
- Tone parameters

**`config/validation.yaml`**
- Quality gates
- Validation rules
- Completeness checks

### Environment Variables

```bash
# LLM Providers
OLLAMA_BASE_URL=http://localhost:11434
GOOGLE_API_KEY=<key>
OPENAI_API_KEY=<key>

# GitHub
GITHUB_TOKEN=<token>

# Paths
CHROMA_DB_PATH=./chroma_db
OUTPUT_PATH=./output
```

## State Management

### Job State
- **Status**: pending, running, completed, failed, cancelled
- **Progress**: Percentage complete, current agent
- **Checkpoints**: Named restore points
- **Metadata**: Job ID, created_at, updated_at, duration

### Workflow State
- **Current Node**: Active agent ID
- **Data**: Accumulated outputs from agents
- **Context**: Shared state across agents
- **History**: Execution trace

### Agent State
- **Health**: healthy, degraded, failed
- **Metrics**: Success rate, avg latency, error count
- **Load**: Current active invocations
- **Version**: Code version for hot reload

## Monitoring & Observability

### Metrics
- Job throughput (jobs/hour)
- Agent latency (p50, p95, p99)
- Error rates per agent
- Resource utilization (CPU, memory)
- LLM token usage

### Logging
- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR
- Context propagation (correlation IDs)
- Agent execution traces

### Visualization
- Real-time workflow graphs
- Agent dependency visualization
- Performance bottleneck analysis
- Live execution monitoring

## Security

### API Key Management
- Environment variable isolation
- No keys in configuration files
- Secure key rotation
- Per-service credentials

### Validation
- Input schema validation
- Output schema validation
- Code injection prevention
- Path traversal protection

### Rate Limiting
- Per-provider rate limits
- Automatic backoff
- Quota management
- Fair scheduling

## Scalability

### Horizontal Scaling
- Multiple worker processes
- Distributed job queue
- Shared vector store
- Load balancing

### Vertical Scaling
- Configurable resource limits per agent
- Memory management
- Parallel execution within jobs
- Streaming for large content

### Caching
- LLM response caching
- Embedding caching
- Template caching
- Configuration caching

## Extension Points

### Custom Agents
1. Extend `Agent` base class
2. Define contract
3. Implement `execute()` method
4. Register in `config/agents.yaml`

### Custom Workflows
1. Define YAML workflow
2. Specify agent sequence
3. Add conditional logic
4. Register workflow

### Custom Templates
1. Create template YAML
2. Define placeholders
3. Add to template registry
4. Reference in agents

### Custom Services
1. Implement service interface
2. Add to services layer
3. Inject into agents
4. Configure in `config/main.yaml`

## Technology Stack

### Core
- **Python 3.10+**: Primary language
- **LangGraph**: Workflow orchestration
- **FastAPI**: Web framework
- **React**: Frontend UI

### Storage
- **ChromaDB**: Vector database
- **SQLite**: Job persistence
- **Filesystem**: Content output

### LLMs
- **Ollama**: Local inference
- **Google Gemini**: Cloud LLM
- **OpenAI**: Cloud LLM

### Libraries
- **sentence-transformers**: Embeddings
- **PyYAML**: Configuration
- **pytest**: Testing
- **Pydantic**: Schema validation

## Performance Characteristics

- **Throughput**: 10-15 blogs/hour (single worker)
- **Latency**: 3-8 minutes per blog post
- **Concurrency**: Up to 5 parallel agents
- **Memory**: 2-4 GB per worker
- **Token Usage**: 10K-20K tokens per blog

---

*This documentation is part of the UCOP project. For more information, see the [main README](../README.md).*
