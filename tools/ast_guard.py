import ast

def ast_equal_ignoring_docs(before: str, after: str) -> bool:
    """
    Ensure behavior unchanged: compare ASTs excluding docstrings/comments.
    """
    def remove_docstrings(node):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
            node.body = [n for n in node.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Str))]
        for child in ast.iter_child_nodes(node):
            remove_docstrings(child)
        return node

    try:
        tree1 = ast.parse(before)
        tree2 = ast.parse(after)
        remove_docstrings(tree1)
        remove_docstrings(tree2)
        return ast.dump(tree1) == ast.dump(tree2)
    except:
        return False