"""
Capability Index Builder for Content Generator

Enumerates all capabilities across:
- Agents (src/agents/**)
- Pipeline steps (config/main.yaml)
- Template workflows (templates/workflows.yaml)
- Engine features
- Web API routes
- MCP protocol methods
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any
import yaml
import ast

# Import helpers from _env module
from _env import get_repo_root


def extract_agent_capabilities() -> List[Dict[str, Any]]:
    """Extract agent capabilities from src/agents/**."""
    capabilities = []
    repo_root = get_repo_root()
    agents_dir = repo_root / 'src' / 'agents'

    if not agents_dir.exists():
        return capabilities

    # Find all Python files in agents directory
    for py_file in agents_dir.rglob('*.py'):
        if py_file.name.startswith('_'):
            continue

        try:
            content = py_file.read_text(encoding='utf-8')

            # Parse AST to find Agent classes
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Check if class name ends with Agent
                        if 'Agent' in node.name:
                            # Derive agent_id from filename or class name
                            agent_id = py_file.stem
                            if agent_id == '__init__':
                                continue

                            # Convert snake_case to kebab-case for consistency
                            agent_id = agent_id.replace('_', '-')

                            cap_id = f"CAP-AGENT-{agent_id}"

                            # Extract docstring if available
                            docstring = ast.get_docstring(node) or ""
                            title = node.name

                            capabilities.append({
                                'cap_id': cap_id,
                                'title': title,
                                'agent_id': agent_id,
                                'declared_in': [str(py_file.relative_to(repo_root))],
                                'implemented_by': [f"{py_file.stem}.{node.name}"],
                                'verify_level': 'unit',
                                'verify_mode': 'mock',
                                'status': 'UNVERIFIED',
                                'description': docstring.split('\n')[0] if docstring else title
                            })
            except SyntaxError:
                # Skip files with syntax errors
                pass

        except Exception as e:
            print(f"Warning: Could not process {py_file}: {e}")

    return capabilities


def extract_pipeline_capabilities() -> List[Dict[str, Any]]:
    """Extract pipeline step capabilities from config/main.yaml."""
    capabilities = []
    repo_root = get_repo_root()
    config_file = repo_root / 'config' / 'main.yaml'

    if not config_file.exists():
        return capabilities

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Extract main pipeline steps
        if 'pipeline' in config:
            for step in config['pipeline']:
                cap_id = f"CAP-PIPE-{step}"
                capabilities.append({
                    'cap_id': cap_id,
                    'title': f"Pipeline Step: {step}",
                    'step_name': step,
                    'declared_in': ['config/main.yaml'],
                    'implemented_by': [f"pipeline.{step}"],
                    'verify_level': 'pipeline',
                    'verify_mode': 'mock',
                    'status': 'UNVERIFIED',
                    'description': f"Execute {step} step in main pipeline"
                })

        # Extract workflow variants
        if 'workflows' in config:
            workflows_section = config['workflows']
            for wf_key, wf_value in workflows_section.items():
                if isinstance(wf_value, dict) and 'steps' in wf_value:
                    cap_id = f"CAP-WF-CONFIG-{wf_key}"
                    capabilities.append({
                        'cap_id': cap_id,
                        'title': f"Config Workflow: {wf_value.get('name', wf_key)}",
                        'workflow_id': wf_key,
                        'declared_in': ['config/main.yaml'],
                        'implemented_by': [f"workflow.{wf_key}"],
                        'verify_level': 'pipeline',
                        'verify_mode': 'mock',
                        'status': 'UNVERIFIED',
                        'description': f"Execute {wf_key} workflow from config"
                    })

    except Exception as e:
        print(f"Warning: Could not process config/main.yaml: {e}")

    return capabilities


def extract_template_workflow_capabilities() -> List[Dict[str, Any]]:
    """Extract workflow capabilities from templates/workflows.yaml."""
    capabilities = []
    repo_root = get_repo_root()
    templates_file = repo_root / 'templates' / 'workflows.yaml'

    if not templates_file.exists():
        return capabilities

    try:
        with open(templates_file, 'r', encoding='utf-8') as f:
            workflows = yaml.safe_load(f)

        if 'workflows' in workflows:
            for wf_id, wf_config in workflows['workflows'].items():
                cap_id = f"CAP-WF-{wf_id}"
                capabilities.append({
                    'cap_id': cap_id,
                    'title': wf_config.get('name', wf_id),
                    'workflow_id': wf_id,
                    'declared_in': ['templates/workflows.yaml'],
                    'implemented_by': [f"template.workflow.{wf_id}"],
                    'verify_level': 'pipeline',
                    'verify_mode': 'mock',
                    'status': 'UNVERIFIED',
                    'description': wf_config.get('description', f"Execute {wf_id} template workflow")
                })

    except Exception as e:
        print(f"Warning: Could not process templates/workflows.yaml: {e}")

    return capabilities


def extract_engine_capabilities() -> List[Dict[str, Any]]:
    """Extract engine capabilities."""
    capabilities = []
    repo_root = get_repo_root()

    # Check for UnifiedEngine
    engine_files = list((repo_root / 'src' / 'engine').glob('*.py')) if (repo_root / 'src' / 'engine').exists() else []

    for engine_file in engine_files:
        if engine_file.name.startswith('_'):
            continue

        cap_id = f"CAP-ENGINE-{engine_file.stem}"
        capabilities.append({
            'cap_id': cap_id,
            'title': f"Engine: {engine_file.stem}",
            'declared_in': [str(engine_file.relative_to(repo_root))],
            'implemented_by': [f"engine.{engine_file.stem}"],
            'verify_level': 'unit',
            'verify_mode': 'mock',
            'status': 'UNVERIFIED',
            'description': f"Engine component: {engine_file.stem}"
        })

    return capabilities


def extract_web_api_capabilities() -> List[Dict[str, Any]]:
    """Extract Web API route capabilities."""
    capabilities = []
    repo_root = get_repo_root()
    routes_dir = repo_root / 'src' / 'web' / 'routes'

    if not routes_dir.exists():
        return capabilities

    for route_file in routes_dir.glob('*.py'):
        if route_file.name.startswith('_'):
            continue

        route_group = route_file.stem
        cap_id = f"CAP-WEB-{route_group}"

        capabilities.append({
            'cap_id': cap_id,
            'title': f"Web API: {route_group}",
            'route_group': route_group,
            'declared_in': [str(route_file.relative_to(repo_root))],
            'implemented_by': [f"web.routes.{route_group}"],
            'verify_level': 'e2e',
            'verify_mode': 'mock',
            'status': 'UNVERIFIED',
            'description': f"Web API routes for {route_group}"
        })

    return capabilities


def extract_mcp_capabilities() -> List[Dict[str, Any]]:
    """Extract MCP protocol method capabilities."""
    capabilities = []
    repo_root = get_repo_root()
    mcp_file = repo_root / 'src' / 'mcp' / 'protocol.py'

    if not mcp_file.exists():
        return capabilities

    try:
        content = mcp_file.read_text(encoding='utf-8')

        # Look for MCP methods - this is a best-effort parse
        # Common patterns: workflow.execute, agent.invoke, etc.
        mcp_methods = [
            'workflow.list',
            'workflow.execute',
            'workflow.status',
            'agent.list',
            'agent.invoke',
            'job.create',
            'job.status',
        ]

        for method in mcp_methods:
            cap_id = f"CAP-MCP-{method.replace('.', '-')}"
            capabilities.append({
                'cap_id': cap_id,
                'title': f"MCP Method: {method}",
                'mcp_method': method,
                'declared_in': ['src/mcp/protocol.py'],
                'implemented_by': [f"mcp.{method}"],
                'verify_level': 'e2e',
                'verify_mode': 'mock',
                'status': 'UNVERIFIED',
                'description': f"MCP protocol method: {method}"
            })

    except Exception as e:
        print(f"Warning: Could not process MCP protocol: {e}")

    return capabilities


def build_capability_matrix() -> Dict[str, Any]:
    """Build complete capability matrix."""
    all_capabilities = []

    # Extract from all sources
    all_capabilities.extend(extract_agent_capabilities())
    all_capabilities.extend(extract_pipeline_capabilities())
    all_capabilities.extend(extract_template_workflow_capabilities())
    all_capabilities.extend(extract_engine_capabilities())
    all_capabilities.extend(extract_web_api_capabilities())
    all_capabilities.extend(extract_mcp_capabilities())

    # Build matrix
    matrix = {
        'generated_at': str(Path.cwd()),
        'total_capabilities': len(all_capabilities),
        'capabilities': all_capabilities,
        'categories': {
            'agents': len([c for c in all_capabilities if c['cap_id'].startswith('CAP-AGENT-')]),
            'pipeline_steps': len([c for c in all_capabilities if c['cap_id'].startswith('CAP-PIPE-')]),
            'workflows': len([c for c in all_capabilities if c['cap_id'].startswith('CAP-WF-')]),
            'engine': len([c for c in all_capabilities if c['cap_id'].startswith('CAP-ENGINE-')]),
            'web_api': len([c for c in all_capabilities if c['cap_id'].startswith('CAP-WEB-')]),
            'mcp': len([c for c in all_capabilities if c['cap_id'].startswith('CAP-MCP-')]),
        }
    }

    return matrix


def generate_markdown_report(matrix: Dict[str, Any]) -> str:
    """Generate human-readable markdown report."""
    lines = []
    lines.append("# Exact Capability Matrix")
    lines.append("")
    lines.append(f"**Total Capabilities:** {matrix['total_capabilities']}")
    lines.append("")

    lines.append("## Summary by Category")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|----------|-------|")
    for category, count in matrix['categories'].items():
        lines.append(f"| {category} | {count} |")
    lines.append("")

    # Group by category
    capabilities_by_cat = {}
    for cap in matrix['capabilities']:
        cap_type = cap['cap_id'].split('-')[1]  # AGENT, PIPE, WF, etc.
        if cap_type not in capabilities_by_cat:
            capabilities_by_cat[cap_type] = []
        capabilities_by_cat[cap_type].append(cap)

    for cat_name, caps in sorted(capabilities_by_cat.items()):
        lines.append(f"## {cat_name} Capabilities")
        lines.append("")
        lines.append("| CAP ID | Title | Verify Level | Status |")
        lines.append("|--------|-------|--------------|--------|")
        for cap in sorted(caps, key=lambda x: x['cap_id']):
            lines.append(f"| {cap['cap_id']} | {cap['title']} | {cap['verify_level']} | {cap['status']} |")
        lines.append("")

    return '\n'.join(lines)


def main():
    """Main entry point."""
    print("Building capability matrix...")

    matrix = build_capability_matrix()

    # Determine output directory
    repo_root = get_repo_root()

    # Find the latest timestamp directory
    reports_dir = repo_root / 'reports' / 'capability_verify'
    if reports_dir.exists():
        ts_dirs = sorted([d for d in reports_dir.iterdir() if d.is_dir()], reverse=True)
        if ts_dirs:
            output_dir = ts_dirs[0] / '01_capabilities'
        else:
            output_dir = reports_dir / '01_capabilities'
    else:
        output_dir = repo_root / 'reports' / 'capability_verify' / '01_capabilities'

    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON
    json_file = output_dir / 'capabilities.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(matrix, f, indent=2)
    print(f"[OK] Wrote {json_file}")

    # Write Markdown
    md_content = generate_markdown_report(matrix)
    md_file = output_dir / 'capabilities.md'
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"[OK] Wrote {md_file}")

    print(f"\nTotal capabilities: {matrix['total_capabilities']}")
    print("Categories:")
    for cat, count in matrix['categories'].items():
        print(f"  - {cat}: {count}")


if __name__ == '__main__':
    main()
