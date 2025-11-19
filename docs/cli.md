# CLI

## Overview

The UCOP CLI (`ucop_cli.py`) provides command-line access to all system functionality. It includes 35+ commands organized into 7 categories: generation, jobs, configuration, agents, checkpoints, visualization, and mesh orchestration.

## Installation

CLI is included with UCOP installation. No separate setup required.

```bash
# Verify CLI is working
python ucop_cli.py --help

# Check version
python ucop_cli.py --version
```

## Command Categories

### Generation Commands

Generate content and manage workflows.

#### generate

Generate blog posts from knowledge base articles.

**Usage**:
```bash
python ucop_cli.py generate \
    --input <file> \
    --output <dir> \
    --workflow <name> \
    [--verbose] \
    [--config <file>]
```

**Options**:
- `--input, -i`: Input KB article file (required)
- `--output, -o`: Output directory (default: ./output)
- `--workflow, -w`: Workflow name (default: default)
- `--verbose, -v`: Enable verbose logging
- `--config, -c`: Custom config file path

**Examples**:
```bash
# Generate with default workflow
python ucop_cli.py generate -i input/kb/article.md -o output/

# Use quick_draft workflow
python ucop_cli.py generate -i input/kb/article.md -w quick_draft

# Code generation only
python ucop_cli.py generate -i input/api/reference.md -w code_only

# With custom config
python ucop_cli.py generate -i input/kb/article.md -c custom_config.yaml
```

#### batch

Process multiple files in batch mode.

**Usage**:
```bash
python ucop_cli.py batch \
    --manifest <json_file> \
    [--parallel] \
    [--max-workers <n>]
```

**Options**:
- `--manifest, -m`: JSON manifest file (required)
- `--parallel, -p`: Enable parallel processing
- `--max-workers`: Maximum parallel workers (default: 3)

**Manifest Format**:
```json
{
  "workflow": "default",
  "inputs": [
    {
      "kb_file": "input/article1.md",
      "output_dir": "output/batch1"
    },
    {
      "kb_file": "input/article2.md",
      "output_dir": "output/batch2"
    }
  ],
  "options": {
    "parallel": true,
    "stop_on_error": false
  }
}
```

**Examples**:
```bash
# Sequential batch processing
python ucop_cli.py batch -m batch_manifest.json

# Parallel batch processing
python ucop_cli.py batch -m batch_manifest.json --parallel --max-workers 5
```

#### validate

Validate input files before processing.

**Usage**:
```bash
python ucop_cli.py validate \
    --input <file> \
    [--type <type>]
```

**Options**:
- `--input, -i`: Input file to validate (required)
- `--type, -t`: File type (kb, api, docs, blog)

**Examples**:
```bash
# Validate KB article
python ucop_cli.py validate -i input/kb/article.md --type kb

# Validate API documentation
python ucop_cli.py validate -i input/api/reference.md --type api
```

#### list-templates

List available content templates.

**Usage**:
```bash
python ucop_cli.py list-templates [--category <name>]
```

**Examples**:
```bash
# List all templates
python ucop_cli.py list-templates

# List blog templates
python ucop_cli.py list-templates --category blog
```

### Job Commands

Manage and monitor jobs.

#### job list

List all jobs or filter by status.

**Usage**:
```bash
python ucop_cli.py job list \
    [--status <status>] \
    [--limit <n>] \
    [--sort <field>]
```

**Options**:
- `--status, -s`: Filter by status (pending, running, completed, failed, cancelled)
- `--limit, -l`: Maximum results (default: 50)
- `--sort`: Sort field (created_at, updated_at, duration)

**Examples**:
```bash
# List all jobs
python ucop_cli.py job list

# List running jobs
python ucop_cli.py job list --status running

# List recent 10 jobs
python ucop_cli.py job list --limit 10 --sort created_at
```

#### job get

Get detailed job information.

**Usage**:
```bash
python ucop_cli.py job get --id <job_id>
```

**Examples**:
```bash
# Get job details
python ucop_cli.py job get --id job_12345

# Get job with output
python ucop_cli.py job get --id job_12345 --show-output
```

#### job pause

Pause a running job.

**Usage**:
```bash
python ucop_cli.py job pause --id <job_id>
```

**Examples**:
```bash
python ucop_cli.py job pause --id job_12345
```

#### job resume

Resume a paused job.

**Usage**:
```bash
python ucop_cli.py job resume --id <job_id>
```

**Examples**:
```bash
python ucop_cli.py job resume --id job_12345
```

