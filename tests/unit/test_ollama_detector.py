"""Unit tests for src/utils/ollama_detector.py.

Tests Ollama model detection and management including:
- Ollama availability checking
- Model discovery (API and CLI)
- Capability detection
- Model recommendations
- Configuration validation
- Global detector instance
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import requests

from src.utils.ollama_detector import (
    OllamaDetector,
    OllamaModel,
    get_ollama_detector,
    check_ollama_setup
)


# ============================================================================
# Test OllamaModel
# ============================================================================

class TestOllamaModel:
    """Test OllamaModel dataclass."""

    def test_ollama_model_creation(self):
        """Test creating OllamaModel instance."""
        model = OllamaModel(
            name="llama2",
            size="3.8 GB",
            modified="2024-01-15",
            capabilities=["content", "topic"]
        )
        assert model.name == "llama2"
        assert model.size == "3.8 GB"
        assert model.modified == "2024-01-15"
        assert model.capabilities == ["content", "topic"]


# ============================================================================
# Test OllamaDetector.__init__
# ============================================================================

class TestOllamaDetectorInit:
    """Test OllamaDetector initialization."""

    def test_init_default_url(self):
        """Test initialization with default base URL."""
        detector = OllamaDetector()
        assert detector.base_url == "http://localhost:11434"
        assert detector._models_cache is None

    def test_init_custom_url(self):
        """Test initialization with custom base URL."""
        detector = OllamaDetector(base_url="http://custom:8080")
        assert detector.base_url == "http://custom:8080"

    def test_init_has_capability_mappings(self):
        """Test initialization includes capability mappings."""
        detector = OllamaDetector()
        assert "code" in detector.model_capabilities
        assert "content" in detector.model_capabilities
        assert "topic" in detector.model_capabilities


# ============================================================================
# Test is_ollama_available
# ============================================================================

class TestIsOllamaAvailable:
    """Test is_ollama_available method."""

    @patch('requests.get')
    def test_available_with_models(self, mock_get):
        """Test Ollama is available with models."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama2'},
                {'name': 'mistral'}
            ]
        }
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        available, message = detector.is_ollama_available()

        assert available is True
        assert "2 model(s)" in message

    @patch('requests.get')
    def test_available_no_models(self, mock_get):
        """Test Ollama available but no models."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'models': []}
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        available, message = detector.is_ollama_available()

        assert available is True
        assert "0 model(s)" in message

    @patch('requests.get')
    def test_not_available_bad_status(self, mock_get):
        """Test Ollama returns bad status code."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        available, message = detector.is_ollama_available()

        assert available is False
        assert "status 500" in message

    @patch('requests.get')
    def test_not_available_connection_error(self, mock_get):
        """Test Ollama connection error."""
        mock_get.side_effect = requests.ConnectionError()

        detector = OllamaDetector()
        available, message = detector.is_ollama_available()

        assert available is False
        assert "not running" in message.lower() or "connection refused" in message.lower()

    @patch('requests.get')
    def test_not_available_timeout(self, mock_get):
        """Test Ollama connection timeout."""
        mock_get.side_effect = requests.Timeout()

        detector = OllamaDetector()
        available, message = detector.is_ollama_available()

        assert available is False
        assert "timeout" in message.lower()

    @patch('requests.get')
    def test_not_available_general_exception(self, mock_get):
        """Test Ollama general exception."""
        mock_get.side_effect = Exception("Unknown error")

        detector = OllamaDetector()
        available, message = detector.is_ollama_available()

        assert available is False
        assert "Error checking Ollama" in message


# ============================================================================
# Test get_installed_models
# ============================================================================

