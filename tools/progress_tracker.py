import json
import os
from typing import Dict, Any, List

def load_state(path: str) -> Dict[str, Any]:
    """
    Load state from JSON file.
    """
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_state(path: str, state: Dict[str, Any]) -> None:
    """
    Save state to JSON file.
    """
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def initialize_state(files: List[str], discovery_hash_path: str, state_path: str) -> Dict[str, Any]:
    """
    Initialize state with files, hash, etc.
    """
    from .util_fs import hash_text, read
    discovery_hash = hash_text('\n'.join(sorted(files)))
    if os.path.exists(discovery_hash_path):
        with open(discovery_hash_path, 'r') as f:
            if f.read().strip() == discovery_hash:
                return load_state(state_path)
    with open(discovery_hash_path, 'w') as f:
        f.write(discovery_hash)
    state = {
        'queue': files,
        'done': [],
        'skipped': [],
        'status': {f: 'pending' for f in files}
    }
    save_state(state_path, state)
    return state

def next_batch(state: Dict[str, Any], batch_size: int) -> List[str]:
    """
    Get next batch of files from queue.
    """
    queue = state.get('queue', [])
    batch = queue[:batch_size]
    state['queue'] = queue[batch_size:]
    return batch

def mark_done(state: Dict[str, Any], path: str, status: str) -> None:
    """
    Mark a file as done with status.
    """
    state['status'][path] = status
    if status in ['updated', 'unchanged']:
        state['done'].append(path)
    elif status == 'skipped':
        state['skipped'].append(path)
    # Note: 'error' could be added to done or separate list, but per API, status in {'updated','skipped','error','unchanged'}
# DOCGEN:LLM-FIRST@v4