#### job cancel

Cancel a running or paused job.

**Usage**:
```bash
python ucop_cli.py job cancel --id <job_id>
```

**Examples**:
```bash
python ucop_cli.py job cancel --id job_12345
```

### Configuration Commands

View and manage configuration.

#### config snapshot

View complete system configuration.

**Usage**:
```bash
python ucop_cli.py config snapshot [--format <format>]
```

**Options**:
- `--format, -f`: Output format (json, yaml, text)

**Examples**:
```bash
# View as text
python ucop_cli.py config snapshot

# Export as JSON
python ucop_cli.py config snapshot --format json > config_backup.json

# Export as YAML
python ucop_cli.py config snapshot --format yaml > config_backup.yaml
```

#### config agents

View agent configurations.

**Usage**:
```bash
python ucop_cli.py config agents [--agent <name>]
```

**Examples**:
```bash
# List all agents
python ucop_cli.py config agents

# View specific agent
python ucop_cli.py config agents --agent code_generation_node
```

#### config workflows

View workflow configurations.

**Usage**:
```bash
python ucop_cli.py config workflows [--workflow <name>]
```

**Examples**:
```bash
# List all workflows
python ucop_cli.py config workflows

# View specific workflow
python ucop_cli.py config workflows --workflow default
```

#### config tone

View tone configuration.

**Usage**:
```bash
python ucop_cli.py config tone [--section <name>]
```

**Examples**:
```bash
# View all tone settings
python ucop_cli.py config tone

# View section-specific tone
python ucop_cli.py config tone --section introduction
```

#### config performance

View performance settings.

**Usage**:
```bash
python ucop_cli.py config performance
```

**Examples**:
```bash
python ucop_cli.py config performance
```

### Agent Commands

Manage and monitor agents.

#### agents list

List all registered agents.

**Usage**:
```bash
python ucop_cli.py agents list [--category <name>]
```

**Options**:
- `--category, -c`: Filter by category (ingestion, content, seo, code, publishing, research, support)

**Examples**:
```bash
# List all agents
python ucop_cli.py agents list

# List content agents
python ucop_cli.py agents list --category content

# List with details
python ucop_cli.py agents list --verbose
```

#### agents invoke

Invoke an agent directly.

**Usage**:
```bash
python ucop_cli.py agents invoke \
    --agent <name> \
    --input <json> \
    [--output <file>]
```

**Options**:
- `--agent, -a`: Agent name (required)
- `--input, -i`: Input JSON data (required)
- `--output, -o`: Output file path

**Examples**:
```bash
# Invoke outline creation
python ucop_cli.py agents invoke \
    --agent create_outline_node \
    --input '{"topic": {"title": "Example"}}' \
    --output outline.json

# Invoke from file
python ucop_cli.py agents invoke \
    --agent create_outline_node \
    --input @input.json
```

#### agents health

Check agent health status.

**Usage**:
```bash
python ucop_cli.py agents health [--agent <name>]
```

**Examples**:
```bash
# Check all agents
python ucop_cli.py agents health

# Check specific agent
python ucop_cli.py agents health --agent code_generation_node
```

#### agents failures

View agent failure history.

**Usage**:
```bash
python ucop_cli.py agents failures \
    [--agent <name>] \
    [--since <date>] \
    [--limit <n>]
```

**Examples**:
```bash
# View all failures
python ucop_cli.py agents failures

# View failures for specific agent
python ucop_cli.py agents failures --agent code_generation_node

# View recent failures
python ucop_cli.py agents failures --since 2024-11-01 --limit 10
```

#### agents logs

View agent execution logs.

**Usage**:
```bash
python ucop_cli.py agents logs \
    --agent <name> \
    [--level <level>] \
    [--tail <n>]
```

**Options**:
- `--agent, -a`: Agent name (required)
- `--level, -l`: Log level (DEBUG, INFO, WARNING, ERROR)
- `--tail, -t`: Show last N lines

**Examples**:
```bash
# View agent logs
python ucop_cli.py agents logs --agent code_generation_node

# View error logs
python ucop_cli.py agents logs --agent code_generation_node --level ERROR

# Tail logs
python ucop_cli.py agents logs --agent code_generation_node --tail 50
```

#### agents reset-health

Reset agent health metrics.

**Usage**:
```bash
python ucop_cli.py agents reset-health [--agent <name>]
```

**Examples**:
```bash
# Reset all agent health
python ucop_cli.py agents reset-health

# Reset specific agent
python ucop_cli.py agents reset-health --agent code_generation_node
```

