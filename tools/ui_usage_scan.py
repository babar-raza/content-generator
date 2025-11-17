#!/usr/bin/env python3
"""
UI and Runtime Usage Scanner
Analyzes import patterns, entry points, and module usage across the codebase.
"""

import os
import re
import ast
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple


def scan_imports(file_path: Path) -> List[str]:
    """Extract all import statements from a Python file."""
    imports = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                    for alias in node.names:
                        imports.append(f"{node.module}.{alias.name}")
    except Exception:
        # Fall back to regex for problematic files
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            imports.extend(re.findall(r'^from\s+([\w.]+)\s+import', content, re.MULTILINE))
            imports.extend(re.findall(r'^import\s+([\w.]+)', content, re.MULTILINE))
        except Exception:
            pass
    
    return imports


def find_references(content: str, pattern: str) -> int:
    """Count references to a pattern in file content."""
    return len(re.findall(pattern, content))


def scan_directory(root_dir: Path, target_dirs: List[str]) -> Dict:
    """Scan directories for module usage patterns."""
    results = {
        'imports': defaultdict(list),
        'references': defaultdict(list),
        'files': defaultdict(list),
        'entry_points': [],
        'ui_apps': [],
        'templates': []
    }
    
    # Find entry points
    for entry in ['start_web.py', 'start_api.py', 'ucop_cli.py', 'job_cli.py', 'src/main.py']:
        entry_path = root_dir / entry
        if entry_path.exists():
            results['entry_points'].append(str(entry_path))
    
    # Find UI apps
    web_dir = root_dir / 'src' / 'web'
    if web_dir.exists():
        for app_file in web_dir.glob('app*.py'):
            results['ui_apps'].append(str(app_file))
    
    # Find templates
    templates_dir = root_dir / 'src' / 'web' / 'templates'
    if templates_dir.exists():
        for template in templates_dir.glob('*.html'):
            results['templates'].append(str(template))
    
    # Scan all Python files
    for py_file in root_dir.rglob('*.py'):
        if 'test' in str(py_file) or '__pycache__' in str(py_file):
            continue
            
        rel_path = py_file.relative_to(root_dir)
        
        # Track files in target directories
        for target in target_dirs:
            if target in str(rel_path):
                results['files'][target].append(str(rel_path))
        
        # Extract imports
        imports = scan_imports(py_file)
        for imp in imports:
            for target in target_dirs:
                if target in imp:
                    results['imports'][target].append({
                        'file': str(rel_path),
                        'import': imp
                    })
        
        # Look for direct references in content
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for target in target_dirs:
                # Check for references
                refs = find_references(content, rf'\b{target.replace("/", ".")}\b')
                if refs > 0:
                    results['references'][target].append({
                        'file': str(rel_path),
                        'count': refs
                    })
        except Exception:
            pass
    
    return results


