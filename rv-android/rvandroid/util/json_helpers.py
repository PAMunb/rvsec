# rvandroid/util/json_helpers.py
"""
Utility module for JSON processing within the rv-android system.
Provides safe parsing and advanced JSON repair functionality.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def safe_parse_json(text: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    Safely parse JSON with improved error handling.

    Args:
        text: JSON string to parse

    Returns:
        Tuple of (parsed_json, error_message)
    """
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, str(e)


def extract_json_array(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract a JSON array from text that might contain other content.

    Args:
        text: Text potentially containing JSON

    Returns:
        Tuple of (json_text, error_message)
    """
    try:
        # Look for array brackets
        open_bracket = text.find('[')
        close_bracket = text.rfind(']')

        if open_bracket == -1 or close_bracket == -1 or close_bracket <= open_bracket:
            return None, "No valid JSON array brackets found"

        # Extract text between brackets
        json_text = text[open_bracket:close_bracket + 1]

        # Try to parse it
        try:
            json.loads(json_text)
            return json_text, None
        except json.JSONDecodeError:
            # Try to fix common issues
            fixed_json = repair_json(json_text)
            if fixed_json:
                return fixed_json, None
            return None, "Invalid JSON array format"

    except Exception as e:
        return None, f"Error extracting JSON: {str(e)}"


def repair_json(text: str) -> Optional[str]:
    """
    Attempt to repair malformed JSON.

    Args:
        text: Potentially malformed JSON

    Returns:
        Repaired JSON string or None if unfixable
    """
    # Ensure we're working with correct brackets
    if not (text.strip().startswith('[') and text.strip().endswith(']')):
        text = f"[{text}]"

    # Replace single quotes with double quotes
    text = re.sub(r"'([^']*)'", r'"\1"', text)

    # Fix unquoted property names
    text = re.sub(r'([a-zA-Z_][a-zA-Z0-9_]*):', r'"\1":', text)

    # Fix trailing commas
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # Fix missing commas between objects
    text = re.sub(r'}\s*{', r'},{', text)

    # Fix missing commas after values before property names
    text = re.sub(r'(true|false|null|\d+|\"\w+\")\s*(\"[a-zA-Z_][a-zA-Z0-9_]*\")', r'\1,\2', text)

    # Fix boolean and null literals
    text = re.sub(r':\s*True', r':true', text)
    text = re.sub(r':\s*False', r':false', text)
    text = re.sub(r':\s*None', r':null', text)

    # Validate the repaired JSON
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        return None


def validate_action_format(actions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Validate and normalize action format.

    Args:
        actions: List of action dictionaries

    Returns:
        Tuple of (valid_actions, errors)
    """
    valid_actions = []
    errors = []

    if not isinstance(actions, list):
        errors.append(f"Expected a list of actions, got {type(actions)}")
        return valid_actions, errors

    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            errors.append(f"Action at index {i} is not a dictionary")
            continue

        # Check for required fields
        if "action_id" not in action:
            errors.append(f"Missing action_id at index {i}")
            continue

        # Ensure params is a dictionary
        if "params" not in action or not isinstance(action["params"], dict):
            action["params"] = {}

        # Ensure explanation exists
        if "explanation" not in action or not action["explanation"]:
            action["explanation"] = f"Executing action {action['action_id']}"

        valid_actions.append(action)

    return valid_actions, errors


def detect_action_format(json_obj: Any) -> str:
    """
    Detect the format of actions in the JSON object.

    Args:
        json_obj: Parsed JSON object

    Returns:
        Format type: "action_id", "coordinate", or "unknown"
    """
    if not isinstance(json_obj, list) or not json_obj:
        return "unknown"

    first_action = json_obj[0]
    if not isinstance(first_action, dict):
        return "unknown"

    # Check for action_id format
    if "action_id" in first_action:
        return "action_id"

    # Check for coordinate format
    if ("action_type" in first_action and
            "target" in first_action and
            ("coordinates" in first_action or isinstance(first_action.get("target"), str))):
        return "coordinate"

    return "unknown"


def extract_structured_content(text: str) -> List[Dict[str, Any]]:
    """
    Extract structured action content from text, even when not properly formatted as JSON.
    Use pattern matching to identify action elements.

    Args:
        text: Text potentially containing action information

    Returns:
        List of action dictionaries
    """
    actions = []

    # Try to find action_id values
    action_id_matches = re.findall(r'action_id["\s:]+([0-9]+)', text)

    # Try to find explanation values
    explanation_matches = re.findall(r'explanation["\s:]+["\'](.*?)["\']', text)

    # Try to find params
    params_matches = re.findall(r'params["\s:]+({.*?})', text)

    # Create actions from matches
    for i, action_id in enumerate(action_id_matches):
        explanation = explanation_matches[i] if i < len(explanation_matches) else f"Action {action_id}"

        # Try to parse params if available
        params = {}
        if i < len(params_matches):
            try:
                # Try to fix and parse params
                params_text = repair_json("{" + params_matches[i] + "}")
                if params_text:
                    params = json.loads(params_text)
            except:
                pass

        actions.append({
            "action_id": action_id,
            "params": params,
            "explanation": explanation
        })

    return actions
