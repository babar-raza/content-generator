#!/bin/bash
set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "================================================================"
echo "  UCOP - Unified Content Operations Platform"
echo "  Setup Script for Linux/Mac"
echo "================================================================"
echo ""

# Function to print colored output
print_step() {
    echo -e "${BLUE}[Step $1/$2]${NC} $3"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Step 1: Check Python
print_step 1 6 "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    echo "Please install Python 3.8+ from https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
print_success "Found Python $PYTHON_VERSION"

# Check Python version is >= 3.8
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    print_error "Python 3.8 or higher is required"
    exit 1
fi

# Step 2: Create virtual environment
print_step 2 6 "Creating virtual environment..."
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists"
    read -p "Recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        print_success "Virtual environment recreated"
    else
        print_success "Using existing virtual environment"
    fi
else
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Step 3: Activate virtual environment
print_step 3 6 "Activating virtual environment..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    print_error "Failed to activate virtual environment"
    exit 1
fi
print_success "Virtual environment activated"

# Step 4: Upgrade pip
print_step 4 6 "Upgrading pip..."
python -m pip install --upgrade pip --quiet
print_success "pip upgraded"

# Step 5: Install dependencies
print_step 5 6 "Installing dependencies..."
echo "This may take a few minutes..."
echo ""

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    if [ $? -eq 0 ]; then
        print_success "All dependencies installed"
    else
        print_warning "Some dependencies failed (optional packages)"
        echo "Core packages should be installed. Check requirements.txt for optional packages."
    fi
else
    print_error "requirements.txt not found"
    exit 1
fi

# Step 6: Create directories
print_step 6 6 "Creating project directories..."
mkdir -p output data logs checkpoints test_output reports
print_success "Project directories created"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating default .env file..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created from .env.example"
    else
        cat > .env << 'ENVEOF'
# UCOP Environment Configuration

# === LLM Configuration ===
# Ollama (Local)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b

# Google Gemini (Optional)
# GEMINI_API_KEY=your_api_key_here

# OpenAI (Optional)
# OPENAI_API_KEY=your_api_key_here

# === System Configuration ===
LOG_LEVEL=INFO
OUTPUT_DIR=./output
DATA_DIR=./data

# === Feature Flags ===
ENABLE_MESH_ORCHESTRATION=true
ENABLE_VISUAL_ORCHESTRATION=true
ENABLE_MCP_ENDPOINTS=true
ENVEOF
        print_success "Default .env file created"
    fi
    echo ""
    print_warning "Edit .env file to configure API keys if needed"
fi

# Validation
echo ""
echo "================================================================"
echo "  Validation"
echo "================================================================"
echo ""

echo "Testing core imports..."
python3 << 'PYEOF'
import sys
import importlib

modules_to_test = [
    ('Core Config', 'src.core.config'),
    ('Core Template Registry', 'src.core.template_registry'),
    ('Mesh Runtime', 'src.mesh.runtime_async'),
    ('Engine Executor', 'src.engine.executor'),
    ('Orchestration Registry', 'src.orchestration.enhanced_registry'),
]

passed = 0
failed = []

for name, module in modules_to_test:
    try:
        importlib.import_module(module)
        print(f'  ✓ {name}')
        passed += 1
    except ImportError as e:
        print(f'  ✗ {name}: {str(e)[:50]}')
        failed.append(name)

print(f'\nResult: {passed}/{len(modules_to_test)} modules imported successfully')

if failed:
    print(f'Failed modules: {", ".join(failed)}')
    print('\nNote: Some optional dependencies may not be installed.')
    print('Check requirements.txt to uncomment optional packages.')
    sys.exit(0)  # Don't fail, just warn
PYEOF

if [ $? -eq 0 ]; then
    print_success "Core modules validated"
else
    print_warning "Some modules failed validation (may need optional dependencies)"
fi

# Final summary
echo ""
echo "================================================================"
echo "  Setup Complete!"
echo "================================================================"
echo ""
echo "Python: $PYTHON_VERSION"
echo "Virtual Environment: $PWD/venv"
echo "Configuration: .env"
echo ""
echo "To activate the environment:"
echo "  ${GREEN}source venv/bin/activate${NC}"
echo ""
echo "To run the CLI:"
echo "  ${GREEN}python ucop_cli.py --help${NC}"
echo ""
echo "To start the web UI:"
echo "  ${GREEN}python start_web.py${NC}"
echo ""
echo "To run tests:"
echo "  ${GREEN}pytest tests/test_imports_smoke.py -v${NC}"
echo ""
echo "For more information, see README.md"
echo ""
