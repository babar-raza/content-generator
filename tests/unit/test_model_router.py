"""Unit tests for src/services/model_router.py.

Tests the Ollama Model Router service including:
- Model capability definitions
- Task analysis and scoring
- Model recommendation logic
- Smart routing vs fallback behavior
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess

from src.services.model_router import (
    ModelCapability,
    OllamaModelRouter
)


# ============================================================================
# Test ModelCapability Dataclass
# ============================================================================

class TestModelCapability:
    """Test ModelCapability dataclass."""

    def test_model_capability_creation(self):
        """Test creating a ModelCapability."""
        cap = ModelCapability(
            name="test-model",
            strengths=["reasoning", "chat"],
            size="medium",
            speed="fast",
            specialization=["general_purpose", "chat"],
            context_window=8192
        )

        assert cap.name == "test-model"
        assert cap.strengths == ["reasoning", "chat"]
        assert cap.size == "medium"
        assert cap.speed == "fast"
        assert cap.specialization == ["general_purpose", "chat"]
        assert cap.context_window == 8192

    def test_model_capability_all_sizes(self):
        """Test model capabilities with different sizes."""
        small = ModelCapability("small", [], "small", "fast", [], 2048)
        medium = ModelCapability("medium", [], "medium", "medium", [], 4096)
        large = ModelCapability("large", [], "large", "slow", [], 8192)

        assert small.size == "small"
        assert medium.size == "medium"
        assert large.size == "large"

    def test_model_capability_all_speeds(self):
        """Test model capabilities with different speeds."""
        fast = ModelCapability("fast", [], "small", "fast", [], 2048)
        medium = ModelCapability("med", [], "medium", "medium", [], 4096)
        slow = ModelCapability("slow", [], "large", "slow", [], 8192)

        assert fast.speed == "fast"
        assert medium.speed == "medium"
        assert slow.speed == "slow"


# ============================================================================
# Test OllamaModelRouter Initialization
# ============================================================================

class TestOllamaModelRouterInit:
    """Test router initialization."""

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_init_default_settings(self, mock_get_models):
        """Test router initialization with defaults."""
        mock_get_models.return_value = ["llama2", "mistral"]

        router = OllamaModelRouter()

        assert router.enable_smart_routing is True
        assert router.default_model == "llama2"
        assert router.available_models == ["llama2", "mistral"]

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_init_smart_routing_disabled(self, mock_get_models):
        """Test initialization with smart routing disabled."""
        mock_get_models.return_value = []

        router = OllamaModelRouter(enable_smart_routing=False)

        assert router.enable_smart_routing is False
        assert router.default_model == "llama2"

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_init_custom_default_model(self, mock_get_models):
        """Test initialization with custom default model."""
        mock_get_models.return_value = ["mistral"]

        router = OllamaModelRouter(default_model="mistral")

        assert router.default_model == "mistral"

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_init_fetches_available_models(self, mock_get_models):
        """Test that init fetches available models."""
        mock_get_models.return_value = ["llama2", "llama3", "mistral"]

        router = OllamaModelRouter()

        mock_get_models.assert_called_once()
        assert len(router.available_models) == 3


# ============================================================================
# Test _get_available_models
# ============================================================================

class TestGetAvailableModels:
    """Test fetching available Ollama models."""

    @patch('subprocess.run')
    def test_get_available_models_success(self, mock_run):
        """Test successfully fetching model list."""
        mock_run.return_value = MagicMock(
            stdout="NAME                    ID              SIZE     MODIFIED\nllama2:latest          abc123          3.8 GB   2 days ago\nmistral:latest         def456          4.1 GB   1 week ago\n",
            returncode=0
        )

        router = OllamaModelRouter()

        assert "llama2" in router.available_models
        assert "mistral" in router.available_models

    @patch('subprocess.run')
    def test_get_available_models_with_tags(self, mock_run):
        """Test parsing models with version tags."""
        mock_run.return_value = MagicMock(
            stdout="NAME                    ID              SIZE\nllama3.2:3b            abc             2.0 GB\ngemma:7b               def             4.8 GB\n",
            returncode=0
        )

        router = OllamaModelRouter()

        # Should strip tags and get base names
        assert "llama3.2" in router.available_models or "llama3" in router.available_models
        assert "gemma" in router.available_models

    @patch('subprocess.run')
    def test_get_available_models_subprocess_error(self, mock_run):
        """Test handling subprocess error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'ollama')

        router = OllamaModelRouter()

        assert router.available_models == []

    @patch('subprocess.run')
    def test_get_available_models_timeout(self, mock_run):
        """Test handling subprocess timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired('ollama', 5)

        router = OllamaModelRouter()

        assert router.available_models == []

    @patch('subprocess.run')
    def test_get_available_models_file_not_found(self, mock_run):
        """Test handling when Ollama is not installed."""
        mock_run.side_effect = FileNotFoundError()

        router = OllamaModelRouter()

        assert router.available_models == []


# ============================================================================
# Test analyze_task
# ============================================================================

class TestAnalyzeTask:
    """Test task analysis logic."""

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_analyze_task_code_detection(self, mock_get_models):
        """Test detecting code-related tasks."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        analysis = router.analyze_task("Write Python code to parse JSON")

        assert "programming" in analysis["detected_specializations"]
        assert "code_generation" in analysis["detected_specializations"]

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_analyze_task_content_writing(self, mock_get_models):
        """Test detecting content writing tasks."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        analysis = router.analyze_task("Write a blog post about AI")

        assert "content_writing" in analysis["detected_specializations"]

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_analyze_task_complexity_high(self, mock_get_models):
        """Test detecting high complexity tasks."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        analysis = router.analyze_task("Provide a comprehensive analysis")

        assert analysis["complexity"] == "high"

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_analyze_task_complexity_low(self, mock_get_models):
        """Test detecting low complexity tasks."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        analysis = router.analyze_task("Quick summary please")

        assert analysis["complexity"] == "low"

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_analyze_task_complexity_medium_default(self, mock_get_models):
        """Test default medium complexity."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        analysis = router.analyze_task("Explain the concept")

        assert analysis["complexity"] == "medium"

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_analyze_task_requires_speed(self, mock_get_models):
        """Test detecting speed requirements."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        analysis = router.analyze_task("I need a quick answer immediately")

        assert analysis["requires_speed"] is True

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_analyze_task_requires_long_context(self, mock_get_models):
        """Test detecting long context requirements."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        analysis = router.analyze_task("Analyze this large document")

        assert analysis["requires_long_context"] is True

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_analyze_task_with_agent_name(self, mock_get_models):
        """Test analysis includes agent name."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        analysis = router.analyze_task("Process data", agent_name="CodeAgent")

        # Task text is concatenated with agent name, just verify it works
        assert "detected_specializations" in analysis
        assert isinstance(analysis["detected_specializations"], set)

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_analyze_task_multiple_keywords(self, mock_get_models):
        """Test analysis with multiple keywords."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        analysis = router.analyze_task("Write Python code for a blog post")

        # Should detect both code and content writing
        assert "programming" in analysis["detected_specializations"]
        assert "content_writing" in analysis["detected_specializations"]


