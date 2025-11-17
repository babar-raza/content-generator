"""
Page routes for serving React UI pages.
"""

import logging
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pages"])


@router.get("/ingestion")
async def ingestion_page():
    """Serve ingestion management page."""
    index_file = Path(__file__).parent.parent / "static" / "dist" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return {"error": "UI not built"}


@router.get("/topics/discover")
async def topic_discovery_page():
    """Serve topic discovery page."""
    index_file = Path(__file__).parent.parent / "static" / "dist" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return {"error": "UI not built"}


@router.get("/agents/test")
async def agent_testing_page():
    """Serve agent testing page."""
    index_file = Path(__file__).parent.parent / "static" / "dist" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return {"error": "UI not built"}
