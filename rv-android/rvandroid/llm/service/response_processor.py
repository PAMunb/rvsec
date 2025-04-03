# rvandroid/llm/service/response_processor.py
import json
from typing import Dict, List, Any, Optional, Tuple

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.experiment.event.bus import EventBus
from rvandroid.llm.response_parser import ResponseParser
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class ResponseProcessor:
    """
    Processes and validates LLM responses to extract viable actions.

    ### Architectural Decisions:
    - Specialized component focusing solely on response processing
    - Implements robust error handling and fallback mechanisms
    - Provides response validation and transformation capabilities
    - Separates response processing from action generation

    ### Role in the System:
    - Parses and validates LLM responses into structured actions
    - Handles malformed responses and implements recovery strategies
    - Transforms LLM outputs into standardized action formats
    - Provides detailed validation feedback for response quality
    """

    def __init__(self, config: ComponentConfigurator):
        """
        Initialize the response processor.

        Args:
            config: Component configurator for response processing configuration
        """
        # Get system services
        self.event_bus = EventBus.get_instance()
        self.performance_monitor = PerformanceMonitor.get_instance()
        logging_manager = LoggingManager.get_instance()

        # Configure logging
        self.logger = logging_manager.get_logger(
            "llm.service.response_processor",
            {CONTEXT_COMPONENT: "ResponseProcessor"}
        )

        # Store configuration
        self.config = config

        # Initialize response parser
        self.parser = ResponseParser()

        # Determine if we're using single action mode
        strategy_class = config.strategy_class
        self.single_action_mode = False
        if strategy_class:
            class_name = strategy_class.__name__
            self.single_action_mode = "SingleAction" in class_name

        self.logger.info(f"Response processor initialized (single_action_mode={self.single_action_mode})")

    def process_response(self,
                         response: str,
                         available_action_ids: List[str],
                         state: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Process LLM response to extract valid actions.

        Args:
            response: LLM response text
            available_action_ids: List of valid action IDs
            state: Current application state

        Returns:
            Tuple of (actions, errors)
        """
        context = {"activity": state.get("activity", "unknown")}

        with self.performance_monitor.measure_time("response_parsing", context):
            self.logger.debug(f"Processing LLM response of length {len(response)}")

            try:
                # Extract JSON from the response
                json_text = self._extract_json(response)

                # Parse the JSON
                actions = json.loads(json_text)

                # Validate the actions
                valid_actions, errors = self._validate_actions(
                    actions, available_action_ids, self.single_action_mode
                )

                # Log any parsing errors
                for error in errors:
                    self.logger.warning(f"Response parsing issue: {error}")

                # If no valid actions, try repair
                if not valid_actions and errors:
                    with self.performance_monitor.measure_time("response_repair", context):
                        self.logger.warning("Primary parsing failed, attempting to repair response")
                        repaired_json = self._try_repair_response(response)
                        if repaired_json:
                            try:
                                repaired_actions = json.loads(repaired_json)
                                valid_actions, repair_errors = self._validate_actions(
                                    repaired_actions, available_action_ids, self.single_action_mode
                                )
                                self.logger.info("Successfully recovered actions from repaired response")

                                # Add repair errors to original errors
                                errors.extend(repair_errors)
                            except Exception as e:
                                errors.append(f"Error parsing repaired JSON: {e}")

                return valid_actions, errors

            except Exception as e:
                self.logger.error(f"Error processing response: {e}", exc_info=True)
                return [], [f"Response processing error: {str(e)}"]

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON content from text that might contain other content.

        Args:
            text: Text potentially containing JSON

        Returns:
            Extracted JSON string

        Raises:
            ValueError: If no valid JSON can be extracted
        """
        self.logger.debug(f"Attempting to extract JSON from response of length {len(text)}")

        # Use the response parser's extraction method
        return self.parser.extract_json(text)

    def _validate_actions(self,
                          actions: List[Dict[str, Any]],
                          available_action_ids: List[str],
                          single_action_mode: bool) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Validate actions against available action IDs.

        Args:
            actions: List of action dictionaries
            available_action_ids: List of valid action IDs
            single_action_mode: Whether to enforce single action

        Returns:
            Tuple of (valid_actions, errors)
        """
        valid_actions = []
        errors = []

        # Log validation attempt
        self.logger.debug(f"Validating {len(actions) if isinstance(actions, list) else 'non-list'} action(s)")
        self.logger.debug(f"Available action IDs: {available_action_ids}")

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
            self.logger.debug(f"Validating action_id: {action_id}")
            
            if not available_action_ids:
                self.logger.warning("No available action IDs to validate against")
                # If we don't have action IDs to validate against, accept the action conditionally
                action_id_as_int = action_id
                try:
                    action_id_as_int = int(action_id)
                    if 1 <= action_id_as_int <= 10:  # A reasonable range for most screens
                        self.logger.debug(f"Conditionally accepting action_id {action_id} (no validation list)")
                        # Still valid in this case
                    else:
                        errors.append(f"Action ID {action_id} is out of reasonable range (1-10)")
                        continue
                except ValueError:
                    errors.append(f"Action ID {action_id} is not a valid number")
                    continue
            elif action_id not in available_action_ids:
                self.logger.warning(f"Action ID {action_id} not found in available actions: {available_action_ids}")
                errors.append(f"Invalid action_id: {action_id} (not in available actions)")
                continue
            else:
                self.logger.debug(f"Action ID {action_id} is valid")

            # Add default fields if missing
            if "params" not in action or not isinstance(action["params"], dict):
                action["params"] = {}

            if "explanation" not in action or not action["explanation"]:
                action["explanation"] = f"Executing action {action_id}"

            valid_actions.append(action)
            self.logger.debug(f"Added valid action with ID {action_id}")

        self.logger.debug(f"Validation result: {len(valid_actions)} valid action(s), {len(errors)} error(s)")
        return valid_actions, errors

    def _try_repair_response(self, response: str) -> Optional[str]:
        """
        Try to repair a malformed response into valid JSON.

        Args:
            response: Malformed response text

        Returns:
            Repaired JSON string or None if unrepairable
        """
        # Use the parser's repair method
        return self.parser.try_repair_response(response)
   