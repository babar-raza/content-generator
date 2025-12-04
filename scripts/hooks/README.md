# Claude Code Hooks

This directory contains hook scripts that automatically run when you edit/write files using Claude Code.

---

## What Are Hooks?

Hooks are automation scripts that enforce repository rules and standards. They run automatically after tool use (Edit/Write) to ensure code quality, proper documentation, and correct file organization.

**Configuration**: Hooks are configured in `.claude/settings.project.json`

---

## Available Hooks

### 1. `check_root_files.sh`
**Purpose**: Prevent files from being created at repository root
**When**: After Edit/Write operations
**Action**: Detects `.md` or `.txt` files at root level (except README.md)
**Feedback**: Tells Claude to move files to correct directories

**Example:**
```
❌ ROOT-LEVEL FILE VIOLATIONS DETECTED
  - GUIDE.md
  - TODO.txt

📁 CORRECT LOCATIONS:
  - Reports/Analysis → reports/
  - User Documentation → docs/
  - Developer Documentation → development/
```

### 2. `check_tests.sh`
**Purpose**: Check if tests exist and run them for modified Python files
**When**: After editing `.py` files
**Action**: Looks for corresponding test files and runs pytest
**Feedback**: Reports missing tests or test failures

**Example:**
```
⚠ MISSING TESTS DETECTED
  - src/agents/seo/keyword_extractor.py → Expected: tests/unit/agents/seo/test_keyword_extractor.py

🔧 ACTION REQUIRED:
  Create test files for these modules.
```

### 3. `check_docs.sh`
**Purpose**: Verify DOCGEN documentation coverage
**When**: After editing `.py` files
**Action**: Checks for module docstrings, class docstrings, and function docstrings
**Feedback**: Reports files with incomplete documentation

**Example:**
```
⚠ MISSING DOCUMENTATION DETECTED
  - src/agents/seo/keyword_extractor.py: Missing module docstring
  - src/core/workflow_compiler.py: Functions missing docstrings

📋 REQUIREMENTS:
  - Module-level docstring
  - Class docstrings with attributes
  - Function/method docstrings with Args, Returns, Raises
```

### 4. `auto_format.sh`
**Purpose**: Auto-format modified Python files with black
**When**: After editing `.py` files
**Action**: Runs `black` formatter on all modified Python files
**Feedback**: Silent unless errors occur

### 5. `check_doc_location.sh`
**Purpose**: Verify documentation files are in correct locations
**When**: After editing `.md` files
**Action**: Analyzes content to determine if doc is system (docs/) or development (development/)
**Feedback**: Reports misplaced documentation

**Example:**
```
⚠ MISPLACED DOCUMENTATION DETECTED
  ⚠ docs/AGENT_ARCHITECTURE.md
     This appears to be DEVELOPMENT documentation but is in docs/
     Should be in: development/architecture/

📋 DOCUMENTATION STRUCTURE:
  docs/        → System documentation (users, operators)
  development/ → Development documentation (developers)
```

### 6. `check_doc_consolidation.sh`
**Purpose**: Prevent documentation sprawl
**When**: After creating new `.md` files
**Action**: Checks for similar existing files
**Feedback**: Warns about potential duplicates

**Example:**
```
⚠ POTENTIAL DOCUMENTATION SPRAWL DETECTED
  ⚠ New: docs/workflow_guide.md
     Similar to: docs/workflows.md
     Consider: Consolidating into existing file

📋 CONSOLIDATION GUIDELINES:
  - Search existing docs before creating new files
  - Update existing files instead of creating duplicates
```

### 7. `check_api_docs.sh`
**Purpose**: Enforce OpenAPI/Swagger documentation
**When**: After editing route files in `src/web/routes/`
**Action**: Checks for Pydantic models, response_model, and docstrings
**Feedback**: Reports missing API documentation

**Example:**
```
⚠ MISSING API DOCUMENTATION DETECTED
  - src/web/routes/workflows.py: Routes missing response_model parameter
  - src/web/routes/workflows.py: Missing Pydantic BaseModel definitions

📋 API DOCUMENTATION REQUIREMENTS:
  - Pydantic BaseModel for requests and responses
  - response_model parameter on all routes
  - Docstrings on all route functions
```

