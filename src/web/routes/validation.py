"""Content validation API routes."""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/validate", tags=["validation"])


# Models
class ValidationRule(BaseModel):
    """Validation rule definition."""
    rule_id: str
    description: str
    severity: str = "error"  # error, warning, info


class ValidationError(BaseModel):
    """Validation error."""
    line: Optional[int] = None
    column: Optional[int] = None
    message: str
    severity: str
    rule_id: Optional[str] = None


class ValidationRequest(BaseModel):
    """Content validation request."""
    content: str = Field(..., description="Content to validate")
    content_type: str = Field(default="markdown", description="Content type (markdown, html, yaml, json)")
    rules: Optional[List[str]] = Field(default=None, description="Specific rules to apply")
    strict: bool = Field(default=False, description="Strict validation mode")


class ValidationResponse(BaseModel):
    """Validation response."""
    valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationError] = Field(default_factory=list)
    info: List[ValidationError] = Field(default_factory=list)
    total_issues: int
    content_type: str
    timestamp: str


class BatchValidationRequest(BaseModel):
    """Batch validation request."""
    items: List[ValidationRequest]


class BatchValidationResponse(BaseModel):
    """Batch validation response."""
    results: List[ValidationResponse]
    total: int
    valid_count: int
    invalid_count: int


def validate_markdown(content: str, strict: bool = False) -> List[ValidationError]:
    """Validate markdown content.
    
    Args:
        content: Markdown content to validate
        strict: Whether to apply strict validation
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Basic markdown validation rules
    lines = content.split('\n')
    
    # Check for empty content
    if not content.strip():
        errors.append(ValidationError(
            line=1,
            message="Content is empty",
            severity="error",
            rule_id="MD001"
        ))
        return errors
    
    # Check heading hierarchy
    prev_heading_level = 0
    for i, line in enumerate(lines, 1):
        if line.startswith('#'):
            heading_level = len(line) - len(line.lstrip('#'))
            if heading_level > prev_heading_level + 1 and prev_heading_level > 0:
                errors.append(ValidationError(
                    line=i,
                    message=f"Heading level skipped from h{prev_heading_level} to h{heading_level}",
                    severity="warning",
                    rule_id="MD001"
                ))
            prev_heading_level = heading_level
    
    # Check for trailing whitespace
    for i, line in enumerate(lines, 1):
        if line.endswith(' ') or line.endswith('\t'):
            errors.append(ValidationError(
                line=i,
                message="Trailing whitespace detected",
                severity="warning" if not strict else "error",
                rule_id="MD009"
            ))
    
    # Check for multiple consecutive blank lines
    blank_count = 0
    for i, line in enumerate(lines, 1):
        if not line.strip():
            blank_count += 1
            if blank_count > 2:
                errors.append(ValidationError(
                    line=i,
                    message="Multiple consecutive blank lines",
                    severity="warning",
                    rule_id="MD012"
                ))
        else:
            blank_count = 0
    
    return errors


def validate_yaml(content: str, strict: bool = False) -> List[ValidationError]:
    """Validate YAML content.
    
    Args:
        content: YAML content to validate
        strict: Whether to apply strict validation
        
    Returns:
        List of validation errors
    """
    import yaml
    errors = []
    
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        errors.append(ValidationError(
            line=getattr(e, 'problem_mark', None) and e.problem_mark.line + 1,
            column=getattr(e, 'problem_mark', None) and e.problem_mark.column + 1,
            message=str(e),
            severity="error",
            rule_id="YAML001"
        ))
    
    return errors


def validate_json(content: str, strict: bool = False) -> List[ValidationError]:
    """Validate JSON content.
    
    Args:
        content: JSON content to validate
        strict: Whether to apply strict validation
        
    Returns:
        List of validation errors
    """
    import json
    errors = []
    
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        errors.append(ValidationError(
            line=e.lineno,
            column=e.colno,
            message=e.msg,
            severity="error",
            rule_id="JSON001"
        ))
    
    return errors


@router.post("", response_model=ValidationResponse)
async def validate_content_endpoint(request: ValidationRequest):
    """Validate content (mirrors cmd_validate).
    
    Args:
        request: Validation request with content and rules
        
    Returns:
        ValidationResponse with validation results
    """
    try:
        from datetime import datetime, timezone
        
        all_errors = []
        
        # Validate based on content type
        if request.content_type == "markdown":
            all_errors = validate_markdown(request.content, request.strict)
        elif request.content_type == "yaml":
            all_errors = validate_yaml(request.content, request.strict)
        elif request.content_type == "json":
            all_errors = validate_json(request.content, request.strict)
        elif request.content_type == "html":
            # Basic HTML validation
            if not request.content.strip():
                all_errors.append(ValidationError(
                    message="Content is empty",
                    severity="error",
                    rule_id="HTML001"
                ))
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported content type: {request.content_type}"
            )
        
        # Separate by severity
        errors = [e for e in all_errors if e.severity == "error"]
        warnings = [e for e in all_errors if e.severity == "warning"]
        info = [e for e in all_errors if e.severity == "info"]
        
        return ValidationResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info,
            total_issues=len(all_errors),
            content_type=request.content_type,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate content: {str(e)}")


@router.post("/file")
async def validate_file(
    file: UploadFile = File(...),
    content_type: Optional[str] = Form(None),
    strict: bool = Form(False)
):
    """Validate uploaded file.
    
    Args:
        file: File to validate
        content_type: Optional content type override
        strict: Whether to apply strict validation
        
    Returns:
        ValidationResponse with validation results
    """
    try:
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # Detect content type from filename if not provided
        if not content_type:
            filename = file.filename.lower()
            if filename.endswith('.md'):
                content_type = "markdown"
            elif filename.endswith('.yaml') or filename.endswith('.yml'):
                content_type = "yaml"
            elif filename.endswith('.json'):
                content_type = "json"
            elif filename.endswith('.html') or filename.endswith('.htm'):
                content_type = "html"
            else:
                content_type = "markdown"  # default
        
        # Create validation request
        request = ValidationRequest(
            content=content_str,
            content_type=content_type,
            strict=strict
        )
        
        return await validate_content_endpoint(request)
        
    except Exception as e:
        logger.error(f"Error validating file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate file: {str(e)}")


@router.post("/batch", response_model=BatchValidationResponse)
async def validate_batch(request: BatchValidationRequest):
    """Validate multiple content items.
    
    Args:
        request: Batch validation request
        
    Returns:
        BatchValidationResponse with all validation results
    """
    try:
        results = []
        valid_count = 0
        
        for item in request.items:
            result = await validate_content_endpoint(item)
            results.append(result)
            if result.valid:
                valid_count += 1
        
        return BatchValidationResponse(
            results=results,
            total=len(results),
            valid_count=valid_count,
            invalid_count=len(results) - valid_count
        )
        
    except Exception as e:
        logger.error(f"Error in batch validation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate batch: {str(e)}")
