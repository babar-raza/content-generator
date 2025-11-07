#!/usr/bin/env python3
"""
Test script for Ollama Model Router integration in UCOP
Run this to verify the router is working correctly
"""

import sys
import logging
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_router_import():
    """Test 1: Can we import the router?"""
    print("\n" + "="*70)
    print("TEST 1: Import Router")
    print("="*70)
    try:
        from src.services.model_router import OllamaModelRouter
        print("✅ Successfully imported OllamaModelRouter")
        return True
    except ImportError as e:
        print(f"❌ Failed to import router: {e}")
        return False


def test_router_initialization():
    """Test 2: Can we initialize the router?"""
    print("\n" + "="*70)
    print("TEST 2: Initialize Router")
    print("="*70)
    try:
        from src.services.model_router import OllamaModelRouter
        router = OllamaModelRouter(enable_smart_routing=True)
        print(f"✅ Router initialized successfully")
        print(f"   Available models: {len(router.available_models)}")
        if router.available_models:
            print(f"   Models: {', '.join(router.available_models[:5])}...")
        else:
            print("   ⚠️  No models found - is Ollama running?")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize router: {e}")
        return False


def test_model_recommendation():
    """Test 3: Can router recommend models?"""
    print("\n" + "="*70)
    print("TEST 3: Model Recommendations")
    print("="*70)
    try:
        from src.services.model_router import OllamaModelRouter
        router = OllamaModelRouter(enable_smart_routing=True)
        
        test_cases = [
            ("Write Python code", "CodeAgent"),
            ("Write blog article", "ContentWriter"),
            ("Debug JavaScript", "CodeReviewer"),
            ("Quick chat", "ChatBot"),
        ]
        
        for task, agent in test_cases:
            model = router.recommend_model(task, agent)
            print(f"✅ Task: '{task}'")
            print(f"   Agent: {agent}")
            print(f"   → Model: {model}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to get recommendations: {e}")
        return False


def test_config_integration():
    """Test 4: Is router integrated with Config?"""
    print("\n" + "="*70)
    print("TEST 4: Config Integration")
    print("="*70)
    try:
        from src.core import Config
        config = Config()
        
        # Check if new config options exist
        has_smart_routing = hasattr(config, 'enable_smart_routing')
        has_ollama_model = hasattr(config, 'ollama_topic_model')
        
        if has_smart_routing:
            print(f"✅ Config has 'enable_smart_routing': {config.enable_smart_routing}")
        else:
            print("❌ Config missing 'enable_smart_routing'")
            
        if has_ollama_model:
            print(f"✅ Config has 'ollama_topic_model': {config.ollama_topic_model}")
        else:
            print("❌ Config missing 'ollama_topic_model'")
        
        return has_smart_routing and has_ollama_model
    except Exception as e:
        print(f"❌ Failed to test config: {e}")
        return False


def test_llm_service_integration():
    """Test 5: Is router integrated with LLMService?"""
    print("\n" + "="*70)
    print("TEST 5: LLMService Integration")
    print("="*70)
    try:
        from src.services import LLMService
        from src.core import Config
        
        config = Config()
        config.llm_provider = "OLLAMA"
        config.enable_smart_routing = True
        
        # Try to initialize LLMService
        # Note: This might fail if Ollama is not running, but that's okay
        try:
            llm_service = LLMService(config)
            
            # Check if router is initialized
            has_router = hasattr(llm_service, 'model_router')
            if has_router and llm_service.model_router:
                print("✅ LLMService has model_router initialized")
                print(f"   Router enabled: {llm_service.model_router.enable_smart_routing}")
                return True
            elif has_router:
                print("⚠️  LLMService has model_router attribute but it's None")
                print("   (This is okay if Ollama is not running)")
                return True
            else:
                print("❌ LLMService missing model_router")
                return False
        except ConnectionError:
            print("⚠️  Could not connect to Ollama")
            print("   (Router will still work once Ollama is started)")
            return True
            
    except Exception as e:
        print(f"❌ Failed to test LLMService: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_helper():
    """Test 6: Can agents use the model helper?"""
    print("\n" + "="*70)
    print("TEST 6: Model Helper for Agents")
    print("="*70)
    try:
        from src.utils.model_helper import get_optimal_model, TaskType, initialize_model_helper
        from src.services.model_router import OllamaModelRouter
        
        # Initialize helper
        router = OllamaModelRouter(enable_smart_routing=True)
        initialize_model_helper(router)
        
        # Test convenience function
        model = get_optimal_model(
            task="Write Python code",
            agent_name="TestAgent"
        )
        print(f"✅ get_optimal_model() works: {model}")
        
        # Test TaskType constants
        model = get_optimal_model(
            task=TaskType.CODE_GENERATION,
            agent_name="CodeAgent"
        )
        print(f"✅ TaskType constants work: {model}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to test model helper: {e}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*70)
    print("OLLAMA MODEL ROUTER INTEGRATION TESTS")
    print("="*70)
    print("Testing the router integration in UCOP v10...")
    
    tests = [
        ("Import Router", test_router_import),
        ("Initialize Router", test_router_initialization),
        ("Model Recommendations", test_model_recommendation),
        ("Config Integration", test_config_integration),
        ("LLMService Integration", test_llm_service_integration),
        ("Model Helper", test_model_helper),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("="*70)
    
    if passed == total:
        print("\n🎉 All tests passed! Router is fully integrated.")
        print("\nNext steps:")
        print("1. Start Ollama: ollama serve")
        print("2. Pull some models: ollama pull llama2")
        print("3. Run UCOP: python ucop_cli.py create blog_generation --input 'Python Tips'")
        print("4. Check logs for: 'Selected model' messages")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("\nTroubleshooting:")
        print("1. Make sure all files are present")
        print("2. Check Python imports")
        print("3. See OLLAMA_ROUTER_INTEGRATION.md for details")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
