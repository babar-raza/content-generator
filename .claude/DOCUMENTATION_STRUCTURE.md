# Documentation Structure - Content Generator

## Overview

The Content Generator maintains **two distinct types of documentation**:

1. **System Documentation** (`docs/`) - For users, operators, and administrators
2. **Development Documentation** (`development/`) - For developers and maintainers

This separation ensures clarity and prevents confusion between "how to use the system" and "how to modify the code."

---

## Directory Structure

```
content-generator/
│
├── docs/                               # SYSTEM DOCUMENTATION
│   ├── README.md                       # System docs index
│   ├── GETTING_STARTED.md              # Getting started guide
│   ├── API_REFERENCE.md                # API endpoint reference
│   ├── DEPLOYMENT_GUIDE.md             # Deployment instructions
│   ├── CLI_CONSOLIDATION.md            # CLI usage guide
│   ├── TROUBLESHOOTING_GUIDE.md        # User troubleshooting
│   ├── WORKFLOW_VISUALIZATION_GUIDE.md # Workflow visualization
│   ├── api/                            # API documentation
│   │   └── endpoint references, usage examples
│   ├── tutorials/                      # Step-by-step tutorials
│   │   └── user guides and walkthroughs
│   └── configuration/                  # Configuration reference
│       └── settings and options
│
├── development/                        # DEVELOPMENT DOCUMENTATION
│   ├── README.md                       # Development docs index
│   ├── CODING_GUIDELINES.md            # Code standards and conventions
│   ├── architecture/                   # Internal architecture
│   │   ├── agents_architecture.md
│   │   ├── workflow_engine.md
│   │   └── execution_engines.md
│   ├── guides/                         # Development guides
│   │   ├── adding_agents.md
│   │   ├── creating_workflows.md
│   │   └── testing_guide.md
│   └── workflows/                      # Development workflows
│       ├── git_workflow.md
│       └── release_process.md
│
├── reports/                            # ANALYSIS & FINDINGS
│   └── task reports, analysis, findings
│
├── .claude/                            # CLAUDE CODE CONFIGURATION
│   ├── rules.md                        # Repository rules
│   ├── DOCUMENTATION_STRUCTURE.md      # This file
│   ├── settings.project.json           # Project hooks & config
│   └── templates/                      # Templates (taskcard, etc.)
│       └── taskcard.md
│
└── scripts/hooks/                      # HOOK SCRIPTS
    ├── README.md                       # Hooks documentation
    ├── check_tests.sh
    ├── check_docs.sh
    ├── check_doc_location.sh           # Enforces doc separation
    └── ...
```

---

## Documentation Types

### 📚 System Documentation (`docs/`)

**Audience**: Users, operators, administrators
**Purpose**: How to USE and OPERATE the system
**Tone**: User-friendly, task-oriented, high-level

**What goes here**:
- ✅ API endpoint references and usage examples
- ✅ CLI usage documentation
- ✅ Web UI guides and tutorials
- ✅ Configuration reference (what settings do)
- ✅ Troubleshooting guides for users
- ✅ System requirements and deployment guides
- ✅ Workflow creation and management
- ✅ Agent usage and capabilities
- ✅ Template documentation

**Examples**:
- "How to create a blog workflow"
- "How to use the Web UI"
- "How to configure tone settings"
- "How to deploy the content generator"
- "API endpoint reference"

---

### 🔧 Development Documentation (`development/`)

**Audience**: Developers, maintainers, contributors
**Purpose**: How to DEVELOP and MAINTAIN the system
**Tone**: Technical, code-focused, detailed

**What goes here**:
- ✅ Architecture diagrams and internal design
- ✅ Code structure and design patterns
- ✅ Development setup instructions
- ✅ How to add new features (agents, workflows, templates)
- ✅ Coding standards and conventions
- ✅ Testing strategies and frameworks
- ✅ CI/CD pipeline documentation
- ✅ Git workflow and branching strategy
- ✅ Claude Code hooks and automation
- ✅ Performance optimization techniques
- ✅ Debugging guides (for developers)

**Examples**:
- "How to create a new agent"
- "Agent architecture and contracts"
- "Workflow engine internals"
- "Git branching strategy"
- "How to write integration tests"

---

## Decision Guide

### Quick Questions

**Ask yourself**: Who is the primary audience?

| Question | `docs/` | `development/` |
|----------|---------|----------------|
| Who reads this? | Users, operators, admins | Developers, maintainers |
| What does it explain? | How the system works | How the code works |
| What's the goal? | Use/operate the system | Modify/extend the system |
| Technical depth? | High-level | Code-level |
| Code examples? | Usage examples only | Implementation details |
| Architecture? | System interfaces only | Internal design |

### Decision Tree

```
Is this document for...

├─ Using the system's features?
│  └─ docs/
│
├─ Operating/administering the system?
│  └─ docs/
│
├─ Understanding internal architecture?
│  └─ development/architecture/
│
├─ Modifying/extending the codebase?
│  └─ development/guides/
│
├─ Development processes and workflows?
│  └─ development/workflows/
│
└─ Analysis or findings from a task?
   └─ reports/
```

### Specific Examples

