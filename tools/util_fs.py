import os
import hashlib
from typing import List

def list_py_files(include: List[str], exclude: List[str]) -> List[str]:
    """
    List Python files in directories specified by include, excluding those in exclude.
    """
    files = []
    for inc in include:
        for root, dirs, filenames in os.walk(inc):
            dirs[:] = [d for d in dirs if not any(ex in os.path.join(root, d) for ex in exclude)]
            for filename in filenames:
                if filename.endswith('.py'):
                    files.append(os.path.join(root, filename))
    return files

def read(path: str) -> str:
    """
    Read the content of a file.
    """
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_once(path: str, content: str) -> None:
    """
    Write content to a file only if it doesn't exist or content differs, with single-write guarantee.
    """
    if not os.path.exists(path) or read(path) != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

def hash_text(text: str) -> str:
    """
    Compute SHA256 hash of the text.
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def exists(path: str) -> bool:
    """
    Check if path exists.
    """
    return os.path.exists(path)

def makedirs(path: str) -> None:
    """
    Create directories if they don't exist.
    """
    os.makedirs(path, exist_ok=True)
# DOCGEN:LLM-FIRST@v4