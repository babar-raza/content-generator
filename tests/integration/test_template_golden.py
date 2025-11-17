"""Template System Golden Tests - Verify template structure and rendering"""

import pytest
from pathlib import Path

from src.core.template_registry import (
    get_template_registry,
    TemplateRegistry,
    Template,
    TemplateType
)


class TestTemplateRegistry:
    """Test template registry loading and validation"""
    
    @pytest.fixture
    def registry(self):
        """Get template registry"""
        return get_template_registry()
    
    def test_registry_loads_templates(self, registry):
        """Test that registry loads templates from directory"""
        templates = registry.list_templates()
        assert len(templates) > 0, "No templates loaded"
    
    def test_all_templates_have_metadata(self, registry):
        """Test that all templates have required metadata"""
        for template in registry.list_templates():
            assert template.name, f"Template missing name"
            assert template.type, f"Template {template.name} missing type"
            assert template.version, f"Template {template.name} missing version"
            assert template.template_content, f"Template {template.name} missing content"
    
    def test_all_templates_validate(self, registry):
        """Test that all templates pass validation"""
        validation_results = registry.validate_all()
        
        failed_templates = {
            name: errors for name, errors in validation_results.items() if errors
        }
        
        if failed_templates:
            msg = "Templates failed validation:\n"
            for name, errors in failed_templates.items():
                msg += f"\n{name}:\n"
                msg += "\n".join(f"  - {e}" for e in errors)
            pytest.fail(msg)
    
    def test_templates_have_valid_schemas(self, registry):
        """Test that all templates have valid schemas"""
        for template in registry.list_templates():
            # Schema should define at least one required placeholder
            assert (
                len(template.schema.required_placeholders) > 0
            ), f"Template {template.name} has no required placeholders"
            
            # All placeholders in schema should be in template
            placeholders_in_template = template.extract_placeholders()
            for placeholder in template.schema.required_placeholders:
                assert placeholder in placeholders_in_template, (
                    f"Required placeholder '{placeholder}' not in template {template.name}"
                )
    
    def test_get_template_by_name(self, registry):
        """Test getting template by name"""
        templates = registry.list_templates()
        if templates:
            first_template = templates[0]
            retrieved = registry.get_template(first_template.name)
            assert retrieved is not None
            assert retrieved.name == first_template.name
    
    def test_list_templates_by_type(self, registry):
        """Test listing templates filtered by type"""
        blog_templates = registry.list_templates(TemplateType.BLOG)
        code_templates = registry.list_templates(TemplateType.CODE)
        
        # All blog templates should have blog type
        for template in blog_templates:
            assert template.type == TemplateType.BLOG
        
        # All code templates should have code type
        for template in code_templates:
            assert template.type == TemplateType.CODE


class TestTemplateRendering:
    """Test template rendering with data"""
    
    @pytest.fixture
    def registry(self):
        """Get template registry"""
        return get_template_registry()
    
    def test_template_renders_with_valid_data(self, registry):
        """Test that template renders successfully with valid data"""
        # Get a template (use first blog template)
        blog_templates = registry.list_templates(TemplateType.BLOG)
        if not blog_templates:
            pytest.skip("No blog templates available")
        
        template = blog_templates[0]
        
        # Create valid data for all required placeholders
        data = {
            placeholder: f"Test {placeholder}"
            for placeholder in template.schema.required_placeholders
        }
        
        # Render should succeed
        result = template.render(data, strict=True)
        assert result
        assert len(result) > 0
        
        # All required placeholders should be replaced
        for placeholder in template.schema.required_placeholders:
            assert f"{{{{{placeholder}}}}}" not in result, (
                f"Placeholder {placeholder} not replaced in rendered output"
            )
    
    def test_template_fails_with_missing_required(self, registry):
        """Test that template fails when required placeholder missing"""
        blog_templates = registry.list_templates(TemplateType.BLOG)
        if not blog_templates:
            pytest.skip("No blog templates available")
        
        template = blog_templates[0]
        
        # Provide incomplete data (missing required)
        if template.schema.required_placeholders:
            incomplete_data = {
                template.schema.required_placeholders[0]: "Test"
                # Missing other required placeholders
            }
            
            # Render should fail in strict mode
            with pytest.raises(ValueError, match="Missing required placeholder"):
                template.render(incomplete_data, strict=True)
    
    def test_template_fails_with_unknown_placeholder(self, registry):
        """Test that template fails when unknown placeholder provided"""
        blog_templates = registry.list_templates(TemplateType.BLOG)
        if not blog_templates:
            pytest.skip("No blog templates available")
        
        template = blog_templates[0]
        
        # Create data with unknown placeholder
        data = {
            placeholder: f"Test {placeholder}"
            for placeholder in template.schema.required_placeholders
        }
        data["unknown_placeholder"] = "This should fail"
        
        # Render should fail in strict mode
        with pytest.raises(ValueError, match="Unknown placeholder"):
            template.render(data, strict=True)
    
    def test_optional_placeholders_can_be_omitted(self, registry):
        """Test that optional placeholders can be omitted"""
        blog_templates = registry.list_templates(TemplateType.BLOG)
        if not blog_templates:
            pytest.skip("No blog templates available")
        
        template = blog_templates[0]
        
        # Only provide required placeholders
        data = {
            placeholder: f"Test {placeholder}"
            for placeholder in template.schema.required_placeholders
        }
        
        # Render should succeed
        result = template.render(data, strict=True)
        assert result
        
        # Optional placeholders should be removed from output
        for placeholder in template.schema.optional_placeholders:
            # Placeholder lines should be removed
            assert f"{{{{{placeholder}}}}}" not in result


