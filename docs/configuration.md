# Configuration

## Overview

UCOP uses a multi-file configuration system combining YAML files, JSON files, and environment variables. Configuration controls LLM providers, workflows, agents, validation rules, and system behavior.

## Configuration Files

### config/main.yaml

Primary configuration file controlling workflows, pipelines, and execution.

#### Workflow Configuration

```yaml
workflows:
  # Enable LangGraph-based execution (experimental)
  use_langgraph: false
  
  # Enable mesh orchestration mode (experimental)
  use_mesh: false
  
  # Enable parallel execution for independent agents
  enable_parallel_execution: false
  
  # Maximum number of agents that can run in parallel
  max_parallel_agents: 5
```

**Options**:
- `use_langgraph`: Use LangGraph for workflow orchestration (default: false)
- `use_mesh`: Enable dynamic mesh routing (default: false)
- `enable_parallel_execution`: Execute independent agents concurrently (default: false)
- `max_parallel_agents`: Concurrency limit (default: 5, recommended: 3-5 for standard systems, 5-10 for high-end)

#### Mesh Configuration

```yaml
mesh:
  enabled: false
  max_hops: 10
  routing_timeout_seconds: 5
  discovery_method: "capability"
  circuit_breaker:
    enabled: true
    failure_threshold: 3
    timeout_seconds: 60
```

**Options**:
- `max_hops`: Maximum agent chain depth
- `routing_timeout_seconds`: Timeout for routing decisions
- `discovery_method`: Agent discovery method ("capability" or "registry")
- `circuit_breaker`: Protection against cascading failures

#### Job Configuration

```yaml
jobs:
  max_retries: 3
  retry_delay_seconds: 60
  max_concurrent_jobs: 3
  storage:
    base_dir: ".jobs"
    archive_dir: ".jobs/archive"
  archive:
    auto_archive_enabled: true
    auto_archive_completed_after_days: 7
    auto_archive_failed_after_days: 14
    retention_days: 30
    auto_cleanup_enabled: true
```

**Options**:
- `max_retries`: Retry attempts for failed jobs
- `retry_delay_seconds`: Initial retry delay (exponential backoff applied)
- `max_concurrent_jobs`: Maximum simultaneous jobs
- `auto_archive_enabled`: Automatic archival of old jobs
- `retention_days`: How long to keep archived jobs

#### MCP Configuration

```yaml
mcp:
  traffic_retention_days: 7
  traffic_logging_enabled: true
```

**Options**:
- `traffic_retention_days`: Days to retain MCP traffic logs
- `traffic_logging_enabled`: Enable/disable MCP traffic logging

#### Pipeline Configuration

```yaml
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

**Note**: Pipeline order matters. Agents execute sequentially unless parallel execution is enabled.

#### Predefined Workflows

**default**: Full blog post generation with SEO
**code_only**: Code generation without blog content
**quick_draft**: Fast content creation without SEO

```yaml
workflows:
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
```

### config/agents.yaml

Defines all 34 agents with contracts, capabilities, and resource limits.

#### Agent Structure

```yaml
agents:
  create_outline_node:
    id: create_outline_node
    version: 1.0.0
    description: Create structured outline for blog post.
    
    capabilities:
      async: false
      model_switchable: true
      side_effects: none
      stateful: true
    
    contract:
      inputs:
        type: object
        required:
          - current_topic
          - context_kb
        properties:
          current_topic: {type: object}
          context_kb: {type: array}
          context_blog: {type: array}
      
      outputs:
        type: object
        required:
          - outline
        properties:
          outline: {type: object}
      
      checkpoints:
        - name: before_execution
          description: Before create_outline_node starts
        - name: after_execution
          description: After create_outline_node completes
    
    entrypoint:
      type: python
      module: agents
      function: create_outline_node
      async: false
    
    resources:
      max_memory_mb: 2048
      max_runtime_s: 600
      max_tokens: 8192
