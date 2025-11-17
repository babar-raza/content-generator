"""Context merger with precedence handling."""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ContextMerger:
    """Merges multiple context sources with precedence."""
    
    PRECEDENCE = {
        "extra": 100,    # Highest priority - user-provided
        "docs": 80,      # Organization knowledge
        "blog": 60,      # Existing content
        "api": 40        # Technical specs
    }
    
    def merge(self,
              extra_contexts: List[Dict[str, Any]] = None,
              api_context: str = "",
              blog_context: str = "",
              docs_context: str = "") -> str:
        """Merge all contexts with precedence."""
        
        merged_parts = []
        
        # Extra context first (highest priority)
        if extra_contexts:
            extra_sorted = sorted(
                extra_contexts,
                key=lambda x: x.get('priority', 50),
                reverse=True
            )
            
            for ctx in extra_sorted:
                ctx_type = ctx.get('type', 'unknown')
                merged_parts.append(f"[PRIORITY CONTEXT - {ctx_type.upper()}]")
                
                if 'content' in ctx:
                    merged_parts.append(ctx['content'])
                elif 'path' in ctx:
                    from pathlib import Path
                    try:
                        content = Path(ctx['path']).read_text(encoding='utf-8')
                        merged_parts.append(content)
                    except Exception as e:
                        logger.warning(f"Failed to load extra context from {ctx['path']}: {e}")
                elif 'url' in ctx:
                    # Would need to fetch URL content
                    logger.warning(f"URL context not yet implemented: {ctx['url']}")
        
        # Docs context
        if docs_context and docs_context.strip():
            merged_parts.append("[DOCUMENTATION CONTEXT]")
            merged_parts.append(docs_context)
        
        # Blog context
        if blog_context and blog_context.strip():
            merged_parts.append("[BLOG CONTEXT]")
            merged_parts.append(blog_context)
        
        # API reference
        if api_context and api_context.strip():
            merged_parts.append("[API REFERENCE]")
            merged_parts.append(api_context)
        
        merged = "\n\n---\n\n".join(merged_parts)
        
        logger.info(
            f"Context merged: {len(merged_parts)} sources, "
            f"{len(merged)} total chars"
        )
        
        return merged
    
    def get_context_summary(self,
                           extra_contexts: List[Dict[str, Any]] = None,
                           api_context: str = "",
                           blog_context: str = "",
                           docs_context: str = "") -> Dict[str, Any]:
        """Get summary of context sources."""
        
        summary = {
            "sources": [],
            "total_size": 0,
            "precedence_order": []
        }
        
        if extra_contexts:
            for ctx in extra_contexts:
                ctx_type = ctx.get('type', 'unknown')
                summary["sources"].append({
                    "type": "extra",
                    "subtype": ctx_type,
                    "priority": ctx.get('priority', 50)
                })
            summary["precedence_order"].append("extra")
        
        if docs_context:
            summary["sources"].append({
                "type": "docs",
                "size": len(docs_context)
            })
            summary["precedence_order"].append("docs")
            summary["total_size"] += len(docs_context)
        
        if blog_context:
            summary["sources"].append({
                "type": "blog",
                "size": len(blog_context)
            })
            summary["precedence_order"].append("blog")
            summary["total_size"] += len(blog_context)
        
        if api_context:
            summary["sources"].append({
                "type": "api",
                "size": len(api_context)
            })
            summary["precedence_order"].append("api")
            summary["total_size"] += len(api_context)
        
        return summary
# DOCGEN:LLM-FIRST@v4