class TestGetInstalledModels:
    """Test get_installed_models method."""

    @patch('requests.get')
    def test_get_models_via_api(self, mock_get):
        """Test getting models via API."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {
                    'name': 'llama2:latest',
                    'size': '3.8 GB',
                    'modified_at': '2024-01-15T10:00:00Z'
                },
                {
                    'name': 'codellama:7b',
                    'size': '3.5 GB',
                    'modified_at': '2024-01-10T12:00:00Z'
                }
            ]
        }
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        models = detector.get_installed_models()

        assert len(models) == 2
        assert models[0].name == 'llama2:latest'
        assert models[1].name == 'codellama:7b'
        assert 'content' in models[0].capabilities
        assert 'code' in models[1].capabilities

    @patch('requests.get')
    def test_get_models_caches_result(self, mock_get):
        """Test model results are cached."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'models': [{'name': 'llama2'}]}
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        models1 = detector.get_installed_models()
        models2 = detector.get_installed_models()

        assert models1 == models2
        # API should only be called once due to caching
        assert mock_get.call_count == 1

    @patch('subprocess.run')
    @patch('requests.get')
    def test_get_models_fallback_to_cli(self, mock_get, mock_run):
        """Test fallback to CLI when API fails."""
        # API fails
        mock_get.side_effect = Exception("API error")

        # CLI succeeds
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """NAME                SIZE    MODIFIED
llama2:latest       3.8 GB  2 days ago
mistral:latest      4.1 GB  1 week ago"""
        mock_run.return_value = mock_result

        detector = OllamaDetector()
        models = detector.get_installed_models()

        assert len(models) == 2
        assert models[0].name == 'llama2:latest'
        assert models[1].name == 'mistral:latest'

    @patch('subprocess.run')
    @patch('requests.get')
    def test_get_models_both_fail(self, mock_get, mock_run):
        """Test when both API and CLI fail."""
        mock_get.side_effect = Exception("API error")
        mock_run.side_effect = Exception("CLI error")

        detector = OllamaDetector()
        models = detector.get_installed_models()

        assert models == []

    @patch('requests.get')
    def test_get_models_empty_response(self, mock_get):
        """Test with empty models response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'models': []}
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        models = detector.get_installed_models()

        assert models == []


# ============================================================================
# Test _detect_capabilities
# ============================================================================

class TestDetectCapabilities:
    """Test _detect_capabilities method."""

    def test_detect_code_capability(self):
        """Test detecting code capability."""
        detector = OllamaDetector()

        assert 'code' in detector._detect_capabilities('codellama')
        assert 'code' in detector._detect_capabilities('deepseek-coder')
        assert 'code' in detector._detect_capabilities('starcoder')

    def test_detect_content_capability(self):
        """Test detecting content capability."""
        detector = OllamaDetector()

        assert 'content' in detector._detect_capabilities('llama2')
        assert 'content' in detector._detect_capabilities('mistral')
        assert 'content' in detector._detect_capabilities('gemma')

    def test_detect_multiple_capabilities(self):
        """Test detecting multiple capabilities."""
        detector = OllamaDetector()

        capabilities = detector._detect_capabilities('qwen')
        assert 'code' in capabilities
        assert 'content' in capabilities
        # qwen matches: code, content, research, analysis based on model_capabilities
        assert len(capabilities) >= 2

    def test_detect_general_capability_fallback(self):
        """Test fallback to general capability."""
        detector = OllamaDetector()

        capabilities = detector._detect_capabilities('unknown-model')
        assert capabilities == ['general']

    def test_detect_case_insensitive(self):
        """Test capability detection is case insensitive."""
        detector = OllamaDetector()

        capabilities = detector._detect_capabilities('CodeLlama')
        assert 'code' in capabilities


# ============================================================================
# Test get_best_model_for_capability
# ============================================================================

class TestGetBestModelForCapability:
    """Test get_best_model_for_capability method."""

    @patch('requests.get')
    def test_get_best_for_code(self, mock_get):
        """Test getting best model for code capability."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama2', 'size': '3.8 GB', 'modified_at': '2024-01-15'},
                {'name': 'codellama', 'size': '3.5 GB', 'modified_at': '2024-01-10'}
            ]
        }
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        best_model = detector.get_best_model_for_capability('code')

        assert best_model == 'codellama'

    @patch('requests.get')
    def test_get_best_fallback_to_general(self, mock_get):
        """Test fallback when no specific capability match."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'unknown-model', 'size': '3.8 GB', 'modified_at': '2024-01-15'}
            ]
        }
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        best_model = detector.get_best_model_for_capability('nonexistent')

        # Should return first available model as last resort
        assert best_model == 'unknown-model'

    @patch('requests.get')
    def test_get_best_no_models(self, mock_get):
        """Test when no models available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'models': []}
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        best_model = detector.get_best_model_for_capability('code')

        assert best_model is None


