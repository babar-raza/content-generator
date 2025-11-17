# Archive Directory

This directory contains files that have been archived as part of the consolidation effort.

## Purpose

Files in this archive are no longer actively used in the production system but are preserved for:
- Historical reference
- Understanding evolution of the codebase
- Potential recovery of specific implementations if needed

## DO NOT USE

**These files are not maintained and should not be imported or referenced by active code.**

## Archived Files

### Web Applications (archive/web/)

#### app_unified.py
- **Date Archived**: 2025-11-13
- **Reason**: Features consolidated into `src/web/app.py`
- **Replacement**: Use `src/web/app.py`
- **Historical Context**: Provided unified engine integration for web interface using Jinja2 templates
- **Key Features Migrated**: 
  - Unified engine integration
  - Job generation endpoints
  - Batch processing
  - Template listing

#### app_integrated.py
- **Date Archived**: 2025-11-13
- **Reason**: Features consolidated into `src/web/app.py`
- **Replacement**: Use `src/web/app.py`
- **Historical Context**: Combined job UI with visual orchestration features
- **Key Features Migrated**:
  - Visual workflow editor
  - WebSocket-based real-time updates
  - Debugging interface
  - Agent flow monitoring
  - Job management UI

### HTML Templates (archive/web/templates/)

All Jinja2 HTML templates have been archived as React is now the primary UI framework.

#### dashboard.html
- **Date Archived**: 2025-11-13
- **Reason**: React UI is primary interface
- **Replacement**: React components in `src/web/static/src/`
- **Historical Context**: Server-side rendered dashboard

#### dashboard_integrated.html
- **Date Archived**: 2025-11-13
- **Reason**: React UI is primary interface
- **Replacement**: React components in `src/web/static/src/`
- **Historical Context**: Integrated dashboard with orchestration

#### job_detail.html
- **Date Archived**: 2025-11-13
- **Reason**: React UI is primary interface
- **Replacement**: React components in `src/web/static/src/`
- **Historical Context**: Job detail view

#### job_detail_enhanced.html
- **Date Archived**: 2025-11-13
- **Reason**: React UI is primary interface
- **Replacement**: React components in `src/web/static/src/`
- **Historical Context**: Enhanced job detail view with metrics

#### orchestration_base.html
- **Date Archived**: 2025-11-13
- **Reason**: React UI is primary interface
- **Replacement**: React components in `src/web/static/src/`
- **Historical Context**: Base template for orchestration UI

#### test.html
- **Date Archived**: 2025-11-13
- **Reason**: React UI is primary interface
- **Replacement**: React components in `src/web/static/src/`
- **Historical Context**: Test page for UI development

## Current System

The active web application is located at:
- **Main App**: `src/web/app.py`
- **React UI**: `src/web/static/src/`
- **MCP Protocol**: Endpoints accessible via `/api/mcp/*`
- **Visualization**: Endpoints accessible via `/api/visualization/*`

## Migration Notes

All functionality from archived web apps has been consolidated into `src/web/app.py`:
- React-based UI (no Jinja2 templates)
- MCP protocol endpoints for workflow operations
- RESTful API for job management
- WebSocket support for real-time updates
- Debugging and monitoring endpoints

## Restoration

If you need to reference these files:
1. They are preserved with their original filenames
2. Each file has an archival comment at the top
3. Do NOT copy them back to src/ without updating imports and dependencies
4. The current system (`src/web/app.py`) is the authoritative implementation

## Questions

If you have questions about:
- Why a specific file was archived: See "Reason" above
- How to implement a feature from an archived file: Check `src/web/app.py` for the current implementation
- Whether an archived file can be restored: Consult the team lead before making changes
