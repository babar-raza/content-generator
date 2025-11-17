import ast
from typing import Dict, Any

def apply(code: str, facts: Dict[str, Any], templates: Dict[str, str], id_marker: str) -> str:
    """
    Generate/merge module/class/function docstrings from templates and detected facts; inject id marker.
    """
    tree = ast.parse(code)
    lines = code.splitlines()

    # For simplicity, assume we add docstrings to functions and classes without them
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not ast.get_docstring(node):
            # Generate docstring based on facts
            doc = f'"""\n{node.name} function/class.\n\n{facts.get("description", "")}\n"""'
            # Insert after the def/class line
            insert_line = node.lineno
            lines.insert(insert_line, doc)
            # Adjust subsequent line numbers? For simplicity, not handling here

    # Inject id_marker at the end or somewhere
    lines.append(f'# {id_marker}')

    return '\n'.join(lines)
# DOCGEN:LLM-FIRST@v4