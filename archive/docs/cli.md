# CLI Reference

## Installation

```bash
chmod +x ucop_cli.py
./ucop_cli.py --help
```

## Commands

### generate

Generate content from a single source.

```bash
python ucop_cli.py generate --input INPUT --output OUTPUT [OPTIONS]

Options:
  --input, -i PATH          Input file path
  --output, -o PATH         Output directory
  --workflow, -w NAME       Workflow profile (default: blog_generation)
  --template, -t NAME       Template to use
  --keywords LIST           Target keywords (comma-separated)
  --verbose, -v             Verbose output
  --dry-run                 Validate without executing
```

**Examples:**
```bash
# Basic generation
python ucop_cli.py generate -i article.md -o output/

# With specific workflow
python ucop_cli.py generate -i article.md -o output/ -w rapid_generation

# With keywords
python ucop_cli.py generate -i article.md -o output/ --keywords "python,tutorial,beginner"
```

### batch

Process multiple files in batch.

```bash
python ucop_cli.py batch --manifest MANIFEST [OPTIONS]

Options:
  --manifest, -m PATH       Batch manifest JSON file
  --parallel, -p N          Number of parallel jobs
  --continue-on-error       Continue if individual job fails
```

**Manifest Format:**
```json
{
  "jobs": [
    {
      "input": "input1.md",
      "output": "output1/",
      "keywords": ["keyword1", "keyword2"]
    },
    {
      "input": "input2.md",
      "output": "output2/"
    }
  ]
}
```

### job

Job control and monitoring.

```bash
# List jobs
python ucop_cli.py job list [--status STATUS]

# Get job status
python ucop_cli.py job status JOB_ID

# Watch job in real-time
python ucop_cli.py job watch JOB_ID

# Cancel job
python ucop_cli.py job cancel JOB_ID

# Pause/Resume job
python ucop_cli.py job pause JOB_ID
python ucop_cli.py job resume JOB_ID

# Get job metrics
python ucop_cli.py job metrics JOB_ID
```

### viz (Visualization)

Workflow visualization commands.

```bash
# List workflows
python ucop_cli.py viz workflows [--json]

# Generate workflow graph
python ucop_cli.py viz graph WORKFLOW_ID [--json]

# Get workflow metrics
python ucop_cli.py viz metrics WORKFLOW_ID [--verbose]
```

### checkpoint

Checkpoint management.

```bash
# List checkpoints
python ucop_cli.py checkpoint list --job JOB_ID

# Save checkpoint
python ucop_cli.py checkpoint save --job JOB_ID --name NAME

# Restore checkpoint
python ucop_cli.py checkpoint restore --job JOB_ID --checkpoint NAME

# Delete checkpoint
python ucop_cli.py checkpoint delete --job JOB_ID --checkpoint NAME
```

### config

Configuration management.

```bash
# Show configuration
python ucop_cli.py config show [--format yaml|json]

# Set configuration value
python ucop_cli.py config set KEY VALUE

# Validate configuration
python ucop_cli.py config validate
```

### template

Template management.

```bash
# List templates
python ucop_cli.py template list [--category CATEGORY]

# Show template
python ucop_cli.py template show TEMPLATE_NAME

# Validate template
python ucop_cli.py template validate TEMPLATE_PATH
```

## Global Options

```bash
--config PATH       Use custom config file
--log-level LEVEL   Set log level (DEBUG, INFO, WARN, ERROR)
--no-color          Disable colored output
--json              Output in JSON format
--quiet, -q         Suppress non-essential output
```

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: Configuration error
- `4`: Execution error
- `5`: Timeout
