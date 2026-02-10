# rvandroid/llm/service/action_generator.py
from typing import Dict, List, Any, Optional, Tuple

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.domain.widget import WidgetEventType
from rvandroid.experiment.event.bus import EventBus
from rvandroid.llm.constants import StateEntry
from rvandroid.parser.screen.visitor.model import ScreenDescription, ItemAction
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor

class GeneratedAction:

    def __init__(self, item: ItemAction, params: Dict[str, Any], coordinates: tuple[int, int], target, explanation: str):
        self.item = item
        self.id = item.id
        self.action_type = str(item.event.name)
        self.text = item.text
        self.reaches_mop = item.reaches_mop
        self.directly_reaches_mop = item.directly_reaches_mop
        self.target_view = item.target_view
        self.params = params
        self.coordinates = coordinates
        self.target = target # deprecated
        self.explanation = explanation

    def to_droidbot_format(self):
        return {
            "action_type": self.action_type,
            "coordinates": self.coordinates,
            "params": self.params,
            "target": self.target, # TODO deprecated
            "explanation": self.explanation
        }

    def to_dict(self):
        return {
            "id": self.id,
            "action_type": self.action_type,
            "coordinates": self.coordinates,
            "params": self.params,
            "reaches_mop": self.reaches_mop,
            "directly_reaches_mop": self.directly_reaches_mop,
            "explanation": self.explanation
        }


