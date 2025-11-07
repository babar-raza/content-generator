"""Completeness gate to prevent empty/trivial outputs."""

import re
import yaml
from typing import Dict, List, Tuple, Optional, Set
import logging

from .exceptions import EmptyOutputError

logger = logging.getLogger(__name__)


class CompletenessGate:
    """Validates output is not empty before completion."""
    
    MIN_WORD_COUNT = 100
    MIN_SECTION_COUNT = 3
    MIN_LENGTH = 500
    MIN_CODE_BLOCKS = 1
    
    REQUIRED_FRONTMATTER_KEYS = {
        'title', 'slug', 'date', 'description', 'keywords', 'tags', 
        'summary', 'canonical', 'og:title', 'og:description'
    }
    
    PLACEHOLDERS = [
        "TODO", "TBD", "[Insert", "Lorem ipsum",
        "[Your content here]", "[Add content]",
        "Coming soon", "Under construction"
    ]
    
    def _extract_frontmatter(self, content: str) -> Optional[Dict]:
        """Extract YAML frontmatter from content.
        
        Args:
            content: Markdown content
            
        Returns:
            Parsed frontmatter dict or None
        """
        if not content.strip().startswith('---'):
            return None
        
        # Find frontmatter block
        parts = content.split('---', 2)
        if len(parts) < 3:
            return None
        
        frontmatter_text = parts[1].strip()
        
        try:
            return yaml.safe_load(frontmatter_text)
        except yaml.YAMLError:
            return None
    
    def _validate_frontmatter(self, content: str) -> List[str]:
        """Validate frontmatter has required SEO keys.
        
        Args:
            content: Markdown content
            
        Returns:
            List of errors (empty if valid)
        """
        errors = []
        
        frontmatter = self._extract_frontmatter(content)
        
        if not frontmatter:
            errors.append("Missing YAML frontmatter block")
            return errors
        
        # Check required keys
        missing_keys = self.REQUIRED_FRONTMATTER_KEYS - set(frontmatter.keys())
        if missing_keys:
            errors.append(f"Missing frontmatter keys: {', '.join(sorted(missing_keys))}")
        
        # Check keys are non-empty
        empty_keys = [k for k in self.REQUIRED_FRONTMATTER_KEYS 
                      if k in frontmatter and not str(frontmatter[k]).strip()]
        if empty_keys:
            errors.append(f"Empty frontmatter values: {', '.join(sorted(empty_keys))}")
        
        return errors
    
    def _validate_sections(self, content: str, required_sections: Optional[List[str]] = None) -> List[str]:
        """Validate body has required sections.
        
        Args:
            content: Markdown content
            required_sections: Optional list of required section names
            
        Returns:
            List of errors (empty if valid)
        """
        errors = []
        
        # Extract body (after frontmatter)
        if content.strip().startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                body = parts[2]
            else:
                body = content
        else:
            body = content
        
        # Count sections
        section_count = body.count('\n## ')
        if section_count < self.MIN_SECTION_COUNT:
            errors.append(
                f"Too few sections: {section_count} (minimum: {self.MIN_SECTION_COUNT})"
            )
        
        # Check for code blocks
        code_block_count = body.count('```')
        if code_block_count < self.MIN_CODE_BLOCKS:
            errors.append(
                f"Missing code blocks: {code_block_count} (minimum: {self.MIN_CODE_BLOCKS})"
            )
        
        # If specific sections required, check them
        if required_sections:
            body_lower = body.lower()
            for section in required_sections:
                if section.lower() not in body_lower:
                    errors.append(f"Missing required section: {section}")
        
        return errors
    
    def validate(self, content: str, metadata: Dict = None, template_spec: Dict = None) -> Tuple[bool, List[str]]:
        """Validate content is not empty.
        
        Args:
            content: Content to validate
            metadata: Optional metadata
            template_spec: Optional template specification with required sections
            
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check existence
        if not content:
            errors.append("Content is completely empty")
            return False, errors
        
        # Check minimum length
        if len(content.strip()) < self.MIN_LENGTH:
            errors.append(
                f"Content too short: {len(content)} characters "
                f"(minimum: {self.MIN_LENGTH})"
            )
        
        # Check word count
        word_count = len(content.split())
        if word_count < self.MIN_WORD_COUNT:
            errors.append(
                f"Content too short: {word_count} words "
                f"(minimum: {self.MIN_WORD_COUNT})"
            )
        
        # Validate frontmatter
        fm_errors = self._validate_frontmatter(content)
        errors.extend(fm_errors)
        
        # Validate sections
        required_sections = None
        if template_spec and 'required_sections' in template_spec:
            required_sections = template_spec['required_sections']
        section_errors = self._validate_sections(content, required_sections)
        errors.extend(section_errors)
        
        # Check for placeholder text
        found_placeholders = [p for p in self.PLACEHOLDERS if p in content]
        if found_placeholders:
            errors.append(
                f"Found placeholder text: {', '.join(found_placeholders)}"
            )
        
        # Check for actual content (not just formatting)
        text_only = re.sub(r'[#*\-_`\[\](){}]', '', content)
        text_only = re.sub(r'\s+', ' ', text_only).strip()
        if len(text_only) < 200:
            errors.append("Content appears to be mostly formatting with little actual text")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"Completeness validation failed with {len(errors)} errors")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return is_valid, errors
    
    def attach_diagnostics(self, content: str) -> Dict:
        """Generate diagnostics for debugging."""
        lines = content.split('\n')
        
        frontmatter = self._extract_frontmatter(content)
        
        diagnostics = {
            "total_length": len(content),
            "word_count": len(content.split()),
            "line_count": len(lines),
            "non_empty_lines": len([l for l in lines if l.strip()]),
            "section_count": content.count('\n## '),
            "heading_count": len(re.findall(r'^#+\s', content, re.MULTILINE)),
            "has_frontmatter": content.strip().startswith('---'),
            "frontmatter_keys": list(frontmatter.keys()) if frontmatter else [],
            "has_headings": bool(re.search(r'^#+\s', content, re.MULTILINE)),
            "code_blocks": content.count('```'),
            "links": len(re.findall(r'\[.*?\]\(.*?\)', content)),
            "first_100_chars": content[:100],
            "last_100_chars": content[-100:] if len(content) > 100 else content
        }
        
        return diagnostics
    
    def fail_if_empty(self, content: str, metadata: Dict = None, template_spec: Dict = None):
        """Raise exception if content is empty/trivial.
        
        Args:
            content: Content to validate
            metadata: Optional metadata
            template_spec: Optional template specification
            
        Raises:
            EmptyOutputError: If validation fails
        """
        is_valid, errors = self.validate(content, metadata, template_spec)
        
        if not is_valid:
            diagnostics = self.attach_diagnostics(content)
            
            error_msg = "Output failed completeness validation:\n"
            error_msg += "\n".join(f"  - {e}" for e in errors)
            error_msg += f"\n\nDiagnostics:\n"
            for key, value in diagnostics.items():
                error_msg += f"  {key}: {value}\n"
            
            raise EmptyOutputError(error_msg)
        
        logger.info(f"✓ Content passed completeness gate: {len(content)} chars, {len(content.split())} words")

