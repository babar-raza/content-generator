# Claude Code Repository Rules

These rules apply to ALL interactions with this repository. Follow them strictly.

---

## 1. File Organization Rules

### 1.1 Task Templates
- **Taskcard Template**: When user says "taskcard template", "use taskcard", or "apply taskcard":
  - Read and apply `.claude/templates/taskcard.md`
  - Follow all requirements specified in the template
  - No need for user to copy-paste the template
- All templates stored in `.claude/templates/`

### 1.1.1 Automated Hooks
- **Hooks are ENABLED** for this project (configured in `.claude/settings.project.json`)
- When you edit/write Python files, hooks will automatically:
  - **Check for root-level files** (prevent clutter)
  - Check for and run tests
  - Verify DOCGEN documentation coverage
  - Auto-format code with black
  - Detect deployment requirements
  - Verify documentation locations
- **Respond to hook feedback**: If hooks report missing tests or docs, create them immediately
- Hook feedback appears as system messages - treat it as a blocking requirement

### 1.1.2 Repository Root - Keep It Clean
- **CRITICAL**: Repository root must remain clean and minimal
- **NEVER** create files at repository root level unless explicitly requested
- **ABSOLUTELY NO** `.md` or `.txt` files at root except `README.md`
  - ❌ No `GUIDE.md`, `NOTES.md`, `TODO.md`, `PLAN.md`, etc.
  - ❌ No `.txt` files at root level
  - ✅ Only exception: `README.md` (must be kept up-to-date)
- Only essential infrastructure files allowed at root:
  - `README.md`, `LICENSE`, `.gitignore`, `.gitattributes`
  - `.env.example`, `requirements.txt`, `setup.py`, `pyproject.toml`
  - `Makefile`, `package.json`, `pytest.ini`
  - `ucop_cli.py` (main CLI entry point)

**Where to put different file types**:

| File Type | Location | Example |
|-----------|----------|---------|
| System documentation | `docs/` | API guides, user guides |
| Development documentation | `development/` | Architecture, coding guides |
| Reports & analysis | `reports/` | Task reports, findings |
| Claude configuration | `.claude/` | Rules, templates, settings |
| Hook scripts | `scripts/hooks/` | Automation scripts |
| Test files | `tests/` | Unit, integration tests |
| Source code | `src/` | Agents, core, engine, web, etc. |
| Configuration | `config/` | YAML configs, validation |
| Templates | `templates/` | Workflow and blog templates |
| Temporary files | `tmp/` or `.gitignore` | Never commit |

**Enforcement**: Automatic hook (`check_root_files.sh`) will alert if root-level files are created

### 1.2 Reports, Analysis & Findings
- **ALWAYS** write reports, analysis, and findings to the `reports/` folder
- Use clear, descriptive filenames with dates: `TASKNAME_REPORT_YYYY-MM-DD.md`
- Include executive summaries at the top of reports
- Examples:
  - `reports/DEPLOYMENT_VERIFICATION_REPORT.md`
  - `reports/PHASE1_COMPLETION_SUMMARY.md`
  - `reports/exploration-phase-01.md`

### 1.3 Documentation - TWO TYPES

#### 1.3.1 System Documentation (`docs/`)
**Audience**: Users, operators, administrators
**Purpose**: How to USE and OPERATE the system

- **ALWAYS** write user/operator documentation to the `docs/` folder
- Use appropriate subdirectories: `docs/tutorials/`, `docs/api/`
- Examples:
  - `docs/GETTING_STARTED.md` - How to get started
  - `docs/API_REFERENCE.md` - API endpoint reference
  - `docs/WORKFLOW_VISUALIZATION_GUIDE.md` - Using visualizations
  - `docs/DEPLOYMENT_GUIDE.md` - Deployment instructions

**What goes here**:
- API documentation and endpoint references
- User guides and tutorials
- Configuration reference (what settings do)
- Troubleshooting guides for users
- System requirements and deployment guides
- CLI usage documentation
- Web UI guides

