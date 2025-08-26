"""
Action generation service for Android testing framework.

This module converts parsed LLM responses into executable test actions,
providing the bridge between AI-generated decisions and device interaction.
"""

from typing import Dict, List, Any, Optional, Tuple

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType
from rv_android_core.event.bus import EventBus
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm import LLMConfig
from rv_llm.llm.constants import StateEntry
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction


class GeneratedAction:
    """
    Represents a test action with complete execution metadata.
    
    ### Architecture Overview:
    Unified action representation supporting UI element actions and future
    coordinate-based actions. Provides conversion methods for different
    execution frameworks while maintaining consistent internal structure.
    
    ### Action Types:
    - UI actions: Target specific UI elements via ItemAction references
    - Coordinate actions: Direct screen coordinate targeting (future support)
    - System actions: Device-level operations (back, home, etc.)
    
    ### Execution Context:
    Actions carry complete metadata including coordinates, parameters,
    and targeting information required for reliable execution across
    different testing frameworks.
    """
    
    def __init__(self, 
                 item_action: Optional[ItemAction] = None,
                 coordinates: Tuple[int, int] = (0, 0),
                 params: Optional[Dict[str, Any]] = None,
                 target: str = "",
                 explanation: str = "",
                 custom_action_type: Optional[str] = None,
                 action_id: Optional[str] = None):
        """
        Initialize action with complete execution metadata.
        
        ### Initialization Strategy:
        Supports both standard UI element actions via ItemAction references
        and custom coordinate-based actions for advanced interaction scenarios.
        Provides unified interface for all action types.
        
        Args:
            item_action: UI element action definition (None for custom actions)
            coordinates: Screen coordinates for action execution
            params: Action-specific parameters (text, direction, etc.)
            target: Target identifier (resource_id or coordinate string)
            explanation: Human-readable action description
            custom_action_type: Action type for custom coordinate actions
            action_id: Action identifier for custom actions
        """
        from rvandroid_tool.constants import ACTION_TYPE_CLICK
        
        # Determine action initialization path based on source type
        # UI element actions use ItemAction metadata, custom actions use direct parameters
        self.is_custom = item_action is None
        
        # Initialize action properties based on source type
        if self.is_custom:
            # Custom coordinate-based actions (manual screen targeting)
            self.item = None
            self.id = action_id or "coord"
            self.action_type = custom_action_type or ACTION_TYPE_CLICK
            self.text = ""
            
            # Custom actions don't have monitored operations metadata
            # because they bypass UI element analysis that provides MOP annotations
            self.reaches_mop = False
            self.directly_reaches_mop = False
        else:
            # UI element actions (derived from screen parser visitor patterns)
            self.item = item_action
            self.id = item_action.id  # From visitor-generated ItemAction
            self.action_type = item_action.event.name.lower()  # WidgetEventType enum
            self.text = item_action.text
            
            # Monitored operations metadata from static analysis integration
            # These flags indicate if the action targets methods under runtime verification
            self.reaches_mop = item_action.reaches_mop
            self.directly_reaches_mop = item_action.directly_reaches_mop
        
        # Execution details
        self.coordinates = coordinates
        self.params = params or {}
        self.target = target
        self.explanation = explanation
        self.custom_action_type = custom_action_type

    def to_droidbot_format(self) -> Dict[str, Any]:
        """
        Convert action to DroidBot-compatible format.
        
        ### Format Specification:
        Returns complete action dictionary with all fields required
        by DroidBot policy for reliable action execution:
        - action_type: Standardized action type string
        - coordinates: Screen coordinates as [x, y] list
        - params: Action parameters dictionary
        - target: Target identifier string
        - explanation: Action description for debugging
        
        Returns:
            Complete action dictionary for DroidBot execution
        """
        return {
            "action_type": self.action_type,
            "coordinates": list(self.coordinates),
            "params": self.params,
            "target": self.target,
            "explanation": self.explanation
        }