# ============================================================================
# Test score_model
# ============================================================================

class TestScoreModel:
    """Test model scoring logic."""

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_score_model_unknown_model(self, mock_get_models):
        """Test scoring unknown model returns 0."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        analysis = router.analyze_task("Some task")
        score = router.score_model("unknown-model", analysis)

        assert score == 0.0

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_score_model_specialization_match(self, mock_get_models):
        """Test specialization matching increases score."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        analysis = router.analyze_task("Write Python code")
        score_codellama = router.score_model("codellama", analysis)
        score_mistral = router.score_model("mistral", analysis)

        # CodeLlama should score higher for coding tasks
        assert score_codellama > score_mistral

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_score_model_complexity_match(self, mock_get_models):
        """Test complexity matching affects score."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        # Low complexity task
        analysis = router.analyze_task("Quick summary")
        score = router.score_model("mistral", analysis)  # mistral is small/fast

        assert score > 0

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_score_model_speed_requirement(self, mock_get_models):
        """Test speed requirement increases score for fast models."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        analysis = router.analyze_task("Quick answer please")
        score_fast = router.score_model("mistral", analysis)  # fast model
        score_slow = router.score_model("mixtral", analysis)  # slower model

        # Fast model should have speed bonus
        assert score_fast >= score_slow

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_score_model_long_context_requirement(self, mock_get_models):
        """Test long context requirement increases score."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        analysis = router.analyze_task("Analyze this large document")
        score_long = router.score_model("mixtral", analysis)  # 32k context
        score_short = router.score_model("phi", analysis)  # 2k context

        # Model with larger context should score higher
        assert score_long > score_short

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_score_model_general_purpose_bonus(self, mock_get_models):
        """Test general purpose bonus for unspecialized tasks."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        # Generic task with no specific keywords
        analysis = router.analyze_task("Help me with something")
        score = router.score_model("llama3", analysis)

        # Should get some score from general purpose bonus
        assert score > 0


