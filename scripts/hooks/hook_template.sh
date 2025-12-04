#!/bin/bash

# Hook: [Brief description of what this hook checks]
# [Extended description with more details about the hook's purpose]

# Exit codes:
# 0 - Success (no violations)
# 1 - Fatal error (unexpected failure)
# 2 - Violations found (sends feedback to Claude for correction)

# Enable strict error handling
set -e

# ============================================================================
# CONFIGURATION
# ============================================================================

# Get list of modified AND untracked files
# CRITICAL: Use git status --porcelain to catch ALL changes including untracked files
# This ensures hooks work correctly for both tracked and untracked files
ALL_FILES=$(git status --porcelain 2>/dev/null | grep -E '^\?\?|^[AM]' | awk '{print $2}' || echo "")
MODIFIED_FILES="$ALL_FILES"

# Define file patterns to check (adjust for your hook)
FILE_PATTERN="\.py$"  # Example: Python files
# FILE_PATTERN="\.md$"  # Example: Markdown files
# FILE_PATTERN="src/web/routes/.*\.py$"  # Example: Specific directory

# Filter modified files by pattern
RELEVANT_FILES=$(echo "$MODIFIED_FILES" | grep -E "$FILE_PATTERN" || echo "")

# ============================================================================
# EARLY EXIT
# ============================================================================

# Exit early if no relevant files modified
if [ -z "$RELEVANT_FILES" ]; then
    # No files to check - success
    exit 0
fi

# ============================================================================
# VALIDATION LOGIC
# ============================================================================

echo "✓ Checking [description] for modified files..."

VIOLATIONS=""
VIOLATION_COUNT=0

for file in $RELEVANT_FILES; do
    # Skip files that don't exist (may be deleted)
    if [ ! -f "$file" ]; then
        continue
    fi

    # Skip specific files if needed
    # Example: Skip test files
    if [[ "$file" =~ ^tests/ ]] || [[ "$file" =~ test_.*\.py$ ]]; then
        continue
    fi

    # Skip __init__.py files (example)
    if [[ "$file" =~ __init__\.py$ ]]; then
        continue
    fi

    echo "  Checking: $file"

    # ========================================================================
    # CHECK 1: [Description of first check]
    # ========================================================================
    if ! grep -q "expected_pattern" "$file" 2>/dev/null; then
        VIOLATIONS="$VIOLATIONS\n  - $file: [Description of violation]"
        VIOLATION_COUNT=$((VIOLATION_COUNT + 1))
    fi

    # ========================================================================
    # CHECK 2: [Description of second check]
    # ========================================================================
    if grep -q "anti_pattern" "$file" 2>/dev/null; then
        VIOLATIONS="$VIOLATIONS\n  - $file: [Description of violation]"
        VIOLATION_COUNT=$((VIOLATION_COUNT + 1))
    fi

    # ========================================================================
    # CHECK 3: [Add more checks as needed]
    # ========================================================================
    # Add additional validation logic here

done

# ============================================================================
# REPORT VIOLATIONS
# ============================================================================

if [ -n "$VIOLATIONS" ]; then
    echo ""
    echo "❌ [VIOLATION TYPE] DETECTED"
    echo ""
    echo "The following violations were found:"
    echo -e "$VIOLATIONS"
    echo ""
    echo "📋 REQUIREMENTS:"
    echo "  - [Requirement 1]"
    echo "  - [Requirement 2]"
    echo "  - [Requirement 3]"
    echo ""
    echo "🔧 ACTION REQUIRED:"
    echo "  [Description of what needs to be done to fix violations]"
    echo "  See .claude/rules.md Section [X] for details."
    echo ""
    echo "📊 SUMMARY:"
    echo "  Violations found: $VIOLATION_COUNT"
    echo ""

    # Exit with code 2 to send feedback to Claude
    exit 2
fi

# ============================================================================
# SUCCESS EXIT
# ============================================================================

echo "✅ All checks passed"
exit 0

# ============================================================================
# PATTERN NOTES
# ============================================================================
#
# EXIT CODE USAGE:
#   exit 0  - Success, no violations found
#   exit 1  - Fatal error (use for unexpected failures only)
#   exit 2  - Violations found, sends feedback to Claude
#
# BEST PRACTICES:
#   1. Always use 'set -e' for error handling
#   2. Always document exit codes at the top
#   3. Use descriptive violation messages
#   4. Provide actionable feedback
#   5. Exit early if no relevant files
#   6. Handle file existence checks
#   7. Use consistent output format
#   8. Keep checks focused and single-purpose
#
# COMMON PATTERNS:
#   - Use VIOLATIONS variable to accumulate messages
#   - Use VIOLATION_COUNT to track number of issues
#   - Check file existence before processing
#   - Skip irrelevant files early
#   - Provide clear, actionable error messages
#   - Reference relevant rules documentation
#
# TESTING:
#   Run hook manually: bash scripts/hooks/your_hook.sh
#   Check exit code: echo $?
#   Verify output format
#   Test with no relevant files
#   Test with violations
#   Test with clean files
#
# ============================================================================
