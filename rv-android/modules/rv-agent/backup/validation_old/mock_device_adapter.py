"""
Mock Device Adapter for coordinate validation without emulator.

Simulates device interactions and validates coordinates against ground truth
from UIAutomator XML dumps.
"""

import logging
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ScreenItem


class MockDeviceAdapter:
    """
    Mock device adapter that simulates Android device interactions.

    Instead of executing real clicks, it validates coordinates against
    ground truth elements from UIAutomator XML dumps.
    """

    def __init__(self, xml_path: Optional[str] = None):
        """
        Initialize mock device with optional XML ground truth.

        Args:
            xml_path: Path to UIAutomator XML dump file
        """
        self.logger = logging.getLogger("rv_agent.validation.mock_device")
        self.parser = UIAutomator2Parser()

        # Store parsed screen description
        self.screen_description: Optional[ScreenDescription] = None
        self.clickable_elements: List[Dict[str, Any]] = []

        # Tracking
        self.click_history: List[Tuple[int, int, str, float]] = []
        self.input_history: List[Tuple[str, str]] = []

        if xml_path:
            self.load_ground_truth(xml_path)

    def load_ground_truth(self, xml_path: str) -> None:
        """
        Load and parse UIAutomator XML dump for ground truth.

        Args:
            xml_path: Path to UIAutomator XML file
        """
        try:
            with open(xml_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()

            # Parse XML to ScreenDescription
            self.screen_description = self.parser.parse(xml_content)

            # Extract clickable elements with coordinates
            self.clickable_elements = self._extract_clickable_elements()

            self.logger.info(f"Loaded ground truth with {len(self.clickable_elements)} clickable elements")

        except Exception as e:
            self.logger.error(f"Failed to load ground truth: {e}")
            raise

    def _extract_clickable_elements(self) -> List[Dict[str, Any]]:
        """
        Extract all clickable elements from screen description.

        Returns:
            List of clickable elements with coordinates and properties
        """
        elements = []

        if not self.screen_description:
            return elements

        for item in self.screen_description.items:
            view = item.view

            # Check if element is interactive
            if view.get('clickable', False) or view.get('checkable', False):
                # Get bounds and calculate center
                bounds = view.get('bounds', [[0, 0], [0, 0]])
                center_x = (bounds[0][0] + bounds[1][0]) // 2
                center_y = (bounds[0][1] + bounds[1][1]) // 2

                element = {
                    'resource_id': view.get('resource_id', ''),
                    'text': view.get('text', ''),
                    'class': view.get('class', ''),
                    'bounds': bounds,
                    'center': (center_x, center_y),
                    'clickable': view.get('clickable', False),
                    'description': item.base_description
                }
                elements.append(element)

        return elements

    def click(self, x: int, y: int) -> bool:
        """
        Simulate click and validate against ground truth.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if click hit a valid element, False otherwise
        """
        print(f"\n[MOCK_DEVICE] 🖱️ Click at ({x}, {y})")

        # Find closest element and calculate distance
        closest_element, distance = self._find_closest_element(x, y)

        # Determine if it's a hit (within 50px threshold)
        hit = distance < 50

        # Log the action
        element_desc = "MISS"
        if closest_element:
            element_desc = closest_element.get('text') or closest_element.get('resource_id') or closest_element.get('class', 'unknown')

        self.click_history.append((x, y, element_desc, distance))

        # Print validation result
        if hit:
            print(f"[MOCK_DEVICE] ✅ HIT: {element_desc} (distance: {distance:.1f}px)")
        else:
            print(f"[MOCK_DEVICE] ❌ MISS: Closest was {element_desc} at {distance:.1f}px away")

        return hit

    def _find_closest_element(self, x: int, y: int) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Find closest clickable element to given coordinates.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Tuple of (closest_element, distance)
        """
        if not self.clickable_elements:
            return None, float('inf')

        closest = None
        min_distance = float('inf')

        for element in self.clickable_elements:
            center = element['center']
            distance = ((x - center[0]) ** 2 + (y - center[1]) ** 2) ** 0.5

            if distance < min_distance:
                min_distance = distance
                closest = element

        return closest, min_distance

    def input_text(self, text: str, element: str = "") -> bool:
        """
        Simulate text input.

        Args:
            text: Text to input
            element: Element description (optional)

        Returns:
            Always True for mock
        """
        print(f"[MOCK_DEVICE] ⌨️ Input text: '{text}' to {element}")
        self.input_history.append((text, element))
        return True

    def scroll(self, direction: str, start_x: int = 540, start_y: int = 1000,
               end_x: int = 540, end_y: int = 500) -> bool:
        """
        Simulate scroll action.

        Args:
            direction: Scroll direction
            start_x, start_y: Start coordinates
            end_x, end_y: End coordinates

        Returns:
            Always True for mock
        """
        print(f"[MOCK_DEVICE] 📜 Scroll {direction}: ({start_x},{start_y}) -> ({end_x},{end_y})")
        return True

    def back(self) -> bool:
        """
        Simulate back button press.

        Returns:
            Always True for mock
        """
        print(f"[MOCK_DEVICE] ⬅️ Back button pressed")
        return True

    def get_current_package(self) -> str:
        """
        Get current package name (mock).

        Returns:
            Mock package name
        """
        return "br.unb.cic.cryptoapp"

    def get_current_activity(self) -> str:
        """
        Get current activity (mock).

        Returns:
            Activity from screen description or mock value
        """
        if self.screen_description:
            return self.screen_description.activity
        return "MainActivity"

    def restart_app(self, package_name: str) -> bool:
        """
        Simulate app restart.

        Args:
            package_name: Package to restart

        Returns:
            Always True for mock
        """
        print(f"[MOCK_DEVICE] 🔄 Restarting app: {package_name}")
        return True

    def take_screenshot(self, path: str) -> bool:
        """
        Simulate screenshot (no-op in mock).

        Args:
            path: Screenshot path

        Returns:
            Always True for mock
        """
        print(f"[MOCK_DEVICE] 📷 Screenshot saved to: {path}")
        return True

    def get_validation_metrics(self) -> Dict[str, Any]:
        """
        Get validation metrics from click history.

        Returns:
            Dictionary with validation metrics
        """
        if not self.click_history:
            return {
                'total_clicks': 0,
                'hits': 0,
                'misses': 0,
                'hit_rate': 0.0,
                'avg_distance': 0.0
            }

        hits = sum(1 for _, _, _, dist in self.click_history if dist < 50)
        misses = len(self.click_history) - hits
        avg_distance = sum(dist for _, _, _, dist in self.click_history) / len(self.click_history)

        return {
            'total_clicks': len(self.click_history),
            'hits': hits,
            'misses': misses,
            'hit_rate': hits / len(self.click_history) * 100,
            'avg_distance': avg_distance,
            'click_history': self.click_history
        }

    def get_element_list_for_prompt(self) -> str:
        """
        Generate element list formatted for LLM prompt.

        Returns:
            Formatted string with numbered list of clickable elements
        """
        if not self.clickable_elements:
            return "No clickable elements found."

        lines = []
        for i, elem in enumerate(self.clickable_elements, 1):
            text = elem.get('text', '')
            resource_id = elem.get('resource_id', '')
            elem_class = elem.get('class', '').split('.')[-1]  # Get last part of class name
            center = elem['center']

            # Build element description
            desc_parts = []
            if text:
                desc_parts.append(f'"{text}"')
            if resource_id:
                desc_parts.append(f'id:{resource_id.split(":")[-1]}')
            if elem_class:
                desc_parts.append(f'({elem_class})')

            desc = ' '.join(desc_parts) if desc_parts else 'Unnamed element'

            # Add coordinate information
            lines.append(f"{i}. {desc} at position ({center[0]}, {center[1]})")

        return '\n'.join(lines)