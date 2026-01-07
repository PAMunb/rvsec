"""
Hit classification for LLM click accuracy validation.

Classifies clicks as HIT, NEAR_MISS, UI_MISS, or EMPTY_MISS
with adaptive tolerance based on element size.
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass

from .metrics import (
    HitClassification,
    ElementBounds,
    UIElement,
)


@dataclass
class ClassificationResult:
    """Result of hit classification."""

    classification: HitClassification
    distance_to_target: float
    distance_to_nearest: float
    hit_element: Optional[UIElement]
    tolerance_used: int


class HitClassifier:
    """
    Classifies click accuracy with adaptive tolerance.

    Classification rules:
    - HIT: Click inside target element bounds (with tolerance)
    - NEAR_MISS: Click hit another interactive element
    - UI_MISS: Click hit non-interactive UI element
    - EMPTY_MISS: Click hit empty screen area
    """

    # Tolerance bounds
    MIN_TOLERANCE = 10
    MAX_TOLERANCE = 50
    TOLERANCE_RATIO = 0.2  # 20% of smallest dimension

    def __init__(
        self,
        min_tolerance: int = 10,
        max_tolerance: int = 50,
        tolerance_ratio: float = 0.2,
    ):
        """
        Initialize classifier with tolerance settings.

        Args:
            min_tolerance: Minimum tolerance in pixels (default: 10)
            max_tolerance: Maximum tolerance in pixels (default: 50)
            tolerance_ratio: Ratio of element size for tolerance (default: 0.2)
        """
        self.min_tolerance = min_tolerance
        self.max_tolerance = max_tolerance
        self.tolerance_ratio = tolerance_ratio

    def calculate_tolerance(self, element: Optional[ElementBounds]) -> int:
        """
        Calculate adaptive tolerance based on element size.

        Tolerance = 20% of smallest dimension, clamped to [10, 50] pixels.

        Args:
            element: Target element bounds (if known)

        Returns:
            Tolerance in pixels
        """
        if element is None:
            return self.max_tolerance

        min_dim = min(element.width, element.height)
        tolerance = int(min_dim * self.tolerance_ratio)
        return max(self.min_tolerance, min(self.max_tolerance, tolerance))

    def classify(
        self,
        click_x: int,
        click_y: int,
        target_element: Optional[ElementBounds],
        ui_elements: List[UIElement],
    ) -> ClassificationResult:
        """
        Classify a click based on accuracy.

        Args:
            click_x: X coordinate of click (device pixels)
            click_y: Y coordinate of click (device pixels)
            target_element: Intended target element (if known)
            ui_elements: All visible UI elements on screen

        Returns:
            ClassificationResult with classification and distances
        """
        tolerance = self.calculate_tolerance(target_element)

        # Calculate distance to target
        distance_to_target = float('inf')
        if target_element:
            distance_to_target = target_element.distance_to(click_x, click_y)

        # Check if hit target (within tolerance)
        if target_element and distance_to_target <= tolerance:
            return ClassificationResult(
                classification=HitClassification.HIT,
                distance_to_target=distance_to_target,
                distance_to_nearest=0.0,
                hit_element=None,  # Hit the target
                tolerance_used=tolerance,
            )

        # Find best element that was hit
        # Prefer: 1) Interactive elements, 2) Smaller/more specific elements
        hit_element: Optional[UIElement] = None
        min_distance = float('inf')
        best_area = float('inf')

        for element in ui_elements:
            if element.bounds.contains(click_x, click_y):
                # Element contains the click - check if it's better than current
                element_area = element.bounds.width * element.bounds.height

                # Prefer interactive elements, then smaller elements
                is_better = False
                if hit_element is None:
                    is_better = True
                elif element.is_interactive and not hit_element.is_interactive:
                    # Interactive is always better than non-interactive
                    is_better = True
                elif element.is_interactive == hit_element.is_interactive:
                    # Same interactivity - prefer smaller (more specific)
                    is_better = element_area < best_area

                if is_better:
                    hit_element = element
                    min_distance = 0.0
                    best_area = element_area
            else:
                # Element doesn't contain click - check distance
                dist = element.bounds.distance_to(click_x, click_y)
                if dist < min_distance and dist <= tolerance:
                    # Only consider nearby elements if no containing element found
                    if hit_element is None or min_distance > 0:
                        min_distance = dist
                        hit_element = element
                        best_area = element.bounds.width * element.bounds.height

        # Classify based on what was hit
        if hit_element is not None:
            if hit_element.is_interactive:
                # Click inside interactive element = HIT
                # (near_miss is only for clicks NEAR but OUTSIDE the element)
                if min_distance == 0.0:
                    classification = HitClassification.HIT
                else:
                    classification = HitClassification.NEAR_MISS
            else:
                classification = HitClassification.UI_MISS
        else:
            classification = HitClassification.EMPTY_MISS

        return ClassificationResult(
            classification=classification,
            distance_to_target=distance_to_target,
            distance_to_nearest=min_distance,
            hit_element=hit_element,
            tolerance_used=tolerance,
        )

    def classify_batch(
        self,
        clicks: List[Tuple[int, int]],
        targets: List[Optional[ElementBounds]],
        ui_elements_per_click: List[List[UIElement]],
    ) -> List[ClassificationResult]:
        """
        Classify multiple clicks.

        Args:
            clicks: List of (x, y) click coordinates
            targets: List of target elements (may be None)
            ui_elements_per_click: UI elements visible at each click

        Returns:
            List of ClassificationResults
        """
        results = []
        for (x, y), target, ui_elements in zip(
            clicks, targets, ui_elements_per_click
        ):
            result = self.classify(x, y, target, ui_elements)
            results.append(result)
        return results


def parse_ui_elements_from_dump(xml_content: str) -> List[UIElement]:
    """
    Parse UIAutomator XML dump into UIElement list.

    Args:
        xml_content: UIAutomator XML dump content

    Returns:
        List of UIElement objects
    """
    import xml.etree.ElementTree as ET

    elements = []
    try:
        root = ET.fromstring(xml_content)

        for node in root.iter("node"):
            bounds_str = node.get("bounds", "")
            if not bounds_str:
                continue

            # Parse bounds "[left,top][right,bottom]"
            try:
                parts = bounds_str.replace("][", ",").strip("[]").split(",")
                if len(parts) == 4:
                    left, top, right, bottom = map(int, parts)
                    bounds = ElementBounds(left, top, right, bottom)
                else:
                    continue
            except (ValueError, IndexError):
                continue

            element = UIElement(
                bounds=bounds,
                element_type=node.get("class", "").split(".")[-1],
                text=node.get("text", ""),
                resource_id=node.get("resource-id", ""),
                is_clickable=node.get("clickable", "false").lower() == "true",
                is_editable=node.get("class", "").endswith("EditText"),
            )
            elements.append(element)

    except ET.ParseError:
        pass

    return elements
