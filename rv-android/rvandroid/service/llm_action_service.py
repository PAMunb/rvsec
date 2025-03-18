import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.llm import LanguageModel
from rvandroid.llm.prompt.dspy_single_action_prompt_strategy import DSPySingleActionPromptStrategy
from rvandroid.llm.prompt.single_action_prompt_strategy import SingleActionPromptStrategy
from rvandroid.llm.response_parser import ResponseParser
from rvandroid.model.dynamic_wtg import DynamicTransitionGraph
from rvandroid.model.static import StaticAnalysisData

logger = logging.getLogger(__name__)


class LLMActionService:
    """
    Service that processes application state, generates prompts, sends them to LLM,
    and returns suggested actions.

    Tracks dynamic screen transitions and uses this information to improve test coverage.

    Expected LLM Response Format:
    -----------------------------
    The LLM should return a JSON array of actions with the following structure:

    ```json
    [
      {
        "action_id": "5",
        "params": {},
        "explanation": "Detailed explanation of why this action was chosen"
      }
    ]
    ```

    For actions requiring parameters (e.g., SET_TEXT), the params field should include
    the necessary values:

    ```json
    [
      {
        "action_id": "6",
        "params": {"text": "example@email.com"},
        "explanation": "Entering an email address in the field"
      }
    ]
    ```

    The service will convert these actions to the format required by DroidBot.
    """

    def __init__(
            self,
            static_data: Optional[StaticAnalysisData] = None,
            config: Optional[ComponentConfigurator] = None,
            dynamic_wtg_file: str = "dynamic_wtg.json",
            **model_kwargs
    ):
        """
        Initialize the LLM action service.

        Args:
            static_data: Static analysis data for the application (optional)
            config: ComponentConfigurator instance
            dynamic_wtg_file: File to store/load dynamic transition graph
            **model_kwargs: Additional arguments for the model constructor
        """
        self.static_data = static_data
        self.config = config
        self.dynamic_wtg_file = dynamic_wtg_file

        self.model_type = config.llm_config["type"]
        self.model_name = config.llm_config["model"]
        self.model_kwargs = model_kwargs
        self.max_tokens = model_kwargs.pop("max_tokens", 800)

        # Set up prompt strategy
        self.prompt_strategy = config.create_strategy(static_data)

        # Initialize response parser
        self.response_parser = ResponseParser()

        # Initialize session recording
        self.record_session = False  # Set to False to disable recording
        self.session_actions = []

        # Initialize logger but defer LLM initialization until needed
        self.llm: Optional[LanguageModel] = None
        self.logger = logger

        # Initialize dynamic transition graph or load from file
        saved_graph = DynamicTransitionGraph.load_from_file(dynamic_wtg_file)
        self.dynamic_wtg = saved_graph if saved_graph else DynamicTransitionGraph()

        self.logger.info(f"Initialized LLM Action Service with model_type={self.config.llm_config['type']}, "
                         f"model_name={self.config.llm_config['model']}, strategy={self.config.strategy_class}, "
                         f"parser_type={self.config.parser_class}, visitor={self.config.visitor_class}")

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
                self.llm = self.config.create_llm()
                self.logger.info(f"Successfully initialized {self.model_type} model")
            except Exception as e:
                self.logger.error(f"Failed to initialize LLM: {e}", exc_info=True)
                raise RuntimeError(f"Could not initialize {self.model_type} model: {str(e)}")

        return self.llm

    def _extract_single_action(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ensure only a single action is returned for single action strategies.
        If the LLM ignored instructions and returned multiple actions,
        this method ensures only the first (likely most important) action is kept.

        Args:
            actions: List of actions from LLM

        Returns:
            List containing just the first action
        """
        if not actions or len(actions) == 0:
            self.logger.warning("No actions found to extract single action from")
            return []

        if len(actions) > 1:
            self.logger.warning(
                f"LLM returned {len(actions)} actions despite single action requirement. Using only the first.")

        # Return just the first action in a list for consistency
        return [actions[0]]

    def process_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process the current application state to generate AI-driven actions.

        This method performs a comprehensive workflow to analyze the current application state,
        generate prompts, call a language model, parse its response, and convert actions to a
        compatible format. It includes performance monitoring, error handling, and optional
        session recording.

        Args:
            state (Dict[str, Any]): A dictionary representing the current application state,
                                    containing information about the app's package, activity,
                                    and other relevant context.

        Returns:
            List[Dict[str, Any]]: A list of action dictionaries that can be executed by
                                   the test automation system, representing suggested
                                   interactions with the application.

        Raises:
            Exception: If any critical error occurs during state processing, with fallback
                       to generating default actions.
        """
        # Get logging and performance monitoring
        from rvandroid.util.logging_manager import LoggingManager
        from rvandroid.util.performance_monitor import PerformanceMonitor

        logger = LoggingManager.get_instance().get_logger(
            "service.llm_action_service",
            {"component": "LLMActionService"}
        )
        performance_monitor = PerformanceMonitor.get_instance()

        # Add timestamp and application info for debugging
        app_package = state.get("package_name", "unknown")
        app_activity = state.get("activity", "unknown")

        context = {
            "package_name": app_package,
            "activity": app_activity
        }

        logger.info(f"Processing state for app: {app_package}, activity: {app_activity}")

        # Measure total processing time
        with performance_monitor.measure_time("state_processing_total", context):
            try:
                # Update dynamic transition graph
                with performance_monitor.measure_time("update_transitions", context):
                    self.update_dynamic_transitions(state)

                # Get transition guidance
                with performance_monitor.measure_time("get_transition_guidance", context):
                    transition_guidance = self.get_transition_guidance(app_activity)
                    # Add guidance to state for use in prompts
                    state["transition_guidance"] = transition_guidance

                # Enhance action history if present
                if "action_history" in state:
                    with performance_monitor.measure_time("enhance_action_history", context):
                        self._enhance_action_history(state)

                # Add action-specific history information
                with performance_monitor.measure_time("add_action_specific_history", context):
                    self._add_action_specific_history(state)

                # Generate prompts using the selected strategy
                with performance_monitor.measure_time("prompt_generation", context):
                    logger.debug(f"Generating prompts using {self.prompt_strategy.__class__.__name__}")
                    messages = self.prompt_strategy.generate_prompts(state)
                    logger.debug(f"System prompt length: {len(messages[0]['content'])}")
                    logger.debug(f"User prompt length: {len(messages[1]['content'])}")

                    # Record prompt length metrics
                    performance_monitor.record_metric(
                        name="prompt_length_system",
                        value=len(messages[0]['content']),
                        unit="chars",
                        context=context
                    )
                    performance_monitor.record_metric(
                        name="prompt_length_user",
                        value=len(messages[1]['content']),
                        unit="chars",
                        context=context
                    )

                # Call the LLM with the generated prompts
                with performance_monitor.measure_time("llm_call", context):
                    logger.info(f"Calling LLM model: {self.model_type}/{self.model_name}")
                    llm = self._get_llm()
                    start_time = time.time()
                    response = llm.generate(messages, max_new_tokens=self.max_tokens)
                    elapsed_time = time.time() - start_time

                    logger.info(f"LLM response received in {elapsed_time:.2f} seconds")
                    logger.debug(f"LLM response length: {len(response)}")

                    # Record response metrics
                    performance_monitor.record_metric(
                        name="llm_response_time",
                        value=elapsed_time,
                        unit="s",
                        context=context
                    )
                    performance_monitor.record_metric(
                        name="llm_response_length",
                        value=len(response),
                        unit="chars",
                        context=context
                    )

                # Parse the response and get available action IDs
                with performance_monitor.measure_time("response_parsing", context):
                    # Get available action IDs for validation
                    screen_description = self.prompt_strategy.parser.parse(state, self.static_data)
                    available_action_ids = [
                        str(action.id) for item in screen_description.items
                        for action in item.actions
                    ]

                    # Determine single action mode based on strategy type
                    single_action_mode = isinstance(self.prompt_strategy,
                                                    (SingleActionPromptStrategy, DSPySingleActionPromptStrategy))

                    # Parse the response
                    actions, errors = self.response_parser.parse_actions(
                        response,
                        available_action_ids=available_action_ids,
                        single_action_mode=single_action_mode
                    )

                    # Log any parsing errors
                    for error in errors:
                        logger.warning(f"Response parsing issue: {error}")

                    # Record parsing metrics
                    performance_monitor.record_metric(
                        name="response_parsing_errors",
                        value=len(errors),
                        context=context
                    )

                # Fall back to secondary parsing if primary fails
                if not actions and errors:
                    with performance_monitor.measure_time("response_repair", context):
                        logger.warning("Primary parsing failed, attempting to repair response")
                        repaired_json = self.response_parser.try_repair_response(response)
                        if repaired_json:
                            try:
                                actions = json.loads(repaired_json)
                                logger.info("Successfully recovered actions from repaired response")
                            except Exception as e:
                                logger.error(f"Error parsing repaired JSON: {e}")

                # Fall back to default actions if all parsing failed
                if not actions:
                    with performance_monitor.measure_time("fallback_actions", context):
                        logger.warning("Failed to extract valid actions from LLM response")
                        return self._generate_fallback_actions(state)

                logger.info(f"Successfully parsed {len(actions)} actions from LLM response")

                # Convert to DroidBot format
                with performance_monitor.measure_time("convert_to_droidbot", context):
                    droidbot_actions = self._convert_to_droidbot_format(actions, state, screen_description)

                # Record actions if enabled
                if self.record_session:
                    app_package = state.get("package_name", "unknown")
                    app_activity = state.get("activity", "unknown")
                    timestamp = datetime.now().isoformat()

                    for action in droidbot_actions:
                        # Add metadata for recording
                        recorded_action = action.copy()
                        recorded_action.update({
                            "timestamp": timestamp,
                            "package": app_package,
                            "activity": app_activity
                        })
                        self.session_actions.append(recorded_action)

                    # Save session periodically (every 20 actions)
                    if len(self.session_actions) % 20 == 0:
                        self._save_session()

                # Update the dynamic transition graph with the chosen actions
                with performance_monitor.measure_time("update_graph_with_actions", context):
                    self._update_graph_with_actions(state, droidbot_actions)

                # Save the dynamic transition graph periodically
                with performance_monitor.measure_time("save_graph", context):
                    self.save_dynamic_transition_graph()

                logger.info(f"Successfully processed state and generated {len(droidbot_actions)} actions")

                # Record success metrics
                performance_monitor.record_metric(
                    name="actions_generated",
                    value=len(droidbot_actions),
                    context=context
                )

                return droidbot_actions

            except Exception as e:
                logger.error(f"Error processing state: {e}", exc_info=True)

                # Record error metrics
                performance_monitor.record_metric(
                    name="state_processing_error",
                    value=1,
                    context={**context, "error": str(e)}
                )

                logger.info("Generating fallback actions")
                return self._generate_fallback_actions(state)

    def _save_session(self):
        """Save the current session to a file."""
        if not self.session_actions:
            return

        try:
            from rvandroid.util.session_replay import ActionReplay

            # Create session directory if needed
            session_dir = os.path.join(os.path.dirname(self.dynamic_wtg_file), "sessions")
            os.makedirs(session_dir, exist_ok=True)

            # Generate session filename
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            package_name = self.session_actions[0].get("package", "unknown")
            session_file = os.path.join(session_dir, f"session_{package_name}_{timestamp}.json")

            # Save session
            replayer = ActionReplay()
            replayer.save_session(self.session_actions, session_file)

            self.logger.info(f"Session saved to {session_file}")

        except Exception as e:
            self.logger.error(f"Error saving session: {e}")

    def _convert_to_droidbot_format(self, actions: List[Dict[str, Any]],
                                    state: Dict[str, Any],
                                    screen_description) -> List[Dict[str, Any]]:
        """
        Convert action_id format actions to DroidBot format.

        Args:
            actions: List of action dictionaries with action_id format
            state: Current application state
            screen_description: Parsed screen description

        Returns:
            List of actions in DroidBot format
        """
        droidbot_actions = []

        # Create a mapping of action IDs to ItemAction objects for quick lookup
        action_map = {}
        for item in screen_description.items:
            for action in item.actions:
                action_map[str(action.id)] = (action, item.view)

        for action_data in actions:
            try:
                action_id = str(action_data["action_id"])
                params = action_data.get("params", {})
                explanation = action_data.get("explanation", "")

                # Find the corresponding ItemAction and view
                if action_id not in action_map:
                    self.logger.warning(f"Action ID {action_id} not found in available actions")
                    continue

                item_action, view_data = action_map[action_id]

                # Extract action type
                action_type = self._extract_action_type(item_action.text)

                # Get coordinates
                coordinates = self._resolve_coordinates(item_action, view_data, state, action_id)

                # Create DroidBot action
                droidbot_action = {
                    "action_type": action_type,
                    "target": self._get_target(item_action, state),
                    "params": self._process_params(action_type, params),
                    "explanation": explanation
                }

                # Add coordinates if available
                if coordinates:
                    droidbot_action["coordinates"] = coordinates

                droidbot_actions.append(droidbot_action)

            except Exception as e:
                self.logger.error(f"Error converting action {action_data}: {e}", exc_info=True)

        return droidbot_actions

    def _enhance_action_history(self, state: Dict[str, Any]) -> None:
        """
        Enhance action history with better formatting and context.

        Args:
            state: State dictionary to enhance
        """
        if "action_history" not in state:
            return

        self.logger.debug("Processing action history for enhanced format")
        enhanced_history = []

        for action in state.get("action_history", []):
            # Skip if already in enhanced format
            if isinstance(action, str) and action.startswith("[Action ID:"):
                enhanced_history.append(action)
                continue

            # Convert dictionary actions to enhanced format
            if isinstance(action, dict):
                action_id = action.get("action_id", "unknown")
                action_type = action.get("action_type", "unknown")
                target = action.get("target", "unknown")
                params = action.get("params", {})
                explanation = action.get("explanation", "")

                # Format parameters
                params_str = ""
                if params:
                    if "text" in params:
                        params_str = f" with text '{params['text']}'"
                    elif "direction" in params:
                        params_str = f" {params['direction']}"

                # Create context-sensitive description
                if action_type == "click":
                    if "spinner" in target.lower() or "dropdown" in target.lower():
                        description = f"CLICKED ON DROPDOWN '{target}'{params_str}"
                    elif any(keyword in target.lower() for keyword in
                             ["submit", "login", "save", "apply", "ok", "next"]):
                        description = f"SUBMITTED FORM by clicking '{target}'{params_str}"
                    else:
                        description = f"CLICKED on '{target}'{params_str}"
                elif action_type == "set_text":
                    description = f"FILLED text field '{target}'{params_str}"
                elif action_type in ["scroll_up", "scroll_down"]:
                    description = f"SCROLLED {action_type.split('_')[1]} on '{target}'{params_str}"
                else:
                    description = f"{action_type.upper()} on '{target}'{params_str}"

                enhanced_action = f"[Action ID: {action_id}] {description} - {explanation}"
                enhanced_history.append(enhanced_action)
            else:
                # Keep string actions as is
                enhanced_history.append(action)

        # Update the state
        state["action_history"] = enhanced_history
        self.logger.debug(f"Enhanced action history now has {len(enhanced_history)} entries")

    def _add_action_specific_history(self, state: Dict[str, Any]) -> None:
        """
        Add action-specific history information to the state.
        This helps the LLM understand the history of each possible action.

        Args:
            state: State dictionary to augment with action history
        """
        try:
            # Parse screen to get available actions
            screen_description = self.prompt_strategy.parser.parse(state, self.static_data)

            # Get current activity
            activity = self.prompt_strategy.parser.get_activity_name(state)

            # Get all action IDs
            action_ids = set()
            for item in screen_description.items:
                for action in item.actions:
                    action_ids.add(str(action.id))

            # Get action history
            action_history = state.get("action_history", [])

            # Create action-specific history
            action_specific_history = {}

            for action_id in action_ids:
                # Filter history entries that reference this action ID
                specific_history = [
                    entry for entry in action_history
                    if isinstance(entry, str) and f"[Action ID: {action_id}]" in entry
                ]

                # Store in the dictionary
                action_specific_history[action_id] = specific_history

                # Check if this action has been tested yet
                is_tested = len(specific_history) > 0

                # Update the dynamic WTG if the action has been tested
                if is_tested:
                    self.dynamic_wtg.record_action(activity, action_id)

            # Add to state
            state["action_specific_history"] = action_specific_history

        except Exception as e:
            self.logger.error(f"Error adding action-specific history: {e}", exc_info=True)

    def _update_graph_with_actions(self, state: Dict[str, Any], actions: List[Dict[str, Any]]) -> None:
        """
        Update the dynamic transition graph with information about chosen actions.

        Args:
            state: Current application state
            actions: List of selected actions
        """
        try:
            activity = self.prompt_strategy.parser.get_activity_name(state)

            for action in actions:
                action_id = action.get("action_id", None)
                if action_id:
                    # Record that this action was chosen for this activity
                    self.dynamic_wtg.record_action(activity, action_id)

        except Exception as e:
            self.logger.error(f"Error updating graph with actions: {e}", exc_info=True)

    # rvandroid/service/llm_action_service.py - _process_action_id_format method update

    def _process_action_id_format(self, llm_actions: List[Dict[str, Any]], state: Dict[str, Any]) -> List[
        Dict[str, Any]]:
        """
        Process actions in action_id format returned by BasicPromptStrategy001 or SingleActionPromptStrategy.
        Ensures coordinates are included for all actions.

        Args:
            llm_actions: Actions from LLM with action_id format
            state: Current application state

        Returns:
            List of actions in droidbot format
        """
        self.logger.debug(
            f"Processing {len(llm_actions) if isinstance(llm_actions, list) else 'non-list'} actions from LLM")

        # Validate input format
        if not isinstance(llm_actions, list):
            self.logger.warning(f"Expected list of actions but got: {type(llm_actions)}")
            return self._generate_fallback_actions(state)

        # Safety check for empty action list
        if not llm_actions:
            self.logger.warning("Received empty action list from LLM")
            return self._generate_fallback_actions(state)

        # Get screen description to access available actions
        try:
            self.logger.debug("Parsing screen description to access available actions")
            screen_description = self.prompt_strategy.parser.parse(state, self.static_data)
            available_actions = {
                str(action.id): action
                for item in screen_description.items
                for action in item.actions
            }
            self.logger.debug(f"Found {len(available_actions)} available actions")

            # Log available action IDs for debugging
            if available_actions:
                action_ids = list(available_actions.keys())
                self.logger.debug(f"Available action_ids: {action_ids[:10]}{'...' if len(action_ids) > 10 else ''}")

            # Safety check - if no actions available, generate fallbacks
            if not available_actions:
                self.logger.warning("No available actions found in screen description")
                return self._generate_fallback_actions(state)

        except Exception as e:
            self.logger.error(f"Error parsing state: {e}", exc_info=True)
            return self._generate_fallback_actions(state)

        droidbot_actions = []

        # For single action strategies, ALWAYS limit to the first action only
        if isinstance(self.prompt_strategy, SingleActionPromptStrategy) or isinstance(self.prompt_strategy,
                                                                                      DSPySingleActionPromptStrategy):
            if len(llm_actions) > 1:
                self.logger.warning(
                    f"Single action strategy detected with {len(llm_actions)} actions. Strictly limiting to first action only.")
                llm_actions = llm_actions[:1]

        for i, action_data in enumerate(llm_actions):
            try:
                self.logger.debug(f"Processing action {i + 1}/{len(llm_actions)}: {action_data}")

                # Validate action data format
                if not isinstance(action_data, dict):
                    self.logger.warning(f"Invalid action format: {action_data}")
                    continue

                # Check if action_id is present, try to handle alternative formats
                action_id = None
                if "action_id" in action_data:
                    action_id = str(action_data["action_id"])
                elif "id" in action_data:
                    action_id = str(action_data["id"])
                    self.logger.debug(f"Using 'id' field instead of 'action_id': {action_id}")
                elif "actionId" in action_data:
                    action_id = str(action_data["actionId"])
                    self.logger.debug(f"Using 'actionId' field instead of 'action_id': {action_id}")

                if not action_id:
                    self.logger.warning(f"No action_id found in: {action_data}")
                    continue

                params = action_data.get("params", {})
                explanation = action_data.get("explanation", "")

                # Find corresponding ItemAction
                if action_id not in available_actions:
                    self.logger.warning(f"Unknown action_id: {action_id} (not in available actions)")
                    # Log available actions for debugging
                    self.logger.debug(f"Available action_ids: {list(available_actions.keys())}")
                    continue

                item_action = available_actions[action_id]
                self.logger.debug(f"Found corresponding ItemAction: {item_action.text}")

                # Extract action type from the item_action text
                action_type = self._extract_action_type(item_action.text)
                self.logger.debug(f"Extracted action_type: {action_type}")

                # Extract view data for this action
                view_data = None
                for item in screen_description.items:
                    if any(action.id == int(action_id) for action in item.actions):
                        view_data = item.view
                        break

                # Get coordinates with enhanced logging
                coordinates = self._resolve_coordinates(item_action, view_data, state, action_id)

                # Create droidbot action format
                target = self._get_target(item_action, state)
                droidbot_action = {
                    "action_type": action_type,
                    "target": target,
                    "params": self._process_params(action_type, params),
                    "explanation": explanation
                }

                # Add coordinates to the action if we found them
                if coordinates:
                    droidbot_action["coordinates"] = coordinates
                    self.logger.info(f"Added coordinates {coordinates} to action: {action_id}")
                else:
                    self.logger.warning(f"No coordinates found for action: {action_id}")

                self.logger.debug(f"Created droidbot action: {droidbot_action}")
                droidbot_actions.append(droidbot_action)
            except Exception as e:
                self.logger.error(f"Error processing action data {action_data}: {e}", exc_info=True)
                continue

        if not droidbot_actions:
            self.logger.warning("Failed to process any actions from LLM response")
            return self._generate_fallback_actions(state)

        self.logger.info(f"Successfully processed {len(droidbot_actions)} actions")
        return droidbot_actions

    def _resolve_coordinates(self, item_action, view_data, state, action_id) -> Optional[tuple]:
        """
        Resolve coordinates for an action using multiple strategies.

        Args:
            item_action: The ItemAction object
            view_data: View data for the action
            state: Current application state
            action_id: Action ID for logging

        Returns:
            Tuple of (x, y) coordinates or None if not found
        """
        self.logger.debug(f"Resolving coordinates for action_id: {action_id}")

        # Method 1: Use coordinates from ItemAction if available
        if hasattr(item_action, 'coordinates') and item_action.coordinates:
            return item_action.coordinates

        # Method 2: Try to extract from target_view if available
        if hasattr(item_action, 'target_view') and item_action.target_view:
            bounds = item_action.target_view.get("bounds")
            if bounds and len(bounds) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                return (x, y)

        # Method 3: Try to extract from the view_data if available
        if view_data:
            bounds = view_data.get("bounds")
            if bounds and len(bounds) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                return (x, y)

        # Method 4: If target is a resource ID, try to find it in the view tree
        if "view_tree" in state:
            resource_id = None
            if hasattr(item_action, 'target_view') and item_action.target_view:
                resource_id = item_action.target_view.get("resource_id")

            if resource_id:
                coordinates = self._find_coordinates_for_resource_id(state["view_tree"], resource_id)
                if coordinates:
                    return coordinates

        # Method 5: Try to extract from target string
        target = self._get_target(item_action, state)
        if isinstance(target, str) and " " in target:
            parts = target.split()
            if len(parts) == 2 and all(part.isdigit() for part in parts):
                x, y = int(parts[0]), int(parts[1])
                return (x, y)

        self.logger.warning(f"Failed to resolve coordinates for action_id: {action_id}")
        return None

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
            Action type string for DroidBot
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

    def _get_target(self, item_action, state: Dict[str, Any]) -> str:
        """
        Get the target for an action from the associated view data.

        Args:
            item_action: The ItemAction object
            state: Current application state

        Returns:
            Target string (resource_id or coordinates)
        """
        # Try to get resource_id from target_view
        if hasattr(item_action, 'target_view') and item_action.target_view:
            if "resource_id" in item_action.target_view:
                return item_action.target_view["resource_id"]

            # Fall back to coordinates if bounds are available
            if "bounds" in item_action.target_view:
                bounds = item_action.target_view["bounds"]
                if bounds and len(bounds) == 2:
                    x = (bounds[0][0] + bounds[1][0]) // 2
                    y = (bounds[0][1] + bounds[1][1]) // 2
                    return f"{x} {y}"

        # If we have coordinates, use them
        if hasattr(item_action, 'coordinates') and item_action.coordinates:
            x, y = item_action.coordinates
            return f"{x} {y}"

        # Last resort, return the action text
        return item_action.text

    def _process_params(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and validate parameters for an action.

        Args:
            action_type: Type of action
            params: Parameters from LLM

        Returns:
            Processed parameters dictionary
        """
        processed_params = params.copy() if params else {}

        # Handle SET_TEXT action type
        if action_type == "set_text":
            if "text" not in processed_params or not processed_params["text"]:
                processed_params["text"] = "test input"
                self.logger.debug(f"Added default text parameter to SET_TEXT action")

        # Handle KEY_EVENT action type
        elif action_type == "key_event":
            if "name" not in processed_params:
                processed_params["name"] = "BACK"
                self.logger.debug("Added default BACK key event parameter")

        # Handle SCROLL action types
        elif action_type in ["scroll_up", "scroll_down", "scroll_left", "scroll_right"]:
            if "direction" not in processed_params:
                direction = action_type.split('_')[1].upper()
                processed_params["direction"] = direction
                self.logger.debug(f"Added direction parameter '{direction}' to scroll action")

        return processed_params

    def _extract_json(self, text: str) -> str:
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
        import re
        import json

        self.logger.debug(f"Attempting to extract JSON from response of length {len(text)}")

        # First attempt: Look for JSON array pattern with action_id
        array_pattern = r'\[\s*\{\s*"action_id"\s*:.*?\}\s*\]'
        array_match = re.search(array_pattern, text, re.DOTALL)
        if array_match:
            json_text = array_match.group(0)
            try:
                parsed = json.loads(json_text)
                self.logger.debug(f"Successfully extracted JSON array with action_id: {json_text[:100]}...")
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found array with action_id but content isn't valid JSON")

        # Second attempt: Look for any JSON array
        array_match = re.search(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL)
        if array_match:
            json_text = array_match.group(0)
            try:
                parsed = json.loads(json_text)
                self.logger.debug(f"Successfully extracted general JSON array: {json_text[:100]}...")
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found array brackets but content isn't valid JSON")

        # Third attempt: Look for JSON object pattern
        object_match = re.search(r'\{\s*".*?"\s*:.*?\}', text, re.DOTALL)
        if object_match:
            json_text = object_match.group(0)
            try:
                parsed = json.loads(json_text)
                # Wrap single object in an array for consistency
                self.logger.debug(f"Found JSON object, wrapping in array: {json_text[:100]}...")
                return f"[{json_text}]"
            except json.JSONDecodeError:
                self.logger.warning("Found object braces but content isn't valid JSON")

        # Fourth attempt: Try to perform common JSON fixes on array content
        self.logger.debug("Attempting to fix and extract JSON array")
        start_idx = text.find('[')
        end_idx = text.rfind(']')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = text[start_idx:end_idx + 1]
            # Fix common JSON issues
            fixed_json = self._fix_json_text(json_text)
            if fixed_json:
                try:
                    parsed = json.loads(fixed_json)
                    self.logger.debug(f"Successfully repaired JSON array: {fixed_json[:100]}...")
                    return fixed_json
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse fixed JSON array")

        # Fifth attempt: Extract action_id values and construct a valid array
        self.logger.warning("Attempting to reconstruct JSON from fragments")
        fallback_actions = self._extract_fallback_json(text)
        if fallback_actions:
            self.logger.debug(f"Reconstructed JSON array from fragments: {fallback_actions[:100]}...")
            return fallback_actions

        # Log the problematic response
        self.logger.error(f"Failed to extract JSON. Response text sample: {text[:200]}...")
        # If all attempts fail, raise the exception
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

        # Replace single quotes with double quotes
        text = re.sub(r"'([^']*)'", r'"\1"', text)

        # Fix unquoted property names
        text = re.sub(r'(\w+):', r'"\1":', text)

        # Fix trailing commas in arrays and objects
        text = re.sub(r',\s*\}', '}', text)
        text = re.sub(r',\s*\]', ']', text)

        # Fix missing quotes around string values
        text = re.sub(r':\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*([,\}])', r': "\1"\2', text)

        # Fix boolean values
        text = re.sub(r':\s*True\s*([,\}])', r': true\1', text)
        text = re.sub(r':\s*False\s*([,\}])', r': false\1', text)

        # Fix double-quoted strings inside single-quoted strings
        text = re.sub(r'\'([^\']*)"([^\']*)"([^\']*)\'', r'"\1\"\2\"\3"', text)

        return text

    def _extract_fallback_json(self, text: str) -> str:
        """
        Extract action data from text and construct a valid JSON array.
        This is a last-resort method for when normal JSON parsing fails.

        Args:
            text: Text containing potential action data

        Returns:
            Valid JSON array string or empty string if extraction fails
        """
        import json
        import re

        # Try to extract action_id values
        action_ids = re.findall(r'action_id["\s:]+([0-9]+)', text)

        # Try to extract explanation values - match text between explanation and the next property
        explanations = re.findall(r'explanation["\s:]+"([^"]+)"', text)

        # Check if we found any action IDs
        if action_ids:
            # Create fallback actions
            actions = []

            for i, action_id in enumerate(action_ids):
                explanation = explanations[i] if i < len(explanations) else "Extracted action"

                action = {
                    "action_id": action_id,
                    "params": {},
                    "explanation": explanation
                }

                actions.append(action)

            if actions:
                return json.dumps(actions)

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

    def save_dynamic_transition_graph(self) -> bool:
        """
        Save the dynamic transition graph to file.

        Returns:
            True if successful, False otherwise
        """
        return self.dynamic_wtg.save_to_file(self.dynamic_wtg_file)

    def cleanup(self):
        """
        Clean up resources used by the service.
        """
        # Save dynamic transition graph before cleanup
        self.save_dynamic_transition_graph()

        # Save final session if recording is enabled
        if self.record_session and self.session_actions:
            self._save_session()
            self.session_actions = []

        if self.llm:
            try:
                self.llm.clean()
                self.llm = None
                self.logger.info("Cleaned up LLM resources")
            except Exception as e:
                self.logger.warning(f"Error cleaning up LLM: {e}")

    def update_dynamic_transitions(self, state: Dict[str, Any], executed_action: Dict[str, Any] = None) -> None:
        """
        Update dynamic transition graph with information about the current state.

        Args:
            state: Current application state
            executed_action: The action that was executed to reach this state (if known)
        """
        try:
            # Get current activity
            current_activity = self.prompt_strategy.parser.get_activity_name(state)

            # Record visit to this activity
            self.dynamic_wtg.record_visit(current_activity)

            # If we have an executed action and we're tracking transitions
            if executed_action and 'previous_activity' in state:
                previous_activity = state['previous_activity']
                action_id = executed_action.get('action_id', 'unknown')
                action_type = executed_action.get('action_type', 'unknown')

                # Record transition
                self.dynamic_wtg.record_transition(
                    previous_activity,
                    current_activity,
                    action_id,
                    action_type
                )

                self.logger.info(
                    f"Recorded transition: {previous_activity} -> {current_activity} via action {action_id}")

        except Exception as e:
            self.logger.error(f"Error updating dynamic transitions: {e}", exc_info=True)

    def get_transition_guidance(self, activity: str) -> Dict[str, Any]:
        """
        Get guidance information based on dynamic transitions for the current activity.

        Args:
            activity: Current activity name

        Returns:
            Dictionary with transition guidance information
        """
        guidance = {
            "current_activity": activity,
            "visit_count": 0,
            "suggested_targets": [],
            "unexplored_elements": [],
            "visited_activities": [],
            "least_visited_activities": []
        }

        try:
            # Normalize activity name by removing the '/' character if present
            normalized_activity = activity.replace("/", ".")
            if normalized_activity.endswith(".."):
                normalized_activity = normalized_activity[:-1]

            # Get activity node
            activity_node = self.dynamic_wtg.activities.get(normalized_activity)
            if activity_node:
                guidance["visit_count"] = activity_node.visit_count
                guidance["unexplored_elements"] = list(activity_node.ui_elements_tested)

            # Get visited activities
            guidance["visited_activities"] = [
                {"name": name, "visits": node.visit_count}
                for name, node in self.dynamic_wtg.activities.items()
            ]

            # Get suggested target activities - use normalized activity name for lookup
            if normalized_activity in self.dynamic_wtg.graph:
                neighbors = list(self.dynamic_wtg.graph.neighbors(normalized_activity))
                least_visited = []

                if neighbors:
                    # Sort neighbors by visit count
                    neighbor_visits = [
                        {"name": n, "visits": self.dynamic_wtg.activities[n].visit_count}
                        for n in neighbors
                    ]
                    neighbor_visits.sort(key=lambda x: x["visits"])
                    guidance["suggested_targets"] = neighbor_visits[:3]
            else:
                # If the activity is not in the graph yet, add it
                self.dynamic_wtg.add_activity(normalized_activity)
                guidance["suggested_targets"] = []

            # Get overall least visited activities
            least_visited_tuples = self.dynamic_wtg.get_least_visited_activities(5)
            guidance["least_visited_activities"] = [
                {"name": name, "visits": count} for name, count in least_visited_tuples
            ]

        except Exception as e:
            self.logger.error(f"Error getting transition guidance: {e}", exc_info=True)

        return guidance
