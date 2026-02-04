"""
Workflow Editor - Web UI Startup Script
========================================
"""

import logging
import sys
import uvicorn
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.web.app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main startup function."""
    print("=" * 60)
    print("Workflow Editor - Web UI")
    print("=" * 60)
    
    # Create web application
    print("Creating web application...")
    app = create_app()
    logger.info("✓ Web application created")
    
    # Check for UI build
    ui_dist = Path(__file__).parent / "src" / "web" / "static" / "dist"
    if ui_dist.exists():
        logger.info("✓ UI build found")
    else:
        logger.warning("⚠ UI build not found - only API will be available")
    
    # Allow port override via environment variable
    import os
    port = int(os.getenv("PORT", "8000"))

    print("=" * 60)
    print(f"Starting server on http://localhost:{port}")
    print("=" * 60)
    print("Press Ctrl+C to stop")

    # Start server
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nShutting down...")
        logger.info("✓ Server stopped")


if __name__ == "__main__":
    main()
