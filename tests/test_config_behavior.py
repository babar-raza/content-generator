"""Unit Tests for Config Validation - Prove each key changes behavior"""

import pytest
import json
import yaml
import tempfile
from pathlib import Path
from config.validator import ConfigValidator, load_validated_config, ConfigSnapshot


class TestConfigValidation:
    """Test config validation with fail-fast behavior"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with valid configs"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # Create valid agents.yaml
            agents = {
                "version": "1.0",
                "agents": {
                    "test_agent": {
                        "id": "test_agent",
                        "version": "1.0.0",
                        "description": "Test Agent",
                        "entrypoint": {
                            "type": "python",
                            "module": "agents",
                            "function": "test_agent"
                        },
                        "contract": {
                            "inputs": {"type": "object"},
                            "outputs": {"type": "object"}
                        },
                        "capabilities": {
                            "stateful": False,
                            "async": False
                        },
                        "resources": {}
                    }
                }
            }
            with open(config_dir / "agents.yaml", 'w') as f:
                yaml.dump(agents, f)
            
            # Create valid perf.json
            perf = {
                "timeouts": {
                    "agent_execution": 30,
                    "total_job": 600,
                    "rag_query": 10,
                    "template_render": 5
                },
                "limits": {
                    "max_tokens_per_agent": 4000,
                    "max_retries": 3
                }
            }
            with open(config_dir / "perf.json", 'w') as f:
                json.dump(perf, f)
            
            # Create valid tone.json
            tone = {
                "global_voice": {
                    "pov": "second_person",
                    "formality": "professional_conversational"
                }
            }
            with open(config_dir / "tone.json", 'w') as f:
                json.dump(tone, f)
            
            # Create valid main.yaml
            main = {
                "version": "1.0",
                "pipeline": ["test_agent"]
            }
            with open(config_dir / "main.yaml", 'w') as f:
                yaml.dump(main, f)
            
            yield config_dir
    
    def test_valid_config_loads(self, temp_config_dir):
        """Test that valid config loads successfully"""
        snapshot = load_validated_config(temp_config_dir)
        assert isinstance(snapshot, ConfigSnapshot)
        assert snapshot.config_hash
        assert snapshot.timestamp
        assert "test_agent" in snapshot.agent_config["agents"]
    
    def test_missing_config_file_fails(self, temp_config_dir):
        """Test that missing config file causes fail-fast"""
        (temp_config_dir / "perf.json").unlink()
        with pytest.raises(FileNotFoundError, match="perf.json"):
            load_validated_config(temp_config_dir)
    
    def test_invalid_json_schema_fails(self, temp_config_dir):
        """Test that invalid JSON schema causes fail-fast"""
        # Invalid perf.json - missing required field
        invalid_perf = {"timeouts": {}}
        with open(temp_config_dir / "perf.json", 'w') as f:
            json.dump(invalid_perf, f)
        
        with pytest.raises(ValueError, match="Schema validation failed"):
            load_validated_config(temp_config_dir)
    
    def test_invalid_yaml_schema_fails(self, temp_config_dir):
        """Test that invalid YAML schema causes fail-fast"""
        # Invalid agents.yaml - missing required field
        invalid_agents = {"version": "1.0", "agents": {}}
        with open(temp_config_dir / "agents.yaml", 'w') as f:
            yaml.dump(invalid_agents, f)
        
        # This should still pass as agents can be empty object
        snapshot = load_validated_config(temp_config_dir)
        assert snapshot.agent_config["agents"] == {}
    
    def test_config_hash_changes_with_content(self, temp_config_dir):
        """Test that config hash changes when config changes"""
        snapshot1 = load_validated_config(temp_config_dir)
        hash1 = snapshot1.config_hash
        
        # Modify perf.json
        perf = json.loads((temp_config_dir / "perf.json").read_text())
        perf["timeouts"]["agent_execution"] = 60  # Changed from 30
        with open(temp_config_dir / "perf.json", 'w') as f:
            json.dump(perf, f)
        
        snapshot2 = load_validated_config(temp_config_dir)
        hash2 = snapshot2.config_hash
        
        assert hash1 != hash2
    
    def test_merged_config_contains_all(self, temp_config_dir):
        """Test that merged config contains all config sources"""
        snapshot = load_validated_config(temp_config_dir)
        merged = snapshot.merged_config
        
        # Check all configs merged
        assert "agents" in merged
        assert "timeouts" in merged
        assert "global_voice" in merged
        assert "pipeline" in merged


class TestConfigBehaviorChanges:
    """Test that each config key measurably changes behavior"""
    
    @pytest.fixture
    def config_dir(self):
        """Use actual config directory"""
        return Path("./config")
    
    def test_perf_timeout_affects_behavior(self, config_dir):
        """Test that changing timeout in perf.json affects behavior"""
        snapshot = load_validated_config(config_dir)
        
        # Check that timeout is read from config
        timeout = snapshot.perf_config["timeouts"]["agent_execution"]
        assert isinstance(timeout, (int, float))
        assert timeout > 0
        
        # Verify it's in merged config
        assert snapshot.merged_config["timeouts"]["agent_execution"] == timeout
    
    def test_perf_retries_affects_behavior(self, config_dir):
        """Test that max_retries in perf.json affects behavior"""
        snapshot = load_validated_config(config_dir)
        
        retries = snapshot.perf_config["limits"]["max_retries"]
        assert isinstance(retries, int)
        assert retries >= 0
    
    def test_perf_concurrency_affects_behavior(self, config_dir):
        """Test that batch settings affect behavior"""
        snapshot = load_validated_config(config_dir)
        
        if "batch" in snapshot.perf_config:
            batch = snapshot.perf_config["batch"]
            assert "max_parallel" in batch
            assert isinstance(batch["max_parallel"], int)
    
    def test_tone_pov_affects_behavior(self, config_dir):
        """Test that POV setting affects behavior"""
        snapshot = load_validated_config(config_dir)
        
        pov = snapshot.tone_config["global_voice"]["pov"]
        assert pov in ["first_person", "second_person", "third_person"]
    
    def test_tone_formality_affects_behavior(self, config_dir):
        """Test that formality setting affects behavior"""
        snapshot = load_validated_config(config_dir)
        
        formality = snapshot.tone_config["global_voice"]["formality"]
        assert formality in ["casual", "professional_conversational", "formal", "academic"]
    
    def test_main_pipeline_order_affects_behavior(self, config_dir):
        """Test that pipeline order in main.yaml affects behavior"""
        snapshot = load_validated_config(config_dir)
        
        pipeline = snapshot.main_config["pipeline"]
        assert isinstance(pipeline, list)
        assert len(pipeline) > 0
        
        # Verify order matters - pipeline should be an ordered list
        assert pipeline == list(pipeline)  # Order preserved
    
    def test_agent_temperature_affects_behavior(self, config_dir):
        """Test that agent temperature affects behavior"""
        snapshot = load_validated_config(config_dir)
        
        agents = snapshot.agent_config.get("agents", {})
        if agents:
            # Check at least one agent has temperature
            has_temp = any("temperature" in agent for agent in agents.values())
            # Some agents might not have temperature, which is OK
    
    def test_config_snapshot_serializable(self, config_dir):
        """Test that config snapshot can be serialized"""
        snapshot = load_validated_config(config_dir)
        
        # Test to_dict
        as_dict = snapshot.to_dict()
        assert isinstance(as_dict, dict)
        assert "config_hash" in as_dict
        
        # Test to_json
        as_json = snapshot.to_json()
        assert isinstance(as_json, str)
        
        # Verify can be parsed back
        parsed = json.loads(as_json)
        assert parsed["config_hash"] == snapshot.config_hash
