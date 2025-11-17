import ast
from typing import Dict, Any, List

def detect(code: str, ast_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect exceptions raised/re-raised; detect I/O surfaces (files, network, DB/queues, GPU).
    """
    tree = ast.parse(code)
    raises: Dict[str, List[str]] = {}
    io: Dict[str, List[str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            # Find the function or class this raise is in
            func_name = None
            for parent in ast.walk(tree):
                if isinstance(parent, ast.FunctionDef) and parent.lineno <= node.lineno <= getattr(parent, 'end_lineno', parent.lineno):
                    func_name = parent.name
                    break
            if func_name:
                if func_name not in raises:
                    raises[func_name] = []
                if node.exc:
                    exc_name = ast.unparse(node.exc) if hasattr(ast, 'unparse') else str(node.exc)
                    raises[func_name].append(exc_name)
                else:
                    raises[func_name].append('re-raise')
        elif isinstance(node, ast.Call):
            func_name = ast.unparse(node.func) if hasattr(ast, 'unparse') else str(node.func)
            # Detect I/O
            if func_name in ['open', 'os.open', 'io.open']:
                io.setdefault('files', []).append(func_name)
            elif func_name in ['requests.get', 'requests.post', 'urllib.request.urlopen', 'socket.socket']:
                io.setdefault('network', []).append(func_name)
            elif func_name in ['sqlite3.connect', 'psycopg2.connect', 'pymongo.MongoClient']:
                io.setdefault('db', []).append(func_name)
            elif func_name in ['queue.Queue', 'multiprocessing.Queue']:
                io.setdefault('queues', []).append(func_name)
            elif func_name in ['torch.cuda.is_available', 'cupy.array']:
                io.setdefault('gpu', []).append(func_name)

    return {'raises': raises, 'io': io}
# DOCGEN:LLM-FIRST@v4