"""Topics API routes for content topic discovery."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/topics", tags=["topics"])


# Models
class DiscoverTopicsRequest(BaseModel):
    """Request to discover topics from content."""
    kb_path: Optional[str] = Field(None, description="Path to KB directory")
    docs_path: Optional[str] = Field(None, description="Path to docs directory")
    content: Optional[str] = Field(None, description="Raw content to analyze")
    max_topics: int = Field(default=50, description="Maximum topics to return")
    min_confidence: float = Field(default=0.7, description="Minimum confidence threshold")


class DiscoverTopicsResponse(BaseModel):
    """Response from topic discovery."""
    status: str
    topics: list
    total_discovered: int
    after_dedup: int
    max_topics: int


@router.post("/discover")
async def discover_topics(request: DiscoverTopicsRequest):
    """Discover topics from content (mirrors cmd_discover_topics).
    
    Args:
        request: Discovery request with paths or content
        
    Returns:
        Discovered topics
    """
    try:
        from src.mcp.handlers import handle_topics_discover
        
        # Build params
        params = {
            "max_topics": request.max_topics
        }
        
        if request.kb_path:
            params["kb_path"] = request.kb_path
        if request.docs_path:
            params["docs_path"] = request.docs_path
        if request.content:
            params["content"] = request.content
        
        # Validate at least one source is provided
        if not request.kb_path and not request.docs_path and not request.content:
            raise HTTPException(
                status_code=400,
                detail="At least one of kb_path, docs_path, or content is required"
            )
        
        # Run discovery
        result = await handle_topics_discover(params)
        
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error discovering topics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to discover topics: {str(e)}")


@router.get("/list")
async def list_topics():
    """List all discovered topics.
    
    Returns:
        List of discovered topics from vector store/cache
    """
    try:
        # This would read from a topics cache or vector store
        # For now, return empty list as implementation would need vector store
        return JSONResponse(content={
            "topics": [],
            "total": 0,
            "message": "Topic listing requires vector store implementation"
        })
    except Exception as e:
        logger.error(f"Error listing topics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list topics: {str(e)}")


@router.get("/{topic_id}")
async def get_topic_details(topic_id: str):
    """Get topic details including related content.
    
    Args:
        topic_id: Topic identifier
        
    Returns:
        Topic details with related content
    """
    try:
        # This would read from a topics database/vector store
        # For now, return 404 as implementation would need vector store
        raise HTTPException(
            status_code=404,
            detail=f"Topic '{topic_id}' not found. Topic details require vector store implementation."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get topic details: {str(e)}")
