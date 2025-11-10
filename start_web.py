#!/usr/bin/env python3
"""Start the UCOP web UI."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.web.app import app
from src.engine.unified_engine import get_engine
from src.orchestration.job_execution_engine import JobExecutionEngine
from src.realtime.job_control import JobController
import uvicorn

def start_web_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the web server with all components initialized."""
    
    # Initialize engine
    engine = get_engine()
    
    # Initialize job execution components
    job_engine = JobExecutionEngine(engine)
    job_controller = JobController(job_engine)
    
    # Set up the web app
    from src.web.app import set_execution_engine
    set_execution_engine(job_engine, job_controller)
    
    print(f"🚀 Starting UCOP Web UI on http://{host}:{port}")
    print("   Press Ctrl+C to stop")
    
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Start UCOP Web UI")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    
    args = parser.parse_args()
    start_web_server(args.host, args.port)
