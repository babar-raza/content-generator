#!/usr/bin/env python3
"""
UCOP API Server - Simple FastAPI Launcher
Lightweight entry point for just the REST API without unified features.
"""

import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def setup_logging(log_level: str = "INFO"):
    """Configure logging."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('ucop_api.log')
        ]
    )
    
    return logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='UCOP API Server - FastAPI REST API',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--host', default='0.0.0.0',
                       help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000,
                       help='Port to bind to (default: 8000)')
    parser.add_argument('--log-level',
                       choices=['debug', 'info', 'warning', 'error'],
                       default='info',
                       help='Logging level (default: info)')
    parser.add_argument('--reload', action='store_true',
                       help='Enable auto-reload (development)')
    parser.add_argument('--workers', type=int, default=1,
                       help='Number of worker processes (default: 1)')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level)
    
    # Print header
    print("=" * 70)
    print("UCOP API Server")
    print("=" * 70)
    print()
    print(f"Starting server on {args.host}:{args.port}")
    print(f"Log level: {args.log_level}")
    print()
    print("Available endpoints:")
    print(f"  - http://{args.host}:{args.port}/")
    print(f"  - http://{args.host}:{args.port}/health")
    print(f"  - http://{args.host}:{args.port}/docs (Swagger UI)")
    print(f"  - http://{args.host}:{args.port}/api/jobs")
    print(f"  - http://{args.host}:{args.port}/api/workflows")
    print(f"  - http://{args.host}:{args.port}/api/agents")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    try:
        import uvicorn
        
        # Run server
        uvicorn.run(
            "src.web.app:app",
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower(),
            reload=args.reload,
            workers=args.workers if not args.reload else 1
        )
        
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down gracefully...")
        return 0
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        print(f"[ERROR] Server error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
# DOCGEN:LLM-FIRST@v4