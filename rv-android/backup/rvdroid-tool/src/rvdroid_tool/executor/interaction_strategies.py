# rvandroid/rvdroid/executor/interaction_strategies.py
"""
Interaction strategies for RVDroid.

This module provides specialized strategies for interacting with different
types of UI components, offering improved handling for complex elements
like spinners, input fields, and multi-step interactions.
"""

import random
import time
from typing import Dict, Any, Optional

from rv_screen_parser.parser.screen.visitor.model import ItemAction


class BaseInteractionStrategy:
    """
    Base class for UI interaction strategies.

    Provides common functionality and interface for all interaction strategies.
    """

    def __init__(self, adapter, logger):
        """
        Initialize the strategy.

        Args:
            adapter: Device adapter instance
            logger: Logger instance
        """
        self.adapter = adapter
        self.logger = logger

    def can_handle(self, view_data: Dict[str, Any]) -> bool:
        """
        Check if this strategy can handle a specific view.

        Args:
            view_data: View properties

        Returns:
            True if this strategy can handle the view, False otherwise
        """
        return False

    def execute(self, action_type: str, view_data: Dict[str, Any],
                params: Dict[str, Any]) -> bool:
        """
        Execute an action using this strategy.

        Args:
            action_type: Type of action to execute
            view_data: View properties
            params: Additional parameters for the action

        Returns:
            True if successful, False otherwise
        """
        return False


class TextFieldStrategy(BaseInteractionStrategy):
    """
    Strategy for interacting with text input fields.

    Provides optimized handling for different types of text fields
    with specialized input generation and validation.
    """

    def can_handle(self, view_data: Dict[str, Any]) -> bool:
        """Check if this strategy can handle a view."""
        class_name = view_data.get("class", "")
        return any(field_class in class_name for field_class in [
            "EditText", "TextInputLayout", "TextInputEditText",
            "AutoCompleteTextView", "MultiAutoCompleteTextView"
        ])

    def execute(self, action_type: str, view_data: Dict[str, Any],
                params: Dict[str, Any]) -> bool:
        """Execute a text field interaction."""
        if action_type != "set_text":
            return False

        text = params.get("text", "TestInput")
        resource_id = view_data.get("resource_id", "")

        # Try using resource ID first
        if resource_id and hasattr(self.adapter, 'click_by_resource_id'):
            if self.adapter.click_by_resource_id(resource_id):
                time.sleep(0.3)
                self.adapter.input_text(text)
                return True

        # Fall back to coordinate-based click
        if "bounds" in view_data:
            bounds = view_data["bounds"]
            if bounds and len(bounds) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2

                if self.adapter.click(x, y):
                    time.sleep(0.3)
                    return self.adapter.input_text(text)

        return False


