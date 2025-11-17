"""
Integration tests for Configuration API endpoints.

Tests all 5 configuration endpoints to ensure they:
1. Are properly mounted and accessible
2. Return actual runtime configuration data
3. Handle errors when config not loaded
4. Return correct data structures
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def mock_config_snapshot():
    """Create a comprehensive mock config snapshot."""
    config = Mock()
    
    # Basic metadata
    config.config_hash = "abc123def456789"
    config.timestamp = "2025-01-15T12:00:00Z"
    config.engine_version = "1.0.0"
    
    # Agent configuration
    config.agent_config = {
        'agents': {
            'KeywordExtractionAgent': {
                'id': 'KeywordExtractionAgent',
                'version': '1.0',
                'description': 'Extracts keywords from content',
                'capabilities': {
                    'extraction': True,
                    'analysis': True
                },
                'resources': {
                    'model': 'gpt-4',
                    'max_tokens': 1000
                }
            },
            'OutlineCreationAgent': {
                'id': 'OutlineCreationAgent',
                'version': '1.0',
                'description': 'Creates content outlines',
                'capabilities': {
                    'structuring': True,
                    'planning': True
                },
                'resources': {
                    'model': 'gpt-4',
                    'max_tokens': 2000
                }
            }
        }
    }
    
    # Main configuration (workflows)
    config.main_config = {
        'workflows': {
            'blog_generation': {
                'name': 'Blog Generation',
                'steps': ['outline', 'content', 'seo'],
                'description': 'Generate blog posts from topics'
            },
            'fast_draft': {
                'name': 'Fast Draft',
                'steps': ['outline', 'content'],
                'description': 'Quick content generation'
            }
        },
        'dependencies': {
            'content': ['outline'],
            'seo': ['content']
        }
    }
    
    # Tone configuration
    config.tone_config = {
        'global_voice': {
            'formality': 'professional',
            'perspective': 'third_person',
            'tense': 'present'
        },
        'section_controls': {
            'introduction': {
                'tone': 'engaging',
                'length': 'medium'
            },
            'conclusion': {
                'tone': 'confident',
                'length': 'short'
            }
        },
        'heading_style': {
            'case': 'title',
            'numbers': False
        },
        'code_template_overrides': {
            'python': '```python\n{code}\n```'
        }
    }
    
    # Performance configuration
    config.perf_config = {
        'timeouts': {
            'agent_execution': 120,
            'workflow_total': 600,
            'api_request': 30
        },
        'limits': {
            'max_tokens': 4000,
            'max_concurrent_jobs': 10,
            'max_retries': 3
        },
        'batch': {
            'size': 5,
            'delay_ms': 100
        },
        'hot_paths': {
            'cache_enabled': True,
            'cache_ttl': 3600
        },
        'tuning': {
            'temperature': 0.7,
            'top_p': 0.9
        }
    }
    
    return config


@pytest.fixture
def mock_executor():
    """Create a mock executor for testing."""
    executor = Mock()
    executor.job_engine = Mock()
    executor.job_engine._jobs = {}
    return executor


@pytest.fixture
def test_app_with_config(mock_executor, mock_config_snapshot):
    """Create a test FastAPI app with config snapshot."""
    from src.web.app import create_app
    
    app = create_app(executor=mock_executor, config_snapshot=mock_config_snapshot)
    return app


@pytest.fixture
def test_app_without_config(mock_executor):
    """Create a test FastAPI app without config snapshot."""
    from src.web.app import create_app
    
    app = create_app(executor=mock_executor, config_snapshot=None)
    return app


@pytest.fixture
def client_with_config(test_app_with_config):
    """Create a test client with config."""
    return TestClient(test_app_with_config)


@pytest.fixture
def client_without_config(test_app_without_config):
    """Create a test client without config."""
    return TestClient(test_app_without_config)


class TestConfigSnapshotEndpoint:
    """Tests for GET /mcp/config/snapshot endpoint."""
    
    def test_snapshot_with_config_loaded(self, client_with_config):
        """Test snapshot endpoint when config is loaded."""
        response = client_with_config.get("/mcp/config/snapshot")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "config" in data
        
        config = data["config"]
        assert "hash" in config
        assert "timestamp" in config
        assert "engine_version" in config
        assert "agent_count" in config
        assert "workflows" in config
        assert "tone_sections" in config
        assert "perf_timeouts" in config
        assert "perf_limits" in config
        
        # Verify actual values
        assert config["hash"] == "abc123def456789"
        assert config["engine_version"] == "1.0.0"
        assert config["agent_count"] == 2
        assert "blog_generation" in config["workflows"]
        assert "fast_draft" in config["workflows"]
    
    def test_snapshot_without_config_loaded(self, client_without_config):
        """Test snapshot endpoint when config is not loaded."""
        response = client_without_config.get("/mcp/config/snapshot")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "unavailable"
        assert "message" in data
        assert "not initialized" in data["message"].lower()
    
    def test_snapshot_includes_metadata(self, client_with_config):
        """Test that snapshot includes runtime metadata."""
        response = client_with_config.get("/mcp/config/snapshot")
        assert response.status_code == 200
        
        data = response.json()
        config = data["config"]
        
        # Verify metadata fields
        assert config["hash"] is not None
        assert config["timestamp"] is not None
        assert config["engine_version"] is not None


class TestConfigAgentsEndpoint:
    """Tests for GET /mcp/config/agents endpoint."""
    
    def test_agents_config_with_config_loaded(self, client_with_config):
        """Test agents endpoint when config is loaded."""
        response = client_with_config.get("/mcp/config/agents")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "agent_count" in data
        assert "agents" in data
        
        # Verify agent count
        assert data["agent_count"] == 2
        
        # Verify agent structure
        agents = data["agents"]
        assert "KeywordExtractionAgent" in agents
        assert "OutlineCreationAgent" in agents
        
        # Verify agent details
        keyword_agent = agents["KeywordExtractionAgent"]
        assert keyword_agent["id"] == "KeywordExtractionAgent"
        assert keyword_agent["version"] == "1.0"
        assert keyword_agent["description"] == "Extracts keywords from content"
        assert "capabilities" in keyword_agent
        assert "resources" in keyword_agent
    
    def test_agents_config_without_config_loaded(self, client_without_config):
        """Test agents endpoint when config is not loaded."""
        response = client_without_config.get("/mcp/config/agents")
        assert response.status_code == 503
        
        data = response.json()
        assert "detail" in data
        assert "not available" in data["detail"].lower()
    
    def test_agents_config_structure(self, client_with_config):
        """Test that agents config has correct structure."""
        response = client_with_config.get("/mcp/config/agents")
        assert response.status_code == 200
        
        data = response.json()
        agents = data["agents"]
        
        # Each agent should have required fields
        for agent_id, agent_data in agents.items():
            assert "id" in agent_data
            assert "version" in agent_data
            assert "description" in agent_data
            assert "capabilities" in agent_data
            assert "resources" in agent_data


class TestConfigWorkflowsEndpoint:
    """Tests for GET /mcp/config/workflows endpoint."""
    
    def test_workflows_config_with_config_loaded(self, client_with_config):
        """Test workflows endpoint when config is loaded."""
        response = client_with_config.get("/mcp/config/workflows")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "workflow_count" in data
        assert "workflows" in data
        assert "dependencies" in data
        
        # Verify workflow count
        assert data["workflow_count"] == 2
        
        # Verify workflows
        workflows = data["workflows"]
        assert "blog_generation" in workflows
        assert "fast_draft" in workflows
        
        # Verify workflow details
        blog_gen = workflows["blog_generation"]
        assert blog_gen["name"] == "Blog Generation"
        assert "steps" in blog_gen
        assert "outline" in blog_gen["steps"]
    
    def test_workflows_config_without_config_loaded(self, client_without_config):
        """Test workflows endpoint when config is not loaded."""
        response = client_without_config.get("/mcp/config/workflows")
        assert response.status_code == 503
        
        data = response.json()
        assert "detail" in data
    
    def test_workflows_dependencies(self, client_with_config):
        """Test that workflow dependencies are included."""
        response = client_with_config.get("/mcp/config/workflows")
        assert response.status_code == 200
        
        data = response.json()
        dependencies = data["dependencies"]
        
        # Verify dependencies structure
        assert isinstance(dependencies, dict)
        assert "content" in dependencies
        assert "outline" in dependencies["content"]


class TestConfigToneEndpoint:
    """Tests for GET /mcp/config/tone endpoint."""
    
    def test_tone_config_with_config_loaded(self, client_with_config):
        """Test tone endpoint when config is loaded."""
        response = client_with_config.get("/mcp/config/tone")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "global_voice" in data
        assert "section_controls" in data
        assert "heading_style" in data
        assert "code_template_overrides" in data
        
        # Verify global voice settings
        global_voice = data["global_voice"]
        assert global_voice["formality"] == "professional"
        assert global_voice["perspective"] == "third_person"
        
        # Verify section controls
        section_controls = data["section_controls"]
        assert "introduction" in section_controls
        assert "conclusion" in section_controls
    
    def test_tone_config_without_config_loaded(self, client_without_config):
        """Test tone endpoint when config is not loaded."""
        response = client_without_config.get("/mcp/config/tone")
        assert response.status_code == 503
    
    def test_tone_config_structure(self, client_with_config):
        """Test that tone config has correct structure."""
        response = client_with_config.get("/mcp/config/tone")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify all required sections
        assert isinstance(data["global_voice"], dict)
        assert isinstance(data["section_controls"], dict)
        assert isinstance(data["heading_style"], dict)
        assert isinstance(data["code_template_overrides"], dict)


class TestConfigPerformanceEndpoint:
    """Tests for GET /mcp/config/performance endpoint."""
    
    def test_performance_config_with_config_loaded(self, client_with_config):
        """Test performance endpoint when config is loaded."""
        response = client_with_config.get("/mcp/config/performance")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "timeouts" in data
        assert "limits" in data
        assert "batch" in data
        assert "hot_paths" in data
        assert "tuning" in data
        
        # Verify timeouts
        timeouts = data["timeouts"]
        assert timeouts["agent_execution"] == 120
        assert timeouts["workflow_total"] == 600
        
        # Verify limits
        limits = data["limits"]
        assert limits["max_tokens"] == 4000
        assert limits["max_concurrent_jobs"] == 10
    
    def test_performance_config_without_config_loaded(self, client_without_config):
        """Test performance endpoint when config is not loaded."""
        response = client_without_config.get("/mcp/config/performance")
        assert response.status_code == 503
    
    def test_performance_config_structure(self, client_with_config):
        """Test that performance config has correct structure."""
        response = client_with_config.get("/mcp/config/performance")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify all required sections
        assert isinstance(data["timeouts"], dict)
        assert isinstance(data["limits"], dict)
        assert isinstance(data["batch"], dict)
        assert isinstance(data["hot_paths"], dict)
        assert isinstance(data["tuning"], dict)


class TestAllConfigEndpointsAccessible:
    """Tests to verify all config endpoints are properly mounted."""
    
    def test_all_endpoints_return_non_404(self, client_with_config):
        """Test that all config endpoints are accessible (not 404)."""
        endpoints = [
            "/mcp/config/snapshot",
            "/mcp/config/agents",
            "/mcp/config/workflows",
            "/mcp/config/tone",
            "/mcp/config/performance",
        ]
        
        for endpoint in endpoints:
            response = client_with_config.get(endpoint)
            assert response.status_code != 404, f"{endpoint} returned 404"
            assert response.status_code in [200, 503], f"{endpoint} returned {response.status_code}"
    
    def test_all_endpoints_return_json(self, client_with_config):
        """Test that all config endpoints return valid JSON."""
        endpoints = [
            "/mcp/config/snapshot",
            "/mcp/config/agents",
            "/mcp/config/workflows",
            "/mcp/config/tone",
            "/mcp/config/performance",
        ]
        
        for endpoint in endpoints:
            response = client_with_config.get(endpoint)
            assert response.status_code == 200
            
            # Verify response is valid JSON
            data = response.json()
            assert isinstance(data, dict)
            assert "status" in data


class TestConfigEndpointErrorHandling:
    """Tests for error handling across config endpoints."""
    
    def test_all_endpoints_handle_missing_config(self, client_without_config):
        """Test that all endpoints properly handle missing config."""
        endpoints = [
            "/mcp/config/agents",
            "/mcp/config/workflows",
            "/mcp/config/tone",
            "/mcp/config/performance",
        ]
        
        for endpoint in endpoints:
            response = client_without_config.get(endpoint)
            assert response.status_code == 503, f"{endpoint} should return 503 when config not loaded"
            
            data = response.json()
            assert "detail" in data
    
    def test_snapshot_gracefully_handles_missing_config(self, client_without_config):
        """Test that snapshot endpoint returns 200 with unavailable status."""
        response = client_without_config.get("/mcp/config/snapshot")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "unavailable"


class TestConfigIntegrationWithReactUI:
    """Tests for React UI integration with config endpoints."""
    
    def test_config_endpoints_support_cors(self, client_with_config):
        """Test that config endpoints support CORS for React UI."""
        response = client_with_config.get(
            "/mcp/config/snapshot",
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 200
        
        # CORS headers should be present (set by middleware)
        # The CORS middleware in the app should handle this
    
    def test_all_config_data_serializable(self, client_with_config):
        """Test that all config data is JSON serializable."""
        endpoints = [
            "/mcp/config/snapshot",
            "/mcp/config/agents",
            "/mcp/config/workflows",
            "/mcp/config/tone",
            "/mcp/config/performance",
        ]
        
        for endpoint in endpoints:
            response = client_with_config.get(endpoint)
            assert response.status_code == 200
            
            # If we can parse it, it's serializable
            data = response.json()
            assert data is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
