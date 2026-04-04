#!/usr/bin/env python3
"""
Geometry utilities for screenshot analysis operations.

This module provides geometric calculations and spatial analysis functions
used across screenshot detection components for overlap detection,
coordinate validation, and element filtering.

### Architectural Role:
- Provides shared geometric computation functions
- Implements overlap detection algorithms for element deduplication
- Enables spatial relationship analysis between UI elements
- Supports coordinate validation and boundary calculations

### Design Decisions:
- Uses pure functions for mathematical operations
- Implements defensive programming with validation
- Provides both pixel-based and percentage-based calculations
- Optimizes for common use cases in UI element detection
"""

from typing import Any, Dict, List, Tuple

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVValidationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class GeometryUtils:
    """
    Utility class for geometric calculations in screenshot analysis.

    Provides methods for overlap detection, coordinate validation,
    and spatial relationship analysis between UI elements.
    """

    def __init__(self):
        """Initialize geometry utilities with logging."""
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "screenshot.geometry", {CONTEXT_COMPONENT: "GeometryUtils"}
        )

    @ErrorHandler.handle_errors(component="GeometryUtils", phase="calculation")
    def calculate_overlap_percentage(
        self, x1: int, y1: int, w1: int, h1: int, x2: int, y2: int, w2: int, h2: int
    ) -> float:
        """
        Calculate the percentage of overlap between two rectangles.

        Computes the intersection area as a percentage of the smaller rectangle,
        which is useful for determining if elements significantly overlap.

        Args:
            x1, y1, w1, h1: First rectangle (x, y, width, height)
            x2, y2, w2, h2: Second rectangle (x, y, width, height)

        Returns:
            Overlap percentage (0.0 to 1.0) relative to the smaller rectangle

        Raises:
            RVValidationError: If rectangle parameters are invalid
        """
        # Validate rectangle parameters
        if w1 <= 0 or h1 <= 0 or w2 <= 0 or h2 <= 0:
            raise RVValidationError(
                f"Rectangle dimensions must be positive: rect1=({w1},{h1}), rect2=({w2},{h2})",
                field_name="rectangle_dimensions",
            )

        if x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0:
            raise RVValidationError(
                f"Rectangle coordinates must be non-negative: rect1=({x1},{y1}), rect2=({x2},{y2})",
                field_name="rectangle_coordinates",
            )

        # Calculate intersection coordinates
        x_intersection = max(x1, x2)
        y_intersection = max(y1, y2)
        w_intersection = min(x1 + w1, x2 + w2) - x_intersection
        h_intersection = min(y1 + h1, y2 + h2) - y_intersection

        # No intersection if width or height is negative
        if w_intersection <= 0 or h_intersection <= 0:
            return 0.0

        # Calculate areas
        intersection_area = w_intersection * h_intersection
        area1 = w1 * h1
        area2 = w2 * h2
        smaller_area = min(area1, area2)

        return intersection_area / smaller_area if smaller_area > 0 else 0.0

    @ErrorHandler.handle_errors(component="GeometryUtils", phase="filtering")
    def filter_overlapping_elements(
        self, elements: List[Dict[str, Any]], overlap_threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Filter out overlapping elements, keeping those with higher confidence.

        This method removes elements that significantly overlap with higher-confidence
        elements, helping to eliminate duplicate detections from different algorithms.

        Args:
            elements: List of element dictionaries with position and confidence data
            overlap_threshold: Minimum overlap percentage to consider elements as duplicates

        Returns:
            Filtered list with non-overlapping elements

        Raises:
            RVValidationError: If elements lack required fields
        """
        if not elements:
            return []

        # Validate that all elements have required fields
        required_fields = ["x", "y", "width", "height"]
        for i, element in enumerate(elements):
            for field in required_fields:
                if field not in element:
                    raise RVValidationError(
                        f"Element {i} missing required field '{field}'",
                        field_name=f"element_{i}_{field}",
                    )

        # Sort by confidence (higher first), using 0.0 as default if no confidence field
        sorted_elements = sorted(
            elements, key=lambda e: e.get("confidence", 0.0), reverse=True
        )

        # Keep track of which elements to include
        included = []

        for element in sorted_elements:
            # Check if this element significantly overlaps with any included element
            has_overlap = False

            for included_element in included:
                x1, y1 = element["x"], element["y"]
                w1, h1 = element["width"], element["height"]

                x2, y2 = included_element["x"], included_element["y"]
                w2, h2 = included_element["width"], included_element["height"]

                # Calculate overlap percentage
                try:
                    overlap = self.calculate_overlap_percentage(
                        x1, y1, w1, h1, x2, y2, w2, h2
                    )

                    if overlap > overlap_threshold:
                        has_overlap = True
                        self.logger.debug(
                            f"Element at ({x1},{y1}) overlaps {overlap:.2f} with element at ({x2},{y2})"
                        )
                        break

                except Exception as e:
                    self.logger.warning(f"Error calculating overlap: {e}")
                    # Continue processing other elements

            # If no significant overlap, include this element
            if not has_overlap:
                included.append(element)

        self.logger.debug(
            f"Filtered {len(elements)} elements to {len(included)} non-overlapping elements"
        )
        return included

    def calculate_center_point(
        self, x: int, y: int, width: int, height: int
    ) -> Tuple[int, int]:
        """
        Calculate the center point of a rectangle.

        Args:
            x, y: Top-left coordinates
            width, height: Rectangle dimensions

        Returns:
            (center_x, center_y) tuple
        """
        return (x + width // 2, y + height // 2)

    def calculate_area(self, width: int, height: int) -> int:
        """
        Calculate the area of a rectangle.

        Args:
            width, height: Rectangle dimensions

        Returns:
            Area in square pixels
        """
        return width * height

    def calculate_aspect_ratio(self, width: int, height: int) -> float:
        """
        Calculate the aspect ratio (width/height) of a rectangle.

        Args:
            width, height: Rectangle dimensions

        Returns:
            Aspect ratio as float, or 1.0 if height is 0
        """
        return float(width) / float(height) if height > 0 else 1.0

    def is_point_inside_rectangle(
        self,
        point_x: int,
        point_y: int,
        rect_x: int,
        rect_y: int,
        rect_width: int,
        rect_height: int,
    ) -> bool:
        """
        Check if a point is inside a rectangle.

        Args:
            point_x, point_y: Point coordinates
            rect_x, rect_y: Rectangle top-left coordinates
            rect_width, rect_height: Rectangle dimensions

        Returns:
            True if point is inside rectangle, False otherwise
        """
        return (
            rect_x <= point_x <= rect_x + rect_width
            and rect_y <= point_y <= rect_y + rect_height
        )

    def calculate_distance_between_centers(
        self, x1: int, y1: int, w1: int, h1: int, x2: int, y2: int, w2: int, h2: int
    ) -> float:
        """
        Calculate the distance between the centers of two rectangles.

        Args:
            x1, y1, w1, h1: First rectangle
            x2, y2, w2, h2: Second rectangle

        Returns:
            Distance between centers in pixels
        """
        center1_x, center1_y = self.calculate_center_point(x1, y1, w1, h1)
        center2_x, center2_y = self.calculate_center_point(x2, y2, w2, h2)

        return ((center2_x - center1_x) ** 2 + (center2_y - center1_y) ** 2) ** 0.5

    def expand_rectangle(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        padding_x: int,
        padding_y: int,
        max_width: int = None,
        max_height: int = None,
    ) -> Tuple[int, int, int, int]:
        """
        Expand a rectangle by adding padding, respecting boundaries.

        Args:
            x, y: Original rectangle top-left coordinates
            width, height: Original rectangle dimensions
            padding_x, padding_y: Padding to add in each direction
            max_width, max_height: Optional maximum boundaries

        Returns:
            (new_x, new_y, new_width, new_height) tuple
        """
        new_x = max(0, x - padding_x)
        new_y = max(0, y - padding_y)
        new_width = width + 2 * padding_x
        new_height = height + 2 * padding_y

        # Respect maximum boundaries if provided
        if max_width is not None:
            if new_x + new_width > max_width:
                new_width = max_width - new_x

        if max_height is not None:
            if new_y + new_height > max_height:
                new_height = max_height - new_y

        return (new_x, new_y, new_width, new_height)


# Global instance for convenient access
_geometry_utils = None


def get_geometry_utils() -> GeometryUtils:
    """
    Get the global geometry utilities instance.

    Returns:
        GeometryUtils instance
    """
    global _geometry_utils
    if _geometry_utils is None:
        _geometry_utils = GeometryUtils()
    return _geometry_utils