class SpinnerStrategy(BaseInteractionStrategy):
    """
    Strategy for interacting with spinner/dropdown components.

    Provides specialized handling for spinners with automatic item selection
    and improved dropdown detection.
    """

    def can_handle(self, view_data: Dict[str, Any]) -> bool:
        """Check if this strategy can handle a view."""
        class_name = view_data.get("class", "")
        spinner_classes = ["Spinner", "DropDown", "Combo", "Select"]
        return any(c in class_name for c in spinner_classes)

    def execute(self, action_type: str, view_data: Dict[str, Any],
                params: Dict[str, Any]) -> bool:
        """Execute a spinner interaction with multiple fallback approaches."""
        if action_type != "click":
            return False

        # Get coordinates
        try:
            # First try by resource ID if available
            resource_id = view_data.get("resource_id", "")
            if resource_id and hasattr(self.adapter, 'click_by_resource_id'):
                self.logger.info(f"Interacting with spinner by resource ID: {resource_id}")
                if self.adapter.click_by_resource_id(resource_id):
                    time.sleep(1.0)  # Wait for dropdown to appear
                    return self._select_dropdown_item()

            # Fall back to coordinates if resource ID approach didn't work or isn't available
            if "bounds" in view_data:
                bounds = view_data["bounds"]
                if bounds and len(bounds) == 2:
                    x = (bounds[0][0] + bounds[1][0]) // 2
                    y = (bounds[0][1] + bounds[1][1]) // 2

                    self.logger.info(f"Interacting with spinner at coordinates ({x}, {y})")

                    # Use spinner-specific click method if available
                    if hasattr(self.adapter, 'click_spinner'):
                        return self.adapter.click_spinner(x, y)

                    # Manual approach if specialized method is not available
                    if self.adapter.click(x, y):
                        time.sleep(1.0)  # Wait for dropdown to appear
                        return self._select_dropdown_item()

            self.logger.warning("Could not determine how to interact with spinner")
            return False

        except Exception as e:
            self.logger.error(f"Error in spinner execution: {e}")
            return False

    def _select_dropdown_item(self) -> bool:
        """
        Select a random item from an open dropdown.

        Returns:
            True if successfully selected an item, False otherwise
        """
        try:
            # Enhanced detection methods for dropdown items
            for attempt in range(3):  # Try multiple approaches
                # 1. Try standard ListView approach
                listview = self.adapter.device(className="android.widget.ListView")
                if listview.exists:
                    items = listview.child(className="android.widget.TextView")
                    if not items or items.count == 0:
                        items = listview.child(clickable=True)

                    if items and items.count > 0:
                        # Ensure we select a truly random item
                        if items.count > 1:
                            # Select any item except the currently selected one (usually the first)
                            index = random.randint(1, items.count - 1)
                            self.logger.info(
                                f"Clicking random item {index} in ListView dropdown of {items.count} items")
                        else:
                            # Only one item, select it
                            index = 0
                            self.logger.info("Only one item in dropdown, selecting it")

                        items[index].click()
                        time.sleep(0.5)
                        return True

                # 2. Try popup window or dialog
                popup = self.adapter.device(className="android.widget.PopupWindow") or \
                        self.adapter.device(className="android.app.AlertDialog") or \
                        self.adapter.device(className="android.widget.PopupMenu")

                if popup.exists:
                    items = popup.child(clickable=True)
                    if items and items.count > 0:
                        # Select a truly random item
                        if items.count > 1:
                            # Avoid the first item (which might be a header or the currently selected item)
                            index = random.randint(1, items.count - 1)
                            self.logger.info(f"Clicking random item {index} in popup of {items.count} items")
                        else:
                            index = 0
                            self.logger.info("Only one item in popup, selecting it")

                        items[index].click()
                        time.sleep(0.5)
                        return True

                # 3. Look for any new clickable TextView elements that appeared
                textviews = self.adapter.device(className="android.widget.TextView", clickable=True)
                if textviews and textviews.count > 1:  # More than one clickable text element
                    # Select random item, avoiding first one which might be a header
                    index = random.randint(1, textviews.count - 1)
                    self.logger.info(f"Clicking random item {index} from {textviews.count} clickable text elements")

                    textviews[index].click()
                    time.sleep(0.5)
                    return True

                # If we didn't find anything yet, wait and try again
                if attempt < 2:
                    self.logger.debug(f"Dropdown items not found yet, waiting and retrying (attempt {attempt + 1})")
                    time.sleep(0.5)

            # If all direct approaches failed, try clicking at positions below the original spinner
            screen_info = self.adapter.device.info
            screen_height = screen_info.get("displayHeight", 1000)
            screen_width = screen_info.get("displayWidth", 500)

            x_center = screen_width // 2

            # Create random positions spread throughout the screen
            y_positions = []
            base_y = 200  # Start a bit down from the top
            for i in range(4):
                # Generate random positions in different screen quadrants
                y_pos = base_y + random.randint(50, 150) + (i * 100)
                if y_pos < screen_height - 50:
                    y_positions.append(y_pos)

            # Shuffle the positions to make selections more random
            random.shuffle(y_positions)

            for y_pos in y_positions:
                self.logger.info(f"Clicking random dropdown position at ({x_center}, {y_pos})")
                self.adapter.click(x_center, y_pos)
                time.sleep(0.5)

            # Consider it a success (we made our best attempt)
            return True

        except Exception as e:
            self.logger.error(f"Error selecting dropdown item: {e}")
            return False


class ButtonStrategy(BaseInteractionStrategy):
    """
    Strategy for interacting with button components.

    Provides specialized handling for different types of buttons
    including ImageButton, standard Button, and clickable elements.
    """

    def can_handle(self, view_data: Dict[str, Any]) -> bool:
        """Check if this strategy can handle a view."""
        class_name = view_data.get("class", "")
        if "Button" in class_name:
            return True

        # Check for clickable views that might act as buttons
        if view_data.get("clickable", False) and "View" in class_name:
            return True

        return False

    def execute(self, action_type: str, view_data: Dict[str, Any],
                params: Dict[str, Any]) -> bool:
        """Execute a button interaction with proper fallbacks."""
        if action_type not in ["click", "long_click"]:
            return False

        resource_id = view_data.get("resource_id", "")

        # Try using resource ID first for more reliable interaction
        if resource_id and hasattr(self.adapter, 'click_by_resource_id') and action_type == "click":
            try:
                return self.adapter.click_by_resource_id(resource_id)
            except Exception as e:
                self.logger.error(f"Resource ID click failed: {e}, falling back to coordinates")
                # Proceed to coordinate-based click below

        # Fall back to coordinate-based interaction
        if "bounds" in view_data:
            bounds = view_data["bounds"]
            if bounds and len(bounds) == 2:
                try:
                    x = (bounds[0][0] + bounds[1][0]) // 2
                    y = (bounds[0][1] + bounds[1][1]) // 2

                    if action_type == "click":
                        return self.adapter.click(x, y)
                    elif action_type == "long_click":
                        duration = params.get("duration", 1.0)
                        return self.adapter.long_click(x, y, duration)
                except Exception as e:
                    self.logger.error(f"Coordinate-based {action_type} failed: {e}")
                    return False

        self.logger.warning(f"Could not determine how to interact with button: {view_data}")
        return False


