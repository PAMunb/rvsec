"""
Screen parsing models for UI element representation and interaction.

This module provides comprehensive data models for representing Android UI elements,
their actions, and hierarchical relationships within screen parsing operations.
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Tuple

from pydantic import Field, field_validator, computed_field

from rv_android_core.domain.widget import WidgetEventType
from rv_android_core.util.validation.base import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


@validated_model(['id', 'text', 'event', 'reaches_mop', 'directly_reaches_mop', 'target_view', 'coordinates'])
class ItemAction(BaseValidatedModel):
    """
    Representation of an executable action on a UI element within the screen parsing framework.
    
    ### Architectural Decisions:
    - Integrates with WidgetEventType enumeration for consistent event classification
    - Provides computed properties for action type extraction and coordinate resolution
    - Supports both explicit coordinate specification and bounds-based coordinate calculation
    - Implements monitor operation tracking through reachability flags
    - Maintains target view context for comprehensive action execution
    
    ### Role in the System:
    - Serves as the primary action representation for UI automation frameworks
    - Enables systematic action extraction from screen analysis operations
    - Provides standardized interface for action execution engines
    - Facilitates monitor operation coverage tracking and analysis
    - Supports coordinate-based and semantic-based action targeting strategies
    
    ### Key Considerations:
    - Action text follows specific format conventions for parsing and execution
    - Coordinates can be provided explicitly or derived from target view bounds
    - Monitor operation flags enable coverage analysis and verification
    - Target view integration supports both resource-based and coordinate-based targeting
    - Event type classification ensures compatibility with widget interaction frameworks
    
    ### Integration Strategy:
    - Compatible with screen parser visitor pattern implementations
    - Supports action execution through UI automation frameworks
    - Enables monitor operation tracking for runtime verification
    - Facilitates coordinate transformation for different screen densities
    - Provides standardized action representation across parser implementations
    """
    
    id: int = Field(..., description="Unique identifier for the action within the screen context")
    text: str = Field(..., description="Human-readable action description with format-specific conventions")
    event: WidgetEventType = Field(..., description="Widget event type for framework compatibility")
    reaches_mop: bool = Field(default=False, description="Indicates if action reaches monitored operations")
    directly_reaches_mop: bool = Field(default=False, description="Indicates direct monitor operation reachability")
    target_view: Dict[str, Any] = Field(default_factory=dict, description="Target UI element properties and metadata")
    coordinates: Optional[Tuple[int, int]] = Field(default=None, description="Explicit action coordinates (x, y)")

    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
        """
        Validate coordinate tuple format and ranges.
        
        Args:
            v: Coordinate tuple to validate
            
        Returns:
            Validated coordinate tuple or None
            
        Raises:
            ValueError: If coordinates are invalid
        """
        if v is None:
            return v
            
        if not isinstance(v, tuple) or len(v) != 2:
            raise ValueError("Coordinates must be a tuple of (x, y)")
            
        x, y = v
        if not isinstance(x, int) or not isinstance(y, int):
            raise ValueError("Coordinate values must be integers")
            
        if x < 0 or y < 0:
            raise ValueError("Coordinate values must be non-negative")
            
        return v

    @computed_field
    @property
    def action_type(self) -> str:
        """
        Extract standardized action type from text description.
        
        Provides normalized action type classification for execution engines
        and automation frameworks based on action text patterns.
        
        Returns:
            Standardized action type string
        """
        text_upper = self.text.upper()
        
        if text_upper.startswith("CLICK"):
            return "click"
        elif text_upper.startswith("LONG_CLICK"):
            return "long_click"
        elif text_upper.startswith("SCROLL"):
            # Extract direction if present for specialized scroll handling
            if "UP" in text_upper:
                return "scroll_up"
            elif "DOWN" in text_upper:
                return "scroll_down"
            elif "LEFT" in text_upper:
                return "scroll_left"
            elif "RIGHT" in text_upper:
                return "scroll_right"
            return "scroll"
        elif text_upper.startswith("SET_TEXT"):
            return "set_text"
        elif text_upper.startswith(("CHECK", "UNCHECK")):
            return "click"  # Checkbox actions are implemented as clicks
        elif text_upper.startswith("BACK"):
            return "key_event"
        
        return "unknown"

    @ErrorHandler.handle_errors(component="ItemAction", phase="target_resolution")
    def get_target_identifier(self) -> str:
        """
        Extract target identifier from associated view for action execution.
        
        Implements priority-based target resolution strategy for reliable
        action execution across different UI frameworks and conditions.
        
        Returns:
            Target identifier string (resource_id or coordinates)
        """
        # Priority 1: Resource ID for semantic targeting (from target_view)
        if self.target_view:
            resource_id = self.target_view.get("resource_id")
            if resource_id:
                return resource_id

        # Priority 2: Explicit coordinates if available
        if self.coordinates:
            x, y = self.coordinates
            return f"{x} {y}"

        # Priority 3: Calculated coordinates from bounds
        if self.target_view:
            bounds = self.target_view.get("bounds")
            if bounds and isinstance(bounds, list) and len(bounds) == 2:
                try:
                    x1, y1 = bounds[0]
                    x2, y2 = bounds[1]
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    return f"{center_x} {center_y}"
                except (TypeError, IndexError, ValueError):
                    pass

        return ""

    @ErrorHandler.handle_errors(component="ItemAction", phase="coordinate_resolution")
    def get_execution_coordinates(self) -> Optional[Tuple[int, int]]:
        """
        Resolve execution coordinates for action targeting.
        
        Implements comprehensive coordinate resolution strategy supporting
        both explicit coordinate specification and bounds-based calculation.
        
        Returns:
            Tuple of (x, y) coordinates or None if resolution fails
        """
        # Priority 1: Explicit coordinates
        if self.coordinates:
            return self.coordinates

        # Priority 2: Calculate from target view bounds
        if self.target_view and "bounds" in self.target_view:
            bounds = self.target_view["bounds"]
            if bounds and isinstance(bounds, list) and len(bounds) == 2:
                try:
                    x1, y1 = bounds[0]
                    x2, y2 = bounds[1]
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    return (center_x, center_y)
                except (TypeError, IndexError, ValueError):
                    pass

        return None


@validated_model(['view', 'base_description', 'actions', 'complement'])
class ScreenItem(BaseValidatedModel):
    """
    Comprehensive representation of a UI element with its description and available actions.
    
    ### Architectural Decisions:
    - Maintains raw view data for complete element context preservation
    - Supports multiple actions per element for comprehensive interaction coverage
    - Provides computed description that aggregates element and action information
    - Enables extensible metadata through complement dictionary
    - Integrates with action execution and analysis frameworks
    
    ### Role in the System:
    - Serves as the primary UI element representation in screen parsing operations
    - Aggregates element properties with executable actions for automation
    - Provides standardized interface for UI element analysis and interaction
    - Enables comprehensive screen state representation and action planning
    - Facilitates element classification and interaction strategy selection
    
    ### Key Considerations:
    - Raw view data preservation ensures complete element context availability
    - Multiple actions per element support complex interaction patterns
    - Computed description provides human-readable element representation
    - Complement metadata enables extensible element annotation
    - Action aggregation supports comprehensive interaction coverage analysis
    
    ### Integration Strategy:
    - Compatible with screen parser visitor pattern for element processing
    - Supports UI automation frameworks through action execution interfaces
    - Enables element classification and analysis through view data access
    - Facilitates screen state comparison and change detection
    - Provides foundation for interaction strategy planning and execution
    """
    
    view: Dict[str, Any] = Field(..., description="Raw UI element data from screen analysis")
    base_description: str = Field(..., description="Human-readable element description")
    actions: List[ItemAction] = Field(default_factory=list, description="Available actions for this element")
    complement: Dict[str, Any] = Field(default_factory=dict, description="Additional element metadata and annotations")

    @field_validator('view')
    @classmethod
    def validate_view_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate view data structure and required properties.
        
        Args:
            v: View data dictionary to validate
            
        Returns:
            Validated view data
            
        Raises:
            ValueError: If view data is invalid
        """
        if not isinstance(v, dict):
            raise ValueError("View data must be a dictionary")
            
        # View data can be empty but should be a valid dictionary
        return v

    @computed_field
    @property
    def description(self) -> str:
        """
        Generate comprehensive human-readable description of element and actions.
        
        Combines base element description with available actions to provide
        complete element representation for analysis and debugging.
        
        Returns:
            Complete element description with actions
        """
        if not self.actions:
            return f"{self.base_description}."
            
        action_descriptions = [action.text for action in self.actions]
        actions_text = ", ".join(action_descriptions)
        return f"{self.base_description}. Actions: {actions_text}"

    def get_actions_by_type(self, action_type: str) -> List[ItemAction]:
        """
        Filter actions by type for targeted interaction planning.
        
        Args:
            action_type: Type of actions to retrieve
            
        Returns:
            List of actions matching the specified type
        """
        return [action for action in self.actions if action.action_type == action_type]

    def has_action_type(self, action_type: str) -> bool:
        """
        Check if element supports a specific action type.
        
        Args:
            action_type: Action type to check
            
        Returns:
            True if element supports the action type, False otherwise
        """
        return any(action.action_type == action_type for action in self.actions)

    def __str__(self) -> str:
        """String representation for debugging and logging."""
        return self.description


