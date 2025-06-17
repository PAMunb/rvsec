# rvandroid/util/config_utils.py
"""
Utility functions for configuration management.
"""
from typing import Dict, Any

# TODO eh usada?
def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries, with values from dict2 taking precedence.

    Args:
        dict1: Base dictionary
        dict2: Dictionary to merge (takes precedence)

    Returns:
        Merged dictionary
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # For non-dict values or keys not in dict1, use the value from dict2
            result[key] = value

    return result
