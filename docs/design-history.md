# Design History & Legacy Notes

This document preserves historical context, deprecated features, design decisions, and migration information for UCOP.

## Table of Contents

- [Version History](#version-history)
- [Production Readiness Status](#production-readiness-status)
- [Known Issues & Fixes](#known-issues--fixes)
- [Deprecated Features](#deprecated-features)
- [Architecture Evolution](#architecture-evolution)
- [Migration Guides](#migration-guides)

## Version History

### v1.2.0 (Current) - November 2025

**Major Features:**
- LangGraph workflow orchestration integration
- 38 MCP-compliant agents (up from 25)
- React-based web UI with visual workflow editor
- Hot-reload configuration support
- Parallel agent execution
- Comprehensive checkpoint system

**Breaking Changes:**
- Agent interface changed to MCP protocol
- Configuration schema updated (added `capabilities` field)
- Workflow definitions moved from code to YAML

**Migration from v1.1.0:**
- Update agent implementations to implement MCP contract
- Migrate workflow definitions to `config/agents.yaml`
- Update CLI commands (some renamed)

### v1.1.0 - September 2025

**Major Features:**
- Web UI (initial version)
- FastAPI backend
- Job queue system
- Basic visualization

**Known Issues:**
- Legacy UI components not fully functional
- Some API endpoints unmounted (see Production Gaps)

### v1.0.0 - July 2025

**Initial Release:**
- CLI-only interface
- 25 agents (sequential execution only)
- Ollama integration
- Basic content generation pipeline

## Production Readiness Status

**Current Status**: ⚠️ **Beta - Not Production Ready**

**Date of Assessment**: November 15, 2025

### Critical Gaps

Based on comprehensive audit (see `/gaps/UCOP_Executive_Summary.md`):

#### 1. Unmounted MCP Web Adapter (P0 - CRITICAL)

**Problem**: The feature-rich MCP web adapter (`src/mcp/web_adapter.py`) with 29 endpoints is NOT mounted to the FastAPI application.

**Impact**:
- React UI makes calls to `/mcp/agents`, `/mcp/config/snapshot`, etc.
- Gets 404 errors
- Features appear functional locally but fail in production

**Root Cause**:
```python
# src/web/app.py currently imports WRONG router:
from .routes import mcp  # ← Minimal implementation (5 endpoints)

# Should import:
from src.mcp.web_adapter import router  # ← Full implementation (29 endpoints)
```

**Fix Required**: 2 hours - Mount correct router in `src/web/app.py`

**Status**: ❌ NOT FIXED

#### 2. Checkpoint Management (P0 - CRITICAL)

**Problem**: No web API for checkpoint operations. CLI only.

**Impact**: Web users cannot recover from failed jobs.

**Workaround**: SSH access + CLI commands

**Fix Required**: 8 hours - Implement REST API for checkpoint operations

**Status**: ❌ NOT FIXED

#### 3. Legacy UI Endpoints (P0 - CRITICAL)

**Problem**: Legacy React UI expects 6 endpoints that don't exist:
- `/api/jobs/{job_id}/artifacts`
- `/api/jobs/{job_id}/logs/stream`
- `/api/jobs/{job_id}/pipeline`
- `/api/config/validate`
- `/api/templates/preview`
- `/api/health/detailed`

**Impact**: Artifact viewing, log streaming, pipeline editing all broken

**Decision Required**: Fix endpoints (6 hours) OR remove legacy UI (2 hours)

**Status**: ❌ PENDING DECISION

#### 4. Incomplete Feature Accessibility

**Statistics** (from production gaps audit):
- **Total features implemented**: 137
- **Accessible via CLI**: 68 (50%)
- **Accessible via Web API**: 66 (48%) 
- **Accessible via UI**: 45 (33%)
- **Implemented but NOT MOUNTED**: 27 (20%)
- **Expected by UI but MISSING**: 6 (4%)
- **Total production blockers**: 33 (24%)

**Categories of inaccessible features**:
- Checkpoint management (CLI only)
- Flow analysis (CLI only)
- Advanced debugging (partial)
- Monitoring dashboard (API exists, no UI)
- Configuration inspection (unmounted)
- Agent health monitoring (missing API)

**Estimated time to production**: 2-3 weeks (40-60 developer hours)

### Production Readiness Phases

#### Phase 1: Critical Integration (Week 1 - 30 hours)

**Deliverable**: All implemented features accessible, no 404 errors

1. Mount MCP web adapter (2h)
2. Implement checkpoint REST API (8h)
3. Fix or remove legacy UI endpoints (6h)
4. Add HTTP endpoint tests (12h)
5. End-to-end smoke tests (2h)

**Status**: ❌ NOT STARTED

#### Phase 2: Operations Support (Week 2 - 50 hours)

**Deliverable**: Ops team can monitor and debug production

1. Implement flow/bottleneck APIs (10h)
2. Build basic monitoring dashboard (20h)
3. Wire debug session management (12h)
4. Add agent health monitoring (8h)

**Status**: ❌ NOT STARTED

#### Phase 3: Polish (Week 3 - 40 hours)

**Deliverable**: Production-ready, well-tested system

1. Comprehensive test coverage (25h)
2. API documentation updates (8h)
3. Performance optimization (7h)

**Status**: ❌ NOT STARTED

## Known Issues & Fixes

### Fixed Issues

#### Issue #1: Config Validator Import Error (FIXED)

**Date**: November 14, 2025

**Problem**: 
```python
# config/__init__.py tried to import non-existent class
from config.validator import ConfigValidator  # ← Doesn't exist
```

**Fix Applied**:
```python
# Removed import, updated __all__
__all__ = ['ConfigSnapshot', 'load_validated_config']
```

**Files Changed**:
- `config/__init__.py`

**Status**: ✅ FIXED

#### Issue #2: TypeScript Compilation Errors (FIXED)

**Date**: November 14, 2025

**Problem**: Multiple TypeScript errors in React UI:
- Missing types: `JobUpdate`, `WorkflowTemplate`
- Unused imports
- `Job.id` vs `Job.job_id` inconsistencies
- Null handling in workflow store

**Fix Applied**:
- Added missing type definitions
- Removed unused imports
- Standardized on `Job.job_id`
- Fixed null handling

**Files Changed**:
- `src/web/static/src/types/`
- `src/web/static/src/components/LogViewer.tsx`
- `src/web/static/src/utils/workflowStore.ts`

**Status**: ✅ FIXED

#### Issue #3: Static File Serving (FIXED)

**Date**: November 14, 2025

**Problem**: React UI not served at root `/` endpoint

**Fix Applied**:
```python
# src/web/app.py
app.mount("/", StaticFiles(directory="src/web/static/dist", html=True), name="static")

# Root endpoint now serves React UI
@app.get("/")
async def root():
    return FileResponse("src/web/static/dist/index.html")
```

**Status**: ✅ FIXED

#### Issue #4: NPM Prefix Errors (FIXED)

**Date**: November 14, 2025

**Problem**: `.npmrc` with `prefix` setting caused install errors

**Fix Applied**:
- Removed problematic `.npmrc`
- Added pre-install hooks to auto-remove if present
- Created root `package.json` that delegates to `src/web/static/`

**Status**: ✅ FIXED

#### Issue #5: Enhanced Config Snapshot (FIXED)

**Date**: November 14, 2025

**Problem**: `EnhancedConfigLoader.get_snapshot()` returned dict instead of `ConfigSnapshot` object

**Fix Applied**:
```python
# Use load_validated_config() for consistent snapshot format
def get_snapshot(self) -> ConfigSnapshot:
    return load_validated_config()
```

**Status**: ✅ FIXED

### Outstanding Issues

#### Issue #6: Unmounted MCP Web Adapter (CRITICAL)

**Status**: ❌ NOT FIXED  
**Priority**: P0  
**Estimated Fix**: 2 hours  

See "Critical Gaps" section above.

#### Issue #7: Missing Checkpoint API (CRITICAL)

**Status**: ❌ NOT FIXED  
**Priority**: P0  
**Estimated Fix**: 8 hours  

See "Critical Gaps" section above.

#### Issue #8: Legacy UI Endpoints (CRITICAL)

**Status**: ❌ PENDING DECISION  
**Priority**: P0  
**Options**:
- A: Implement missing endpoints (6 hours)
- B: Remove legacy UI entirely (2 hours)

**Recommendation**: Remove legacy UI (Option B) - simpler, faster

## Deprecated Features

### Sequential-Only Execution (Deprecated in v1.2.0)

**Old Behavior**:
```python
# Agents executed one at a time, in strict order
for agent in pipeline:
    result = agent.execute(state)
    state.update(result)
```

**New Behavior**:
```yaml
# Agents with no dependencies execute in parallel
workflows:
  enable_parallel_execution: true
  max_parallel_agents: 5
```

**Migration**: No code changes needed. Set `enable_parallel_execution: true` in config.

**Removal Timeline**: Sequential mode still supported, will be removed in v2.0.0

### Hardcoded Agent Configuration (Deprecated in v1.2.0)

**Old Behavior**:
```python
# Agents configured in Python code
agents = {
    'outline': OutlineAgent(model='qwen2.5:14b', timeout=300),
    'content': ContentAgent(model='qwen2.5:14b', timeout=600)
}
```

**New Behavior**:
```yaml
# config/agents.yaml
agents:
  outline_creation_agent:
    model: "qwen2.5:14b"
    resources:
      max_runtime_s: 300
```

**Migration**: Move agent config to `config/agents.yaml`

**Removal Timeline**: Code-based config removed in v1.2.0

### Direct LLM Service Instantiation (Deprecated in v1.1.0)

**Old Behavior**:
```python
from src.services.llm import OllamaService
llm = OllamaService(base_url='http://localhost:11434')
```

**New Behavior**:
```python
from src.services.llm_service import LLMService
from src.core.config import load_config

config = load_config()
llm = LLMService(config)  # Handles all providers with fallback
```

**Migration**: Replace direct provider instantiation with `LLMService`

**Status**: Still supported with deprecation warning

### Legacy Workflow API (Deprecated in v1.2.0)

**Old Behavior**:
```python
from src.orchestration.workflow import Workflow
workflow = Workflow(name='blog_gen', steps=[...])
```

**New Behavior**:
```python
from src.orchestration.workflow_compiler import WorkflowCompiler
compiler = WorkflowCompiler(config)
graph = compiler.compile(workflow_id='blog_generation')
```

**Migration**: Use `WorkflowCompiler` to compile YAML workflows

**Removal Timeline**: Legacy API removed in v1.2.0

## Architecture Evolution

### Phase 1: Monolithic CLI (v1.0.0)

```
┌─────────────────────────────────┐
│         CLI (ucop_cli.py)       │
├─────────────────────────────────┤
│    Sequential Agent Pipeline    │
├─────────────────────────────────┤
│     LLM Service (Ollama only)   │
└─────────────────────────────────┘
```

**Characteristics**:
- Single-file CLI
- 25 agents, sequential only
- Ollama-only
- No checkpointing
- No web interface

### Phase 2: Web UI Addition (v1.1.0)

```
┌──────────────┬──────────────────┐
│     CLI      │     Web UI       │
├──────────────┴──────────────────┤
│      Job Queue & Scheduler      │
├─────────────────────────────────┤
│    Sequential Agent Pipeline    │
├─────────────────────────────────┤
│   LLM Service (Multi-provider)  │
└─────────────────────────────────┘
```

**Characteristics**:
- Added FastAPI backend
- Basic React UI
- Job queue system
- Multi-LLM support
- Still sequential execution

### Phase 3: Current Architecture (v1.2.0)

```
┌──────────────┬──────────────────┐
│     CLI      │   Web UI (React) │
├──────────────┴──────────────────┤
│   MCP Protocol Layer (Unmounted)│ ← ISSUE
├─────────────────────────────────┤
│   LangGraph Orchestration       │
│   (Parallel, Checkpoints)       │
├─────────────────────────────────┤
│    Agent Mesh (38 Agents)       │
├─────────────────────────────────┤
│   Unified Engine & Services     │
├─────────────────────────────────┤
│   LLM Providers & Storage       │
└─────────────────────────────────┘
```

**Characteristics**:
- 38 MCP-compliant agents
- LangGraph workflows
- Parallel execution
- Checkpointing
- Hot-reload
- MCP endpoints (partially unmounted)

### Phase 4: Target Architecture (v2.0.0 - Future)

```
┌──────────┬─────────┬──────────┬───────────┐
│   CLI    │  Web UI │ API SDK  │ External  │
├──────────┴─────────┴──────────┴───────────┤
│      Fully Mounted MCP Protocol Layer     │
├───────────────────────────────────────────┤
│   LangGraph Orchestration (Distributed)   │
├───────────────────────────────────────────┤
│      Agent Mesh (50+ Agents, Pluggable)   │
├───────────────────────────────────────────┤
│   Unified Engine & Microservices          │
├───────────────────────────────────────────┤
│   Multi-LLM + Vector Store + Job Queue    │
└───────────────────────────────────────────┘
```

**Planned Features**:
- Fully mounted MCP layer
- Distributed agent execution
- Plugin system for custom agents
- GraphQL API
- Advanced monitoring dashboard
- Multi-tenant support

## Migration Guides

### Migrating from v1.1.0 to v1.2.0

#### 1. Update Agent Implementations

**Before (v1.1.0)**:
```python
class OutlineAgent:
    def execute(self, input_data):
        # Agent logic
        return result
```

**After (v1.2.0)**:
```python
from src.agents.base import Agent

class OutlineCreationAgent(Agent):
    def execute(self, input_data):
        # Agent logic
        return result
    
    @property
    def contract(self):
        return {
            'inputs': {...},
            'outputs': {...}
        }
```

#### 2. Update Configuration Files

**Before**:
```yaml
# config/agents.yaml (v1.1.0)
agents:
  outline_agent:
    timeout: 300
```

**After**:
```yaml
# config/agents.yaml (v1.2.0)
agents:
  outline_creation_agent:
    id: "outline_creation_agent"
    capabilities:
      async: false
      model_switchable: true
    resources:
      max_runtime_s: 300
      max_memory_mb: 1024
      max_tokens: 4096
```

#### 3. Update CLI Commands

**Before**:
```bash
# v1.1.0
python ucop_cli.py run --input file.md
python ucop_cli.py agents
```

**After**:
```bash
# v1.2.0
python ucop_cli.py generate --input file.md
python ucop_cli.py agent list
```

#### 4. Enable New Features

```yaml
# config/main.yaml
workflows:
  use_langgraph: true              # Enable LangGraph
  enable_parallel_execution: true  # Enable parallel agents
  max_parallel_agents: 5
```

### Migrating from v1.0.0 to v1.2.0

Follow v1.0.0 → v1.1.0 guide first (if exists), then v1.1.0 → v1.2.0 guide above.

Major changes:
- All agent names changed (added suffix: `_agent`)
- Configuration schema completely different
- CLI commands reorganized
- Workflow definitions moved to YAML

**Recommendation**: Fresh install recommended for v1.0.0 users.

## Legacy Code Locations

### Deprecated but Still Present

```
archive/                    # Archived code (v1.0.0)
├── src/                   # Old source code
├── tests/                 # Old tests
└── blog-archive.7z        # Compressed archive

src/web/routes/mcp.py      # Minimal MCP router (5 endpoints)
                          # Should be replaced with src/mcp/web_adapter.py

Legacy UI files (if kept):
src/web/static/src/legacy/  # Old React components
                          # Decision pending: remove or update
```

### Safe to Delete (After Migration)

- `archive/` directory (after confirming no dependencies)
- `src/orchestration/fallback_engine.py` (replaced by LangGraph)
- Legacy test files referencing old agent names
- Old configuration examples (`.env.example.old`)

## Design Decisions

### Why LangGraph?

**Decision Date**: August 2025

**Rationale**:
- Proven framework for multi-agent orchestration
- Built-in checkpointing
- Parallel execution support
- Active community
- Better than custom implementation

**Alternatives Considered**:
- LangChain (too generic)
- Custom orchestration (too much maintenance)
- Celery + RabbitMQ (overkill)

### Why MCP Protocol?

**Decision Date**: September 2025

**Rationale**:
- Emerging standard for AI agent communication
- External tool compatibility
- Future-proof architecture
- Claude Desktop integration potential

**Trade-offs**:
- More boilerplate code
- Learning curve for developers
- Still evolving standard

### Why 38 Agents (Not Fewer)?

**Decision Date**: October 2025

**Rationale**:
- Single Responsibility Principle
- Easier testing and maintenance
- Parallel execution benefits
- Modular reusability

**Trade-off**: More complex orchestration

### Why ChromaDB (Not Pinecone/Weaviate)?

**Decision Date**: July 2025

**Rationale**:
- Free, self-hosted
- Python-native
- Simple API
- Good enough for use case

**Trade-off**: No managed cloud option

## Future Breaking Changes

### Planned for v2.0.0

1. **Remove sequential execution mode**
2. **Require Python 3.10+** (currently 3.8+)
3. **Remove deprecated agent names**
4. **Change configuration schema** (breaking)
5. **Remove legacy UI entirely**
6. **Require async agent implementations**

### Deprecation Timeline

- **v1.3.0** (Q1 2026): Deprecation warnings for legacy features
- **v1.4.0** (Q2 2026): Remove some deprecated features
- **v2.0.0** (Q3 2026): Major breaking changes

## Document Version

**Version**: 1.0  
**Last Updated**: November 17, 2025  
**Next Review**: January 2026
