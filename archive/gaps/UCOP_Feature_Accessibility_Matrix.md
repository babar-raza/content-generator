# UCOP Feature Accessibility Matrix

**Quick Reference Guide - All Implemented Features & Their Access Methods**

---

## Legend
- ✅ = Fully Accessible
- ⚠️ = Partially Accessible
- ❌ = Not Accessible
- 🔴 = Implemented but Unmounted

---

## 1. CHECKPOINT MANAGEMENT (❌ CLI Only - No Web Access)

| Feature | Implementation | CLI Access | Web/API Access | UI Access |
|---------|---------------|------------|----------------|-----------|
| List checkpoints | ucop_cli.py:19 | ✅ `ucop checkpoint list` | ❌ No endpoint | ❌ No UI |
| Restore from checkpoint | ucop_cli.py:46 | ✅ `ucop checkpoint restore` | ❌ No endpoint | ❌ No UI |
| Delete checkpoint | ucop_cli.py:89 | ✅ `ucop checkpoint delete` | ❌ No endpoint | ❌ No UI |
| Cleanup old checkpoints | ucop_cli.py:105 | ✅ `ucop checkpoint cleanup` | ❌ No endpoint | ❌ No UI |

**Impact**: Web users cannot manage job checkpoints - must use CLI  
**Effort to Fix**: 6-8 hours - Implement `/api/checkpoints/*` endpoints

---

## 2. CONFIGURATION INSPECTION (❌ CLI Only - Endpoints Exist but NOT MOUNTED)

| Feature | Implementation | CLI Access | Web/API Access | UI Access |
|---------|---------------|------------|----------------|-----------|
| Show config snapshot | ucop_cli.py:655 | ✅ `ucop config snapshot` | 🔴 `/mcp/config/snapshot` (unmounted) | ❌ No UI |
| Show agent configs | ucop_cli.py:693 | ✅ `ucop config agents` | 🔴 `/mcp/config/agents` (unmounted) | ❌ No UI |
| Show workflow configs | ucop_cli.py:728 | ✅ `ucop config workflows` | 🔴 `/mcp/config/workflows` (unmounted) | ❌ No UI |
| Show tone config | ucop_cli.py:753 | ✅ `ucop config tone` | 🔴 `/mcp/config/tone` (unmounted) | ❌ No UI |
| Show perf config | ucop_cli.py:780 | ✅ `ucop config performance` | 🔴 `/mcp/config/performance` (unmounted) | ❌ No UI |

**Impact**: Cannot inspect runtime configuration via web  
**Effort to Fix**: 2 hours - Mount `src/mcp/web_adapter.py` router

---

## 3. JOB MANAGEMENT (✅ Accessible - Both CLI & Web)

| Feature | Implementation | CLI Access | Web/API Access | UI Access |
|---------|---------------|------------|----------------|-----------|
| Create job | src/web/routes/jobs.py:56 | ✅ `ucop generate` | ✅ `POST /api/jobs` | ✅ React UI |
| List jobs | src/web/routes/jobs.py:243 | ✅ `ucop list-jobs` | ✅ `GET /api/jobs` | ✅ React UI |
| Get job details | src/web/routes/jobs.py:298 | ✅ `ucop get-job` | ✅ `GET /api/jobs/{id}` | ✅ React UI |
| Pause job | src/web/routes/jobs.py:337 | ❌ No CLI | ✅ `POST /api/jobs/{id}/pause` | ✅ React UI |
| Resume job | src/web/routes/jobs.py:392 | ❌ No CLI | ✅ `POST /api/jobs/{id}/resume` | ✅ React UI |
| Cancel job | src/web/routes/jobs.py:447 | ❌ No CLI | ✅ `POST /api/jobs/{id}/cancel` | ✅ React UI |
| Batch create | src/web/routes/jobs.py:180 | ✅ `ucop batch` | ✅ `POST /api/batch` | ⚠️ Partial UI |
| Generate content | src/web/routes/jobs.py:112 | ✅ `ucop generate` | ✅ `POST /api/generate` | ✅ React UI |

**Impact**: Core functionality works well  
**Note**: Some advanced features in MCP adapter (unmounted) duplicate these

---

## 4. JOB DETAILS (💔 Legacy UI Expects Missing Endpoints)

