"""Start server for diagnostic testing of expansion fixes"""
import logging
import uvicorn
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.web.app import create_app
from src.engine.unified_engine import UnifiedEngine
from src.core.config import Config

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    print("=" * 60)
    print("Content Generator - Diagnostic Server (Port 8103)")
    print("With deterministic fallback expansion")
    print("=" * 60)

    config = Config()
    executor = UnifiedEngine()
    app = create_app(executor=executor, config_snapshot=config)

    print("Server starting on http://0.0.0.0:8103")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8103, log_level="debug")
