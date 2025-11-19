# Agents

## Overview

UCOP includes 34 specialized agents organized into functional categories. Each agent is MCP-compliant with defined contracts, capabilities, and resource limits. Agents communicate through an event-driven architecture and support checkpoint persistence, hot-reload, and dependency resolution.

## Agent Architecture

Agents in UCOP follow a standardized structure:

- **Base Class**: All agents inherit from `Agent` and optionally `SelfCorrectingAgent`
- **Contract Definition**: Each agent defines input/output schemas and capabilities
- **Event-Driven**: Agents subscribe to events and publish results
- **Resource Limited**: Memory, runtime, and token limits enforced
- **Stateful**: Support checkpoint persistence for resume/retry

## Agent Categories

### Ingestion Agents (5 agents)

Ingestion agents process various content sources and create embeddings for semantic search.

#### ingest_kb_node
**Description**: Ingest KB article and create embeddings.  
**Inputs**: `kb_file_path`, `config`  
**Outputs**: `current_topic`, `ingestion_metadata`  
**Side Effects**: Database writes  
**Resources**: 2048 MB memory, 300s timeout

#### ingest_docs_node
**Description**: Ingest documentation content and create embeddings.  
**Inputs**: `docs_file_path`, `config`  
**Outputs**: `docs_metadata`  
**Side Effects**: Database writes  
**Resources**: 2048 MB memory, 300s timeout

#### ingest_api_node
**Description**: Ingest API documentation for code generation context.  
**Inputs**: `api_file_path`, `config`  
**Outputs**: `api_metadata`  
**Side Effects**: Database writes  
**Resources**: 2048 MB memory, 300s timeout

#### ingest_blog_node
**Description**: Ingest existing blog posts for context and duplication checking.  
**Inputs**: `blog_file_path`, `config`  
**Outputs**: `blog_metadata`  
**Side Effects**: Database writes  
**Resources**: 2048 MB memory, 300s timeout

#### ingest_tutorial_node
**Description**: Ingest tutorial content and create embeddings.  
**Inputs**: `tutorial_file_path`, `config`  
**Outputs**: `tutorial_metadata`  
**Side Effects**: Database writes  
**Resources**: 2048 MB memory, 300s timeout

### Content Generation Agents (7 agents)

Content agents handle the creation of blog post components.

#### create_outline_node
**Description**: Create structured outline for blog post.  
**Inputs**: `current_topic`, `context_kb`, `context_blog`  
**Outputs**: `outline`  
**LLM**: Required  
**Resources**: 2048 MB memory, 600s timeout, 8192 max tokens

#### introduction_writer_node
**Description**: Write engaging blog post introduction.  
**Inputs**: `current_topic`, `outline`, `context_kb`  
**Outputs**: `introduction`  
**LLM**: Required  
**Resources**: 2048 MB memory, 600s timeout, 8192 max tokens

#### section_writer_node
**Description**: Write detailed blog post sections.  
**Inputs**: `current_topic`, `outline`, `context_kb`, `context_api`  
**Outputs**: `sections`  
**LLM**: Required  
**Resources**: 2048 MB memory, 600s timeout, 8192 max tokens

#### conclusion_writer_node
**Description**: Write blog post conclusion.  
**Inputs**: `current_topic`, `outline`, `sections`  
**Outputs**: `conclusion`  
**LLM**: Required  
**Resources**: 2048 MB memory, 600s timeout, 8192 max tokens

#### supplementary_content_node
**Description**: Generate supplementary sections (FAQ, troubleshooting, etc.).  
**Inputs**: `current_topic`, `outline`, `sections`  
**Outputs**: `supplementary_sections`  
**LLM**: Required  
**Resources**: 2048 MB memory, 600s timeout, 8192 max tokens

#### content_assembly_node
**Description**: Assemble final blog post content from parts.  
**Inputs**: `introduction`, `sections`, `conclusion`, `supplementary_sections`, `code_blocks`  
**Outputs**: `assembled_content`  
**Resources**: 1024 MB memory, 120s timeout

#### content_reviewer_node
**Description**: Review content quality and relevance (non-blocking).  
**Inputs**: `assembled_content`  
**Outputs**: `review_feedback`  
**LLM**: Required  
**Resources**: 1024 MB memory, 300s timeout, 4096 max tokens

### SEO Optimization Agents (3 agents)

SEO agents enhance content discoverability.