### 8. `validate_hooks.sh` (META-HOOK)
**Purpose**: Validate all hook scripts follow correct patterns
**When**: After any Edit/Write operation (runs first)
**Action**: Checks all hooks in `scripts/hooks/` for compliance
**Feedback**: Reports hook pattern violations

**This hook ensures all other hooks maintain quality standards.**

**Example:**
```
❌ HOOK VALIDATION FAILED

The following hook pattern violations were detected:
  ❌ custom_hook.sh: Missing or incorrect shebang (#!/bin/bash)
  ⚠ custom_hook.sh: Missing exit code documentation comment
  ❌ custom_hook.sh: Uses invalid exit codes (only 0, 1, 2 allowed)

📋 REQUIRED HOOK PATTERN:
  1. #!/bin/bash shebang (first line)
  2. # Hook: <description> comment
  3. # Exit codes: documentation
  4. set -e (error handling)
  5. Only exit codes 0, 1, 2
  6. Explicit exit statements
  7. File must be executable
```

---

## How Hooks Work

### Execution Flow

1. **User/Claude edits or writes a file**
2. **Hooks run automatically** based on configuration
3. **Each hook checks for specific issues**
4. **Hook returns exit code:**
   - `0` - Success, no issues
   - `1` - Fatal error (rare)
   - `2` - Issues found, feedback sent to Claude
5. **Claude sees feedback and takes corrective action**

### Hook Configuration

Hooks are configured in `.claude/settings.project.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash scripts/hooks/check_root_files.sh",
            "timeout": 30,
            "description": "Prevent files from being created at repository root"
          }
        ]
      }
    ]
  }
}
```

---

## Benefits

### Automatic Enforcement
- Rules are enforced automatically, no manual checks needed
- Claude receives immediate feedback and can self-correct
- Maintains code quality without user intervention

### Consistency
- Ensures consistent code formatting (black)
- Enforces documentation standards (DOCGEN)
- Maintains proper file organization

### Quality Assurance
- Tests run automatically after code changes
- Documentation coverage verified
- API documentation completeness checked

### Clean Repository
- Prevents root-level file clutter
- Enforces proper documentation structure
- Prevents documentation sprawl

---

## Disabling Hooks

### Temporarily Disable (for current session)
Edit `.claude/settings.project.json`:
```json
{
  "preferences": {
    "auto_run_hooks": false
  }
}
```

### Disable Specific Hook
Comment out the hook in `.claude/settings.project.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          // {
          //   "type": "command",
          //   "command": "bash scripts/hooks/check_root_files.sh",
          //   ...
          // }
        ]
      }
    ]
  }
}
```

---

## Hook Pattern Requirements (ENFORCED)

All hook scripts **MUST** follow this pattern. The `validate_hooks.sh` meta-hook automatically enforces these requirements.

### Required Elements

#### 1. Shebang (REQUIRED - ERROR if missing)
```bash
#!/bin/bash
```
- Must be the first line
- Must be exactly `#!/bin/bash`
- No spaces or variations

#### 2. Hook Description (REQUIRED - WARNING if missing)
```bash
# Hook: Brief description of what this hook checks
```
- Must have `# Hook:` comment
- Describes the hook's purpose

#### 3. Exit Code Documentation (REQUIRED - WARNING if missing)
```bash
# Exit codes:
# 0 - Success (no violations)
# 1 - Fatal error (unexpected failure)
# 2 - Violations found (sends feedback to Claude)
```
- Must document exit codes
- Standard format recommended

#### 4. Error Handling (REQUIRED - WARNING if missing)
```bash
set -e
```
- Enables strict error handling
- Prevents silent failures

#### 5. Valid Exit Codes Only (REQUIRED - ERROR if violated)
```bash
exit 0  # Success
exit 1  # Fatal error (rare)
exit 2  # Violations found
```
- **Only use exit codes 0, 1, or 2**
- No other exit codes allowed
- Must have explicit exit statements

