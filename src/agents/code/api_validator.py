"""API validator for code strictness checking."""

import ast
from pathlib import Path
from typing import List, Dict, Any, Set
import json
import logging

logger = logging.getLogger(__name__)


class APIStrictValidator:
    """Validates code against API reference truth tables."""
    
    def __init__(self, api_ref_path: Path = None):
        self.api_ref_path = api_ref_path or Path("./data/api_reference/python_stdlib.json")
        self.api_reference = self._load_api_reference()
        logger.info(f"APIStrictValidator initialized with {len(self.api_reference.get('functions', {}))} functions")
    
    def _load_api_reference(self) -> Dict[str, Any]:
        """Load API reference JSON."""
        if not self.api_ref_path.exists():
            logger.warning(f"API reference not found: {self.api_ref_path}, using empty reference")
            return {"functions": {}, "classes": {}}
        
        try:
            with open(self.api_ref_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load API reference: {e}")
            return {"functions": {}, "classes": {}}
    
    def validate_code(self, code: str) -> List[str]:
        """Check code against API reference."""
        errors = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [f"Syntax error: {e}"]
        
        # Check function calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_func_name(node)
                
                if func_name and func_name in self.api_reference.get('functions', {}):
                    api_def = self.api_reference['functions'][func_name]
                    
                    # Validate signature
                    validation_error = self._check_signature(node, api_def)
                    if validation_error:
                        errors.append(
                            f"API mismatch in '{func_name}': {validation_error}\n"
                            f"  Expected: {api_def.get('signature', 'unknown')}"
                        )
            
            elif isinstance(node, ast.Attribute):
                # Check method calls on known classes
                attr_name = node.attr
                
                # Get the object type if possible
                if isinstance(node.value, ast.Name):
                    # Could track variable types in more sophisticated analysis
                    pass
        
        return errors
    
    def _get_func_name(self, node: ast.Call) -> str:
        """Extract function name from call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            # e.g., os.path.join
            parts = []
            current = node.func
            
            while isinstance(current, ast.Attribute):
                parts.insert(0, current.attr)
                current = current.value
            
            if isinstance(current, ast.Name):
                parts.insert(0, current.id)
            
            return ".".join(parts)
        
        return ""
    
    def _check_signature(self, node: ast.Call, api_def: Dict[str, Any]) -> str:
        """Check if call matches API signature."""
        errors = []
        
        # Get expected parameters
        expected_params = api_def.get('params', [])
        required_params = [p for p in expected_params if not p.startswith('*') and not p.startswith('[')]
        
        # Count provided arguments
        provided_args = len(node.args) + len(node.keywords)
        
        # Check argument count
        if '*' not in str(expected_params):
            # Fixed argument count
            if provided_args < len(required_params):
                return f"too few arguments (got {provided_args}, expected at least {len(required_params)})"
        
        # Check keyword arguments
        if node.keywords:
            provided_kwargs = {kw.arg for kw in node.keywords}
            valid_kwargs = set(expected_params)
            
            invalid_kwargs = provided_kwargs - valid_kwargs
            if invalid_kwargs:
                return f"invalid keyword arguments: {', '.join(invalid_kwargs)}"
        
        return ""
    
    def validate_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate a Python file."""
        try:
            code = file_path.read_text(encoding='utf-8')
            errors = self.validate_code(code)
            
            return {
                "file": str(file_path),
                "valid": len(errors) == 0,
                "errors": errors,
                "error_count": len(errors)
            }
        except Exception as e:
            return {
                "file": str(file_path),
                "valid": False,
                "errors": [f"Failed to validate: {e}"],
                "error_count": 1
            }
    
    def get_api_info(self, func_name: str) -> Dict[str, Any]:
        """Get API information for a function."""
        return self.api_reference.get('functions', {}).get(func_name, {})


def create_sample_api_reference(output_path: Path):
    """Create sample API reference file."""
    sample = {
        "functions": {
            "os.path.join": {
                "signature": "join(*paths) -> str",
                "params": ["*paths"],
                "return_type": "str",
                "description": "Join one or more path components intelligently",
                "examples": [
                    "os.path.join('/home', 'user', 'file.txt')"
                ]
            },
            "open": {
                "signature": "open(file, mode='r', encoding=None) -> file object",
                "params": ["file", "[mode='r']", "[encoding=None]"],
                "return_type": "file object",
                "description": "Open file and return a stream"
            },
            "len": {
                "signature": "len(obj) -> int",
                "params": ["obj"],
                "return_type": "int",
                "description": "Return the length of an object"
            }
        },
        "classes": {
            "pathlib.Path": {
                "methods": {
                    "exists": {
                        "signature": "exists() -> bool",
                        "params": [],
                        "return_type": "bool"
                    },
                    "read_text": {
                        "signature": "read_text(encoding=None) -> str",
                        "params": ["[encoding=None]"],
                        "return_type": "str"
                    }
                }
            }
        }
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(sample, f, indent=2)
    
    logger.info(f"Sample API reference created at {output_path}")
