# rvandroid/llm/response_parser.py
"""
Module for parsing and validating LLM responses.
Provides robust JSON extraction and validation functionality.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple

from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.json_helpers import (
    repair_json,
    extract_structured_content
)
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ResponseValidator:
    """
    Validates the structure and content of LLM responses.
    Ensures responses adhere to the unified format with an "actions" array.
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
    Supports the unified response format with an "actions" array.
    """

    def __init__(self):
        """Initialize the response parser."""
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.response_parser",
            {CONTEXT_COMPONENT: "ResponseParser"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

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

        # Look for JSON object pattern - modified to look for objects containing "actions"
        actions_object_pattern = r'\{\s*"actions"\s*:\s*\[.*?\]\s*\}'
        actions_match = re.search(actions_object_pattern, text, re.DOTALL)
        if actions_match:
            json_text = actions_match.group(0)
            try:
                json.loads(json_text)  # Validate
                self.logger.debug(f"Successfully extracted JSON with actions array")
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found actions object but content isn't valid JSON")

        # Look for batch action format with pattern_type
        batch_pattern = r'\{\s*"pattern_type"\s*:.*?"actions"\s*:\s*\[.*?\]\s*\}'
        batch_match = re.search(batch_pattern, text, re.DOTALL)
        if batch_match:
            json_text = batch_match.group(0)
            try:
                json.loads(json_text)  # Validate
                self.logger.debug(f"Successfully extracted batch action JSON")
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found batch pattern but content isn't valid JSON")

        # First attempt: Look for JSON array pattern with action_id
        array_pattern = r'\[\s*\{\s*"action_id"\s*:.*?\}\s*\]'
        array_match = re.search(array_pattern, text, re.DOTALL)
        if array_match:
            json_text = array_match.group(0)
            try:
                # Parse to validate
                actions = json.loads(json_text)
                # Convert legacy format to new format
                actions_obj = {"actions": actions}
                self.logger.debug(f"Successfully extracted JSON array with action_id and converted to new format")
                return json.dumps(actions_obj)
            except json.JSONDecodeError:
                self.logger.warning("Found array with action_id but content isn't valid JSON")

        # Second attempt: Look for any JSON array
        array_match = re.search(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL)
        if array_match:
            json_text = array_match.group(0)
            try:
                actions = json.loads(json_text)
                # Convert to new format
                actions_obj = {"actions": actions}
                self.logger.debug(f"Successfully extracted general JSON array and converted to new format")
                return json.dumps(actions_obj)
            except json.JSONDecodeError:
                self.logger.warning("Found array brackets but content isn't valid JSON")

        # Third attempt: Look for JSON object pattern for a single action and wrap it
        object_match = re.search(r'\{\s*"action_id"\s*:.*?\}', text, re.DOTALL)
        if object_match:
            json_text = object_match.group(0)
            try:
                action = json.loads(json_text)  # Validate
                # Wrap single object in the new format
                actions_obj = {"actions": [action]}
                self.logger.debug(f"Found single action object, wrapping in new format")
                return json.dumps(actions_obj)
            except json.JSONDecodeError:
                self.logger.warning("Found object with action_id but content isn't valid JSON")

        # Fourth attempt: Try to repair JSON in the full content
        self.logger.debug("Attempting to fix and extract JSON object")
        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = text[start_idx:end_idx + 1]
            # Fix common JSON issues
            fixed_json = repair_json(json_text)
            if fixed_json:
                try:
                    json_obj = json.loads(fixed_json)  # Validate

                    # Check if it's already in the new format
                    if "actions" in json_obj:
                        self.logger.debug(f"Successfully repaired JSON with actions array")
                        return fixed_json

                    # If it's a single action, wrap it
                    if "action_id" in json_obj:
                        actions_obj = {"actions": [json_obj]}
                        self.logger.debug(f"Successfully repaired single action JSON and converted to new format")
                        return json.dumps(actions_obj)

                    # If it's neither, it might be some other JSON
                    self.logger.warning("Repaired JSON does not match expected formats")
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse fixed JSON")

        # Fifth attempt: Extract action_id values and construct a valid array
        self.logger.warning("Attempting to reconstruct JSON from fragments")
        actions = extract_structured_content(text)
        if actions:
            if isinstance(actions, list) and len(actions) > 0 and "action_id" in actions[0]:
                # We have a list of actions, put it in the new format
                actions_obj = {"actions": actions}
                self.logger.debug(f"Reconstructed JSON array from fragments and converted to new format")
                return json.dumps(actions_obj)

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
            actions_obj = {"actions": actions}
            return json.dumps(actions_obj)

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
            parsed_data = json.loads(json_text)

            # Extract actions based on format
            if "actions" in parsed_data and isinstance(parsed_data["actions"], list):
                actions = parsed_data["actions"]
            else:
                # Legacy format or unexpected format
                self.logger.warning("Response doesn't contain 'actions' array, attempting to adapt")
                if "action_id" in parsed_data:
                    # Single action in legacy format
                    actions = [parsed_data]
                else:
                    # Unknown format
                    errors.append("Unexpected response format: missing 'actions' array")
                    return [], errors

            # Validate the actions
            return ResponseValidator.validate_action_id_format(
                actions, available_action_ids, single_action_mode)

        except ValueError as e:
            errors.append(f"Failed to extract JSON: {str(e)}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ResponseParser",
                    "function": "parse_actions",
                    "response_length": len(response) if response else 0
                }
            )
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON format: {str(e)}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ResponseParser",
                    "function": "parse_actions",
                    "json_error": str(e)
                }
            )
        except Exception as e:
            errors.append(f"Unexpected error parsing response: {str(e)}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ResponseParser",
                    "function": "parse_actions"
                }
            )

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
            if isinstance(actions, list) and len(actions) > 0 and "action_id" in actions[0]:
                # We have a list of actions, put it in the new format
                actions_obj = {"actions": actions}
                self.logger.debug(f"Successfully extracted {len(actions)} actions using heuristics")
                return json.dumps(actions_obj)

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
            actions_obj = {"actions": actions}
            return json.dumps(actions_obj)

        # Look for batch action format
        batch_pattern = r'pattern_type["\s:]*([a-z]+)'
        pattern_match = re.search(batch_pattern, response)

        if pattern_match:
            pattern_type = pattern_match.group(1).strip()
            # Extract action IDs
            id_matches = re.findall(r'action_id["\s:]*([0-9]+)', response)

            if id_matches:
                actions = []
                for action_id in id_matches:
                    actions.append({
                        "action_id": action_id.strip(),
                        "params": {},
                        "explanation": f"Action extracted from pattern {pattern_type}"
                    })

                batch_obj = {
                    "pattern_type": pattern_type,
                    "actions": actions,
                    "batch_explanation": f"Reconstructed batch with pattern {pattern_type}"
                }

                self.logger.debug(f"Reconstructed batch with {len(actions)} actions")
                return json.dumps(batch_obj)

        return None
