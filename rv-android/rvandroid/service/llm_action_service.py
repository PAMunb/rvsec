import json
import logging
from typing import Dict, List, Any, Optional

from rvandroid.config.component_config import ComponentConfig
from rvandroid.llm.llm import LanguageModel
from rvandroid.llm.llm_config import LLMConfiguration
from rvandroid.llm.model_factory import ModelFactory
from rvandroid.llm.prompt.prompt_strategy_basic_001 import BasicPromptStrategy001
from rvandroid.llm.prompt.prompt_strategy_factory import PromptStrategyFactory
from rvandroid.llm.prompt.single_action_prompt_strategy import SingleActionPromptStrategy
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.screen.parser_factory import ParserType, ParserFactory
from rvandroid.llm.huggingface_llm import HuggingFaceLLM

logger = logging.getLogger(__name__)


class LLMActionService:
    """
    Service that processes application state, generates prompts, sends them to LLM,
    and returns suggested actions.
    """

    def __init__(
            self,
            static_data: Optional[StaticAnalysisData] = None,
            model_type: str = HuggingFaceLLM.NAME,
            model_name: str = HuggingFaceLLM.LLAMA,
            strategy_type: str = "basic",
            parser_type: ParserType = ParserType.DROIDBOT,
            config: Optional[LLMConfiguration] = None,
            component_config: Optional[ComponentConfig] = None,
            **model_kwargs
    ):
        """
        Initialize the LLM action service.

        Args:
            static_data: Static analysis data for the application (optional)
            model_type: Type of model to use
            model_name: Name of the model
            strategy_type: Type of prompt strategy to use
            parser_type: Type of parser to use
            config: LLMConfiguration instance (overrides other parameters if provided)
            component_config: ComponentConfig for customizing components (optional)
            **model_kwargs: Additional arguments for the model constructor
        """
        self.static_data = static_data
        self.component_config = component_config

        # Use config if provided, otherwise use parameters
        if config:
            self.model_type = config.get_model_type()
            self.model_name = config.get_model_name()
            self.strategy_type = config.get_strategy_type()
            self.parser_type = config.get_parser_type()
            self.model_kwargs = config.get_model_kwargs()
            self.max_tokens = config.get_max_tokens()
        else:
            self.model_type = model_type
            self.model_name = model_name
            self.strategy_type = strategy_type
            self.parser_type = parser_type
            self.model_kwargs = model_kwargs
            self.max_tokens = model_kwargs.pop("max_tokens", 800)

        # Set up prompt strategy with custom component config if provided
        if self.component_config:
            self.prompt_strategy = PromptStrategyFactory.create(
                self.strategy_type, self.static_data, parser_type, self.component_config)
        else:
            parser = ParserFactory.create(parser_type)
            self.prompt_strategy = PromptStrategyFactory.create(
                self.strategy_type, self.static_data, parser)

        # Initialize logger but defer LLM initialization until needed
        self.llm: Optional[LanguageModel] = None
        self.logger = logger

        self.logger.info(f"Initialized LLM Action Service with model_type={self.model_type}, "
                         f"model_name={self.model_name}, strategy_type={self.strategy_type}, "
                         f"parser_type={self.parser_type}")

    def _get_llm(self) -> LanguageModel:
        """
        Get (or initialize) the LLM instance.

        Returns:
            LanguageModel instance

        Raises:
            RuntimeError: If LLM initialization fails
        """
        if not self.llm:
            self.logger.info(f"Initializing {self.model_type} LLM with model: {self.model_name}")
            try:
                self.llm = ModelFactory.create(
                    self.model_type,
                    self.model_name,
                    **self.model_kwargs
                )
                self.logger.info(f"Successfully initialized {self.model_type} model")
            except Exception as e:
                self.logger.error(f"Failed to initialize LLM: {e}", exc_info=True)
                raise RuntimeError(f"Could not initialize {self.model_type} model: {str(e)}")

        return self.llm

    # Changes to LLMActionService.process_state method
    def process_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process the current application state and return suggested actions.

        Args:
            state: Application state dictionary

        Returns:
            List of action dictionaries

        Raises:
            Exception: If processing fails
        """
        self.logger.info("Processing application state")

        try:
            # Enhance action history format if present
            if "action_history" in state:
                enhanced_history = []
                for action in state.get("action_history", []):
                    # Check if the action is already in the enhanced format
                    if isinstance(action, str) and not action.startswith("[Action ID:"):
                        # Convert to enhanced format
                        if isinstance(action, dict):
                            # If it's a dictionary, extract details
                            action_id = action.get("action_id", "unknown")
                            action_type = action.get("action_type", "unknown")
                            target = action.get("target", "unknown")
                            params = action.get("params", {})
                            explanation = action.get("explanation", "")

                            # Format parameters in a more readable way
                            params_str = ""
                            if params:
                                if "text" in params:
                                    params_str = f" with text '{params['text']}'"
                                elif "direction" in params:
                                    params_str = f" {params['direction']}"

                            # Create enhanced description with form context
                            if action_type == "click":
                                # Check if this appears to be a dropdown/spinner
                                if "spinner" in target.lower() or "dropdown" in target.lower():
                                    enhanced_action = f"[Action ID: {action_id}] CLICKED ON DROPDOWN '{target}'{params_str} - {explanation}"
                                # Check if this might be a submit button
                                elif any(keyword in target.lower() for keyword in
                                         ["submit", "login", "save", "apply", "ok", "next", "continue",
                                          "generate", "create", "send", "search", "encrypt", "decrypt"]):
                                    enhanced_action = f"[Action ID: {action_id}] SUBMITTED FORM by clicking '{target}'{params_str} - {explanation}"
                                else:
                                    enhanced_action = f"[Action ID: {action_id}] CLICKED on '{target}'{params_str} - {explanation}"
                            elif action_type == "set_text":
                                enhanced_action = f"[Action ID: {action_id}] FILLED text field '{target}'{params_str} - {explanation}"
                            elif action_type == "scroll_up" or action_type == "scroll_down":
                                if "spinner" in target.lower() or "dropdown" in target.lower():
                                    enhanced_action = f"[Action ID: {action_id}] SCROLLED {params_str} in dropdown '{target}' - {explanation}"
                                else:
                                    enhanced_action = f"[Action ID: {action_id}] SCROLLED {params_str} on '{target}' - {explanation}"
                            else:
                                enhanced_action = f"[Action ID: {action_id}] {action_type.upper()} on '{target}'{params_str} - {explanation}"

                            enhanced_history.append(enhanced_action)
                        else:
                            # If it's already a string but not enhanced, keep as is
                            enhanced_history.append(action)
                    else:
                        # Already in enhanced format or other format, keep as is
                        enhanced_history.append(action)

                # Update the history in the state
                state["action_history"] = enhanced_history

            # Generate prompts using the selected strategy
            messages = self.prompt_strategy.generate_prompts(state)

            self.logger.debug(f"System prompt: {messages[0]['content'][:200]}...")
            self.logger.debug(f"User prompt: {messages[1]['content'][:200]}...")

            # Call the LLM with the generated prompts
            llm = self._get_llm()
            response = llm.generate(messages, max_new_tokens=self.max_tokens)

            self.logger.debug(f"LLM response: {response[:200]}...")

            # Parse the response
            json_response = self._extract_json(response)
            action_data = json.loads(json_response)

            # Process actions based on the prompt strategy used
            if isinstance(self.prompt_strategy, BasicPromptStrategy001) or isinstance(self.prompt_strategy,
                                                                                      SingleActionPromptStrategy):
                # Handle action_id based format
                validated_actions = self._process_action_id_format(action_data, state)
            else:
                # Handle standard action_type format
                validated_actions = self._validate_actions(action_data)

            # For SingleActionPromptStrategy, add the action to the enhanced history
            if isinstance(self.prompt_strategy, SingleActionPromptStrategy) and validated_actions:
                action = validated_actions[0]
                action_id = action_data[0].get("action_id", "unknown") if action_data and len(
                    action_data) > 0 else "unknown"
                explanation = action_data[0].get("explanation", "") if action_data and len(action_data) > 0 else ""

                # Create enhanced description for the history
                action_type = action.get("action_type", "unknown")
                target = action.get("target", "unknown")
                params = action.get("params", {})

                # Format parameters in a more readable way
                params_str = ""
                if params:
                    if "text" in params:
                        params_str = f" with text '{params['text']}'"
                    elif "direction" in params:
                        params_str = f" {params['direction']}"

                # Create enhanced description with form context
                if action_type == "click":
                    # Check if this appears to be a dropdown/spinner
                    if "spinner" in target.lower() or "dropdown" in target.lower():
                        enhanced_action = f"[Action ID: {action_id}] CLICKED ON DROPDOWN '{target}'{params_str} - {explanation}"
                    # Check if this might be a submit button
                    elif any(keyword in target.lower() for keyword in
                             ["submit", "login", "save", "apply", "ok", "next", "continue",
                              "generate", "create", "send", "search", "encrypt", "decrypt"]):
                        enhanced_action = f"[Action ID: {action_id}] SUBMITTED FORM by clicking '{target}'{params_str} - {explanation}"
                    else:
                        enhanced_action = f"[Action ID: {action_id}] CLICKED on '{target}'{params_str} - {explanation}"
                elif action_type == "set_text":
                    enhanced_action = f"[Action ID: {action_id}] FILLED text field '{target}'{params_str} - {explanation}"
                elif action_type == "scroll_up" or action_type == "scroll_down":
                    if "spinner" in target.lower() or "dropdown" in target.lower():
                        enhanced_action = f"[Action ID: {action_id}] SCROLLED {params_str} in dropdown '{target}' - {explanation}"
                    else:
                        enhanced_action = f"[Action ID: {action_id}] SCROLLED {params_str} on '{target}' - {explanation}"
                else:
                    enhanced_action = f"[Action ID: {action_id}] {action_type.upper()} on '{target}'{params_str} - {explanation}"

                # Update history in state for next iteration
                if "action_history" not in state:
                    state["action_history"] = []
                state["action_history"].append(enhanced_action)

            self.logger.info(f"Successfully processed state and generated {len(validated_actions)} actions")

            print(f"\n******** User prompt:\n{messages[1]['content']}...")
            print(f"\n******** LLM response:\n{response}...")

            return validated_actions

        except Exception as e:
            self.logger.error(f"Error processing state: {e}", exc_info=True)
            return self._generate_fallback_actions(state)

    def _process_action_id_format(self, llm_actions: List[Dict[str, Any]], state: Dict[str, Any]) -> List[
        Dict[str, Any]]:
        """
        Process actions in action_id format returned by BasicPromptStrategy001 or SingleActionPromptStrategy.
        With improved error handling and coordinate extraction.

        Args:
            llm_actions: Actions from LLM with action_id format
            state: Current application state

        Returns:
            List of actions in droidbot format
        """
        if not isinstance(llm_actions, list):
            self.logger.warning(f"Expected list of actions but got: {type(llm_actions)}")
            return self._generate_fallback_actions(state)

        # Safety check for empty action list
        if not llm_actions:
            self.logger.warning("Received empty action list from LLM")
            return self._generate_fallback_actions(state)

        # Get screen description to access available actions
        try:
            screen_description = self.prompt_strategy.parser.parse(state, self.static_data)
            available_actions = {
                str(action.id): action
                for item in screen_description.items
                for action in item.actions
            }
            print(f"***** Available actions: {available_actions}")

            # Safety check - if no actions available, generate fallbacks
            if not available_actions:
                self.logger.warning("No available actions found in screen description")
                return self._generate_fallback_actions(state)

        except Exception as e:
            self.logger.error(f"Error parsing state: {e}", exc_info=True)
            return self._generate_fallback_actions(state)

        droidbot_actions = []

        for action_data in llm_actions:
            try:
                # Validate action data format
                if not isinstance(action_data, dict):
                    self.logger.warning(f"Invalid action format: {action_data}")
                    continue

                # Check if action_id is present, try to handle alternative formats
                action_id = None
                if "action_id" in action_data:
                    action_id = str(action_data["action_id"])
                elif "id" in action_data:
                    # Alternative key that might be used
                    action_id = str(action_data["id"])
                elif "actionId" in action_data:
                    # Alternative key that might be used
                    action_id = str(action_data["actionId"])

                if not action_id:
                    self.logger.warning(f"No action_id found in: {action_data}")
                    continue

                params = action_data.get("params", {})
                explanation = action_data.get("explanation", "")

                # Find corresponding ItemAction
                if action_id not in available_actions:
                    self.logger.warning(f"Unknown action_id: {action_id}")
                    continue

                item_action = available_actions[action_id]

                # Extract action type from the item_action text
                action_type = self._extract_action_type(item_action.text)

                # Extract view data for this action
                view_data = None
                for item in screen_description.items:
                    if any(action.id == int(action_id) for action in item.actions):
                        view_data = item.view
                        break

                # Get coordinates - try multiple methods to ensure we have them
                coordinates = None

                # Method 1: Use coordinates from ItemAction if available
                if hasattr(item_action, 'coordinates') and item_action.coordinates:
                    coordinates = item_action.coordinates

                # Method 2: Try to extract from target_view if available
                if not coordinates and hasattr(item_action, 'target_view') and item_action.target_view:
                    bounds = item_action.target_view.get("bounds")
                    if bounds and len(bounds) == 2:
                        x = (bounds[0][0] + bounds[1][0]) // 2
                        y = (bounds[0][1] + bounds[1][1]) // 2
                        coordinates = (x, y)

                # Method 3: Try to extract from the view_data if available
                if not coordinates and view_data:
                    bounds = view_data.get("bounds")
                    if bounds and len(bounds) == 2:
                        x = (bounds[0][0] + bounds[1][0]) // 2
                        y = (bounds[0][1] + bounds[1][1]) // 2
                        coordinates = (x, y)

                # Method 4: If target is a resource ID, try to find it in the view tree
                if not coordinates and isinstance(item_action.target_view,
                                                  dict) and "resource_id" in item_action.target_view:
                    resource_id = item_action.target_view["resource_id"]
                    coordinates = self._find_coordinates_for_resource_id(state.get("view_tree", {}), resource_id)

                # Method 5: Try to extract from the target if it's in "x y" format
                target = self._get_target(item_action, state)
                if not coordinates and isinstance(target, str) and " " in target:
                    parts = target.split()
                    if len(parts) == 2 and all(part.isdigit() for part in parts):
                        x, y = int(parts[0]), int(parts[1])
                        coordinates = (x, y)

                # Create droidbot action format
                droidbot_action = {
                    "action_type": action_type,
                    "target": target,
                    "params": self._process_params(action_type, params),
                    "explanation": explanation
                }

                # Add coordinates to the action if we found them
                if coordinates:
                    droidbot_action["coordinates"] = coordinates
                    self.logger.info(f"Added coordinates {coordinates} to action")
                else:
                    self.logger.warning(f"Could not find coordinates for action: {action_id}")
                    # For UI elements without coordinates, use a fallback method
                    if action_type != "key_event":  # Key events don't need coordinates
                        # Try one more time with the state's view tree if available
                        if "view_tree" in state:
                            if isinstance(target, str) and ":" in target:  # Looks like a resource ID
                                coordinates = self._find_coordinates_for_resource_id(state["view_tree"], target)
                                if coordinates:
                                    droidbot_action["coordinates"] = coordinates
                                    self.logger.info(f"Found coordinates {coordinates} from view tree")

                print(f"***** droidbot_action={droidbot_action}")

                droidbot_actions.append(droidbot_action)
            except Exception as e:
                self.logger.error(f"Error processing action data {action_data}: {e}", exc_info=True)
                continue

        if not droidbot_actions:
            self.logger.warning("Failed to process any actions from LLM response")
            return self._generate_fallback_actions(state)

        return droidbot_actions

    def _find_coordinates_for_resource_id(self, view_tree: Dict[str, Any], resource_id: str) -> Optional[tuple]:
        """
        Recursively search the view tree for a view with the given resource_id and return its coordinates.

        Args:
            view_tree: The view tree to search
            resource_id: The resource_id to look for

        Returns:
            Tuple of (x, y) coordinates or None if not found
        """
        if not view_tree:
            return None

        # Check if this is the view we're looking for
        if view_tree.get("resource_id") == resource_id:
            bounds = view_tree.get("bounds")
            if bounds and len(bounds) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                return (x, y)

        # Also check if it has the same ID part (after :id/)
        if ":" in resource_id and view_tree.get("resource_id", ""):
            id_part = resource_id.split(":")[-1]
            view_id_part = view_tree.get("resource_id", "").split(":")[-1]
            if id_part == view_id_part:
                bounds = view_tree.get("bounds")
                if bounds and len(bounds) == 2:
                    x = (bounds[0][0] + bounds[1][0]) // 2
                    y = (bounds[0][1] + bounds[1][1]) // 2
                    return (x, y)

        # Check children
        for child in view_tree.get("children", []):
            coords = self._find_coordinates_for_resource_id(child, resource_id)
            if coords:
                return coords

        return None

    def _extract_action_type(self, action_text: str) -> str:
        """
        Extract the action type from the action text description.
        
        Args:
            action_text: Text description of the action
            
        Returns:
            Action type string for droidbot
        """
        if action_text.startswith("CLICK"):
            return "click"
        elif action_text.startswith("LONG_CLICK"):
            return "long_click"
        elif action_text.startswith("SCROLL"):
            # Extract direction if present
            if "UP" in action_text:
                return "scroll_up"
            elif "DOWN" in action_text:
                return "scroll_down"
            elif "LEFT" in action_text:
                return "scroll_left"
            elif "RIGHT" in action_text:
                return "scroll_right"
            return "scroll"
        elif action_text.startswith("SET_TEXT"):
            return "set_text"
        elif action_text.startswith("CHECK") or action_text.startswith("UNCHECK"):
            return "click"  # Checkbox actions are clicks
        elif action_text.startswith("BACK"):
            return "key_event"
        return "unknown"

    def _get_target(self, item_action: 'ItemAction', state: Dict[str, Any]) -> str:
        """
        Get the target for an action from the associated view data.

        Args:
            item_action: The ItemAction being processed
            state: Current application state

        Returns:
            Target string (resource_id or coordinates)
        """
        # Get the view data associated with this action
        view_data = None
        for item in self.prompt_strategy.parser.parse(state, self.static_data).items:
            if item_action in item.actions:
                view_data = item.view
                break

        if not view_data:
            return ""

        # Always calculate coordinates when bounds are available
        coordinates = None
        if "bounds" in view_data:
            bounds = view_data["bounds"]
            if bounds and len(bounds) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                coordinates = (x, y)
                item_action.coordinates = coordinates

        # Set coordinates explicitly on the action
        item_action.coordinates = coordinates

        # Try resource_id first
        if "resource_id" in view_data:
            return view_data["resource_id"]

        # Fall back to coordinates if bounds are available
        if coordinates:
            x, y = coordinates
            return f"{x} {y}"

        return ""

    def _process_params(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and validate parameters for an action.
        
        Args:
            action_type: Type of action
            params: Parameters from LLM
            
        Returns:
            Processed parameters dictionary
        """
        if action_type == "set_text" and "text" not in params:
            # Default text if not provided
            params["text"] = "test input"

        if action_type == "key_event" and "name" not in params:
            # Default key event name
            params["name"] = "BACK"

        return params

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
        # Look for JSON array
        start_idx = text.find('[')
        end_idx = text.rfind(']')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = text[start_idx:end_idx + 1]
            # Validate that it can be parsed
            try:
                json.loads(json_text)
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found array brackets but content isn't valid JSON")

        # Look for JSON object
        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = text[start_idx:end_idx + 1]
            try:
                json.loads(json_text)
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found object braces but content isn't valid JSON")

        # If we get here, we need to do more aggressive fixing
        # Try to fix common JSON issues
        fixed_text = self._fix_json_text(text)
        if fixed_text:
            return fixed_text

        raise ValueError("No valid JSON found in response")

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
        # Look for JSON array
        start_idx = text.find('[')
        end_idx = text.rfind(']')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = text[start_idx:end_idx + 1]
            # Validate that it can be parsed
            try:
                json.loads(json_text)
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found array brackets but content isn't valid JSON")

        # Look for JSON object
        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = text[start_idx:end_idx + 1]
            try:
                json.loads(json_text)
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found object braces but content isn't valid JSON")

        # If we get here, we need to do more aggressive fixing
        # Try to fix common JSON issues
        fixed_text = self._fix_json_text(text)
        if fixed_text:
            return fixed_text

        raise ValueError("No valid JSON found in response")

    def _fix_json_text(self, text: str) -> str:
        """
        Attempt to fix common JSON formatting issues.

        Args:
            text: Text containing malformed JSON

        Returns:
            Fixed JSON string or empty string if unfixable
        """
        import re

        # Look for JSON-like content
        match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if match:
            json_candidate = match.group(0)

            # Try to parse it
            try:
                json.loads(json_candidate)
                return json_candidate
            except json.JSONDecodeError:
                # Still invalid, but we found something JSON-like
                pass

        # More aggressive: extract anything between [ and ] and try to fix it
        if '[' in text and ']' in text:
            start = text.find('[')
            end = text.rfind(']')
            if start < end:
                json_candidate = text[start:end + 1]

                # Common fixes:
                # Fix single quotes to double quotes
                json_candidate = json_candidate.replace("'", '"')
                # Fix unquoted keys
                json_candidate = re.sub(r'(\w+):', r'"\1":', json_candidate)

                try:
                    json.loads(json_candidate)
                    return json_candidate
                except json.JSONDecodeError:
                    pass

        return ""

    def _validate_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and clean up actions returned by the LLM.

        Args:
            actions: List of action dictionaries

        Returns:
            Validated list of action dictionaries
        """
        valid_actions = []

        # Ensure actions is a list
        if not isinstance(actions, list):
            self.logger.warning(f"Expected list of actions but got: {type(actions)}")
            if isinstance(actions, dict):
                # Single action as a dict - convert to list
                actions = [actions]
            else:
                return valid_actions
        valid_action_types = {'click', 'long_click', 'scroll', 'set_text', 'key_event'}

        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                self.logger.warning(f"Invalid action format at index {i}: {action}")
                continue

            # Check for required fields
            if 'action_type' not in action or 'target' not in action:
                self.logger.warning(f"Invalid action missing required fields at index {i}: {action}")
                continue

            # Normalize action type
            action_type = action['action_type'].lower()
            if action_type not in valid_action_types:
                self.logger.warning(f"Invalid action type at index {i}: {action_type}")
                continue

            # Ensure params is a dictionary
            if 'params' not in action or not isinstance(action['params'], dict):
                action['params'] = {}

            # Add explanation if missing
            if 'explanation' not in action or not action['explanation']:
                action['explanation'] = f"Executing {action_type} on {action['target']}"

            # Add validated action
            valid_actions.append({
                'action_type': action_type,
                'target': action['target'],
                'params': action['params'],
                'explanation': action.get('explanation', '')
            })

        return valid_actions

    def _generate_fallback_actions(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate fallback actions when LLM response parsing fails.

        Args:
            state: Application state dictionary

        Returns:
            List of fallback action dictionaries
        """
        self.logger.info("Generating fallback actions")

        fallback_actions = []

        # Try to find some interactive elements
        if 'view_tree' in state:
            self._extract_clickable_elements(state['view_tree'], fallback_actions)

        # If no elements found, add a random scroll action
        if not fallback_actions:
            fallback_actions.append({
                'action_type': 'scroll',
                'target': '',
                'params': {'direction': 'DOWN'},
                'explanation': 'Fallback scroll action'
            })

        return fallback_actions

    def _extract_clickable_elements(self, view: Dict[str, Any], actions: List[Dict[str, Any]], max_elements: int = 3):
        """
        Extract clickable elements from view tree for fallback actions.

        Args:
            view: View tree dictionary
            actions: List to append actions to
            max_elements: Maximum number of elements to extract
        """
        # Check if this view is clickable
        if (len(actions) < max_elements and
                view.get('clickable', False) and
                view.get('enabled', True) and
                view.get('visible', True)):

            target = view.get('resource_id', '')
            if not target and 'bounds' in view:
                # If no resource_id, use center of bounds
                bounds = view['bounds']
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                target = f"{x} {y}"

            if target:
                actions.append({
                    'action_type': 'click',
                    'target': target,
                    'params': {},
                    'explanation': 'Fallback click on visible element'
                })

        # Recursively process children
        for child in view.get('children', []):
            if len(actions) >= max_elements:
                break
            self._extract_clickable_elements(child, actions, max_elements)

    def cleanup(self):
        """
        Clean up resources used by the service.
        """
        if self.llm:
            try:
                self.llm.clean()
                self.llm = None
                self.logger.info("Cleaned up LLM resources")
            except Exception as e:
                self.logger.warning(f"Error cleaning up LLM: {e}")
