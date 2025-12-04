#!/bin/bash

# Hook: Prevent files from being created at repository root
# This keeps the repository root clean and organized

# Exit codes:
# 0 - Success (no violations)
# 1 - Fatal error
# 2 - Violations found (sends feedback to Claude)

set -e

# Get list of modified AND untracked files from git
# Use git status --porcelain to catch ALL changes including untracked files
MODIFIED_FILES=$(git status --porcelain 2>/dev/null | grep -E '^\?\?|^[AM]' | awk '{print $2}' || echo "")

# Also check recent untracked files at root
UNTRACKED_ROOT=$(git ls-files --others --exclude-standard 2>/dev/null | grep -v '/' || echo "")

# Combine both lists
ALL_FILES="$MODIFIED_FILES"$'\n'"$UNTRACKED_ROOT"

if [ -z "$ALL_FILES" ] || [ "$ALL_FILES" = $'\n' ]; then
    # No files to check
    exit 0
fi

# Check for new .md or .txt files at root level (except README.md)
VIOLATIONS=""

for file in $ALL_FILES; do
    # Skip empty lines
    if [ -z "$file" ]; then
        continue
    fi

    # Check if file is at root level (no directory separators)
    if [[ ! "$file" =~ / ]]; then
        # Check if it's a .md or .txt file
        if [[ "$file" =~ \.(md|txt)$ ]] && [ "$file" != "README.md" ]; then
            VIOLATIONS="$VIOLATIONS\n  - $file"
        fi
    fi
done

if [ -n "$VIOLATIONS" ]; then
    echo "❌ ROOT-LEVEL FILE VIOLATIONS DETECTED"
    echo ""
    echo "The following files violate the clean root policy:"
    echo -e "$VIOLATIONS"
    echo ""
    echo "📁 CORRECT LOCATIONS:"
    echo "  - Reports/Analysis → reports/"
    echo "  - User Documentation → docs/"
    echo "  - Developer Documentation → development/"
    echo "  - Task Plans → plans/"
    echo ""
    echo "🔧 ACTION REQUIRED:"
    echo "  Move these files to the appropriate directory."
    echo "  See .claude/rules.md Section 1.1.2 for details."
    echo ""
    exit 2
fi

# Success - no violations
exit 0
