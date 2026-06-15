"""
Helper functions for common operations
"""

import uuid
import json
import re
from datetime import datetime
from typing import Any, Dict, Optional, Union
from bson import ObjectId
import hashlib


def generate_request_id() -> str:
    """
    Generate unique request ID
    
    Returns:
        Unique request ID string
    """
    return str(uuid.uuid4())


def format_datetime(dt: Union[datetime, str, None], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime to string
    
    Args:
        dt: Datetime object or string
        format_str: Output format
    
    Returns:
        Formatted datetime string
    """
    if dt is None:
        return "N/A"
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    
    if isinstance(dt, datetime):
        return dt.strftime(format_str)
    
    return str(dt)


def safe_json_parse(data: Union[str, bytes], default: Any = None) -> Any:
    """
    Safely parse JSON data
    
    Args:
        data: JSON string or bytes
        default: Default value if parsing fails
    
    Returns:
        Parsed JSON or default value
    """
    try:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return json.loads(data)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        return default


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to maximum length
    
    Args:
        text: Input string
        max_length: Maximum length
        suffix: Suffix to add when truncated
    
    Returns:
        Truncated string
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two strings using Levenshtein distance
    
    Args:
        text1: First text
        text2: Second text
    
    Returns:
        Similarity score between 0 and 1
    """
    if not text1 or not text2:
        return 0.0
    
    # Normalize texts
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    
    if text1 == text2:
        return 1.0
    
    # Calculate Levenshtein distance
    len1, len2 = len(text1), len(text2)
    matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    
    for i in range(len1 + 1):
        matrix[i][0] = i
    for j in range(len2 + 1):
        matrix[0][j] = j
    
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if text1[i-1] == text2[j-1] else 1
            matrix[i][j] = min(
                matrix[i-1][j] + 1,      # deletion
                matrix[i][j-1] + 1,      # insertion
                matrix[i-1][j-1] + cost   # substitution
            )
    
    distance = matrix[len1][len2]
    max_len = max(len1, len2)
    similarity = 1.0 - (distance / max_len)
    
    return similarity


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to be safe for filesystem
    
    Args:
        filename: Input filename
    
    Returns:
        Sanitized filename
    """
    # Remove path separators
    filename = filename.replace("/", "_").replace("\\", "_")
    
    # Remove invalid characters
    filename = re.sub(r'[<>:"|?*]', "_", filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', "", filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:255 - len(ext) - 1] + "." + ext if ext else name[:255]
    
    return filename.strip()


def bytes_to_mb(bytes_value: int) -> float:
    """
    Convert bytes to megabytes
    
    Args:
        bytes_value: Size in bytes
    
    Returns:
        Size in megabytes
    """
    return bytes_value / (1024 * 1024)


def is_valid_object_id(id_str: str) -> bool:
    """
    Check if string is a valid MongoDB ObjectId
    
    Args:
        id_str: String to check
    
    Returns:
        True if valid ObjectId
    """
    try:
        ObjectId(id_str)
        return True
    except:
        return False


def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """
    Deep merge two dictionaries
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary
    
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def generate_hash(data: Union[str, bytes, Dict]) -> str:
    """
    Generate SHA-256 hash of data
    
    Args:
        data: Input data
    
    Returns:
        SHA-256 hash as hex string
    """
    if isinstance(data, dict):
        data = json.dumps(data, sort_keys=True)
    elif not isinstance(data, (str, bytes)):
        data = str(data)
    
    if isinstance(data, str):
        data = data.encode("utf-8")
    
    return hashlib.sha256(data).hexdigest()


def chunk_list(lst: list, chunk_size: int):
    """
    Split list into chunks
    
    Args:
        lst: List to split
        chunk_size: Size of each chunk
    
    Yields:
        Chunks of the list
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def mask_sensitive_data(data: Dict, sensitive_keys: list = None) -> Dict:
    """
    Mask sensitive data in dictionary
    
    Args:
        data: Dictionary with potential sensitive data
        sensitive_keys: Keys to mask (default: ['password', 'api_key', 'token'])
    
    Returns:
        Dictionary with masked values
    """
    if sensitive_keys is None:
        sensitive_keys = ['password', 'api_key', 'token', 'secret', 'authorization']
    
    result = data.copy()
    
    for key in sensitive_keys:
        if key in result:
            value = result[key]
            if isinstance(value, str) and len(value) > 4:
                result[key] = value[:2] + "***" + value[-2:]
            else:
                result[key] = "***MASKED***"
    
    return result