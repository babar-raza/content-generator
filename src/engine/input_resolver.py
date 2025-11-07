"""Input resolver for multiple input modes."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Union, List, Dict, Any
import logging

from .exceptions import InputResolutionError

logger = logging.getLogger(__name__)


@dataclass
class ContextSet:
    """Normalized context from any input type."""
    primary_content: str
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.primary_content:
            raise InputResolutionError("Primary content is empty")


class InputResolver:
    """Resolves different input types to ContextSet."""
    
    def resolve(self, input_spec: Union[str, Path, List[Union[str, Path]], Dict[str, List[str]]]) -> ContextSet:
        """Resolve any input type to normalized ContextSet.
        
        Args:
            input_spec: Can be:
                - str: topic or file path
                - Path: file or folder path
                - List: list of paths
                - Dict: {'kb': [paths], 'docs': [paths], ...} from uploads
        """
        
        # Dict mode (uploaded files)
        if isinstance(input_spec, dict) and any(k in input_spec for k in ['kb', 'docs', 'blog', 'api', 'tutorial']):
            return self._resolve_uploaded_files(input_spec)
        
        # List mode
        if isinstance(input_spec, list):
            return self._resolve_list(input_spec)
        
        # Convert to Path for checking
        path = Path(input_spec) if isinstance(input_spec, str) else input_spec
        
        # Folder mode
        if path.exists() and path.is_dir():
            return self._resolve_folder(path)
        
        # File mode
        if path.exists() and path.is_file():
            return self._resolve_file(path)
        
        # Topic mode (string that's not a file)
        if isinstance(input_spec, str):
            return self._resolve_topic(input_spec)
        
        raise InputResolutionError(f"Cannot resolve input: {input_spec}")
    
    def _resolve_topic(self, topic: str) -> ContextSet:
        """Topic mode: simple string input."""
        logger.info(f"Input mode: topic - '{topic}'")
        return ContextSet(
            primary_content=topic,
            sources=["user_topic"],
            metadata={
                "input_mode": "topic",
                "topic": topic
            }
        )
    
    def _resolve_file(self, path: Path) -> ContextSet:
        """File mode: single file input."""
        logger.info(f"Input mode: file - {path}")
        
        try:
            content = path.read_text(encoding='utf-8')
        except Exception as e:
            raise InputResolutionError(f"Failed to read file {path}: {e}")
        
        return ContextSet(
            primary_content=content,
            sources=[str(path)],
            metadata={
                "input_mode": "file",
                "filename": path.name,
                "filepath": str(path),
                "size_bytes": path.stat().st_size
            }
        )
    
    def _resolve_folder(self, path: Path) -> ContextSet:
        """Folder mode: all .md files in folder."""
        logger.info(f"Input mode: folder - {path}")
        
        md_files = sorted(path.glob("**/*.md"))
        
        if not md_files:
            raise InputResolutionError(f"No .md files found in {path}")
        
        contents = []
        sources = []
        
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
                contents.append(f"# File: {md_file.name}\n\n{content}")
                sources.append(str(md_file))
            except Exception as e:
                logger.warning(f"Failed to read {md_file}: {e}")
                continue
        
        if not contents:
            raise InputResolutionError(f"Failed to read any files from {path}")
        
        combined = "\n\n---\n\n".join(contents)
        
        return ContextSet(
            primary_content=combined,
            sources=sources,
            metadata={
                "input_mode": "folder",
                "folder_path": str(path),
                "file_count": len(sources),
                "total_size_bytes": sum(Path(s).stat().st_size for s in sources)
            }
        )
    
    def _resolve_list(self, file_list: List[Union[str, Path]]) -> ContextSet:
        """List mode: explicit list of files."""
        logger.info(f"Input mode: list - {len(file_list)} files")
        
        contents = []
        sources = []
        
        for item in file_list:
            path = Path(item)
            
            if not path.exists():
                logger.warning(f"File not found: {path}")
                continue
            
            if not path.is_file():
                logger.warning(f"Not a file: {path}")
                continue
            
            try:
                content = path.read_text(encoding='utf-8')
                contents.append(f"# File: {path.name}\n\n{content}")
                sources.append(str(path))
            except Exception as e:
                logger.warning(f"Failed to read {path}: {e}")
                continue
        
        if not contents:
            raise InputResolutionError("Failed to read any files from list")
        
        combined = "\n\n---\n\n".join(contents)
        
        return ContextSet(
            primary_content=combined,
            sources=sources,
            metadata={
                "input_mode": "list",
                "file_count": len(sources),
                "requested_count": len(file_list)
            }
        )
    
    def _resolve_uploaded_files(self, uploads_dict: Dict[str, List[str]]) -> ContextSet:
        """Uploaded files mode: dict of {category: [paths]}.
        
        Args:
            uploads_dict: Dict with keys like 'kb', 'docs', 'blog', etc.
                         Values are lists of file paths
        """
        logger.info(f"Input mode: uploaded_files")
        
        contents = []
        sources = []
        categories_found = []
        
        # Process each category
        for category, file_paths in uploads_dict.items():
            if not file_paths:
                continue
            
            categories_found.append(category)
            
            for file_path in file_paths:
                path = Path(file_path)
                
                if not path.exists():
                    logger.warning(f"Uploaded file not found: {path}")
                    continue
                
                try:
                    content = path.read_text(encoding='utf-8')
                    contents.append(f"# [{category.upper()}] {path.name}\n\n{content}")
                    sources.append(str(path))
                except Exception as e:
                    logger.warning(f"Failed to read uploaded file {path}: {e}")
                    continue
        
        if not contents:
            raise InputResolutionError("No uploaded files could be read")
        
        combined = "\n\n---\n\n".join(contents)
        
        return ContextSet(
            primary_content=combined,
            sources=sources,
            metadata={
                "input_mode": "uploaded_files",
                "file_count": len(sources),
                "categories": categories_found
            }
        )