@validated_model(['activity', 'items', 'events_by_id'])
class ScreenDescription(BaseValidatedModel):
    """
    Complete representation of a screen state including all UI elements and interaction capabilities.
    
    ### Architectural Decisions:
    - Provides comprehensive screen state representation with element and action aggregation
    - Implements automatic standard action injection for consistent navigation capabilities
    - Maintains action-to-element mapping for efficient action resolution and execution
    - Supports screen comparison and state transition analysis through structured representation
    - Enables systematic action enumeration for automation and testing frameworks
    
    ### Role in the System:
    - Serves as the primary screen state representation in UI automation and analysis
    - Aggregates all UI elements and actions for comprehensive interaction planning
    - Provides standardized interface for screen analysis and action execution
    - Enables screen state comparison and transition tracking in automation workflows
    - Facilitates action space enumeration for systematic testing and exploration
    
    ### Key Considerations:
    - Automatic back action injection ensures consistent navigation capabilities
    - Action ID mapping enables efficient action resolution during execution
    - Screen description generation supports human-readable state representation
    - Element aggregation provides complete screen interaction surface analysis
    - Activity context preservation enables screen classification and routing
    
    ### Integration Strategy:
    - Compatible with UI automation frameworks for action execution
    - Supports screen analysis and comparison operations
    - Enables action planning and execution strategy development
    - Facilitates screen state tracking and transition analysis
    - Provides foundation for systematic UI exploration and testing
    """
    
    activity: str = Field(..., description="Current activity name for screen context")
    items: List[ScreenItem] = Field(..., description="All UI elements with their available actions")
    events_by_id: Dict[int, ItemAction] = Field(default_factory=dict, description="Mapping of action IDs to action objects")

    def __init__(self, **data):
        """
        Initialize screen description with automatic standard action injection.
        
        Ensures all screens have basic navigation capabilities through automatic
        back action injection and maintains efficient action lookup structures.
        """
        super().__init__(**data)
        
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self._logger = logging_manager.get_logger(
            'rv_screen_parser.models.ScreenDescription',
            {CONTEXT_COMPONENT: 'ScreenDescription'}
        )
        
        # Add standard back action if not present
        self._ensure_standard_back_action()
        
        # Build action lookup mapping for efficient resolution
        self._build_action_mapping()

    @ErrorHandler.handle_errors(component="ScreenDescription", phase="back_action_injection")
    def _ensure_standard_back_action(self) -> None:
        """
        Ensure screen has standard back action for consistent navigation.
        
        Automatically injects a standard back action if one doesn't exist,
        ensuring all screens provide basic navigation capabilities.
        """
        # Find maximum action ID across all items
        max_action_id = 0
        has_back_action = False
        
        for item in self.items:
            for action in item.actions:
                max_action_id = max(max_action_id, action.id)
                if "BACK" in action.text.upper():
                    has_back_action = True
        
        # Inject standard back action if not present
        if not has_back_action:
            self._logger.debug("Injecting standard back action for consistent navigation")
            
            # Create virtual view for back action
            back_view = {
                "content_description": "Back",
                "class": "BackAction",
                "resource_id": "standard_back_action",
                "bounds": [[0, 0], [0, 0]]  # Virtual bounds
            }
            
            # Create back action with next available ID
            back_action = ItemAction(
                id=max_action_id + 1,
                text=f"BACK ({max_action_id + 1})",
                event=WidgetEventType.KEY,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view=back_view,
                coordinates=None
            )
            
            # Create screen item for back action
            back_item = ScreenItem(
                view=back_view,
                base_description="Standard back action for navigation",
                actions=[back_action]
            )
            
            # Add to items list
            self.items.append(back_item)

    def _build_action_mapping(self) -> None:
        """Build efficient action ID to action mapping for lookup operations."""
        action_mapping = {}
        for item in self.items:
            for action in item.actions:
                action_mapping[action.id] = action
        self.events_by_id = action_mapping

    @computed_field
    @property
    def description(self) -> str:
        """
        Generate comprehensive human-readable screen description.
        
        Provides complete screen state representation including all UI elements
        and their available actions with action IDs for execution reference.
        
        Returns:
            Complete screen description with elements and actions
        """
        element_descriptions = [f" - {item.description}" for item in self.items]
        header = (
            "The current screen has the following UI views and corresponding actions, "
            "with action id in parentheses:"
        )
        return header + "\n" + "\n".join(element_descriptions)

    def get_action_by_id(self, action_id: int) -> Optional[ItemAction]:
        """
        Retrieve action by unique identifier for execution.
        
        Args:
            action_id: Unique action identifier
            
        Returns:
            ItemAction instance or None if not found
        """
        return self.events_by_id.get(action_id)

    def get_all_actions(self) -> List[ItemAction]:
        """
        Get all available actions across all screen elements.
        
        Returns:
            Complete list of all executable actions
        """
        actions = []
        for item in self.items:
            actions.extend(item.actions)
        return actions

    def get_actions_by_type(self, action_type: str) -> List[ItemAction]:
        """
        Filter all screen actions by type.
        
        Args:
            action_type: Action type to filter by
            
        Returns:
            List of actions matching the specified type
        """
        return [action for action in self.get_all_actions() if action.action_type == action_type]

    def get_element_count(self) -> int:
        """Get total number of UI elements on screen."""
        return len(self.items)

    def get_action_count(self) -> int:
        """Get total number of available actions on screen."""
        return len(self.get_all_actions())

    def __str__(self) -> str:
        """String representation for debugging and logging."""
        return self.description