class ActionGenerator:
    """
    Generates framework-compatible test actions from parsed LLM responses.

    ### Architectural Decisions:
    - Focuses specifically on action generation and formatting
    - Separates action creation from response parsing
    - Implements fallback mechanisms for error cases
    - Provides conversion between different action formats
    - Supports the unified response format with an "actions" array

    ### Role in the System:
    - Transforms parsed LLM responses into executable test actions
    - Handles action formatting for compatibility with test frameworks
    - Provides fallback actions when normal generation fails
    - Ensures actions include necessary metadata and coordinates
    - Maintains consistent output format regardless of input strategy
    """

    def __init__(self, config: ComponentConfigurator, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the action generator.

        Args:
            config: Component configurator for action generation configuration
            static_data: Static analysis data for action enrichment
        """
        # Get system services
        self.event_bus = EventBus.get_instance()
        self.performance_monitor = PerformanceMonitor.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        logging_manager = LoggingManager.get_instance()

        # Configure logging
        self.logger = logging_manager.get_logger(
            "llm.service.action_generator",
            {CONTEXT_COMPONENT: "ActionGenerator"}
        )

        # Store configuration
        self.config = config
        self.static_data = static_data

        self.logger.info("Action generator initialized")

    def create_actions(self, actions: List[Dict[str, Any]], state: Dict[str, Any]) -> list[GeneratedAction]:
        """
        Convert parsed actions to framework-compatible format.

        Args:
            actions: List of parsed action dictionaries
            state: Current application state

        Returns:
            List of actions in DroidBot format
        """
        if not actions:
            self.logger.warning("No actions to convert, generating fallbacks")
            return self.generate_fallback_actions(state)

        try:
            # Convert to DroidBot format
            return self._convert_to_droidbot_format(actions, state)

        except Exception as e:
            self.logger.error(f"Error creating actions: {e}", exc_info=True)
            self.error_handler.handle_error(
                e,
                context={
                    "component": "ActionGenerator",
                    "function": "create_actions"
                }
            )
            return self.generate_fallback_actions(state)

    def generate_fallback_actions(self, state: Dict[str, Any]) -> list[GeneratedAction]:
        """
        Generate fallback actions when normal generation fails.

        Args:
            state: Application state dictionary

        Returns:
            List of fallback action dictionaries
        """
        self.logger.info("Generating fallback actions")

        fallback_actions: List[GeneratedAction] = []

        # Try to find some interactive elements
        if 'view_tree' in state:
            self._extract_clickable_elements(state['view_tree'], fallback_actions)

        # If no elements found, add a scroll action
        if not fallback_actions:
            item_id = 500 + len(fallback_actions) + 1
            item_action = ItemAction(item_id, f"SCROLL DOWN ({item_id})", WidgetEventType.SCROLL)
            generated_action = GeneratedAction(item_action,
                                               {},
                                               (100,100),
                                               "",
                                               "Fallback scroll action")
            fallback_actions.append(generated_action)

        return fallback_actions

    def _extract_clickable_elements(self, view: Dict[str, Any], actions: List[GeneratedAction], max_elements: int = 3):
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
                target = (x, y)

            if target:
                item_id = 500+len(actions)+1
                item_action = ItemAction(item_id, f"{WidgetEventType.CLICK.name}({item_id})", WidgetEventType.CLICK)
                generated_action = GeneratedAction(item_action,
                                                  {},
                                                  target,
                                                  str(target),
                                                  "Fallback click on visible element")
                actions.append(generated_action)

        # Recursively process children
        for child in view.get('children', []):
            if len(actions) >= max_elements:
                break
            self._extract_clickable_elements(child, actions, max_elements)

    # TODO renomear e converter em outro lugar
    def _convert_to_droidbot_format(self,
                                    actions: List[Dict[str, Any]],
                                    state: Dict[str, Any]) -> List[GeneratedAction]:
        """
        Convert action_id format actions to DroidBot format.

        Args:
            actions: List of action dictionaries with action_id format
            state: Current application state

        Returns:
            List of actions in DroidBot format
        """
        screen_description: ScreenDescription = state[StateEntry.STRUCTURED_SCREEN]
        droidbot_actions: List[GeneratedAction] = []

        # Create a mapping of action IDs to ItemAction objects for quick lookup
        action_map: Dict[str, Tuple[ItemAction, Dict[str, Any]]] = {}
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
                action_type = item_action.event.name

                # Get coordinates
                coordinates = self._resolve_coordinates(item_action, view_data, state, action_id)

                # Create DroidBot action
                droidbot_action = GeneratedAction(item_action,
                                                  self._process_params(action_type, params),
                                                  coordinates,
                                                  self._get_target(item_action, state),
                                                  explanation)

                droidbot_actions.append(droidbot_action)

            except Exception as e:
                self.logger.error(f"Error converting action {action_data}: {e}", exc_info=True)
                self.error_handler.handle_error(
                    e,
                    context={
                        "component": "ActionGenerator",
                        "function": "_convert_to_droidbot_format",
                        "action_data": str(action_data)
                    }
                )

        return droidbot_actions

    # def _extract_action_type(self, action_text: str) -> str:
    #     """
    #     Extract the action type from the action text description.
    #
    #     Args:
    #         action_text: Text description of the action
    #
    #     Returns:
    #         Action type string for DroidBot
    #     """
    #     if action_text.startswith("CLICK"):
    #         return "click"
    #     elif action_text.startswith("LONG_CLICK"):
    #         return "long_click"
    #     elif action_text.startswith("SCROLL"):
    #         # Extract direction if present
    #         if "UP" in action_text:
    #             return "scroll_up"
    #         elif "DOWN" in action_text:
    #             return "scroll_down"
    #         elif "LEFT" in action_text:
    #             return "scroll_left"
    #         elif "RIGHT" in action_text:
    #             return "scroll_right"
    #         return "scroll"
    #     elif action_text.startswith("SET_TEXT"):
    #         return "set_text"
    #     elif action_text.startswith("CHECK") or action_text.startswith("UNCHECK"):
    #         return "click"  # Checkbox actions are clicks
    #     elif action_text.startswith("BACK"):
    #         return "key_event"
    #     return "unknown"

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

    def _resolve_coordinates(self,
                             item_action: ItemAction,
                             view_data,
                             state: Dict[str, Any],
                             action_id: str) -> Optional[Tuple[int, int]]:
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
                return x, y

        # Method 3: Try to extract from the view_data if available
        if view_data:
            bounds = view_data.get("bounds")
            if bounds and len(bounds) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                return x, y

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
                return x, y

        self.logger.warning(f"Failed to resolve coordinates for action_id: {action_id}")
        return None

    def _find_coordinates_for_resource_id(self,
                                          view_tree: Dict[str, Any],
                                          resource_id: str) -> Optional[Tuple[int, int]]:
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
                return x, y

        # Also check if it has the same ID part (after :id/)
        if ":" in resource_id and view_tree.get("resource_id", ""):
            id_part = resource_id.split(":")[-1]
            view_id_part = view_tree.get("resource_id", "").split(":")[-1]
            if id_part == view_id_part:
                bounds = view_tree.get("bounds")
                if bounds and len(bounds) == 2:
                    x = (bounds[0][0] + bounds[1][0]) // 2
                    y = (bounds[0][1] + bounds[1][1]) // 2
                    return x, y

        # Check children
        for child in view_tree.get("children", []):
            coords = self._find_coordinates_for_resource_id(child, resource_id)
            if coords:
                return coords

        return None
