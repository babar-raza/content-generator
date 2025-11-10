#!/bin/bash
set -e

echo "🚀 UCOP Setup Script"
echo "===================="

# Check Python version
echo ""
echo "Checking Python version..."
python3 --version || { echo "Python 3.8+ required"; exit 1; }

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p reports
mkdir -p output
mkdir -p logs

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️  Please edit .env with your API keys"
    else
        cat > .env << 'EOFENV'
# LLM Provider API Keys
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# GitHub (for Gist uploads)
GITHUB_TOKEN=your_github_token_here

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b

# System Configuration
LOG_LEVEL=INFO
ENABLE_GPU=auto
MAX_WORKERS=5
EOFENV
        echo "✓ Created .env file - please edit with your API keys"
    fi
fi

# Check Ollama installation
echo ""
echo "Checking Ollama..."
if command -v ollama &> /dev/null; then
    echo "✓ Ollama is installed"
    echo "  Testing Ollama connection..."
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "  ✓ Ollama server is running"
    else
        echo "  ⚠️  Ollama server is not running"
        echo "  Start it with: ollama serve"
    fi
else
    echo "⚠️  Ollama not found"
    echo "   Install from: https://ollama.ai"
fi

# Run validation
echo ""
echo "Running system validation..."
if python tools/validate_imports.py; then
    echo "✓ Import validation passed"
else
    echo "⚠️  Some imports failed - check logs"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Start Ollama if not running: ollama serve"
echo "  3. Pull Ollama model: ollama pull qwen2.5:14b"
echo "  4. Run CLI: python ucop_cli.py --help"
echo "  5. Start Web UI: python start_web.py"
echo ""