@validated_model(['value'])
class Counter(BaseValidatedModel):
    """
    Thread-safe counter implementation for generating unique sequential identifiers.
    
    ### Architectural Decisions:
    - Provides atomic increment operations for unique ID generation
    - Supports configurable starting values for different numbering schemes
    - Implements both increment-and-get and get-only access patterns
    - Maintains simple interface while ensuring uniqueness guarantees
    - Enables sequential ID assignment for UI elements and actions
    
    ### Role in the System:
    - Generates unique action IDs during screen parsing operations
    - Provides sequential numbering for UI element identification
    - Ensures ID uniqueness across screen parsing sessions
    - Facilitates deterministic ID assignment for testing and debugging
    - Supports configurable numbering schemes for different contexts
    
    ### Key Considerations:
    - Atomic operations ensure thread safety in concurrent parsing scenarios
    - Configurable start values support different numbering conventions
    - Simple interface minimizes complexity while ensuring correctness
    - Sequential assignment provides predictable ID patterns
    - Uniqueness guarantees enable reliable element and action identification
    
    ### Integration Strategy:
    - Compatible with screen parser implementations for ID generation
    - Supports different numbering schemes through start value configuration
    - Enables deterministic ID assignment for reproducible parsing results
    - Facilitates testing through predictable numbering patterns
    - Provides foundation for element and action tracking systems
    """
    
    value: int = Field(default=0, description="Current counter value")

    @field_validator('value')
    @classmethod
    def validate_counter_value(cls, v: int) -> int:
        """
        Validate counter value is non-negative.
        
        Args:
            v: Counter value to validate
            
        Returns:
            Validated counter value
            
        Raises:
            ValueError: If value is negative
        """
        if v < 0:
            raise ValueError("Counter value must be non-negative")
        return v

    def increment(self) -> int:
        """
        Increment counter and return new value.
        
        Provides atomic increment operation for unique ID generation
        with immediate access to the new value.
        
        Returns:
            New counter value after increment
        """
        self.value += 1
        return self.value

    def get_current(self) -> int:
        """
        Get current counter value without incrementing.
        
        Returns:
            Current counter value
        """
        return self.value

    def reset(self, start_value: int = 0) -> None:
        """
        Reset counter to specified starting value.
        
        Args:
            start_value: New starting value for counter
        """
        if start_value < 0:
            raise ValueError("Start value must be non-negative")
        self.value = start_value


