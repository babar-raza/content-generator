"""Multi-Template Manager - Supports multiple templates per type

Loads and manages all templates from /templates/ directory.
Supports selection of different templates for blog, code, and frontmatter.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class TemplateDefinition:
    """Definition of a single template"""
    name: str
    type: str  # 'blog', 'code', 'frontmatter'
    content: str
    schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_file: Optional[Path] = None
    
    def get_required_fields(self) -> List[str]:
        """Get list of required template fields"""
        return self.schema.get('required', [])
    
    def get_optional_fields(self) -> List[str]:
        """Get list of optional template fields"""
        return self.schema.get('optional', [])


class MultiTemplateManager:
    """Manager for multiple templates of each type"""
    
    def __init__(self, templates_dir: Path = None):
        self.templates_dir = templates_dir or Path('./templates')
        self._templates: Dict[str, List[TemplateDefinition]] = {
            'blog': [],
            'code': [],
            'frontmatter': [],
            'markdown': []
        }
        self._loaded = False
        
    def load_templates(self):
        """Load all templates from templates directory"""
        if self._loaded:
            return
            
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            self._loaded = True
            return
        
        # Load YAML template files
        for template_file in self.templates_dir.glob('*.yaml'):
            try:
                self._load_template_file(template_file)
            except Exception as e:
                logger.warning(f"Failed to load template {template_file}: {e}")
        
        self._loaded = True
        
        # Log summary
        for ttype, templates in self._templates.items():
            if templates:
                logger.info(f"✓ Loaded {len(templates)} {ttype} template(s)")
    
    def _load_template_file(self, filepath: Path):
        """Load a single template file"""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data:
            return
        
        # Determine template type from filename
        template_type = self._get_type_from_filename(filepath.stem)
        
        # Handle new format (with 'templates' key)
        if 'templates' in data:
            for template_data in data['templates']:
                template = self._create_template(template_data, template_type, filepath)
                if template:
                    self._templates[template_type].append(template)
        
        # Handle old format (direct structure)
        elif 'blog_structure' in data or 'section_templates' in data:
            # Old blog template format
            template = TemplateDefinition(
                name=filepath.stem,
                type='blog',
                content=self._convert_old_blog_format(data),
                schema={},
                metadata={'legacy': True},
                source_file=filepath
            )
            self._templates['blog'].append(template)
        
        # Handle code templates format
        elif any(k in data for k in ['api_documentation', 'code_example', 'library_guide']):
            for name, content in data.items():
                template = TemplateDefinition(
                    name=name,
                    type='code',
                    content=str(content),
                    schema={},
                    metadata={},
                    source_file=filepath
                )
                self._templates['code'].append(template)
    
    def _get_type_from_filename(self, filename: str) -> str:
        """Determine template type from filename"""
        filename_lower = filename.lower()
        
        if 'blog' in filename_lower:
            return 'blog'
        elif 'code' in filename_lower:
            return 'code'
        elif 'frontmatter' in filename_lower:
            return 'frontmatter'
        else:
            return 'markdown'
    
    def _create_template(self, data: Dict[str, Any], default_type: str, source_file: Path) -> Optional[TemplateDefinition]:
        """Create a template definition from data"""
        if 'name' not in data:
            return None
        
        template_type = data.get('type', default_type)
        content = data.get('content', data.get('template', ''))
        
        return TemplateDefinition(
            name=data['name'],
            type=template_type,
            content=content,
            schema=data.get('schema', {}),
            metadata=data.get('metadata', {}),
            source_file=source_file
        )
    
    def _convert_old_blog_format(self, data: Dict[str, Any]) -> str:
        """Convert old blog template format to content string"""
        # Extract structure
        structure = data.get('blog_structure', {}).get('default', {})
        sections = structure.get('sections', [])
        
        # Build template content
        content_parts = ['# {{title}}\n\n']
        
        for section in sections:
            content_parts.append(f'{{{{ {section} }}}}\n\n')
        
        return ''.join(content_parts)
    
    def get_templates_by_type(self, template_type: str) -> List[TemplateDefinition]:
        """Get all templates of a specific type"""
        if not self._loaded:
            self.load_templates()
        
        return self._templates.get(template_type, [])
    
    def get_template(self, name: str, template_type: str = None) -> Optional[TemplateDefinition]:
        """Get a specific template by name"""
        if not self._loaded:
            self.load_templates()
        
        # Search in specific type if provided
        if template_type:
            for template in self._templates.get(template_type, []):
                if template.name == name:
                    return template
        
        # Search in all types
        for templates_list in self._templates.values():
            for template in templates_list:
                if template.name == name:
                    return template
        
        return None
    
    def list_all_templates(self) -> Dict[str, List[str]]:
        """List all available templates grouped by type"""
        if not self._loaded:
            self.load_templates()
        
        return {
            ttype: [t.name for t in templates]
            for ttype, templates in self._templates.items()
            if templates
        }
    
    def get_template_choices(self) -> List[Dict[str, str]]:
        """Get template choices for UI dropdown"""
        if not self._loaded:
            self.load_templates()
        
        choices = []
        for ttype, templates in self._templates.items():
            for template in templates:
                choices.append({
                    'name': template.name,
                    'type': template.type,
                    'label': f"{template.name} ({template.type})",
                    'description': template.metadata.get('description', '')
                })
        
        return choices
    
    def render_template(self, template: TemplateDefinition, context: Dict[str, Any]) -> str:
        """Render a template with context data"""
        content = template.content
        
        # Simple placeholder replacement
        for key, value in context.items():
            placeholder = f'{{{{{key}}}}}'
            content = content.replace(placeholder, str(value) if value else '')
        
        return content


# Global instance
_template_manager: Optional[MultiTemplateManager] = None


def get_template_manager() -> MultiTemplateManager:
    """Get global template manager instance"""
    global _template_manager
    if _template_manager is None:
        _template_manager = MultiTemplateManager()
        _template_manager.load_templates()
    return _template_manager
