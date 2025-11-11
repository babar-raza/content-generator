"""Test Unified Engine functionality."""

import pytest
import json
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

from src.engine.engine import (
    UnifiedEngine, 
    get_engine, 
    RunSpec, 
    JobStatus, 
    JobResult,
    AgentStepLog,
    urlify,
    convert_paths_to_strings
)


class TestRunSpec:
    """Test RunSpec validation and conversion."""
    
    def test_runspec_validation_success(self):
        """Test successful RunSpec validation."""
        spec = RunSpec(
            topic="Test Topic",
            template_name="default_blog",
            output_dir=Path("/tmp/output")
        )
        
        errors = spec.validate()
        assert errors == []
    
    def test_runspec_validation_missing_topic(self):
        """Test RunSpec validation with missing topic."""
        spec = RunSpec(
            template_name="default_blog"
        )
        
        errors = spec.validate()
        assert "Must provide topic when auto_topic=False" in errors
    
    def test_runspec_validation_auto_topic(self):
        """Test RunSpec validation with auto_topic."""
        with tempfile.NamedTemporaryFile(suffix=".md") as f:
            spec = RunSpec(
                auto_topic=True,
                kb_path=f.name,
                template_name="default_blog"
            )
            
            errors = spec.validate()
            assert errors == []
    
    def test_runspec_validation_invalid_path(self):
        """Test RunSpec validation with invalid path."""
        spec = RunSpec(
            topic="Test",
            kb_path="/nonexistent/path",
            template_name="default_blog"
        )
        
        errors = spec.validate()
        assert any("does not exist" in e for e in errors)
    
    def test_runspec_to_dict(self):
        """Test RunSpec conversion to dictionary."""
        spec = RunSpec(
            topic="Test Topic",
            template_name="blog",
            output_dir=Path("/tmp/test")
        )
        
        data = spec.to_dict()
        assert data['topic'] == "Test Topic"
        assert data['template_name'] == "blog"
        assert data['output_dir'] == "/tmp/test"
    
    def test_runspec_from_dict(self):
        """Test RunSpec creation from dictionary."""
        data = {
            'topic': 'Test Topic',
            'template_name': 'blog',
            'output_dir': '/tmp/test'
        }
        
        spec = RunSpec.from_dict(data)
        assert spec.topic == "Test Topic"
        assert spec.template_name == "blog"
        assert spec.output_dir == Path("/tmp/test")


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_urlify(self):
        """Test URL slug generation."""
        assert urlify("Test Title") == "test-title"
        assert urlify("Title with 123 Numbers") == "title-with-123-numbers"
        assert urlify("Multiple   Spaces") == "multiple-spaces"
        assert urlify("Special!@#$%Characters") == "special-characters"
        assert urlify("") == ""
    
    def test_convert_paths_to_strings(self):
        """Test Path object conversion."""
        data = {
            'path': Path('/tmp/test'),
            'nested': {
                'path': Path('/home/user'),
                'string': 'test'
            },
            'list': [Path('/a'), Path('/b')],
            'tuple': (Path('/c'), 'text')
        }
        
        result = convert_paths_to_strings(data)
        assert result['path'] == '/tmp/test'
        assert result['nested']['path'] == '/home/user'
        assert result['nested']['string'] == 'test'
        assert result['list'] == ['/a', '/b']
        assert result['tuple'] == ('/c', 'text')


class TestJobResult:
    """Test JobResult functionality."""
    
    def test_job_result_creation(self):
        """Test JobResult creation."""
        result = JobResult(
            job_id="test_123",
            status=JobStatus.COMPLETED,
            topic="Test Topic"
        )
        
        assert result.job_id == "test_123"
        assert result.status == JobStatus.COMPLETED
        assert result.topic == "Test Topic"
    
    def test_job_result_to_dict(self):
        """Test JobResult serialization."""
        result = JobResult(
            job_id="test_123",
            status=JobStatus.COMPLETED,
            output_path=Path("/tmp/output"),
            files_written=["/tmp/file1.md"],
            steps=[
                AgentStepLog(
                    agent_name="TestAgent",
                    status="completed",
                    timestamp="2024-01-01T10:00:00"
                )
            ]
        )
        
        data = result.to_dict()
        assert data['job_id'] == "test_123"
        assert data['status'] == "completed"
        assert data['output_path'] == "/tmp/output"
        assert len(data['steps']) == 1
        assert data['steps'][0]['agent_name'] == "TestAgent"
    
    def test_job_result_from_dict(self):
        """Test JobResult deserialization."""
        data = {
            'job_id': 'test_123',
            'status': 'completed',
            'topic': 'Test',
            'output_path': '/tmp/output',
            'files_written': ['/tmp/file.md'],
            'steps': [
                {
                    'agent_name': 'TestAgent',
                    'status': 'completed',
                    'timestamp': '2024-01-01T10:00:00'
                }
            ]
        }
        
        result = JobResult.from_dict(data)
        assert result.job_id == "test_123"
        assert result.status == JobStatus.COMPLETED
        assert result.output_path == Path("/tmp/output")
        assert len(result.steps) == 1