def analyze_ui_implementations(root_dir: Path) -> Dict:
    """Analyze different UI implementations."""
    web_dir = root_dir / 'src' / 'web'
    analysis = {
        'apps': [],
        'routes': [],
        'templates': [],
        'static_ui': None
    }
    
    # Analyze app files
    for app_file in web_dir.glob('app*.py'):
        app_info = {
            'file': app_file.name,
            'path': str(app_file),
            'size': app_file.stat().st_size,
            'routes': [],
            'imports': [],
            'features': []
        }
        
        try:
            with open(app_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find routes
            app_info['routes'] = re.findall(r'@app\.(get|post|put|delete|websocket)\("([^"]+)"', content)
            
            # Find key imports
            if 'visualization' in content:
                app_info['features'].append('visualization')
            if 'WebSocket' in content:
                app_info['features'].append('websocket')
            if 'Jinja2Templates' in content:
                app_info['features'].append('jinja_templates')
            if 'StaticFiles' in content:
                app_info['features'].append('static_files')
            if 'mcp' in content.lower():
                app_info['features'].append('mcp')
                
        except Exception:
            pass
        
        analysis['apps'].append(app_info)
    
    # Analyze routes
    routes_dir = web_dir / 'routes'
    if routes_dir.exists():
        for route_file in routes_dir.glob('*.py'):
            if route_file.name != '__init__.py':
                analysis['routes'].append(route_file.name)
    
    # Analyze templates
    templates_dir = web_dir / 'templates'
    if templates_dir.exists():
        for template in templates_dir.glob('*.html'):
            template_info = {
                'name': template.name,
                'size': template.stat().st_size
            }
            analysis['templates'].append(template_info)
    
    # Check for React UI
    static_dir = web_dir / 'static'
    if static_dir.exists():
        vite_config = static_dir / 'vite.config.ts'
        package_json = static_dir / 'package.json'
        
        if vite_config.exists() or package_json.exists():
            analysis['static_ui'] = {
                'type': 'React/Vite',
                'path': str(static_dir),
                'has_vite': vite_config.exists(),
                'has_package': package_json.exists()
            }
    
    return analysis


def main():
    """Main analysis function."""
    root_dir = Path('/mnt/data/project')
    
    target_dirs = [
        'src/web',
        'src/realtime',
        'src/mesh',
        'src/visualization',
        'src/engine',
        'src/orchestration'
    ]
    
    print("Scanning repository...")
    results = scan_directory(root_dir, target_dirs)
    
    print("\n" + "="*80)
    print("ENTRY POINTS")
    print("="*80)
    for ep in results['entry_points']:
        print(f"  - {ep}")
    
    print("\n" + "="*80)
    print("UI APPLICATIONS")
    print("="*80)
    for app in results['ui_apps']:
        print(f"  - {app}")
    
    print("\n" + "="*80)
    print("HTML TEMPLATES")
    print("="*80)
    for template in results['templates']:
        print(f"  - {template}")
    
    print("\n" + "="*80)
    print("MODULE FILES COUNT")
    print("="*80)
    for target in sorted(results['files'].keys()):
        count = len(results['files'][target])
        print(f"  {target}: {count} files")
    
    print("\n" + "="*80)
    print("IMPORT USAGE")
    print("="*80)
    for target in sorted(results['imports'].keys()):
        imports = results['imports'][target]
        print(f"\n  {target}: {len(imports)} imports")
        
        # Group by importing file
        by_file = defaultdict(list)
        for imp in imports:
            by_file[imp['file']].append(imp['import'])
        
        for file in sorted(by_file.keys())[:5]:  # Show top 5
            print(f"    {file}: {len(by_file[file])} imports")
    
    print("\n" + "="*80)
    print("UI IMPLEMENTATION ANALYSIS")
    print("="*80)
    ui_analysis = analyze_ui_implementations(root_dir)
    
    print("\nApp Files:")
    for app in ui_analysis['apps']:
        print(f"\n  {app['file']} ({app['size']} bytes)")
        print(f"    Routes: {len(app['routes'])}")
        print(f"    Features: {', '.join(app['features']) if app['features'] else 'none'}")
        if app['routes'][:3]:
            for method, route in app['routes'][:3]:
                print(f"      {method.upper()}: {route}")
    
    print("\n\nRoutes Modules:")
    for route in ui_analysis['routes']:
        print(f"  - {route}")
    
    print("\n\nTemplates:")
    for template in sorted(ui_analysis['templates'], key=lambda x: x['name']):
        print(f"  - {template['name']} ({template['size']} bytes)")
    
    if ui_analysis['static_ui']:
        print("\n\nStatic UI:")
        print(f"  Type: {ui_analysis['static_ui']['type']}")
        print(f"  Path: {ui_analysis['static_ui']['path']}")
        print(f"  Has Vite: {ui_analysis['static_ui']['has_vite']}")
        print(f"  Has package.json: {ui_analysis['static_ui']['has_package']}")
    
    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)


if __name__ == '__main__':
    main()