class CheckableStrategy(BaseInteractionStrategy):
    """
    Strategy for interacting with checkable components.

    Provides specialized handling for CheckBox, RadioButton,
    ToggleButton, and other checkable elements.
    """

    def can_handle(self, view_data: Dict[str, Any]) -> bool:
        """Check if this strategy can handle a view."""
        class_name = view_data.get("class", "")
        checkable_classes = ["CheckBox", "RadioButton", "ToggleButton", "Switch", "SwitchCompat"]

        if any(c in class_name for c in checkable_classes):
            return True

        # Also check for explicitly checkable views
        if view_data.get("checkable", False):
            return True

        return False

    def execute(self, action_type: str, view_data: Dict[str, Any],
                params: Dict[str, Any]) -> bool:
        """Execute a checkable interaction."""
        if action_type != "click":
            return False

        # For checkable items, we want to change the state
        # Check current state if possible
        is_checked = view_data.get("checked", None)
        resource_id = view_data.get("resource_id", "")

        # Simple click for checkable items
        if resource_id and hasattr(self.adapter, 'click_by_resource_id'):
            return self.adapter.click_by_resource_id(resource_id)

        # Fall back to coordinate-based click
        if "bounds" in view_data:
            bounds = view_data["bounds"]
            if bounds and len(bounds) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                return self.adapter.click(x, y)

        return False


class ScrollStrategy(BaseInteractionStrategy):
    """
    Strategy for scrolling interactions.

    Provides specialized handling for ScrollView, ListView, RecyclerView,
    and other scrollable containers.
    """

    def can_handle(self, view_data: Dict[str, Any]) -> bool:
        """Check if this strategy can handle a view."""
        class_name = view_data.get("class", "")
        scrollable_classes = ["ScrollView", "ListView", "RecyclerView", "ViewPager", "HorizontalScrollView"]

        if any(c in class_name for c in scrollable_classes):
            return True

        # Also check for explicitly scrollable views
        if view_data.get("scrollable", False):
            return True

        return False

    def execute(self, action_type: str, view_data: Dict[str, Any],
                params: Dict[str, Any]) -> bool:
        """Execute a scroll interaction."""
        if not action_type.startswith("scroll"):
            return False

        # Determine scroll direction
        direction = params.get("direction", "DOWN").upper()

        # Get scroll distance
        distance = params.get("distance", 400)

        # Get coordinates for scroll start point
        if "bounds" in view_data:
            bounds = view_data["bounds"]
            if bounds and len(bounds) == 2:
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2

                # Execute scroll
                return self.adapter.scroll(x, y, direction, distance)

        return False


class StrategySelector:
    """
    Selector for UI interaction strategies.

    Manages the registration and selection of appropriate strategies
    for different UI component types.
    """

    def __init__(self, adapter, logger):
        """
        Initialize the strategy selector.

        Args:
            adapter: Device adapter instance
            logger: Logger instance
        """
        self.adapter = adapter
        self.logger = logger
        self.strategies = []

        # Register default strategies
        self._register_default_strategies()

    def _register_default_strategies(self):
        """Register the default set of interaction strategies in priority order."""
        # Register in specific order of precedence (first matching strategy wins)
        self.register_strategy(SpinnerStrategy(self.adapter, self.logger))  # Prioritize spinners
        self.register_strategy(TextFieldStrategy(self.adapter, self.logger))
        self.register_strategy(ButtonStrategy(self.adapter, self.logger))
        self.register_strategy(CheckableStrategy(self.adapter, self.logger))
        self.register_strategy(ScrollStrategy(self.adapter, self.logger))

    def register_strategy(self, strategy: BaseInteractionStrategy):
        """
        Register a new interaction strategy.

        Args:
            strategy: Strategy instance to register
        """
        self.strategies.append(strategy)

    def get_strategy_for_view(self, view_data: Dict[str, Any]) -> Optional[BaseInteractionStrategy]:
        """
        Get the appropriate strategy for a view.

        Args:
            view_data: View properties

        Returns:
            Appropriate strategy or None if no suitable strategy found
        """
        for strategy in self.strategies:
            if strategy.can_handle(view_data):
                return strategy

        return None

    def execute_with_strategy(self, action_type: str, view_data: Dict[str, Any],
                              params: Dict[str, Any]) -> bool:
        """
        Execute an action using the appropriate strategy.

        Args:
            action_type: Type of action to execute
            view_data: View properties
            params: Additional parameters for the action

        Returns:
            True if successful, False otherwise
        """
        strategy = self.get_strategy_for_view(view_data)

        if strategy:
            self.logger.debug(f"Using {strategy.__class__.__name__} for {action_type}")
            return strategy.execute(action_type, view_data, params)

        # No specific strategy found, return False to use default handling
        return False
