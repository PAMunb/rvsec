# rvandroid/llm/response_parser.py
"""
Module for parsing and validating LLM responses.
Provides robust JSON extraction and validation functionality.
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from rvandroid.util.json_helpers import (
    repair_json,
    extract_structured_content
)


class ResponseValidator:
    """
    Validates the structure and content of LLM responses.
    """

    @staticmethod
    def validate_action_id_format(actions: List[Dict[str, Any]],
                                  available_action_ids: List[str],
                                  single_action_mode: bool = False) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Validate actions in action_id format.

        Args:
            actions: List of action dictionaries
            available_action_ids: List of valid action IDs
            single_action_mode: Whether to enforce single action

        Returns:
            Tuple of (valid_actions, errors)
        """
        valid_actions = []
        errors = []

        # Check if actions is a list
        if not isinstance(actions, list):
            errors.append(f"Expected a list of actions, got {type(actions)}")
            return valid_actions, errors

        # For single action mode, enforce exactly one action
        if single_action_mode and len(actions) > 1:
            actions = actions[:1]  # Take only the first action
            errors.append("Received multiple actions in single action mode. Using only the first action.")

        # Validate each action
        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                errors.append(f"Action at index {i} is not a dictionary")
                continue

            # Check for required fields
            if "action_id" not in action:
                errors.append(f"Missing action_id at index {i}")
                continue

            # Validate action_id
            action_id = str(action["action_id"])
            if available_action_ids and action_id not in available_action_ids:
                errors.append(f"Invalid action_id: {action_id} (not in available actions)")
                continue

            # Add default fields if missing
            if "params" not in action or not isinstance(action["params"], dict):
                action["params"] = {}

            if "explanation" not in action or not action["explanation"]:
                action["explanation"] = f"Executing action {action_id}"

            valid_actions.append(action)

        return valid_actions, errors