| Feature | Expected Endpoint | Status | File Reference |
|---------|-------------------|--------|----------------|
| Stream job logs | `GET /api/jobs/{id}/logs/stream` | ❌ NOT IMPLEMENTED | job_detail.js:156 |
| View job artifacts | `GET /api/jobs/{id}/artifacts` | ❌ NOT IMPLEMENTED | job_detail.js:312 |
| Step through job | `POST /api/jobs/{id}/step` | ❌ NOT IMPLEMENTED | job_detail.js:428 |
| Add pipeline stage | `POST /api/jobs/{id}/pipeline/add` | ❌ NOT IMPLEMENTED | job_detail.js:544 |
| Remove pipeline stage | `POST /api/jobs/{id}/pipeline/remove` | ❌ NOT IMPLEMENTED | job_detail.js:589 |
| Get agent output | `GET /api/jobs/{id}/agents/{aid}/output` | ❌ NOT IMPLEMENTED | job_detail.js:673 |

**Impact**: Legacy dashboard silently fails - 6 broken features  
**Effort to Fix**: 6 hours to implement OR 2 hours to remove legacy UI

---

## 5. AGENT OPERATIONS (✅ Accessible - Web Only)

| Feature | Implementation | CLI Access | Web/API Access | UI Access |
|---------|---------------|------------|----------------|-----------|
| List agents | src/web/routes/agents.py:91 | ❌ No CLI | ✅ `GET /api/agents` | ✅ React UI |
| Get agent details | src/web/routes/agents.py:128 | ❌ No CLI | ✅ `GET /api/agents/{id}` | ✅ React UI |
| Get job agent logs | src/web/routes/agents.py:168 | ❌ No CLI | ✅ `GET /api/jobs/{jid}/logs/{agent}` | ✅ React UI |
| Get all agent logs | src/web/routes/agents.py:237 | ❌ No CLI | ✅ `GET /api/agents/{id}/logs` | ✅ React UI |

**Note**: These endpoints work but:
- No CLI equivalent
- No agent health/status monitoring
- Cannot test individual agents

---

## 6. WORKFLOW OPERATIONS (✅ Accessible - Both CLI & Web)

| Feature | Implementation | CLI Access | Web/API Access | UI Access |
|---------|---------------|------------|----------------|-----------|
| List workflows | src/web/routes/workflows.py:30 | ⚠️ Via templates | ✅ `GET /api/workflows` | ✅ React UI |
| Get workflow details | src/web/routes/workflows.py:65 | ⚠️ Via templates | ✅ `GET /api/workflows/{id}` | ✅ React UI |

**Gap**: Advanced workflow features exist in unmounted MCP adapter:
- `GET /mcp/workflows/profiles` - 🔴 NOT MOUNTED
- `GET /mcp/workflows/visual/{profile}` - 🔴 NOT MOUNTED  
- `GET /mcp/workflows/{profile}/metrics` - 🔴 NOT MOUNTED
- `POST /mcp/workflows/{profile}/reset` - 🔴 NOT MOUNTED

---

## 7. VISUALIZATION & MONITORING (⚠️ Fragmented Access)

### Workflow Visualization

| Feature | Implementation | CLI Access | Web/API Access | UI Access |
|---------|---------------|------------|----------------|-----------|
| List workflow profiles | ucop_cli.py:125 | ✅ `ucop viz workflows` | ⚠️ Partial: `/api/visualization/workflows` | ⚠️ Partial |
| Generate workflow graph | ucop_cli.py:156 | ✅ `ucop viz graph` | ⚠️ Partial: `/api/visualization/workflows/{id}` | ⚠️ Partial |
| Get workflow metrics | ucop_cli.py:183 | ✅ `ucop viz metrics` | ⚠️ Partial: `/api/visualization/workflows/{id}/render` | ❌ No UI |

### Agent Monitoring

| Feature | Implementation | CLI Access | Web/API Access | UI Access |
|---------|---------------|------------|----------------|-----------|
| Show agent status | ucop_cli.py:218 | ✅ `ucop viz agents` | ❌ No endpoint | ❌ No UI |
| Monitor agents | src/web/routes/visualization.py:191 | ❌ No CLI | ✅ `GET /api/monitoring/agents` | ❌ No UI |
| Agent metrics | src/web/routes/visualization.py:217 | ❌ No CLI | ✅ `GET /api/monitoring/agents/{id}` | ❌ No UI |

### Flow Analysis (❌ CLI Only - No Web Access)

| Feature | Implementation | CLI Access | Web/API Access | UI Access |
|---------|---------------|------------|----------------|-----------|
| Show active flows | ucop_cli.py:248 | ✅ `ucop viz flows` | ❌ No endpoint* | ❌ No UI |
| Detect bottlenecks | ucop_cli.py:277 | ✅ `ucop viz bottlenecks` | ❌ No endpoint* | ❌ No UI |

