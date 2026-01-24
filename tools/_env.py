"""
Environment helpers for capability verification tools.

Provides consistent path resolution, sys.path management, and venv Python access.
"""

import sys
from pathlib import Path


def get_repo_root() -> Path:
    """Get repository root directory by finding .git folder."""
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / '.git').exists():
            return current
        current = current.parent
    return Path.cwd()


def ensure_sys_path() -> None:
    """
    Ensure REPO_ROOT is in sys.path for proper imports.

    This allows imports like 'from src.agents.base import BaseAgent'
    as well as 'from src.web import app'.

    Important: We insert REPO_ROOT (not REPO_ROOT/src) so that
    'import src.module' works correctly.
    """
    repo_root = str(get_repo_root())
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def venv_python() -> Path:
    """
    Return path to capability verification interpreter.

    Tries multiple venv paths in priority order:
    1. .venv_wave5_3 (Wave 5.3 dedicated venv)
    2. .venv_capfix (legacy capability fix venv)
    3. .venv (default venv)
    4. Current sys.executable (fallback)
    """
    repo_root = get_repo_root()

    # Priority 1: .venv_wave5_3
    venv_wave5_3 = repo_root / '.venv_wave5_3' / 'Scripts' / 'python.exe'
    if venv_wave5_3.exists():
        return venv_wave5_3

    # Priority 2: .venv_capfix
    venv_capfix = repo_root / '.venv_capfix' / 'Scripts' / 'python.exe'
    if venv_capfix.exists():
        return venv_capfix

    # Priority 3: .venv
    venv_default = repo_root / '.venv' / 'Scripts' / 'python.exe'
    if venv_default.exists():
        return venv_default

    # Last resort: system Python (not recommended)
    return Path(sys.executable)


def get_pytest_command() -> list[str]:
    """Get the pytest command using the venv Python."""
    return [str(venv_python()), '-m', 'pytest']


def file_to_module_path(file_path: str) -> str:
    """
    Convert a file path to a module path.

    Example: 'src/agents/base.py' -> 'src.agents.base'

    Important: This keeps the 'src.' prefix to ensure correct imports
    when REPO_ROOT is in sys.path.
    """
    # Normalize path separators
    module_path = file_path.replace('\\', '/').replace('.py', '').replace('/', '.')

    # Remove leading dot if present
    if module_path.startswith('.'):
        module_path = module_path[1:]

    return module_path
