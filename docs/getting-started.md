# Getting Started

## Overview

This guide will help you install, configure, and run your first UCOP workflow in under 10 minutes.

## Prerequisites

### Required

- **Python 3.10+** (3.12 recommended)
  - Check version: `python --version`
  - Install from: https://www.python.org/downloads/

- **Git**
  - Check version: `git --version`
  - Install from: https://git-scm.com/downloads

### Recommended

- **Ollama** (for local LLM inference)
  - Faster and free compared to cloud providers
  - Install from: https://ollama.ai
  - Recommended models:
    - `ollama pull qwen2.5:14b` (content generation)
    - `ollama pull deepseek-coder:33b` (code generation)

- **Node.js 18+** (for web UI development)
  - Check version: `node --version`
  - Install from: https://nodejs.org/

### Optional

- **Google Gemini API Key** (fallback LLM)
  - Get from: https://ai.google.dev/
  - Free tier available

- **OpenAI API Key** (secondary fallback)
  - Get from: https://platform.openai.com/
  - Paid service

- **GitHub Token** (for Gist uploads)
  - Generate at: https://github.com/settings/tokens
  - Requires `gist` scope

## Installation

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd ucop
```

### Step 2: Run Setup Script

#### Windows

```cmd
setup.bat
```

This script will:
- Create Python virtual environment
- Install all dependencies
- Set up initial configuration
- Verify installation

#### Linux/Mac

```bash
chmod +x setup.sh
./setup.sh
```

### Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env  # or use your preferred editor
```

Required environment variables:

```bash
# LLM Providers (at least one required)
OLLAMA_BASE_URL=http://localhost:11434
GOOGLE_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here

# GitHub (optional, for Gist uploads)
GITHUB_TOKEN=your_github_token_here

# Paths
CHROMA_DB_PATH=./chroma_db
OUTPUT_PATH=./output
```

### Step 4: Verify Installation

```bash
# Check CLI is working
python ucop_cli.py --help

# List available agents
python ucop_cli.py agents list

# Check system health
python tools/validate_system.py
```

Expected output:
```
✓ Python version: 3.12.0
✓ Dependencies installed
✓ Configuration loaded
✓ Ollama connection: OK
✓ ChromaDB initialized
✓ 34 agents registered
```

## Quick Start - CLI

### Example 1: Generate Single Blog Post

```bash
# Prepare your knowledge base article
mkdir -p input
echo "# Example KB Article
This is a sample knowledge base article about file conversion.
" > input/example.md

# Generate blog post
python ucop_cli.py generate \
    --input input/example.md \
    --output output/ \
    --workflow default

# Check output
ls -l output/
cat output/example_blog.md
```

### Example 2: Batch Processing

Create a batch configuration file `batch.json`:

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
    "parallel": false,
    "stop_on_error": false
  }
}
```

Run batch:

```bash
python ucop_cli.py batch --manifest batch.json
```

### Example 3: Code Generation Only

```bash
# Generate only code from API docs
python ucop_cli.py generate \
    --input input/api_reference.md \
    --output output/ \
    --workflow code_only
```

### Example 4: Monitor Jobs

```bash
# List all jobs
python ucop_cli.py job list

# Get job details
python ucop_cli.py job get --id <job_id>

# View job status
python ucop_cli.py job list --status running

# Cancel a job
python ucop_cli.py job cancel --id <job_id>
```

## Quick Start - Web UI

### Step 1: Start Web Server

```bash
# Start the server
python start_web.py

# Server will start on http://localhost:8000
```

### Step 2: Access Web Interface

Open your browser to: http://localhost:8000

The web UI provides:
- Visual workflow editor
- Job monitoring dashboard
- Agent status viewer
- Configuration inspector
- Performance metrics

### Step 3: Create Workflow

1. Click "Workflow Editor"
2. Drag agents from left panel to canvas
3. Connect agents with edges
4. Configure agent parameters
5. Save workflow
6. Click "Execute"

### Step 4: Monitor Execution

1. Go to "Jobs" page
2. See real-time job status
3. View agent execution trace
4. Check output files

## Your First Workflow

Let's create a complete blog generation workflow step by step.

### 1. Prepare Input Files

```bash
# Create directory structure
mkdir -p input/{kb,api,docs}
mkdir -p output

# Create sample KB article
cat > input/kb/sample.md << 'EOF'
# How to Convert DOCX to PDF

Converting DOCX files to PDF is a common requirement in document processing.
This article explains how to use Aspose.Words for .NET to perform this conversion.

## Prerequisites
- Aspose.Words for .NET library
- .NET Framework 4.7.2 or higher

## Basic Conversion
The simplest way to convert DOCX to PDF is using the Save method.

## Advanced Options
You can customize the PDF output with PdfSaveOptions.
EOF
```

### 2. Ingest Content

```bash
# Ingest KB article and create embeddings
python ucop_cli.py ingest \
    --type kb \
    --input input/kb/sample.md
```

### 3. Generate Content

```bash
# Run full blog generation workflow
python ucop_cli.py generate \
    --input input/kb/sample.md \
    --output output/ \
    --workflow default \
    --verbose

# Watch progress
# Progress will show agent execution in real-time:
# [1/18] topic_identification: ✓ Complete
# [2/18] kb_ingestion: ✓ Complete
# [3/18] outline_creation: ✓ Complete
# ...
```

### 4. Review Output

```bash
# Check generated file
ls -lh output/

# View content
cat output/how-to-convert-docx-to-pdf.md

