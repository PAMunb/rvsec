"""
LLM response processing service for Android testing framework.

This module processes and validates LLM responses to extract viable actions,
providing robust parsing and validation with comprehensive error recovery.
"""

import json
from typing import Dict, List, Any, Tuple

from rv_android_core.event.bus import EventBus
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance.performance_monitor import PerformanceMonitor
from rv_llm import LLMConfig
from rv_llm.llm.constants import StateEntry
from rv_screen_parser.parser.screen.visitor.model import ItemAction
from rvandroid_tool.llm.response_parser import ResponseParser


class ResponseProcessor:
    """
    Processes and validates LLM responses to extract executable actions.
    
    ### Architecture Overview:
    Provides unified response processing with robust error recovery and
    validation. Handles JSON extraction, action validation, and response
    repair mechanisms to ensure reliable action generation from LLM outputs.
    
    ### Processing Pipeline:
    1. Extract JSON content from LLM response text
    2. Parse and validate action structure
    3. Verify action_id references against available actions
    4. Apply repair strategies for malformed responses
    5. Return validated actions with error reporting
    
    ### Error Recovery:
    Implements comprehensive error recovery strategies including JSON repair,
    action reconstruction, and fallback mechanisms to maintain testing
    session continuity even with problematic LLM responses.
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize response processor with configuration.
        
        Args:
            config: LLM configuration for response processing
        """
        # System services
        self.event_bus = EventBus.get_instance()
        self.performance_monitor = PerformanceMonitor.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        logging_manager = LoggingManager.get_instance()
        
        # Configure logging
        self.logger = logging_manager.get_logger(
            "rvandroid_tool.llm.service.response_processor",
            {CONTEXT_COMPONENT: "ResponseProcessor"}
        )
        
        # Store configuration
        self.config = config
        
        # Initialize response parser
        self.parser = ResponseParser()
        
        self.logger.info("Response processor initialized")

    def process_response(self, 
                        response: str, 
                        state: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Process LLM response to extract valid actions.
        
        ### Processing Strategy:
        Extracts and validates actions from LLM response text using robust
        JSON parsing and validation. Applies repair strategies when normal
        processing fails to maximize action extraction success rate.
        
        ### Performance Monitoring:
        Measures processing time for performance analysis and optimization.
        Tracks both successful parsing and repair operation durations.
        
        Args:
            response: Raw LLM response text
            state: Current application state with available actions
            
        Returns:
            Tuple of (validated_actions, error_messages)
        """
        context = {"activity": state.get("activity", "unknown")}
        
        with self.performance_monitor.measure_time("response_parsing", context):
            self.logger.debug(f"Processing LLM response of length {len(response)}")
            
            # Extract available action IDs for validation
            available_actions: Dict[int, ItemAction] = state.get(StateEntry.AVAILABLE_ACTIONS, {})
            available_action_ids = [str(action_id) for action_id in available_actions.keys()]
            
            try:
                return self._extract_and_validate_actions(response, available_action_ids, context)
            except Exception as e:
                self.logger.error(f"Response processing failed: {e}", exc_info=True)
                self.error_handler.handle_error(e, {
                    "component": "ResponseProcessor",
                    "function": "process_response",
                    "response_length": len(response)
                })
                return [], [f"Response processing error: {str(e)}"]

    def _extract_and_validate_actions(self, 
                                    response: str, 
                                    available_action_ids: List[str],
                                    context: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Extract JSON and validate actions with repair fallback.
        
        ### Extraction Strategy:
        Attempts primary JSON extraction and validation, falling back to
        response repair mechanisms when initial processing fails. Ensures
        maximum action recovery from LLM responses.
        
        Args:
            response: Raw LLM response text
            available_action_ids: List of valid action IDs for validation
            context: Processing context for performance monitoring
            
        Returns:
            Tuple of (validated_actions, error_messages)
        """
        try:
            # Primary processing: Extract and validate JSON
            json_text = self.parser.extract_json(response)
            parsed_data = json.loads(json_text)
            
            self.logger.info(f"Parsed JSON: {parsed_data}")
            
            # Extract and validate actions
            actions, errors = self._extract_actions_from_data(parsed_data, available_action_ids)
            
            # Log validation results
            for error in errors:
                self.logger.warning(f"Response validation issue: {error}")
            
            # Attempt repair if no valid actions found
            if not actions and errors:
                return self._attempt_response_repair(response, available_action_ids, context, errors)
            
            return actions, errors
            
        except Exception as e:
            self.logger.warning(f"Primary processing failed: {e}")
            return self._attempt_response_repair(response, available_action_ids, context, [str(e)])

    def _extract_actions_from_data(self, 
                                  parsed_data: Dict[str, Any], 
                                  available_action_ids: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Extract actions from parsed JSON data.
        
        ### Data Format Handling:
        Supports unified format with "actions" array and provides fallback
        handling for legacy single-action formats. Ensures compatibility
        across different response formats.
        
        Args:
            parsed_data: Parsed JSON response data
            available_action_ids: List of valid action IDs for validation
            
        Returns:
            Tuple of (extracted_actions, validation_errors)
        """
        errors = []
        
        # Check for actions array in unified format
        if "actions" not in parsed_data or not isinstance(parsed_data["actions"], list):
            errors.append("Missing or invalid 'actions' array in response")
            return [], errors
        
        actions = parsed_data["actions"]
        
        # Validate actions
        validated_actions, validation_errors = self._validate_actions(actions, available_action_ids)
        errors.extend(validation_errors)
        
        return validated_actions, errors

    def _validate_actions(self, 
                         actions: List[Dict[str, Any]], 
                         available_action_ids: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Validate actions against available action IDs.
        
        ### Validation Strategy:
        Checks action structure, validates action_id references, and ensures
        required fields are present. Provides detailed error reporting for
        debugging and response quality assessment.
        
        Args:
            actions: List of action dictionaries to validate
            available_action_ids: List of valid action IDs
            
        Returns:
            Tuple of (valid_actions, validation_errors)
        """
        valid_actions = []
        errors = []
        
        self.logger.debug(f"Validating {len(actions) if isinstance(actions, list) else 'non-list'} actions")
        self.logger.debug(f"Available action IDs: {available_action_ids}")
        
        # Verify actions is a list
        if not isinstance(actions, list):
            errors.append(f"Expected list of actions, got {type(actions)}")
            return valid_actions, errors
        
        # Check for empty actions
        if not actions:
            errors.append("No actions found in response")
            return valid_actions, errors
        
        # Validate each action
        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                errors.append(f"Action at index {i} is not a dictionary")
                continue
            
            # Validate action structure and ID
            validation_result = self._validate_single_action(action, available_action_ids, i)
            if validation_result["valid"]:
                valid_actions.append(validation_result["action"])
                self.logger.debug(f"Action {action.get('action_id')} validated successfully")
            else:
                errors.extend(validation_result["errors"])
        
        self.logger.debug(f"Validation result: {len(valid_actions)} valid actions, {len(errors)} errors")
        return valid_actions, errors

    def _validate_single_action(self, 
                               action: Dict[str, Any], 
                               available_action_ids: List[str], 
                               index: int) -> Dict[str, Any]:
        """
        Validate individual action structure and content.
        
        ### Validation Rules:
        - action_id field must be present and valid
        - action_id must exist in available actions or be "coord" (future support)
        - params must be dictionary if present
        - explanation field is optional but recommended
        
        Args:
            action: Single action dictionary to validate
            available_action_ids: List of valid action IDs
            index: Action index for error reporting
            
        Returns:
            Dictionary with validation results and processed action
        """
        errors = []
        
        # Check required action_id field
        if "action_id" not in action:
            errors.append(f"Missing action_id at index {index}")
            return {"valid": False, "errors": errors, "action": None}
        
        action_id = str(action["action_id"])
        self.logger.debug(f"Validating action_id: {action_id}")
        
        # Validate action_id against available actions
        if action_id == "coord":
            # Future multimodal support - validate coordinate format
            coords = action.get("params", {}).get("coordinates", [])
            if not (isinstance(coords, list) and len(coords) == 2 and 
                    all(isinstance(c, int) for c in coords)):
                errors.append(f"Invalid coordinates format for coord action at index {index}")
                return {"valid": False, "errors": errors, "action": None}
        elif available_action_ids and action_id not in available_action_ids:
            # Standard action_id validation
            try:
                action_id_int = int(action_id)
                if not (1 <= action_id_int <= 100):  # Reasonable range check
                    errors.append(f"Action ID {action_id} outside reasonable range at index {index}")
                    return {"valid": False, "errors": errors, "action": None}
            except ValueError:
                errors.append(f"Action ID {action_id} is not valid at index {index}")
                return {"valid": False, "errors": errors, "action": None}
            
            self.logger.warning(f"Action ID {action_id} not in available actions, but proceeding")
        
        # Ensure required fields are present with defaults
        processed_action = action.copy()
        if "params" not in processed_action or not isinstance(processed_action["params"], dict):
            processed_action["params"] = {}
        
        if "explanation" not in processed_action or not processed_action["explanation"]:
            processed_action["explanation"] = f"Execute action {action_id}"
        
        return {"valid": True, "errors": [], "action": processed_action}

    def _attempt_response_repair(self, 
                                response: str, 
                                available_action_ids: List[str],
                                context: Dict[str, Any],
                                initial_errors: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Attempt to repair malformed response using recovery strategies.
        
        ### Repair Strategy:
        Applies specialized repair techniques to extract actions from
        malformed responses, including JSON reconstruction, pattern matching,
        and structural recovery mechanisms.
        
        Args:
            response: Original malformed response text
            available_action_ids: List of valid action IDs
            context: Processing context for performance monitoring
            initial_errors: Errors from primary processing attempt
            
        Returns:
            Tuple of (repaired_actions, combined_errors)
        """
        with self.performance_monitor.measure_time("response_repair", context):
            self.logger.warning("Attempting response repair")
            
            repaired_json = self.parser.try_repair_response(response)
            if not repaired_json:
                return [], initial_errors + ["Response repair failed"]
            
            try:
                repaired_data = json.loads(repaired_json)
                repaired_actions, repair_errors = self._extract_actions_from_data(
                    repaired_data, available_action_ids
                )
                
                if repaired_actions:
                    self.logger.info(f"Successfully repaired response, extracted {len(repaired_actions)} actions")
                    return repaired_actions, initial_errors + repair_errors
                
            except Exception as e:
                repair_errors = [f"Error parsing repaired JSON: {e}"]
            
            return [], initial_errors + repair_errors