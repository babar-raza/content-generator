#!/bin/bash

# Hook: Auto-format modified Python files with black
# Ensures consistent code formatting

# Exit codes:
# 0 - Success (files formatted)
# 1 - Fatal error

set -e

# Get list of modified AND untracked Python files
# Use git status --porcelain to catch ALL changes including untracked files
ALL_FILES=$(git status --porcelain 2>/dev/null | grep -E '^\?\?|^[AM]' | awk '{print $2}' || echo "")
MODIFIED_FILES=$(echo "$ALL_FILES" | grep '\.py$' || echo "")

if [ -z "$MODIFIED_FILES" ]; then
    # No Python files modified
    exit 0
fi

echo "✓ Auto-formatting modified Python files with black..."

# Format each file
for file in $MODIFIED_FILES; do
    if [ -f "$file" ]; then
        python -m black "$file" 2>&1 | grep -v "would reformat\|reformatted" || true
    fi
done

echo "✓ Formatting complete"

# Success
exit 0