# Check frontmatter
head -20 output/how-to-convert-docx-to-pdf.md
```

Expected output structure:
```markdown
---
title: "How to Convert DOCX to PDF in C#"
description: "Learn how to convert DOCX to PDF using Aspose.Words"
keywords: ["docx to pdf", "document conversion", "aspose"]
date: 2024-11-17
---

# How to Convert DOCX to PDF in C#

Introduction paragraph...

## Prerequisites

...

## Code Example

```csharp
// Code here
```
```

## Common Workflows

### Workflow 1: Default (Full Blog)

**Purpose**: Complete blog post with SEO and code  
**Duration**: 5-8 minutes  
**Agents Used**: 18

```bash
python ucop_cli.py generate \
    --input input/kb/article.md \
    --workflow default
```

### Workflow 2: Quick Draft

**Purpose**: Fast content without SEO  
**Duration**: 2-3 minutes  
**Agents Used**: 7

```bash
python ucop_cli.py generate \
    --input input/kb/article.md \
    --workflow quick_draft
```

### Workflow 3: Code Only

**Purpose**: Generate code examples only  
**Duration**: 3-4 minutes  
**Agents Used**: 8

```bash
python ucop_cli.py generate \
    --input input/api/reference.md \
    --workflow code_only
```

## CLI Command Reference

### Generation Commands

```bash
# Generate single blog post
ucop_cli.py generate --input <file> --output <dir> --workflow <name>

# Batch processing
ucop_cli.py batch --manifest <json_file>

# List templates
ucop_cli.py list-templates

# Validate input
ucop_cli.py validate --input <file>
```

### Job Commands

```bash
# List jobs
ucop_cli.py job list [--status <status>]

# Get job details
ucop_cli.py job get --id <job_id>

# Pause/resume/cancel
ucop_cli.py job pause --id <job_id>
ucop_cli.py job resume --id <job_id>
ucop_cli.py job cancel --id <job_id>
```

### Agent Commands

```bash
# List agents
ucop_cli.py agents list

# Invoke agent directly
ucop_cli.py agents invoke --agent <name> --input <json>

# Check agent health
ucop_cli.py agents health

# View agent failures
ucop_cli.py agents failures [--agent <name>]
```

### Configuration Commands

```bash
# View configuration
ucop_cli.py config snapshot
ucop_cli.py config agents
ucop_cli.py config workflows
ucop_cli.py config tone

# Validate configuration
ucop_cli.py config validate
```

### Checkpoint Commands

```bash
# List checkpoints
ucop_cli.py checkpoint list --job <job_id>

# Restore from checkpoint
ucop_cli.py checkpoint restore --id <checkpoint_id>

# Delete checkpoint
ucop_cli.py checkpoint delete --id <checkpoint_id>

# Cleanup old checkpoints
ucop_cli.py checkpoint cleanup --days 30
```

### Visualization Commands

```bash
# List workflows
ucop_cli.py viz workflows

# Show workflow graph
ucop_cli.py viz graph --workflow <name>

# Show agent metrics
ucop_cli.py viz metrics

# Show agent list
ucop_cli.py viz agents

# Show data flows
ucop_cli.py viz flows

# Show bottlenecks
ucop_cli.py viz bottlenecks

# Debug workflow
ucop_cli.py viz debug --job <job_id>
```

## Configuration Quick Reference

### Minimal Configuration

```yaml
# config/main.yaml
workflows:
  use_langgraph: false
  enable_parallel_execution: false

jobs:
  max_concurrent_jobs: 1
```

### Recommended Configuration

```yaml
# config/main.yaml
workflows:
  use_langgraph: true
  enable_parallel_execution: true
  max_parallel_agents: 5

jobs:
  max_concurrent_jobs: 3
  max_retries: 3
```

### High-Performance Configuration

```yaml
# config/main.yaml
workflows:
  use_langgraph: true
  enable_parallel_execution: true
  max_parallel_agents: 10

jobs:
  max_concurrent_jobs: 5
  max_retries: 3
```

## Troubleshooting

### Common Issues

#### Issue: Ollama Connection Failed

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Check available models
ollama list
```

#### Issue: Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python version
python --version  # Should be 3.10+
```

#### Issue: ChromaDB Errors

```bash
# Delete and reinitialize database
rm -rf chroma_db/
python ucop_cli.py ingest --type kb --input input/kb/
```

#### Issue: Agent Failures

```bash
# Check agent health
python ucop_cli.py agents health

# View failure details
python ucop_cli.py agents failures

# View agent logs
python ucop_cli.py agents logs --agent <agent_name>
```

#### Issue: Out of Memory

```bash
# Reduce parallel execution
# Edit config/main.yaml:
max_parallel_agents: 2

# Reduce agent memory limits
# Edit config/agents.yaml:
max_memory_mb: 1024
```

### Getting Help

- **Documentation**: Check docs/ folder
- **Troubleshooting**: See [troubleshooting.md](troubleshooting.md)
- **Examples**: Check examples/ folder
- **Validation**: Run `python tools/validate_system.py`

## Next Steps

1. **Learn More**:
   - [Architecture](architecture.md) - System design
   - [Agents](agents.md) - Agent reference
   - [Workflows](workflows.md) - Workflow details
   - [Configuration](configuration.md) - Advanced config

2. **Customize**:
   - Create custom workflows
   - Tune agent parameters
   - Add custom templates
   - Write custom agents

3. **Production**:
   - [Deployment](deployment.md) - Production setup
   - [Performance](performance.md) - Optimization
   - [Monitoring](monitoring.md) - Observability
   - [Security](security.md) - Best practices

---

*This documentation is part of the UCOP project. For more information, see the [main README](../README.md).*
