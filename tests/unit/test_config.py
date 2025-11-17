"""Unit tests for src/core/config.py - config precedence."""

import os
import tempfile
import json
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import Config, LLMConfig, DatabaseConfig, MeshConfig, OrchestrationConfig


class TestConfigPrecedence:
    """Test config precedence: defaults → file → env; env override wins."""

    def setup_method(self):
        """Reset environment before each test."""
        # Clear any existing env vars
        env_vars = [
            'GEMINI_API_KEY', 'OPENAI_API_KEY', 'OLLAMA_BASE_URL',
            'CHROMA_DB_PATH', 'MESH_ENABLED', 'ORCHESTRATION_ENABLED',
            'LOG_LEVEL', 'FORCE_DEVICE'
        ]
        for var in env_vars:
            os.environ.pop(var, None)

    def teardown_method(self):
        """Clean up after each test."""
        self.setup_method()

    def test_defaults_only(self):
        """Test default configuration values."""
        config = Config()

        # Check default paths
        assert config.config_dir == Path("./config")
        assert config.templates_dir == Path("./templates")
        assert config.output_dir == Path("./output")

        # Check default LLM config
        assert config.llm.ollama_base_url == "http://localhost:11434"
        assert config.llm.default_model == "gemini-1.5-flash"
        assert config.llm.temperature == 0.7

        # Check default database config
        assert config.database.chroma_db_path == "./chroma_db"
        assert config.database.collection_name == "blog_knowledge"

        # Check default mesh config
        assert config.mesh.enabled == False
        assert config.mesh.registry_timeout == 2.0

        # Check default orchestration config
        assert config.orchestration.enabled == False
        assert config.orchestration.ops_console_port == 8080

    @patch('torch.cuda.is_available', return_value=True)
    def test_cuda_auto_detection_enabled(self, mock_cuda):
        """Test CUDA auto-detection when available."""
        config = Config()
        assert config.device == "cuda"

    @patch('torch.cuda.is_available', return_value=False)
    def test_cuda_auto_detection_disabled(self, mock_cuda):
        """Test CPU fallback when CUDA not available."""
        config = Config()
        assert config.device == "cpu"

    def test_env_override_wins(self):
        """Test that environment variables override defaults."""
        # Set environment variables
        os.environ['GEMINI_API_KEY'] = 'test_gemini_key'
        os.environ['OPENAI_API_KEY'] = 'test_openai_key'
        os.environ['OLLAMA_BASE_URL'] = 'http://custom:11434'
        os.environ['CHROMA_DB_PATH'] = '/custom/db/path'
        os.environ['MESH_ENABLED'] = 'true'
        os.environ['ORCHESTRATION_ENABLED'] = 'true'
        os.environ['LOG_LEVEL'] = 'DEBUG'
        os.environ['FORCE_DEVICE'] = 'cuda'

        config = Config()
        config.load_from_env()

        # Check env vars override defaults
        assert config.llm.gemini_api_key == 'test_gemini_key'
        assert config.llm.openai_api_key == 'test_openai_key'
        assert config.llm.ollama_base_url == 'http://custom:11434'
        assert config.database.chroma_db_path == '/custom/db/path'
        assert config.mesh.enabled == True
        assert config.enable_mesh == True
        assert config.orchestration.enabled == True
        assert config.enable_orchestration == True
        assert config.log_level == 'DEBUG'

    def test_force_device_env_var(self):
        """Test FORCE_DEVICE environment variable."""
        os.environ['FORCE_DEVICE'] = 'cpu'

        config = Config()
        config.load_from_env()
        assert config.device == "cpu"  # Should be overridden by env var

    def test_family_detection_from_path(self):
        """Test API family detection from file paths."""
        test_cases = [
            (Path("words/api/document.md"), "words"),
            (Path("cells/api/workbook.md"), "cells"),
            (Path("pdf/api/document.md"), "pdf"),
            (Path("slides/api/presentation.md"), "slides"),
            (Path("email/api/message.md"), "email"),
            (Path("barcode/api/barcode.md"), "barcode"),
            (Path("diagram/api/diagram.md"), "diagram"),
            (Path("tasks/api/project.md"), "tasks"),
            (Path("ocr/api/image.md"), "ocr"),
            (Path("note/api/notebook.md"), "note"),
            (Path("imaging/api/image.md"), "imaging"),
            (Path("zip/api/archive.md"), "zip"),
            (Path("unknown/api/file.md"), "general"),
        ]

        for path, expected_family in test_cases:
            assert Config.detect_family_from_path(path) == expected_family

    def test_family_name_mapping(self):
        """Test family name mapping for API products."""
        config = Config()

        assert config.FAMILY_NAME_MAP['words'] == 'Aspose.Words'
        assert config.FAMILY_NAME_MAP['cells'] == 'Aspose.Cells'
        assert config.FAMILY_NAME_MAP['pdf'] == 'Aspose.PDF'
        assert config.FAMILY_NAME_MAP['slides'] == 'Aspose.Slides'

    def test_tone_config_loading(self):
        """Test loading tone configuration from JSON file."""
        config = Config()

        # Create temporary tone.json
        with tempfile.TemporaryDirectory() as temp_dir:
            config.config_dir = Path(temp_dir)
            tone_file = config.config_dir / "tone.json"

            test_tone = {
                "professional": {"formality": "high", "tone": "formal"},
                "casual": {"formality": "low", "tone": "conversational"}
            }

            tone_file.write_text(json.dumps(test_tone))

            loaded_tone = config.load_tone_config()
            assert loaded_tone == test_tone

    def test_tone_config_missing_file(self):
        """Test tone config loading when file doesn't exist."""
        config = Config()

        with tempfile.TemporaryDirectory() as temp_dir:
            config.config_dir = Path(temp_dir)

            loaded_tone = config.load_tone_config()
            assert loaded_tone == {}  # Should return empty dict

    def test_get_template_method(self):
        """Test template retrieval with naming convention."""
        config = Config()

        # Mock templates
        config._templates = {
            "blog_templates": {"title": "Blog Template"},
            "code_templates": {"language": "Python"},
            "workflows": {"steps": ["step1", "step2"]}
        }

        # Test with template type
        assert config.get_template("blog") == {"title": "Blog Template"}
        assert config.get_template("code") == {"language": "Python"}

        # Test direct template name
        assert config.get_template("workflows") == {"steps": ["step1", "step2"]}

        # Test non-existent template
        assert config.get_template("nonexistent") == {}

    def test_config_dataclasses_immutable_defaults(self):
        """Test that config dataclasses have proper default values."""
        llm_config = LLMConfig()
        assert llm_config.ollama_base_url == "http://localhost:11434"
        assert llm_config.temperature == 0.7

        db_config = DatabaseConfig()
        assert db_config.chroma_db_path == "./chroma_db"
        assert db_config.collection_name == "blog_knowledge"

        mesh_config = MeshConfig()
        assert mesh_config.enabled == False
        assert mesh_config.max_workers == 4

        orch_config = OrchestrationConfig()
        assert orch_config.enabled == False
        assert orch_config.ops_console_port == 8080
# DOCGEN:LLM-FIRST@v4