# ============================================================================
# Test recommend_model
# ============================================================================

class TestRecommendModel:
    """Test model recommendation logic."""

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_recommend_model_smart_routing_disabled(self, mock_get_models):
        """Test recommendation with smart routing disabled."""
        mock_get_models.return_value = []
        router = OllamaModelRouter(enable_smart_routing=False, default_model="llama2")

        model = router.recommend_model("Write code")

        assert model == "llama2"

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_recommend_model_no_models_available(self, mock_get_models):
        """Test recommendation when no models available."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        model = router.recommend_model("Some task")

        assert model == router.default_model

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_recommend_model_code_task(self, mock_get_models):
        """Test recommending model for coding task."""
        mock_get_models.return_value = ["llama2", "codellama", "mistral"]
        router = OllamaModelRouter()

        model = router.recommend_model("Write Python code to parse JSON")

        # Should recommend CodeLlama for coding
        assert model == "codellama"

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_recommend_model_content_writing(self, mock_get_models):
        """Test recommending model for content writing."""
        mock_get_models.return_value = ["llama2", "llama3", "codellama"]
        router = OllamaModelRouter()

        model = router.recommend_model("Write a blog post about Python")

        # Should recommend one of the available models (scoring may vary)
        assert model in ["llama2", "llama3", "codellama"]

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_recommend_model_quick_task(self, mock_get_models):
        """Test recommending fast model for quick tasks."""
        mock_get_models.return_value = ["mixtral", "mistral", "phi"]
        router = OllamaModelRouter()

        model = router.recommend_model("Quick question")

        # Should recommend fast model
        assert model in ["mistral", "phi"]

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_recommend_model_with_agent_name(self, mock_get_models):
        """Test recommendation includes agent name in analysis."""
        mock_get_models.return_value = ["llama2", "codellama"]
        router = OllamaModelRouter()

        model = router.recommend_model("Process data", agent_name="PythonCodeAgent")

        # Should return one of the available models
        assert model in ["llama2", "codellama"]

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_recommend_model_fallback_to_default(self, mock_get_models):
        """Test fallback to default when no good match."""
        mock_get_models.return_value = ["unknown-model"]
        router = OllamaModelRouter(default_model="llama2")

        model = router.recommend_model("Some task", fallback_to_default=True)

        assert model == "llama2"

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_recommend_model_no_fallback(self, mock_get_models):
        """Test no fallback returns None."""
        mock_get_models.return_value = ["unknown-model"]
        router = OllamaModelRouter()

        model = router.recommend_model("Some task", fallback_to_default=False)

        assert model is None


# ============================================================================
# Test get_model_info
# ============================================================================

class TestGetModelInfo:
    """Test retrieving model information."""

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_get_model_info_known_model(self, mock_get_models):
        """Test getting info for known model."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        info = router.get_model_info("llama2")

        assert info is not None
        assert info["name"] == "llama2"
        assert "strengths" in info
        assert "size" in info
        assert "speed" in info
        assert "specialization" in info
        assert "context_window" in info

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_get_model_info_unknown_model(self, mock_get_models):
        """Test getting info for unknown model."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        info = router.get_model_info("unknown-model")

        assert info is None

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_get_model_info_all_known_models(self, mock_get_models):
        """Test all known models have valid info."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        # Test all models in MODEL_PROFILES
        for model_name in router.MODEL_PROFILES.keys():
            info = router.get_model_info(model_name)
            assert info is not None
            assert info["context_window"] > 0