class ResponseParser:
    """
    Parses and extracts structured data from LLM responses.
    Handles common issues like malformed JSON or unexpected formats.
    """

    def __init__(self):
        """Initialize the response parser."""
        self.logger = logging.getLogger(__name__)

    def extract_json(self, text: str) -> str:
        """
        Extract JSON content from text that might contain other content.
        Enhanced version with more robust extraction and repair capabilities.

        Args:
            text: Text potentially containing JSON

        Returns:
            Extracted JSON string

        Raises:
            ValueError: If no valid JSON can be extracted
        """
        self.logger.debug(f"Attempting to extract JSON from response of length {len(text)}")

        # Try to validate the entire text as JSON first (common in API responses)
        try:
            json.loads(text)
            self.logger.debug("Entire response is valid JSON")
            return text
        except json.JSONDecodeError:
            self.logger.debug("Response is not valid JSON as a whole, attempting extraction")

        # Look for JSON in code blocks (common with Claude and GPT)
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if code_block_match:
            json_text = code_block_match.group(1).strip()
            try:
                json.loads(json_text)  # Validate
                self.logger.debug("Successfully extracted JSON from code block")
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found code block but content isn't valid JSON")

        # First attempt: Look for JSON array pattern with action_id
        array_pattern = r'\[\s*\{\s*"action_id"\s*:.*?\}\s*\]'
        array_match = re.search(array_pattern, text, re.DOTALL)
        if array_match:
            json_text = array_match.group(0)
            try:
                json.loads(json_text)  # Validate
                self.logger.debug(f"Successfully extracted JSON array with action_id")
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found array with action_id but content isn't valid JSON")

        # Second attempt: Look for any JSON array
        array_match = re.search(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL)
        if array_match:
            json_text = array_match.group(0)
            try:
                json.loads(json_text)  # Validate
                self.logger.debug(f"Successfully extracted general JSON array")
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found array brackets but content isn't valid JSON")

        # Third attempt: Look for JSON object pattern and wrap it
        object_match = re.search(r'\{\s*".*?"\s*:.*?\}', text, re.DOTALL)
        if object_match:
            json_text = object_match.group(0)
            try:
                json.loads(json_text)  # Validate
                # Wrap single object in an array for consistency
                self.logger.debug(f"Found JSON object, wrapping in array")
                return f"[{json_text}]"
            except json.JSONDecodeError:
                self.logger.warning("Found object braces but content isn't valid JSON")

        # Fourth attempt: Try to repair JSON in the full content
        self.logger.debug("Attempting to fix and extract JSON array")
        start_idx = text.find('[')
        end_idx = text.rfind(']')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = text[start_idx:end_idx + 1]
            # Fix common JSON issues
            fixed_json = repair_json(json_text)
            if fixed_json:
                try:
                    json.loads(fixed_json)  # Validate
                    self.logger.debug(f"Successfully repaired JSON array")
                    return fixed_json
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse fixed JSON array")

        # Fifth attempt: Extract action_id values and construct a valid array
        self.logger.warning("Attempting to reconstruct JSON from fragments")
        actions = extract_structured_content(text)
        if actions:
            self.logger.debug(f"Reconstructed JSON array from fragments")
            return json.dumps(actions)
            
        # Last resort: Look for any mentions of action IDs in the text
        action_id_pattern = r'action_id\s*[:=]?\s*["\'`]?(\d+)["\'`]?'
        action_id_matches = re.findall(action_id_pattern, text, re.IGNORECASE)
        
        if action_id_matches:
            self.logger.warning(f"Found raw action IDs in text: {action_id_matches}")
            actions = []
            for action_id in action_id_matches:
                actions.append({
                    "action_id": action_id,
                    "params": {},
                    "explanation": f"Extracted action ID {action_id} from text"
                })
            return json.dumps(actions)

        # If all attempts fail, raise the exception
        raise ValueError("No valid JSON found in response")

    def parse_actions(self, response: str,
                      available_action_ids: Optional[List[str]] = None,
                      single_action_mode: bool = False) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parse actions from an LLM response.

        Args:
            response: LLM response text
            available_action_ids: List of valid action IDs (optional)
            single_action_mode: Whether to enforce single action mode

        Returns:
            Tuple of (actions, errors)
        """
        errors = []

        try:
            # Extract JSON from the response
            json_text = self.extract_json(response)

            # Parse the JSON
            actions = json.loads(json_text)

            # Validate the actions
            return ResponseValidator.validate_action_id_format(
                actions, available_action_ids, single_action_mode)

        except ValueError as e:
            errors.append(f"Failed to extract JSON: {str(e)}")
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            errors.append(f"Unexpected error parsing response: {str(e)}")

        return [], errors

    def try_repair_response(self, response: str) -> Optional[str]:
        """
        Try multiple approaches to repair a malformed response.
        Used as a fallback when normal parsing fails.

        Args:
            response: The malformed response text

        Returns:
            Repaired JSON string or None if unrepairable
        """
        self.logger.debug("Attempting to repair malformed response")

        # Attempt to extract using specialized heuristics
        actions = extract_structured_content(response)
        if actions:
            self.logger.debug(f"Successfully extracted {len(actions)} actions using heuristics")
            return json.dumps(actions)

        # Look for common patterns that indicate actions
        # Example: Look for text that resembles action ID and explanation pairs
        action_pattern = r'(?:action|action_id)[^0-9]*([0-9]+)[^\n]*?([^\n]*?(?:click|scroll|set text|tap)[^\n]*)'
        matches = re.findall(action_pattern, response, re.IGNORECASE)

        if matches:
            actions = []
            for action_id, explanation in matches:
                actions.append({
                    "action_id": action_id.strip(),
                    "params": {},
                    "explanation": explanation.strip()
                })

            self.logger.debug(f"Extracted {len(actions)} actions using pattern matching")
            return json.dumps(actions)

        return None
