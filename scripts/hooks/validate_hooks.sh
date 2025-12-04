#!/bin/bash

# Hook: Validate all hook scripts follow correct patterns
# This is a meta-hook that ensures hook quality and consistency

# Exit codes:
# 0 - Success (all hooks valid)
# 1 - Fatal error
# 2 - Invalid hooks found (sends feedback to Claude)

set -e

HOOKS_DIR="scripts/hooks"
VIOLATIONS=""
WARNING_COUNT=0
ERROR_COUNT=0

echo "🔍 Validating hook scripts..."

# Skip validation and template files
SKIP_FILES="validate_hooks.sh|hook_template.sh|README.md"

# Get all .sh files in hooks directory
for hook_file in "$HOOKS_DIR"/*.sh; do
    # Skip if file doesn't exist (glob didn't match)
    if [ ! -f "$hook_file" ]; then
        continue
    fi

    BASENAME=$(basename "$hook_file")

    # Skip validation and template files
    if echo "$BASENAME" | grep -E "$SKIP_FILES" >/dev/null 2>&1; then
        continue
    fi

    echo "  Checking: $BASENAME"

    # Check 1: Shebang must be present
    if ! head -1 "$hook_file" | grep -q "^#!/bin/bash"; then
        VIOLATIONS="$VIOLATIONS\n  ❌ $BASENAME: Missing or incorrect shebang (#!/bin/bash)"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi

    # Check 2: Must document exit codes
    if ! grep -q "# Exit codes:" "$hook_file"; then
        VIOLATIONS="$VIOLATIONS\n  ⚠ $BASENAME: Missing exit code documentation comment"
        WARNING_COUNT=$((WARNING_COUNT + 1))
    fi

    # Check 3: Must have 'set -e' for error handling
    if ! grep -q "^set -e" "$hook_file"; then
        VIOLATIONS="$VIOLATIONS\n  ⚠ $BASENAME: Missing 'set -e' error handling"
        WARNING_COUNT=$((WARNING_COUNT + 1))
    fi

    # Check 4: Must use only valid exit codes (0, 1, 2)
    INVALID_EXITS=$(grep -E "exit [0-9]+" "$hook_file" | grep -Ev "exit [012]([^0-9]|$)" || true)
    if [ -n "$INVALID_EXITS" ]; then
        VIOLATIONS="$VIOLATIONS\n  ❌ $BASENAME: Uses invalid exit codes (only 0, 1, 2 allowed)"
        VIOLATIONS="$VIOLATIONS\n     Found: $(echo "$INVALID_EXITS" | tr '\n' ' ')"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi

    # Check 5: Must have at least one exit statement
    if ! grep -q "^exit" "$hook_file"; then
        VIOLATIONS="$VIOLATIONS\n  ❌ $BASENAME: No explicit exit statement found"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi

    # Check 6: Should document what it checks
    if ! grep -q "# Hook:" "$hook_file"; then
        VIOLATIONS="$VIOLATIONS\n  ⚠ $BASENAME: Missing '# Hook:' description comment"
        WARNING_COUNT=$((WARNING_COUNT + 1))
    fi

    # Check 7: Check for common mistakes

    # Using exit without explicit code
    if grep -E "^exit$" "$hook_file" >/dev/null 2>&1; then
        VIOLATIONS="$VIOLATIONS\n  ⚠ $BASENAME: Uses 'exit' without explicit code (use 'exit 0')"
        WARNING_COUNT=$((WARNING_COUNT + 1))
    fi

    # Using exit in conditionals without proper handling
    if grep -E "exit [0-9]+" "$hook_file" | grep -v "^exit" >/dev/null 2>&1; then
        # Check if it's in a proper conditional block
        CONDITIONAL_EXITS=$(grep -B1 -E "exit [0-9]+" "$hook_file" | grep -E "if|then|else|fi" || true)
        if [ -z "$CONDITIONAL_EXITS" ]; then
            VIOLATIONS="$VIOLATIONS\n  ⚠ $BASENAME: Exit statements should be at line start or in conditionals"
            WARNING_COUNT=$((WARNING_COUNT + 1))
        fi
    fi

    # Check 8: Must have success exit (exit 0)
    if ! grep -q "exit 0" "$hook_file"; then
        VIOLATIONS="$VIOLATIONS\n  ⚠ $BASENAME: Missing success exit code (exit 0)"
        WARNING_COUNT=$((WARNING_COUNT + 1))
    fi

    # Check 9: Should have feedback exit (exit 2)
    if ! grep -q "exit 2" "$hook_file"; then
        VIOLATIONS="$VIOLATIONS\n  💡 $BASENAME: Consider adding feedback exit (exit 2) for violations"
        # Don't increment count for suggestions
    fi

    # Check 10: File must be executable
    if [ ! -x "$hook_file" ]; then
        VIOLATIONS="$VIOLATIONS\n  ❌ $BASENAME: File is not executable (run: chmod +x $hook_file)"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi
done

# Report results
echo ""
if [ -n "$VIOLATIONS" ]; then
    echo "❌ HOOK VALIDATION FAILED"
    echo ""
    echo "The following hook pattern violations were detected:"
    echo -e "$VIOLATIONS"
    echo ""
    echo "📋 REQUIRED HOOK PATTERN:"
    echo "  1. #!/bin/bash shebang (first line)"
    echo "  2. # Hook: <description> comment"
    echo "  3. # Exit codes: documentation"
    echo "  4. set -e (error handling)"
    echo "  5. Only exit codes 0, 1, 2"
    echo "  6. Explicit exit statements"
    echo "  7. File must be executable"
    echo ""
    echo "📊 SUMMARY:"
    echo "  Errors: $ERROR_COUNT"
    echo "  Warnings: $WARNING_COUNT"
    echo ""
    echo "🔧 ACTION REQUIRED:"
    echo "  Fix hook pattern violations."
    echo "  See scripts/hooks/hook_template.sh for correct pattern."
    echo "  See .claude/rules.md for hook requirements."
    echo ""

    # Exit with code 2 if any errors found
    if [ "$ERROR_COUNT" -gt 0 ]; then
        exit 2
    fi

    # Exit with code 0 for warnings only (don't block)
    exit 0
fi

# Success - all hooks valid
echo "✅ All hook scripts follow correct patterns"
exit 0
