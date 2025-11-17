import ast
from typing import Dict, Any, List

def detect(code: str, ast_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect config touchpoints (env/CLI/config files) and concurrency (async/threads/locks/queues).
    """
    tree = ast.parse(code)
    config: Dict[str, List[str]] = {}
    concurrency: Dict[str, List[str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = ast.unparse(node.func) if hasattr(ast, 'unparse') else str(node.func)
            # Detect config
            if func_name in ['os.environ.get', 'os.getenv', 'argparse.ArgumentParser', 'configparser.ConfigParser']:
                config.setdefault('env_cli_config', []).append(func_name)
            elif func_name in ['open', 'json.load', 'yaml.safe_load'] and node.args:
                # Check if it's a config file
                if isinstance(node.args[0], ast.Str) and any(ext in node.args[0].s for ext in ['.json', '.yaml', '.yml', '.ini', '.cfg']):
                    config.setdefault('files', []).append(node.args[0].s)
            # Detect concurrency
            elif func_name in ['threading.Thread', 'multiprocessing.Process']:
                concurrency.setdefault('threads', []).append(func_name)
            elif func_name in ['asyncio.run', 'async def']:
                concurrency.setdefault('async', []).append(func_name)
            elif func_name in ['threading.Lock', 'threading.RLock', 'multiprocessing.Lock']:
                concurrency.setdefault('locks', []).append(func_name)
            elif func_name in ['queue.Queue', 'asyncio.Queue']:
                concurrency.setdefault('queues', []).append(func_name)
        elif isinstance(node, ast.AsyncFunctionDef):
            concurrency.setdefault('async', []).append(node.name)

    return {'config': config, 'concurrency': concurrency}
# DOCGEN:LLM-FIRST@v4