import ast
from typing import Dict, Any, List

def catalog(module_path: str, code: str, ast_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build Public API Catalog from __all__, public top-level names, and __init__ re-exports.
    """
    tree = ast.parse(code)
    catalog_items: List[Dict[str, Any]] = []

    # From __all__
    exports = ast_info.get('exports', [])
    for exp in exports:
        catalog_items.append({'name': exp, 'type': 'export', 'source': '__all__'})

    # Public top-level names
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
            catalog_items.append({'name': node.name, 'type': 'class', 'source': 'top-level'})
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
            catalog_items.append({'name': node.name, 'type': 'function', 'source': 'top-level'})
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and not node.targets[0].id.startswith('_'):
            catalog_items.append({'name': node.targets[0].id, 'type': 'variable', 'source': 'top-level'})

    # __init__ re-exports (if it's __init__.py)
    if module_path.endswith('__init__.py'):
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    if not alias.name.startswith('_'):
                        catalog_items.append({'name': alias.name, 'type': 'import', 'source': '__init__'})

    return catalog_items
# DOCGEN:LLM-FIRST@v4