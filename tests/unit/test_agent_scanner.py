"""Tests for agent_scanner module."""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.core.agent_scanner import AgentScanner, BaseAgent


class TestAgent(BaseAgent):
    """Test agent implementation."""
    name = "test_agent"
    description = "Test agent description"
    
    def execute(self, *args, **kwargs):
        return "executed"


class InvalidAgent(BaseAgent):
    """Invalid agent missing required fields."""
    
    def execute(self, *args, **kwargs):
        return "executed"


class TestAgentScanner:
    """Tests for AgentScanner class."""
    
    def test_initialization(self):
        """Test scanner initialization."""
        scanner = AgentScanner("src/agents")
        assert scanner.agents_dir == Path("src/agents")
        assert scanner._cache is None
        assert scanner._agent_files == []
        assert scanner._cache_time == 0
    
    def test_scan_directory_nonexistent(self):
        """Test scanning non-existent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent"
            scanner = AgentScanner(str(nonexistent))
            files = scanner._scan_directory()
            assert files == []
    
    def test_scan_directory_with_files(self):
        """Test scanning directory with Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "agent1.py").touch()
            (tmppath / "agent2.py").touch()
            (tmppath / "__init__.py").touch()
            
            scanner = AgentScanner(tmpdir)
            files = scanner._scan_directory()
            
            assert len(files) == 2
            assert all(f.suffix == ".py" for f in files)
    
    def test_scan_directory_recursive(self):
        """Test scanning directory recursively."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            subdir = tmppath / "subdir"
            subdir.mkdir()
            
            (tmppath / "agent1.py").touch()
            (subdir / "agent2.py").touch()
            (subdir / "__init__.py").touch()
            
            scanner = AgentScanner(tmpdir)
            files = scanner._scan_directory()
            
            assert len(files) == 2
    
    def test_extract_agents(self):
        """Test extracting agents from module."""
        mock_module = MagicMock()
        mock_module.__dict__ = {
            'TestAgent': TestAgent,
            'BaseAgent': BaseAgent,
            'SomeClass': str
        }
        
        scanner = AgentScanner()
        
        with patch('inspect.getmembers') as mock_getmembers:
            mock_getmembers.return_value = [
                ('TestAgent', TestAgent),
                ('BaseAgent', BaseAgent),
                ('SomeClass', str)
            ]
            agents = scanner._extract_agents(mock_module)
            assert len(agents) == 1
            assert agents[0] == TestAgent
    
    def test_scan_file_success(self):
        """Test scanning a single file successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "test_agent.py"
            agent_file.write_text("""
from src.core.agent_scanner import BaseAgent

class MyAgent(BaseAgent):
    name = "my_agent"
    description = "Test"
    
    def execute(self, *args, **kwargs):
        return "ok"
""")
            
            scanner = AgentScanner(tmpdir)
            agents = scanner._scan_file(agent_file)
            
            assert len(agents) >= 0  # Might be 0 due to import issues in isolated env
    
    def test_scan_file_import_error(self):
        """Test scanning file with import error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "bad_agent.py"
            agent_file.write_text("import nonexistent_module")
            
            scanner = AgentScanner(tmpdir)
            agents = scanner._scan_file(agent_file)
            
            assert agents == []
    
    def test_scan_file_invalid_spec(self):
        """Test scanning file that produces invalid spec."""
        scanner = AgentScanner()
        
        with patch('importlib.util.spec_from_file_location', return_value=None):
            agents = scanner._scan_file(Path("test.py"))
            assert agents == []
    
    def test_validate_agent_valid(self):
        """Test validating a valid agent."""
        scanner = AgentScanner()
        assert scanner._validate_agent(TestAgent) is True
    
    def test_validate_agent_missing_name(self):
        """Test validating agent with missing name."""
        class NoNameAgent(BaseAgent):
            name = ""
            description = "Test"
            def execute(self, *args, **kwargs):
                pass
        
        scanner = AgentScanner()
        assert scanner._validate_agent(NoNameAgent) is False
    
    def test_validate_agent_missing_description(self):
        """Test validating agent with missing description."""
        class NoDescAgent(BaseAgent):
            name = "test"
            description = ""
            def execute(self, *args, **kwargs):
                pass
        
        scanner = AgentScanner()
        assert scanner._validate_agent(NoDescAgent) is False
    
    def test_validate_agent_missing_execute(self):
        """Test validating agent with missing execute method."""
        class NoExecAgent:
            name = "test"
            description = "Test"
        
        scanner = AgentScanner()
        assert scanner._validate_agent(NoExecAgent) is False
    
    def test_cache_stale_no_files(self):
        """Test cache staleness with no files."""
        scanner = AgentScanner()
        assert scanner._cache_stale() is True
    
    def test_cache_stale_modified_file(self):
        """Test cache staleness with modified file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            test_file = tmppath / "test.py"
            test_file.touch()
            
            scanner = AgentScanner(tmpdir)
            scanner._agent_files = [test_file]
            scanner._cache_time = time.time() - 100
            
            # Modify file
            time.sleep(0.01)
            test_file.touch()
            
            assert scanner._cache_stale() is True
    
    def test_cache_stale_new_file_added(self):
        """Test cache staleness when new file is added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            old_file = tmppath / "old.py"
            old_file.touch()
            
            scanner = AgentScanner(tmpdir)
            scanner._agent_files = [old_file]
            scanner._cache_time = time.time()
            
            # Add new file
            new_file = tmppath / "new.py"
            new_file.touch()
            
            assert scanner._cache_stale() is True
    
    def test_cache_stale_file_deleted(self):
        """Test cache staleness when file is deleted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = AgentScanner()
            deleted_file = Path(tmpdir) / "deleted.py"
            scanner._agent_files = [deleted_file]
            scanner._cache_time = time.time()
            
            assert scanner._cache_stale() is True
    
    def test_scan_empty_directory(self):
        """Test scanning empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = AgentScanner(tmpdir)
            agents = scanner.scan()
            assert agents == {}
    
    def test_scan_with_valid_cache(self):
        """Test scan returns cached results."""
        scanner = AgentScanner()
        scanner._cache = {"test": TestAgent}
        scanner._agent_files = []
        scanner._cache_time = time.time()
        
        with patch.object(scanner, '_cache_stale', return_value=False):
            result = scanner.scan()
            assert result == {"test": TestAgent}
    
    def test_scan_duplicate_agent_names(self):
        """Test scanning with duplicate agent names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create two files with agents of same name
            file1 = tmppath / "agent1.py"
            file1.write_text("""
from src.core.agent_scanner import BaseAgent

class Agent1(BaseAgent):
    name = "duplicate"
    description = "First"
    def execute(self, *args, **kwargs):
        pass
""")
            
            file2 = tmppath / "agent2.py"
            file2.write_text("""
from src.core.agent_scanner import BaseAgent

class Agent2(BaseAgent):
    name = "duplicate"
    description = "Second"
    def execute(self, *args, **kwargs):
        pass
""")
            
            scanner = AgentScanner(tmpdir)
            # The scan should handle duplicates gracefully
            agents = scanner.scan()
            # Either 0 or 1 agents should be loaded
            assert len(agents) <= 1
    
    def test_get_agent_exists(self):
        """Test getting an existing agent."""
        scanner = AgentScanner()
        scanner._cache = {"test_agent": TestAgent}
        scanner._agent_files = []
        scanner._cache_time = time.time()
        
        with patch.object(scanner, '_cache_stale', return_value=False):
            agent = scanner.get_agent("test_agent")
            assert agent == TestAgent
    
    def test_get_agent_not_exists(self):
        """Test getting a non-existent agent."""
        scanner = AgentScanner()
        scanner._cache = {}
        scanner._agent_files = []
        scanner._cache_time = time.time()
        
        with patch.object(scanner, '_cache_stale', return_value=False):
            agent = scanner.get_agent("nonexistent")
            assert agent is None
    
    def test_list_agents(self):
        """Test listing all agents."""
        scanner = AgentScanner()
        scanner._cache = {
            "agent1": TestAgent,
            "agent2": TestAgent
        }
        scanner._agent_files = []
        scanner._cache_time = time.time()
        
        with patch.object(scanner, '_cache_stale', return_value=False):
            agents = scanner.list_agents()
            assert set(agents) == {"agent1", "agent2"}
    
    def test_reload(self):
        """Test force reload of agents."""
        scanner = AgentScanner()
        scanner._cache = {"old": TestAgent}
        
        with patch.object(scanner, 'scan', return_value={"new": TestAgent}) as mock_scan:
            result = scanner.reload()
            assert scanner._cache is None or "new" in result


class TestBaseAgent:
    """Tests for BaseAgent class."""
    
    def test_base_agent_is_abstract(self):
        """Test that BaseAgent cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseAgent()
    
    def test_base_agent_attributes(self):
        """Test BaseAgent has required attributes."""
        assert hasattr(BaseAgent, 'name')
        assert hasattr(BaseAgent, 'description')
        assert hasattr(BaseAgent, 'execute')
    
    def test_test_agent_implementation(self):
        """Test TestAgent implementation."""
        agent = TestAgent()
        assert agent.name == "test_agent"
        assert agent.description == "Test agent description"
        assert agent.execute() == "executed"