#### 1.3.2 Development Documentation (`development/`)
**Audience**: Developers, maintainers, contributors
**Purpose**: How to DEVELOP and MAINTAIN the system

- **ALWAYS** write developer/maintainer documentation to the `development/` folder
- Use subdirectories:
  - `development/architecture/` - System design and internal structure
  - `development/guides/` - Development guides and how-tos
  - `development/workflows/` - Development processes
- Examples:
  - `development/CODING_GUIDELINES.md` - Code standards
  - `development/guides/adding_agents.md` - How to add agents
  - `development/architecture/workflow_engine.md` - Engine design

**What goes here**:
- Architecture diagrams and internal design
- Code structure and design patterns
- Development setup instructions
- How to add new features (agents, workflows, templates)
- Coding standards and conventions
- Testing strategies and frameworks
- CI/CD pipeline documentation
- Git workflow and branching strategy
- Claude Code hooks and automation
- Performance optimization techniques

#### 1.3.3 Decision Guide

**Ask**: Who is the primary audience?

| If the document explains... | Location |
|------------------------------|----------|
| How to USE the system | `docs/` |
| How to OPERATE the system | `docs/` |
| How the CODE WORKS | `development/` |
| How to MODIFY the code | `development/guides/` |
| API endpoints (usage) | `docs/api/` |
| Internal architecture | `development/architecture/` |
| Deployment (for operators) | `docs/` |
| Development workflow | `development/workflows/` |

#### 1.3.4 Documentation Consolidation (HARD RULE - PREVENT SPRAWL)

**CRITICAL**: Prevent documentation sprawl by consolidating related information.

**ALWAYS check for existing documentation before creating new files:**
- ✅ **ALWAYS** search for existing documentation on the topic first
- ✅ **ALWAYS** update/append to existing files instead of creating new ones
- ✅ **ALWAYS** check related documentation files for consolidation opportunities
- ✅ **ALWAYS** use descriptive section headers for different topics within a file
- ❌ **NEVER** create multiple files covering similar/related topics
- ❌ **NEVER** create new files when existing files can be updated
- ❌ **NEVER** create documentation files without checking for duplicates

**How to check for existing documentation:**
1. Search existing docs: `grep -r "topic_keyword" docs/ development/`
2. Check existing files for similar topics
3. Review related feature documentation
4. Ask: "Could this go in an existing file with a new section?"

**Consolidation strategy:**
- If adding information about a feature → Update the feature's existing documentation
- If documenting a new workflow → Check `development/workflows/` or `docs/` for related workflows
- If adding API documentation → Update existing API docs in `docs/API_REFERENCE.md`
- If documenting a fix/change → Update the relevant system documentation
- If documenting deployment → Update `docs/DEPLOYMENT_GUIDE.md`

**When a new file IS justified:**
- Completely new major feature with no existing documentation
- New category of documentation (e.g., first security guide)
- Documentation grows too large (>1000 lines) and needs splitting
- Different audience requires separate documentation (ops vs dev)

### 1.4 DOCGEN Documentation Coverage
- **ALWAYS** generate or enhance DOCGEN documentation with **100% .py file coverage**
- Every Python file must have:
  - Module-level docstring
  - Class docstrings with attributes
  - Function/method docstrings with parameters, returns, and raises sections
- Use Google-style docstrings format
- Run documentation coverage checks before considering work complete

**Important - Update Existing Documentation:**
- If documentation already exists, **UPDATE** it to reflect code changes
- Don't just create new docs - refresh existing ones
- Ensure docstrings match current function signatures and behavior
- Update examples if code behavior changed

---

## 2. Code Modification Rules

### 2.1 Before Editing
- **ALWAYS** read files before modifying them
- Never propose changes to code you haven't seen
- Understand existing patterns before making changes

### 2.2 During Editing
- Respect existing architecture and patterns
- Follow PEP 8 for Python code
- Add type hints to all new Python functions
- Keep functions small and focused

### 2.3 After Editing
- Run tests: `python -m pytest`
- Run linting: `python -m black` for formatting
- Verify no regressions introduced
- Update relevant documentation in `docs/` or `development/`