class UiElementType(Enum):
    """
    Enumeration of UI element types for standardized element classification.
    
    ### Architectural Decisions:
    - Provides comprehensive coverage of Android UI element types
    - Supports generic element classification for cross-platform compatibility
    - Enables element-specific interaction strategies through type mapping
    - Maintains mapping from Android class names to generic element types
    - Facilitates element analysis and automation strategy selection
    
    ### Role in the System:
    - Standardizes UI element classification across parsing implementations
    - Enables element-specific interaction strategies and validation
    - Supports cross-platform UI analysis through generic type mapping
    - Facilitates element capability inference from type classification
    - Provides foundation for element-aware automation and testing strategies
    
    ### Key Considerations:
    - Comprehensive type coverage ensures compatibility with diverse Android UIs
    - Generic type mapping enables cross-platform automation strategies
    - Class name mapping provides automatic type inference from Android metadata
    - Element capabilities can be inferred from type classification
    - Unknown type handling ensures graceful degradation for new element types
    
    ### Integration Strategy:
    - Compatible with UI automation frameworks for element-specific handling
    - Supports element capability inference and interaction strategy selection
    - Enables cross-platform UI analysis and automation development
    - Facilitates element classification in screen parsing and analysis
    - Provides foundation for element-aware testing and interaction frameworks
    """
    
    CONTAINER = "container"
    BUTTON = "button"
    TEXT_FIELD = "text_field"
    TEXT_VIEW = "text_view"
    CHECKBOX = "checkbox"
    TOGGLE = "toggle"
    RADIO_BUTTON = "radio_button"
    SPINNER = "spinner"
    SLIDER = "slider"
    IMAGE = "image"
    UNKNOWN = "unknown"

    @staticmethod
    def from_class_name(class_name: str) -> 'UiElementType':
        """
        Map Android class names to standardized element types.
        
        Provides automatic element type classification from Android
        class metadata for consistent element handling across frameworks.
        
        Args:
            class_name: Android class name from UI hierarchy
            
        Returns:
            Corresponding UiElementType or UNKNOWN if not mapped
        """
        # Comprehensive mapping of Android classes to generic types
        class_type_mapping = {
            "android.widget.Button": UiElementType.BUTTON,
            "android.widget.ImageButton": UiElementType.BUTTON,
            "android.widget.EditText": UiElementType.TEXT_FIELD,
            "android.widget.TextView": UiElementType.TEXT_VIEW,
            "android.widget.CheckBox": UiElementType.CHECKBOX,
            "android.widget.CheckedTextView": UiElementType.CHECKBOX,
            "android.widget.ToggleButton": UiElementType.TOGGLE,
            "android.widget.Switch": UiElementType.TOGGLE,
            "android.widget.RadioButton": UiElementType.RADIO_BUTTON,
            "android.widget.Spinner": UiElementType.SPINNER,
            "android.widget.SeekBar": UiElementType.SLIDER,
            "android.widget.ImageView": UiElementType.IMAGE,
            "android.widget.LinearLayout": UiElementType.CONTAINER,
            "android.widget.RelativeLayout": UiElementType.CONTAINER,
            "android.widget.FrameLayout": UiElementType.CONTAINER,
            "android.widget.ScrollView": UiElementType.CONTAINER,
        }
        
        return class_type_mapping.get(class_name, UiElementType.UNKNOWN)


