"""QualityGateAgent - Enforces quality standards and aggregates validation results.

This agent acts as a quality gate that:
- Aggregates validation results from ValidationAgent
- Applies severity-based scoring
- Determines if content passes quality standards
- Provides detailed failure reports with suggestions
"""

from typing import Optional, Dict, List, Any
from pathlib import Path
import logging
import yaml

from ..base import (
    Agent, EventBus, AgentEvent, AgentContract,
    Config, logger
)


class QualityGateAgent(Agent):
    """Enforces quality standards based on validation results.
    
    Acts as a quality gate by:
    - Evaluating validation check results
    - Applying severity-based thresholds
    - Determining pass/fail status
    - Providing actionable feedback
    - Logging all quality decisions
    
    Aggregates results from ValidationAgent and enforces configured thresholds.
    """

    def __init__(self, config: Config, event_bus: EventBus):
        """Initialize QualityGateAgent.
        
        Args:
            config: System configuration object
            event_bus: EventBus instance for communication
        """
        self.quality_config = self._load_quality_config()
        Agent.__init__(self, "QualityGateAgent", config, event_bus)
        logger.info("QualityGateAgent initialized with thresholds: critical=%d, warnings=%d",
                   self.quality_config.get('quality_gate', {}).get('thresholds', {}).get('critical_failures', 0),
                   self.quality_config.get('quality_gate', {}).get('thresholds', {}).get('warnings', 5))

    def _load_quality_config(self) -> Dict[str, Any]:
        """Load quality gate configuration from yaml file.
        
        Returns:
            Dict containing quality gate rules
        """
        config_path = Path(__file__).parents[3] / "config" / "validation.yaml"
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    logger.info("Loaded quality gate config from %s", config_path)
                    return config_data
            else:
                logger.warning("Quality gate config not found at %s, using defaults", config_path)
                return self._get_default_config()
        except Exception as e:
            logger.error("Error loading quality gate config: %s, using defaults", e)
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default quality gate configuration.
        
        Returns:
            Dict with default quality gate rules
        """
        return {
            'quality_gate': {
                'thresholds': {
                    'critical_failures': 0,
                    'warnings': 5
                },
                'severity_weights': {
                    'critical': 1.0,
                    'high': 0.75,
                    'medium': 0.5,
                    'low': 0.25
                },
                'check_severity': {
                    'content_length': 'medium',
                    'keyword_density': 'high',
                    'code_syntax': 'critical',
                    'link_validation': 'low',
                    'frontmatter': 'critical',
                    'seo_title': 'high',
                    'seo_description': 'high',
                    'seo_keywords': 'medium'
                }
            }
        }

    def _create_contract(self) -> AgentContract:
        """Create agent contract defining capabilities.
        
        Returns:
            AgentContract with quality gate capabilities
        """
        return AgentContract(
            agent_id="QualityGateAgent",
            capabilities=["enforce_quality"],
            input_schema={
                "type": "object",
                "required": ["validation_results"],
                "properties": {
                    "validation_results": {
                        "type": "object",
                        "properties": {
                            "checks": {"type": "array"},
                            "summary": {"type": "object"}
                        }
                    }
                }
            },
            output_schema={
                "type": "object",
                "required": ["passed"],
                "properties": {
                    "passed": {"type": "boolean"},
                    "score": {"type": "number"},
                    "failures": {"type": "array"},
                    "warnings": {"type": "array"},
                    "passed_checks": {"type": "array"},
                    "decision": {"type": "string"},
                    "suggestions": {"type": "array"}
                }
            },
            publishes=["quality_gate_decision"]
        )

    def _subscribe_to_events(self):
        """Set up event subscriptions."""
        self.event_bus.subscribe("quality_gate_request", self.execute)
        self.event_bus.subscribe("validation_complete", self.execute)

    def execute(self, event: AgentEvent) -> Optional[AgentEvent]:
        """Execute quality gate evaluation.
        
        Args:
            event: AgentEvent with validation results
            
        Returns:
            AgentEvent with quality gate decision
            
        Raises:
            ValueError: If required data is missing
        """
        validation_results = event.data.get("validation_results")
        if not validation_results:
            # Try alternate data structure
            validation_results = event.data
        
        checks = validation_results.get("checks", [])
        if not checks:
            raise ValueError("validation_results.checks is required but was missing or empty")
        
        # Categorize checks by result
        failures = []
        warnings = []
        passed_checks = []
        
        critical_failures = 0
        warning_count = 0
        
        for check in checks:
            check_name = check.get('name', 'unknown')
            passed = check.get('passed', False)
            severity = check.get('severity', 'medium')
            message = check.get('message', '')
            
            if passed:
                passed_checks.append({
                    'name': check_name,
                    'message': message
                })
            else:
                check_info = {
                    'name': check_name,
                    'severity': severity,
                    'message': message,
                    'details': check.get('details', {})
                }
                
                if severity in ['critical', 'high']:
                    failures.append(check_info)
                    if severity == 'critical':
                        critical_failures += 1
                else:
                    warnings.append(check_info)
                    warning_count += 1
        
        # Apply quality gate thresholds
        thresholds = self.quality_config.get('quality_gate', {}).get('thresholds', {})
        max_critical = thresholds.get('critical_failures', 0)
        max_warnings = thresholds.get('warnings', 5)
        
        passed = (critical_failures <= max_critical and warning_count <= max_warnings)
        
        # Calculate quality score
        score = self._calculate_quality_score(checks)
        
        # Generate decision message
        if passed:
            decision = f"Quality gate PASSED: {len(passed_checks)} checks passed, {len(failures)} failures, {len(warnings)} warnings (Score: {score:.2f}/100)"
        else:
            reasons = []
            if critical_failures > max_critical:
                reasons.append(f"{critical_failures} critical failures (max: {max_critical})")
            if warning_count > max_warnings:
                reasons.append(f"{warning_count} warnings (max: {max_warnings})")
            decision = f"Quality gate FAILED: {', '.join(reasons)} (Score: {score:.2f}/100)"
        
        # Generate suggestions
        suggestions = self._generate_suggestions(failures, warnings)
        
        # Log decision
        logger.info("Quality gate decision: %s", decision)
        if failures:
            for failure in failures:
                logger.error("Quality check failed [%s]: %s - %s", 
                           failure['severity'], failure['name'], failure['message'])
        if warnings:
            for warning in warnings:
                logger.warning("Quality check warning [%s]: %s - %s",
                             warning['severity'], warning['name'], warning['message'])
        
        result = {
            'passed': passed,
            'score': score,
            'failures': failures,
            'warnings': warnings,
            'passed_checks': passed_checks,
            'decision': decision,
            'suggestions': suggestions,
            'statistics': {
                'total_checks': len(checks),
                'passed': len(passed_checks),
                'failed': len(failures),
                'warnings': len(warnings),
                'critical_failures': critical_failures
            }
        }
        
        return AgentEvent(
            event_type="quality_gate_decision",
            data=result,
            source_agent=self.agent_id,
            correlation_id=event.correlation_id
        )

    def _calculate_quality_score(self, checks: List[Dict[str, Any]]) -> float:
        """Calculate overall quality score based on checks and severity weights.
        
        Args:
            checks: List of validation check results
            
        Returns:
            Quality score from 0-100
        """
        if not checks:
            return 0.0
        
        weights = self.quality_config.get('quality_gate', {}).get('severity_weights', {})
        
        total_weight = 0.0
        earned_weight = 0.0
        
        for check in checks:
            severity = check.get('severity', 'medium')
            weight = weights.get(severity, 0.5)
            total_weight += weight
            
            if check.get('passed', False):
                earned_weight += weight
        
        if total_weight == 0:
            return 100.0
        
        score = (earned_weight / total_weight) * 100
        return round(score, 2)

    def _generate_suggestions(self, failures: List[Dict[str, Any]], 
                            warnings: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable suggestions based on failures and warnings.
        
        Args:
            failures: List of failed checks
            warnings: List of warning checks
            
        Returns:
            List of suggestion strings
        """
        suggestions = []
        
        # Group by check type
        check_types = {}
        for check in failures + warnings:
            check_name = check['name']
            if check_name not in check_types:
                check_types[check_name] = []
            check_types[check_name].append(check)
        
        # Generate specific suggestions
        for check_name, check_list in check_types.items():
            suggestion = self._get_suggestion_for_check(check_name, check_list[0])
            if suggestion:
                suggestions.append(suggestion)
        
        # General suggestions
        if failures:
            suggestions.append("Review and address all critical and high-severity failures before proceeding")
        
        if warnings:
            suggestions.append(f"Consider addressing {len(warnings)} warning(s) to improve content quality")
        
        return suggestions

    def _get_suggestion_for_check(self, check_name: str, check: Dict[str, Any]) -> str:
        """Get specific suggestion for a failed check.
        
        Args:
            check_name: Name of the check
            check: Check result dictionary
            
        Returns:
            Suggestion string
        """
        details = check.get('details', {})
        
        suggestions = {
            'content_length': self._suggest_content_length(details),
            'keyword_density': self._suggest_keyword_density(details),
            'code_syntax': "Fix code syntax errors. Review the issues list and ensure all code is valid.",
            'link_validation': "Check and fix broken links. Verify all URLs are accessible.",
            'frontmatter': self._suggest_frontmatter(details),
            'seo_title': self._suggest_seo_title(details),
            'seo_description': self._suggest_seo_description(details)
        }
        
        return suggestions.get(check_name, "")

    def _suggest_content_length(self, details: Dict[str, Any]) -> str:
        """Generate suggestion for content length issues.
        
        Args:
            details: Check details
            
        Returns:
            Suggestion string
        """
        word_count = details.get('word_count', 0)
        min_words = details.get('min_words', 0)
        max_words = details.get('max_words', 0)
        
        if word_count < min_words:
            needed = min_words - word_count
            return f"Add approximately {needed} more words to meet minimum length requirement"
        elif word_count > max_words:
            excess = word_count - max_words
            return f"Reduce content by approximately {excess} words to meet maximum length limit"
        return ""

    def _suggest_keyword_density(self, details: Dict[str, Any]) -> str:
        """Generate suggestion for keyword density issues.
        
        Args:
            details: Check details
            
        Returns:
            Suggestion string
        """
        density = details.get('density', 0)
        if density < 0.01:
            return "Increase keyword usage. Target keywords should appear more frequently in the content"
        elif density > 0.05:
            return "Reduce keyword usage to avoid keyword stuffing. Content should read naturally"
        return ""

    def _suggest_frontmatter(self, details: Dict[str, Any]) -> str:
        """Generate suggestion for frontmatter issues.
        
        Args:
            details: Check details
            
        Returns:
            Suggestion string
        """
        missing = details.get('missing_fields', [])
        if missing:
            return f"Add missing frontmatter fields: {', '.join(missing)}"
        return ""

    def _suggest_seo_title(self, details: Dict[str, Any]) -> str:
        """Generate suggestion for SEO title issues.
        
        Args:
            details: Check details
            
        Returns:
            Suggestion string
        """
        length = details.get('length', 0)
        min_len = details.get('min_length', 30)
        max_len = details.get('max_length', 60)
        
        if length < min_len:
            return f"Lengthen SEO title to at least {min_len} characters (current: {length})"
        elif length > max_len:
            return f"Shorten SEO title to at most {max_len} characters (current: {length})"
        return ""

    def _suggest_seo_description(self, details: Dict[str, Any]) -> str:
        """Generate suggestion for SEO description issues.
        
        Args:
            details: Check details
            
        Returns:
            Suggestion string
        """
        length = details.get('length', 0)
        min_len = details.get('min_length', 120)
        max_len = details.get('max_length', 160)
        
        if length < min_len:
            return f"Lengthen SEO description to at least {min_len} characters (current: {length})"
        elif length > max_len:
            return f"Shorten SEO description to at most {max_len} characters (current: {length})"
        return ""
# DOCGEN:LLM-FIRST@v4