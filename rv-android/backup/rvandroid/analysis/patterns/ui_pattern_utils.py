# rvandroid/analysis/patterns/ui_pattern_utils.py
"""
Utility functions for UI pattern detection.

This module provides common utility functions used by various
pattern detectors to analyze UI elements and detect patterns.
"""

from typing import List, Dict, Any, Tuple, Optional

from rvandroid.parser.screen.visitor.model import ScreenItem, ScreenDescription
from rvandroid.util.logging.manager import LoggingManager


class UIPatternUtils:
    """
    Utility functions for UI pattern detection.

    This class provides static methods for common operations in pattern detection,
    including bounds calculations, element visibility checks, and arrangement analysis.

    ### Architectural Decisions:
    - Implements utility methods as static methods for easy access
    - Centralizes common pattern detection logic to avoid duplication
    - Provides standardized algorithms for UI element analysis
    - Ensures consistent behavior across different pattern detectors

    ### Role in the System:
    - Provides reusable components for all pattern detectors
    - Ensures consistent handling of UI elements across detectors
    - Centralizes complex algorithms for better maintainability
    - Standardizes common pattern detection operations
    """

    # Initialize logging
    _logger = LoggingManager.get_instance().get_logger(
        "analysis.patterns.utils",
        {"component": "UIPatternUtils"}
    )

    @staticmethod
    def is_visible(item: ScreenItem) -> bool:
        """
        Check if an element is visible.

        Args:
            item: Screen item to check

        Returns:
            True if the element is visible
        """
        view = item.view

        # Check visibility
        if view.get("visibility") == "gone" or view.get("visibility") == "invisible":
            return False

        # Check bounds
        bounds = view.get("bounds", {})
        if not bounds:
            return False

        # Ensure minimum size
        width, height = UIPatternUtils.get_width_height(bounds)
        if width <= 0 or height <= 0:
            return False

        return True

    @staticmethod
    def get_width_height(bounds: List[List[int]]) -> Tuple[int, int]:
        """
        Get width and height from bounds.

        Args:
            bounds: Bounds in format [[left, top], [right, bottom]]

        Returns:
            Tuple of (width, height)
        """
        if not isinstance(bounds, list) or len(bounds) != 2:
            UIPatternUtils._logger.warning(f"Invalid bounds format: {bounds}")
            return 0, 0

        try:
            width = bounds[1][0] - bounds[0][0]
            height = bounds[1][1] - bounds[0][1]
            return width, height
        except (IndexError, TypeError):
            UIPatternUtils._logger.warning(f"Error calculating width/height from bounds: {bounds}")
            return 0, 0

    @staticmethod
    def get_center_coordinates(bounds: List[List[int]]) -> Tuple[int, int]:
        """
        Calculate the center coordinates of a bounding box.

        Args:
            bounds: Bounds in format [[left, top], [right, bottom]]

        Returns:
            Tuple of (center_x, center_y)
        """
        if not isinstance(bounds, list) or len(bounds) != 2:
            UIPatternUtils._logger.warning(f"Invalid bounds format: {bounds}")
            return 0, 0

        try:
            center_x = (bounds[0][0] + bounds[1][0]) // 2
            center_y = (bounds[0][1] + bounds[1][1]) // 2
            return center_x, center_y
        except (IndexError, TypeError):
            UIPatternUtils._logger.warning(f"Error calculating center from bounds: {bounds}")
            return 0, 0

    @staticmethod
    def get_bounds_dimensions(bounds: List[List[int]]) -> Dict[str, int]:
        """
        Get all dimensions from bounds.

        Args:
            bounds: Bounds in format [[left, top], [right, bottom]]

        Returns:
            Dictionary with left, top, right, bottom, width, height
        """
        if not isinstance(bounds, list) or len(bounds) != 2:
            UIPatternUtils._logger.warning(f"Invalid bounds format: {bounds}")
            return {"left": 0, "top": 0, "right": 0, "bottom": 0, "width": 0, "height": 0}

        try:
            left = bounds[0][0]
            top = bounds[0][1]
            right = bounds[1][0]
            bottom = bounds[1][1]
            width = right - left
            height = bottom - top

            return {
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "width": width,
                "height": height
            }
        except (IndexError, TypeError):
            UIPatternUtils._logger.warning(f"Error calculating dimensions from bounds: {bounds}")
            return {"left": 0, "top": 0, "right": 0, "bottom": 0, "width": 0, "height": 0}

    @staticmethod
    def get_direct_children(container: ScreenItem, screen: ScreenDescription) -> List[ScreenItem]:
        """
        Get direct children of a container.

        Args:
            container: Container element
            screen: Screen description

        Returns:
            List of direct children
        """
        child_ids = container.view.get("children", [])

        children = []
        for child_id in child_ids:
            for item in screen.items:
                if item.view.get("id") == child_id:
                    children.append(item)
                    break

        return children

    @staticmethod
    def is_horizontal_arrangement(items: List[ScreenItem]) -> bool:
        """
        Check if items are arranged horizontally.

        Args:
            items: List of screen items

        Returns:
            True if items are arranged horizontally
        """
        if not items or len(items) < 2:
            return False

        # Extract bounds
        bounds_list = []
        for item in items:
            bounds = item.view.get("bounds")
            if bounds and isinstance(bounds, list) and len(bounds) == 2:
                bounds_list.append(bounds)

        if len(bounds_list) < 2:
            return False

        # Check if items are mostly at the same vertical position
        # but different horizontal positions
        tops = [bounds[0][1] for bounds in bounds_list]
        lefts = [bounds[0][0] for bounds in bounds_list]

        # Calculate average top position
        avg_top = sum(tops) / len(tops)

        # Check if tops are similar (within 20% of height)
        heights = [bounds[1][1] - bounds[0][1] for bounds in bounds_list]
        avg_height = sum(heights) / len(heights) if heights else 1
        height_threshold = max(20, avg_height * 0.2)  # 20px or 20% of average height

        vertical_alignment = all(abs(top - avg_top) <= height_threshold for top in tops)

        # Check if lefts are distributed (not all in the same place)
        lefts_variation = max(lefts) - min(lefts)
        screen_width = max([bounds[1][0] for bounds in bounds_list], default=1000)  # Estimate screen width

        horizontal_distribution = lefts_variation > (screen_width * 0.3)  # Items span at least 30% of width

        return vertical_alignment and horizontal_distribution

    @staticmethod
    def is_vertical_arrangement(items: List[ScreenItem]) -> bool:
        """
        Check if items are arranged vertically.

        Args:
            items: List of screen items

        Returns:
            True if items are arranged vertically
        """
        if not items or len(items) < 2:
            return False

        # Extract bounds
        bounds_list = []
        for item in items:
            bounds = item.view.get("bounds")
            if bounds and isinstance(bounds, list) and len(bounds) == 2:
                bounds_list.append(bounds)

        if len(bounds_list) < 2:
            return False

        # Check if items are mostly at the same horizontal position
        # but different vertical positions
        lefts = [bounds[0][0] for bounds in bounds_list]
        tops = [bounds[0][1] for bounds in bounds_list]

        # Calculate average left position
        avg_left = sum(lefts) / len(lefts)

        # Check if lefts are similar (within 20% of width)
        widths = [bounds[1][0] - bounds[0][0] for bounds in bounds_list]
        avg_width = sum(widths) / len(widths) if widths else 1
        width_threshold = max(20, avg_width * 0.2)  # 20px or 20% of average width

        horizontal_alignment = all(abs(left - avg_left) <= width_threshold for left in lefts)

        # Check if tops are distributed (not all in the same place)
        tops_variation = max(tops) - min(tops)
        screen_height = max([bounds[1][1] for bounds in bounds_list], default=1000)  # Estimate screen height

        vertical_distribution = tops_variation > (screen_height * 0.1)  # Items span at least 10% of height

        return horizontal_alignment and vertical_distribution

    @staticmethod
    def calculate_overlap_percentage(
            bounds1: List[List[int]],
            bounds2: List[List[int]]
    ) -> float:
        """
        Calculate the percentage of overlap between two rectangles.

        Args:
            bounds1: First rectangle bounds
            bounds2: Second rectangle bounds

        Returns:
            Overlap percentage (0.0 to 1.0) relative to the smaller rectangle
        """
        # Extract coordinates
        x1, y1 = bounds1[0]
        x2, y2 = bounds1[1]

        x3, y3 = bounds2[0]
        x4, y4 = bounds2[1]

        # Calculate intersection coordinates
        x_intersection = max(x1, x3)
        y_intersection = max(y1, y3)
        w_intersection = min(x2, x4) - x_intersection
        h_intersection = min(y2, y4) - y_intersection

        if w_intersection <= 0 or h_intersection <= 0:
            return 0.0

        intersection_area = w_intersection * h_intersection
        area1 = (x2 - x1) * (y2 - y1)
        area2 = (x4 - x3) * (y4 - y3)
        smaller_area = min(area1, area2)

        return intersection_area / smaller_area if smaller_area > 0 else 0.0

    @staticmethod
    def find_elements_by_property(
            screen: ScreenDescription,
            property_check_func
    ) -> List[ScreenItem]:
        """
        Find elements by a property check function.

        Args:
            screen: Screen description
            property_check_func: Function that takes a ScreenItem and returns bool

        Returns:
            List of elements that pass the property check
        """
        return [item for item in screen.items if property_check_func(item)]

    @staticmethod
    def estimate_screen_dimensions(screen: ScreenDescription) -> Tuple[int, int]:
        """
        Estimate screen dimensions based on elements.

        Args:
            screen: Screen description

        Returns:
            Tuple of (width, height)
        """
        max_width = 0
        max_height = 0

        for item in screen.items:
            bounds = item.view.get("bounds")
            if bounds and isinstance(bounds, list) and len(bounds) == 2:
                max_width = max(max_width, bounds[1][0])
                max_height = max(max_height, bounds[1][1])

        # Default values if no elements found
        if max_width == 0:
            max_width = 1080  # Common screen width
        if max_height == 0:
            max_height = 1920  # Common screen height

        return max_width, max_height
   