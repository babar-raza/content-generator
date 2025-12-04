#!/bin/bash

# Hook: Enforce auto-generated OpenAPI/Swagger documentation
# Ensures all API endpoints have proper documentation

# Exit codes:
# 0 - Success (API docs look good)
# 1 - Fatal error
# 2 - Missing API documentation (sends feedback to Claude)

set -e

# Get list of modified AND untracked Python files in web/routes
# Use git status --porcelain to catch ALL changes including untracked files
ALL_FILES=$(git status --porcelain 2>/dev/null | grep -E '^\?\?|^[AM]' | awk '{print $2}' || echo "")
MODIFIED_ROUTES=$(echo "$ALL_FILES" | grep 'src/web/routes/.*\.py$' || echo "")

if [ -z "$MODIFIED_ROUTES" ]; then
    # No route files modified
    exit 0
fi

MISSING_DOCS=""

for file in $MODIFIED_ROUTES; do
    # Skip __init__.py
    if [[ "$file" =~ __init__\.py$ ]]; then
        continue
    fi

    # Skip if file doesn't exist
    if [ ! -f "$file" ]; then
        continue
    fi

    # Check for Pydantic models (basic check)
    if grep -E '@router\.(get|post|put|delete|patch)' "$file" >/dev/null 2>&1; then
        # File has route definitions

        # Check if response_model is used
        if ! grep -E 'response_model=' "$file" >/dev/null 2>&1; then
            MISSING_DOCS="$MISSING_DOCS\n  - $file: Routes missing response_model parameter"
        fi

        # Check for BaseModel definitions
        if ! grep -E 'class.*\(BaseModel\)' "$file" >/dev/null 2>&1; then
            MISSING_DOCS="$MISSING_DOCS\n  - $file: Missing Pydantic BaseModel definitions"
        fi

        # Check for docstrings on route functions
        if ! grep -A 2 '@router\.' "$file" | grep -E '"""' >/dev/null 2>&1; then
            MISSING_DOCS="$MISSING_DOCS\n  - $file: Route functions missing docstrings"
        fi
    fi
done

if [ -n "$MISSING_DOCS" ]; then
    echo "⚠ MISSING API DOCUMENTATION DETECTED"
    echo ""
    echo "The following route files have incomplete API documentation:"
    echo -e "$MISSING_DOCS"
    echo ""
    echo "📋 API DOCUMENTATION REQUIREMENTS:"
    echo "  - Pydantic BaseModel for requests and responses"
    echo "  - response_model parameter on all routes"
    echo "  - Docstrings on all route functions"
    echo "  - OpenAPI documentation auto-generated"
    echo ""
    echo "🔧 ACTION REQUIRED:"
    echo "  Add complete API documentation to route files."
    echo "  See .claude/rules.md Section 8.2 for requirements."
    echo ""
    echo "✓ Verify: curl http://localhost:5555/docs"
    echo ""
    exit 2
fi

# Success
exit 0
