"""Unified execution engine for CLI and Web."""

from .executor import UnifiedJobExecutor, JobConfig
from .input_resolver import InputResolver, ContextSet
from .aggregator import OutputAggregator, AggregatorReport, TemplateSchema, SectionRequirement
from .context_merger import ContextMerger
from .completeness_gate import CompletenessGate
from .agent_tracker import AgentExecutionTracker, AgentRun
from .slug_service import slugify
from .output_path_resolver import resolve_output_path, is_blog_template
from .device import GpuManager, get_gpu_manager, DeviceType
from .exceptions import *
from .engine import UnifiedEngine, get_engine, RunSpec, JobResult, JobStatus

__all__ = [
    'UnifiedJobExecutor',
    'JobConfig',
    'JobResult',
    'InputResolver',
    'ContextSet',
    'OutputAggregator',
    'AggregatorReport',
    'TemplateSchema',
    'SectionRequirement',
    'ContextMerger',
    'CompletenessGate',
    'AgentExecutionTracker',
    'AgentRun',
    'slugify',
    'resolve_output_path',
    'is_blog_template',
    'GpuManager',
    'get_gpu_manager',
    'DeviceType',
    'UnifiedEngine',
    'get_engine',
    'RunSpec',
    'JobResult',
    'JobStatus',
]
# DOCGEN:LLM-FIRST@v4