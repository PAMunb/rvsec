"""State enricher for the prompt system.

This module defines the StateEnricher class, which is responsible for analyzing
and enriching the application state before prompt generation.
"""

from typing import Any, Dict, Optional

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.constants import StateEntry
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction


class StateEnricher:
    """Enriches the state with additional information before prompt generation.
    
    This component preprocesses the application state to add or enhance information
    that will be used during prompt generation, such as:
    - Processing screenshots for additional insights
    - Detecting UI patterns like login forms, settings pages, etc.
    - Adding monitored operations information based on static analysis
    - Parsing screen information into structured ScreenDescription objects
    """

    def __init__(
            self,
            static_data: StaticAnalysisData = None,
            config: Optional[LLMConfig] = None
    ):
        """Initialize the state enricher with parser support.
        
        Args:
            static_data: Static analysis data.
            config: Component configuration.
        """
        # Store data and configuration
        self.static_data = static_data
        self.config = config

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvandroid_tool.llm.service.state_enricher",
            {CONTEXT_COMPONENT: "StateEnricher"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

        # Initialize screen parser for generating ScreenDescription objects
        try:
            from rv_screen_parser.parser.screen.parser_factory import ParserFactory, ParserType
            visitor_class = DefaultTextVisitor
            if config is not None and config.visitor_class:
                visitor_class = config.visitor_class
            self.parser = ParserFactory.create(ParserType.DROIDBOT, visitor_class)
            self.logger.info(
                f"Initialized screen parser: {self.parser.__class__.__name__} with visitor: {visitor_class.__name__}")
        except ImportError:
            self.logger.warning("Could not initialize screen parser, screen descriptions may be limited")
            self.parser = None

        # Initialize analyzers (as needed)
        self.screenshot_action_complementor = None
        self.pattern_detector = None

        # Try to initialize analyzers if they exist
        try:
            from rvandroid_tool.analysis.screenshot.screenshot_action_complementor import ScreenshotActionComplementor
            self.screenshot_action_complementor = ScreenshotActionComplementor(static_data=self.static_data)
        except ImportError:
            self.logger.warning("Screenshot Action Complementor not available")

        try:
            from rv_android_core.analysis.ui_pattern_detector import UIPatternDetector
            self.pattern_detector = UIPatternDetector()
        except ImportError:
            self.logger.warning("UIPatternDetector not available")

    def enrich_state(self, state: Dict[str, Any]):
        """Add additional information to state before prompt generation.
        
        Args:
            state: The current application state.
        """
        self.logger.debug("Enriching state for prompt generation")

        try:
            # Add screen description if not present
            self._add_screen_description(state)

            # Process screenshot if available
            self._process_screenshot(state)

            # Detect UI patterns
            self._detect_ui_patterns(state)

            # Add monitored operations information
            self._add_monitored_operations(state)

        except Exception as e:
            self.logger.error(f"Error enriching state: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "StateEnricher",
                    "state_id": state.get("id", "unknown")
                }
            )
            return state

    def _process_screenshot(self, state: Dict[str, Any]) -> None:
        """Process screenshot to extract additional information.
        
        Args:
            state: The current application state.
        """
        if not self.screenshot_action_complementor:
            return

        if StateEntry.SCREENSHOT_PATH in state and state[StateEntry.SCREENSHOT_PATH]:
            try:
                self.logger.debug(f"Processing screenshot: {state[StateEntry.SCREENSHOT_PATH]}")

                # Use screenshot analyzer to complement ScreenDescription information
                screen_description = self.screenshot_action_complementor.analyze(state)

                # Update state with screen description´d
                if screen_description:
                    state[StateEntry.STRUCTURED_SCREEN] = screen_description["enhanced_screen"]
                    state[StateEntry.SCREENSHOT_INFO] = screen_description["visual_mapping"]
            except Exception as e:
                self.logger.error(f"Error processing screenshot: {e}", exc_info=True)
                self.error_handler.handle_error(
                    e,
                    context={
                        "component": "StateEnricher",
                        "function": "_process_screenshot",
                        "screenshot_path": state.get(StateEntry.SCREENSHOT_PATH, "unknown")
                    }
                )

    def _detect_ui_patterns(self, state: Dict[str, Any]) -> None:
        """Detect UI patterns in the screen.
        
        Args:
            state: The current application state.
        """
        # Skip if pattern detector is not available
        if not self.pattern_detector:
            return

        # Skip if screen patterns already present
        if StateEntry.UI_PATTERNS in state:
            return

        # Skip if screen description is not present
        if StateEntry.STRUCTURED_SCREEN not in state:
            return

        try:
            self.logger.debug("Detecting UI patterns")

            # Use pattern detector to identify UI patterns
            screen_description = state[StateEntry.STRUCTURED_SCREEN]
            patterns = self.pattern_detector.detect_patterns(screen_description, self.static_data)

            # Add detected patterns to state
            if patterns:
                state[StateEntry.UI_PATTERNS] = patterns

                # If there's a high confidence pattern, add it as the detected pattern
                for pattern_name, pattern_info in patterns.items():
                    if isinstance(pattern_info, dict) and pattern_info.get("confidence", 0) >= 0.7:
                        # TODO transformar em texto para estar pronto para ser usado em algum template
                        state[StateEntry.DETECTED_PATTERN] = {
                            "name": pattern_name,
                            **pattern_info
                        }
                        break
        except Exception as e:
            self.logger.error(f"Error detecting UI patterns: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "StateEnricher",
                    "function": "_detect_ui_patterns"
                }
            )

    def _add_monitored_operations(self, state: Dict[str, Any]) -> None:
        """Add monitored operations information from static analysis.
        
        Args:
            state: The current application state.
        """
        if not self.static_data:
            self.logger.warning("No static analysis data available")
            return

        try:
            self.logger.debug("Adding monitored operations information")

            # Get current activity
            activity = state.get(StateEntry.ACTIVITY, "unknown")

            # Get monitored operations for this activity
            monitored_ops = []
            actv_class = self.static_data.classes.get_clazz(activity)
            if actv_class and hasattr(actv_class, 'methods'):
                for method in actv_class.methods:
                    if method.directly_reaches_mop or method.reaches_mop:
                        monitored_ops.append(method.signature)
            else:
                self.logger.warning(f"Activity class not found or has no methods: {activity}")

            # Add monitored operations to state
            if monitored_ops:
                state[StateEntry.MONITORED_OPERATIONS] = monitored_ops
        except Exception as e:
            self.logger.error(f"Error adding monitored operations: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "StateEnricher",
                    "function": "_add_monitored_operations",
                    "activity": state.get(StateEntry.ACTIVITY, "unknown")
                }
            )

    def _add_screen_description(self, state: Dict[str, Any]) -> None:
        """Add screen description by parsing UI elements into a structured ScreenDescription.
        
        This method uses the appropriate parser to create a structured ScreenDescription
        object representing the screen content. This approach ensures compatibility with
        both droidbot and uiautomator parsers.
        
        Args:
            state: The current application state.
        """
        # Screen description already exists, no need to add it again
        if StateEntry.SCREEN_DESCRIPTION in state:
            return

        try:
            self.logger.debug("Adding screen description using parser")

            # Check if we have a parser available
            if not hasattr(self, 'parser') or self.parser is None:
                # Try to initialize parser dynamically if it's not already available
                try:
                    from rv_screen_parser.parser.screen.parser_factory import ParserFactory
                    from rv_screen_parser.constants import ScreenParserType
                    self.parser = ParserFactory.create(ScreenParserType.DROIDBOT, DefaultTextVisitor)
                    self.logger.debug(f"Created parser on demand: {self.parser.__class__.__name__}")
                except ImportError:
                    self.logger.warning("Could not create parser, using simple text description")
                    # TODO rever
                    screen = state[StateEntry.SCREEN_PATTERNS]
                    state[StateEntry.SCREEN_DESCRIPTION] = self._format_screen_elements(screen)
                    return

            # Parse the screen to get a structured ScreenDescription object
            screen_description: ScreenDescription = self.parser.parse_screen(state, self.static_data)

            if screen_description:
                self.logger.debug(f"Successfully created ScreenDescription with {len(screen_description.items)} items")

                # Extract available action IDs for later use
                available_actions_map: Dict[int, ItemAction] = {}
                for item in screen_description.items:
                    for action in item.actions:
                        available_actions_map[action.id] = action

                # Add the complete structured object for other components to use directly
                state[StateEntry.STRUCTURED_SCREEN] = screen_description

                # Get the string representation for template rendering
                # This uses the ScreenDescription's own string representation method
                formatted_text = str(screen_description)

                # Update state with necessary information
                state[StateEntry.SCREEN_DESCRIPTION] = formatted_text
                state[StateEntry.AVAILABLE_ACTIONS] = available_actions_map
                print(f"**** screen_description:\n{formatted_text}")

                self.logger.debug(f"Added ScreenDescription with {len(available_actions_map)} available actions")
            else:
                # If parsing failed, use simple fallback
                self.logger.warning("Failed to create ScreenDescription, using text fallback")
                state[StateEntry.SCREEN_DESCRIPTION] = ""
                if StateEntry.SCREEN_PATTERNS in state:
                    screen = state[StateEntry.SCREEN_PATTERNS]
                    state[StateEntry.SCREEN_DESCRIPTION] = self._format_screen_elements(screen)
        except Exception as e:
            self.logger.error(f"Error adding screen description: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "StateEnricher",
                    "function": "_add_screen_description"
                }
            )

            # Use simple fallback on error
            try:
                screen = state.get(StateEntry.SCREEN_PATTERNS, {})
                state[StateEntry.SCREEN_DESCRIPTION] = self._format_screen_elements(screen)
            except Exception:
                state[StateEntry.SCREEN_DESCRIPTION] = "Error generating screen description"

    def _format_screen_elements(self, screen: Dict[str, Any]) -> str:
        """Format screen elements for display in the prompt.
        
        Args:
            screen: The screen information from the state.
            
        Returns:
            A formatted string representation of the screen elements.
        """
        if not screen:
            return "No screen information available."

        components = screen.get("components", [])
        if not components:
            return "No UI components found on screen."

        formatted_parts = []

        # Add screen title and activity if available
        title = screen.get("title", "")
        if title:
            formatted_parts.append(f"Screen title: {title}")

        # Add components with details
        formatted_parts.append("UI Components:")

        for i, component in enumerate(components):
            component_type = component.get("type", "unknown")
            component_text = component.get("text", "")
            component_id = component.get("resource_id", "")
            component_clickable = "clickable" if component.get("clickable", False) else "not clickable"
            component_enabled = "enabled" if component.get("enabled", True) else "disabled"

            details = []
            if component_text:
                details.append(f"text='{component_text}'")
            if component_id:
                details.append(f"id='{component_id}'")

            # Add bounds if available
            bounds = component.get("bounds", {})
            if bounds:
                left = bounds.get("left", 0)
                top = bounds.get("top", 0)
                right = bounds.get("right", 0)
                bottom = bounds.get("bottom", 0)
                details.append(f"bounds=[{left},{top},{right},{bottom}]")

            details.append(component_clickable)
            details.append(component_enabled)

            formatted_parts.append(f"{i + 1}. {component_type}: {', '.join(details)}")

        return "\n".join(formatted_parts)

    # def _format_screen_description(self, screen_description) -> str:
    #     """Format a ScreenDescription object into detailed text format.
    #
    #     This method creates a rich textual representation of the ScreenDescription
    #     object, including detailed information about all UI elements and available
    #     actions - similar to what the original prompt strategies provided.
    #
    #     Args:
    #         screen_description: The ScreenDescription object.
    #
    #     Returns:
    #         A formatted string representation similar to the original prompt format.
    #     """
    #     if not screen_description or not screen_description.items:
    #         return "No UI elements detected in the current state."
    #
    #     lines = []
    #
    #     # Add activity information
    #     activity = screen_description.activity
    #     if activity:
    #         lines.append(f"Activity: {activity}")
    #
    #     # Process each item with rich details
    #     for item in screen_description.items:
    #         view = item.view
    #         widget_id = view.get("resource_id", "").split("/")[-1] if view.get("resource_id") else "unknown"
    #
    #         # Add detailed description
    #         lines.append(f"- {item.base_description}")
    #
    #         # Add actions with their IDs
    #         if item.actions:
    #             lines.append("  Available actions:")
    #             for action in item.actions:
    #                 # Add indicators for operations of interest
    #                 importance_tag = ""
    #                 if action.directly_reaches_mop:
    #                     importance_tag = " [CRITICAL: Directly reaches operation of interest]"
    #                 elif action.reaches_mop:
    #                     importance_tag = " [IMPORTANT: Can reach operation of interest]"
    #
    #                 # Create detailed action description
    #                 action_desc = f"  - {action.text} (action_id: \"{action.id}\"){importance_tag}"
    #                 lines.append(action_desc)
    #
    #         # Add guidance for parameterized actions
    #         has_text_action = False
    #         if item.actions:
    #             has_text_action = any(a.text.startswith("SET_TEXT") for a in item.actions)
    #
    #         if has_text_action:
    #             # Get input hints or description
    #             hint = ""
    #             if "hint" in view and view["hint"]:
    #                 hint = f" (hint: {view['hint']})"
    #             elif "content_description" in view and view["content_description"]:
    #                 hint = f" (description: {view['content_description']})"
    #             elif "text" in view and view["text"]:
    #                 hint = f" (current text: {view['text']})"
    #
    #             # Infer input type based on context
    #             is_password = "password" in str(view).lower() or "password" in str(item.base_description).lower()
    #             is_email = "email" in str(view).lower() or "email" in str(item.base_description).lower()
    #
    #             input_type = ""
    #             if is_password:
    #                 input_type = "password"
    #             elif is_email:
    #                 input_type = "email"
    #             else:
    #                 input_type = "text"
    #
    #             if input_type:
    #                 lines.append(f"  Input type appears to be: {input_type}{hint}")
    #
    #     return "\n".join(lines)
