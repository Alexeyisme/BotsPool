"""
Input validation utilities
"""

import re
import json
import uuid
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse


def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """
    Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not phone or not isinstance(phone, str):
        return False

    # Remove all non-digit characters
    digits = re.sub(r"\D", "", phone)

    # Check if it's a valid length (10-15 digits)
    return 10 <= len(digits) <= 15


def validate_password(password: str, min_length: int = 8) -> Dict[str, Any]:
    """
    Validate password strength.

    Args:
        password: Password to validate
        min_length: Minimum password length

    Returns:
        Dict[str, Any]: Validation result with details
    """
    if not password or not isinstance(password, str):
        return {"valid": False, "errors": ["Password is required"]}

    errors = []

    # Check length
    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters long")

    # Check for uppercase letter
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    # Check for lowercase letter
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    # Check for digit
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    # Check for special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")

    return {"valid": len(errors) == 0, "errors": errors}


def validate_username(username: str, min_length: int = 3, max_length: int = 30) -> bool:
    """
    Validate username format.

    Args:
        username: Username to validate
        min_length: Minimum username length
        max_length: Maximum username length

    Returns:
        bool: True if valid, False otherwise
    """
    if not username or not isinstance(username, str):
        return False

    # Check length
    if not (min_length <= len(username) <= max_length):
        return False

    # Check format (alphanumeric and underscores only)
    pattern = r"^[a-zA-Z0-9_]+$"
    return bool(re.match(pattern, username))


def validate_url(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_uuid(uuid_string: str) -> bool:
    """
    Validate UUID format.

    Args:
        uuid_string: UUID string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not uuid_string or not isinstance(uuid_string, str):
        return False

    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False


def validate_json(json_string: str) -> bool:
    """
    Validate JSON format.

    Args:
        json_string: JSON string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not json_string or not isinstance(json_string, str):
        return False

    try:
        json.loads(json_string)
        return True
    except json.JSONDecodeError:
        return False


def validate_schema(data: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate data against a schema.

    Args:
        data: Data to validate
        schema: Schema definition

    Returns:
        Dict[str, Any]: Validation result with details
    """
    errors = []

    # Check required fields
    required_fields = schema.get("required", [])
    for field in required_fields:
        if field not in data:
            errors.append(f"Required field '{field}' is missing")

    # Check field types
    properties = schema.get("properties", {})
    for field, value in data.items():
        if field in properties:
            field_schema = properties[field]
            field_type = field_schema.get("type")

            if field_type == "string" and not isinstance(value, str):
                errors.append(f"Field '{field}' must be a string")
            elif field_type == "integer" and not isinstance(value, int):
                errors.append(f"Field '{field}' must be an integer")
            elif field_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Field '{field}' must be a number")
            elif field_type == "boolean" and not isinstance(value, bool):
                errors.append(f"Field '{field}' must be a boolean")
            elif field_type == "array" and not isinstance(value, list):
                errors.append(f"Field '{field}' must be an array")
            elif field_type == "object" and not isinstance(value, dict):
                errors.append(f"Field '{field}' must be an object")

    return {"valid": len(errors) == 0, "errors": errors}


def validate_enum(value: Any, allowed_values: List[Any]) -> bool:
    """
    Validate that a value is in a list of allowed values.

    Args:
        value: Value to validate
        allowed_values: List of allowed values

    Returns:
        bool: True if valid, False otherwise
    """
    return value in allowed_values


def validate_range(
    value: Union[int, float],
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
) -> bool:
    """
    Validate that a numeric value is within a range.

    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(value, (int, float)):
        return False

    if min_value is not None and value < min_value:
        return False

    if max_value is not None and value > max_value:
        return False

    return True


def validate_length(
    value: str, min_length: Optional[int] = None, max_length: Optional[int] = None
) -> bool:
    """
    Validate string length.

    Args:
        value: String to validate
        min_length: Minimum length
        max_length: Maximum length

    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(value, str):
        return False

    length = len(value)

    if min_length is not None and length < min_length:
        return False

    if max_length is not None and length > max_length:
        return False

    return True
