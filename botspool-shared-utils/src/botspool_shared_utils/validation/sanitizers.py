"""
Input sanitization utilities
"""

import re
import html
import urllib.parse
from typing import Any, Dict, List, Optional


def sanitize_string(
    value: str, max_length: Optional[int] = None, allowed_chars: Optional[str] = None
) -> str:
    """
    Sanitize a string by removing or replacing unwanted characters.

    Args:
        value: String to sanitize
        max_length: Maximum length of the string
        allowed_chars: Regular expression pattern for allowed characters

    Returns:
        str: Sanitized string
    """
    if not isinstance(value, str):
        return str(value)

    # Remove null bytes and control characters
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", value)

    # Apply character filter if specified
    if allowed_chars:
        sanitized = re.sub(f"[^{allowed_chars}]", "", sanitized)

    # Truncate if max_length is specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized.strip()


def sanitize_html(html_content: str, allowed_tags: Optional[List[str]] = None) -> str:
    """
    Sanitize HTML content by escaping or removing dangerous elements.

    Args:
        html_content: HTML content to sanitize
        allowed_tags: List of allowed HTML tags

    Returns:
        str: Sanitized HTML content
    """
    if not isinstance(html_content, str):
        return str(html_content)

    # If no allowed tags specified, escape all HTML
    if not allowed_tags:
        return html.escape(html_content)

    # Remove script tags and dangerous attributes
    sanitized = re.sub(
        r"<script[^>]*>.*?</script>", "", html_content, flags=re.IGNORECASE | re.DOTALL
    )
    sanitized = re.sub(
        r"<iframe[^>]*>.*?</iframe>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
    )
    sanitized = re.sub(
        r"<object[^>]*>.*?</object>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
    )
    sanitized = re.sub(
        r"<embed[^>]*>.*?</embed>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove dangerous attributes
    dangerous_attrs = [
        "onload",
        "onerror",
        "onclick",
        "onmouseover",
        "onfocus",
        "onblur",
    ]
    for attr in dangerous_attrs:
        sanitized = re.sub(
            f"{attr}\\s*=\\s*[\"'][^\"']*[\"']", "", sanitized, flags=re.IGNORECASE
        )

    # Keep only allowed tags
    if allowed_tags:
        # Create pattern for allowed tags
        allowed_pattern = "|".join(allowed_tags)
        # Remove all tags except allowed ones
        sanitized = re.sub(
            f"<(?!({allowed_pattern})\\b)[^>]*>", "", sanitized, flags=re.IGNORECASE
        )

    return sanitized


def sanitize_sql(value: str) -> str:
    """
    Sanitize string to prevent SQL injection.

    Args:
        value: String to sanitize

    Returns:
        str: Sanitized string
    """
    if not isinstance(value, str):
        return str(value)

    # Remove or escape dangerous SQL characters
    dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]

    sanitized = value
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")

    # Remove SQL keywords that could be used for injection
    sql_keywords = [
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "EXEC",
        "EXECUTE",
    ]
    for keyword in sql_keywords:
        sanitized = re.sub(f"\\b{keyword}\\b", "", sanitized, flags=re.IGNORECASE)

    return sanitized.strip()


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename by removing dangerous characters.

    Args:
        filename: Filename to sanitize
        max_length: Maximum filename length

    Returns:
        str: Sanitized filename
    """
    if not isinstance(filename, str):
        return str(filename)

    # Remove path separators and dangerous characters
    dangerous_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    sanitized = filename

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "_")

    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip(". ")

    # Truncate if too long
    if len(sanitized) > max_length:
        name, ext = sanitized.rsplit(".", 1) if "." in sanitized else (sanitized, "")
        if ext:
            max_name_length = max_length - len(ext) - 1
            sanitized = name[:max_name_length] + "." + ext
        else:
            sanitized = sanitized[:max_length]

    return sanitized


def sanitize_url(url: str) -> str:
    """
    Sanitize URL by removing dangerous components.

    Args:
        url: URL to sanitize

    Returns:
        str: Sanitized URL
    """
    if not isinstance(url, str):
        return str(url)

    try:
        # Parse the URL
        parsed = urllib.parse.urlparse(url)

        # Only allow http and https schemes
        if parsed.scheme not in ["http", "https"]:
            return ""

        # Remove dangerous query parameters
        query_params = urllib.parse.parse_qs(parsed.query)
        dangerous_params = ["javascript", "data", "vbscript"]

        for param in dangerous_params:
            query_params.pop(param, None)

        # Rebuild the URL
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        sanitized = urllib.parse.urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

        return sanitized

    except Exception:
        return ""


def sanitize_json(json_string: str) -> str:
    """
    Sanitize JSON string by removing dangerous content.

    Args:
        json_string: JSON string to sanitize

    Returns:
        str: Sanitized JSON string
    """
    if not isinstance(json_string, str):
        return str(json_string)

    # Remove null bytes and control characters
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", json_string)

    # Remove potential script injections
    sanitized = re.sub(
        r"<script[^>]*>.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
    )
    sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"vbscript:", "", sanitized, flags=re.IGNORECASE)

    return sanitized.strip()


def sanitize_xss(value: str) -> str:
    """
    Sanitize string to prevent XSS attacks.

    Args:
        value: String to sanitize

    Returns:
        str: Sanitized string
    """
    if not isinstance(value, str):
        return str(value)

    # Escape HTML entities
    sanitized = html.escape(value)

    # Remove script tags and dangerous attributes
    sanitized = re.sub(
        r"<script[^>]*>.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
    )
    sanitized = re.sub(
        r"<iframe[^>]*>.*?</iframe>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
    )
    sanitized = re.sub(
        r"<object[^>]*>.*?</object>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
    )
    sanitized = re.sub(
        r"<embed[^>]*>.*?</embed>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove dangerous attributes
    dangerous_attrs = [
        "onload",
        "onerror",
        "onclick",
        "onmouseover",
        "onfocus",
        "onblur",
        "onchange",
    ]
    for attr in dangerous_attrs:
        sanitized = re.sub(
            f"{attr}\\s*=\\s*[\"'][^\"']*[\"']", "", sanitized, flags=re.IGNORECASE
        )

    return sanitized


def sanitize_path(path: str) -> str:
    """
    Sanitize file path by removing dangerous components.

    Args:
        path: File path to sanitize

    Returns:
        str: Sanitized file path
    """
    if not isinstance(path, str):
        return str(path)

    # Remove path traversal attempts
    sanitized = path.replace("../", "").replace("..\\", "")
    sanitized = sanitized.replace("./", "").replace(".\\", "")

    # Remove dangerous characters
    dangerous_chars = ["<", ">", ":", '"', "|", "?", "*"]
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "_")

    # Remove leading/trailing slashes and dots
    sanitized = sanitized.strip("/\\.")

    return sanitized
