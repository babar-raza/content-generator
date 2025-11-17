"""Output path resolution for blog vs non-blog templates."""

from pathlib import Path
from typing import Optional


def is_blog_template(template_id: str) -> bool:
    """Check if template is a blog template.
    
    Args:
        template_id: Template identifier or label
        
    Returns:
        True if blog template, False otherwise
    """
    if not template_id:
        return False
    return "blog" in template_id.lower()


def resolve_output_path(
    template_id: str,
    slug: str,
    output_dir: Path = Path("./output")
) -> Path:
    """Resolve output path based on template type.
    
    Rules:
    - Blog template: ./output/{slug}/index.md
    - Non-blog template: ./output/{slug}.md
    
    Args:
        template_id: Template identifier
        slug: URL-safe slug
        output_dir: Base output directory
        
    Returns:
        Full output path
    """
    if is_blog_template(template_id):
        # Blog: create directory structure
        return output_dir / slug / "index.md"
    else:
        # Non-blog: single file
        return output_dir / f"{slug}.md"
# DOCGEN:LLM-FIRST@v4