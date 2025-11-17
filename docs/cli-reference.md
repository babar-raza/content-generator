# CLI Reference

Complete command-line interface reference for UCOP.

## Overview

The UCOP CLI (`ucop_cli.py`) provides 23 commands organized into 7 categories:

- **Generation**: Content generation commands
- **Jobs**: Job management and monitoring  
- **Agents**: Agent invocation and listing
- **Workflows**: Workflow visualization
- **Checkpoints**: Checkpoint management
- **Configuration**: Config inspection
- **Ingestion**: Content ingestion

## Global Options

```bash
python ucop_cli.py [GLOBAL_OPTIONS] COMMAND [OPTIONS]

Global Options:
  --config FILE     Path to config file (default: config/main.yaml)
  --log-level LEVEL Set log level (DEBUG, INFO, WARNING, ERROR)
  --format FORMAT   Output format (text, json) (default: text)
  --help            Show help message
  --version         Show version
```

## Generation Commands

### `generate`

Generate content from a single source file.

```bash
python ucop_cli.py generate [OPTIONS]

Options:
  --input FILE          Input file path (required)
  --output DIR          Output directory (default: ./output)
  --workflow NAME       Workflow profile (default: blog_generation)
  --keywords WORDS      Target keywords (comma-separated)
  --tone TONE          Content tone (professional, casual, technical)
  --format FORMAT      Output format (markdown, html)
  --checkpoint         Enable checkpointing
  --parallel           Enable parallel execution
  
Examples:
  # Basic generation
  python ucop_cli.py generate --input kb/article.md --output output/

  # With specific workflow
  python ucop_cli.py generate --input kb/article.md --workflow quick_draft

  # With keywords and tone
  python ucop_cli.py generate \
    --input kb/article.md \
    --keywords "python,tutorial,beginner" \
    --tone technical
```

### `batch`

Process multiple files in batch.

```bash
python ucop_cli.py batch [OPTIONS]

Options:
  --manifest FILE      Batch manifest JSON file (required)
  --parallel          Enable parallel processing
  --max-workers N     Max concurrent workers (default: 3)
  --checkpoint        Enable checkpointing
  --resume            Resume from checkpoint
  
Manifest Format:
{
  "batch_name": "Q1_2025_Content",
  "workflow": "blog_generation",
  "inputs": [
    {"source": "input/article1.md", "keywords": ["python"]},
    {"source": "input/article2.md", "keywords": ["java"]}
  ],
  "output_dir": "output/q1_2025",
  "options": {
    "parallel": true,
    "max_workers": 3
  }
}

Examples:
  # Process batch
  python ucop_cli.py batch --manifest batch.json

  # With parallel processing
  python ucop_cli.py batch --manifest batch.json --parallel --max-workers 5
```

### `validate`

Validate content without generating.

```bash
python ucop_cli.py validate [OPTIONS]

Options:
  --input FILE         Input file to validate (required)
  --rules FILE         Validation rules file (default: config/validation.yaml)
  --fix               Attempt to fix issues
  --report FILE       Save validation report
  
Examples:
  # Validate single file
  python ucop_cli.py validate --input output/blog.md

  # Validate and fix
  python ucop_cli.py validate --input output/blog.md --fix

  # Generate validation report
  python ucop_cli.py validate --input output/blog.md --report validation.json
```

## Job Commands

### `job list`

List all jobs.

```bash
python ucop_cli.py job list [OPTIONS]

Options:
  --status STATUS     Filter by status (pending, running, completed, failed)
  --limit N          Max results to show (default: 20)
  --workflow NAME    Filter by workflow
  --format FORMAT    Output format (text, json, table)
  
Examples:
  # List all jobs
  python ucop_cli.py job list

  # List running jobs
  python ucop_cli.py job list --status running

  # List in JSON format
  python ucop_cli.py job list --format json
```

### `job get`

Get detailed job information.

```bash
python ucop_cli.py job get JOB_ID [OPTIONS]

Options:
  --format FORMAT     Output format (text, json) (default: text)
  --logs             Include execution logs
  --metrics          Include detailed metrics
  
Examples:
  # Get job details
  python ucop_cli.py job get 550e8400-e29b-41d4-a716-446655440000

  # Get with logs
  python ucop_cli.py job get 550e8400 --logs

  # Get as JSON
  python ucop_cli.py job get 550e8400 --format json --metrics
```

### `job pause`

Pause a running job.

```bash
python ucop_cli.py job pause JOB_ID

Examples:
  python ucop_cli.py job pause 550e8400-e29b-41d4-a716-446655440000
```

### `job resume`

Resume a paused job.

```bash
python ucop_cli.py job resume JOB_ID

Examples:
  python ucop_cli.py job resume 550e8400-e29b-41d4-a716-446655440000
```

### `job cancel`

Cancel a job.

```bash
python ucop_cli.py job cancel JOB_ID

Examples:
  python ucop_cli.py job cancel 550e8400-e29b-41d4-a716-446655440000
```

### `job watch`

Watch job progress in real-time.

