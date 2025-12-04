#!/bin/bash

# Hook: Check if tests exist and run them for modified Python files
# Ensures test coverage for all code changes

# Exit codes:
# 0 - Success (tests exist and pass)
# 1 - Fatal error
# 2 - Tests missing or failing (sends feedback to Claude)

set -e

# Get list of modified AND untracked Python files
# Use git status --porcelain to catch ALL changes including untracked files
ALL_FILES=$(git status --porcelain 2>/dev/null | grep -E '^\?\?|^[AM]' | awk '{print $2}' || echo "")
MODIFIED_FILES=$(echo "$ALL_FILES" | grep '\.py$' || echo "")

if [ -z "$MODIFIED_FILES" ]; then
    # No Python files modified
    exit 0
fi

MISSING_TESTS=""
FAILED_TESTS=""

for file in $MODIFIED_FILES; do
    # Skip test files themselves
    if [[ "$file" =~ ^tests/ ]] || [[ "$file" =~ test_.*\.py$ ]]; then
        continue
    fi

    # Skip __init__.py files
    if [[ "$file" =~ __init__\.py$ ]]; then
        continue
    fi

    # Determine expected test file path
    # Convert src/module/file.py to tests/unit/module/test_file.py
    TEST_FILE=$(echo "$file" | sed 's|^src/||' | sed 's|\.py$||' | sed 's|/|/test_|g' | sed 's|^|tests/unit/test_|')".py"

    # Check if test file exists
    if [ ! -f "$TEST_FILE" ]; then
        # Also check tests/integration/
        INT_TEST_FILE=$(echo "$TEST_FILE" | sed 's|tests/unit/|tests/integration/|')
        if [ ! -f "$INT_TEST_FILE" ]; then
            MISSING_TESTS="$MISSING_TESTS\n  - $file → Expected: $TEST_FILE"
        fi
    fi
done

# Run pytest on modified files if tests exist
if [ -z "$MISSING_TESTS" ]; then
    echo "✓ Running tests for modified Python files..."

    # Run pytest with relevant test paths
    if ! python -m pytest tests/ -v --tb=short 2>&1 | head -50; then
        FAILED_TESTS="Tests failed for modified files"
    fi
fi

if [ -n "$MISSING_TESTS" ]; then
    echo "⚠ MISSING TESTS DETECTED"
    echo ""
    echo "The following files have no corresponding tests:"
    echo -e "$MISSING_TESTS"
    echo ""
    echo "🔧 ACTION REQUIRED:"
    echo "  Create test files for these modules."
    echo "  See .claude/rules.md Section 3 for testing requirements."
    echo ""
    exit 2
fi

if [ -n "$FAILED_TESTS" ]; then
    echo "❌ TEST FAILURES DETECTED"
    echo ""
    echo "Tests failed for modified files."
    echo "Please fix failing tests before continuing."
    echo ""
    exit 2
fi

# Success
exit 0
