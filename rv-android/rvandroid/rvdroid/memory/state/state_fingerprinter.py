# rvandroid/rvdroid/memory/state/state_fingerprinter.py

"""
State fingerprinting module for RVDroid.

This module provides mechanisms for generating consistent state fingerprints
based on UI elements, layout structure, and activity information.
"""

import hashlib
from typing import Dict, Any, List, Set

from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class StateFingerprinter:
    """
    Generates unique fingerprints for application states.

    Creates stable identifiers that combine activity name and UI structure,
    allowing the system to reliably identify and track application states.

    ### Architectural Decisions:
    - Combines activity name and UI structure for reliable state identification
    - Filters out unstable or irrelevant UI elements to improve consistency
    - Prioritizes structural elements over dynamic content
    - Uses robust hashing algorithm to minimize collision risk
    """

    def __init__(self, ignore_dynamic_content: bool = True):
        """
        Initialize the state fingerprinter.

        Args:
            ignore_dynamic_content: Whether to ignore elements with dynamic content
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.memory.state_fingerprinter",
            {CONTEXT_COMPONENT: "StateFingerprinter"}
        )

        # Configuration options
        self.ignore_dynamic_content = ignore_dynamic_content

        # System package prefixes to ignore
        self.system_packages = {
            "android",
            "com.android",
            "com.google.android",
            "androidx"
        }

        # Dynamic content identifiers
        self.dynamic_content_patterns = {
            "timestamp",
            "counter",
            "random",
            "uuid",
            "id="
        }

        self.logger.info("Initialized state fingerprinter")

    def generate_fingerprint(self, screen: ScreenDescription,
                             state_data: Dict[str, Any]) -> str:
        """
        Generate a stable fingerprint for the current application state.

        The fingerprint combines the activity name with essential UI elements
        to ensure states are reliably identified even with minor UI changes.

        Args:
            screen: Parsed screen description
            state_data: Raw state data

        Returns:
            State fingerprint string
        """
        # Start with activity name as base component
        activity_name = screen.activity
        components = [activity_name]

        # Extract essential UI elements that define the state
        ui_elements = self._extract_significant_elements(screen)
        components.extend(ui_elements)

        # Create fingerprint from combined components
        fingerprint = self._create_hash_from_components(components)

        # Log components for debugging if needed
        if len(ui_elements) < 5:
            self.logger.debug(f"State fingerprint components for {activity_name}: {ui_elements}")
        else:
            self.logger.debug(f"State fingerprint based on {len(ui_elements)} elements for {activity_name}")

        return fingerprint

    def _extract_significant_elements(self, screen: ScreenDescription) -> List[str]:
        """
        Extract significant UI elements that define the state.

        Focuses on stable identifiers like resource IDs and avoids
        dynamic content that might change between instances.

        Args:
            screen: Parsed screen description

        Returns:
            List of element identifiers
        """
        # Lists to store elements by type
        id_elements = []  # Elements with resource IDs
        text_elements = []  # Elements with text
        structural_elements = []  # Elements with just a class name

        # Track processed resource IDs to avoid duplicates
        processed_ids: Set[str] = set()

        # Process all items
        for item in screen.items:
            # Skip system elements
            item_class = item.view.get("class", "")
            if any(pkg in item_class for pkg in self.system_packages):
                continue

            # Extract key properties
            element_id = item.view.get("resource_id", "")
            element_class = item.view.get("class", "")
            element_text = item.view.get("text", "").strip()

            # Skip if we've already processed this resource ID
            if element_id and element_id in processed_ids:
                continue

            # Add to processed IDs if not empty
            if element_id:
                processed_ids.add(element_id)

            # Skip dynamic content if configured
            if self.ignore_dynamic_content and element_text:
                if any(pattern in element_text.lower() for pattern in self.dynamic_content_patterns):
                    # Replace dynamic content with placeholder or skip
                    element_text = "<dynamic_content>"

            # Categorize by available properties
            if element_id:
                id_elements.append(f"id:{element_id}")
            elif element_text:
                # Only include text if it's meaningful
                if len(element_text) > 1:
                    text_elements.append(f"text:{element_text}:{element_class}")
            elif element_class:
                # For structural elements, include bounds to avoid confusion
                bounds = item.view.get("bounds", [])
                if bounds and len(bounds) == 2:
                    x1, y1 = bounds[0]
                    x2, y2 = bounds[1]
                    area = (x2 - x1) * (y2 - y1)
                    # Only include larger elements
                    if area > 1000:
                        structural_elements.append(f"class:{element_class}:{x1}_{y1}_{x2}_{y2}")
                else:
                    structural_elements.append(f"class:{element_class}")

        # Sort each category for consistency
        id_elements.sort()
        text_elements.sort()
        structural_elements.sort()

        # Combine elements with priority for more stable identifiers
        return id_elements + text_elements + structural_elements

    def _create_hash_from_components(self, components: List[str]) -> str:
        """
        Create a hash from component strings.

        Args:
            components: List of component strings

        Returns:
            Hash string
        """
        # Create a deterministic string representation
        combined = "|".join(components)

        # Use MD5 for quick and reliable hashing
        return hashlib.md5(combined.encode()).hexdigest()