\* **Endpoints exist in unmounted MCP adapter:**
- `GET /mcp/flows/realtime` - 🔴 NOT MOUNTED
- `GET /mcp/flows/history/{correlation_id}` - 🔴 NOT MOUNTED
- `GET /mcp/flows/bottlenecks` - 🔴 NOT MOUNTED

### System Monitoring

| Feature | Implementation | CLI Access | Web/API Access | UI Access |
|---------|---------------|------------|----------------|-----------|
| System health | src/web/app.py:127 | ❌ No CLI | ✅ `GET /api/system/health` | ⚠️ No dashboard |
| System metrics | src/web/routes/visualization.py:295 | ❌ No CLI | ✅ `GET /api/monitoring/system` | ❌ No UI |
| Job metrics | src/web/routes/visualization.py:339 | ❌ No CLI | ✅ `GET /api/monitoring/jobs/{id}/metrics` | ❌ No UI |

**Impact**: Monitoring capabilities split across CLI and web - no unified view  
**Effort to Fix**: 8-10 hours to implement missing endpoints + 20 hours for UI dashboard

---

## 8. DEBUG CAPABILITIES (⚠️ Basic Web, Full CLI)

### Basic Debug (✅ Web API Exists, No UI)

| Feature | Implementation | CLI Access | Web/API Access | UI Access |
|---------|---------------|------------|----------------|-----------|
| Create breakpoint | src/web/routes/debug.py:38 | ⚠️ Via `viz debug` | ✅ `POST /api/debug/breakpoints` | ❌ No UI |
| Delete breakpoint | src/web/routes/debug.py:85 | ⚠️ Via `viz debug` | ✅ `DELETE /api/debug/breakpoints/{id}` | ❌ No UI |
| List breakpoints | src/web/routes/debug.py:124 | ⚠️ Via `viz debug` | ✅ `GET /api/debug/breakpoints` | ❌ No UI |
| Debug step | src/web/routes/debug.py:194 | ⚠️ Via `viz debug` | ✅ `POST /api/debug/step` | ❌ No UI |
| Get debug state | src/web/routes/debug.py:228 | ⚠️ Via `viz debug` | ✅ `GET /api/debug/state/{job_id}` | ❌ No UI |

### Advanced Debug (❌ CLI Only - Endpoints Exist but NOT MOUNTED)

| Feature | Implementation | CLI Access | Web/API Access | UI Access |
|---------|---------------|------------|----------------|-----------|
| Create debug session | ucop_cli.py:306 | ✅ `ucop viz debug create` | 🔴 `/mcp/debug/sessions` (unmounted) | ❌ No UI |
| Get debug session | - | ✅ `ucop viz debug` | 🔴 `/mcp/debug/sessions/{id}` (unmounted) | ❌ No UI |
| Add session breakpoint | ucop_cli.py:306 | ✅ `ucop viz debug breakpoint` | 🔴 `/mcp/debug/breakpoints` (unmounted) | ❌ No UI |
| Remove breakpoint | - | ❌ No CLI | 🔴 `/mcp/debug/sessions/{id}/breakpoints/{bid}` (unmounted) | ❌ No UI |
| Step through session | - | ❌ No CLI | 🔴 `/mcp/debug/sessions/{id}/step` (unmounted) | ❌ No UI |
| Continue session | - | ❌ No CLI | 🔴 `/mcp/debug/sessions/{id}/continue` (unmounted) | ❌ No UI |
| Get workflow trace | - | ❌ No CLI | 🔴 `/mcp/debug/workflows/{id}/trace` (unmounted) | ❌ No UI |

**Impact**: Cannot debug production issues from web - must SSH and use CLI  
**Effort to Fix**: 2 hours to mount router + 16-20 hours to build debug UI

---

## 9. WEBSOCKET CAPABILITIES (✅ Implemented, Underutilized)

| Feature | Implementation | Status | Used By |
|---------|---------------|--------|---------|
| Per-job updates | src/web/websocket_handlers.py | ✅ ACTIVE | React UI (partial) |
| Visual updates | src/web/websocket_handlers.py | ✅ ACTIVE | React UI (partial) |
| Agent monitoring | src/web/websocket_handlers.py | ✅ ACTIVE | ❌ Not used |
| System monitoring | src/web/routes/visualization.py:242 | ✅ ACTIVE | ❌ Not used |

**Gap**: WebSockets work but aren't fully integrated into UI  
**Effort to Fix**: 8-12 hours to build realtime monitoring dashboard

---

## 10. TEMPLATE MANAGEMENT (✅ CLI Only)