#### keyword_extraction_node
**Description**: Extract keywords from content.  
**Inputs**: `current_topic`, `assembled_content`  
**Outputs**: `keywords`  
**LLM**: Required  
**Resources**: 1024 MB memory, 300s timeout, 4096 max tokens

#### keyword_injection_node
**Description**: Inject keywords naturally into content.  
**Inputs**: `assembled_content`, `keywords`  
**Outputs**: `seo_enhanced_content`  
**LLM**: Required  
**Resources**: 1024 MB memory, 300s timeout, 4096 max tokens

#### seo_metadata_node
**Description**: Generate SEO metadata.  
**Inputs**: `current_topic`, `seo_enhanced_content`, `keywords`  
**Outputs**: `seo_metadata`  
**LLM**: Required  
**Resources**: 1024 MB memory, 300s timeout, 4096 max tokens

### Code Generation Agents (7 agents)

Code agents handle creation, validation, and publishing of code examples.

#### code_generation_node
**Description**: Generate complete C# code examples.  
**Inputs**: `current_topic`, `context_api`, `sections`  
**Outputs**: `code_examples`  
**LLM**: Required  
**Resources**: 4096 MB memory, 900s timeout, 16384 max tokens

#### code_extraction_node
**Description**: Extract code blocks from content.  
**Inputs**: `sections`  
**Outputs**: `extracted_code_blocks`  
**Resources**: 1024 MB memory, 120s timeout

#### code_validation_node
**Description**: Validate C# code quality.  
**Inputs**: `code_examples`, `context_api`  
**Outputs**: `validated_code`  
**Resources**: 2048 MB memory, 300s timeout

#### license_injection_node
**Description**: Inject license header into code.  
**Inputs**: `validated_code`  
**Outputs**: `licensed_code`  
**Resources**: 512 MB memory, 60s timeout

#### code_splitting_node
**Description**: Split code into segments for explanation.  
**Inputs**: `licensed_code`  
**Outputs**: `code_segments`  
**Resources**: 1024 MB memory, 120s timeout

#### gist_readme_node
**Description**: Create README for Gist.  
**Inputs**: `current_topic`, `code_segments`  
**Outputs**: `gist_readme`  
**LLM**: Required  
**Resources**: 1024 MB memory, 300s timeout, 4096 max tokens

#### gist_upload_node
**Description**: Upload code to GitHub Gist.  
**Inputs**: `licensed_code`, `gist_readme`  
**Outputs**: `gist_url`  
**Side Effects**: Network (GitHub API)  
**Resources**: 512 MB memory, 300s timeout

### Publishing Agents (3 agents)

Publishing agents finalize and write content.

#### frontmatter_node
**Description**: Add frontmatter to blog post.  
**Inputs**: `current_topic`, `seo_metadata`, `gist_url`  
**Outputs**: `frontmatter`  
**Resources**: 512 MB memory, 60s timeout

#### link_validation_node
**Description**: Validate gist URLs.  
**Inputs**: `gist_url`  
**Outputs**: `validated_gist_url`  
**Side Effects**: Network (HTTP HEAD requests)  
**Resources**: 512 MB memory, 120s timeout

#### write_file_node
**Description**: Write final blog post to file.  
**Inputs**: `frontmatter`, `seo_enhanced_content`, `output_path`  
**Outputs**: `written_file_path`  
**Side Effects**: Filesystem writes  
**Resources**: 512 MB memory, 60s timeout

### Research & Intelligence Agents (8 agents)

Research agents perform semantic search and analysis.

#### identify_topics_node
**Description**: Identify blog post topics from KB article.  
**Inputs**: `current_topic`, `config`  
**Outputs**: `identified_topics`  
**LLM**: Required  
**Resources**: 2048 MB memory, 600s timeout, 8192 max tokens

#### topic_prep_node
**Description**: Prepare current topic for processing.  
**Inputs**: `current_topic`, `identified_topics`  
**Outputs**: `prepared_topic`  
**Resources**: 512 MB memory, 60s timeout

#### kb_search_node
**Description**: Search KB for relevant context.  
**Inputs**: `current_topic`, `config`  
**Outputs**: `context_kb`  
**Side Effects**: Database reads  
**Resources**: 1024 MB memory, 300s timeout

#### api_search_node
**Description**: Search API docs for code generation context.  
**Inputs**: `current_topic`, `config`  
**Outputs**: `context_api`  
**Side Effects**: Database reads  
**Resources**: 1024 MB memory, 300s timeout

