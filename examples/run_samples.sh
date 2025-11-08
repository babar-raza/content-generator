#!/bin/bash
# Sample Run Script - Demonstrates all features

echo "========================================="
echo "UCOP CLI - Sample Runs"
echo "========================================="

# 1. Validate configuration
echo -e "\n1. Validating configuration..."
python ucop_unified_cli.py validate

# 2. List available templates
echo -e "\n2. Listing available templates..."
python ucop_unified_cli.py list-templates

# 3. Simple generation
echo -e "\n3. Simple generation with topic..."
python ucop_unified_cli.py generate \
  --template default_blog \
  --topic "Introduction to Python" \
  --output-dir ./output/example1

# 4. Generation with context (RAG)
echo -e "\n4. Generation with knowledge base..."
# Create sample KB
mkdir -p ./examples/sample_kb
echo "# Python is a high-level programming language" > ./examples/sample_kb/python.md

python ucop_unified_cli.py generate \
  --template default_blog \
  --topic "Python Basics" \
  --kb ./examples/sample_kb \
  --output-dir ./output/example2

# 5. Auto-topic generation
echo -e "\n5. Auto-topic from context..."
python ucop_unified_cli.py generate \
  --template default_blog \
  --auto-topic \
  --kb ./examples/sample_kb \
  --output-dir ./output/example3

# 6. Batch generation
echo -e "\n6. Batch generation..."
python ucop_unified_cli.py batch \
  --template default_blog \
  --topics-file ./examples/sample_topics.txt \
  --output-dir ./output/batch

# 7. Different template type
echo -e "\n7. Tutorial template..."
python ucop_unified_cli.py generate \
  --template tutorial_blog \
  --topic "Step-by-Step Python Setup" \
  --output-dir ./output/example4

# 8. Verbose output
echo -e "\n8. Verbose generation..."
python ucop_unified_cli.py generate \
  --template default_blog \
  --topic "Python Advanced Topics" \
  --output-dir ./output/example5 \
  --verbose

echo -e "\n========================================="
echo "All examples completed!"
echo "Check ./output/ directory for results"
echo "========================================="
