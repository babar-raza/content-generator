"""Enhanced validation utilities for UCOP.

Provides comprehensive validation functions for configuration, input data, and more.
"""

import re
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from urllib.parse import urlparse


def validate_config(
    config: Any,
    required_fields: Optional[List[str]] = None,
    schema: Optional[Dict[str, type]] = None,
    strict: bool = False
) -> None:
    """Validate configuration data against optional schema.

    Args:
        config: Configuration data to validate
        required_fields: List of required field names
        schema: Optional schema definition with field types (dict of field_name: type)
        strict: If True, raise error on extra keys not in schema

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(config, dict):
        raise ValueError(f"Config must be a dict, got {type(config).__name__}")

    # Check required fields
    if required_fields is not None:
        missing = set(required_fields) - set(config.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

    # Validate against schema
    if schema is not None:
        for field_name, expected_type in schema.items():
            if field_name in config:
                value = config[field_name]
                if not isinstance(value, expected_type):
                    raise ValueError(
                        f"Config field '{field_name}' has wrong type: expected {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )

        if strict:
            # Check for extra keys not in schema
            extra_keys = set(config.keys()) - set(schema.keys())
            if extra_keys:
                raise ValueError(f"Unexpected fields: {extra_keys}")


def validate_input(
    value: Any,
    field_name: str,
    expected_type: Optional[type] = None,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
    allowed_values: Optional[List] = None,
    not_none: bool = False,
    not_empty: bool = False
) -> None:
    """Validate input with various checks.

    Args:
        value: Value to validate
        field_name: Name of the field being validated
        expected_type: Expected type (e.g., int, str)
        min_value: Minimum value for numeric validation
        max_value: Maximum value for numeric validation
        min_length: Minimum length for string/list validation
        max_length: Maximum length for string/list validation
        pattern: Regex pattern for string validation
        allowed_values: List of allowed values
        not_none: If True, value cannot be None
        not_empty: If True, value cannot be empty string or empty collection

    Raises:
        ValueError: If validation fails
        TypeError: If type check fails
    """
    # Check not_none
    if not_none and value is None:
        raise ValueError(f"{field_name} cannot be None")

    # Check not_empty
    if not_empty:
        if value is None or (hasattr(value, '__len__') and len(value) == 0):
            raise ValueError(f"{field_name} cannot be empty")

    # Check type
    if expected_type is not None and value is not None:
        if not isinstance(value, expected_type):
            raise TypeError(
                f"{field_name} must be of type {expected_type.__name__}, got {type(value).__name__}"
            )

    # Check min_value (for numbers)
    if min_value is not None and value is not None:
        if value < min_value:
            raise ValueError(f"{field_name} must be >= {min_value}")

    # Check max_value (for numbers)
    if max_value is not None and value is not None:
        if value > max_value:
            raise ValueError(f"{field_name} must be <= {max_value}")

    # Check min_length (for strings/lists)
    if min_length is not None and value is not None:
        actual_len = len(value)
        if actual_len < min_length:
            raise ValueError(f"{field_name} length must be >= {min_length}")

    # Check max_length (for strings/lists)
    if max_length is not None and value is not None:
        actual_len = len(value)
        if actual_len > max_length:
            raise ValueError(f"{field_name} length must be <= {max_length}")

    # Check pattern (for strings)
    if pattern is not None and value is not None:
        if not re.match(pattern, str(value)):
            raise ValueError(f"{field_name} does not match required pattern")

    # Check allowed values
    if allowed_values is not None and value is not None:
        if value not in allowed_values:
            raise ValueError(f"{field_name} must be one of {allowed_values}")


def validate_url(url: str, schemes: Optional[List[str]] = None) -> bool:
    """Validate URL with optional scheme checking.

    Args:
        url: URL to validate
        schemes: List of allowed schemes (e.g., ['http', 'https'])

    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)

        # Check if URL has scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return False

        # If no schemes specified, default to http and https
        if schemes is None:
            schemes = ['http', 'https']

        # Check allowed schemes
        if parsed.scheme not in schemes:
            return False

        return True
    except Exception:
        return False