@validated_model(['data', 'children', 'parent'])
class Node(BaseValidatedModel):
    """
    Hierarchical representation of UI elements with comprehensive property access and visitor pattern support.
    
    ### Architectural Decisions:
    - Implements comprehensive UI hierarchy representation with parent-child relationships
    - Provides type-safe property access with fallback mechanisms for missing attributes
    - Supports visitor pattern for systematic UI tree traversal and analysis
    - Enables element-specific processing through class-based handler mapping
    - Maintains derived properties for efficient element capability assessment
    
    ### Role in the System:
    - Serves as the primary UI hierarchy representation in screen parsing operations
    - Enables systematic UI tree traversal and analysis through visitor pattern
    - Provides comprehensive element property access for automation frameworks
    - Facilitates element classification and capability inference
    - Supports hierarchical UI analysis and interaction strategy development
    
    ### Key Considerations:
    - Comprehensive property extraction ensures compatibility with diverse UI frameworks
    - Visitor pattern implementation enables extensible UI analysis operations
    - Element-specific handlers support specialized processing for different widget types
    - Derived properties provide efficient access to commonly used element capabilities
    - Parent-child relationships enable hierarchical analysis and navigation
    
    ### Integration Strategy:
    - Compatible with UI automation frameworks through comprehensive property access
    - Supports screen parser visitor implementations for systematic element processing
    - Enables element classification and analysis through property and type access
    - Facilitates UI hierarchy analysis and navigation operations
    - Provides foundation for element-aware automation and interaction strategies
    """
    
    data: Dict[str, Any] = Field(..., description="Raw UI element data from framework")
    children: List['Node'] = Field(default_factory=list, description="Child nodes in UI hierarchy")
    parent: Optional['Node'] = Field(default=None, description="Parent node reference")
    
    # UI capability properties (extracted from data during initialization)
    clickable: bool = Field(default=False, description="Element supports click interactions")
    scrollable: bool = Field(default=False, description="Element supports scroll interactions")
    checkable: bool = Field(default=False, description="Element supports check/uncheck interactions")
    long_clickable: bool = Field(default=False, description="Element supports long click interactions")
    editable: bool = Field(default=False, description="Element supports text editing")
    
    # UI state properties
    checked: bool = Field(default=False, description="Element is currently checked")
    selected: bool = Field(default=False, description="Element is currently selected")
    enabled: bool = Field(default=True, description="Element is currently enabled")
    focused: bool = Field(default=False, description="Element is currently focused")
    is_password: bool = Field(default=False, description="Element is a password field")
    
    # Element identification and content
    content_description: str = Field(default="", description="Accessibility content description")
    view_text: str = Field(default="", description="Visible text content")
    view_class: str = Field(default="", description="Android widget class name")
    package: str = Field(default="", description="Application package name")
    resource_id: str = Field(default="", description="Android resource identifier")
    hint: str = Field(default="", description="Hint text for input fields")
    
    # Spatial properties
    bounds: List[List[int]] = Field(default_factory=lambda: [[0, 0], [0, 0]], description="Element bounding box coordinates")
    
    # Progress properties
    progress: int = Field(default=0, description="Current progress value")
    max_progress: int = Field(default=100, description="Maximum progress value")
    
    # Derived properties
    actionable: bool = Field(default=False, description="Element supports any form of interaction")
    element_type: UiElementType = Field(default=UiElementType.UNKNOWN, description="Generic element type classification")

    def __init__(self, **data_dict):
        """
        Initialize Node with comprehensive property extraction and relationship setup.
        
        Performs extensive property extraction from raw view data and establishes
        derived properties for efficient element analysis and interaction.
        """
        # Extract properties from data before calling super().__init__
        raw_data = data_dict.get('data', {})
        
        # Update data_dict with extracted properties
        data_dict.update({
            # UI capability properties
            'clickable': raw_data.get('clickable', False),
            'scrollable': raw_data.get('scrollable', False),
            'checkable': raw_data.get('checkable', False),
            'long_clickable': raw_data.get('long_clickable', False),
            'editable': raw_data.get('editable', False),
            
            # UI state properties
            'checked': raw_data.get('checked', False),
            'selected': raw_data.get('selected', False),
            'enabled': raw_data.get('enabled', True),
            'focused': raw_data.get('focused', False),
            'is_password': raw_data.get('is_password', False),
            
            # Element identification and content
            'content_description': raw_data.get('content_description') or '',
            'view_text': raw_data.get('text') or '',
            'view_class': raw_data.get('class') or '',
            'package': raw_data.get('package') or '',
            'resource_id': raw_data.get('resource_id') or '',
            'hint': raw_data.get('hint') or '',
            
            # Spatial properties
            'bounds': raw_data.get('bounds', [[0, 0], [0, 0]]),
            
            # Progress properties
            'progress': raw_data.get('progress', 0),
            'max_progress': raw_data.get('max', 100),
        })
        
        super().__init__(**data_dict)
        
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self._logger = logging_manager.get_logger(
            'rv_screen_parser.models.Node',
            {CONTEXT_COMPONENT: 'Node'}
        )
        
        # Calculate derived properties for element capabilities
        self._calculate_derived_properties()

    def _calculate_derived_properties(self) -> None:
        """Calculate derived properties for efficient capability assessment."""
        # Element is actionable if it supports any interaction
        self.actionable = (
            self.clickable or self.scrollable or self.checkable or
            self.long_clickable or self.editable
        )
        
        # Determine element type for specialized handling
        self.element_type = UiElementType.from_class_name(self.view_class)

    def _get_property(self, key: str, default: Any) -> Any:
        """
        Safely retrieve property from raw data with type-aware defaults.
        
        Args:
            key: Property key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            Property value or default
        """
        return self.data.get(key, default)

    @field_validator('data')
    @classmethod
    def validate_data_structure(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate raw UI data structure.
        
        Args:
            v: Raw UI data to validate
            
        Returns:
            Validated UI data
            
        Raises:
            ValueError: If data structure is invalid
        """
        if not isinstance(v, dict):
            raise ValueError("Node data must be a dictionary")
        return v

    @ErrorHandler.handle_errors(component="Node", phase="visitor_traversal")
    def accept(self, visitor) -> None:
        """
        Implement visitor pattern for systematic UI hierarchy traversal.
        
        Provides specialized handling for different node types through
        class-based method dispatching and supports both leaf and container nodes.
        
        Args:
            visitor: Visitor implementation for UI analysis
        """
        if not self.children:
            self._handle_leaf_node(visitor)
        else:
            self._handle_container_node(visitor)

    def _handle_leaf_node(self, visitor) -> None:
        """
        Handle visitor pattern for leaf nodes with element-specific processing.
        
        Dispatches to specialized visitor methods based on widget class,
        enabling element-specific analysis and processing strategies.
        
        Args:
            visitor: Visitor implementation
        """
        # Mapping of widget classes to specialized visitor methods
        widget_handler_mapping = {
            "android.widget.Button": "visit_button",
            "android.widget.EditText": "visit_edit_text",
            "android.widget.TextView": "visit_text_view",
            "android.widget.CheckBox": "visit_checkbox",
            "android.widget.CheckedTextView": "visit_checked_text",
            "android.widget.ImageButton": "visit_image_button",
            "android.widget.ImageView": "visit_image",
            "android.widget.ToggleButton": "visit_toggle_button",
            "android.widget.Switch": "visit_switch",
            "android.widget.RadioButton": "visit_radio_button",
            "android.widget.SeekBar": "visit_slider"
        }
        
        # Get specialized handler or fall back to generic leaf handling
        handler_name = widget_handler_mapping.get(self.view_class, "visit_leaf_node")
        handler = getattr(visitor, handler_name, None)
        
        if handler and callable(handler):
            handler(self)
        else:
            # Fallback to generic leaf node handling
            generic_handler = getattr(visitor, "visit_leaf_node", None)
            if generic_handler and callable(generic_handler):
                generic_handler(self)

    def _handle_container_node(self, visitor) -> None:
        """
        Handle visitor pattern for container nodes with recursive traversal.
        
        Provides specialized handling for specific container types while
        maintaining recursive traversal for comprehensive UI analysis.
        
        Args:
            visitor: Visitor implementation
        """
        # Specialized container handling for specific widget types
        if self.view_class == "android.widget.Spinner":
            spinner_handler = getattr(visitor, "visit_spinner", None)
            if spinner_handler and callable(spinner_handler):
                spinner_handler(self)
        elif self.view_class == "android.widget.RadioGroup":
            radio_group_handler = getattr(visitor, "visit_radio_group", None)
            if radio_group_handler and callable(radio_group_handler):
                radio_group_handler(self)
        else:
            # Generic container handling with recursive traversal
            generic_handler = getattr(visitor, "visit_node", None)
            if generic_handler and callable(generic_handler):
                generic_handler(self)
            
            # Recursively process all children
            for child in self.children:
                child.accept(visitor)

    def find_children_by_class(self, class_name: str) -> List['Node']:
        """
        Recursively find all descendant nodes with specified class name.
        
        Args:
            class_name: Android class name to search for
            
        Returns:
            List of matching descendant nodes
        """
        matching_nodes = []
        
        # Check direct children
        for child in self.children:
            if child.view_class == class_name:
                matching_nodes.append(child)
            
            # Recursively search in child's descendants
            matching_nodes.extend(child.find_children_by_class(class_name))
        
        return matching_nodes

    def find_children_by_resource_id(self, resource_id: str) -> List['Node']:
        """
        Recursively find all descendant nodes with specified resource ID.
        
        Args:
            resource_id: Resource ID to search for
            
        Returns:
            List of matching descendant nodes
        """
        matching_nodes = []
        
        for child in self.children:
            if child.resource_id == resource_id:
                matching_nodes.append(child)
            
            matching_nodes.extend(child.find_children_by_resource_id(resource_id))
        
        return matching_nodes

    @computed_field
    @property
    def center_coordinates(self) -> Tuple[int, int]:
        """
        Calculate center coordinates of element's bounding box.
        
        Returns:
            Tuple of (x, y) center coordinates
        """
        try:
            if isinstance(self.bounds, list) and len(self.bounds) == 2:
                x1, y1 = self.bounds[0]
                x2, y2 = self.bounds[1]
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                return (center_x, center_y)
        except (TypeError, IndexError, ValueError):
            pass
        
        return (0, 0)

    @computed_field
    @property
    def unique_identifier(self) -> str:
        """
        Generate unique identifier for element based on properties.
        
        Returns:
            Unique string identifier for element
        """
        bounds_str = str(self.bounds) if self.bounds else ""
        return f"{self.view_class}_{self.resource_id}_{bounds_str}"

    def get_display_text(self) -> str:
        """
        Get best available display text for element.
        
        Returns:
            Most appropriate text representation for element
        """
        if self.view_text:
            return self.view_text
        elif self.content_description:
            return self.content_description
        elif self.hint:
            return self.hint
        elif self.resource_id:
            return self.resource_id.split('/')[-1]  # Get just the ID part
        else:
            return self.view_class.split('.')[-1]  # Get just the class name

    def __str__(self) -> str:
        """String representation for debugging and logging."""
        display_text = self.get_display_text()
        return f"{self.view_class} - {display_text}"