---

## 3. Testing Rules

### 3.1 Test Coverage
- Write tests for all new features
- Place tests in `tests/` with matching structure
- Run full test suite before claiming completion

**Important - Update Existing Tests:**
- If tests already exist for modified code, **UPDATE** them to match code changes
- Don't just run existing tests - refresh them to cover new behavior
- Update test assertions if function behavior changed
- Add new test cases for new edge cases or features
- Ensure test coverage remains comprehensive after changes

### 3.2 Test Types
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- E2E tests: `tests/e2e/`
- Web tests: `tests/web/`

---

## 4. Git Commit Rules

### 4.1 Commit Messages
- Use conventional commits format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- Include ticket references when applicable
- Examples:
  - `feat(agents): add code validation agent`
  - `fix(web): correct workflow loading issue`
  - `docs(api): update endpoint documentation`

### 4.2 When to Commit
- Only commit when explicitly requested by user
- Always include Claude attribution footer
- Never skip pre-commit hooks unless explicitly requested

---

## 5. Documentation Generation Rules

### 5.1 Python Documentation
- Use Google-style docstrings
- Document all public APIs
- Include usage examples in docstrings
- Keep docstrings up-to-date with code changes

### 5.2 Coverage Requirements
- **100% coverage** of all `.py` files
- No exceptions unless explicitly documented
- Verify coverage with documentation checks

### 5.3 Documentation Types
```python
"""Module docstring: Brief description.

Extended description with more details about
the module's purpose and usage.
"""

class Example:
    """Class docstring.

    Attributes:
        attr1: Description of attr1
        attr2: Description of attr2
    """

    def method(self, param1: str, param2: int) -> bool:
        """Method docstring.

        Args:
            param1: Description of param1
            param2: Description of param2

        Returns:
            Description of return value

        Raises:
            ValueError: When param2 is negative
        """
        pass
```

---

## 6. Error Handling Rules

### 6.1 Validation
- Validate at system boundaries (APIs, CLI, web handlers)
- Fail fast on invalid input
- Use consistent error types

### 6.2 Logging
- Log enough context to debug issues
- Never log sensitive data (secrets, passwords, tokens)
- Use appropriate log levels

---

## 7. Content Generator Specific Rules

### 7.1 Agent Development
- All agents inherit from `AgentBase` in `src/core/agent_base.py`
- Agents must declare their contracts (inputs/outputs)
- Agents categorized by type: code, content, ingestion, research, seo, publishing, support
- Use `@agent_scanner` decorator for automatic registration

### 7.2 Workflow Management
- Workflows defined in `templates/workflows.yaml`
- Multi-template manager supports multiple workflow templates
- Workflow compilation happens in `src/core/workflow_compiler.py`
- Use dependency resolver for agent ordering

### 7.3 Web API Guidelines
- All routes in `src/web/routes/`
- Use FastAPI with Pydantic models for request/response
- Follow RESTful conventions
- Document all endpoints in OpenAPI/Swagger

### 7.4 Frontend Development
- Frontend code in `src/web/static/src/`
- TypeScript with React
- Use shared API client from `src/api/client.ts`
- Build with Vite: `npm run build`

### 7.5 Configuration Management
- Main config in `config/main.yaml`
- Validation rules in `config/validation.yaml`
- Tone settings in `config/tone.json`
- Performance settings in `config/perf.json`

---

## 8. Feature Development & API Exposure Rules

### 8.1 MCP Endpoints (RECOMMENDED)
**RECOMMENDED**: Expose features via MCP (Model Context Protocol) endpoints where appropriate

- ✅ **CONSIDER** creating MCP endpoints for agent execution and content generation
- ✅ **USE** MCP adapter in `src/mcp/adapter.py` for integration
- ✅ **DOCUMENT** MCP endpoints when created
- ✅ Test MCP integration when adding MCP features

**Pattern for MCP features:**
1. Implement core functionality in appropriate module
2. Create MCP handler if appropriate
3. Add tests for MCP functionality
4. Document MCP usage

