# rvandroid/analysis/patterns/navigation_detector.py
"""
Navigation pattern detector implementation.

This module provides a specialized detector for navigation patterns in Android applications.
It identifies navigation drawers, bottom navigation bars, and other navigation structures.
"""

from typing import List, Optional, Tuple

from rv_android_core.analysis.patterns.pattern_data import PatternType, PatternResult
from rv_android_core.analysis.patterns.pattern_detector import BasePatternDetector
from rv_screen_parser.parser.screen.visitor.model import ScreenItem, ScreenDescription
from rv_android_core.util.error.error_handler import ErrorHandler


class NavigationDetector(BasePatternDetector):
    """
    Detector for navigation patterns in UI.

    ### Architectural Decisions:
    - Implements specialized navigation detection focusing on common Android patterns
    - Identifies primary navigation structures like drawers, bottom bars, and nav rails
    - Uses DOM-based analysis with normalized node structure
    - Applies confidence scoring based on structural patterns and UI conventions

    ### Role in the System:
    - Provides reliable navigation pattern detection for batch action generation
    - Enables systematic exploration of application navigation
    - Enhances testing effectiveness by supporting navigation-focused action sequences
    - Facilitates thorough app structure exploration
    """

    def __init__(self):
        """Initialize the navigation detector."""
        super().__init__()
        self.error_handler = ErrorHandler.get_instance()

    @property
    def pattern_type(self) -> PatternType:
        """Get the pattern type."""
        return PatternType.NAVIGATION

    def detect(self, screen: ScreenDescription) -> PatternResult:
        """
        Detect navigation patterns in a screen.

        Args:
            screen: Parsed screen description

        Returns:
            PatternResult with detection results
        """
        self.logger.debug(f"Detecting navigation patterns in screen with {len(screen.items)} items")

        # Initialize pattern result
        result = self.create_base_result(PatternType.NAVIGATION)

        # Check if there are enough items to form a pattern
        if len(screen.items) < 3:
            self.logger.debug("Not enough items for a navigation pattern")
            return result

        # Check for different navigation patterns
        drawer_result = self._detect_navigation_drawer(screen)
        bottom_nav_result = self._detect_bottom_navigation(screen)
        side_nav_result = self._detect_side_navigation(screen)

        # Use the pattern with highest confidence
        nav_patterns = [
            (drawer_result, "drawer"),
            (bottom_nav_result, "bottom_navigation"),
            (side_nav_result, "side_navigation")
        ]

        best_pattern = max(nav_patterns, key=lambda x: x[0][0])
        confidence, elements = best_pattern[0]
        nav_type = best_pattern[1]

        if confidence < 0.6:
            self.logger.debug(f"No strong navigation pattern detected (confidence: {confidence:.2f})")
            return result

        # Set pattern confidence and properties
        result.confidence = confidence
        result.properties["navigation_type"] = nav_type
        result.properties["item_count"] = len(elements)
        result.elements_count = len(elements)

        # Apply pattern data to elements
        for i, item in enumerate(elements):
            if i == 0 and nav_type == "drawer":
                # First element is the drawer container
                role = "container"
                props = {
                    "is_container": True,
                    "navigation_type": nav_type,
                    "item_index": i
                }
            else:
                # Navigation items
                role = "navigation_item"
                props = {
                    "is_container": False,
                    "navigation_type": nav_type,
                    "item_index": i,
                    "clickable": item.view.get("clickable", False),
                    "has_click_action": any(a.event == "click" for a in item.actions)
                }

                # Add text if available
                if "text" in item.view:
                    props["text"] = item.view["text"]

            pattern_data = self.create_pattern_data(
                item,
                role=role,
                confidence=confidence,
                properties=props
            )
            self.apply_pattern_to_item(item, pattern_data)

        self.logger.debug(f"Detected {nav_type} navigation pattern with confidence {confidence:.2f}, "
                          f"{len(elements)} elements")

        return result

    def _detect_navigation_drawer(self, screen: ScreenDescription) -> Tuple[float, List[ScreenItem]]:
        """
        Detect navigation drawer pattern.

        Args:
            screen: Parsed screen description

        Returns:
            Tuple of (confidence, list of drawer elements)
        """
        # Look for drawer layout or similar container
        potential_drawers = []

        for item in screen.items:
            view = item.view

            # Skip invisible elements
            if not self.is_visible(item):
                continue

            # Check class name
            class_name = view.get("class", "").lower()
            drawer_score = 0.0

            # Direct drawer classes
            if "drawerlayout" in class_name:
                drawer_score += 0.7
            elif "navigationview" in class_name:
                drawer_score += 0.6
            elif "slidingpane" in class_name:
                drawer_score += 0.5

            # Check resource ID
            resource_id = self.get_resource_id(view)
            if any(drawer_hint in resource_id for drawer_hint in [
                "drawer", "navigation", "nav_view", "sidebar", "menu"
            ]):
                drawer_score += 0.3

            # Check position and size - drawers are typically full height and to the side
            bounds = view.get("bounds", {})
            if bounds:
                width, height = self.get_width_height(bounds)

                # Estimated screen dimensions
                screen_width, screen_height = self.estimate_screen_dimensions(screen)

                # Is it tall enough to be a drawer?
                if height >= screen_height * 0.7:
                    drawer_score += 0.2

                # Is it at the edge of the screen?
                left = bounds[0][0]
                right = bounds[1][0]

                if left <= 5:  # Left edge
                    drawer_score += 0.2
                elif right >= screen_width - 5:  # Right edge (rare but possible)
                    drawer_score += 0.1

            # Check for navigation-like elements
            children = self.get_direct_children(item, screen)
            nav_items = self._count_navigation_items(children)

            if nav_items >= 3:
                drawer_score += min(0.3, nav_items / 20)  # Up to 0.3 for many nav items

            if drawer_score >= 0.4:
                potential_drawers.append((item, drawer_score, children))

        # If no potential drawers, look for the drawer toggle button
        if not potential_drawers:
            # Look for hamburger menu button
            hamburger_button = self._find_hamburger_button(screen)
            if hamburger_button:
                return 0.5, [hamburger_button]

            return 0.0, []

        # Return the most likely drawer and its elements
        best_drawer = max(potential_drawers, key=lambda x: x[1])
        drawer_item, confidence, children = best_drawer

        # Add drawer item and navigation items
        elements = [drawer_item] + self._filter_navigation_items(children)

        return confidence, elements

    def _detect_bottom_navigation(self, screen: ScreenDescription) -> Tuple[float, List[ScreenItem]]:
        """
        Detect bottom navigation bar pattern.

        Args:
            screen: Parsed screen description

        Returns:
            Tuple of (confidence, list of bottom navigation elements)
        """
        # Look for bottom navigation container
        potential_bottom_nav = []

        for item in screen.items:
            view = item.view

            # Skip invisible elements
            if not self.is_visible(item):
                continue

            # Check class name
            class_name = view.get("class", "").lower()
            bottom_nav_score = 0.0

            # Direct bottom navigation classes
            if "bottomnavigation" in class_name:
                bottom_nav_score += 0.8
            elif "bottomappbar" in class_name:
                bottom_nav_score += 0.7
            elif "tabbar" in class_name:
                bottom_nav_score += 0.5

            # Check resource ID
            resource_id = self.get_resource_id(view)
            if any(nav_hint in resource_id for nav_hint in [
                "bottom_navigation", "bottomnav", "navbar", "tab_bar", "tabbar"
            ]):
                bottom_nav_score += 0.3

            # Check position - bottom nav is at bottom of screen
            bounds = view.get("bounds", {})
            if bounds:
                # Estimated screen dimensions
                screen_width, screen_height = self.estimate_screen_dimensions(screen)

                bottom = bounds[1][1]
                top = bounds[0][1]
                height = bottom - top
                width = bounds[1][0] - bounds[0][0]

                # Is it at the bottom of the screen?
                if bottom >= screen_height - 20:
                    bottom_nav_score += 0.3

                # Is it wide enough?
                if width >= screen_width * 0.9:
                    bottom_nav_score += 0.2

                # Is it the right height for a bottom nav?
                if 40 <= height <= 150:
                    bottom_nav_score += 0.2

            # Check for navigation-like elements
            children = self.get_direct_children(item, screen)

            # Bottom navigation typically has 3-5 items
            if 3 <= len(children) <= 5:
                bottom_nav_score += 0.2

                # Check if items are arranged horizontally
                if self.is_horizontal_arrangement(children):
                    bottom_nav_score += 0.2

            if bottom_nav_score >= 0.6:
                potential_bottom_nav.append((item, bottom_nav_score, children))

        # If no potential bottom nav container, look for a row of buttons at the bottom
        if not potential_bottom_nav:
            bottom_row = self._find_bottom_row_buttons(screen)
            if bottom_row:
                # Calculate confidence based on number of items and position
                confidence = min(0.7, 0.4 + (len(bottom_row) * 0.05))
                return confidence, bottom_row

            return 0.0, []

        # Return the most likely bottom nav and its elements
        best_bottom_nav = max(potential_bottom_nav, key=lambda x: x[1])
        nav_item, confidence, children = best_bottom_nav

        # If children look like navigation items, use them
        if children and self._items_look_like_navigation(children):
            elements = [nav_item] + children
        else:
            elements = [nav_item]

        return confidence, elements

    def _detect_side_navigation(self, screen: ScreenDescription) -> Tuple[float, List[ScreenItem]]:
        """
        Detect side navigation rail/menu pattern.

        Args:
            screen: Parsed screen description

        Returns:
            Tuple of (confidence, list of side navigation elements)
        """
        # Look for side navigation container
        potential_side_nav = []

        for item in screen.items:
            view = item.view

            # Skip invisible elements
            if not self.is_visible(item):
                continue

            # Check class name
            class_name = view.get("class", "").lower()
            side_nav_score = 0.0

            # Direct side navigation classes
            if "navigationrail" in class_name:
                side_nav_score += 0.8
            elif "sidemenu" in class_name or "sidenavigation" in class_name:
                side_nav_score += 0.7
            elif "sidebar" in class_name:
                side_nav_score += 0.6

            # Check resource ID
            resource_id = self.get_resource_id(view)
            if any(nav_hint in resource_id for nav_hint in [
                "navigation_rail", "side_nav", "sidebar", "navview"
            ]):
                side_nav_score += 0.3

            # Check position - side nav is typically full height and at side
            bounds = view.get("bounds", {})
            if bounds:
                # Estimated screen dimensions
                screen_width, screen_height = self.estimate_screen_dimensions(screen)

                height = bounds[1][1] - bounds[0][1]
                width = bounds[1][0] - bounds[0][0]
                left = bounds[0][0]

                # Is it tall enough?
                if height >= screen_height * 0.7:
                    side_nav_score += 0.2

                # Is it at the side of the screen?
                if left <= 5:
                    side_nav_score += 0.2

                # Is it narrow enough to be a side rail?
                if width <= 150:
                    side_nav_score += 0.2

            # Check for navigation-like elements
            children = self.get_direct_children(item, screen)

            # Side navigation typically has vertically arranged items
            if len(children) >= 3:
                side_nav_score += 0.1

                # Check if items are arranged vertically
                if self.is_vertical_arrangement(children):
                    side_nav_score += 0.2

            if side_nav_score >= 0.6:
                potential_side_nav.append((item, side_nav_score, children))

        # If no potential side nav, try to find a vertical column of buttons at the side
        if not potential_side_nav:
            side_column = self._find_side_column_buttons(screen)
            if side_column:
                # Calculate confidence based on number of items and position
                confidence = min(0.7, 0.4 + (len(side_column) * 0.05))
                return confidence, side_column

            return 0.0, []

        # Return the most likely side nav and its elements
        best_side_nav = max(potential_side_nav, key=lambda x: x[1])
        nav_item, confidence, children = best_side_nav

        # If children look like navigation items, use them
        if children and self._items_look_like_navigation(children):
            elements = [nav_item] + children
        else:
            elements = [nav_item]

        return confidence, elements

    def _count_navigation_items(self, items: List[ScreenItem]) -> int:
        """
        Count items that look like navigation elements.

        Args:
            items: List of items to check

        Returns:
            Count of navigation-like items
        """
        count = 0

        for item in items:
            # Navigation items typically have text and icon
            has_text = bool(item.view.get("text", ""))
            has_icon = (
                    "imageview" in item.view.get("class", "").lower() or
                    item.view.get("drawable", False) or
                    bool(item.view.get("content_description", ""))
            )

            if has_text or has_icon:
                count += 1

        return count

    def _filter_navigation_items(self, items: List[ScreenItem]) -> List[ScreenItem]:
        """
        Filter items to keep only those that look like navigation elements.

        Args:
            items: List of items to filter

        Returns:
            Filtered list of navigation-like items
        """
        nav_items = []

        for item in items:
            # Skip invisible items
            if not self.is_visible(item):
                continue

            # Navigation items are typically clickable
            if not item.view.get("clickable", False):
                # Check if it has clickable children instead
                children = self.get_direct_children(item, screen=None)
                if not any(child.view.get("clickable", False) for child in children if hasattr(child, 'view')):
                    continue

            # Check for text or icon
            has_text = bool(item.view.get("text", ""))
            has_icon = (
                    "imageview" in item.view.get("class", "").lower() or
                    item.view.get("drawable", False) or
                    bool(item.view.get("content_description", ""))
            )

            if has_text or has_icon:
                nav_items.append(item)

        return nav_items

    def _find_hamburger_button(self, screen: ScreenDescription) -> Optional[ScreenItem]:
        """
        Find hamburger menu / drawer toggle button.

        Args:
            screen: Screen description

        Returns:
            Hamburger button item or None
        """
        for item in screen.items:
            view = item.view

            # Skip invisible or non-clickable items
            if not self.is_visible(item) or not view.get("clickable", False):
                continue

            # Check content description
            content_desc = self.get_view_property("content_description", view)
            if any(menu_hint in content_desc for menu_hint in [
                "menu", "drawer", "navigation", "hamburger", "toggle"
            ]):
                return item

            # Check resource ID
            resource_id = self.get_resource_id(view)
            if any(menu_hint in resource_id for menu_hint in [
                "hamburger", "drawer_indicator", "drawer_toggle", "menu_button", "nav_button"
            ]):
                return item

            # Check position - typically at top left
            bounds = view.get("bounds", {})
            if bounds:
                left = bounds[0][0]
                top = bounds[0][1]
                width = bounds[1][0] - left
                height = bounds[1][1] - top

                # Small button at top left corner
                if left <= 20 and top <= 80 and width <= 70 and height <= 70:
                    return item

        return None

    def _find_bottom_row_buttons(self, screen: ScreenDescription) -> List[ScreenItem]:
        """
        Find a row of buttons at the bottom of the screen.

        Args:
            screen: Screen description

        Returns:
            List of bottom row button items
        """
        # Get all visible, clickable items
        candidates = []

        for item in screen.items:
            # Skip invisible or non-clickable items
            if not self.is_visible(item) or not item.view.get("clickable", False):
                continue

            candidates.append(item)

        # If not enough candidates, return empty list
        if len(candidates) < 3:
            return []

        # Estimate screen height
        _, screen_height = self.estimate_screen_dimensions(screen)

        # Find items at the bottom
        bottom_items = []
        for item in candidates:
            bounds = item.view.get("bounds", {})
            bottom = bounds[1][1]

            # Within bottom 15% of screen
            if bottom >= screen_height * 0.85:
                bottom_items.append(item)

        # If not enough bottom items, return empty list
        if len(bottom_items) < 3:
            return []

        # Check if they're arranged horizontally
        if self.is_horizontal_arrangement(bottom_items):
            return bottom_items

        # Try to find a subset that is arranged horizontally
        if len(bottom_items) > 3:
            # Sort by x-coordinate
            sorted_items = sorted(bottom_items, key=lambda x: x.view.get("bounds", {})[0][0])

            # Check different subsets
            for i in range(len(sorted_items) - 2):
                subset = sorted_items[i:i + 3]
                if self.is_horizontal_arrangement(subset):
                    return subset

        return []

    def _find_side_column_buttons(self, screen: ScreenDescription) -> List[ScreenItem]:
        """
        Find a column of buttons at the side of the screen.

        Args:
            screen: Screen description

        Returns:
            List of side column button items
        """
        # Get all visible, clickable items
        candidates = []

        for item in screen.items:
            # Skip invisible or non-clickable items
            if not self.is_visible(item) or not item.view.get("clickable", False):
                continue

            candidates.append(item)

        # If not enough candidates, return empty list
        if len(candidates) < 3:
            return []

        # Estimate screen width
        screen_width, _ = self.estimate_screen_dimensions(screen)

        # Find items at the left side
        side_items = []
        for item in candidates:
            bounds = item.view.get("bounds", {})
            left = bounds[0][0]

            # Within leftmost 15% of screen
            if left <= screen_width * 0.15:
                side_items.append(item)

        # If not enough side items, return empty list
        if len(side_items) < 3:
            return []

        # Check if they're arranged vertically
        if self.is_vertical_arrangement(side_items):
            return side_items

        # Try to find a subset that is arranged vertically
        if len(side_items) > 3:
            # Sort by y-coordinate
            sorted_items = sorted(side_items, key=lambda x: x.view.get("bounds", {})[0][1])

            # Check different subsets
            for i in range(len(sorted_items) - 2):
                subset = sorted_items[i:i + 3]
                if self.is_vertical_arrangement(subset):
                    return subset

        return []

    def _items_look_like_navigation(self, items: List[ScreenItem]) -> bool:
        """
        Check if a list of items looks like navigation items.

        Args:
            items: List of items to check

        Returns:
            True if items look like navigation elements
        """
        if not items:
            return False

        # Count items with navigation-like properties
        nav_like_count = 0

        for item in items:
            # Skip invisible items
            if not self.is_visible(item):
                continue

            # Navigation items are typically clickable
            if not item.view.get("clickable", False):
                continue

            # Check for text or icon
            has_text = bool(item.view.get("text", ""))
            has_icon = (
                    "imageview" in item.view.get("class", "").lower() or
                    item.view.get("drawable", False) or
                    bool(item.view.get("content_description", ""))
            )

            if has_text or has_icon:
                nav_like_count += 1

        # If most items look like navigation, return true
        return nav_like_count >= len(items) * 0.7