### Checkpoint Commands

Manage workflow checkpoints.

#### checkpoint list

List checkpoints for a job.

**Usage**:
```bash
python ucop_cli.py checkpoint list \
    --job <job_id> \
    [--limit <n>]
```

**Examples**:
```bash
# List all checkpoints
python ucop_cli.py checkpoint list --job job_12345

# List recent checkpoints
python ucop_cli.py checkpoint list --job job_12345 --limit 10
```

#### checkpoint restore

Restore job from checkpoint.

**Usage**:
```bash
python ucop_cli.py checkpoint restore \
    --id <checkpoint_id> \
    [--continue]
```

**Options**:
- `--id, -i`: Checkpoint ID (required)
- `--continue, -c`: Continue execution after restore

**Examples**:
```bash
# Restore checkpoint
python ucop_cli.py checkpoint restore --id checkpoint_67890

# Restore and continue
python ucop_cli.py checkpoint restore --id checkpoint_67890 --continue
```

#### checkpoint delete

Delete a checkpoint.

**Usage**:
```bash
python ucop_cli.py checkpoint delete --id <checkpoint_id>
```

**Examples**:
```bash
python ucop_cli.py checkpoint delete --id checkpoint_67890
```

#### checkpoint cleanup

Clean up old checkpoints.

**Usage**:
```bash
python ucop_cli.py checkpoint cleanup \
    [--days <n>] \
    [--job <job_id>] \
    [--force]
```

**Options**:
- `--days, -d`: Delete checkpoints older than N days (default: 7)
- `--job, -j`: Cleanup for specific job
- `--force, -f`: Skip confirmation

**Examples**:
```bash
# Cleanup old checkpoints
python ucop_cli.py checkpoint cleanup --days 7

# Cleanup for specific job
python ucop_cli.py checkpoint cleanup --job job_12345

# Force cleanup
python ucop_cli.py checkpoint cleanup --days 30 --force
```

### Visualization Commands

Visualize workflows and performance.

#### viz workflows

List available workflows.

**Usage**:
```bash
python ucop_cli.py viz workflows [--format <format>]
```

**Examples**:
```bash
# List workflows
python ucop_cli.py viz workflows

# Export as JSON
python ucop_cli.py viz workflows --format json
```

#### viz graph

Visualize workflow graph.

**Usage**:
```bash
python ucop_cli.py viz graph \
    --workflow <name> \
    [--output <file>]
```

**Examples**:
```bash
# Show workflow graph
python ucop_cli.py viz graph --workflow default

# Export to file
python ucop_cli.py viz graph --workflow default --output graph.png
```

#### viz metrics

Show agent performance metrics.

**Usage**:
```bash
python ucop_cli.py viz metrics \
    [--agent <name>] \
    [--period <days>]
```

**Examples**:
```bash
# Show all metrics
python ucop_cli.py viz metrics

# Show agent-specific metrics
python ucop_cli.py viz metrics --agent code_generation_node

# Show recent metrics
python ucop_cli.py viz metrics --period 7
```

#### viz agents

Visualize agent dependencies.

**Usage**:
```bash
python ucop_cli.py viz agents [--output <file>]
```

**Examples**:
```bash
# Show agent graph
python ucop_cli.py viz agents

# Export to file
python ucop_cli.py viz agents --output agents.png
```

#### viz flows

Visualize data flows.

**Usage**:
```bash
python ucop_cli.py viz flows \
    --workflow <name> \
    [--output <file>]
```

**Examples**:
```bash
# Show data flows
python ucop_cli.py viz flows --workflow default

# Export to file
python ucop_cli.py viz flows --workflow default --output flows.png
```

#### viz bottlenecks

Identify performance bottlenecks.

**Usage**:
```bash
python ucop_cli.py viz bottlenecks \
    [--workflow <name>] \
    [--threshold <ms>]
```

**Examples**:
```bash
# Show bottlenecks
python ucop_cli.py viz bottlenecks

# Show for specific workflow
python ucop_cli.py viz bottlenecks --workflow default

# Show agents slower than 5s
python ucop_cli.py viz bottlenecks --threshold 5000
```

#### viz debug

Debug workflow execution.

**Usage**:
```bash
python ucop_cli.py viz debug \
    --job <job_id> \
    [--output <file>]
```

**Examples**:
```bash
# Debug job execution
python ucop_cli.py viz debug --job job_12345

# Export debug trace
python ucop_cli.py viz debug --job job_12345 --output debug.html
```