def validate_email(email: str, allow_localhost: bool = False) -> bool:
    """Validate email address.

    Args:
        email: Email address to validate
        allow_localhost: If True, allow localhost domain

    Returns:
        True if valid, False otherwise
    """
    if not email or "@" not in email:
        return False

    # Check for localhost if allowed
    if allow_localhost and email.endswith('@localhost'):
        return True

    # Basic email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(pattern, email):
        return False

    return True


def validate_port(port: Union[int, str], allow_privileged: bool = False) -> bool:
    """Validate port number.

    Args:
        port: Port number (int or string)
        allow_privileged: If True, allow privileged ports (< 1024)

    Returns:
        True if valid, False otherwise
    """
    try:
        port_int = int(port)
    except (ValueError, TypeError):
        return False

    # Check port range
    if not (1 <= port_int <= 65535):
        return False

    # Check privileged ports
    if port_int < 1024 and not allow_privileged:
        return False

    return True


def validate_ipv4(ip: str) -> bool:
    """Validate IPv4 address.

    Args:
        ip: IP address string to validate

    Returns:
        True if valid IPv4 address, False otherwise
    """
    if not isinstance(ip, str):
        return False

    parts = ip.split('.')
    if len(parts) != 4:
        return False

    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False


def validate_range(
    value: Union[int, float],
    min_val: Union[int, float],
    max_val: Union[int, float],
    inclusive: bool = True
) -> bool:
    """Validate numeric range.

    Args:
        value: Numeric value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        inclusive: If True, endpoints are included; if False, endpoints are excluded

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(value, (int, float)):
        return False

    if inclusive:
        return min_val <= value <= max_val
    else:
        return min_val < value < max_val


def validate_dict_structure(
    data: Any,
    required_keys: List[str],
    optional_keys: Optional[List[str]] = None,
    strict: bool = False
) -> bool:
    """Validate dictionary structure.

    Args:
        data: Data to validate (should be dict)
        required_keys: List of required keys
        optional_keys: List of optional keys
        strict: If True, no extra keys allowed beyond required and optional

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(data, dict):
        return False

    # Check required keys
    missing_keys = set(required_keys) - set(data.keys())
    if missing_keys:
        return False

    if strict:
        # In strict mode, check that all keys are either required or optional
        allowed_keys = set(required_keys)
        if optional_keys is not None:
            allowed_keys.update(optional_keys)

        extra_keys = set(data.keys()) - allowed_keys
        if extra_keys:
            return False

    return True


def validate_path(path: str, must_exist: bool = False) -> bool:
    """Validate file system path.

    Args:
        path: Path string to validate
        must_exist: If True, path must exist

    Returns:
        True if valid path
    """
    try:
        p = Path(path)
        if must_exist:
            return p.exists()
        return True
    except (ValueError, OSError):
        return False


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """Validate data against JSON schema (simplified).

    Args:
        data: Data to validate
        schema: Schema to validate against

    Returns:
        True if data matches schema

    Note:
        This is a simplified validator. For production use, consider jsonschema library.
    """
    if not isinstance(data, dict) or not isinstance(schema, dict):
        return False

    # Simple type checking
    required_fields = schema.get('required', [])
    properties = schema.get('properties', {})

    # Check required fields
    for field in required_fields:
        if field not in data:
            return False

    # Check property types
    for field, field_schema in properties.items():
        if field in data:
            expected_type = field_schema.get('type')
            if expected_type == 'string' and not isinstance(data[field], str):
                return False
            elif expected_type == 'integer' and not isinstance(data[field], int):
                return False
            elif expected_type == 'number' and not isinstance(data[field], (int, float)):
                return False
            elif expected_type == 'boolean' and not isinstance(data[field], bool):
                return False
            elif expected_type == 'array' and not isinstance(data[field], list):
                return False
            elif expected_type == 'object' and not isinstance(data[field], dict):
                return False

    return True


__all__ = [
    'validate_config',
    'validate_input',
    'validate_url',
    'validate_email',
    'validate_port',
    'validate_ipv4',
    'validate_path',
    'validate_json_schema',
    'validate_range',
    'validate_dict_structure',
]
