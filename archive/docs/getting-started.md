# Getting Started with UCOP

This guide walks you through installing, configuring, and running your first content generation workflow with UCOP.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [First Content Generation](#first-content-generation)
- [Understanding the Output](#understanding-the-output)
- [Next Steps](#next-steps)

## System Requirements

### Minimum Requirements

- **OS**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Python**: 3.8 or higher (3.10+ recommended)
- **Memory**: 4 GB RAM minimum, 8 GB recommended
- **Disk Space**: 2 GB for code and dependencies, 10+ GB for models (if using Ollama)
- **Internet**: Required for cloud LLM providers (Gemini, OpenAI)

### Optional Components

- **Ollama**: For local LLM inference (recommended for privacy and cost savings)
  - Download from https://ollama.ai
  - Supports qwen2.5, phi4, deepcoder, mistral models
- **Node.js 18+**: For web UI development
- **Docker**: For containerized deployment
- **CUDA-capable GPU**: For faster local model inference (optional)

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd ucop
```

### Step 2: Run Setup Script

#### Windows

```bash
# Run the automated setup script
setup.bat

# What it does:
# 1. Checks Python version (3.8+)
# 2. Creates virtual environment
# 3. Installs all dependencies
# 4. Creates project directories
# 5. Generates default .env file
# 6. Validates core modules
```

#### Linux/Mac

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup
./setup.sh

# Or manually install
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Install Optional Dependencies

#### Ollama (Recommended)

```bash
# Download and install from https://ollama.ai

# Pull recommended models
ollama pull qwen2.5:14b       # Primary model (8 GB)
ollama pull phi4:14b          # Alternative (8 GB)
ollama pull mistral:latest    # Fallback (4 GB)

# Verify installation
ollama list
```

#### Node.js (For Web UI)

```bash
# Check if Node.js is installed
node --version

# If not installed, download from https://nodejs.org

# Install web UI dependencies
cd src/web/static
npm install
npm run build
```

### Step 4: Verify Installation

```bash
# Activate virtual environment (if not active)
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Run smoke tests
pytest tests/test_imports_smoke.py -v

# Verify CLI
python ucop_cli.py --help

# Expected output: List of available commands
```

## Configuration

### Step 1: Environment Variables

Create or edit `.env` file:

```bash
# Copy example if it doesn't exist
cp .env.example .env

# Edit with your preferred editor
vim .env  # or nano, notepad, etc.
```

### Step 2: Configure LLM Providers

#### Option A: Local-Only (Ollama)

```bash
# .env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b
LOG_LEVEL=INFO
```

This configuration uses only local models (no API keys needed).

#### Option B: Cloud + Fallback

```bash
# .env
# Primary: Ollama (local)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b

# Fallback: Google Gemini
GEMINI_API_KEY=your_gemini_api_key_here

# Fallback: OpenAI (optional)
OPENAI_API_KEY=your_openai_api_key_here

LOG_LEVEL=INFO
```

#### Option C: Cloud-Only (No Ollama)

```bash
# .env
# Primary: Google Gemini
GEMINI_API_KEY=your_gemini_api_key_here

# Fallback: OpenAI
OPENAI_API_KEY=your_openai_api_key_here

LOG_LEVEL=INFO
```

### Step 3: Configure Workflows

Edit `config/main.yaml` for workflow preferences:

```yaml
workflows:
  # Use LangGraph for advanced orchestration
  use_langgraph: true
  
  # Enable parallel agent execution
  enable_parallel_execution: true
  max_parallel_agents: 5
  
  # Default workflow profile
  default_profile: "blog_generation"
```

### Step 4: API Keys (Optional Services)

```bash
# .env
# GitHub Gists (for code sample uploads)
GITHUB_TOKEN=your_github_token_here

# Google Trends (for keyword research)
# No API key needed - uses pytrends
```

### Step 5: Validate Configuration

```bash
# Check configuration
python tools/validate.py

# Expected output: ✓ All validations passed

# Test LLM connectivity
python -c "from src.services.llm_service import LLMService; from src.core.config import load_config; config = load_config(); llm = LLMService(config); print(llm.check_health())"

# Expected: {'OLLAMA': True, 'GEMINI': False, ...}
```

## First Content Generation

### Example 1: Single Article (CLI)

```bash
# Create a simple KB article
mkdir -p input
cat > input/example.md << 'EOF'
# Image Processing with Aspose.Imaging

Aspose.Imaging is a powerful library for image manipulation.

## Key Features
- Load and save images in multiple formats
- Apply filters and transformations
- Convert between formats

## Example Usage
```csharp
using Aspose.Imaging;

var image = Image.Load("input.jpg");
image.Save("output.png");
```
EOF

# Generate blog post
python ucop_cli.py generate \
    --input input/example.md \
    --output output/ \
    --workflow blog_generation

# Watch progress
# Expected output:
# ✓ Ingesting KB article...
# ✓ Creating outline...
# ✓ Writing introduction...
# ✓ Writing sections...
# ✓ Generating code examples...
# ✓ Optimizing for SEO...
# ✓ Creating frontmatter...
# ✓ Blog post generated: output/blog_image_processing.md
```

### Example 2: Batch Processing

```bash
# Create batch manifest
cat > batch.json << 'EOF'
{
  "batch_name": "Q1_2025_Content",
  "workflow": "blog_generation",
  "inputs": [
    {"source": "input/article1.md"},
    {"source": "input/article2.md"},
    {"source": "input/article3.md"}
  ],
  "output_dir": "output/q1_2025",
  "options": {
    "parallel": true,
    "max_workers": 3
  }
}
EOF

# Process batch
python ucop_cli.py batch --manifest batch.json

# Monitor progress
python ucop_cli.py job list
```

### Example 3: Web UI (Visual)

```bash
# Start web server
python start_web.py

# Open browser to http://localhost:8000

# In the web UI:
# 1. Click "New Job" button
# 2. Select "Blog Generation" workflow
# 3. Upload KB article or paste content
# 4. Configure options (keywords, tone, etc.)
# 5. Click "Generate"
# 6. Monitor real-time progress in right panel
# 7. Download completed blog post
```

## Understanding the Output

### Output Structure

```
output/
├── blog_image_processing.md      # Final blog post (Hugo/Jekyll format)
├── blog_image_processing_manifest.json  # Generation metadata
└── code_samples/                 # Extracted code samples (if any)
    └── example_csharp.cs
```

### Blog Post Format

```markdown
---
title: "Image Processing Made Easy with Aspose.Imaging"
date: 2025-11-17T10:30:00Z
draft: false
slug: image-processing-aspose-imaging
description: "Learn how to process images..."
keywords:
  - image processing
  - aspose.imaging
  - csharp
categories:
  - Tutorials
tags:
  - Images
  - Programming
author: "UCOP Content Generator"
---

# Image Processing Made Easy with Aspose.Imaging

[Generated introduction with hook...]

## Understanding Image Formats

[Generated section content...]

## Working with Transformations

[Generated section content with code examples...]

## Conclusion

[Generated conclusion with CTA...]

## FAQ

**Q: What image formats are supported?**
A: [Generated answer...]

[Additional sections...]
```

### Manifest File

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "workflow": "blog_generation",
  "status": "completed",
  "input": {
    "source_file": "input/example.md",
    "keywords": ["image processing", "aspose.imaging"]
  },
  "output": {
    "blog_file": "output/blog_image_processing.md",
    "word_count": 1850,
    "code_samples": 3
  },
  "metrics": {
    "duration_seconds": 245,
    "tokens_used": 15420,
    "agents_executed": 18
  },
  "agents_used": [
    "KBIngestionAgent",
    "OutlineCreationAgent",
    "IntroductionWriterAgent",
    ...
  ]
}
```

## Next Steps

### Learn More About Workflows

- Read [Workflows & Pipelines](workflows.md) for advanced workflow customization
- Explore [Agent Reference](agents.md) to understand each agent's role
- Check [Configuration](configuration.md) for fine-tuning options

### Customize Your Setup

- Create custom workflows in `templates/workflows.yaml`
- Adjust agent behavior in `config/agents.yaml`
- Modify content tone in `config/tone.json`
- Add custom templates in `templates/`

### Explore Advanced Features

- **Parallel Execution**: Speed up generation with concurrent agents
- **Checkpointing**: Resume failed jobs from any point
- **Hot Reload**: Update workflows without restart
- **MCP Integration**: Use agents in external tools
- **Real-Time Monitoring**: Track jobs via WebSocket

### Common Use Cases

1. **Bulk Content Generation**: Process hundreds of KB articles
2. **SEO Optimization**: Enhance existing content with keywords
3. **Code Documentation**: Generate tutorials from API docs
4. **Content Translation**: Adapt content for different audiences
5. **Quality Assurance**: Validate content before publishing

### Getting Help

- **Troubleshooting**: See [troubleshooting.md](troubleshooting.md) for common issues
- **Performance**: Read [performance.md](performance.md) for optimization tips
- **Examples**: Check the `examples/` directory for more samples
- **CLI Reference**: Run `python ucop_cli.py --help` for command details

## Quick Reference Commands

```bash
# Generate single article
python ucop_cli.py generate --input <file> --output <dir>

# Process batch
python ucop_cli.py batch --manifest <json>

# List workflows
python ucop_cli.py viz workflows

# Monitor jobs
python ucop_cli.py job list

# Get job status
python ucop_cli.py job get <job_id>

# Pause/resume job
python ucop_cli.py job pause <job_id>
python ucop_cli.py job resume <job_id>

# List available agents
python ucop_cli.py agent list

# Test single agent
python ucop_cli.py agent invoke <agent_id> --input <json>

# Start web UI
python start_web.py
```

## Environment Setup Examples

### Development Environment

```bash
# .env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b
LOG_LEVEL=DEBUG
ENABLE_HOT_RELOAD=true
CHECKPOINT_ENABLED=true
```

### Production Environment

```bash
# .env
GEMINI_API_KEY=production_key_here
OPENAI_API_KEY=fallback_key_here
LOG_LEVEL=INFO
ENABLE_PARALLEL_EXECUTION=true
MAX_PARALLEL_AGENTS=10
CHECKPOINT_ENABLED=true
ENABLE_MONITORING=true
```

### Testing Environment

```bash
# .env.test
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=phi4:14b
LOG_LEVEL=WARNING
DETERMINISTIC=true
GLOBAL_SEED=42
```

## Troubleshooting Installation

### Python Version Issues

```bash
# Check Python version
python --version

# If < 3.8, install newer Python
# Windows: Download from https://python.org
# Mac: brew install python@3.11
# Linux: sudo apt install python3.11
```

### Virtual Environment Issues

```bash
# Remove and recreate
rm -rf venv
python -m venv venv

# Windows activation issues
# Try: venv\Scripts\activate.ps1 (PowerShell)
# Or: venv\Scripts\activate.bat (CMD)
```

### Dependency Installation Failures

```bash
# Upgrade pip first
pip install --upgrade pip

# Install with verbose output
pip install -r requirements.txt -v

# Install optional dependencies separately
pip install torch torchvision  # GPU support
pip install sentence-transformers  # Embeddings
```

### Ollama Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
# Mac: Ollama app should be in Applications
# Linux: systemctl start ollama
# Windows: Run Ollama from Start menu

# Verify model is pulled
ollama list
ollama pull qwen2.5:14b
```

For more troubleshooting, see [troubleshooting.md](troubleshooting.md).