### 8.2 Auto Swagger/OpenAPI Documentation (MANDATORY)
**CRITICAL**: ALL API endpoints must have auto-generated OpenAPI documentation

- ✅ **ALWAYS** add Pydantic models for request/response schemas
- ✅ **ALWAYS** use FastAPI route decorators with response_model
- ✅ **ALWAYS** add docstrings to API endpoints (becomes OpenAPI description)
- ✅ **ALWAYS** verify `/docs` endpoint shows new routes
- ❌ **NEVER** create undocumented API endpoints
- ❌ **NEVER** skip schema validation for "simple" endpoints

**Pattern for new API endpoints:**
```python
from pydantic import BaseModel
from fastapi import APIRouter

class FeatureRequest(BaseModel):
    """Request schema for feature endpoint."""
    param1: str
    param2: int

class FeatureResponse(BaseModel):
    """Response schema for feature endpoint."""
    status: str
    result: dict

router = APIRouter()

@router.post("/feature", response_model=FeatureResponse)
async def create_feature(request: FeatureRequest):
    """
    Create new feature.

    This endpoint processes the feature request and returns results.
    Auto-documented in OpenAPI/Swagger.
    """
    # Implementation
    return FeatureResponse(status="success", result={})
```

**Validation:**
```bash
# After adding/updating endpoints, verify:
curl http://localhost:5555/docs  # Swagger UI should show new endpoint
```

### 8.3 Feature Integration Checklist
Before claiming feature complete:
- [ ] Core functionality implemented
- [ ] API endpoint created (if web-accessible)
- [ ] Pydantic schemas defined
- [ ] OpenAPI documentation auto-generated
- [ ] `/docs` endpoint displays correctly
- [ ] Integration tests pass
- [ ] Documentation updated in `docs/`

---

## 9. Special Requirements

### 9.1 Windows Compatibility
- This repo runs on Windows - ensure paths use forward slashes in code
- Test PowerShell scripts on Windows
- Use cross-platform commands when possible

### 9.2 CLI Usage
- Main CLI is `ucop_cli.py`
- Support both command-line and programmatic usage
- Provide helpful error messages

---

## 10. Testing & Validation Rules

### 10.1 Autonomous Testing
- **NEVER** ask the user to test manually
- **ALWAYS** run tests yourself and report results
- Test all changes before reporting completion
- Provide test output and results in responses