#### blog_search_node
**Description**: Search blog posts for relevant context.  
**Inputs**: `current_topic`, `config`  
**Outputs**: `context_blog`  
**Side Effects**: Database reads  
**Resources**: 1024 MB memory, 300s timeout

#### docs_search_node
**Description**: Search documentation for relevant context.  
**Inputs**: `current_topic`, `config`  
**Outputs**: `context_docs`  
**Side Effects**: Database reads  
**Resources**: 1024 MB memory, 300s timeout

#### tutorial_search_node
**Description**: Search tutorial content for relevant context.  
**Inputs**: `current_topic`, `config`  
**Outputs**: `context_tutorial`  
**Side Effects**: Database reads  
**Resources**: 1024 MB memory, 300s timeout

#### check_duplication_node
**Description**: Check if current topic is duplicate of existing content.  
**Inputs**: `current_topic`, `config`  
**Outputs**: `is_duplicate`, `duplicate_score`  
**Side Effects**: Database reads  
**Resources**: 1024 MB memory, 300s timeout

### Support Agents (1 agent)

Support agents provide system-level functionality.

#### model_selection_node
**Description**: Select best Ollama model for capability.  
**Inputs**: `capability`, `config`  
**Outputs**: `selected_model`  
**Resources**: 256 MB memory, 30s timeout

## Agent Capabilities

Agents declare capabilities that determine their behavior:

- **async**: Whether the agent supports async execution
- **model_switchable**: Can use different LLM models
- **side_effects**: `none`, `filesystem`, `network`, `database`
- **stateful**: Maintains state across invocations

## Contract System

Each agent defines a contract with:

1. **Input Schema**: Required and optional input parameters
2. **Output Schema**: Guaranteed output structure
3. **Checkpoints**: State capture points for resume/retry
4. **Resource Limits**: Memory, runtime, and token constraints

## Using Agents

### CLI Usage

```bash
# List all agents
python ucop_cli.py agents list

# Invoke a specific agent
python ucop_cli.py agents invoke \
    --agent create_outline_node \
    --input '{"topic": "Example Topic"}' \
    --output output.json

# View agent health status
python ucop_cli.py agents health
```

### Programmatic Usage

```python
from src.agents import OutlineCreationAgent
from src.core import Config, EventBus
from src.services import LLMService

config = Config()
event_bus = EventBus()
llm_service = LLMService(config)

agent = OutlineCreationAgent(config, event_bus, llm_service)
result = agent.execute(event_data)
```

## Agent Development

### Creating Custom Agents

1. Extend `Agent` base class
2. Define contract with input/output schemas
3. Implement `execute()` method
4. Subscribe to events
5. Register in `config/agents.yaml`

Example:

```python
from src.agents.base import Agent, AgentContract, AgentEvent

class CustomAgent(Agent):
    def __init__(self, config, event_bus):
        super().__init__("CustomAgent", config, event_bus)
    
    def _create_contract(self) -> AgentContract:
        return AgentContract(
            agent_id="CustomAgent",
            capabilities=["custom_capability"],
            input_schema={"type": "object"},
            output_schema={"type": "object"}
        )
    
    def execute(self, event: AgentEvent):
        # Implementation
        return AgentEvent(
            event_type="custom_completed",
            data={"result": "value"},
            source_agent=self.agent_id
        )
```

## Agent Registry

The `AgentRegistry` tracks all available agents:

- **Discovery**: Auto-discovers agents at startup
- **Health Monitoring**: Tracks agent failures and performance
- **Dynamic Loading**: Hot-reload support for agent updates
- **Capability Indexing**: Searchable by capabilities

## Troubleshooting

### Agent Failures

Check agent health status:

```bash
python ucop_cli.py agents health
python ucop_cli.py agents failures --agent <agent_id>
python ucop_cli.py agents logs --agent <agent_id>
```

### Memory Issues

Agents exceeding memory limits will be terminated. Adjust limits in `config/agents.yaml`:

```yaml
agents:
  custom_agent:
    resources:
      max_memory_mb: 4096  # Increase limit
```

### Timeout Issues

Increase timeout for long-running agents:

```yaml
agents:
  custom_agent:
    resources:
      max_runtime_s: 900  # 15 minutes
```

---

*This documentation is part of the UCOP project. For more information, see the [main README](../README.md).*
