"""Path utilities for safe file operations and slug generation.

This module provides utilities for:
- Path traversal prevention
- URL-safe slug generation
- Safe directory creation

All using only Python standard library.

Example:
    >>> from path_utils import safe_path, generate_slug, ensure_directory
    >>> base = Path("/data")
    >>> safe_file = safe_path(base, "files/report.txt")
    >>> slug = generate_slug("My Amazing Article!")
    >>> directory = ensure_directory("/tmp/my_app/data")
"""

import re
from pathlib import Path
from typing import Union
import os


def safe_path(base_dir: Union[str, Path], user_path: Union[str, Path]) -> Path:
    """Prevent path traversal attacks by ensuring path stays within base_dir.
    
    Resolves the user-provided path and ensures it's within the base directory.
    This prevents attacks like "../../../etc/passwd".
    
    Args:
        base_dir: Root directory that paths must stay within
        user_path: User-provided path (absolute or relative)
        
    Returns:
        Resolved safe path within base_dir
        
    Raises:
        ValueError: If resolved path escapes base_dir
        
    Example:
        >>> base = Path("/data")
        >>> safe_path(base, "files/report.txt")
        PosixPath('/data/files/report.txt')
        
        >>> safe_path(base, "../etc/passwd")  # Raises ValueError
        Traceback (most recent call last):
            ...
        ValueError: Path traversal detected: resolved path is outside base directory
    """
    base_dir = Path(base_dir).resolve()
    
    # If user_path is absolute, ignore it and use just the filename
    user_path = Path(user_path)
    if user_path.is_absolute():
        # Take only the name component to prevent absolute path bypass
        user_path = user_path.name
    
    # Resolve the full path
    resolved = (base_dir / user_path).resolve()
    
    # Check if resolved path is within base_dir
    try:
        resolved.relative_to(base_dir)
    except ValueError:
        raise ValueError(
            f"Path traversal detected: resolved path is outside base directory. "
            f"Base: {base_dir}, Requested: {user_path}, Resolved: {resolved}"
        )
    
    return resolved


def generate_slug(text: str, max_length: int = 50, lowercase: bool = True) -> str:
    """Generate URL-safe slug from text.
    
    Converts text to a URL-safe format by:
    - Converting to lowercase (optional)
    - Replacing spaces and special characters with hyphens
    - Removing consecutive hyphens
    - Trimming to max_length
    - Removing leading/trailing hyphens
    
    Args:
        text: Input text to slugify
        max_length: Maximum slug length (default: 50)
        lowercase: Convert to lowercase (default: True)
        
    Returns:
        URL-safe slug string
        
    Example:
        >>> generate_slug("Hello, World! 123")
        'hello-world-123'
        
        >>> generate_slug("Python 3.11: New Features")
        'python-3-11-new-features'
        
        >>> generate_slug("  Multiple   Spaces  ")
        'multiple-spaces'
        
        >>> generate_slug("Über cool café", max_length=20)
        'uber-cool-cafe'
    """
    if not text:
        return ""
    
    # Convert to string if not already
    slug = str(text)
    
    # Convert to lowercase if requested
    if lowercase:
        slug = slug.lower()
    
    # Replace accented characters with ASCII equivalents
    # Using a simple approach with standard library only
    replacements = {
        'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
        'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
        'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
        'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
        'ý': 'y', 'ÿ': 'y',
        'ñ': 'n', 'ç': 'c',
        'ß': 'ss',
        'æ': 'ae', 'œ': 'oe',
    }
    for accented, ascii_char in replacements.items():
        slug = slug.replace(accented, ascii_char)
    
    # Replace any non-alphanumeric character with hyphen
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Trim to max length
    if len(slug) > max_length:
        slug = slug[:max_length]
        # Ensure we don't cut in the middle of a word
        if '-' in slug:
            slug = slug.rsplit('-', 1)[0]
    
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug


def ensure_directory(path: Union[str, Path], mode: int = 0o755) -> Path:
    """Create directory if it doesn't exist (thread-safe).
    
    Handles race conditions where directory is created between check and creation.
    
    Args:
        path: Directory path to create
        mode: Permission mode (default: 0o755)
        
    Returns:
        Path object for the directory
        
    Raises:
        OSError: If directory cannot be created (permissions, etc.)
        
    Example:
        >>> ensure_directory("/tmp/my_app/data")
        PosixPath('/tmp/my_app/data')
        
        >>> # Safe to call multiple times
        >>> ensure_directory("/tmp/my_app/data")
        PosixPath('/tmp/my_app/data')
    """
    path = Path(path)
    
    try:
        path.mkdir(mode=mode, parents=True, exist_ok=True)
    except FileExistsError:
        # Another thread/process created it between our check and mkdir
        # This is fine, just verify it's actually a directory
        if not path.is_dir():
            raise OSError(f"Path exists but is not a directory: {path}")
    
    return path


def get_safe_filename(filename: str, max_length: int = 255) -> str:
    """Get safe filename by removing/replacing dangerous characters.
    
    Ensures filename is safe for use on most filesystems by:
    - Removing path separators
    - Replacing dangerous characters
    - Trimming to max_length (accounting for filesystem limits)
    - Preserving file extension
    
    Args:
        filename: Original filename
        max_length: Maximum filename length (default: 255, typical filesystem limit)
        
    Returns:
        Safe filename string
        
    Example:
        >>> get_safe_filename("my/file:name?.txt")
        'my-file-name.txt'
        
        >>> get_safe_filename("report*.docx")
        'report.docx'
    """
    if not filename:
        return "unnamed"
    
    # Split extension
    name_parts = filename.rsplit('.', 1)
    name = name_parts[0]
    ext = f".{name_parts[1]}" if len(name_parts) > 1 else ""
    
    # Remove or replace dangerous characters
    dangerous_chars = r'[<>:"/\\|?*\x00-\x1f]'
    name = re.sub(dangerous_chars, '-', name)
    
    # Remove consecutive hyphens
    name = re.sub(r'-+', '-', name)
    
    # Trim to max length (account for extension)
    max_name_length = max_length - len(ext)
    if len(name) > max_name_length:
        name = name[:max_name_length]
    
    # Combine name and extension
    safe_name = name.strip(' -') + ext
    
    # Ensure we have a valid name
    if not safe_name or safe_name == ext:
        safe_name = f"unnamed{ext}"
    
    return safe_name


def is_safe_path(path: Union[str, Path], allowed_extensions: list = None) -> bool:
    """Check if path is safe (no traversal, allowed extension).
    
    Uses proper Path resolution to detect traversal attempts.
    
    Args:
        path: Path to check
        allowed_extensions: List of allowed extensions (e.g., ['.txt', '.json'])
                           None allows all extensions
        
    Returns:
        True if path is safe, False otherwise
        
    Example:
        >>> is_safe_path("data/file.txt", ['.txt', '.json'])
        True
        
        >>> is_safe_path("../etc/passwd", ['.txt'])
        False
        
        >>> is_safe_path("file.exe", ['.txt', '.json'])
        False
    """
    try:
        path = Path(path)
        
        # Check for absolute paths
        if path.is_absolute():
            return False
        
        # Resolve and check if it would go outside current directory
        # This properly handles encoded characters and various bypass attempts
        resolved = path.resolve()
        cwd = Path.cwd().resolve()
        
        # Ensure resolved path starts with cwd
        try:
            resolved.relative_to(cwd)
        except ValueError:
            # Path escapes current directory
            return False
        
        # Check extension if specified
        if allowed_extensions is not None:
            if path.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
                return False
        
        return True
        
    except (ValueError, OSError):
        return False


def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize path by resolving . and .. components.
    
    Does NOT resolve symlinks or check if path exists.
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized Path object
        
    Example:
        >>> normalize_path("./data/../files/./report.txt")
        PosixPath('files/report.txt')
    """
    return Path(os.path.normpath(path))