### 10.2 Test Execution
- Run relevant tests immediately after code changes
- Run full test suite for significant changes
- Report test results with pass/fail counts and any errors
- If tests fail, fix issues and re-run until passing
- **UPDATE existing tests** when modifying code they cover (don't just create new tests)

---

## 11. Task Completion Standards

### 11.1 Definition of "Complete"
A task is **NOT complete** until ALL of the following criteria are met:

#### End-to-End Implementation
- **Zero TODOs** left in code
- **Zero partial implementations** or placeholder code
- **Zero skipped edge cases** or deferred work
- Every requirement explicitly verified and addressed
- No files left in inconsistent or intermediate state
- No configuration left incomplete or partially applied

#### System-Wide Verification
- **Regression check MANDATORY**: All previously working scenarios must continue to work exactly as before (or better)
- **Impact analysis MANDATORY**: Identify all affected components, workflows, and integrations
- **Ripple effect detection**: Check for unintended side effects in:
  - Related modules and services
  - Configuration files
  - API contracts and integrations
  - Documentation and examples
  - Tests and test fixtures

#### Fix-Verify Loop
- If ANY regressions or side effects detected:
  1. **Fix** the issue immediately
  2. **Re-verify** the entire system
  3. Repeat until clean
- Never report completion with known issues
- Never defer regression fixes to "later"

### 11.2 Pre-Completion Checklist
Before claiming task completion, verify:

1. **Implementation Complete**
   - [ ] All requirements implemented
   - [ ] No TODOs, FIXMEs, or placeholders
   - [ ] All edge cases handled
   - [ ] All error paths tested

2. **System Stability**
   - [ ] No regressions introduced
   - [ ] All existing tests still pass
   - [ ] No breaking changes to APIs or contracts
   - [ ] All integrations verified working

3. **Code Quality**
   - [ ] Code follows existing patterns
   - [ ] No temporary hacks or workarounds
   - [ ] No commented-out code
   - [ ] All files in consistent state

4. **Documentation & Testing**
   - [ ] New code has tests
   - [ ] **Existing tests updated** to match code changes (not just new tests added)
   - [ ] Documentation updated
   - [ ] **Existing documentation refreshed** to match code changes (not just new docs added)
   - [ ] Examples still work

---

## 12. Prohibited Actions

**NEVER** do these without explicit user request:
- Ask user to test manually - YOU test and report results
- **Create ANY files at repository root level** (keeps root clean and organized)
  - ❌ No markdown files (*.md) at root except README.md
  - ❌ No documentation files at root
  - ❌ No guide files at root
  - ❌ No report files at root
  - ✅ Only exception: Critical files like README.md (already exists)
  - ✅ Use proper directories: `docs/`, `development/`, `reports/`, `.claude/`, `scripts/`
- Skip running tests after code changes
- Commit code with failing tests
- Generate incomplete DOCGEN documentation (<100% coverage)
- Put reports outside `reports/` folder
- **Put system documentation outside `docs/` folder**
- **Put development documentation outside `development/` folder**
- **Mix system docs and development docs** (they must be separate)
- **Report task complete with TODOs, partial implementations, or known issues**
- **Skip regression checks or system-wide verification**
- **Defer fixing detected regressions to later**

**API Integration Prohibitions:**
- ❌ **NEVER** create API endpoints without Pydantic schemas
- ❌ **NEVER** skip OpenAPI/Swagger documentation generation
- ❌ **NEVER** create undocumented API endpoints
- ❌ **NEVER** commit API changes without verifying `/docs` endpoint works

**Documentation Consolidation Prohibitions:**
- ❌ **NEVER** create new documentation files without checking for existing related files
- ❌ **NEVER** create separate files for related topics that should be consolidated
- ❌ **NEVER** skip searching existing documentation before creating new files
- ❌ **NEVER** create duplicate documentation on the same topic

---

## 13. Quality Checklist

Before considering ANY task complete, verify ALL items in Section 11 "Task Completion Standards" PLUS:

- [ ] All `.py` files have 100% DOCGEN documentation coverage
- [ ] **Existing docstrings updated** to match code changes
- [ ] Tests pass: `python -m pytest`
- [ ] **Existing tests updated** to cover modified code behavior
- [ ] Code is formatted: `python -m black`
- [ ] Reports written to `reports/` folder
- [ ] Documentation written to `docs/` folder (for system docs) or `development/` folder (for dev docs)
- [ ] **Existing documentation files refreshed** to reflect changes
- [ ] No sensitive data in code or logs
- [ ] Git status clean (unless changes are intentional)
- [ ] **NO TODOs, partial implementations, or skipped edge cases**
- [ ] **System-wide regression check performed and passed**
- [ ] **All ripple effects identified and resolved**

**API Integration Checks (if features added/modified):**
- [ ] Pydantic request/response models defined
- [ ] API endpoint has `response_model` parameter
- [ ] Endpoint docstring present (for OpenAPI description)
- [ ] OpenAPI spec generated: verify `/docs` endpoint shows new routes
- [ ] Feature integration tests pass

**Documentation Consolidation Checks (if documentation modified/created):**
- [ ] Searched for existing documentation on same topic: `grep -r "topic" docs/ development/`
- [ ] Verified no duplicate/overlapping documentation exists
- [ ] Updated existing files instead of creating new ones (if related file exists)
- [ ] Used descriptive section headers for different topics within a file
- [ ] Justified creation of new file (completely new major feature, different audience, etc.)

---

**Last Updated**: 2025-12-04
**Enforcement**: Strict - These rules apply to ALL interactions