### Mesh Commands

Mesh orchestration mode commands.

#### mesh discover

Discover available agents in mesh.

**Usage**:
```bash
python ucop_cli.py mesh discover [--capability <name>]
```

**Examples**:
```bash
# Discover all agents
python ucop_cli.py mesh discover

# Discover code generation agents
python ucop_cli.py mesh discover --capability code_generation
```

#### mesh execute

Execute task in mesh mode.

**Usage**:
```bash
python ucop_cli.py mesh execute \
    --task <json> \
    [--max-hops <n>]
```

**Examples**:
```bash
# Execute mesh task
python ucop_cli.py mesh execute \
    --task '{"goal": "generate_blog", "input": "article.md"}' \
    --max-hops 10
```

#### mesh list

List mesh execution history.

**Usage**:
```bash
python ucop_cli.py mesh list [--limit <n>]
```

**Examples**:
```bash
# List mesh executions
python ucop_cli.py mesh list

# List recent executions
python ucop_cli.py mesh list --limit 10
```

#### mesh stats

Show mesh performance statistics.

**Usage**:
```bash
python ucop_cli.py mesh stats [--period <days>]
```

**Examples**:
```bash
# Show mesh stats
python ucop_cli.py mesh stats

# Show last 7 days
python ucop_cli.py mesh stats --period 7
```

### Ingestion Commands

#### ingest

Ingest content and create embeddings.

**Usage**:
```bash
python ucop_cli.py ingest \
    --type <type> \
    --input <path> \
    [--force]
```

**Options**:
- `--type, -t`: Content type (kb, api, docs, blog, tutorial)
- `--input, -i`: Input file or directory
- `--force, -f`: Force re-ingestion

**Examples**:
```bash
# Ingest KB article
python ucop_cli.py ingest --type kb --input input/kb/article.md

# Ingest API docs directory
python ucop_cli.py ingest --type api --input input/api/

# Force re-ingestion
python ucop_cli.py ingest --type kb --input input/kb/ --force
```

#### discover-topics

Discover topics from KB articles.

**Usage**:
```bash
python ucop_cli.py discover-topics \
    --input <path> \
    [--output <file>]
```

**Examples**:
```bash
# Discover topics
python ucop_cli.py discover-topics --input input/kb/

# Save to file
python ucop_cli.py discover-topics --input input/kb/ --output topics.json
```

## Global Options

Available for all commands:

- `--help, -h`: Show command help
- `--verbose, -v`: Enable verbose output
- `--quiet, -q`: Suppress output
- `--config, -c`: Custom config file
- `--log-level`: Set log level (DEBUG, INFO, WARNING, ERROR)
- `--no-color`: Disable colored output

**Examples**:
```bash
# Get command help
python ucop_cli.py generate --help

# Verbose mode
python ucop_cli.py generate -i input.md -v

# Custom config
python ucop_cli.py generate -i input.md -c custom_config.yaml

# Debug logging
python ucop_cli.py generate -i input.md --log-level DEBUG
```

## Output Formats

Many commands support multiple output formats:

- `--format json`: JSON output
- `--format yaml`: YAML output
- `--format text`: Plain text (default)
- `--format csv`: CSV output
- `--format html`: HTML output

## Shell Completion

Enable shell completion for faster CLI usage:

### Bash
```bash
# Add to ~/.bashrc
eval "$(_UCOP_CLI_COMPLETE=bash_source python ucop_cli.py)"
```

### Zsh
```bash
# Add to ~/.zshrc
eval "$(_UCOP_CLI_COMPLETE=zsh_source python ucop_cli.py)"
```

## Aliases

Create shell aliases for common commands:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias ucop='python ucop_cli.py'
alias ucop-gen='python ucop_cli.py generate'
alias ucop-jobs='python ucop_cli.py job list'
alias ucop-agents='python ucop_cli.py agents list'
```

## Best Practices

1. **Use --help**: Check command help before usage
2. **Enable verbose mode**: Use -v for troubleshooting
3. **Save outputs**: Redirect output to files for records
4. **Check job status**: Monitor jobs with `job list`
5. **Use batch mode**: Process multiple files efficiently
6. **Validate inputs**: Use `validate` before generation
7. **Monitor resources**: Check agent health regularly
8. **Cleanup checkpoints**: Clean old checkpoints periodically

---

*This documentation is part of the UCOP project. For more information, see the [main README](../README.md).*
