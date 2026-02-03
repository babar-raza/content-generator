# Production Quality Gates

**Version**: 2.0
**Effective Date**: 2026-02-03
**Status**: Active

## Overview

This document defines the quality gate criteria for content generation outputs in production. The quality gate is designed to ensure outputs meet minimum standards for structure, completeness, grounding, and safety before being deployed at scale.

## Historical Context

**Version 1.0** (deprecated) used a single hard threshold:
- Minimum output size: 2048 bytes
- No structural or content quality checks
- Result: Brittle failures on structurally sound outputs (e.g., 2032 bytes failed)

**Version 2.0** (current) uses a multi-dimensional rubric that evaluates:
- Frontmatter validity
- Structural completeness
- Content grounding in retrieval evidence
- Size as a soft requirement with flexible thresholds
- Safety guardrails

## Quality Rubric v2.0

An output **PASSES** quality gates if it meets **ALL** of the following criteria:

### A) Frontmatter (REQUIRED)
- **Criterion**: Valid YAML frontmatter between `---` delimiters
- **Check**: First line must be `---`, YAML block must end with `---`
- **Failure modes**:
  - Missing frontmatter
  - Malformed YAML
  - Fenced code block frontmatter (```yaml at top)

### B) Structure (REQUIRED)
- **Criterion**: Minimum 3 markdown headings (`#`, `##`, `###`, etc.)
- **Check**: Count heading markers in content
- **Rationale**: Indicates organized, multi-section content

### C) Completeness (REQUIRED)
- **Criterion**: At least 2 distinct content sections after introduction
- **Check**: Count sections between headings (excluding frontmatter)
- **Rationale**: Ensures content goes beyond a single intro paragraph

### D) Grounding (REQUIRED)
- **Criterion**: Minimum 2 references or mentions tied to retrieval
- **Check**: Detect citation patterns, quoted terms, or explicit references
- **Rationale**: Verifies RAG retrieval is being used (not pure generation)
- **Examples**:
  - Quoted terms: "AI agents", "automation"
  - Citations: (Source: X), [1], mentioned in Y
  - Named references: UCOP Research Team, Aspose

### E) Size (SOFT REQUIREMENT)
- **Hard minimum**: 1800 bytes
- **Target**: 2200+ bytes
- **Behavior**:
  - `< 1800 bytes`: **FAIL** (too short, likely incomplete)
  - `1800-2199 bytes`: **PASS** if A-D criteria met (acceptable)
  - `≥ 2200 bytes`: **PASS** (ideal)
- **Rationale**: Size alone is not sufficient, but extreme brevity indicates issues

### F) Safety (REQUIRED)
- **Criterion**: No fenced frontmatter blocks (```yaml at top)
- **Check**: Detect ` ```yaml` followed by frontmatter-style content
- **Rationale**: Prevents malformed frontmatter that breaks parsers

## Implementation

### Scorer: `tools/quality_gate.py`

```python
def evaluate_output(output_path: str) -> dict
```

**Input**: Path to a markdown output file
**Output**: JSON verdict with structure:
```json
{
  "pass": true/false,
  "reasons": ["criterion_a_pass", "criterion_b_pass", ...],
  "failures": ["criterion_x_fail", ...],
  "metrics": {
    "has_frontmatter": true,
    "heading_count": 4,
    "section_count": 3,
    "reference_count": 2,
    "size_bytes": 2032,
    "has_fenced_frontmatter": false
  }
}
```

### Batch Runner: `tools/quality_gate_runner.py`

```python
def run_quality_audit(jobs: List[dict], output_dir: str) -> dict
```

**Input**: List of job records (from jobs.jsonl) with output paths
**Output**: Aggregated results with pass/fail counts and details

## Upgrade Path from v1.0

For existing deployments using v1.0:
1. **Backtest**: Run v2.0 rubric on v1.0 pilot outputs to validate
2. **Compare**: Ensure v2.0 does NOT reduce overall quality standards
3. **Deploy**: Replace v1.0 quality check with v2.0 scorer
4. **Monitor**: Track pass rates and failure distributions

## Success Criteria for Production

- **Pilot phase**: 10/10 outputs must pass quality gates
- **Retrieval active**: 100% of outputs show grounding (criterion D)
- **No regression**: v2.0 should pass outputs that v1.0 passed
- **Reduced brittleness**: v2.0 should pass structurally sound outputs that v1.0 failed on size alone

## Maintenance

This document and the quality rubric should be reviewed:
- After every pilot run with failures
- Quarterly for quality standard updates
- When model or retrieval systems change

**Owner**: Platform Engineering
**Reviewers**: Product, QA, Data Science
