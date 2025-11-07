"""JSON Repair Utility - Fixes common JSON parsing errors from LLM responses"""

import json
import re
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class JSONRepair:
    """Repairs malformed JSON strings from LLM responses."""
    
    @staticmethod
    def repair(json_str: str, max_attempts: int = 3) -> Union[Dict, List]:
        """
        Attempt to repair and parse malformed JSON.
        
        Args:
            json_str: Potentially malformed JSON string
            max_attempts: Maximum repair attempts
            
        Returns:
            Parsed JSON object (dict or list)
            
        Raises:
            json.JSONDecodeError: If all repair attempts fail
        """
        if not json_str:
            return {}
        
        # Try to parse as-is first
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as original_error:
            logger.debug(f"Initial JSON parse failed: {original_error}")
        
        # Progressive repair attempts
        repaired = json_str
        for attempt in range(max_attempts):
            try:
                # Apply repairs
                repaired = JSONRepair._apply_repairs(repaired, attempt)
                
                # Try to parse
                result = json.loads(repaired)
                logger.info(f"JSON repaired successfully on attempt {attempt + 1}")
                return result
                
            except json.JSONDecodeError as e:
                logger.debug(f"Repair attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    # Final attempt - try more aggressive repairs
                    try:
                        result = JSONRepair._aggressive_repair(json_str)
                        logger.info("JSON repaired using aggressive method")
                        return result
                    except:
                        # Return a safe default
                        logger.warning("All repair attempts failed, returning default")
                        return JSONRepair._safe_default(json_str)
        
        return {}
    
    @staticmethod
    def _apply_repairs(json_str: str, level: int) -> str:
        """Apply progressive repair strategies."""
        
        # Level 0: Basic cleaning
        if level >= 0:
            # Remove BOM and zero-width characters
            json_str = json_str.encode('utf-8', 'ignore').decode('utf-8-sig')
            
            # Remove control characters except newlines and tabs
            json_str = ''.join(char if char in '\n\t' or ord(char) >= 32 else '' for char in json_str)
            
            # Strip leading/trailing whitespace
            json_str = json_str.strip()
            
            # Remove any text before the first { or [
            first_brace = json_str.find('{')
            first_bracket = json_str.find('[')
            if first_brace >= 0 or first_bracket >= 0:
                if first_brace < 0:
                    json_str = json_str[first_bracket:]
                elif first_bracket < 0:
                    json_str = json_str[first_brace:]
                else:
                    json_str = json_str[min(first_brace, first_bracket):]
        
        # Level 1: Fix common syntax errors
        if level >= 1:
            # Fix unterminated strings by adding closing quotes
            json_str = JSONRepair._fix_unterminated_strings(json_str)
            
            # Fix trailing commas
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            # Add missing commas between elements
            json_str = re.sub(r'"\s*\n\s*"', '",\n"', json_str)
            json_str = re.sub(r'}\s*\n\s*{', '},\n{', json_str)
            json_str = re.sub(r']\s*\n\s*\[', '],\n[', json_str)
        
        # Level 2: Balance brackets and braces
        if level >= 2:
            json_str = JSONRepair._balance_brackets(json_str)
        
        return json_str
    
    @staticmethod
    def _fix_unterminated_strings(json_str: str) -> str:
        """Fix unterminated string literals."""
        lines = json_str.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Count quotes in the line
            quote_count = line.count('"') - line.count('\\"')
            
            # If odd number of quotes, likely unterminated
            if quote_count % 2 != 0:
                # Add closing quote before comma or bracket/brace
                if line.rstrip().endswith(','):
                    line = line.rstrip()[:-1] + '",'
                elif line.rstrip()[-1:] in '}]':
                    line = line[:-1] + '"' + line[-1:]
                else:
                    line = line.rstrip() + '"'
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    @staticmethod
    def _balance_brackets(json_str: str) -> str:
        """Balance brackets and braces."""
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        
        # Add missing closing braces
        if open_braces > close_braces:
            json_str += '}' * (open_braces - close_braces)
        
        # Add missing closing brackets
        if open_brackets > close_brackets:
            json_str += ']' * (open_brackets - close_brackets)
        
        return json_str
    
    @staticmethod
    def _aggressive_repair(json_str: str) -> Union[Dict, List]:
        """More aggressive repair using regex extraction."""
        
        # Try to extract JSON-like structures
        json_patterns = [
            r'\{[^{}]*\}',  # Simple object
            r'\[[^\[\]]*\]',  # Simple array
            r'\{.*\}',  # Any object (greedy)
            r'\[.*\]',  # Any array (greedy)
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, json_str, re.DOTALL)
            for match in matches:
                try:
                    # Clean up the match
                    cleaned = match.strip()
                    cleaned = re.sub(r',\s*[}\]]', lambda m: m.group(0)[1:], cleaned)
                    return json.loads(cleaned)
                except:
                    continue
        
        # Try to build a valid structure from key-value pairs
        return JSONRepair._extract_key_values(json_str)
    
    @staticmethod
    def _extract_key_values(json_str: str) -> Dict:
        """Extract key-value pairs from malformed JSON."""
        result = {}
        
        # Look for "key": "value" patterns
        pattern = r'"([^"]+)"\s*:\s*"([^"]*)"'
        matches = re.findall(pattern, json_str)
        for key, value in matches:
            result[key] = value
        
        # Look for "key": number patterns
        pattern = r'"([^"]+)"\s*:\s*(-?\d+\.?\d*)'
        matches = re.findall(pattern, json_str)
        for key, value in matches:
            try:
                result[key] = float(value) if '.' in value else int(value)
            except:
                result[key] = value
        
        # Look for "key": boolean patterns
        pattern = r'"([^"]+)"\s*:\s*(true|false|null)'
        matches = re.findall(pattern, json_str, re.IGNORECASE)
        for key, value in matches:
            if value.lower() == 'true':
                result[key] = True
            elif value.lower() == 'false':
                result[key] = False
            else:
                result[key] = None
        
        # Look for "key": [...] patterns
        pattern = r'"([^"]+)"\s*:\s*\[([^\]]*)\]'
        matches = re.findall(pattern, json_str)
        for key, value in matches:
            try:
                # Try to parse the array
                array_str = f'[{value}]'
                result[key] = json.loads(array_str)
            except:
                # Split by comma and clean
                items = [item.strip().strip('"') for item in value.split(',') if item.strip()]
                result[key] = items
        
        return result
    
    @staticmethod
    def _safe_default(json_str: str) -> Dict:
        """Return a safe default structure when all repairs fail."""
        # Try to extract any meaningful data
        result = {}
        
        # Look for a title-like field
        title_patterns = [
            r'"title"\s*:\s*"([^"]*)"',
            r'"name"\s*:\s*"([^"]*)"',
            r'"topic"\s*:\s*"([^"]*)"'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, json_str, re.IGNORECASE)
            if match:
                result['title'] = match.group(1)
                break
        
        # If no title found, generate a default
        if 'title' not in result:
            # Try to extract any quoted string as potential title
            quotes = re.findall(r'"([^"]+)"', json_str)
            if quotes and len(quotes[0]) > 5:
                result['title'] = quotes[0]
            else:
                result['title'] = 'Untitled'
        
        # Ensure it has the structure expected by agents
        if 'topics' not in result:
            result = {'topics': [result]}
        
        return result


def safe_json_loads(json_str: str, default: Optional[Any] = None) -> Any:
    """
    Safely parse JSON with automatic repair.
    
    Args:
        json_str: JSON string to parse
        default: Default value to return on failure
        
    Returns:
        Parsed JSON or default value
    """
    try:
        return JSONRepair.repair(json_str)
    except Exception as e:
        logger.error(f"Failed to parse/repair JSON: {e}")
        return default if default is not None else {}