class TestGoldenSnapshots:
    """Golden tests - verify template output structure"""
    
    @pytest.fixture
    def registry(self):
        """Get template registry"""
        return get_template_registry()
    
    def test_default_blog_template_structure(self, registry):
        """Test default_blog template has expected structure"""
        template = registry.get_template("default_blog")
        if not template:
            pytest.skip("default_blog template not found")
        
        # Should have these required sections
        expected_sections = [
            "## Introduction",
            "## Conclusion"
        ]
        
        for section in expected_sections:
            assert section in template.template_content, (
                f"Expected section '{section}' not found in default_blog template"
            )
        
        # Should have topic placeholder
        assert 'topic' in template.schema.required_placeholders
    
    def test_code_template_structure(self, registry):
        """Test code templates have expected structure"""
        code_templates = registry.list_templates(TemplateType.CODE)
        
        if not code_templates:
            pytest.skip("No code templates available")
        
        for template in code_templates:
            # Code templates should have meaningful placeholders
            placeholders = template.extract_placeholders()
            
            # Should have at least one placeholder
            assert len(placeholders) > 0, (
                f"Code template {template.name} has no placeholders"
            )
    
    def test_template_output_layout_consistency(self, registry):
        """Test that switching templates changes layout only, not core content"""
        blog_templates = registry.list_templates(TemplateType.BLOG)
        
        if len(blog_templates) < 2:
            pytest.skip("Need at least 2 blog templates for comparison")
        
        # Create common data
        common_data = {
            "topic": "Test Topic",
            "introduction": "Test intro",
            "content": "Test content",
            "conclusion": "Test conclusion"
        }
        
        # Render with different templates
        renders = []
        for template in blog_templates[:2]:
            # Add required placeholders for this template
            data = common_data.copy()
            for placeholder in template.schema.required_placeholders:
                if placeholder not in data:
                    data[placeholder] = f"Test {placeholder}"
            
            try:
                result = template.render(data, strict=False)  # Non-strict for flexibility
                renders.append((template.name, result))
            except Exception as e:
                # Template might need different data, skip
                continue
        
        if len(renders) >= 2:
            # Core content should be present in both (topic and conclusion are common)
            for _, rendered in renders:
                assert "Test Topic" in rendered or "test topic" in rendered
                assert "Test conclusion" in rendered or "test conclusion" in rendered


class TestTemplateSchemaValidation:
    """Test that template schema validation works correctly"""
    
    def test_schema_validates_required_placeholders(self):
        """Test that schema validates required placeholders"""
        from src.core.template_registry import TemplateSchema
        
        schema = TemplateSchema(
            required_placeholders=["topic", "content"],
            optional_placeholders=["extra"]
        )
        
        # Valid data
        valid_data = {"topic": "Test", "content": "Content"}
        errors = schema.validate_data(valid_data)
        assert len(errors) == 0
        
        # Missing required
        invalid_data = {"topic": "Test"}  # missing content
        errors = schema.validate_data(invalid_data)
        assert len(errors) > 0
        assert any("content" in e.lower() for e in errors)
    
    def test_schema_rejects_unknown_placeholders(self):
        """Test that schema rejects unknown placeholders"""
        from src.core.template_registry import TemplateSchema
        
        schema = TemplateSchema(
            required_placeholders=["topic"],
            optional_placeholders=[]
        )
        
        # Data with unknown placeholder
        data = {"topic": "Test", "unknown": "Should fail"}
        errors = schema.validate_data(data)
        
        assert len(errors) > 0
        assert any("unknown" in e.lower() for e in errors)
# DOCGEN:LLM-FIRST@v4