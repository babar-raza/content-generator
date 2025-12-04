#!/bin/bash

# Hook: Verify DOCGEN documentation coverage for modified Python files
# Ensures 100% docstring coverage

# Exit codes:
# 0 - Success (100% coverage)
# 1 - Fatal error
# 2 - Missing documentation (sends feedback to Claude)

set -e

# Get list of modified AND untracked Python files
# Use git status --porcelain to catch ALL changes including untracked files
ALL_FILES=$(git status --porcelain 2>/dev/null | grep -E '^\?\?|^[AM]' | awk '{print $2}' || echo "")
MODIFIED_FILES=$(echo "$ALL_FILES" | grep '\.py$' || echo "")

if [ -z "$MODIFIED_FILES" ]; then
    # No Python files modified
    exit 0
fi

MISSING_DOCS=""

for file in $MODIFIED_FILES; do
    # Skip test files
    if [[ "$file" =~ ^tests/ ]] || [[ "$file" =~ test_.*\.py$ ]]; then
        continue
    fi

    # Skip if file doesn't exist (might be deleted)
    if [ ! -f "$file" ]; then
        continue
    fi

    # Basic check for module docstring (first non-comment line should be docstring)
    if ! grep -q '"""' "$file" 2>/dev/null; then
        MISSING_DOCS="$MISSING_DOCS\n  - $file: Missing module docstring"
    fi

    # Check for function/class definitions without docstrings
    # This is a basic check - full validation would require AST parsing
    if grep -E '^\s*def ' "$file" | head -5 | while read -r line; do
        # Get the function name
        func_name=$(echo "$line" | sed 's/.*def \([^(]*\).*/\1/')

        # Check if next non-empty line after function def has docstring
        if ! awk "/def $func_name/,/\"\"\"/" "$file" | grep -q '"""' 2>/dev/null; then
            echo "$file: Function $func_name missing docstring"
        fi
    done | grep -q "missing docstring"; then
        MISSING_DOCS="$MISSING_DOCS\n  - $file: Functions missing docstrings"
    fi
done

if [ -n "$MISSING_DOCS" ]; then
    echo "⚠ MISSING DOCUMENTATION DETECTED"
    echo ""
    echo "The following files have incomplete DOCGEN documentation:"
    echo -e "$MISSING_DOCS"
    echo ""
    echo "📋 REQUIREMENTS:"
    echo "  - Module-level docstring"
    echo "  - Class docstrings with attributes"
    echo "  - Function/method docstrings with Args, Returns, Raises"
    echo "  - Use Google-style docstring format"
    echo ""
    echo "🔧 ACTION REQUIRED:"
    echo "  Add complete docstrings to all Python files."
    echo "  See .claude/rules.md Section 1.4 for DOCGEN requirements."
    echo ""
    exit 2
fi

# Success
exit 0
