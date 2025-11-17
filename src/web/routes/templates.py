"""Template management API routes."""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])


# Models
class TemplateInfo(BaseModel):
    """Template information."""
    name: str
    type: str
    description: Optional[str] = None
    version: str = "1.0"
    required_placeholders: List[str] = Field(default_factory=list)
    optional_placeholders: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TemplateListResponse(BaseModel):
    """Response for template list."""
    templates: List[TemplateInfo]
    total: int
    categories: List[str]


class TemplateDetailResponse(BaseModel):
    """Detailed template response."""
    name: str
    type: str
    content: str
    description: Optional[str] = None
    version: str
    schema: Dict[str, Any]
    metadata: Dict[str, Any]


@router.get("", response_model=TemplateListResponse)
async def list_all_templates():
    """List all available templates (mirrors cmd_list_templates).
    
    Returns:
        TemplateListResponse with all templates
    """
    try:
        from src.core.template_registry import TemplateRegistry
        
        # Initialize template registry
        registry = TemplateRegistry()
        
        # Load templates from the templates directory
        templates_dir = Path("./templates")
        if templates_dir.exists():
            try:
                registry.load_from_directory(templates_dir)
            except Exception as e:
                logger.warning(f"Failed to load templates from directory: {e}")
        
        # Get all templates
        templates = []
        categories = set()
        
        for template_name, template in registry.templates.items():
            # Get category from metadata or type
            category = template.metadata.get("category", template.type.value)
            categories.add(category)
            
            templates.append(TemplateInfo(
                name=template.name,
                type=template.type.value,
                description=template.metadata.get("description"),
                version=template.version,
                required_placeholders=template.schema.required_placeholders,
                optional_placeholders=template.schema.optional_placeholders,
                metadata=template.metadata
            ))
        
        return TemplateListResponse(
            templates=templates,
            total=len(templates),
            categories=sorted(list(categories))
        )
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template_details(template_id: str):
    """Get template details.
    
    Args:
        template_id: Template identifier
        
    Returns:
        TemplateDetailResponse with full template information
    """
    try:
        from src.core.template_registry import TemplateRegistry
        
        # Initialize template registry
        registry = TemplateRegistry()
        
        # Load templates from the templates directory
        templates_dir = Path("./templates")
        if templates_dir.exists():
            try:
                registry.load_from_directory(templates_dir)
            except Exception as e:
                logger.warning(f"Failed to load templates from directory: {e}")
        
        # Get specific template
        template = registry.get(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
        
        return TemplateDetailResponse(
            name=template.name,
            type=template.type.value,
            content=template.template_content,
            description=template.metadata.get("description"),
            version=template.version,
            schema={
                "required_placeholders": template.schema.required_placeholders,
                "optional_placeholders": template.schema.optional_placeholders,
                "required_sections": template.schema.required_sections
            },
            metadata=template.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get template: {str(e)}")


@router.get("/categories/{category}", response_model=TemplateListResponse)
async def list_templates_by_category(category: str):
    """List templates by category.
    
    Args:
        category: Template category
        
    Returns:
        TemplateListResponse filtered by category
    """
    try:
        from src.core.template_registry import TemplateRegistry
        
        # Initialize template registry
        registry = TemplateRegistry()
        
        # Load templates from the templates directory
        templates_dir = Path("./templates")
        if templates_dir.exists():
            try:
                registry.load_from_directory(templates_dir)
            except Exception as e:
                logger.warning(f"Failed to load templates from directory: {e}")
        
        # Filter templates by category
        templates = []
        categories = set()
        
        for template_name, template in registry.templates.items():
            template_category = template.metadata.get("category", template.type.value)
            categories.add(template_category)
            
            if template_category.lower() == category.lower():
                templates.append(TemplateInfo(
                    name=template.name,
                    type=template.type.value,
                    description=template.metadata.get("description"),
                    version=template.version,
                    required_placeholders=template.schema.required_placeholders,
                    optional_placeholders=template.schema.optional_placeholders,
                    metadata=template.metadata
                ))
        
        return TemplateListResponse(
            templates=templates,
            total=len(templates),
            categories=sorted(list(categories))
        )
        
    except Exception as e:
        logger.error(f"Error listing templates for category {category}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")
