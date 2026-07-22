"""
Action validator for offline validation.

Validates that actions target valid UI elements with correct coordinates
and action types.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    """Represents a UI element from UIAutomator dump."""

    bounds: Tuple[Tuple[int, int], Tuple[int, int]]  # ((x1, y1), (x2, y2))
    clickable: bool
    long_clickable: bool
    checkable: bool
    editable: bool
    class_name: str
    resource_id: str
    text: str
    content_desc: str

    def contains_point(self, x: int, y: int) -> bool:
        """Check if point (x,y) is within element bounds."""
        (x1, y1), (x2, y2) = self.bounds
        return x1 <= x <= x2 and y1 <= y <= y2

    def __str__(self) -> str:
        text_repr = self.text if self.text else self.content_desc if self.content_desc else self.resource_id
        return f"{self.class_name}[{text_repr}] @ {self.bounds}"


@dataclass
class ValidationResult:
    """Result of action validation."""

    valid: bool
    reason: str
    element: Optional[UIElement] = None


class ActionValidator:
    """
    Validates actions against actual UI elements.

    Checks:
    - Click coordinates within clickable element bounds
    - Type text target is editable (EditText)
    - Long click target supports long_clickable
    - Element capabilities match action type
    """

    def __init__(self):
        """Initialize action validator."""
        self.current_elements: List[UIElement] = []
        self.validation_history: List[Dict] = []

        logger.info("ActionValidator initialized")

    def load_ui_elements(self, uiautomator_path: Path) -> int:
        """
        Load UI elements from UIAutomator XML dump.

        Args:
            uiautomator_path: Path to .uiautomator XML file

        Returns:
            Number of elements loaded
        """
        try:
            tree = ET.parse(uiautomator_path)
            root = tree.getroot()

            self.current_elements = []
            self._parse_node(root)

            logger.info(f"Loaded {len(self.current_elements)} UI elements from {uiautomator_path.name}")
            return len(self.current_elements)

        except Exception as e:
            logger.error(f"Failed to parse UI elements: {e}")
            self.current_elements = []
            return 0

    def _parse_node(self, node: ET.Element):
        """Recursively parse XML node to extract UI elements."""
        # Parse bounds: "[x1,y1][x2,y2]"
        bounds_str = node.get('bounds', '[0,0][0,0]')
        try:
            # Parse "[42,101][316,172]" -> ((42, 101), (316, 172))
            parts = bounds_str.replace('[', '').replace(']', ',').split(',')
            parts = [p for p in parts if p]  # Remove empty strings
            x1, y1, x2, y2 = map(int, parts[:4])
            bounds = ((x1, y1), (x2, y2))
        except (ValueError, IndexError):
            bounds = ((0, 0), (0, 0))

        element = UIElement(
            bounds=bounds,
            clickable=node.get('clickable', 'false') == 'true',
            long_clickable=node.get('long-clickable', 'false') == 'true',
            checkable=node.get('checkable', 'false') == 'true',
            editable=node.get('editable', 'true') == 'true' or 'EditText' in node.get('class', ''),
            class_name=node.get('class', 'unknown'),
            resource_id=node.get('resource-id', ''),
            text=node.get('text', ''),
            content_desc=node.get('content-desc', '')
        )

        self.current_elements.append(element)

        # Recursively parse children
        for child in node:
            self._parse_node(child)

    def find_element_at(self, x: int, y: int) -> Optional[UIElement]:
        """
        Find UI element at coordinates (x, y).

        Returns the smallest element containing the point (most specific).

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            UIElement if found, None otherwise
        """
        # Find all elements containing the point
        candidates = [e for e in self.current_elements if e.contains_point(x, y)]

        if not candidates:
            return None

        # Return the smallest element (most specific)
        return min(candidates, key=lambda e: (e.bounds[1][0] - e.bounds[0][0]) * (e.bounds[1][1] - e.bounds[0][1]))

    def validate_click(self, x: int, y: int) -> ValidationResult:
        """
        Validate click action.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            ValidationResult with validation status
        """
        element = self.find_element_at(x, y)

        if element is None:
            result = ValidationResult(
                valid=False,
                reason=f"No element at coordinates ({x}, {y})"
            )
        elif not element.clickable:
            result = ValidationResult(
                valid=False,
                reason=f"Element is not clickable: {element}",
                element=element
            )
        else:
            result = ValidationResult(
                valid=True,
                reason="Valid click action",
                element=element
            )

        # Record validation
        self.validation_history.append({
            'action': 'click',
            'x': x,
            'y': y,
            'valid': result.valid,
            'reason': result.reason,
            'element': str(element) if element else None
        })

        return result

    def validate_long_click(self, x: int, y: int) -> ValidationResult:
        """
        Validate long click action.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            ValidationResult with validation status
        """
        element = self.find_element_at(x, y)

        if element is None:
            result = ValidationResult(
                valid=False,
                reason=f"No element at coordinates ({x}, {y})"
            )
        elif not element.long_clickable:
            result = ValidationResult(
                valid=False,
                reason=f"Element does not support long click: {element}",
                element=element
            )
        else:
            result = ValidationResult(
                valid=True,
                reason="Valid long click action",
                element=element
            )

        # Record validation
        self.validation_history.append({
            'action': 'long_click',
            'x': x,
            'y': y,
            'valid': result.valid,
            'reason': result.reason,
            'element': str(element) if element else None
        })

        return result

    def validate_type_text(self, x: int, y: int, text: str) -> ValidationResult:
        """
        Validate type text action.

        Args:
            x: X coordinate
            y: Y coordinate
            text: Text to type

        Returns:
            ValidationResult with validation status
        """
        element = self.find_element_at(x, y)

        if element is None:
            result = ValidationResult(
                valid=False,
                reason=f"No element at coordinates ({x}, {y})"
            )
        elif not element.editable:
            result = ValidationResult(
                valid=False,
                reason=f"Element is not editable: {element}",
                element=element
            )
        else:
            result = ValidationResult(
                valid=True,
                reason="Valid type text action",
                element=element
            )

        # Record validation
        self.validation_history.append({
            'action': 'type_text',
            'x': x,
            'y': y,
            'text': text,
            'valid': result.valid,
            'reason': result.reason,
            'element': str(element) if element else None
        })

        return result

    def validate_system_action(self, action_type: str) -> ValidationResult:
        """
        Validate system action (BACK, HOME, etc).

        System actions are always valid.

        Args:
            action_type: Type of system action

        Returns:
            ValidationResult (always valid)
        """
        result = ValidationResult(
            valid=True,
            reason=f"System action: {action_type}"
        )

        # Record validation
        self.validation_history.append({
            'action': action_type.lower(),
            'valid': True,
            'reason': result.reason
        })

        return result

    def get_element_type_distribution(self) -> Dict[str, int]:
        """
        Get distribution of UI element types in current screen.

        Returns:
            Dictionary mapping class names to counts
        """
        distribution = {}
        for element in self.current_elements:
            class_name = element.class_name.split('.')[-1]  # Get simple name
            distribution[class_name] = distribution.get(class_name, 0) + 1
        return distribution

    def get_interactive_elements(self) -> List[UIElement]:
        """
        Get all interactive elements (clickable, long-clickable, or editable).

        Returns:
            List of interactive UIElements
        """
        return [e for e in self.current_elements if e.clickable or e.long_clickable or e.editable]

    def get_validation_summary(self) -> Dict:
        """
        Get summary of validation history.

        Returns:
            Dictionary with validation statistics
        """
        total = len(self.validation_history)
        valid = sum(1 for v in self.validation_history if v['valid'])
        invalid = total - valid

        action_types = {}
        for v in self.validation_history:
            action = v['action']
            action_types[action] = action_types.get(action, 0) + 1

        return {
            'total_actions': total,
            'valid_actions': valid,
            'invalid_actions': invalid,
            'valid_rate': valid / total if total > 0 else 0.0,
            'action_types': action_types
        }