```bash
python ucop_cli.py job watch JOB_ID [OPTIONS]

Options:
  --interval N       Refresh interval in seconds (default: 2)
  
Examples:
  python ucop_cli.py job watch 550e8400
```

## Agent Commands

### `agent list`

List all available agents.

```bash
python ucop_cli.py agent list [OPTIONS]

Options:
  --category CAT     Filter by category (content, seo, code, etc.)
  --format FORMAT    Output format (text, json, table)
  
Examples:
  # List all agents
  python ucop_cli.py agent list

  # List content agents only
  python ucop_cli.py agent list --category content

  # JSON output
  python ucop_cli.py agent list --format json
```

### `agent invoke`

Invoke a specific agent directly.

```bash
python ucop_cli.py agent invoke AGENT_ID [OPTIONS]

Options:
  --input JSON        Agent input as JSON string (required)
  --format FORMAT     Output format (text, json)
  
Examples:
  # Invoke keyword extraction
  python ucop_cli.py agent invoke keyword_extraction_agent \
    --input '{"content": "Article about Python programming"}'

  # JSON output
  python ucop_cli.py agent invoke outline_creation_agent \
    --input '{"kb_content": "..."}' \
    --format json
```

## Visualization Commands

### `viz workflows`

List and visualize workflows.

```bash
python ucop_cli.py viz workflows [OPTIONS]

Options:
  --format FORMAT     Output format (text, json, mermaid)
  --workflow NAME     Show specific workflow
  
Examples:
  # List all workflows
  python ucop_cli.py viz workflows

  # Show specific workflow
  python ucop_cli.py viz workflows --workflow blog_generation

  # Generate Mermaid diagram
  python ucop_cli.py viz workflows --format mermaid > workflow.mmd
```

### `viz graph`

Visualize workflow as graph.

```bash
python ucop_cli.py viz graph WORKFLOW [OPTIONS]

Options:
  --output FILE      Save graph to file (PNG, SVG, PDF)
  --format FORMAT    Graph format (graphviz, mermaid)
  
Examples:
  # Display workflow graph
  python ucop_cli.py viz graph blog_generation

  # Save as PNG
  python ucop_cli.py viz graph blog_generation --output workflow.png
```

### `viz agents`

Visualize agent relationships.

```bash
python ucop_cli.py viz agents [OPTIONS]

Options:
  --category CAT     Filter by category
  --output FILE      Save visualization
  
Examples:
  python ucop_cli.py viz agents
  python ucop_cli.py viz agents --category content
```

### `viz flows`

Visualize data flows between agents.

```bash
python ucop_cli.py viz flows [OPTIONS]

Options:
  --job JOB_ID       Show flows for specific job
  --output FILE      Save visualization
  
Examples:
  python ucop_cli.py viz flows --job 550e8400
```

### `viz bottlenecks`

Identify performance bottlenecks.

```bash
python ucop_cli.py viz bottlenecks [OPTIONS]

Options:
  --job JOB_ID       Analyze specific job
  --threshold N      Min execution time to highlight (seconds)
  
Examples:
  python ucop_cli.py viz bottlenecks
  python ucop_cli.py viz bottlenecks --job 550e8400 --threshold 30
```

### `viz metrics`

Display performance metrics.

```bash
python ucop_cli.py viz metrics [OPTIONS]

Options:
  --job JOB_ID       Metrics for specific job
  --agent AGENT_ID   Metrics for specific agent
  --format FORMAT    Output format (text, json, chart)
  
Examples:
  # System-wide metrics
  python ucop_cli.py viz metrics

  # Job metrics
  python ucop_cli.py viz metrics --job 550e8400

  # Agent metrics
  python ucop_cli.py viz metrics --agent code_generation_agent
```

## Checkpoint Commands

### `checkpoint list`

List checkpoints for a job.

```bash
python ucop_cli.py checkpoint list [OPTIONS]

Options:
  --job JOB_ID       Job ID (required)
  --format FORMAT    Output format (text, json)
  
Examples:
  python ucop_cli.py checkpoint list --job 550e8400
```

### `checkpoint restore`

Restore job from checkpoint.

```bash
python ucop_cli.py checkpoint restore [OPTIONS]

Options:
  --job JOB_ID       Job ID (required)
  --checkpoint ID    Checkpoint ID (required)
  
Examples:
  python ucop_cli.py checkpoint restore --job 550e8400 --checkpoint ckpt_3
```

### `checkpoint delete`

Delete checkpoint.

```bash
python ucop_cli.py checkpoint delete [OPTIONS]

Options:
  --job JOB_ID       Job ID (required)
  --checkpoint ID    Checkpoint ID (required)
  
Examples:
  python ucop_cli.py checkpoint delete --job 550e8400 --checkpoint ckpt_1
```

### `checkpoint cleanup`

Clean up old checkpoints.

