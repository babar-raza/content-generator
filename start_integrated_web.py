"""Launch UCOP Integrated Web UI with Visual Orchestration."""

import sys
import uvicorn
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core import Config, EventBus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    print("=" * 70)
    print("UCOP Integrated Web UI with Visual Orchestration")
    print("=" * 70)
    print()
    print("Features:")
    print("  • Job Management & Execution")
    print("  • Visual Workflow Orchestration")
    print("  • Real-time Monitoring")
    print("  • Interactive Workflow Graphs")
    print("  • Advanced Debugging & Analytics")
    print()
    
    # Load configuration and create event bus
    config = Config()
    config.load_from_env()
    event_bus = EventBus()
    
    # Initialize system with comprehensive checks
    print("Initializing system components...")
    print()
    
    try:
        from src.initialization import initialize_integrated_system
        execution_engine, job_controller, init_status = initialize_integrated_system(
            config, event_bus
        )
    except ImportError as e:
        logger.error(f"Failed to import initialization: {e}")
        execution_engine, job_controller, init_status = None, None, {}
    except Exception as e:
        logger.error(f"Initialization failed: {e}", exc_info=True)
        execution_engine, job_controller, init_status = None, None, {}
    
    # Import integrated web app
    try:
        from src.web.app_integrated import app, set_execution_engine
    except ImportError as e:
        logger.error(f"Failed to import integrated web app: {e}")
        logger.error("Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    
    # Connect execution engine if available
    if execution_engine and job_controller:
        try:
            set_execution_engine(execution_engine, job_controller)
            print("✓ Job execution engine connected to web UI")
        except:
            print("⚠ Using web UI in limited mode")
    else:
        print("⚠ Web UI running in limited mode (no job execution)")
        print("  Jobs from CLI will not be visible")
        print("  Job creation from web UI will not work")
    
    print()
    print("Starting integrated web server...")
    print()
    print("Dashboard:    http://localhost:8080  (or http://127.0.0.1:8080)")
    print("API Docs:     http://localhost:8080/docs")
    print("Health Check: http://localhost:8080/health")
    print("Visual API:   http://localhost:8080/api/health")
    print()
    print("Tabs Available:")
    print("  • Jobs - Manage content generation jobs")
    print("  • Visual Workflows - Interactive workflow visualization")
    print("  • Monitoring - Real-time system metrics")
    print("  • Debugging - Step-through workflow debugging")
    print()
    print("Note: Server runs on 0.0.0.0:8080 (listens on all interfaces)")
    print("      You can access it via localhost:8080 from this machine")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    # Start uvicorn server
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
