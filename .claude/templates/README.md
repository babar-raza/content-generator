# Claude Code Templates

This directory contains reusable templates for the content-generator project.

## Available Templates

### `taskcard.md`
Standard taskcard template used for all task tracking and implementation.

**Usage**: Say "use the taskcard template" or "create a taskcard" and Claude will automatically use this template.

---

## Adding New Templates

1. Create a new `.md` file in this directory
2. Add reference to this README
3. Use descriptive names (e.g., `pr-description.md`, `incident-report.md`)

## Template Variables

Templates may use placeholder variables that Claude will fill in:
- `{TASK_ID}` - Task identifier
- `{DATE}` - Current date
- `{DESCRIPTION}` - Task description
- etc.

---

**Last Updated**: 2025-12-04