| Document Title | Location | Reasoning |
|----------------|----------|-----------|
| "API Endpoints" | `docs/api/` | Users need to know how to call the API |
| "How to Add a New Agent" | `development/guides/` | Developers need to modify code |
| "CLI Usage Guide" | `docs/` | Users need to use the CLI |
| "Workflow Engine Design" | `development/architecture/` | Developers need to understand internal design |
| "Troubleshooting Workflows" | `docs/` | Users need to resolve issues |
| "Agent Base Class Architecture" | `development/architecture/` | Developers need to understand structure |
| "Git Branching Strategy" | `development/workflows/` | Developers need to follow process |
| "Deployment Instructions" | `docs/` | Operators need to deploy |
| "Testing Framework" | `development/guides/` | Developers need to write tests |
| "Web UI Guide" | `docs/` | Users need to use the interface |

---

## Enforcement

### Automated Hook

A hook (`scripts/hooks/check_doc_location.sh`) runs automatically when markdown files are modified to ensure correct placement.

**How it works**:
1. Scans modified `.md` files
2. Analyzes content for keywords:
   - Development keywords: "architecture", "coding", "implementation", "internal", etc.
   - System keywords: "user guide", "api reference", "tutorial", "how to use", etc.
3. Verifies file location matches content type
4. **Exits with code 2** if misplaced → Sends feedback to Claude
5. Claude automatically moves files to correct location

**Example Hook Output**:
```
⚠ MISPLACED: docs/AGENT_ARCHITECTURE.md
   This appears to be DEVELOPMENT documentation but is in docs/
   Should be in: development/architecture/

Feedback: Please move these documentation files to the correct location
```

### Repository Rules

Enforced in `.claude/rules.md` Section 1.3:

- ✅ **System documentation** → `docs/` only
- ✅ **Development documentation** → `development/` only
- ❌ **Never mix** system and development docs
- ❌ **Never put** development docs in `docs/`
- ❌ **Never put** system docs in `development/`

### Prohibited Actions (Section 12)

- **Put system documentation outside `docs/` folder**
- **Put development documentation outside `development/` folder**
- **Mix system docs and development docs**

---

## Documentation Consolidation

### CRITICAL: Prevent Documentation Sprawl

**ALWAYS check for existing documentation before creating new files:**
- ✅ Search for existing documentation: `grep -r "topic" docs/ development/`
- ✅ Update existing files instead of creating new ones
- ✅ Use descriptive section headers within files
- ❌ Don't create multiple files for related topics
- ❌ Don't duplicate information

**When a new file IS justified:**
- Completely new major feature with no existing documentation
- New category of documentation (e.g., first security guide)
- Documentation grows too large (>1000 lines) and needs splitting
- Different audience requires separate documentation (ops vs dev)

---

## Benefits

### For Users/Operators
✅ Clear, focused documentation on HOW TO USE the system
✅ No confusion with code-level details
✅ Task-oriented guides and procedures
✅ Easy to find operational information

### For Developers
✅ Clear, focused documentation on HOW TO MODIFY the code
✅ No clutter from user guides
✅ Deep technical details and architecture
✅ Development workflows and standards

### For the Project
✅ Clear separation of concerns
✅ Easier to maintain both types of docs
✅ Automatically enforced via hooks
✅ Scalable as project grows

---

## Contributing Documentation

### System Documentation (`docs/`)

**When to create**:
- Adding a new user-facing feature
- Changing API endpoints
- Adding new workflows or templates
- Creating new operational procedures

**Template**:
```markdown
# Feature/System Name

## Overview
What does this feature/system do?

## Prerequisites
What does the user need?

## Usage
Step-by-step instructions

## Configuration
Available settings and their effects

## Troubleshooting
Common issues and solutions

## Examples
Real-world usage examples
```

### Development Documentation (`development/`)

**When to create**:
- Adding new code components
- Changing architecture
- Adding development tools
- Establishing new workflows

**Template**:
```markdown
# Component/System Name

## Architecture
How is this designed internally?

## Implementation Details
How does the code work?

## Development Setup
How to set up for development

## Adding Features
How to extend this component

## Testing
How to test changes

## Code Examples
Implementation examples with annotations
```

---

## Finding Documentation

### I want to...

| Goal | Look in... |
|------|-----------|
| Use the API | `docs/API_REFERENCE.md` |
| Use the CLI | `docs/CLI_CONSOLIDATION.md` |
| Deploy the system | `docs/DEPLOYMENT_GUIDE.md` |
| Troubleshoot issues | `docs/TROUBLESHOOTING_GUIDE.md` |
| Configure the system | `docs/configuration/` |
| Add a new agent | `development/guides/adding_agents.md` |
| Understand agent architecture | `development/architecture/agents_architecture.md` |
| Learn git workflow | `development/workflows/git_workflow.md` |
| Find code standards | `development/CODING_GUIDELINES.md` |
| Understand workflow engine | `development/architecture/workflow_engine.md` |

---

## Summary

**Two types of documentation, completely separate:**

1. **`docs/`** → System documentation (for users/operators)
   - How to USE the system
   - How to OPERATE the system

2. **`development/`** → Development documentation (for developers)
   - How the CODE works
   - How to MODIFY the code

**Automatically enforced** via hooks and repository rules.

**Never mix them** - Claude will automatically detect and correct misplaced documentation.

---

**Last Updated**: 2025-12-04
**Enforcement**: Strict - Automated via hooks
**Rules Reference**: `.claude/rules.md` Section 1.3
