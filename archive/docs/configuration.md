# Configuration Guide

UCOP uses a multi-layered configuration system combining environment variables, YAML files, and JSON templates. This guide covers all configuration options and best practices.

## Table of Contents

- [Configuration Files](#configuration-files)
- [Environment Variables](#environment-variables)
- [LLM Configuration](#llm-configuration)
- [Workflow Configuration](#workflow-configuration)
- [Agent Configuration](#agent-configuration)
- [Performance Tuning](#performance-tuning)
- [Security](#security)

## Configuration Files

### File Locations

```
config/
├── main.yaml           # Pipeline and workflow settings
├── agents.yaml         # Agent definitions (38 agents, ~1600 lines)
├── tone.json           # Content tone and style guidelines
├── perf.json           # Performance benchmarks and targets
├── validation.yaml     # Content validation rules
├── checkpoints.yaml    # Checkpoint configuration
└── schemas.py          # Configuration schemas
```

### Loading Order

1. **Default values** (hardcoded in code)
2. **YAML configurations** (`config/*.yaml`)
3. **Environment variables** (`.env` file)
4. **Runtime overrides** (CLI flags, API params)

Later sources override earlier ones.

## Environment Variables

### Core Settings

```bash
# .env

#=== System Configuration ===
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR, CRITICAL
OUTPUT_DIR=./output         # Default output directory
DATA_DIR=./data             # Data storage directory
TEMP_DIR=./temp             # Temporary files directory
CACHE_DIR=./cache           # Cache directory
```

### LLM Providers

```bash
#=== Ollama (Local) ===
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b
OLLAMA_TIMEOUT=120          # Seconds
OLLAMA_NUM_CTX=4096         # Context window size

#=== Google Gemini ===
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-pro
GEMINI_RPM_LIMIT=60         # Requests per minute
GEMINI_TEMPERATURE=0.7

#=== OpenAI ===
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o
OPENAI_ORG=your_org_id      # Optional
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4000
```

### Feature Flags

```bash
#=== Feature Toggles ===
ENABLE_MESH_ORCHESTRATION=true      # LangGraph workflows
ENABLE_VISUAL_ORCHESTRATION=true    # Web UI workflow editor
ENABLE_MCP_ENDPOINTS=true           # MCP protocol endpoints
ENABLE_HOT_RELOAD=true              # Live config reload
ENABLE_PARALLEL_EXECUTION=true      # Concurrent agents
ENABLE_CHECKPOINTS=true             # Workflow checkpointing
ENABLE_MONITORING=true              # Metrics and telemetry
```

### Optional Services

```bash
#=== GitHub (for Gist uploads) ===
GITHUB_TOKEN=your_token_here

#=== ChromaDB (Vector Store) ===
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_PERSIST_DIR=./chroma_db

#=== Redis (Optional Caching) ===
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

#=== PostgreSQL (Optional Metadata Storage) ===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ucop
POSTGRES_USER=ucop
POSTGRES_PASSWORD=
```

### Performance Tuning

```bash
#=== Resource Limits ===
MAX_PARALLEL_AGENTS=5       # Concurrent agent execution
MAX_WORKERS=4               # Thread pool size
MAX_MEMORY_PER_AGENT=2048   # MB
AGENT_TIMEOUT=300           # Seconds
WORKFLOW_TIMEOUT=3600       # Seconds

#=== Caching ===
CACHE_TTL=3600              # Cache TTL in seconds
CACHE_MAX_SIZE=1000         # Max cached items
ENABLE_TEMPLATE_CACHE=true
ENABLE_EMBEDDING_CACHE=true
ENABLE_RESPONSE_CACHE=true

#=== Rate Limiting ===
GEMINI_RPM_LIMIT=60
OPENAI_RPM_LIMIT=100
RATE_LIMIT_WINDOW=60        # Seconds
```

## LLM Configuration

### Provider Selection

Configure LLM providers in `config/main.yaml`:

```yaml
llm:
  # Provider priority (tries in order)
  providers:
    - ollama    # Try local first
    - gemini    # Fallback to Gemini
    - openai    # Final fallback to OpenAI
  
  # Model selection per provider
  models:
    ollama: "qwen2.5:14b"
    gemini: "gemini-1.5-pro"
    openai: "gpt-4o"
  
  # Fallback behavior
  fallback_enabled: true
  max_retries: 3
  retry_delay: 2              # Seconds
  timeout: 120                # Seconds
  
  # Default parameters
  temperature: 0.7
  top_p: 0.9
  top_k: 40
  max_tokens: 4000
```

### Model Selection per Agent

Some agents can use different models for optimization:

```yaml
# config/agents.yaml
agents:
  code_generation_agent:
    model: "phi4:14b"         # Good at code
    provider: "ollama"
  
  seo_metadata_agent:
    model: "qwen2.5:14b"      # Good at marketing
    provider: "ollama"
  
  outline_creation_agent:
    model: "gemini-1.5-pro"   # Good at structure
    provider: "gemini"
```

### Rate Limiting

```yaml
llm:
  rate_limiting:
    enabled: true
    
    # Per-provider limits
    gemini:
      requests_per_minute: 60
      tokens_per_minute: 100000
      concurrent_requests: 10
    
    openai:
      requests_per_minute: 100
      tokens_per_minute: 200000
      concurrent_requests: 20
    
    # Backoff strategy
    backoff_factor: 2.0
    max_backoff: 60           # Seconds
```

### Caching Strategy

```yaml
llm:
  caching:
    enabled: true
    ttl: 3600                 # 1 hour
    max_size: 1000            # Max cached responses
    
    # Cache key includes:
    # - Prompt hash
    # - Model name
    # - Temperature
    # - Top_p
    
    # Never cache for:
    exclude_agents:
      - "code_generation_agent"  # Always fresh code
      - "trends_research_agent"  # Always fresh trends
```

## Workflow Configuration

### Pipeline Definition

```yaml
# config/main.yaml

# Global pipeline order (all agents)
pipeline:
  - topic_identification
  - kb_ingestion
  - api_ingestion
  - blog_ingestion
  - duplication_check
  - outline_creation
  - introduction_writer
  - section_writer
  - code_generation
  - code_validation
  - conclusion_writer
  - keyword_extraction
  - keyword_injection
  - seo_metadata
  - frontmatter
  - content_assembly
  - link_validation
  - file_writer
```

### Workflow Profiles

```yaml
# config/main.yaml
workflows:
  # LangGraph execution mode
  use_langgraph: true
  
  # Parallel execution
  enable_parallel_execution: true
  max_parallel_agents: 5
  
  # Profile definitions
  default:
    name: "Full Blog Post Generation"
    steps:
      - topic_identification
      - kb_ingestion
      - api_ingestion
      - blog_ingestion
      - duplication_check
      - outline_creation
      - introduction_writer
      - section_writer
      - code_generation
      - code_validation
      - conclusion_writer
      - keyword_extraction
      - keyword_injection
      - seo_metadata
      - frontmatter
      - content_assembly
      - link_validation
      - file_writer
  
  code_only:
    name: "Code Generation Only"
    steps:
      - topic_identification
      - api_ingestion
      - code_generation
      - code_validation
      - code_splitting
      - license_injection
      - file_writer
  
  quick_draft:
    name: "Quick Draft (No SEO)"
    steps:
      - topic_identification
      - kb_ingestion
      - outline_creation
      - section_writer
      - conclusion_writer
      - content_assembly
      - file_writer
  
  seo_only:
    name: "SEO Optimization Only"
    steps:
      - topic_identification
      - kb_ingestion
      - keyword_extraction
      - keyword_injection
      - seo_metadata
      - frontmatter
      - file_writer
```

### Workflow Dependencies

```yaml
# config/main.yaml
dependencies:
  outline_creation:
    requires:
      - topic_identification
      - kb_ingestion
  
  section_writer:
    requires:
      - outline_creation
  
  code_generation:
    requires:
      - api_ingestion
  
  content_assembly:
    requires:
      - section_writer
      - conclusion_writer
    optional:
      - code_generation  # Only if code was generated
  
  file_writer:
    requires:
      - content_assembly
```

### Checkpoint Configuration

```yaml
# config/checkpoints.yaml
checkpoints:
  enabled: true
  storage_dir: "./checkpoints"
  
  # Auto-checkpoint after each agent
  auto_checkpoint: true
  
  # Checkpoint retention
  max_checkpoints_per_job: 10
  retention_days: 30
  
  # Compression
  compress: true
  compression_level: 6
```

## Agent Configuration

### Agent Definition Structure

```yaml
# config/agents.yaml
agents:
  outline_creation_agent:
    # Identity
    id: "outline_creation_agent"
    version: "1.0.0"
    description: "Creates structured content outlines from source material"
    
    # Entrypoint
    entrypoint:
      type: "python"
      module: "agents.content"
      function: "outline_creation_node"
      async: false
    
    # Contract (inputs/outputs)
    contract:
      inputs:
        type: "object"
        properties:
          kb_content:
            type: "string"
          current_topic:
            type: "object"
        required:
          - "kb_content"
          - "current_topic"
      
      outputs:
        type: "object"
        properties:
          outline:
            type: "object"
          sections:
            type: "array"
        required:
          - "outline"
          - "sections"
    
    # Capabilities
    capabilities:
      async: false
      model_switchable: true
      side_effects: "none"
      stateful: true
    
    # Resource limits
    resources:
      max_runtime_s: 300
      max_memory_mb: 1024
      max_tokens: 4096
```

### Agent Categories

Agents are organized into categories for easier management:

```yaml
categories:
  content:
    - outline_creation_agent
    - introduction_writer_agent
    - section_writer_agent
    - conclusion_writer_agent
    - supplementary_content_agent
  
  seo:
    - keyword_extraction_agent
    - keyword_injection_agent
    - seo_metadata_agent
  
  code:
    - code_generation_agent
    - code_validation_agent
    - api_compliance_agent
    - gist_upload_agent
  
  publishing:
    - frontmatter_agent
    - slug_generation_agent
    - content_assembly_agent
    - file_writer_agent
  
  research:
    - trends_research_agent
    - content_intelligence_agent
    - topic_identification_agent
    - duplication_check_agent
  
  support:
    - validation_agent
    - quality_gate_agent
    - link_validation_agent
    - health_monitor_agent
  
  ingestion:
    - kb_ingestion_agent
    - docs_ingestion_agent
    - api_ingestion_agent
    - blog_ingestion_agent
```

## Performance Tuning

### Parallel Execution

```yaml
# config/main.yaml
workflows:
  enable_parallel_execution: true
  max_parallel_agents: 5
  
  # Agents that can run in parallel
  parallelizable_groups:
    content_generation:
      - introduction_writer_agent
      - section_writer_agent
      - conclusion_writer_agent
    
    seo_optimization:
      - keyword_extraction_agent
      - keyword_injection_agent
      - seo_metadata_agent
```

### Resource Allocation

```yaml
# config/perf.json
{
  "resource_allocation": {
    "agent_pools": {
      "high_priority": {
        "max_workers": 3,
        "agents": [
          "outline_creation_agent",
          "code_generation_agent"
        ]
      },
      "low_priority": {
        "max_workers": 2,
        "agents": [
          "supplementary_content_agent",
          "link_validation_agent"
        ]
      }
    }
  },
  
  "memory_limits": {
    "per_agent": "2GB",
    "total_system": "8GB"
  },
  
  "timeouts": {
    "agent_default": 300,
    "code_generation": 600,
    "api_calls": 30
  }
}
```

### Caching Strategy

```yaml
# Enable multiple cache layers
caching:
  levels:
    # L1: In-memory cache
    - type: "memory"
      ttl: 300
      max_size: 100
    
    # L2: Redis cache (if available)
    - type: "redis"
      ttl: 3600
      max_size: 1000
    
    # L3: Disk cache
    - type: "disk"
      ttl: 86400
      max_size: 10000
  
  # What to cache
  cache_targets:
    - "templates"
    - "embeddings"
    - "llm_responses"
    - "api_docs"
```

## Security

### API Key Management

```bash
# Best practice: Use environment variables
export GEMINI_API_KEY="..."
export OPENAI_API_KEY="..."

# Never commit .env files
# Add to .gitignore
echo ".env" >> .gitignore
echo ".env.*" >> .gitignore
```

### Input Validation

```yaml
# config/validation.yaml
validation:
  input:
    max_file_size_mb: 10
    allowed_extensions:
      - ".md"
      - ".txt"
      - ".html"
    
    content:
      max_length: 100000  # characters
      min_length: 100
      
      # Block suspicious patterns
      blocked_patterns:
        - "(?i)<script"   # XSS
        - "(?i)eval\("    # Code injection
        - "(?i)exec\("
  
  output:
    sanitize_html: true
    escape_markdown: false
    validate_links: true
```

### Rate Limiting

```yaml
# Protect against abuse
rate_limiting:
  enabled: true
  
  # Per-IP limits (web UI)
  per_ip:
    requests_per_minute: 10
    burst: 20
  
  # Per-user limits (API)
  per_user:
    jobs_per_hour: 100
    jobs_per_day: 1000
```

## Configuration Examples

### Development Setup

```yaml
# config/main.yaml (dev)
workflows:
  use_langgraph: true
  enable_parallel_execution: false  # Easier debugging
  max_parallel_agents: 1

llm:
  providers:
    - ollama  # Local only for dev
  models:
    ollama: "phi4:14b"  # Smaller, faster model

logging:
  level: DEBUG
  format: detailed
  output: console

checkpoints:
  enabled: true
  auto_checkpoint: true
```

### Production Setup

```yaml
# config/main.yaml (prod)
workflows:
  use_langgraph: true
  enable_parallel_execution: true
  max_parallel_agents: 10

llm:
  providers:
    - gemini   # Fast, reliable
    - openai   # Fallback
  models:
    gemini: "gemini-1.5-pro"
    openai: "gpt-4o"

logging:
  level: INFO
  format: json
  output: file
  path: /var/log/ucop/

checkpoints:
  enabled: true
  auto_checkpoint: true
  storage_dir: /data/checkpoints
  retention_days: 90
```

### Testing Setup

```yaml
# config/main.yaml (test)
workflows:
  use_langgraph: false  # Simpler for unit tests
  enable_parallel_execution: false

llm:
  providers:
    - mock  # Mock LLM for tests

logging:
  level: WARNING

deterministic: true
global_seed: 42
```

## Validation

### Validate Configuration

```bash
# Check syntax and schema
python tools/validate.py

# Test LLM connectivity
python tools/validate_system.py

# Verify all agents load
python tools/validate_production.py
```

### Configuration Schema

Configuration files are validated against JSON schemas defined in `config/schemas.py`. Invalid configurations will raise errors at startup.

## Hot Reload

UCOP supports hot-reloading configuration without restart:

```bash
# Enable hot reload
export ENABLE_HOT_RELOAD=true

# Modify configuration
vim config/main.yaml

# Changes auto-detected and applied
# Check logs: "Configuration reloaded"
```

**Note**: Hot reload works for most settings but not all (e.g., cannot change LLM provider mid-job).

## Troubleshooting

### Configuration Not Loading

```bash
# Check file syntax
python -m yaml config/main.yaml

# Validate schema
python tools/validate.py config/main.yaml

# Check file permissions
ls -l config/
```

### LLM Connection Issues

```bash
# Test Ollama
curl http://localhost:11434/api/tags

# Test Gemini
python -c "from google import generativeai; generativeai.configure(api_key='YOUR_KEY'); print(generativeai.list_models())"

# Check logs
tail -f logs/ucop.log
```

### Performance Issues

```bash
# Check resource usage
python tools/perf_report.py

# Profile workflow
python profile_system.py --workflow blog_generation

# View bottlenecks
python ucop_cli.py viz bottlenecks
```

For more help, see [troubleshooting.md](troubleshooting.md).
