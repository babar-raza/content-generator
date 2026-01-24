"""First-Class Template Registry - Schema-validated template system"""

import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Pattern
from dataclasses import dataclass, field
from enum import Enum

from ..utils.path_utils import get_repo_root


class TemplateType(Enum):
    """Template types"""
    BLOG = "blog"
    CODE = "code"
    MARKDOWN = "markdown"
    YAML = "yaml"


@dataclass
class TemplateSchema:
    """Template schema definition"""
    required_placeholders: List[str] = field(default_factory=list)
    optional_placeholders: List[str] = field(default_factory=list)
    required_sections: List[str] = field(default_factory=list)
    
    def all_placeholders(self) -> Set[str]:
        """Get all allowed placeholders"""
        return set(self.required_placeholders + self.optional_placeholders)
    
    def validate_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate that data matches schema.
        
        Args:
            data: Data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required placeholders
        for placeholder in self.required_placeholders:
            if placeholder not in data or not data[placeholder]:
                errors.append(f"Missing required placeholder: {placeholder}")
        
        # Check for unknown placeholders (strict mode)
        allowed = self.all_placeholders()
        for key in data.keys():
            if key not in allowed:
                errors.append(f"Unknown placeholder: {key} (not in schema)")
        
        return errors


@dataclass
class Template:
    """Registered template with metadata and precompiled patterns."""
    name: str
    type: TemplateType
    template_content: str
    schema: TemplateSchema
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    _placeholder_pattern: Optional[re.Pattern] = field(default=None, init=False, repr=False)
    _compiled_placeholders: Optional[Set[str]] = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        """Precompile regex patterns after initialization."""
        self.precompile()
    
    def precompile(self):
        """Precompile template patterns for faster rendering."""
        if self._placeholder_pattern is None:
            self._placeholder_pattern = re.compile(r'\{\{(\w+)\}\}')
        if self._compiled_placeholders is None:
            self._compiled_placeholders = self.extract_placeholders()
    
    def extract_placeholders(self) -> Set[str]:
        """Extract all placeholders from template content (cached)."""
        if self._compiled_placeholders is not None:
            return self._compiled_placeholders
        
        # Match {{placeholder}} pattern using precompiled regex
        if self._placeholder_pattern is None:
            self._placeholder_pattern = re.compile(r'\{\{(\w+)\}\}')
        
        matches = self._placeholder_pattern.findall(self.template_content)
        return set(matches)
    
    def validate_template(self) -> List[str]:
        """Validate template structure.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Extract placeholders from template
        placeholders_in_template = self.extract_placeholders()
        schema_placeholders = self.schema.all_placeholders()
        
        # Check that all schema placeholders are in template
        for placeholder in self.schema.required_placeholders:
            if placeholder not in placeholders_in_template:
                errors.append(
                    f"Required placeholder '{placeholder}' not found in template"
                )
        
        # Check that all template placeholders are in schema
        for placeholder in placeholders_in_template:
            if placeholder not in schema_placeholders:
                errors.append(
                    f"Placeholder '{placeholder}' in template but not in schema"
                )
        
        # Check required sections
        for section in self.schema.required_sections:
            if section not in self.template_content:
                errors.append(
                    f"Required section '{section}' not found in template"
                )
        
        return errors
    
    def render(self, data: Dict[str, Any], strict: bool = True) -> str:
        """Render template with data.
        
        Args:
            data: Data to fill placeholders
            strict: If True, fail on unknown placeholders or missing required
            
        Returns:
            Rendered template string
            
        Raises:
            ValueError: If strict=True and validation fails
        """
        if strict:
            # Validate data against schema
            errors = self.schema.validate_data(data)
            if errors:
                raise ValueError(
                    f"Template data validation failed for '{self.name}':\n" +
                    "\n".join(f"  - {e}" for e in errors)
                )
        
        # Render template
        result = self.template_content
        
        # Replace required placeholders
        for key in self.schema.required_placeholders:
            placeholder = f"{{{{{key}}}}}"
            value = data.get(key, "")
            result = result.replace(placeholder, str(value))
        
        # Replace optional placeholders (remove if not provided)
        for key in self.schema.optional_placeholders:
            placeholder = f"{{{{{key}}}}}"
            value = data.get(key, "")
            if value:
                result = result.replace(placeholder, str(value))
            else:
                # Remove line with empty optional placeholder
                lines = result.split('\n')
                result = '\n'.join(
                    line for line in lines
                    if placeholder not in line
                )

        return result

    def validate_output(self, output: str) -> List[str]:
        """Validate that rendered output contains required sections.

        Args:
            output: Rendered template output to validate

        Returns:
            List of missing required sections (empty if all present)
        """
        missing = []

        for section in self.schema.required_sections:
            if section not in output:
                missing.append(section)

        return missing


class TemplateRegistry:
    """Registry of all available templates"""

    def __init__(self, templates_dir: Path = Path("./templates")):
        """Initialize registry and load templates.

        Args:
            templates_dir: Directory containing template YAML files (relative paths resolved against repo root)
        """
        # Resolve relative paths against repo root (not CWD)
        if not templates_dir.is_absolute():
            try:
                repo_root = get_repo_root()
                templates_dir = repo_root / templates_dir
            except FileNotFoundError:
                # Fallback to CWD if repo root not found (for backwards compatibility)
                templates_dir = Path.cwd() / templates_dir

        self.templates_dir = templates_dir
        self.templates: Dict[str, Template] = {}
        self.templates_by_type: Dict[TemplateType, List[Template]] = {
            t: [] for t in TemplateType
        }
        self._template_cache: Dict[str, Template] = {}

        # Load all templates
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load and validate all templates from directory"""
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {self.templates_dir}")
        
        # Find all *_templates.yaml files
        template_files = list(self.templates_dir.glob("*_templates.yaml"))
        
        if not template_files:
            raise ValueError(f"No template files found in {self.templates_dir}")
        
        for template_file in template_files:
            self._load_template_file(template_file)
        
        print(f"OK Loaded {len(self.templates)} templates from {len(template_files)} files")
    
    def _load_template_file(self, file_path: Path) -> None:
        """Load templates from a single YAML file.
        
        Args:
            file_path: Path to template YAML file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ Failed to parse {file_path}: {e}")
            return
        
        if not data or 'templates' not in data:
            return  # Skip files without templates key
        
        for template_data in data['templates']:
            template = self._parse_template(template_data, file_path)
            if template:
                self._register_template(template)
    
    def _parse_template(self, data: Dict[str, Any], source_file: Path) -> Optional[Template]:
        """Parse template from YAML data.
        
        Args:
            data: Template data from YAML
            source_file: Source file for error messages
            
        Returns:
            Template instance or None if invalid
        """
        try:
            # Extract fields
            name = data.get('name')
            if not name:
                print(f"⚠️ Template in {source_file} missing name, skipping")
                return None
            
            # Parse type
            type_str = data.get('type', 'blog')
            try:
                template_type = TemplateType(type_str)
            except ValueError:
                print(f"⚠️ Unknown template type '{type_str}' for {name}, skipping")
                return None
            
            # Parse schema
            schema_data = data.get('schema', {})
            schema = TemplateSchema(
                required_placeholders=schema_data.get('required_placeholders', []),
                optional_placeholders=schema_data.get('optional_placeholders', []),
                required_sections=schema_data.get('required_sections', [])
            )
            
            # Get template content
            template_content = data.get('template', '')
            if not template_content:
                print(f"⚠️ Template {name} has no content, skipping")
                return None
            
            # Get metadata
            metadata = data.get('metadata', {})
            version = metadata.get('version', '1.0')
            
            # Create template
            template = Template(
                name=name,
                type=template_type,
                template_content=template_content,
                schema=schema,
                metadata=metadata,
                version=version
            )
            
            # Validate template
            errors = template.validate_template()
            if errors:
                print(f"⚠️ Template {name} validation failed:")
                for error in errors:
                    print(f"   - {error}")
                print(f"   Skipping template.")
                return None
            
            return template
            
        except Exception as e:
            print(f"⚠️ Error parsing template from {source_file}: {e}")
            return None
    
    def _register_template(self, template: Template) -> None:
        """Register a template.
        
        Args:
            template: Template to register
        """
        # Check for duplicates
        if template.name in self.templates:
            print(f"⚠️ Duplicate template name: {template.name}, overwriting")
        
        # Register
        self.templates[template.name] = template
        self.templates_by_type[template.type].append(template)
    
    def precompile_all(self) -> None:
        """Precompile all templates at startup.
        
        This ensures all templates are loaded and validated,
        improving runtime performance by avoiding lazy loading.
        """
        # Templates are already loaded in __init__, but this method
        # can be called explicitly to ensure all templates are ready
        for name, template in self.templates.items():
            # Store in cache (already in self.templates, but make it explicit)
            self._template_cache[name] = template
        
        print(f"OK Precompiled {len(self._template_cache)} templates")
    
    def get_template(self, name: str) -> Optional[Template]:
        """Get template by name.
        
        Args:
            name: Template name
            
        Returns:
            Template or None if not found
        """
        return self.templates.get(name)
    
    def list_templates(self, template_type: Optional[TemplateType] = None) -> List[Template]:
        """List all templates, optionally filtered by type.
        
        Args:
            template_type: Optional type filter
            
        Returns:
            List of templates
        """
        if template_type:
            return self.templates_by_type.get(template_type, [])
        return list(self.templates.values())
    
    def validate_all(self) -> Dict[str, List[str]]:
        """Validate all registered templates.
        
        Returns:
            Dict mapping template name to list of errors (empty if valid)
        """
        results = {}
        for name, template in self.templates.items():
            errors = template.validate_template()
            results[name] = errors
        return results
    
    def compile(self, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Compile a template with given context.
        
        Args:
            template_name: Name of template to compile
            context: Context data for compilation
            
        Returns:
            Compiled template result with workflow and metadata
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        # Get workflow if template has it
        workflow = []
        if hasattr(template, 'metadata') and isinstance(template.metadata, dict):
            workflow = template.metadata.get("workflow", [])
        
        # Build compiled result
        result = {
            "template_name": template_name,
            "template": template,
            "workflow": workflow,
            "context": context
        }
        
        return result


# Global registry instance
_registry_instance: Optional[TemplateRegistry] = None


def get_template_registry(templates_dir: Path = Path("./templates")) -> TemplateRegistry:
    """Get global template registry instance.
    
    Args:
        templates_dir: Directory containing templates
        
    Returns:
        TemplateRegistry instance
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = TemplateRegistry(templates_dir)
    return _registry_instance


def get_template(name: str) -> Optional[Template]:
    """Get a template by name from the global registry.
    
    Args:
        name: Template name
        
    Returns:
        Template or None if not found
    """
    registry = get_template_registry()
    return registry.get_template(name)


def list_templates(template_type: Optional[TemplateType] = None) -> List[Template]:
    """List all templates from the global registry.
    
    Args:
        template_type: Optional type filter
        
    Returns:
        List of templates
    """
    registry = get_template_registry()
    return registry.list_templates(template_type)


__all__ = [
    "Template",
    "TemplateSchema",
    "TemplateType",
    "TemplateRegistry",
    "get_template_registry",
    "get_template",
    "list_templates"
]
# DOCGEN:LLM-FIRST@v4