class ActionGenerator:
    """
    Converts parsed LLM responses into executable test actions.
    
    ### Architecture Overview:
    Provides action generation services by mapping action_id references
    to complete action specifications with coordinates, parameters, and
    targeting information. Handles both current UI actions and prepares
    for future coordinate-based actions.
    
    ### Core Responsibilities:
    - Map action_id to ItemAction objects via ScreenDescription
    - Resolve coordinates for reliable action execution
    - Process action parameters based on action type
    - Generate fallback actions when normal processing fails
    - Provide consistent output format across action types
    
    ### Action Processing Pipeline:
    1. Parse action_id from LLM response
    2. Locate corresponding ItemAction in screen description
    3. Resolve execution coordinates from UI element bounds
    4. Process action-specific parameters
    5. Create GeneratedAction with complete metadata
    """

    def __init__(self, config: LLMConfig, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize action generator with configuration.
        
        Args:
            config: LLM configuration for action generation
            static_data: Static analysis data for action enrichment
        """
        # System services
        self.error_handler = ErrorHandler.get_instance()
        logging_manager = LoggingManager.get_instance()
        
        # Configure logging
        self.logger = logging_manager.get_logger(
            "rvandroid_tool.llm.service.action_generator",
            {CONTEXT_COMPONENT: "ActionGenerator"}
        )
        
        # Store configuration
        self.config = config
        self.static_data = static_data
        
        self.logger.info("Action generator initialized")

    def create_actions(self, 
                       actions: List[Dict[str, Any]], 
                       state: Dict[str, Any]) -> List[GeneratedAction]:
        """
        Convert parsed actions to executable format.
        
        ### Processing Strategy:
        Maps action_id values to ItemAction objects via ScreenDescription,
        then generates complete action specifications with coordinates,
        parameters, and targeting information.
        
        ### Error Handling:
        Returns fallback actions when normal processing fails, ensuring
        the testing session can continue even with malformed LLM responses.
        
        Args:
            actions: List of parsed action dictionaries with action_id
            state: Current application state with ScreenDescription
            
        Returns:
            List of GeneratedAction objects ready for execution
        """
        if not actions:
            self.logger.warning("No actions provided, generating fallback")
            return self._generate_fallback_actions(state)

        try:
            # Convert parsed action dictionaries to executable GeneratedAction objects
            # Maps action_id values to UI elements from ScreenDescription visitor analysis
            return self._convert_actions(actions, state)
        except Exception as e:
            self.logger.error(f"Action conversion failed: {e}", exc_info=True)
            self.error_handler.handle_error(e, {
                "component": "ActionGenerator", 
                "function": "create_actions",
                "actions_count": len(actions)
            })
            return self._generate_fallback_actions(state)

    def _convert_actions(self, 
                        actions: List[Dict[str, Any]], 
                        state: Dict[str, Any]) -> List[GeneratedAction]:
        """
        Convert action_id format actions to GeneratedAction objects.
        
        ### Conversion Process:
        1. Extract ScreenDescription from state
        2. Build action_id to ItemAction mapping
        3. Process each action_id reference
        4. Generate complete action specifications
        
        Args:
            actions: List of action dictionaries with action_id
            state: Application state with ScreenDescription
            
        Returns:
            List of converted GeneratedAction objects
        """
        screen_description: ScreenDescription = state[StateEntry.STRUCTURED_SCREEN]
        generated_actions: List[GeneratedAction] = []
        
        # Build action mapping for efficient lookup
        action_map = self._build_action_map(screen_description)
        
        for action_data in actions:
            try:
                action = self._convert_single_action(action_data, action_map, state)
                if action:
                    generated_actions.append(action)
                    self.logger.debug(f"Converted action {action_data['action_id']} to {action.action_type}")
            except Exception as e:
                self.logger.error(f"Failed to convert action {action_data}: {e}")
                continue
        
        return generated_actions

    def _build_action_map(self, screen_description: ScreenDescription) -> Dict[str, Tuple[ItemAction, Dict[str, Any]]]:
        """
        Build mapping from action_id to ItemAction and view data.
        
        ### Mapping Strategy:
        Creates efficient lookup table mapping string action_id values
        to their corresponding ItemAction objects and associated view data
        for coordinate resolution and parameter processing.
        
        Args:
            screen_description: Parsed screen with UI elements and actions
            
        Returns:
            Dictionary mapping action_id strings to (ItemAction, view_data) tuples
        """
        action_map = {}
        
        for item in screen_description.items:
            for action in item.actions:
                action_map[str(action.id)] = (action, item.view)
                
        self.logger.debug(f"Built action map with {len(action_map)} actions")
        return action_map

    def _convert_single_action(self, 
                              action_data: Dict[str, Any],
                              action_map: Dict[str, Tuple[ItemAction, Dict[str, Any]]],
                              state: Dict[str, Any]) -> Optional[GeneratedAction]:
        """
        Convert single action_id reference to GeneratedAction.
        
        ### Conversion Strategy:
        Handles both standard UI element actions and custom coordinate actions.
        Standard actions use action_map lookup while custom actions process
        coordinate parameters directly for multimodal interaction scenarios.
        
        Args:
            action_data: Single action dictionary with action_id
            action_map: Mapping from action_id to ItemAction objects
            state: Current application state
            
        Returns:
            GeneratedAction object or None if conversion fails
        """
        from rvandroid_tool.constants import (
            CUSTOM_COORDINATE_ACTION_ID,
            ACTION_TYPE_CLICK,
            COORDINATE_VALIDATION_MIN,
            COORDINATE_VALIDATION_MAX
        )
        
        action_id = str(action_data["action_id"])
        params = action_data.get("params", {})
        explanation = action_data.get("explanation", f"Execute action {action_id}")
        
        # Handle custom coordinate actions
        if action_id == CUSTOM_COORDINATE_ACTION_ID:
            return self._create_custom_coordinate_action(action_data, params, explanation)
        
        # Handle standard UI element actions
        if action_id not in action_map:
            self.logger.warning(f"Action ID {action_id} not found in available actions")
            return None
            
        item_action, view_data = action_map[action_id]
        
        # Resolve coordinates for UI element action
        coordinates = self._resolve_coordinates(item_action, view_data)
        if not coordinates:
            self.logger.warning(f"Could not resolve coordinates for action {action_id}")
            return None
            
        # Process parameters for standard action
        processed_params = self._process_parameters(item_action.event.name.lower(), params)
        
        # Generate target identifier
        target = self._resolve_target(item_action, coordinates)
        
        return GeneratedAction(
            item_action=item_action,
            coordinates=coordinates,
            params=processed_params,
            target=target,
            explanation=explanation
        )

    def _create_custom_coordinate_action(self,
                                       action_data: Dict[str, Any],
                                       params: Dict[str, Any],
                                       explanation: str) -> Optional[GeneratedAction]:
        """
        Create custom coordinate action for multimodal interactions.
        
        ### Custom Action Processing:
        Processes coordinate-based actions generated from screenshot analysis,
        enabling interaction with UI elements not captured in standard UI
        descriptions. Validates coordinate parameters and creates complete
        action specification for DroidBot execution.
        
        Args:
            action_data: Action data dictionary with coordinate parameters
            params: Action parameters including coordinates
            explanation: Action explanation for debugging
            
        Returns:
            GeneratedAction for custom coordinate interaction or None if invalid
        """
        from rvandroid_tool.constants import (
            ACTION_TYPE_CLICK,
            COORDINATE_VALIDATION_MIN,
            COORDINATE_VALIDATION_MAX,
            CUSTOM_COORDINATE_ACTION_ID
        )
        
        # Extract and validate coordinates
        coordinates_list = params.get("coordinates", [])
        
        if not isinstance(coordinates_list, list) or len(coordinates_list) != 2:
            self.logger.error(f"Invalid coordinates format: {coordinates_list}")
            return None
            
        try:
            x, y = int(coordinates_list[0]), int(coordinates_list[1])
        except (ValueError, TypeError) as e:
            self.logger.error(f"Non-numeric coordinates: {coordinates_list}, error: {e}")
            return None
            
        # Validate coordinate range
        if not (COORDINATE_VALIDATION_MIN <= x <= COORDINATE_VALIDATION_MAX and
                COORDINATE_VALIDATION_MIN <= y <= COORDINATE_VALIDATION_MAX):
            self.logger.error(f"Coordinates out of valid range: ({x}, {y})")
            return None
            
        # Determine action type from parameters or default to click
        action_type = params.get("action_type", ACTION_TYPE_CLICK)
        
        # Process additional parameters based on action type
        processed_params = self._process_custom_parameters(action_type, params)
        
        # Generate target identifier for custom action
        target = f"custom:{x},{y}"
        
        # Create custom coordinate action
        custom_action = GeneratedAction(
            item_action=None,
            coordinates=(x, y),
            params=processed_params,
            target=target,
            explanation=explanation,
            custom_action_type=action_type,
            action_id=CUSTOM_COORDINATE_ACTION_ID
        )
        
        self.logger.debug(f"Created custom coordinate action at ({x}, {y}) with type {action_type}")
        return custom_action

    def _process_custom_parameters(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process parameters for custom coordinate actions.
        
        ### Parameter Processing Strategy:
        Handles action-type specific parameters for custom coordinate actions,
        ensuring compatibility with DroidBot execution while maintaining
        parameter validation and default value assignment.
        
        Args:
            action_type: Type of custom action being processed
            params: Raw parameters from LLM response
            
        Returns:
            Processed parameter dictionary
        """
        from rvandroid_tool.constants import ACTION_TYPE_SET_TEXT, ACTION_TYPE_TEXT_CHANGE
        
        processed_params = {}
        
        # Copy coordinates for DroidBot compatibility
        if "coordinates" in params:
            processed_params["coordinates"] = params["coordinates"]
        
        # Handle text input for custom actions
        if action_type in [ACTION_TYPE_SET_TEXT, ACTION_TYPE_TEXT_CHANGE]:
            text = params.get("text", "")
            if text:
                processed_params["text"] = text
                self.logger.debug(f"Added text parameter for custom action: {text}")
        
        # Handle scroll direction for custom scroll actions
        if "scroll" in action_type.lower():
            direction = params.get("direction", "DOWN").upper()
            if direction in ["UP", "DOWN", "LEFT", "RIGHT"]:
                processed_params["direction"] = direction
                self.logger.debug(f"Added direction parameter for custom scroll: {direction}")
        
        return processed_params

    def _resolve_coordinates(self, 
                           item_action: ItemAction, 
                           view_data: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        """
        Resolve screen coordinates for action execution.
        
        ### Coordinate Resolution:
        Extracts coordinates from UI element bounds data, calculating
        center point for reliable action execution. Handles various
        coordinate sources with fallback strategies.
        
        Args:
            item_action: UI element action definition
            view_data: UI element view information with bounds
            
        Returns:
            Tuple of (x, y) coordinates or None if resolution fails
        """
        # Primary: Use bounds from view data
        if view_data and "bounds" in view_data:
            bounds = view_data["bounds"]
            if bounds and len(bounds) == 2 and len(bounds[0]) == 2 and len(bounds[1]) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                return (x, y)
        
        # Secondary: Use target_view bounds
        if hasattr(item_action, 'target_view') and item_action.target_view:
            target_bounds = item_action.target_view.get("bounds")
            if target_bounds and len(target_bounds) == 2:
                x = (target_bounds[0][0] + target_bounds[1][0]) // 2
                y = (target_bounds[0][1] + target_bounds[1][1]) // 2
                return (x, y)
        
        # Fallback: Use pre-computed coordinates if available
        if hasattr(item_action, 'coordinates') and item_action.coordinates:
            return item_action.coordinates
            
        return None

    def _process_parameters(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and validate action-specific parameters.
        
        ### Parameter Processing:
        Ensures action parameters contain required fields with appropriate
        default values. Handles type-specific requirements for text input,
        scrolling, and key events.
        
        Args:
            action_type: Type of action being processed
            params: Raw parameters from LLM response
            
        Returns:
            Processed parameters dictionary with required fields
        """
        processed_params = params.copy() if params else {}
        
        # Text input actions require text parameter
        if action_type in ["set_text", "text_change"]:
            if "text" not in processed_params or not processed_params["text"]:
                processed_params["text"] = "test input"
                self.logger.debug("Added default text parameter")
        
        # Key events require key name
        elif action_type == "key_event":
            if "name" not in processed_params:
                processed_params["name"] = "BACK"
                self.logger.debug("Added default BACK key parameter")
        
        # Scroll actions require direction
        elif action_type.startswith("scroll"):
            if "direction" not in processed_params:
                direction = action_type.split('_')[-1].upper() if '_' in action_type else "DOWN"
                processed_params["direction"] = direction
                self.logger.debug(f"Added direction parameter: {direction}")
        
        return processed_params

    def _resolve_target(self, item_action: ItemAction, coordinates: Tuple[int, int]) -> str:
        """
        Generate target identifier for action execution.
        
        ### Target Resolution:
        Creates target identifier from resource_id when available,
        falling back to coordinate string for reliable action targeting.
        
        Args:
            item_action: UI element action definition
            coordinates: Screen coordinates for action
            
        Returns:
            Target identifier string
        """
        # Primary: Use resource_id from target_view
        if hasattr(item_action, 'target_view') and item_action.target_view:
            resource_id = item_action.target_view.get("resource_id")
            if resource_id:
                return resource_id
        
        # Fallback: Use coordinates as string
        return f"{coordinates[0]} {coordinates[1]}"

    def _generate_fallback_actions(self, state: Dict[str, Any]) -> List[GeneratedAction]:
        """
        Generate fallback actions when normal processing fails.
        
        ### Fallback Strategy:
        Creates basic scroll action to ensure testing continues even
        when LLM response processing fails. Provides minimal viable
        action for session continuation.
        
        Args:
            state: Current application state
            
        Returns:
            List containing single fallback action
        """
        self.logger.info("Generating fallback scroll action")
        
        # Create fallback scroll action
        fallback_action = ItemAction(
            id=9999,
            text="Fallback scroll down",
            event=WidgetEventType.SCROLL
        )
        
        return [GeneratedAction(
            item_action=fallback_action,
            coordinates=(540, 960),  # Center of typical screen
            params={"direction": "DOWN"},
            target="540 960",
            explanation="Fallback scroll action when normal processing fails"
        )]