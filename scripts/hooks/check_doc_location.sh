#!/bin/bash

# Hook: Verify documentation files are in correct locations
# Enforces separation between system docs (docs/) and development docs (development/)

# Exit codes:
# 0 - Success (all docs in correct location)
# 1 - Fatal error
# 2 - Misplaced docs (sends feedback to Claude)

set -e

# Get list of modified AND untracked markdown files
# Use git status --porcelain to catch ALL changes including untracked files
ALL_FILES=$(git status --porcelain 2>/dev/null | grep -E '^\?\?|^[AM]' | awk '{print $2}' || echo "")
MODIFIED_FILES=$(echo "$ALL_FILES" | grep '\.md$' || echo "")

if [ -z "$MODIFIED_FILES" ]; then
    # No markdown files modified
    exit 0
fi

MISPLACED_DOCS=""

# Keywords that indicate development documentation
DEV_KEYWORDS="architecture|internal|implementation|design pattern|code structure|development|developer|maintainer|contributor|how to add|how to create|extending|modifying|codebase"

# Keywords that indicate system documentation
SYS_KEYWORDS="user guide|how to use|api reference|tutorial|getting started|deployment|troubleshooting|configuration|operator|administrator"

for file in $MODIFIED_FILES; do
    # Skip README files
    if [[ "$file" =~ README\.md$ ]]; then
        continue
    fi

    # Skip files not in docs/ or development/
    if [[ ! "$file" =~ ^docs/ ]] && [[ ! "$file" =~ ^development/ ]]; then
        continue
    fi

    # Skip if file doesn't exist (might be deleted)
    if [ ! -f "$file" ]; then
        continue
    fi

    # Get file content (first 100 lines should be enough for classification)
    CONTENT=$(head -100 "$file" | tr '[:upper:]' '[:lower:]')

    # Check if file appears to be development documentation but is in docs/
    if [[ "$file" =~ ^docs/ ]] && echo "$CONTENT" | grep -E "$DEV_KEYWORDS" >/dev/null 2>&1; then
        MISPLACED_DOCS="$MISPLACED_DOCS\n  ⚠ $file"
        MISPLACED_DOCS="$MISPLACED_DOCS\n     This appears to be DEVELOPMENT documentation but is in docs/"
        MISPLACED_DOCS="$MISPLACED_DOCS\n     Should be in: development/"
    fi

    # Check if file appears to be system documentation but is in development/
    if [[ "$file" =~ ^development/ ]] && echo "$CONTENT" | grep -E "$SYS_KEYWORDS" >/dev/null 2>&1; then
        MISPLACED_DOCS="$MISPLACED_DOCS\n  ⚠ $file"
        MISPLACED_DOCS="$MISPLACED_DOCS\n     This appears to be SYSTEM documentation but is in development/"
        MISPLACED_DOCS="$MISPLACED_DOCS\n     Should be in: docs/"
    fi
done

if [ -n "$MISPLACED_DOCS" ]; then
    echo "⚠ MISPLACED DOCUMENTATION DETECTED"
    echo ""
    echo "The following documentation files may be in the wrong location:"
    echo -e "$MISPLACED_DOCS"
    echo ""
    echo "📋 DOCUMENTATION STRUCTURE:"
    echo "  docs/        → System documentation (users, operators)"
    echo "  development/ → Development documentation (developers)"
    echo ""
    echo "🔧 ACTION REQUIRED:"
    echo "  Review and move files to the correct location."
    echo "  See .claude/DOCUMENTATION_STRUCTURE.md for details."
    echo ""
    exit 2
fi

# Success
exit 0
