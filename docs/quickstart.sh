#!/bin/bash
# Quick Start Guide for UCOP

echo "=========================================="
echo "UCOP - Quick Start Guide"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✓ Python found: $(python3 --version)"
echo ""

# Check if in correct directory
if [ ! -f "start_web_ui.py" ]; then
    echo "❌ Error: Must run from UCOP root directory"
    exit 1
fi

echo "📦 Step 1: Installing dependencies..."
echo "----------------------------------------"
pip install -r requirements.txt --quiet
if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed"
else
    echo "⚠ Some dependencies may have failed. Check output above."
fi
echo ""

echo "🚀 Step 2: Starting web server..."
echo "----------------------------------------"
echo "Server will start on http://localhost:8080"
echo ""
echo "Available interfaces:"
echo "  • Web Dashboard: http://localhost:8080"
echo "  • API Docs: http://localhost:8080/docs"
echo "  • Health Check: http://localhost:8080/health"
echo ""
echo "CLI Usage (in another terminal):"
echo "  • List jobs: python ucop_cli.py list"
echo "  • Create job: python ucop_cli.py create workflow_name --params '{\"key\":\"value\"}'"
echo "  • Watch job: python ucop_cli.py watch <job-id>"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

python3 start_web_ui.py
