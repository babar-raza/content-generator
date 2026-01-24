"""
Live LLM Smoke Tests - Wave 2 Prep

These tests make real API calls to LLM providers. They are:
- Guarded by TEST_MODE=live
- Guarded by provider-specific API keys
- Rate-limited (small prompts, minimal calls)
- Safe (no secrets logged)

Run with: pytest -m live tests/live/test_live_llm_smoke.py
"""

import os
import pytest
from .conftest import skip_if_not_live, skip_if_no_env


@pytest.mark.live
class TestOllamaLive:
    """Test Ollama local LLM (if running)."""

    @skip_if_not_live()
    @skip_if_no_env('OLLAMA_BASE_URL', 'OLLAMA_BASE_URL not set')
    def test_ollama_ping(self):
        """Test that Ollama server is reachable."""
        import requests

        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

        try:
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            assert response.status_code == 200, f"Ollama not reachable at {base_url}"
            print(f"[OK] Ollama reachable at {base_url}")
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Ollama not reachable: {e}")

    @skip_if_not_live()
    @skip_if_no_env('OLLAMA_BASE_URL', 'OLLAMA_BASE_URL not set')
    def test_ollama_tiny_prompt(self):
        """Test Ollama with a tiny deterministic prompt."""
        import requests

        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        model = os.getenv('OLLAMA_MODEL', 'llama2')

        payload = {
            "model": model,
            "prompt": "Say 'OK'",
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 5
            }
        }

        try:
            response = requests.post(
                f"{base_url}/api/generate",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                assert 'response' in data
                print(f"[OK] Ollama response received (model: {model})")
            else:
                pytest.skip(f"Ollama returned {response.status_code}")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Ollama request failed: {e}")


@pytest.mark.live
class TestOpenAILive:
    """Test OpenAI API (if API key provided)."""

    @skip_if_not_live()
    @skip_if_no_env('OPENAI_API_KEY', 'OPENAI_API_KEY not set')
    def test_openai_tiny_prompt(self):
        """Test OpenAI with a tiny prompt (costs <$0.001)."""
        try:
            from openai import OpenAI
        except ImportError:
            pytest.skip("OpenAI package not installed")

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key or api_key == 'sk-...':
            pytest.skip("OPENAI_API_KEY not configured")

        client = OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say OK"}],
                max_tokens=5,
                temperature=0
            )

            assert response.choices[0].message.content
            print("[OK] OpenAI API call succeeded")

        except Exception as e:
            pytest.fail(f"OpenAI API call failed: {e}")


@pytest.mark.live
class TestGeminiLive:
    """Test Google Gemini API (if API key provided)."""

    @skip_if_not_live()
    @skip_if_no_env('GEMINI_API_KEY', 'GEMINI_API_KEY not set')
    def test_gemini_tiny_prompt(self):
        """Test Gemini with a tiny prompt."""
        try:
            import google.generativeai as genai
        except ImportError:
            pytest.skip("google-generativeai package not installed")

        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key or api_key == 'sk-...':
            pytest.skip("GEMINI_API_KEY not configured")

        genai.configure(api_key=api_key)

        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(
                "Say OK",
                generation_config={
                    'max_output_tokens': 5,
                    'temperature': 0
                }
            )

            assert response.text
            print("[OK] Gemini API call succeeded")

        except Exception as e:
            pytest.fail(f"Gemini API call failed: {e}")


@pytest.mark.live
class TestAnthropicLive:
    """Test Anthropic Claude API (if API key provided)."""

    @skip_if_not_live()
    @skip_if_no_env('ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY not set')
    def test_anthropic_tiny_prompt(self):
        """Test Anthropic with a tiny prompt."""
        try:
            from anthropic import Anthropic
        except ImportError:
            pytest.skip("anthropic package not installed")

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key or api_key == 'sk-...':
            pytest.skip("ANTHROPIC_API_KEY not configured")

        client = Anthropic(api_key=api_key)

        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=5,
                messages=[{"role": "user", "content": "Say OK"}]
            )

            assert response.content[0].text
            print("[OK] Anthropic API call succeeded")

        except Exception as e:
            pytest.fail(f"Anthropic API call failed: {e}")