```

**Key Fields**:
- `capabilities`: Agent behavior flags
- `contract`: Input/output schemas
- `checkpoints`: State capture points
- `resources`: Execution limits

### config/tone.json

Content style and tone configuration.

```json
{
  "tone": {
    "formality": "professional",
    "voice": "active",
    "person": "second",
    "style": "technical",
    "audience": "developers"
  },
  
  "sections": {
    "introduction": {
      "style": "engaging",
      "length": "medium",
      "include_hook": true
    },
    "body": {
      "style": "informative",
      "code_examples": true,
      "explanations": "detailed"
    },
    "conclusion": {
      "include_cta": true,
      "style": "actionable"
    }
  },
  
  "formatting": {
    "code_style": "csharp",
    "heading_style": "atx",
    "list_style": "unordered"
  }
}
```

### config/validation.yaml

Quality gates and validation rules.

```yaml
validation:
  # Content validation
  content:
    min_word_count: 300
    max_word_count: 3000
    require_code_examples: true
    require_conclusion: true
  
  # Code validation
  code:
    require_license_header: true
    validate_syntax: true
    min_lines: 5
    max_lines: 100
  
  # SEO validation
  seo:
    require_meta_description: true
    require_keywords: true
    min_keywords: 3
    max_keywords: 10
  
  # Link validation
  links:
    validate_gist_urls: true
    check_http_status: true
    timeout_seconds: 10
```

### config/schemas.py

Python schema definitions for data structures.

```python
SCHEMAS = {
    "outline": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "heading": {"type": "string"},
                        "description": {"type": "string"}
                    }
                }
            }
        }
    },
    
    "topic": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "keywords": {"type": "array"}
        }
    }
}
```

## Environment Variables

### Required Variables

```bash
# LLM Providers
OLLAMA_BASE_URL=http://localhost:11434  # Ollama server URL
GOOGLE_API_KEY=your_key_here            # Google Gemini API key
OPENAI_API_KEY=your_key_here            # OpenAI API key

# GitHub
GITHUB_TOKEN=your_token_here            # GitHub personal access token

# Paths
CHROMA_DB_PATH=./chroma_db              # ChromaDB storage path
OUTPUT_PATH=./output                    # Generated content output
```

### Optional Variables

```bash
# Advanced LLM Settings
OLLAMA_TIMEOUT=300                      # Request timeout in seconds
LLM_RETRY_ATTEMPTS=3                    # Number of retry attempts
LLM_RATE_LIMIT=10                       # Requests per minute

# Database Settings
CHROMA_COLLECTION_NAME=ucop             # ChromaDB collection name
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Development
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR
DEBUG_MODE=false                        # Enable debug logging
HOT_RELOAD_ENABLED=true                 # Enable hot reload
```

### Setting Environment Variables

#### Linux/Mac

```bash
# In .bashrc or .zshrc
export OLLAMA_BASE_URL=http://localhost:11434
export GOOGLE_API_KEY=your_key_here

# Or in .env file (recommended)
cp .env.example .env
# Edit .env with your values
```

#### Windows

```cmd
# In command prompt
set OLLAMA_BASE_URL=http://localhost:11434
set GOOGLE_API_KEY=your_key_here

# Or in PowerShell
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:GOOGLE_API_KEY="your_key_here"
```

## LLM Provider Configuration

### Ollama (Local)

Primary LLM provider for local inference.

```yaml
# In config or environment
ollama:
  base_url: http://localhost:11434
  models:
    content: "qwen2.5:14b"      # Content generation
    code: "deepseek-coder:33b"  # Code generation
    seo: "qwen2.5:7b"           # SEO tasks
  timeout: 300
  retry_attempts: 3
```

**Recommended Models**:
- **Content**: qwen2.5:14b, llama3.1:8b
- **Code**: deepseek-coder:33b, codellama:13b
- **SEO**: qwen2.5:7b, mistral:7b

### Google Gemini (Cloud)

Fallback provider for Ollama failures.

```yaml
gemini:
  api_key: ${GOOGLE_API_KEY}
  model: "gemini-1.5-pro"
  timeout: 60
  max_tokens: 8192
  rate_limit: 15  # requests per minute
```

### OpenAI (Cloud)

Secondary fallback provider.

```yaml
openai:
  api_key: ${OPENAI_API_KEY}
  model: "gpt-4o"
  timeout: 60
  max_tokens: 8192
  rate_limit: 10  # requests per minute
