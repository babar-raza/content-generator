import ast
from typing import Dict, Any, List, Tuple, Optional

def scan(code: str) -> Dict[str, Any]:
    """
    Parse a .py file into AST and collect symbols and docstring locations.
    """
    tree = ast.parse(code)
    classes: List[Dict[str, Any]] = []
    functions: List[Dict[str, Any]] = []
    exports: List[str] = []
    imports: List[Dict[str, Any]] = []
    module_docstring_span: Optional[Tuple[int, int]] = None
    docstrings: Dict[str, str] = {}

    # Collect module docstring
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Str):
        start = tree.body[0].lineno
        end = getattr(tree.body[0], 'end_lineno', start)
        module_docstring_span = (start, end)

    # Walk the AST
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append({'name': node.name, 'lineno': node.lineno})
            doc = ast.get_docstring(node)
            if doc:
                docstrings[node.name] = doc
        elif isinstance(node, ast.FunctionDef):
            functions.append({'name': node.name, 'lineno': node.lineno})
            doc = ast.get_docstring(node)
            if doc:
                docstrings[node.name] = doc
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    'name': alias.name,
                    'asname': alias.asname,
                    'lineno': node.lineno
                })
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ''
            for alias in node.names:
                full_name = f"{module_name}.{alias.name}" if module_name else alias.name
                imports.append({
                    'name': full_name,
                    'asname': alias.asname,
                    'lineno': node.lineno
                })
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == '__all__':
                    if isinstance(node.value, ast.List):
                        exports = [elt.value for elt in node.value.elts if isinstance(elt, ast.Str)]

    return {
        'classes': classes,
        'functions': functions,
        'exports': exports,
        'imports': imports,
        'module_docstring_span': module_docstring_span,
        'docstrings': docstrings
    }
# DOCGEN:LLM-FIRST@v4