#!/usr/bin/env python3
"""Ollama performance diagnostic - check if Ollama is responding slowly.

Usage:
    python check_ollama.py
"""

import time
import requests
import json

def check_ollama_health():
    """Check Ollama health and performance."""
    print("\n" + "="*80)
    print("OLLAMA DIAGNOSTIC")
    print("="*80 + "\n")
    
    # Check if Ollama is running
    try:
        start = time.time()
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            print(f"✓ Ollama is running (response time: {elapsed:.2f}s)")
            
            # Get available models
            data = response.json()
            models = data.get('models', [])
            print(f"\n📦 Available Models: {len(models)}")
            for model in models:
                name = model.get('name', 'unknown')
                size = model.get('size', 0) / (1024**3)  # Convert to GB
                print(f"  • {name} ({size:.1f} GB)")
        else:
            print(f"✗ Ollama returned status {response.status_code}")
            return
            
    except requests.exceptions.Timeout:
        print("✗ Ollama not responding (timeout after 5s)")
        print("  Check if Ollama is running: ollama serve")
        return
    except Exception as e:
        print(f"✗ Cannot connect to Ollama: {e}")
        print("  Is Ollama running on localhost:11434?")
        return
    
    # Test generation speed
    print("\n🧪 Testing generation speed...")
    print("  (This will generate a short response with qwen2.5:14b)")
    
    test_payload = {
        "model": "qwen2.5:14b",
        "messages": [
            {"role": "user", "content": "Write a single sentence about Python programming."}
        ],
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }
    
    try:
        start = time.time()
        response = requests.post(
            "http://localhost:11434/api/chat",
            json=test_payload,
            timeout=60
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            result = response.json()
            output = result.get('message', {}).get('content', '')
            tokens = len(output.split())
            tokens_per_sec = tokens / elapsed if elapsed > 0 else 0
            
            print(f"\n✓ Generation completed in {elapsed:.2f}s")
            print(f"  Output: {output[:100]}...")
            print(f"  Speed: ~{tokens_per_sec:.1f} tokens/sec")
            
            if elapsed > 10:
                print(f"\n⚠ WARNING: Generation is slow ({elapsed:.2f}s for short text)")
                print("  This could significantly delay blog generation.")
                print("  Consider:")
                print("    • Using a smaller/faster model (e.g., mistral:latest)")
                print("    • Checking GPU availability")
                print("    • Checking system resources (CPU/RAM/GPU)")
            elif elapsed > 5:
                print(f"\n⚠ Generation is moderately slow ({elapsed:.2f}s)")
                print("  Blog generation may take 10-20 minutes.")
            else:
                print(f"\n✓ Generation speed is good!")
                
        else:
            print(f"✗ Generation failed with status {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("✗ Generation timed out after 60s")
        print("  This is too slow for blog generation!")
    except Exception as e:
        print(f"✗ Generation test failed: {e}")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    check_ollama_health()
# DOCGEN:LLM-FIRST@v4