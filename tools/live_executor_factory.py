"""
Live Executor Factory for Wave 3 Testing

Creates real executor instances for live end-to-end tests.
Supports offline mode when LLM providers are not configured.
"""

from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.engine import get_engine, UnifiedEngine


def create_live_executor(config: dict = None) -> UnifiedEngine:
    """Create a live executor instance for testing.

    Args:
        config: Optional configuration dictionary

    Returns:
        UnifiedEngine instance ready for live testing

    Notes:
        - Uses real workflow compiler and checkpoint manager
        - If no LLM providers configured, will use deterministic stubs where applicable
        - Safe for offline testing
    """
    # Create engine instance
    engine = get_engine(config=config)

    return engine


if __name__ == '__main__':
    # Test factory
    print("=== Live Executor Factory Test ===")

    executor = create_live_executor()
    print(f"[OK] Executor created: {type(executor).__name__}")
    print(f"  Has event_bus: {hasattr(executor, 'event_bus')}")
    print(f"  Has agents: {hasattr(executor, 'agents')}")
    print(f"  Active jobs: {len(executor.active_jobs)}")
    print("\nFactory test successful!")
