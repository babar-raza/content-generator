# Architecture Overview

## System Design

UCOP follows a layered, event-driven architecture built on LangGraph for workflow orchestration and agent coordination.

## Core Layers

### 1. Interface Layer (CLI & Web)

**CLI (`ucop_cli.py`)**
- Command-line interface for batch processing and automation
- Supports generation, batch processing, job control, and visualization
- Direct integration with unified engine

**Web UI (`src/web/app.py`)**
- FastAPI-based web application serving React-based interface
- MCP protocol endpoints for workflow operations
- Real-time WebSocket updates for job monitoring
- Visualization features accessible via `/api/visualization/*` endpoints

**Note:** React UI implementation located in `src/web/static/`. Backend (`src/web/app.py`) provides MCP endpoints for workflow operations.

### 2. Orchestration Layer

**Components:**
- `JobExecutionEngine`: Manages job lifecycle and state transitions
- `WorkflowCompiler`: Compiles workflow definitions into LangGraph graphs
- `CheckpointManager`: Handles workflow persistence and recovery
- `HotReloadMonitor`: Enables live workflow updates without restart

**Key Features:**
- Event-driven execution with state machines
- Checkpoint persistence for resume capability
- Dependency resolution and parallel execution
- Resource management and rate limiting

### 3. Agent Mesh Layer

**Agent Organization:**

```
agents/
├── content/         # Content generation agents
│   ├── outline_creation.py
│   ├── introduction_writer.py
│   ├── section_writer.py
│   ├── conclusion_writer.py
│   └── supplementary_content.py
├── seo/            # SEO optimization agents
│   ├── keyword_extraction.py
│   ├── keyword_injection.py
│   └── seo_metadata.py
├── code/           # Code-related agents
│   ├── code_generation.py
│   ├── code_validation.py
│   └── api_compliance.py
├── publishing/     # Publishing workflow agents
│   ├── frontmatter_enhanced.py
│   └── gist_upload.py
├── research/       # Research and analysis
│   ├── trends_research.py
│   └── content_intelligence.py
├── support/        # Support agents
│   ├── validation.py
│   └── quality_gate.py
└── ingestion/      # Content ingestion
    └── kb_ingestion.py
```

**Agent Base (`src/agents/base.py`):**
- Standard interface for all agents
- Input/output validation
- Error handling and retry logic
- Metrics collection

**Agent Discovery (`src/orchestration/agent_scanner.py`):**
- Automatic agent registration
- Capability detection
- Dependency graph construction

### 4. Engine & Services Layer

**Unified Engine (`src/engine/unified_engine.py`):**
- Central execution coordinator
- Manages agent lifecycle
- Handles context passing between agents
- Integrates with LLM providers

**Key Services:**
- `TemplateRegistry`: Manages content templates
- `SlugService`: Generates SEO-friendly URLs
- `ConfigValidator`: Validates configurations
- `CompletenessGate`: Ensures output quality

**Device Management (`src/engine/device/gpu_manager.py`):**
- GPU detection and allocation
- Automatic fallback to CPU
- Resource monitoring

### 5. LLM Provider Layer

**Provider Integration:**
- **Ollama**: Local model inference (primary)
- **Gemini**: Google Gemini API (fallback)
- **OpenAI**: OpenAI API (fallback)

**Features:**
- Intelligent fallback cascade
- Rate limiting and backoff
- Response caching
- Token usage tracking

**Provider Selection Logic:**
```python
1. Try Ollama (local, fast, no API costs)
2. If Ollama fails or unavailable → Try Gemini
3. If Gemini fails or rate limited → Try OpenAI
4. If all fail → Return error with retry suggestion
```

### 6. Storage & Retrieval Layer

**Vector Store (`src/services/vectorstore.py`):**
- ChromaDB for semantic search
- Sentence transformers for embeddings
- Content similarity and retrieval

**Checkpoint Storage (`src/orchestration/checkpoint_manager.py`):**
- Workflow state persistence
- Checkpoint storage and restoration
- Job history and recovery

**Datastore (`src/services/datastore.py`):**
- Content metadata
- Agent execution logs
- Performance metrics

## Data Flow

### Blog Generation Workflow

```
1. Input Ingestion
   └→ KBIngestionAgent reads source content
   
2. Content Planning
   └→ OutlineCreationAgent generates structure
   
3. Content Generation (Parallel)
   ├→ IntroductionWriterAgent
   ├→ SectionWriterAgent (for each section)
   └→ ConclusionWriterAgent
   
4. Code Generation (if needed)
   ├→ CodeGenerationAgent
   └→ CodeValidationAgent
   
5. SEO Optimization
   ├→ KeywordExtractionAgent
   ├→ KeywordInjectionAgent
   └→ SEOMetadataAgent
   
6. Publishing Preparation
   ├→ FrontmatterAgent
   ├→ GistUploadAgent (if code exists)
   └→ SlugService
   
7. Validation & Quality Gate
   └→ ValidationAgent → CompletenessGate
   
8. Output Assembly
   └→ OutputAggregator → Final blog post
```

## Communication Patterns

### 1. Synchronous Agent Invocation
Direct function calls for simple operations.

### 2. Event-Driven Orchestration
LangGraph nodes emit events consumed by downstream agents.

### 3. WebSocket Streaming
Real-time updates from server to web UI clients.

### 4. MCP Protocol
Standardized interface for external agent invocation.

## State Management

### Workflow State
- Current step/agent
- Input data and context
- Output accumulator
- Error state

### Job State
- Job ID and metadata
- Status (pending, running, completed, failed)
- Progress percentage
- Start/end timestamps

### Checkpoint State
- Complete workflow state snapshot
- Resumable from any point
- Automatic save on step completion

## Error Handling

### Strategy
1. **Agent-Level**: Retry with exponential backoff
2. **Workflow-Level**: Checkpoint and pause for manual intervention
3. **System-Level**: Fail gracefully with detailed error context

### Recovery
- Automatic retry for transient failures
- Checkpoint restoration for fatal errors
- Manual intervention UI for stuck workflows

## Scalability Considerations

### Horizontal Scaling
- Stateless agent execution
- Distributed checkpoint storage
- Load-balanced web UI

### Vertical Scaling
- GPU utilization for local models
- Parallel agent execution
- Efficient memory management

### Performance Optimization
- Agent output caching
- Template precompilation
- Lazy loading of heavy resources
- Connection pooling for LLM providers

## Security

### API Key Management
- Environment variable storage
- No hardcoded credentials
- Rotation support

### Input Validation
- Schema validation for all inputs
- Sanitization of user-provided content
- Rate limiting on web endpoints

### Output Safety
- Content filtering
- Code validation before execution
- Malware scanning for uploaded files

## Monitoring & Observability

### Metrics Collected
- Agent execution time
- LLM token usage
- Success/failure rates
- System resource utilization

### Logging
- Structured logging with `structlog`
- Per-agent log isolation
- Centralized log aggregation

### Visualization
- Real-time workflow graphs
- Performance dashboards
- Error tracking and alerting