```

### Fallback Chain

LLM providers are tried in order until success:

1. **Ollama** (local, fast, free)
2. **Gemini** (cloud, reliable, paid)
3. **OpenAI** (cloud, high-quality, paid)

```python
# Automatic fallback in LLMService
try:
    response = ollama.generate(prompt)
except OllamaError:
    try:
        response = gemini.generate(prompt)
    except GeminiError:
        response = openai.generate(prompt)
```

## Vector Store Configuration

### ChromaDB Settings

```yaml
vectorstore:
  provider: "chromadb"
  persist_directory: "./chroma_db"
  collection_name: "ucop"
  
  # Embedding configuration
  embedding:
    model: "sentence-transformers/all-MiniLM-L6-v2"
    dimension: 384
    distance_metric: "cosine"
  
  # Search configuration
  search:
    top_k: 5
    min_similarity: 0.7
    include_metadata: true
```

**Options**:
- `persist_directory`: Database storage location
- `collection_name`: ChromaDB collection identifier
- `top_k`: Number of results for similarity search
- `min_similarity`: Minimum similarity threshold (0.0-1.0)

## Configuration Management

### Viewing Current Configuration

```bash
# View all configuration
python ucop_cli.py config snapshot

# View specific sections
python ucop_cli.py config agents
python ucop_cli.py config workflows
python ucop_cli.py config tone
python ucop_cli.py config performance
```

### Validating Configuration

```bash
# Validate all configuration files
python tools/validate.py

# Check for configuration errors
python ucop_cli.py config validate
```

### Hot Reload

Configuration can be updated without restarting:

```bash
# Edit configuration files
vim config/main.yaml

# Configuration automatically reloaded
# Or manually trigger reload:
python ucop_cli.py config reload
```

## Advanced Configuration

### Custom Workflows

Define custom workflows in `config/main.yaml`:

```yaml
workflows:
  custom_workflow:
    name: "Custom Content Pipeline"
    steps:
      - topic_identification
      - kb_ingestion
      - custom_agent_node
      - outline_creation
      - section_writer
      - file_writer
```

### Agent Resource Tuning

Adjust agent resources in `config/agents.yaml`:

```yaml
agents:
  code_generation_node:
    resources:
      max_memory_mb: 8192  # Increase for large codebases
      max_runtime_s: 1800  # Allow longer execution
      max_tokens: 32768    # Increase token limit
```

### Parallel Execution Tuning

```yaml
workflows:
  enable_parallel_execution: true
  max_parallel_agents: 10  # Higher for powerful systems
  
# Define parallelizable agent groups
parallel_groups:
  - [kb_search_node, api_search_node, blog_search_node]
  - [code_generation_node, supplementary_content_node]
```

## Configuration Best Practices

1. **Use .env files**: Store secrets in `.env`, never commit to version control
2. **Validate before deploying**: Run `tools/validate.py` before production
3. **Start conservative**: Use default settings, tune based on performance
4. **Monitor resources**: Watch memory/CPU usage, adjust limits accordingly
5. **Version control**: Track configuration changes, use git tags
6. **Document customizations**: Comment custom settings in YAML files
7. **Test changes**: Validate with small jobs before production runs
8. **Backup configs**: Keep copies of working configurations

## Troubleshooting

### Configuration Not Loading

```bash
# Check configuration syntax
python tools/validate.py

# Check file permissions
ls -la config/

# Check environment variables
env | grep -E "OLLAMA|GOOGLE|OPENAI|GITHUB"
```

### Agent Resource Errors

```bash
# View agent failures
python ucop_cli.py agents failures

# Check resource limits
python ucop_cli.py config agents | grep -A5 resources

# Increase limits in config/agents.yaml
```

### LLM Connection Issues

```bash
# Test Ollama connection
curl http://localhost:11434/api/tags

# Test API keys
python -c "import os; print(os.getenv('GOOGLE_API_KEY'))"

# Check fallback chain
python ucop_cli.py config performance | grep fallback
```

---

*This documentation is part of the UCOP project. For more information, see the [main README](../README.md).*