| Feature | Implementation | CLI Access | Web/API Access | UI Access |
|---------|---------------|------------|----------------|-----------|
| List templates | ucop_cli.py:349 | ✅ `ucop list-templates` | ❌ No endpoint | ❌ No UI |
| Get template details | ucop_cli.py:349 | ✅ `ucop list-templates` | ❌ No endpoint | ❌ No UI |

**Impact**: Web users cannot see available templates  
**Effort to Fix**: 3-4 hours to add `/api/templates` endpoint

---

## 11. AGENT INVENTORY (38 Agents - All Accessible via Workflows)

All agents work when invoked by workflows but cannot be tested individually.

### Research Agents (10)
✅ api_search, blog_search, docs_search, kb_search, tutorial_search, topic_identification, trends_research, content_intelligence, competitor_analysis, duplication_check

### Content Agents (7)
✅ outline_creation, introduction_writer, section_writer, conclusion_writer, supplementary_content, content_assembly, quality_gate

### Code Agents (6)
✅ code_generation, code_extraction, code_validation, code_splitting, api_validator, license_injection

### Publishing Agents (5)
✅ file_writer, frontmatter_enhanced, link_validation, gist_readme, gist_upload

### SEO Agents (3)
✅ keyword_extraction, keyword_injection, seo_metadata

### Ingestion Agents (5)
✅ api_ingestion, blog_ingestion, docs_ingestion, kb_ingestion, tutorial_ingestion

### Support Agents (3)
✅ model_selection, error_recovery, validation

**Gap**: No way to test individual agents outside workflows  
**Effort to Fix**: 12-15 hours to build agent testing framework

---

## SUMMARY TABLE

| Category | Total Features | CLI Only | Web Only | Both | Unmounted | Broken UI |
|----------|----------------|----------|----------|------|-----------|-----------|
| Checkpoint Mgmt | 4 | 4 | 0 | 0 | 0 | 0 |
| Configuration | 5 | 5 | 0 | 0 | 5 (unmounted) | 0 |
| Job Management | 8 | 2 | 3 | 3 | 6 (unmounted) | 6 |
| Agent Ops | 4 | 0 | 4 | 0 | 2 (unmounted) | 0 |
| Workflows | 2 | 0 | 2 | 0 | 4 (unmounted) | 0 |
| Visualization | 10 | 6 | 3 | 1 | 3 (unmounted) | 0 |
| Debug | 12 | 4 | 5 | 3 | 7 (unmounted) | 0 |
| Templates | 2 | 2 | 0 | 0 | 0 | 0 |
| Agents | 38 | 0 | 0 | 38 | 0 | 0 |
| WebSockets | 4 | 0 | 4 | 0 | 0 | 2 (unused) |
| **TOTAL** | **89** | **23** | **21** | **45** | **27** | **8** |

---

## CRITICAL BLOCKERS (Must Fix for Production)

1. **Mount MCP Web Adapter** [2 hours]
   - 27 unmounted endpoints become accessible
   - React UI stops getting 404 errors

2. **Implement Missing Job Endpoints** [6 hours]
   - Fix 6 broken legacy UI features
   - Or remove legacy UI completely

3. **Add Checkpoint REST API** [8 hours]
   - Web users can manage job checkpoints
   - Critical for job recovery

4. **Expose Config Endpoints** [2 hours]
   - Already in MCP adapter, just mount it
   - Enables runtime config inspection

5. **Build Basic Monitoring Dashboard** [20 hours]
   - Utilize existing metrics endpoints
   - Show system health, agent status

**Total Critical Path**: ~40 hours to make project production-ready

---

## ACCESS PATTERNS SUMMARY

### ✅ WORKS WELL
- Job creation, listing, control (CLI + Web + UI)
- Agent execution via workflows
- Basic agent/workflow queries
- System health checks

### ⚠️ PARTIALLY WORKS
- Visualization (CLI has more features than web)
- Debug capabilities (basic web, advanced CLI only)
- Monitoring (endpoints exist, UI missing)

### ❌ DOESN'T WORK
- Checkpoint management from web
- Configuration inspection from web (endpoints unmounted)
- Flow analysis from web (endpoints unmounted)
- Individual agent testing
- Template listing from web
- Advanced debugging from web
- Legacy UI artifact viewing

### 🔴 IMPLEMENTED BUT INACCESSIBLE
- 27 MCP adapter endpoints (exist in code, not mounted)
- 6 job detail endpoints (expected by UI, never implemented)
- Advanced debug session management
- Flow/bottleneck analysis APIs

---

**Document Version**: 1.0  
**Generated**: November 15, 2025  
**Purpose**: Quick reference for feature accessibility status