#### 6. File Executable (REQUIRED - ERROR if missing)
```bash
chmod +x scripts/hooks/your_hook.sh
```
- Hook file must be executable
- Run chmod after creating hook

### Exit Code Behavior

| Code | Meaning | Effect | When to Use |
|------|---------|--------|-------------|
| `0` | Success | Hook passes, continues | No violations found |
| `1` | Fatal error | Hook failed | Script errors (rare) |
| `2` | Violations | Sends feedback to Claude | **Violations detected** |

**Critical**: Use `exit 2` when you want Claude to receive feedback and take corrective action.

### Hook Template

Use the provided template as a starting point:

```bash
cp scripts/hooks/hook_template.sh scripts/hooks/your_hook.sh
```

The template includes:
- All required elements
- Standard structure
- Commented examples
- Best practices
- Common patterns

See [hook_template.sh](hook_template.sh) for the full template with extensive comments.

### Validation Enforcement

The `validate_hooks.sh` meta-hook automatically checks:
- ✅ Shebang present and correct
- ✅ Hook description comment exists
- ✅ Exit codes documented
- ✅ Error handling enabled (set -e)
- ✅ Only valid exit codes used (0, 1, 2)
- ✅ Explicit exit statements present
- ✅ File is executable
- ✅ Success exit code defined (exit 0)
- ⚠️ Feedback exit code present (exit 2) - suggestion only

**The validation hook runs automatically on every Edit/Write operation**, ensuring all hooks maintain correct patterns.

---

## Adding New Hooks

### Step-by-Step Process

1. **Copy the template**:
   ```bash
   cp scripts/hooks/hook_template.sh scripts/hooks/your_hook.sh
   ```

2. **Customize the template**:
   - Update hook description
   - Set file pattern to match
   - Add your validation checks
   - Customize violation messages

3. **Make executable**:
   ```bash
   chmod +x scripts/hooks/your_hook.sh
   ```

4. **Test the hook**:
   ```bash
   bash scripts/hooks/your_hook.sh
   echo $?  # Should be 0, 1, or 2
   ```

5. **Validate the hook**:
   ```bash
   bash scripts/hooks/validate_hooks.sh
   ```
   Fix any violations reported.

6. **Register the hook** (see below)

7. **Test in context**: Edit a file and verify hook runs

### Register Hook

Add to `.claude/settings.project.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash scripts/hooks/your_hook.sh",
            "timeout": 60,
            "description": "Your hook description"
          }
        ]
      }
    ]
  }
}
```

### Hook Development Best Practices

#### Do's ✅
- **Do** use the provided template
- **Do** follow the required pattern
- **Do** use descriptive violation messages
- **Do** provide actionable feedback
- **Do** reference relevant rules documentation
- **Do** test with various scenarios
- **Do** handle file existence gracefully
- **Do** exit early if no relevant files
- **Do** use consistent output format
- **Do** document what you're checking

#### Don'ts ❌
- **Don't** use exit codes other than 0, 1, 2
- **Don't** forget the shebang
- **Don't** skip error handling (set -e)
- **Don't** use bare 'exit' without code
- **Don't** forget to make file executable
- **Don't** create hooks without testing
- **Don't** skip validation check
- **Don't** block on warnings (use exit 2 for errors only)

---

## Troubleshooting

### Hook Not Running
- Check `.claude/settings.project.json` is properly formatted
- Verify `auto_run_hooks: true` in preferences
- Check hook script is executable
- Check timeout is sufficient

### Hook Errors
- Check hook script for syntax errors
- Verify required tools are installed (black, pytest, etc.)
- Check file paths in hook script
- Review hook output for error messages

### False Positives
- Hook may need tuning for edge cases
- Consider adjusting keyword matching in hooks
- Report issues for hook improvement

---

## Related Documentation

- **Rules**: See `.claude/rules.md` for all repository rules
- **Documentation Structure**: See `.claude/DOCUMENTATION_STRUCTURE.md`
- **Settings**: See `.claude/settings.project.json` for hook configuration

---

**Last Updated**: 2025-12-04
**Enforcement**: Automatic via Claude Code hooks
