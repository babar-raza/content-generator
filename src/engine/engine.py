"""Unified Engine - Single entry point for CLI and Web with complete parity."""

import json
import re
import time
import hashlib
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


def convert_paths_to_strings(data: Any) -> Any:
    """Recursively convert Path objects to strings in nested data structures.
    
    Args:
        data: Data to convert (dict, list, or any value)
        
    Returns:
        Data with all Path objects converted to strings
    """
    if isinstance(data, Path):
        return str(data)
    elif isinstance(data, dict):
        return {key: convert_paths_to_strings(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_paths_to_strings(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(convert_paths_to_strings(item) for item in data)
    else:
        return data


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


@dataclass
class RunSpec:
    """Specification for a job run - used by both CLI and Web."""
    
    # Core inputs
    topic: Optional[str] = None
    template_name: str = "default_blog"
    
    # Context paths
    kb_path: Optional[str] = None
    docs_path: Optional[str] = None
    blog_path: Optional[str] = None
    api_path: Optional[str] = None
    
    # Options
    auto_topic: bool = False
    output_dir: Path = field(default_factory=lambda: Path('./output'))
    
    # Model overrides
    model: Optional[str] = None
    provider: Optional[str] = None
    
    # Advanced options
    batch_size: int = 1
    parallel: bool = False
    cache_enabled: bool = True
    
    def validate(self) -> List[str]:
        """Validate run spec.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Require template name
        if not self.template_name:
            errors.append("template_name is required")
        
        # Validate topic requirements
        if self.auto_topic:
            has_context = any([self.kb_path, self.docs_path, self.blog_path, self.api_path])
            if not has_context:
                errors.append("auto_topic requires at least one context source")
        elif not self.topic:
            errors.append("Must provide topic when auto_topic=False")
        
        # Validate paths exist if provided
        for path_name in ['kb_path', 'docs_path', 'blog_path', 'api_path']:
            path_value = getattr(self, path_name)
            if path_value and not Path(path_value).exists():
                errors.append(f"{path_name} does not exist: {path_value}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert Path to string for JSON serialization
        data['output_dir'] = str(self.output_dir)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RunSpec':
        """Create from dictionary."""
        # Convert string to Path
        if 'output_dir' in data and isinstance(data['output_dir'], str):
            data['output_dir'] = Path(data['output_dir'])
        return cls(**data)


def urlify(text: str) -> str:
    """Convert text to URL-safe slug.
    
    Args:
        text: Text to convert
        
    Returns:
        URL-safe slug
    """
    if not text:
        return ''
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces and special characters with hyphens
    text = re.sub(r'[^a-z0-9\-]', '-', text)
    
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    return text


@dataclass
class AgentStepLog:
    """Log entry for an agent execution step."""
    agent_name: str
    status: str  # 'started', 'completed', 'failed', 'skipped'
    timestamp: str
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    output_preview: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'agent_name': self.agent_name,
            'status': self.status,
            'timestamp': self.timestamp,
            'duration_ms': self.duration_ms,
            'error': self.error,
            'output_preview': self.output_preview,
            'metadata': self.metadata
        }


@dataclass
class JobResult:
    """Result of a job execution."""
    job_id: str
    status: JobStatus
    topic: Optional[str] = None
    output_path: Optional[Path] = None
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Outputs
    files_written: List[str] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    
    # Execution log
    steps: List[AgentStepLog] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Metrics
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'job_id': self.job_id,
            'status': self.status.value,
            'topic': self.topic,
            'output_path': str(self.output_path) if self.output_path else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'files_written': self.files_written,
            'artifacts': convert_paths_to_strings(self.artifacts),
            'steps': [step.to_dict() for step in self.steps],
            'errors': self.errors,
            'warnings': self.warnings,
            'metrics': self.metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobResult':
        """Create from dictionary."""
        # Convert status string to enum
        if isinstance(data.get('status'), str):
            data['status'] = JobStatus(data['status'])
        
        # Convert timestamps
        if data.get('start_time'):
            data['start_time'] = datetime.fromisoformat(data['start_time'])
        if data.get('end_time'):
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        
        # Convert Path
        if data.get('output_path'):
            data['output_path'] = Path(data['output_path'])
        
        # Convert steps
        if data.get('steps'):
            data['steps'] = [AgentStepLog(**step) if isinstance(step, dict) else step 
                           for step in data['steps']]
        
        return cls(**data)


class UnifiedEngine:
    """Unified execution engine for CLI and Web interfaces."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the unified engine.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.job_counter = 0
        self.active_jobs: Dict[str, JobResult] = {}
        
        # Initialize services
        self._initialize_services()
        
        # Load templates
        self._load_templates()
        
        logger.info("UnifiedEngine initialized")
    
    def _initialize_services(self):
        """Initialize required services."""
        try:
            # Initialize configuration
            from src.initialization.integrated_init import initialize_integrated_system
            from src.core.config import Config
            from src.core.event_bus import EventBus

            logger.info("Initializing system services...")
            config = Config()
            event_bus = EventBus()

            execution_engine, job_controller, init_status = initialize_integrated_system(config, event_bus)

            # Extract services from initialized components
            self.llm_service = getattr(execution_engine, 'llm_service', None)
            self.database_service = getattr(execution_engine, 'database_service', None)
            self.embedding_service = getattr(execution_engine, 'embedding_service', None)
            self.event_bus = event_bus
            self.agents = getattr(execution_engine, 'agents', {})
            self.template_registry = None  # Will be loaded in _load_templates

            logger.info(f"Initialized {len(self.agents)} agents")

        except Exception as e:
            logger.warning(f"Failed to initialize services: {e}")
            self._setup_fallback_services()
    
    def _setup_fallback_services(self):
        """Setup fallback services for testing."""
        logger.info("Setting up fallback services...")

        # Create minimal services for testing
        from src.core.event_bus import EventBus

        self.llm_service = None  # Will be initialized on demand
        self.database_service = None
        self.embedding_service = None
        self.event_bus = EventBus()
        self.agents = {}
        self.template_registry = None
    
    def _load_templates(self):
        """Load workflow templates."""
        try:
            from src.core.template_registry import TemplateRegistry
            
            if not self.template_registry:
                self.template_registry = TemplateRegistry()
                # Templates are loaded automatically in __init__
            
            logger.info(f"Loaded {len(self.template_registry.templates)} templates")
            
        except Exception as e:
            logger.warning(f"Failed to load templates: {e}")
            self.templates = {}
    
    def execute(self, spec: Union[RunSpec, Dict[str, Any]]) -> JobResult:
        """Execute a job based on the run specification.
        
        Args:
            spec: RunSpec object or dictionary with run parameters
            
        Returns:
            JobResult with execution details
        """
        # Convert dict to RunSpec if needed
        if isinstance(spec, dict):
            spec = RunSpec.from_dict(spec)
        
        # Validate specification
        validation_errors = spec.validate()
        if validation_errors:
            return JobResult(
                job_id=self._generate_job_id(),
                status=JobStatus.FAILED,
                errors=validation_errors
            )
        
        # Create job
        job_id = self._generate_job_id()
        result = JobResult(
            job_id=job_id,
            status=JobStatus.RUNNING,
            topic=spec.topic,
            output_path=spec.output_dir,
            start_time=datetime.now()
        )
        
        # Store active job
        self.active_jobs[job_id] = result
        
        try:
            # Execute workflow
            logger.info(f"Starting job {job_id} with topic: {spec.topic}")
            self._execute_workflow(spec, result)
            
            # Mark as completed
            result.status = JobStatus.COMPLETED
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            
            logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            result.status = JobStatus.FAILED
            result.errors.append(str(e))
            result.end_time = datetime.now()
            if result.start_time:
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()
        
        finally:
            # Clean up active job
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
        
        return result
    
    def _generate_job_id(self) -> str:
        """Generate unique job ID.
        
        Returns:
            Unique job identifier
        """
        self.job_counter += 1
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"job_{timestamp}_{self.job_counter:04d}"
    
    def _execute_workflow(self, spec: RunSpec, result: JobResult):
        """Execute the workflow based on template.
        
        Args:
            spec: Run specification
            result: Job result to populate
        """
        # Get template
        template = self._get_template(spec.template_name)
        if not template:
            raise ValueError(f"Template not found: {spec.template_name}")
        
        # Initialize context
        context = self._initialize_context(spec)
        
        # Execute workflow steps
        workflow_steps = template.get('workflow', [])
        for step in workflow_steps:
            step_log = self._execute_step(step, context, spec, result)
            result.steps.append(step_log)
            
            # Check for failures
            if step_log.status == 'failed' and not step.get('optional', False):
                result.status = JobStatus.PARTIAL
                break
        
        # Write output
        if result.status != JobStatus.FAILED:
            self._write_output(context, spec, result)
    
    def _get_template(self, template_name: str) -> Dict[str, Any]:
        """Get workflow template by name.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template configuration
        """
        if self.template_registry:
            return self.template_registry.get_template(template_name)
        
        # Fallback to default template
        return self._get_default_template()
    
    def _get_default_template(self) -> Dict[str, Any]:
        """Get default workflow template.
        
        Returns:
            Default template configuration
        """
        return {
            'name': 'default_blog',
            'description': 'Default blog generation workflow',
            'workflow': [
                {'name': 'topic_identification', 'agent': 'TopicIdentificationAgent'},
                {'name': 'kb_ingestion', 'agent': 'KBIngestionAgent', 'optional': True},
                {'name': 'outline_creation', 'agent': 'OutlineCreationAgent'},
                {'name': 'introduction_writer', 'agent': 'IntroductionWriterAgent'},
                {'name': 'section_writer', 'agent': 'SectionWriterAgent'},
                {'name': 'conclusion_writer', 'agent': 'ConclusionWriterAgent'},
                {'name': 'content_assembly', 'agent': 'ContentAssemblyAgent'},
                {'name': 'seo_metadata', 'agent': 'SEOMetadataAgent'},
                {'name': 'file_writer', 'agent': 'FileWriterAgent'}
            ]
        }
    
    def _initialize_context(self, spec: RunSpec) -> Dict[str, Any]:
        """Initialize execution context from specification.
        
        Args:
            spec: Run specification
            
        Returns:
            Initialized context dictionary
        """
        context = {
            'topic': spec.topic,
            'template_name': spec.template_name,
            'output_dir': str(spec.output_dir),
            'timestamp': datetime.now().isoformat(),
            'job_id': None,  # Will be set by execution
            'config': self.config
        }
        
        # Add path contexts if provided
        if spec.kb_path:
            context['kb_path'] = spec.kb_path
            context['kb_ingested'] = self._ingest_path(spec.kb_path)
        
        if spec.docs_path:
            context['docs_path'] = spec.docs_path
            context['docs_ingested'] = self._ingest_path(spec.docs_path)
        
        if spec.blog_path:
            context['blog_path'] = spec.blog_path
            context['blog_ingested'] = self._ingest_path(spec.blog_path)
        
        if spec.api_path:
            context['api_path'] = spec.api_path
            context['api_ingested'] = self._ingest_path(spec.api_path)
        
        # Add model overrides
        if spec.model:
            context['model'] = spec.model
        if spec.provider:
            context['provider'] = spec.provider
        
        return context
    
    def _ingest_path(self, path: str) -> Dict[str, Any]:
        """Ingest content from path for RAG.
        
        Args:
            path: Path to ingest
            
        Returns:
            Ingested content with files and chunks
        """
        path_obj = Path(path)
        
        if not path_obj.exists():
            logger.warning(f"Path does not exist: {path}")
            return {
                'path': path,
                'ingested': False,
                'error': 'Path not found',
                'file_count': 0,
                'files': [],
                'content': ''
            }
        
        # Collect files
        files = []
        if path_obj.is_file():
            files = [path_obj]
        elif path_obj.is_dir():
            # Recursively find markdown and text files
            files = list(path_obj.rglob("*.md"))
            files.extend(list(path_obj.rglob("*.txt")))
        
        # Read file contents
        contents = []
        file_info = []
        for file_path in files:
            try:
                # Try to read with UTF-8, fallback to other encodings
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Try latin-1 as fallback
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                
                if content.strip():
                    contents.append(content)
                    file_info.append({
                        'path': str(file_path),
                        'name': file_path.name,
                        'size': len(content)
                    })
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
        
        # Combine contents
        combined_content = '\n\n'.join(contents)
        
        return {
            'path': path,
            'ingested': bool(contents),
            'file_count': len(file_info),
            'files': file_info,
            'content': combined_content,
            'chunks': self._chunk_content(combined_content)
        }
    
    def _chunk_content(self, content: str, chunk_size: int = 1000) -> List[str]:
        """Chunk content for processing.
        
        Args:
            content: Content to chunk
            chunk_size: Maximum size of each chunk
            
        Returns:
            List of content chunks
        """
        if not content:
            return []
        
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph_size = len(paragraph)
            
            if current_size + paragraph_size > chunk_size and current_chunk:
                # Save current chunk and start new one
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_size = paragraph_size
            else:
                # Add to current chunk
                current_chunk.append(paragraph)
                current_size += paragraph_size
        
        # Add remaining chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def _execute_step(self, step: Dict[str, Any], context: Dict[str, Any], 
                     spec: RunSpec, result: JobResult) -> AgentStepLog:
        """Execute a single workflow step.
        
        Args:
            step: Step configuration
            context: Execution context
            spec: Run specification
            result: Job result
            
        Returns:
            Step execution log
        """
        agent_name = step.get('agent', 'Unknown')
        step_name = step.get('name', agent_name)
        
        logger.info(f"Executing step: {step_name} (agent: {agent_name})")
        
        start_time = datetime.now()
        step_log = AgentStepLog(
            agent_name=agent_name,
            status='started',
            timestamp=start_time.isoformat()
        )
        
        try:
            # Get agent instance
            agent = self._get_agent(agent_name)
            if not agent:
                if step.get('optional', False):
                    step_log.status = 'skipped'
                    step_log.output_preview = 'Agent not available (optional step)'
                    return step_log
                else:
                    raise ValueError(f"Agent not found: {agent_name}")
            
            # Validate prerequisites
            validation = self._validate_agent_prerequisites(agent_name, context)
            if not validation.get('validated', True):
                if step.get('optional', False):
                    step_log.status = 'skipped'
                    step_log.output_preview = f"Prerequisites not met: {validation.get('errors', [])}"
                    return step_log
                else:
                    raise ValueError(f"Prerequisites failed: {validation.get('errors', [])}")
            
            # Execute agent
            agent_input = self._prepare_agent_input(agent_name, context)
            agent_output = agent.execute(agent_input)
            
            # Update context with output
            context[step_name] = agent_output
            
            # Update step log
            step_log.status = 'completed'
            step_log.output_preview = self._get_output_preview(agent_output)
            
        except Exception as e:
            logger.error(f"Step {step_name} failed: {e}")
            step_log.status = 'failed'
            step_log.error = str(e)
        
        finally:
            end_time = datetime.now()
            step_log.duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return step_log
    
    def _get_agent(self, agent_name: str):
        """Get agent instance by name.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent instance or None
        """
        # Try to get from registered agents
        if self.agents and agent_name in self.agents:
            return self.agents[agent_name]
        
        # Try to create dynamically
        return self._create_agent(agent_name)
    
    def _create_agent(self, agent_name: str):
        """Create agent instance dynamically.
        
        Args:
            agent_name: Name of the agent to create
            
        Returns:
            Agent instance or None
        """
        try:
            # Map agent names to modules
            agent_modules = {
                'TopicIdentificationAgent': 'src.agents.research',
                'KBIngestionAgent': 'src.agents.ingestion',
                'BlogIngestionAgent': 'src.agents.ingestion',
                'APIIngestionAgent': 'src.agents.ingestion',
                'OutlineCreationAgent': 'src.agents.content',
                'IntroductionWriterAgent': 'src.agents.content',
                'SectionWriterAgent': 'src.agents.content',
                'ConclusionWriterAgent': 'src.agents.content',
                'ContentAssemblyAgent': 'src.agents.content',
                'SEOMetadataAgent': 'src.agents.seo',
                'FileWriterAgent': 'src.agents.publishing'
            }
            
            module_name = agent_modules.get(agent_name)
            if not module_name:
                return None
            
            # Import and create agent
            import importlib
            module = importlib.import_module(module_name)
            agent_class = getattr(module, agent_name)
            
            # Create agent instance
            if self.llm_service:
                agent = agent_class(llm_service=self.llm_service)
            else:
                agent = agent_class()
            
            # Cache for future use
            if self.agents is not None:
                self.agents[agent_name] = agent
            
            return agent
            
        except Exception as e:
            logger.warning(f"Failed to create agent {agent_name}: {e}")
            return None
    
    def _validate_agent_prerequisites(self, agent_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate agent prerequisites.
        
        Args:
            agent_name: Name of the agent
            context: Current execution context
            
        Returns:
            Validation result dictionary
        """
        validation = {
            'validated': True,
            'warnings': [],
            'errors': []
        }
        
        # Agent-specific validation rules
        if 'ingest' in agent_name.lower():
            # Validate ingestion agents
            has_kb = context.get('kb_ingested', {}).get('ingested', False)
            has_blog = context.get('blog_ingested', {}).get('ingested', False)
            has_api = context.get('api_ingested', {}).get('ingested', False)
            
            if not (has_kb or has_blog or has_api):
                validation['warnings'].append('No content sources ingested yet')
        
        elif 'search' in agent_name.lower() or 'rag' in agent_name.lower():
            # Validate search/RAG agents
            if not context.get('kb_ingested', {}).get('ingested', False):
                validation['warnings'].append('KB not ingested before search')
        
        elif 'outline' in agent_name.lower():
            # Validate outline agent
            if not context.get('topic'):
                validation['errors'].append('No topic defined for outline')
                validation['validated'] = False
        
        elif 'write' in agent_name.lower() or 'writer' in agent_name.lower():
            # Validate writer agents
            if not context.get('outline_creation', {}).get('outline'):
                validation['warnings'].append('Writing without outline')
        
        elif 'seo' in agent_name.lower() or 'keyword' in agent_name.lower():
            # Validate SEO agents
            if not context.get('content_assembly', {}).get('content'):
                validation['warnings'].append('SEO optimization before content assembly')
        
        elif 'file' in agent_name.lower() or 'write_file' in agent_name.lower():
            # Validate file writing
            if not context.get('content_assembly', {}).get('content'):
                validation['errors'].append('Cannot write file without content')
                validation['validated'] = False
        
        return validation
    
    def _prepare_agent_input(self, agent_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input for agent execution.
        
        Args:
            agent_name: Name of the agent
            context: Execution context
            
        Returns:
            Agent input dictionary
        """
        # Base input
        agent_input = {
            'topic': context.get('topic'),
            'context': context
        }
        
        # Agent-specific input preparation
        if 'outline' in agent_name.lower():
            agent_input['kb_content'] = context.get('kb_ingested', {}).get('content', '')
            agent_input['blog_content'] = context.get('blog_ingested', {}).get('content', '')
        
        elif 'writer' in agent_name.lower():
            agent_input['outline'] = context.get('outline_creation', {}).get('outline', {})
        
        elif 'assembly' in agent_name.lower():
            agent_input['introduction'] = context.get('introduction_writer', {}).get('content', '')
            agent_input['sections'] = context.get('section_writer', {}).get('sections', [])
            agent_input['conclusion'] = context.get('conclusion_writer', {}).get('content', '')
        
        elif 'seo' in agent_name.lower():
            agent_input['content'] = context.get('content_assembly', {}).get('content', '')
        
        elif 'file' in agent_name.lower():
            agent_input['content'] = context.get('content_assembly', {}).get('content', '')
            agent_input['metadata'] = context.get('seo_metadata', {}).get('metadata', {})
            agent_input['output_dir'] = context.get('output_dir', './output')
        
        return agent_input
    
    def _get_output_preview(self, output: Any, max_length: int = 200) -> str:
        """Get preview of agent output.
        
        Args:
            output: Agent output
            max_length: Maximum preview length
            
        Returns:
            Preview string
        """
        if not output:
            return 'No output'
        
        if isinstance(output, dict):
            # Try to get meaningful preview from dict
            if 'content' in output:
                preview = str(output['content'])[:max_length]
            elif 'text' in output:
                preview = str(output['text'])[:max_length]
            elif 'result' in output:
                preview = str(output['result'])[:max_length]
            else:
                preview = json.dumps(output)[:max_length]
        else:
            preview = str(output)[:max_length]
        
        if len(str(output)) > max_length:
            preview += '...'
        
        return preview
    
    def _write_output(self, context: Dict[str, Any], spec: RunSpec, result: JobResult):
        """Write final output files.
        
        Args:
            context: Execution context with results
            spec: Run specification
            result: Job result to update
        """
        try:
            output_dir = spec.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate slug from topic
            slug = urlify(spec.topic or 'output')
            
            # Write main content file
            content = context.get('content_assembly', {}).get('content', '')
            if content:
                output_file = output_dir / f"{slug}.md"
                with open(output_file, 'w', encoding='utf-8') as f:
                    # Add frontmatter
                    metadata = context.get('seo_metadata', {}).get('metadata', {})
                    if metadata:
                        f.write("---\n")
                        for key, value in metadata.items():
                            f.write(f"{key}: {value}\n")
                        f.write("---\n\n")
                    
                    f.write(content)
                
                result.files_written.append(str(output_file))
                logger.info(f"Written output to: {output_file}")
            
            # Write artifacts JSON
            artifacts_file = output_dir / f"{slug}_artifacts.json"
            artifacts = {
                'topic': spec.topic,
                'template': spec.template_name,
                'timestamp': datetime.now().isoformat(),
                'context': self._clean_context_for_save(context)
            }
            
            with open(artifacts_file, 'w', encoding='utf-8') as f:
                json.dump(artifacts, f, indent=2, default=str)
            
            result.files_written.append(str(artifacts_file))
            result.artifacts = artifacts
            
            logger.info(f"Written artifacts to: {artifacts_file}")
            
        except Exception as e:
            logger.error(f"Failed to write output: {e}")
            result.errors.append(f"Output write failed: {e}")
    
    def _clean_context_for_save(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Clean context for saving to file.
        
        Args:
            context: Context to clean
            
        Returns:
            Cleaned context
        """
        # Remove large content fields
        cleaned = {}
        
        for key, value in context.items():
            if key in ['kb_ingested', 'blog_ingested', 'api_ingested', 'docs_ingested']:
                # Only save metadata, not full content
                if isinstance(value, dict):
                    cleaned[key] = {
                        'path': value.get('path'),
                        'file_count': value.get('file_count'),
                        'ingested': value.get('ingested')
                    }
            elif key in ['config', 'llm_service', 'database_service']:
                # Skip service objects
                continue
            else:
                # Convert complex objects to strings
                cleaned[key] = convert_paths_to_strings(value)
        
        return cleaned
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """List active jobs.
        
        Returns:
            List of active job summaries
        """
        jobs = []
        for job_id, result in self.active_jobs.items():
            jobs.append({
                'job_id': job_id,
                'status': result.status.value,
                'topic': result.topic,
                'start_time': result.start_time.isoformat() if result.start_time else None,
                'steps_completed': len([s for s in result.steps if s.status == 'completed']),
                'total_steps': len(result.steps)
            })
        return jobs
    
    def get_job(self, job_id: str) -> Optional[JobResult]:
        """Get job details.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job result or None if not found
        """
        return self.active_jobs.get(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancelled, False if not found
        """
        if job_id in self.active_jobs:
            result = self.active_jobs[job_id]
            result.status = JobStatus.CANCELLED
            result.end_time = datetime.now()
            if result.start_time:
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            del self.active_jobs[job_id]
            logger.info(f"Cancelled job: {job_id}")
            return True
        return False


# Singleton instance
_engine_instance = None


def get_engine(**kwargs) -> UnifiedEngine:
    """Get or create the unified engine instance.
    
    Args:
        **kwargs: Optional configuration parameters
        
    Returns:
        UnifiedEngine instance
    """
    global _engine_instance
    
    if _engine_instance is None:
        _engine_instance = UnifiedEngine(**kwargs)
    
    return _engine_instance
# DOCGEN:LLM-FIRST@v4