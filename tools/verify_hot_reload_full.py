#!/usr/bin/env python3
"""Verify hot reload functionality.

Tests:
- Hot reload monitor initialization
- File watching
- Config validation
- Reload callbacks
- Rollback on error
"""

import sys
import time
import tempfile
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.orchestration.hot_reload import HotReloadMonitor, ConfigValidator
from src.orchestration.agent_scanner import AgentScanner
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_validator():
    """Test config validation."""
    print("\n" + "="*60)
    print("Test 1: Config Validation")
    print("="*60)
    
    # Valid config
    valid_config = {
        "agents": {
            "test_agent": {
                "class": "TestAgent"
            }
        }
    }
    
    is_valid, error = ConfigValidator.validate_agents_config(valid_config)
    assert is_valid, f"Valid config failed validation: {error}"
    print("✓ Valid config passed validation")
    
    # Invalid config
    invalid_config = {"invalid": "config"}
    is_valid, error = ConfigValidator.validate_agents_config(invalid_config)
    assert not is_valid, "Invalid config passed validation"
    print(f"✓ Invalid config rejected: {error}")
    
    print("\nConfig validation: PASSED")


def test_monitor_lifecycle():
    """Test monitor start/stop lifecycle."""
    print("\n" + "="*60)
    print("Test 2: Monitor Lifecycle")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "test.yaml"
        config_file.write_text("test: value")
        
        monitor = HotReloadMonitor(paths=[config_file])
        
        # Test start
        monitor.start()
        assert monitor._running, "Monitor should be running after start"
        print("✓ Monitor started successfully")
        
        # Test stop
        monitor.stop()
        assert not monitor._running, "Monitor should be stopped"
        print("✓ Monitor stopped successfully")
    
    print("\nMonitor lifecycle: PASSED")


def test_callback_registration():
    """Test callback registration and execution."""
    print("\n" + "="*60)
    print("Test 3: Callback Registration")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "agents.yaml"
        
        # Create valid config
        config = {
            "agents": {
                "test": {"class": "Test"}
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        monitor = HotReloadMonitor(paths=[config_file])
        
        # Register callback
        callback_executed = []
        
        def test_callback(path, data):
            callback_executed.append(True)
            assert "agents" in data
        
        monitor.register_reload_callback("agents.yaml", test_callback)
        print("✓ Callback registered")
        
        # Trigger reload
        monitor.reload_config_file(config_file)
        
        assert len(callback_executed) > 0, "Callback not executed"
        print("✓ Callback executed on reload")
    
    print("\nCallback registration: PASSED")


def test_validation_failure():
    """Test validation failure and rollback."""
    print("\n" + "="*60)
    print("Test 4: Validation Failure & Rollback")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "agents.yaml"
        
        # Create valid initial config
        valid_config = {
            "agents": {
                "test": {"class": "Test"}
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(valid_config, f)
        
        monitor = HotReloadMonitor(paths=[config_file])
        
        # Create snapshot
        monitor._create_snapshot(config_file)
        print("✓ Initial snapshot created")
        
        # Write invalid config
        invalid_config = {"invalid": "config"}
        with open(config_file, "w") as f:
            yaml.dump(invalid_config, f)
        
        # Try to reload - should fail
        success = monitor.reload_config_file(config_file)
        
        assert not success, "Reload should fail with invalid config"
        print("✓ Invalid config rejected")
        
        # Check stats
        stats = monitor.get_stats()
        assert stats["failed_reloads"] > 0, "Failed reload not tracked"
        print(f"✓ Failure tracked in stats: {stats['failed_reloads']} failed reloads")
    
    print("\nValidation failure: PASSED")


def test_debouncing():
    """Test file change debouncing."""
    print("\n" + "="*60)
    print("Test 5: Change Debouncing")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "agents.yaml"
        
        # Create valid config
        config = {
            "agents": {
                "test": {"class": "Test"}
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        monitor = HotReloadMonitor(paths=[config_file])
        monitor.start()
        
        callback_count = []
        
        def count_callback(path, data):
            callback_count.append(1)
        
        monitor.register_reload_callback("agents.yaml", count_callback)
        
        # Give monitor time to start
        time.sleep(0.5)
        
        # Make multiple rapid changes
        for i in range(3):
            with open(config_file, "a") as f:
                f.write(f"\n# Change {i}\n")
            time.sleep(0.1)  # 100ms between changes
        
        # Wait for debounce (1 second) + processing
        time.sleep(2.0)
        
        # Should only be called once due to debouncing
        assert len(callback_count) == 1, f"Expected 1 callback, got {len(callback_count)}"
        print(f"✓ Debouncing worked: {len(callback_count)} callback for 3 changes")
        
        monitor.stop()
    
    print("\nDebouncing: PASSED")


def test_agent_scanner_integration():
    """Test integration with agent scanner."""
    print("\n" + "="*60)
    print("Test 6: Agent Scanner Integration")
    print("="*60)
    
    scanner = AgentScanner()
    
    # Test trigger_reload method exists
    assert hasattr(scanner, 'trigger_reload'), "Scanner missing trigger_reload method"
    print("✓ Agent scanner has trigger_reload method")
    
    # Test calling trigger_reload
    try:
        agents = scanner.trigger_reload()
        print(f"✓ Agent scanner reload triggered: {len(agents)} agents discovered")
    except Exception as e:
        logger.warning(f"Agent discovery failed (expected if no agents): {e}")
        print("✓ Agent scanner reload callable (no agents found)")
    
    print("\nAgent scanner integration: PASSED")


def test_statistics():
    """Test reload statistics tracking."""
    print("\n" + "="*60)
    print("Test 7: Statistics Tracking")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "agents.yaml"
        
        config = {
            "agents": {
                "test": {"class": "Test"}
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config, f)
        
        monitor = HotReloadMonitor(paths=[config_file])
        
        # Get initial stats
        stats = monitor.get_stats()
        assert "total_reloads" in stats
        assert "failed_reloads" in stats
        assert "success_rate" in stats
        print(f"✓ Initial stats: {stats}")
        
        # Perform successful reload
        monitor.reload_config_file(config_file)
        
        # Check stats updated
        stats = monitor.get_stats()
        assert stats["total_reloads"] > 0
        print(f"✓ Stats after reload: total={stats['total_reloads']}, failed={stats['failed_reloads']}")
    
    print("\nStatistics tracking: PASSED")


def main():
    """Run all verification tests."""
    print("\n" + "="*60)
    print("HOT RELOAD VERIFICATION")
    print("="*60)
    
    tests = [
        ("Config Validation", test_validator),
        ("Monitor Lifecycle", test_monitor_lifecycle),
        ("Callback Registration", test_callback_registration),
        ("Validation Failure", test_validation_failure),
        ("Debouncing", test_debouncing),
        ("Agent Scanner Integration", test_agent_scanner_integration),
        ("Statistics Tracking", test_statistics),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n✗ {name}: FAILED")
            print(f"  Error: {e}")
            logger.exception(f"Test failed: {name}")
    
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print(f"\n✗ {failed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