class TestUnifiedEngine:
    """Test UnifiedEngine functionality."""
    
    @pytest.fixture
    def engine(self):
        """Create engine instance for testing."""
        with patch('src.engine.engine.UnifiedEngine._initialize_services'):
            with patch('src.engine.engine.UnifiedEngine._load_templates'):
                engine = UnifiedEngine()
                engine.llm_service = Mock()
                engine.agents = {}
                engine.template_registry = Mock()
                return engine
    
    def test_engine_initialization(self):
        """Test engine initialization."""
        with patch('src.engine.engine.UnifiedEngine._initialize_services') as mock_init:
            with patch('src.engine.engine.UnifiedEngine._load_templates') as mock_load:
                engine = UnifiedEngine()
                
                mock_init.assert_called_once()
                mock_load.assert_called_once()
                assert engine.job_counter == 0
                assert engine.active_jobs == {}
    
    def test_generate_job_id(self, engine):
        """Test job ID generation."""
        job_id1 = engine._generate_job_id()
        job_id2 = engine._generate_job_id()
        
        assert job_id1 != job_id2
        assert job_id1.startswith("job_")
        assert engine.job_counter == 2
    
    def test_execute_with_invalid_spec(self, engine):
        """Test execution with invalid specification."""
        spec = RunSpec(template_name="")  # Invalid: no template name
        
        result = engine.execute(spec)
        
        assert result.status == JobStatus.FAILED
        assert len(result.errors) > 0
        assert "template_name is required" in result.errors
    
    @patch('src.engine.engine.UnifiedEngine._execute_workflow')
    def test_execute_success(self, mock_workflow, engine):
        """Test successful job execution."""
        spec = RunSpec(
            topic="Test Topic",
            template_name="default_blog"
        )
        
        result = engine.execute(spec)
        
        assert result.status == JobStatus.COMPLETED
        assert result.topic == "Test Topic"
        assert result.job_id.startswith("job_")
        mock_workflow.assert_called_once()
    
    @patch('src.engine.engine.UnifiedEngine._execute_workflow')
    def test_execute_with_exception(self, mock_workflow, engine):
        """Test job execution with exception."""
        mock_workflow.side_effect = Exception("Test error")
        
        spec = RunSpec(
            topic="Test Topic",
            template_name="default_blog"
        )
        
        result = engine.execute(spec)
        
        assert result.status == JobStatus.FAILED
        assert "Test error" in result.errors
        assert result.duration_seconds is not None
    
    def test_ingest_path_file(self, engine):
        """Test ingesting a single file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test Content\n\nThis is test content.")
            temp_path = f.name
        
        try:
            result = engine._ingest_path(temp_path)
            
            assert result['ingested'] == True
            assert result['file_count'] == 1
            assert "Test Content" in result['content']
            assert len(result['chunks']) > 0
        finally:
            Path(temp_path).unlink()
    
    def test_ingest_path_directory(self, engine):
        """Test ingesting a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "file1.md").write_text("Content 1")
            (Path(tmpdir) / "file2.md").write_text("Content 2")
            (Path(tmpdir) / "subdir").mkdir()
            (Path(tmpdir) / "subdir" / "file3.md").write_text("Content 3")
            
            result = engine._ingest_path(tmpdir)
            
            assert result['ingested'] == True
            assert result['file_count'] == 3
            assert "Content 1" in result['content']
            assert "Content 2" in result['content']
            assert "Content 3" in result['content']
    
    def test_ingest_path_nonexistent(self, engine):
        """Test ingesting non-existent path."""
        result = engine._ingest_path("/nonexistent/path")
        
        assert result['ingested'] == False
        assert result['error'] == 'Path not found'
        assert result['file_count'] == 0
    
    def test_chunk_content(self, engine):
        """Test content chunking."""
        content = "Paragraph 1\n\nParagraph 2\n\nParagraph 3"
        
        chunks = engine._chunk_content(content, chunk_size=20)
        
        assert len(chunks) == 3
        assert "Paragraph 1" in chunks[0]
        assert "Paragraph 2" in chunks[1]
        assert "Paragraph 3" in chunks[2]
    
    def test_validate_agent_prerequisites(self, engine):
        """Test agent prerequisite validation."""
        # Test outline agent without topic
        result = engine._validate_agent_prerequisites(
            "OutlineCreationAgent",
            {}
        )
        assert not result['validated']
        assert "No topic defined" in str(result['errors'])
        
        # Test outline agent with topic
        result = engine._validate_agent_prerequisites(
            "OutlineCreationAgent",
            {'topic': 'Test Topic'}
        )
        assert result['validated']
        
        # Test file writer without content
        result = engine._validate_agent_prerequisites(
            "FileWriterAgent",
            {}
        )
        assert not result['validated']
        assert "Cannot write file without content" in str(result['errors'])
    
    def test_prepare_agent_input(self, engine):
        """Test agent input preparation."""
        context = {
            'topic': 'Test Topic',
            'kb_ingested': {'content': 'KB Content'},
            'outline_creation': {'outline': {'sections': []}},
            'content_assembly': {'content': 'Final content'}
        }
        
        # Test outline agent input
        input_data = engine._prepare_agent_input('OutlineCreationAgent', context)
        assert input_data['topic'] == 'Test Topic'
        assert input_data['kb_content'] == 'KB Content'
        
        # Test writer agent input
        input_data = engine._prepare_agent_input('SectionWriterAgent', context)
        assert 'outline' in input_data
        
        # Test file writer input
        input_data = engine._prepare_agent_input('FileWriterAgent', context)
        assert input_data['content'] == 'Final content'
    
    def test_list_jobs(self, engine):
        """Test listing active jobs."""
        # Add some active jobs
        result1 = JobResult(
            job_id="job1",
            status=JobStatus.RUNNING,
            topic="Topic 1"
        )
        result2 = JobResult(
            job_id="job2",
            status=JobStatus.COMPLETED,
            topic="Topic 2"
        )
        
        engine.active_jobs = {
            "job1": result1,
            "job2": result2
        }
        
        jobs = engine.list_jobs()
        
        assert len(jobs) == 2
        assert jobs[0]['job_id'] in ['job1', 'job2']
        assert jobs[0]['status'] in ['running', 'completed']
    
    def test_get_job(self, engine):
        """Test getting job details."""
        result = JobResult(
            job_id="test_job",
            status=JobStatus.RUNNING,
            topic="Test"
        )
        engine.active_jobs["test_job"] = result
        
        retrieved = engine.get_job("test_job")
        assert retrieved == result
        
        missing = engine.get_job("nonexistent")
        assert missing is None
    
    def test_cancel_job(self, engine):
        """Test job cancellation."""
        result = JobResult(
            job_id="test_job",
            status=JobStatus.RUNNING
        )
        engine.active_jobs["test_job"] = result
        
        success = engine.cancel_job("test_job")
        assert success == True
        assert "test_job" not in engine.active_jobs
        assert result.status == JobStatus.CANCELLED
        
        # Try to cancel non-existent job
        success = engine.cancel_job("nonexistent")
        assert success == False
    
    def test_write_output(self, engine):
        """Test output file writing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spec = RunSpec(
                topic="Test Topic",
                output_dir=Path(tmpdir)
            )
            
            context = {
                'content_assembly': {
                    'content': '# Test Content\n\nThis is test content.'
                },
                'seo_metadata': {
                    'metadata': {
                        'title': 'Test Title',
                        'description': 'Test Description'
                    }
                }
            }
            
            result = JobResult(
                job_id="test",
                status=JobStatus.RUNNING
            )
            
            engine._write_output(context, spec, result)
            
            # Check files were written
            assert len(result.files_written) == 2
            
            # Check main content file
            content_file = Path(tmpdir) / "test-topic.md"
            assert content_file.exists()
            
            content = content_file.read_text()
            assert "Test Content" in content
            assert "title: Test Title" in content
    
    def test_singleton_pattern(self):
        """Test that get_engine returns singleton."""
        engine1 = get_engine()
        engine2 = get_engine()
        
        assert engine1 is engine2


class TestEngineIntegration:
    """Integration tests for the unified engine."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing."""
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir)
    
    def test_end_to_end_execution(self, temp_workspace):
        """Test end-to-end job execution."""
        # Create test input file
        kb_file = temp_workspace / "knowledge.md"
        kb_file.write_text("# Test Knowledge\n\nThis is test content about Python.")
        
        # Create run specification
        spec = RunSpec(
            topic="Python Tutorial",
            template_name="default_blog",
            kb_path=str(kb_file),
            output_dir=temp_workspace / "output"
        )
        
        # Execute with mock services
        with patch('src.engine.engine.UnifiedEngine._initialize_services'):
            with patch('src.engine.engine.UnifiedEngine._load_templates'):
                engine = UnifiedEngine()
                
                # Mock the template registry
                engine.template_registry = Mock()
                engine.template_registry.get_template.return_value = {
                    'workflow': [
                        {'name': 'test_step', 'agent': 'TestAgent'}
                    ]
                }
                
                # Mock agent execution
                mock_agent = Mock()
                mock_agent.execute.return_value = {'content': 'Generated content'}
                engine.agents = {'TestAgent': mock_agent}
                
                # Execute
                result = engine.execute(spec)
                
                # Verify result
                assert result.status in [JobStatus.COMPLETED, JobStatus.PARTIAL]
                assert result.topic == "Python Tutorial"
                assert result.job_id.startswith("job_")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
