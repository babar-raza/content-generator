"""ValidationAgent - Performs comprehensive content quality validation checks.

This agent validates content against configurable quality rules including:
- Content length requirements
- Keyword density analysis
- Code syntax validation
- Link validity checks
- Frontmatter completeness
- SEO requirements
"""

from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
import logging
import re
import yaml
from urllib.parse import urlparse
import requests

from ..base import (
    Agent, EventBus, AgentEvent, AgentContract,
    Config, validate_code_quality, extract_code_blocks, logger
)


class ValidationAgent(Agent):
    """Performs content quality validation checks.
    
    Validates content against configurable rules for:
    - Content length (min/max words)
    - Keyword density (target range)
    - Code syntax (if code present)
    - Link validity (no 404s)
    - Frontmatter completeness
    - SEO requirements
    
    Returns detailed validation results with pass/fail for each check.
    """

    def __init__(self, config: Config, event_bus: EventBus):
        """Initialize ValidationAgent.
        
        Args:
            config: System configuration object
            event_bus: EventBus instance for communication
        """
        self.validation_config = self._load_validation_config()
        Agent.__init__(self, "ValidationAgent", config, event_bus)
        logger.info("ValidationAgent initialized with config: %s", 
                   list(self.validation_config.keys()))

    def _load_validation_config(self) -> Dict[str, Any]:
        """Load validation configuration from yaml file.
        
        Returns:
            Dict containing validation rules
        """
        config_path = Path(__file__).parents[3] / "config" / "validation.yaml"
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    logger.info("Loaded validation config from %s", config_path)
                    return config_data
            else:
                logger.warning("Validation config not found at %s, using defaults", config_path)
                return self._get_default_config()
        except Exception as e:
            logger.error("Error loading validation config: %s, using defaults", e)
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default validation configuration.
        
        Returns:
            Dict with default validation rules
        """
        return {
            'content_validation': {
                'length': {'min_words': 300, 'max_words': 3000, 'strict': False},
                'keyword_density': {'min_density': 0.01, 'max_density': 0.05, 'strict': True},
                'code_syntax': {'enabled': True, 'strict': True},
                'link_validation': {'enabled': True, 'check_404': True, 'timeout': 5, 'strict': False},
                'frontmatter': {'required_fields': ['title', 'description'], 'strict': True},
                'seo': {
                    'title': {'min_length': 30, 'max_length': 60, 'strict': True},
                    'description': {'min_length': 120, 'max_length': 160, 'strict': True}
                }
            }
        }

    def _create_contract(self) -> AgentContract:
        """Create agent contract defining capabilities.
        
        Returns:
            AgentContract with validation capabilities
        """
        return AgentContract(
            agent_id="ValidationAgent",
            capabilities=["validate_content"],
            input_schema={
                "type": "object",
                "required": ["content"],
                "properties": {
                    "content": {"type": "string"},
                    "code": {"type": "string"},
                    "frontmatter": {"type": "object"},
                    "keywords": {"type": "array"}
                }
            },
            output_schema={
                "type": "object",
                "required": ["checks"],
                "properties": {
                    "checks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "passed": {"type": "boolean"},
                                "message": {"type": "string"},
                                "severity": {"type": "string"},
                                "details": {"type": "object"}
                            }
                        }
                    },
                    "summary": {
                        "type": "object",
                        "properties": {
                            "total_checks": {"type": "integer"},
                            "passed": {"type": "integer"},
                            "failed": {"type": "integer"},
                            "warnings": {"type": "integer"}
                        }
                    }
                }
            },
            publishes=["validation_complete"]
        )

    def _subscribe_to_events(self):
        """Set up event subscriptions."""
        self.event_bus.subscribe("validate_request", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:
        """Execute validation checks on content.
        
        Args:
            event: AgentEvent with content to validate
            
        Returns:
            AgentEvent with validation results
            
        Raises:
            ValueError: If required data is missing
        """
        content = event.data.get("content", "")
        code = event.data.get("code", "")
        frontmatter = event.data.get("frontmatter", {})
        keywords = event.data.get("keywords", [])
        
        if not content:
            raise ValueError("content is required but was missing or empty")
        
        # Run all validation checks
        checks = []
        
        # Content length validation
        length_check = self._validate_content_length(content)
        checks.append(length_check)
        
        # Keyword density validation
        if keywords:
            keyword_check = self._validate_keyword_density(content, keywords)
            checks.append(keyword_check)
        
        # Code syntax validation
        if code or self._extract_code_from_content(content):
            code_to_validate = code or self._extract_code_from_content(content)
            code_check = self._validate_code_syntax(code_to_validate)
            checks.append(code_check)
        
        # Link validation
        links = self._extract_links(content)
        if links:
            link_check = self._validate_links(links)
            checks.append(link_check)
        
        # Frontmatter validation
        if frontmatter or self._extract_frontmatter(content):
            fm = frontmatter or self._extract_frontmatter(content)
            frontmatter_check = self._validate_frontmatter(fm)
            checks.append(frontmatter_check)
            
            # SEO validation (depends on frontmatter)
            seo_checks = self._validate_seo(fm)
            checks.extend(seo_checks)
        
        # Calculate summary
        summary = {
            'total_checks': len(checks),
            'passed': sum(1 for c in checks if c['passed']),
            'failed': sum(1 for c in checks if not c['passed'] and c.get('severity') in ['critical', 'high']),
            'warnings': sum(1 for c in checks if not c['passed'] and c.get('severity') in ['medium', 'low'])
        }
        
        validation_results = {
            'checks': checks,
            'summary': summary
        }
        
        logger.info("Validation complete: %d checks, %d passed, %d failed, %d warnings",
                   summary['total_checks'], summary['passed'], summary['failed'], summary['warnings'])
        
        return AgentEvent(
            event_type="validation_complete",
            data=validation_results,
            source_agent=self.agent_id,
            correlation_id=event.correlation_id
        )

    def _validate_content_length(self, content: str) -> Dict[str, Any]:
        """Validate content length against configured limits.
        
        Args:
            content: Content text to validate
            
        Returns:
            Dict with check result
        """
        config = self.validation_config.get('content_validation', {}).get('length', {})
        min_words = config.get('min_words', 300)
        max_words = config.get('max_words', 3000)
        strict = config.get('strict', False)
        
        word_count = len(content.split())
        passed = min_words <= word_count <= max_words
        
        if passed:
            message = f"Content length valid: {word_count} words (range: {min_words}-{max_words})"
        else:
            if word_count < min_words:
                message = f"Content too short: {word_count} words (minimum: {min_words})"
            else:
                message = f"Content too long: {word_count} words (maximum: {max_words})"
        
        return {
            'name': 'content_length',
            'passed': passed,
            'message': message,
            'severity': 'high' if strict else 'medium',
            'details': {
                'word_count': word_count,
                'min_words': min_words,
                'max_words': max_words
            }
        }

    def _validate_keyword_density(self, content: str, keywords: List[str]) -> Dict[str, Any]:
        """Validate keyword density in content.
        
        Args:
            content: Content text to validate
            keywords: List of keywords to check
            
        Returns:
            Dict with check result
        """
        config = self.validation_config.get('content_validation', {}).get('keyword_density', {})
        min_density = config.get('min_density', 0.01)
        max_density = config.get('max_density', 0.05)
        strict = config.get('strict', True)
        
        total_words = len(content.split())
        content_lower = content.lower()
        
        keyword_counts = {}
        total_keyword_count = 0
        
        for keyword in keywords:
            count = content_lower.count(keyword.lower())
            keyword_counts[keyword] = count
            total_keyword_count += count
        
        density = total_keyword_count / total_words if total_words > 0 else 0
        passed = min_density <= density <= max_density
        
        if passed:
            message = f"Keyword density valid: {density:.2%} (range: {min_density:.2%}-{max_density:.2%})"
        else:
            if density < min_density:
                message = f"Keyword density too low: {density:.2%} (minimum: {min_density:.2%})"
            else:
                message = f"Keyword density too high: {density:.2%} (maximum: {max_density:.2%})"
        
        return {
            'name': 'keyword_density',
            'passed': passed,
            'message': message,
            'severity': 'high' if strict else 'medium',
            'details': {
                'density': density,
                'keyword_counts': keyword_counts,
                'total_keywords': total_keyword_count,
                'total_words': total_words
            }
        }

    def _validate_code_syntax(self, code: str) -> Dict[str, Any]:
        """Validate code syntax.
        
        Args:
            code: Code to validate
            
        Returns:
            Dict with check result
        """
        config = self.validation_config.get('content_validation', {}).get('code_syntax', {})
        strict = config.get('strict', True)
        
        try:
            is_valid, issues = validate_code_quality(code, level="moderate")
            
            if is_valid:
                message = "Code syntax valid"
                passed = True
            else:
                message = f"Code syntax issues found: {len(issues)} issues"
                passed = False
            
            return {
                'name': 'code_syntax',
                'passed': passed,
                'message': message,
                'severity': 'critical' if strict else 'high',
                'details': {
                    'is_valid': is_valid,
                    'issues': issues[:5] if issues else []  # Limit to first 5 issues
                }
            }
        except Exception as e:
            logger.error("Code validation error: %s", e)
            return {
                'name': 'code_syntax',
                'passed': False,
                'message': f"Code validation failed: {str(e)}",
                'severity': 'critical' if strict else 'high',
                'details': {'error': str(e)}
            }

    def _validate_links(self, links: List[str]) -> Dict[str, Any]:
        """Validate links in content.
        
        Args:
            links: List of URLs to validate
            
        Returns:
            Dict with check result
        """
        config = self.validation_config.get('content_validation', {}).get('link_validation', {})
        check_404 = config.get('check_404', True)
        timeout = config.get('timeout', 5)
        max_links = config.get('max_links_to_check', 50)
        strict = config.get('strict', False)
        
        if not check_404:
            return {
                'name': 'link_validation',
                'passed': True,
                'message': "Link validation disabled",
                'severity': 'low',
                'details': {'links_found': len(links)}
            }
        
        broken_links = []
        valid_links = []
        links_to_check = links[:max_links]
        
        for link in links_to_check:
            try:
                response = requests.head(link, timeout=timeout, allow_redirects=True)
                if response.status_code >= 400:
                    broken_links.append({'url': link, 'status': response.status_code})
                else:
                    valid_links.append(link)
            except Exception as e:
                logger.debug("Link check failed for %s: %s", link, e)
                broken_links.append({'url': link, 'error': str(e)})
        
        passed = len(broken_links) == 0
        
        if passed:
            message = f"All links valid: {len(valid_links)} links checked"
        else:
            message = f"Broken links found: {len(broken_links)} of {len(links_to_check)} links"
        
        return {
            'name': 'link_validation',
            'passed': passed,
            'message': message,
            'severity': 'medium' if strict else 'low',
            'details': {
                'total_links': len(links),
                'checked_links': len(links_to_check),
                'valid_links': len(valid_links),
                'broken_links': broken_links[:10]  # Limit to first 10
            }
        }

    def _validate_frontmatter(self, frontmatter: Dict[str, Any]) -> Dict[str, Any]:
        """Validate frontmatter completeness.
        
        Args:
            frontmatter: Frontmatter dictionary
            
        Returns:
            Dict with check result
        """
        config = self.validation_config.get('content_validation', {}).get('frontmatter', {})
        required_fields = config.get('required_fields', ['title', 'description'])
        strict = config.get('strict', True)
        
        missing_fields = [field for field in required_fields if field not in frontmatter or not frontmatter[field]]
        passed = len(missing_fields) == 0
        
        if passed:
            message = f"Frontmatter complete: all {len(required_fields)} required fields present"
        else:
            message = f"Frontmatter incomplete: missing {len(missing_fields)} fields: {', '.join(missing_fields)}"
        
        return {
            'name': 'frontmatter',
            'passed': passed,
            'message': message,
            'severity': 'critical' if strict else 'high',
            'details': {
                'required_fields': required_fields,
                'missing_fields': missing_fields,
                'present_fields': list(frontmatter.keys())
            }
        }

    def _validate_seo(self, frontmatter: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate SEO requirements.
        
        Args:
            frontmatter: Frontmatter dictionary
            
        Returns:
            List of check results for SEO requirements
        """
        checks = []
        seo_config = self.validation_config.get('content_validation', {}).get('seo', {})
        
        # Validate title
        title_config = seo_config.get('title', {})
        title = frontmatter.get('title', '')
        min_len = title_config.get('min_length', 30)
        max_len = title_config.get('max_length', 60)
        strict = title_config.get('strict', True)
        
        title_len = len(title)
        title_passed = min_len <= title_len <= max_len
        
        if title_passed:
            title_msg = f"SEO title valid: {title_len} characters (range: {min_len}-{max_len})"
        else:
            if title_len < min_len:
                title_msg = f"SEO title too short: {title_len} characters (minimum: {min_len})"
            else:
                title_msg = f"SEO title too long: {title_len} characters (maximum: {max_len})"
        
        checks.append({
            'name': 'seo_title',
            'passed': title_passed,
            'message': title_msg,
            'severity': 'high' if strict else 'medium',
            'details': {'length': title_len, 'min_length': min_len, 'max_length': max_len}
        })
        
        # Validate description
        desc_config = seo_config.get('description', {})
        description = frontmatter.get('description', '')
        min_len = desc_config.get('min_length', 120)
        max_len = desc_config.get('max_length', 160)
        strict = desc_config.get('strict', True)
        
        desc_len = len(description)
        desc_passed = min_len <= desc_len <= max_len
        
        if desc_passed:
            desc_msg = f"SEO description valid: {desc_len} characters (range: {min_len}-{max_len})"
        else:
            if desc_len < min_len:
                desc_msg = f"SEO description too short: {desc_len} characters (minimum: {min_len})"
            else:
                desc_msg = f"SEO description too long: {desc_len} characters (maximum: {max_len})"
        
        checks.append({
            'name': 'seo_description',
            'passed': desc_passed,
            'message': desc_msg,
            'severity': 'high' if strict else 'medium',
            'details': {'length': desc_len, 'min_length': min_len, 'max_length': max_len}
        })
        
        return checks

    def _extract_code_from_content(self, content: str) -> str:
        """Extract code blocks from markdown content.
        
        Args:
            content: Markdown content
            
        Returns:
            Concatenated code from all code blocks
        """
        try:
            code_blocks = extract_code_blocks(content)
            return '\n\n'.join(code_blocks) if code_blocks else ''
        except Exception as e:
            logger.debug("Error extracting code blocks: %s", e)
            return ''

    def _extract_links(self, content: str) -> List[str]:
        """Extract URLs from content.
        
        Args:
            content: Content text
            
        Returns:
            List of URLs found in content
        """
        # Match markdown links [text](url) and plain URLs
        markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        plain_urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', content)
        
        links = [url for text, url in markdown_links] + plain_urls
        
        # Filter out invalid URLs
        valid_links = []
        for link in links:
            try:
                parsed = urlparse(link)
                if parsed.scheme in ['http', 'https'] and parsed.netloc:
                    valid_links.append(link)
            except Exception:
                pass
        
        return list(set(valid_links))  # Remove duplicates

    def _extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """Extract frontmatter from markdown content.
        
        Args:
            content: Markdown content
            
        Returns:
            Dict with frontmatter data
        """
        # Match YAML frontmatter between --- delimiters
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            try:
                return yaml.safe_load(match.group(1)) or {}
            except Exception as e:
                logger.debug("Error parsing frontmatter: %s", e)
        return {}
# DOCGEN:LLM-FIRST@v4