#!/bin/bash

# Hook: Prevent documentation sprawl by enforcing consolidation
# Detects potentially duplicate or overlapping documentation

# Exit codes:
# 0 - Success (no sprawl detected)
# 1 - Fatal error
# 2 - Potential sprawl (sends feedback to Claude)

set -e

# Get list of modified AND untracked markdown files
# Use git status --porcelain to catch ALL changes including untracked files
ALL_FILES=$(git status --porcelain 2>/dev/null | grep -E '^\?\?|^[AM]' | awk '{print $2}' || echo "")
NEW_FILES=$(echo "$ALL_FILES" | grep '\.md$' || echo "")

if [ -z "$NEW_FILES" ]; then
    # No new markdown files
    exit 0
fi

POTENTIAL_DUPLICATES=""

for new_file in $NEW_FILES; do
    # Skip if file already exists (modification, not creation)
    if git ls-files --error-unmatch "$new_file" >/dev/null 2>&1; then
        continue
    fi

    # Skip README files
    if [[ "$new_file" =~ README\.md$ ]]; then
        continue
    fi

    # Extract key terms from filename
    BASENAME=$(basename "$new_file" .md | tr '_' ' ' | tr '-' ' ' | tr '[:upper:]' '[:lower:]')

    # Search for similar files in the same directory
    DIR=$(dirname "$new_file")

    # Look for files with similar names
    if [ -d "$DIR" ]; then
        for existing_file in "$DIR"/*.md; do
            if [ -f "$existing_file" ] && [ "$existing_file" != "$new_file" ]; then
                EXISTING_BASENAME=$(basename "$existing_file" .md | tr '_' ' ' | tr '-' ' ' | tr '[:upper:]' '[:lower:]')

                # Check for common words (crude similarity check)
                COMMON_WORDS=$(comm -12 <(echo "$BASENAME" | tr ' ' '\n' | sort) <(echo "$EXISTING_BASENAME" | tr ' ' '\n' | sort) | wc -l)

                if [ "$COMMON_WORDS" -ge 2 ]; then
                    POTENTIAL_DUPLICATES="$POTENTIAL_DUPLICATES\n  ⚠ New: $new_file"
                    POTENTIAL_DUPLICATES="$POTENTIAL_DUPLICATES\n     Similar to: $existing_file"
                    POTENTIAL_DUPLICATES="$POTENTIAL_DUPLICATES\n     Consider: Consolidating into existing file"
                fi
            fi
        done
    fi
done

if [ -n "$POTENTIAL_DUPLICATES" ]; then
    echo "⚠ POTENTIAL DOCUMENTATION SPRAWL DETECTED"
    echo ""
    echo "The following new files may duplicate existing documentation:"
    echo -e "$POTENTIAL_DUPLICATES"
    echo ""
    echo "📋 CONSOLIDATION GUIDELINES:"
    echo "  - Search existing docs before creating new files"
    echo "  - Update existing files instead of creating duplicates"
    echo "  - Use sections within files for related topics"
    echo "  - Only create new files for truly distinct topics"
    echo ""
    echo "🔍 VERIFY:"
    echo "  1. Is this information already documented elsewhere?"
    echo "  2. Can this be added as a section to an existing file?"
    echo "  3. Is a new file truly necessary?"
    echo ""
    echo "See .claude/rules.md Section 1.3.4 for consolidation rules."
    echo ""
    exit 2
fi

# Success
exit 0