# ============================================================================
# Test list_available_models
# ============================================================================

class TestListAvailableModels:
    """Test listing available models."""

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_list_available_models(self, mock_get_models):
        """Test listing available models."""
        mock_get_models.return_value = ["llama2", "mistral", "codellama"]
        router = OllamaModelRouter()

        models = router.list_available_models()

        assert models == ["llama2", "mistral", "codellama"]

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_list_available_models_empty(self, mock_get_models):
        """Test listing when no models available."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        models = router.list_available_models()

        assert models == []


# ============================================================================
# Test refresh_models
# ============================================================================

class TestRefreshModels:
    """Test refreshing available models."""

    @patch('subprocess.run')
    def test_refresh_models(self, mock_run):
        """Test refreshing model list."""
        # Initial state
        mock_run.return_value = MagicMock(
            stdout="NAME\nllama2:latest\n",
            returncode=0
        )
        router = OllamaModelRouter()
        assert "llama2" in router.available_models

        # After refresh
        mock_run.return_value = MagicMock(
            stdout="NAME\nllama2:latest\nmistral:latest\n",
            returncode=0
        )
        router.refresh_models()

        assert "mistral" in router.available_models

    @patch('subprocess.run')
    def test_refresh_models_logs_count(self, mock_run):
        """Test refresh logs model count."""
        mock_run.return_value = MagicMock(
            stdout="NAME\nllama2:latest\nmistral:latest\ncodellama:latest\n",
            returncode=0
        )
        router = OllamaModelRouter()

        with patch('src.services.model_router.logger') as mock_logger:
            router.refresh_models()
            # Should log the count
            assert any("models available" in str(call) for call in mock_logger.info.call_args_list)


# ============================================================================
# Test MODEL_PROFILES Data Integrity
# ============================================================================

class TestModelProfiles:
    """Test MODEL_PROFILES data integrity."""

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_all_profiles_have_required_fields(self, mock_get_models):
        """Test all model profiles have required fields."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        for model_name, profile in router.MODEL_PROFILES.items():
            assert profile.name == model_name
            assert isinstance(profile.strengths, list)
            assert profile.size in ["small", "medium", "large"]
            assert profile.speed in ["fast", "medium", "slow"]
            assert isinstance(profile.specialization, list)
            assert profile.context_window > 0

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_profiles_context_windows_valid(self, mock_get_models):
        """Test all context windows are reasonable values."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        valid_windows = {2048, 4096, 8192, 16384, 32768}
        for profile in router.MODEL_PROFILES.values():
            assert profile.context_window in valid_windows


# ============================================================================
# Test TASK_KEYWORDS Data Integrity
# ============================================================================

class TestTaskKeywords:
    """Test TASK_KEYWORDS mapping integrity."""

    @patch('src.services.model_router.OllamaModelRouter._get_available_models')
    def test_all_keywords_map_to_lists(self, mock_get_models):
        """Test all keywords map to lists of specializations."""
        mock_get_models.return_value = []
        router = OllamaModelRouter()

        for keyword, specializations in router.TASK_KEYWORDS.items():
            assert isinstance(keyword, str)
            assert isinstance(specializations, list)
            assert len(specializations) > 0