```bash
python ucop_cli.py checkpoint cleanup [OPTIONS]

Options:
  --days N          Delete checkpoints older than N days
  --keep N          Keep only N most recent per job
  
Examples:
  # Delete checkpoints older than 30 days
  python ucop_cli.py checkpoint cleanup --days 30

  # Keep only 5 most recent per job
  python ucop_cli.py checkpoint cleanup --keep 5
```

## Configuration Commands

### `config snapshot`

Get configuration snapshot.

```bash
python ucop_cli.py config snapshot [OPTIONS]

Options:
  --format FORMAT    Output format (text, json, yaml)
  --output FILE      Save to file
  
Examples:
  # View current config
  python ucop_cli.py config snapshot

  # Save as JSON
  python ucop_cli.py config snapshot --format json --output config.json
```

### `config agents`

View agent configuration.

```bash
python ucop_cli.py config agents [OPTIONS]

Options:
  --agent AGENT_ID   Show specific agent
  --category CAT     Show category
  --format FORMAT    Output format
  
Examples:
  python ucop_cli.py config agents
  python ucop_cli.py config agents --agent code_generation_agent
```

### `config workflows`

View workflow configuration.

```bash
python ucop_cli.py config workflows [OPTIONS]

Options:
  --workflow NAME    Show specific workflow
  --format FORMAT    Output format
  
Examples:
  python ucop_cli.py config workflows
  python ucop_cli.py config workflows --workflow blog_generation
```

## Ingestion Commands

### `ingest kb`

Ingest knowledge base articles.

```bash
python ucop_cli.py ingest kb PATH [OPTIONS]

Options:
  --recursive        Process subdirectories
  --pattern PATTERN  File pattern (default: *.md)
  
Examples:
  python ucop_cli.py ingest kb ./kb_articles/
  python ucop_cli.py ingest kb ./kb --recursive --pattern "*.md"
```

### `ingest docs`

Ingest documentation.

```bash
python ucop_cli.py ingest docs PATH

Examples:
  python ucop_cli.py ingest docs ./documentation/
```

### `ingest api`

Ingest API reference.

```bash
python ucop_cli.py ingest api PATH

Examples:
  python ucop_cli.py ingest api ./api_docs/
```

### `discover topics`

Discover topics from KB directory.

```bash
python ucop_cli.py discover topics KB_DIR [OPTIONS]

Options:
  --max N           Max topics to return (default: 50)
  --format FORMAT   Output format (text, json)
  
Examples:
  python ucop_cli.py discover topics ./kb_articles/ --max 100
```

## Exit Codes

- **0**: Success
- **1**: General error
- **2**: Invalid arguments
- **3**: Configuration error
- **4**: Connection error
- **5**: Job execution failed

## Environment Variables

CLI commands respect these environment variables:

```bash
UCOP_CONFIG_DIR    # Config directory (default: ./config)
UCOP_OUTPUT_DIR    # Output directory (default: ./output)
UCOP_LOG_LEVEL     # Log level (default: INFO)
UCOP_LOG_FILE      # Log file path
```

## Examples by Use Case

### Daily Content Generation

```bash
# Morning: Generate from new KB articles
python ucop_cli.py ingest kb ./new_articles/
python ucop_cli.py discover topics ./new_articles/ --max 10

# Generate batch
python ucop_cli.py batch --manifest daily_batch.json --parallel

# Monitor progress
python ucop_cli.py job list --status running
```

### Quality Assurance

```bash
# Validate all generated content
for file in output/*.md; do
  python ucop_cli.py validate --input "$file" --fix
done

# Check for broken links
python ucop_cli.py validate --input output/ --recursive
```

### Performance Analysis

```bash
# View metrics
python ucop_cli.py viz metrics

# Identify bottlenecks
python ucop_cli.py viz bottlenecks --threshold 60

# Generate performance report
python tools/perf_report.py
```

### Debugging

```bash
# Enable debug logging
export UCOP_LOG_LEVEL=DEBUG

# Run single agent
python ucop_cli.py agent invoke outline_creation_agent \
  --input '{"kb_content": "test"}' \
  --format json

# Watch job execution
python ucop_cli.py job watch JOB_ID --interval 1
```

## Tips & Tricks

### Output Formatting

```bash
# Text output (default)
python ucop_cli.py job list

# JSON for scripting
python ucop_cli.py job list --format json | jq '.jobs[] | select(.status=="running")'

# Table format
python ucop_cli.py job list --format table
```

### Batch Processing

```bash
# Create manifest from glob
python -c "
import json, glob
manifest = {
    'batch_name': 'auto_batch',
    'workflow': 'blog_generation',
    'inputs': [{'source': f} for f in glob.glob('input/*.md')],
    'output_dir': 'output'
}
print(json.dumps(manifest))
" > batch.json

python ucop_cli.py batch --manifest batch.json
```

### Checkpoint Management

```bash
# Auto-checkpoint every 5 minutes
python ucop_cli.py generate --input file.md --checkpoint

# Resume from last checkpoint
python ucop_cli.py checkpoint list --job JOB_ID
python ucop_cli.py checkpoint restore --job JOB_ID --checkpoint latest
```

For more examples, see the [examples/](../examples/) directory.
