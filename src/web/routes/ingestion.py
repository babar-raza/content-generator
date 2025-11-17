"""Ingestion API routes for content processing."""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])


# Models
class IngestRequest(BaseModel):
    """Request to ingest content."""
    path: str = Field(..., description="Path to content directory")


class IngestResponse(BaseModel):
    """Response from ingestion."""
    status: str
    type: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    stats: Optional[dict] = None


@router.post("/kb")
async def ingest_kb(request: IngestRequest):
    """Ingest KB articles (mirrors cmd_ingest kb).
    
    Args:
        request: Ingestion request with path
        
    Returns:
        Ingestion result
    """
    try:
        from src.mcp.handlers import handle_ingest_kb
        
        result = await handle_ingest_kb({"kb_path": request.path})
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error ingesting KB: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest KB: {str(e)}")


@router.post("/docs")
async def ingest_docs(request: IngestRequest):
    """Ingest documentation (mirrors cmd_ingest docs).
    
    Args:
        request: Ingestion request with path
        
    Returns:
        Ingestion result
    """
    try:
        from src.mcp.handlers import handle_ingest_docs
        
        result = await handle_ingest_docs({"docs_path": request.path})
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error ingesting docs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest docs: {str(e)}")


@router.post("/api")
async def ingest_api(request: IngestRequest):
    """Ingest API reference (mirrors cmd_ingest api).
    
    Args:
        request: Ingestion request with path
        
    Returns:
        Ingestion result
    """
    try:
        from src.mcp.handlers import handle_ingest_api
        
        result = await handle_ingest_api({"api_path": request.path})
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error ingesting API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest API: {str(e)}")


@router.post("/blog")
async def ingest_blog(request: IngestRequest):
    """Ingest blog posts (mirrors cmd_ingest blog).
    
    Args:
        request: Ingestion request with path
        
    Returns:
        Ingestion result
    """
    try:
        from src.mcp.handlers import handle_ingest_blog
        
        result = await handle_ingest_blog({"blog_path": request.path})
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error ingesting blog: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest blog: {str(e)}")


@router.post("/tutorial")
async def ingest_tutorial(request: IngestRequest):
    """Ingest tutorials (mirrors cmd_ingest tutorial).
    
    Args:
        request: Ingestion request with path
        
    Returns:
        Ingestion result
    """
    try:
        from src.mcp.handlers import handle_ingest_tutorial
        
        result = await handle_ingest_tutorial({"tutorial_path": request.tutorial})
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error ingesting tutorial: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest tutorial: {str(e)}")


@router.post("/kb/upload")
async def ingest_kb_upload(files: List[UploadFile] = File(...)):
    """Ingest KB articles from uploaded files.
    
    Args:
        files: Uploaded KB article files
        
    Returns:
        Ingestion result
    """
    try:
        import tempfile
        import os
        from pathlib import Path
        from src.mcp.handlers import handle_ingest_kb
        
        # Create temporary directory for uploads
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Save uploaded files
            for file in files:
                file_path = temp_path / file.filename
                with open(file_path, 'wb') as f:
                    content = await file.read()
                    f.write(content)
            
            # Ingest from temp directory
            result = await handle_ingest_kb({"kb_path": str(temp_path)})
            
            return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error ingesting uploaded KB: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest uploaded KB: {str(e)}")


@router.get("/status")
async def get_ingestion_status():
    """Get status of all ingestion operations.
    
    Returns:
        Status of ingestion operations
    """
    try:
        # This would track ingestion operations
        # For now, return empty status
        return JSONResponse(content={
            "operations": [],
            "total": 0,
            "active": 0,
            "completed": 0,
            "failed": 0
        })
    except Exception as e:
        logger.error(f"Error getting ingestion status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get ingestion status: {str(e)}")
