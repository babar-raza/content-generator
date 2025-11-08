"""Workflow Visualizer - Converts YAML workflow definitions to interactive React Flow graphs."""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class WorkflowVisualizer:
    """Converts YAML workflow definitions into visual graphs for React Flow."""
    
    def __init__(self, workflow_dir: str = './templates'):
        self.workflow_dir = Path(workflow_dir)
        self.workflows = {}
        self.execution_state = {}
        self.load_workflows()
    
    def load_workflows(self):
        """Load workflow definitions from YAML files."""
        workflow_file = self.workflow_dir / 'workflows.yaml'
        
        if not workflow_file.exists():
            logger.warning(f"Workflow file not found: {workflow_file}")
            # Create a sample workflow for demo purposes
            self.workflows = self._create_sample_workflow()
            return
        
        try:
            with open(workflow_file, 'r') as f:
                self.workflows = yaml.safe_load(f)
            logger.info(f"Loaded workflows from {workflow_file}")
        except Exception as e:
            logger.error(f"Error loading workflows: {e}")
            self.workflows = self._create_sample_workflow()
    
    def _create_sample_workflow(self) -> Dict[str, Any]:
        """Create a sample workflow for demonstration."""
        return {
            'profiles': {
                'fast-draft': {
                    'name': 'Fast Draft',
                    'description': 'Quick content generation workflow',
                    'steps': [
                        {
                            'id': 'initialize',
                            'name': 'Initialize',
                            'category': 'orchestration',
                            'dependencies': []
                        },
                        {
                            'id': 'research',
                            'name': 'Research',
                            'category': 'research',
                            'dependencies': ['initialize']
                        },
                        {
                            'id': 'outline',
                            'name': 'Create Outline',
                            'category': 'planning',
                            'dependencies': ['research']
                        },
                        {
                            'id': 'write_content',
                            'name': 'Write Content',
                            'category': 'content',
                            'dependencies': ['outline']
                        },
                        {
                            'id': 'review',
                            'name': 'Review',
                            'category': 'quality',
                            'dependencies': ['write_content']
                        },
                        {
                            'id': 'finalize',
                            'name': 'Finalize',
                            'category': 'orchestration',
                            'dependencies': ['review']
                        }
                    ]
                },
                'full': {
                    'name': 'Full Production',
                    'description': 'Complete workflow with all steps',
                    'steps': [
                        {
                            'id': 'initialize',
                            'name': 'Initialize',
                            'category': 'orchestration',
                            'dependencies': []
                        },
                        {
                            'id': 'deep_research',
                            'name': 'Deep Research',
                            'category': 'research',
                            'dependencies': ['initialize']
                        },
                        {
                            'id': 'competitive_analysis',
                            'name': 'Competitive Analysis',
                            'category': 'research',
                            'dependencies': ['initialize']
                        },
                        {
                            'id': 'outline',
                            'name': 'Create Outline',
                            'category': 'planning',
                            'dependencies': ['deep_research', 'competitive_analysis']
                        },
                        {
                            'id': 'write_content',
                            'name': 'Write Content',
                            'category': 'content',
                            'dependencies': ['outline']
                        },
                        {
                            'id': 'fact_check',
                            'name': 'Fact Check',
                            'category': 'quality',
                            'dependencies': ['write_content']
                        },
                        {
                            'id': 'seo_optimize',
                            'name': 'SEO Optimization',
                            'category': 'optimization',
                            'dependencies': ['write_content']
                        },
                        {
                            'id': 'review',
                            'name': 'Review',
                            'category': 'quality',
                            'dependencies': ['fact_check', 'seo_optimize']
                        },
                        {
                            'id': 'finalize',
                            'name': 'Finalize',
                            'category': 'orchestration',
                            'dependencies': ['review']
                        }
                    ]
                }
            }
        }
    
    def create_visual_graph(self, profile_name: str) -> Dict[str, Any]:
        """Create a React Flow compatible graph from a workflow profile."""
        if profile_name not in self.workflows.get('profiles', {}):
            raise ValueError(f"Profile '{profile_name}' not found")
        
        profile = self.workflows['profiles'][profile_name]
        order = profile.get('order', [])
        
        # Convert string-based order to full step definitions
        steps = self._convert_order_to_steps(order, profile_name)
        
        # Create nodes and edges
        nodes = self._create_nodes(steps, profile_name)
        edges = self._create_edges(steps)
        
        # Calculate layout positions
        self._calculate_hierarchical_layout(nodes, edges)
        
        return {
            'profile_name': profile_name,
            'name': profile.get('name', profile_name),
            'description': profile.get('description', ''),
            'nodes': nodes,
            'edges': edges,
            'metadata': {
                'created_at': datetime.now(timezone.utc).isoformat(),
                'total_steps': len(steps),
                'categories': list(set(step.get('category', 'default') for step in steps))
            }
        }
    
    def _create_nodes(self, steps: List[Dict[str, Any]], profile_name: str) -> List[Dict[str, Any]]:
        """Create React Flow nodes from workflow steps."""
        nodes = []
        
        for step in steps:
            step_id = step['id']
            category = step.get('category', 'default')
            
            # Get execution state if available
            state_key = f"{profile_name}:{step_id}"
            execution_state = self.execution_state.get(state_key, {})
            
            node = {
                'id': step_id,
                'type': self._get_node_type(category),
                'position': {'x': 0, 'y': 0},  # Will be calculated later
                'data': {
                    'label': step.get('name', step_id),
                    'category': category,
                    'description': step.get('description', ''),
                    'status': execution_state.get('status', 'pending'),
                    'progress': execution_state.get('progress', 0),
                    'startTime': execution_state.get('start_time'),
                    'endTime': execution_state.get('end_time'),
                    'duration': execution_state.get('duration'),
                    'error': execution_state.get('error')
                },
                'style': self._get_node_style(category, execution_state.get('status', 'pending'))
            }
            
            nodes.append(node)
        
        return nodes
    
    def _create_edges(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create React Flow edges from workflow dependencies."""
        edges = []
        
        for step in steps:
            step_id = step['id']
            dependencies = step.get('dependencies', [])
            
            for dep_id in dependencies:
                edge = {
                    'id': f"{dep_id}-{step_id}",
                    'source': dep_id,
                    'target': step_id,
                    'type': 'smoothstep',
                    'animated': True,
                    'style': {
                        'stroke': '#64748b',
                        'strokeWidth': 2
                    },
                    'markerEnd': {
                        'type': 'arrowclosed',
                        'color': '#64748b'
                    }
                }
                
                edges.append(edge)
        
        return edges
    
    def _get_node_type(self, category: str) -> str:
        """Map workflow category to React Flow node type."""
        type_mapping = {
            'orchestration': 'orchestrationNode',
            'research': 'researchNode',
            'planning': 'planningNode',
            'content': 'contentNode',
            'quality': 'qualityNode',
            'optimization': 'optimizationNode'
        }
        
        return type_mapping.get(category, 'default')
    
    def _get_node_style(self, category: str, status: str) -> Dict[str, Any]:
        """Get node styling based on category and status."""
        # Base styles by category
        category_colors = {
            'orchestration': {'bg': '#f3f4f6', 'border': '#9ca3af', 'text': '#1f2937'},
            'research': {'bg': '#dbeafe', 'border': '#3b82f6', 'text': '#1e40af'},
            'planning': {'bg': '#fef3c7', 'border': '#f59e0b', 'text': '#92400e'},
            'content': {'bg': '#d1fae5', 'border': '#10b981', 'text': '#065f46'},
            'quality': {'bg': '#ede9fe', 'border': '#8b5cf6', 'text': '#5b21b6'},
            'optimization': {'bg': '#fce7f3', 'border': '#ec4899', 'text': '#9f1239'}
        }
        
        colors = category_colors.get(category, {'bg': '#f3f4f6', 'border': '#9ca3af', 'text': '#1f2937'})
        
        # Modify based on status
        if status == 'running':
            colors['border'] = '#3b82f6'
            colors['bg'] = '#dbeafe'
        elif status == 'completed':
            colors['border'] = '#10b981'
            colors['bg'] = '#d1fae5'
        elif status == 'failed':
            colors['border'] = '#ef4444'
            colors['bg'] = '#fee2e2'
        elif status == 'paused':
            colors['border'] = '#f59e0b'
            colors['bg'] = '#fef3c7'
        
        return {
            'background': colors['bg'],
            'border': f"2px solid {colors['border']}",
            'borderRadius': '8px',
            'padding': '12px',
            'minWidth': '180px',
            'color': colors['text'],
            'fontSize': '14px',
            'fontWeight': '500',
            'boxShadow': '0 2px 4px rgba(0, 0, 0, 0.1)'
        }
    
    def _calculate_hierarchical_layout(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        """Calculate hierarchical layout positions for nodes."""
        # Build dependency graph
        dependencies = {}
        dependents = {}
        
        for node in nodes:
            node_id = node['id']
            dependencies[node_id] = []
            dependents[node_id] = []
        
        for edge in edges:
            source = edge['source']
            target = edge['target']
            dependencies[target].append(source)
            dependents[source].append(target)
        
        # Calculate levels using topological sort
        levels = {}
        visited = set()
        
        def get_level(node_id):
            if node_id in levels:
                return levels[node_id]
            
            if node_id in visited:
                return 0  # Cycle detection
            
            visited.add(node_id)
            
            if not dependencies[node_id]:
                level = 0
            else:
                level = max(get_level(dep) for dep in dependencies[node_id]) + 1
            
            levels[node_id] = level
            visited.remove(node_id)
            return level
        
        for node in nodes:
            get_level(node['id'])
        
        # Group nodes by level
        level_groups = {}
        for node_id, level in levels.items():
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(node_id)
        
        # Calculate positions
        x_spacing = 250
        y_spacing = 150
        
        for node in nodes:
            node_id = node['id']
            level = levels[node_id]
            level_nodes = level_groups[level]
            index = level_nodes.index(node_id)
            
            # Center nodes horizontally within their level
            total_width = len(level_nodes) * x_spacing
            start_x = -total_width / 2 + x_spacing / 2
            
            node['position'] = {
                'x': start_x + index * x_spacing,
                'y': level * y_spacing
            }
    
    def update_step_status(self, profile_name: str, step_id: str, status: str, data: Optional[Dict[str, Any]] = None):
        """Update the execution status of a workflow step."""
        state_key = f"{profile_name}:{step_id}"
        
        if state_key not in self.execution_state:
            self.execution_state[state_key] = {
                'status': 'pending',
                'progress': 0
            }
        
        state = self.execution_state[state_key]
        old_status = state.get('status')
        
        # Update status
        state['status'] = status
        
        # Handle status transitions
        if status == 'running' and old_status != 'running':
            state['start_time'] = datetime.now(timezone.utc).isoformat()
        
        if status in ['completed', 'failed']:
            if 'start_time' in state:
                start = datetime.fromisoformat(state['start_time'])
                end = datetime.now(timezone.utc)
                state['end_time'] = end.isoformat()
                state['duration'] = (end - start).total_seconds()
            
            if status == 'completed':
                state['progress'] = 100
        
        # Add any additional data
        if data:
            state.update(data)
        
        logger.info(f"Updated step {step_id} status to {status}")
    
    def get_execution_metrics(self, profile_name: str) -> Dict[str, Any]:
        """Get execution metrics for a workflow profile."""
        if profile_name not in self.workflows.get('profiles', {}):
            raise ValueError(f"Profile '{profile_name}' not found")
        
        profile = self.workflows['profiles'][profile_name]
        steps = profile['steps']
        
        total_steps = len(steps)
        completed = 0
        failed = 0
        running = 0
        pending = 0
        total_duration = 0.0
        
        for step in steps:
            state_key = f"{profile_name}:{step['id']}"
            state = self.execution_state.get(state_key, {})
            status = state.get('status', 'pending')
            
            if status == 'completed':
                completed += 1
                if 'duration' in state:
                    total_duration += state['duration']
            elif status == 'failed':
                failed += 1
            elif status == 'running':
                running += 1
            else:
                pending += 1
        
        overall_progress = (completed / total_steps * 100) if total_steps > 0 else 0
        
        return {
            'profile_name': profile_name,
            'total_steps': total_steps,
            'completed': completed,
            'failed': failed,
            'running': running,
            'pending': pending,
            'overall_progress': round(overall_progress, 2),
            'total_duration': round(total_duration, 2),
            'average_step_duration': round(total_duration / completed, 2) if completed > 0 else 0
        }
    
    def reset_execution_state(self, profile_name: str):
        """Reset execution state for a workflow profile."""
        if profile_name not in self.workflows.get('profiles', {}):
            raise ValueError(f"Profile '{profile_name}' not found")
        
        profile = self.workflows['profiles'][profile_name]
        
        for step in profile['steps']:
            state_key = f"{profile_name}:{step['id']}"
            if state_key in self.execution_state:
                del self.execution_state[state_key]
        
        logger.info(f"Reset execution state for profile: {profile_name}")
    
    def _get_agent_metadata(self, agent_id: str) -> Dict[str, str]:
        """Get metadata for an agent including category and display name.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Dict with 'name', 'category', and 'description'
        """
        # Map agent IDs to categories and readable names
        agent_metadata = {
            # Ingestion agents
            'ingest_kb': {'name': 'Ingest KB', 'category': 'ingestion', 'description': 'Load knowledge base content'},
            'ingest_kb_node': {'name': 'Ingest KB', 'category': 'ingestion', 'description': 'Load knowledge base content'},
            'ingest_blog': {'name': 'Ingest Blog', 'category': 'ingestion', 'description': 'Load blog content'},
            'ingest_blog_node': {'name': 'Ingest Blog', 'category': 'ingestion', 'description': 'Load blog content'},
            'ingest_api': {'name': 'Ingest API', 'category': 'ingestion', 'description': 'Load API reference content'},
            'ingest_api_node': {'name': 'Ingest API', 'category': 'ingestion', 'description': 'Load API reference content'},
            
            # Topic agents
            'identify_blog_topics': {'name': 'Identify Topics', 'category': 'research', 'description': 'Identify potential blog topics'},
            'identify_topics_node': {'name': 'Identify Topics', 'category': 'research', 'description': 'Identify potential topics'},
            'check_duplication': {'name': 'Check Duplication', 'category': 'research', 'description': 'Check for duplicate content'},
            'check_duplication_node': {'name': 'Check Duplication', 'category': 'research', 'description': 'Check for duplicate content'},
            
            # RAG agents
            'gather_rag_kb': {'name': 'KB Search', 'category': 'research', 'description': 'Search knowledge base'},
            'kb_search_node': {'name': 'KB Search', 'category': 'research', 'description': 'Search knowledge base'},
            'gather_rag_blog': {'name': 'Blog Search', 'category': 'research', 'description': 'Search blog content'},
            'blog_search_node': {'name': 'Blog Search', 'category': 'research', 'description': 'Search blog content'},
            'gather_rag_api': {'name': 'API Search', 'category': 'research', 'description': 'Search API reference'},
            'api_search_node': {'name': 'API Search', 'category': 'research', 'description': 'Search API reference'},
            
            # Planning agents
            'topic_prep_node': {'name': 'Topic Prep', 'category': 'planning', 'description': 'Prepare topic for writing'},
            'create_outline': {'name': 'Create Outline', 'category': 'planning', 'description': 'Generate content outline'},
            'create_outline_node': {'name': 'Create Outline', 'category': 'planning', 'description': 'Generate content outline'},
            
            # Content agents
            'write_introduction': {'name': 'Write Introduction', 'category': 'content', 'description': 'Write introduction section'},
            'introduction_writer_node': {'name': 'Write Introduction', 'category': 'content', 'description': 'Write introduction section'},
            'write_sections': {'name': 'Write Sections', 'category': 'content', 'description': 'Write main content sections'},
            'section_writer_node': {'name': 'Write Sections', 'category': 'content', 'description': 'Write main content sections'},
            'write_conclusion': {'name': 'Write Conclusion', 'category': 'content', 'description': 'Write conclusion section'},
            'conclusion_writer_node': {'name': 'Write Conclusion', 'category': 'content', 'description': 'Write conclusion section'},
            'generate_supplementary': {'name': 'Generate Supplementary', 'category': 'content', 'description': 'Generate supplementary content'},
            'supplementary_content_node': {'name': 'Generate Supplementary', 'category': 'content', 'description': 'Generate supplementary content'},
            'assemble_content': {'name': 'Assemble Content', 'category': 'content', 'description': 'Assemble all content sections'},
            'content_assembly_node': {'name': 'Assemble Content', 'category': 'content', 'description': 'Assemble all content sections'},
            
            # Code agents
            'generate_code': {'name': 'Generate Code', 'category': 'code', 'description': 'Generate code examples'},
            'code_generation_node': {'name': 'Generate Code', 'category': 'code', 'description': 'Generate code examples'},
            'extract_code': {'name': 'Extract Code', 'category': 'code', 'description': 'Extract code from content'},
            'code_extraction_node': {'name': 'Extract Code', 'category': 'code', 'description': 'Extract code from content'},
            'inject_license': {'name': 'Inject License', 'category': 'code', 'description': 'Add license headers'},
            'license_injection_node': {'name': 'Inject License', 'category': 'code', 'description': 'Add license headers'},
            'validate_code': {'name': 'Validate Code', 'category': 'quality', 'description': 'Validate code samples'},
            'code_validation_node': {'name': 'Validate Code', 'category': 'quality', 'description': 'Validate code samples'},
            'split_code': {'name': 'Split Code', 'category': 'code', 'description': 'Split code into files'},
            'code_splitting_node': {'name': 'Split Code', 'category': 'code', 'description': 'Split code into files'},
            
            # SEO agents
            'generate_seo': {'name': 'Generate SEO', 'category': 'optimization', 'description': 'Generate SEO metadata'},
            'seo_metadata_node': {'name': 'Generate SEO', 'category': 'optimization', 'description': 'Generate SEO metadata'},
            'extract_keywords': {'name': 'Extract Keywords', 'category': 'optimization', 'description': 'Extract keywords from content'},
            'keyword_extraction_node': {'name': 'Extract Keywords', 'category': 'optimization', 'description': 'Extract keywords'},
            'inject_keywords': {'name': 'Inject Keywords', 'category': 'optimization', 'description': 'Inject keywords into content'},
            'keyword_injection_node': {'name': 'Inject Keywords', 'category': 'optimization', 'description': 'Inject keywords'},
            
            # Publishing agents
            'inject_api_links': {'name': 'Inject API Links', 'category': 'publishing', 'description': 'Add API reference links'},
            'create_gist_readme': {'name': 'Create Gist README', 'category': 'publishing', 'description': 'Create README for Gist'},
            'gist_readme_node': {'name': 'Create Gist README', 'category': 'publishing', 'description': 'Create README for Gist'},
            'upload_gist': {'name': 'Upload Gist', 'category': 'publishing', 'description': 'Upload code to Gist'},
            'gist_upload_node': {'name': 'Upload Gist', 'category': 'publishing', 'description': 'Upload code to Gist'},
            'validate_links': {'name': 'Validate Links', 'category': 'quality', 'description': 'Validate all links'},
            'link_validation_node': {'name': 'Validate Links', 'category': 'quality', 'description': 'Validate all links'},
            'add_frontmatter': {'name': 'Add Frontmatter', 'category': 'publishing', 'description': 'Add frontmatter metadata'},
            'frontmatter_node': {'name': 'Add Frontmatter', 'category': 'publishing', 'description': 'Add frontmatter metadata'},
            'write_file': {'name': 'Write File', 'category': 'publishing', 'description': 'Write final output file'},
            'write_file_node': {'name': 'Write File', 'category': 'publishing', 'description': 'Write final output file'},
            
            # Review agents
            'content_reviewer_node': {'name': 'Content Review', 'category': 'quality', 'description': 'Review final content'},
            'model_selection_node': {'name': 'Model Selection', 'category': 'orchestration', 'description': 'Select AI model'},
        }
        
        # Get metadata or create default
        metadata = agent_metadata.get(agent_id, {
            'name': agent_id.replace('_', ' ').title(),
            'category': 'default',
            'description': f'Execute {agent_id}'
        })
        
        return metadata
    
    def _convert_order_to_steps(self, order: List[Any], profile_name: str) -> List[Dict[str, Any]]:
        """Convert workflow order (strings or dicts) to full step definitions.
        
        Args:
            order: List of agent IDs (strings) or step definitions (dicts)
            profile_name: Name of the workflow profile
            
        Returns:
            List of step definitions with id, name, category, dependencies
        """
        steps = []
        dependencies_map = self.workflows.get('dependencies', {})
        
        for item in order:
            if isinstance(item, dict):
                # Already a full step definition
                steps.append(item)
            elif isinstance(item, str):
                # String agent ID - convert to full definition
                metadata = self._get_agent_metadata(item)
                step = {
                    'id': item,
                    'name': metadata['name'],
                    'category': metadata['category'],
                    'description': metadata['description'],
                    'dependencies': dependencies_map.get(item, [])
                }
                steps.append(step)
            else:
                logger.warning(f"Unknown step type in order: {type(item)}")
        
        return steps
    