# ============================================================================
# Test get_model_recommendations
# ============================================================================

class TestGetModelRecommendations:
    """Test get_model_recommendations method."""

    @patch('requests.get')
    def test_get_recommendations(self, mock_get):
        """Test getting model recommendations."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama2', 'size': '3.8 GB', 'modified_at': '2024-01-15'},
                {'name': 'codellama', 'size': '3.5 GB', 'modified_at': '2024-01-10'}
            ]
        }
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        recommendations = detector.get_model_recommendations()

        assert 'code' in recommendations
        assert 'codellama' in recommendations['code']
        assert 'content' in recommendations
        assert 'llama2' in recommendations['content']

    @patch('requests.get')
    def test_get_recommendations_empty(self, mock_get):
        """Test recommendations with no models."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'models': []}
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        recommendations = detector.get_model_recommendations()

        assert recommendations == {}


# ============================================================================
# Test validate_model_config
# ============================================================================

class TestValidateModelConfig:
    """Test validate_model_config method."""

    @patch('requests.get')
    def test_validate_valid_config(self, mock_get):
        """Test validation of valid config."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama2', 'size': '3.8 GB', 'modified_at': '2024-01-15'},
                {'name': 'codellama', 'size': '3.5 GB', 'modified_at': '2024-01-10'}
            ]
        }
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        config = {
            'content': 'llama2',
            'code': 'codellama'
        }
        is_valid, warnings = detector.validate_model_config(config)

        assert is_valid is True
        assert len(warnings) == 0

    @patch('requests.get')
    def test_validate_invalid_model(self, mock_get):
        """Test validation with invalid model."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama2', 'size': '3.8 GB', 'modified_at': '2024-01-15'}
            ]
        }
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        config = {
            'code': 'nonexistent-model'
        }
        is_valid, warnings = detector.validate_model_config(config)

        assert is_valid is False
        assert len(warnings) > 0
        assert 'nonexistent-model' in warnings[0]

    @patch('requests.get')
    def test_validate_suggests_alternative(self, mock_get):
        """Test validation suggests alternatives."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'codellama', 'size': '3.5 GB', 'modified_at': '2024-01-10'}
            ]
        }
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        config = {
            'code': 'nonexistent'
        }
        is_valid, warnings = detector.validate_model_config(config)

        assert is_valid is False
        # Should suggest codellama as alternative for code
        assert any('codellama' in w for w in warnings)

    @patch('requests.get')
    def test_validate_no_models_installed(self, mock_get):
        """Test validation with no models installed."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'models': []}
        mock_get.return_value = mock_response

        detector = OllamaDetector()
        config = {'code': 'llama2'}
        is_valid, warnings = detector.validate_model_config(config)

        assert is_valid is False
        assert any('No Ollama models installed' in w for w in warnings)


# ============================================================================
# Test get_ollama_detector (Global Instance)
# ============================================================================

class TestGetOllamaDetector:
    """Test get_ollama_detector global instance function."""

    def test_returns_detector_instance(self):
        """Test returns OllamaDetector instance."""
        detector = get_ollama_detector()
        assert isinstance(detector, OllamaDetector)

    def test_returns_same_instance(self):
        """Test returns same global instance."""
        # Reset global instance first
        import src.utils.ollama_detector as module
        module._detector = None

        detector1 = get_ollama_detector()
        detector2 = get_ollama_detector()

        assert detector1 is detector2

    def test_custom_base_url(self):
        """Test with custom base URL."""
        # Reset global instance
        import src.utils.ollama_detector as module
        module._detector = None

        detector = get_ollama_detector(base_url="http://custom:9999")
        assert detector.base_url == "http://custom:9999"


# ============================================================================
# Test check_ollama_setup
# ============================================================================

class TestCheckOllamaSetup:
    """Test check_ollama_setup function."""

    @patch('requests.get')
    def test_check_setup_available(self, mock_get):
        """Test setup check when Ollama is available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama2', 'size': '3.8 GB', 'modified_at': '2024-01-15'},
                {'name': 'codellama', 'size': '3.5 GB', 'modified_at': '2024-01-10'}
            ]
        }
        mock_get.return_value = mock_response

        # Reset global detector
        import src.utils.ollama_detector as module
        module._detector = None

        result = check_ollama_setup()

        assert result['available'] is True
        assert result['models_count'] == 2
        assert len(result['models']) == 2
        assert result['base_url'] == "http://localhost:11434"
        assert 'recommendations' in result

    @patch('requests.get')
    def test_check_setup_not_available(self, mock_get):
        """Test setup check when Ollama is not available."""
        mock_get.side_effect = requests.ConnectionError()

        # Reset global detector
        import src.utils.ollama_detector as module
        module._detector = None

        result = check_ollama_setup()

        assert result['available'] is False
        assert result['models_count'] == 0
        assert len(result['models']) == 0
        assert 'not running' in result['status'].lower() or 'connection refused' in result['status'].lower()

    @patch('requests.get')
    def test_check_setup_custom_url(self, mock_get):
        """Test setup check with custom URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'models': []}
        mock_get.return_value = mock_response

        # Reset global detector
        import src.utils.ollama_detector as module
        module._detector = None

        result = check_ollama_setup(base_url="http://custom:8080")

        assert result['base_url'] == "http://custom:8080"


# ============================================================================
# Test Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @patch('requests.get')
    def test_full_workflow(self, mock_get):
        """Test complete workflow from check to recommendation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama2:latest', 'size': '3.8 GB', 'modified_at': '2024-01-15'},
                {'name': 'codellama:7b', 'size': '3.5 GB', 'modified_at': '2024-01-10'},
                {'name': 'mistral:latest', 'size': '4.1 GB', 'modified_at': '2024-01-12'}
            ]
        }
        mock_get.return_value = mock_response

        detector = OllamaDetector()

        # Check availability
        available, status = detector.is_ollama_available()
        assert available is True
        assert "3 model(s)" in status

        # Get models
        models = detector.get_installed_models()
        assert len(models) == 3

        # Get recommendations
        recommendations = detector.get_model_recommendations()
        assert 'code' in recommendations
        assert 'content' in recommendations

        # Get best for specific capability
        best_code = detector.get_best_model_for_capability('code')
        assert 'codellama' in best_code.lower()

        # Validate config
        config = {
            'content': 'llama2:latest',
            'code': 'codellama:7b'
        }
        is_valid, warnings = detector.validate_model_config(config)
        assert is_valid is True
        assert len(warnings) == 0

    @patch('requests.get')
    def test_model_not_found_workflow(self, mock_get):
        """Test workflow when configured model not found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama2', 'size': '3.8 GB', 'modified_at': '2024-01-15'}
            ]
        }
        mock_get.return_value = mock_response

        detector = OllamaDetector()

        # Try to validate config with missing model
        config = {
            'code': 'gpt-4'  # Not an Ollama model
        }
        is_valid, warnings = detector.validate_model_config(config)

        assert is_valid is False
        assert len(warnings) > 0
        assert 'gpt-4' in warnings[0]
        # Should suggest alternative
        assert any('Consider using' in w for w in warnings)
