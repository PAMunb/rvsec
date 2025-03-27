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

    ### Architectural Decisions:
    - Implements a deterministic fingerprinting algorithm for reproducible state identification
    - Uses elements' structural properties rather than visual appearance for stability
    - Applies intelligent filtering to exclude volatile or irrelevant UI elements
    - Supports context-aware fingerprinting with configurable precision levels
    - Optimizes computation by focusing on the most distinctive screen elements

    ### Role in the System:
    - Provides stable, unique identifiers for application states
    - Enables reliable state tracking and transition analysis
    - Supports memory systems with consistent state identification
    - Minimizes false state change detection due to irrelevant UI elements
    """

    def __init__(self, ignore_dynamic_content: bool = True,
                 ignore_system_elements: bool = True,
                 prioritize_interactive_elements: bool = True):
        """
        Initialize the state fingerprinter.

        Args:
            ignore_dynamic_content: Whether to ignore elements with dynamic content
            ignore_system_elements: Whether to ignore system UI elements
            prioritize_interactive_elements: Whether to prioritize interactive elements
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.memory.state_fingerprinter",
            {CONTEXT_COMPONENT: "StateFingerprinter"}
        )

        # Configuration options
        self.ignore_dynamic_content = ignore_dynamic_content
        self.ignore_system_elements = ignore_system_elements
        self.prioritize_interactive_elements = prioritize_interactive_elements

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

        # Interactive element classes for prioritization
        self.interactive_classes = {
            "Button",
            "CheckBox",
            "RadioButton",
            "Spinner",
            "EditText",
            "Switch"
        }

        self.logger.info("Initialized state fingerprinter")

    def generate_fingerprint(self, screen: ScreenDescription,
                             state_data: Dict[str, Any]) -> str:
        """
        Generate a stable fingerprint for the current application state.

        Args:
            screen: Parsed screen description
            state_data: Raw state data

        Returns:
            State fingerprint string
        """
        # Start with activity name as base component
        components = [screen.activity]

        # Extract essential UI elements that define the state
        ui_elements = self._extract_significant_elements(screen)
        components.extend(ui_elements)

        # Create fingerprint from combined components
        fingerprint = self._create_hash_from_components(components)

        return fingerprint

    def _extract_significant_elements(self, screen: ScreenDescription) -> List[str]:
        """
        Extract significant UI elements that define the state.

        Args:
            screen: Parsed screen description

        Returns:
            List of element identifiers
        """
        # Lists to store elements by priority
        priority_elements = []
        standard_elements = []

        # Track processed resource IDs to avoid duplicates
        processed_ids: Set[str] = set()

        # Process all items
        for item in screen.items:
            # Skip system elements if configured
            if self.ignore_system_elements:
                item_class = item.view.get("class", "")
                if any(pkg in item_class for pkg in self.system_packages):
                    continue

            # Extract key properties that identify the element
            element_id = item.view.get("resource_id", "")
            element_class = item.view.get("class", "")
            element_text = item.view.get("text", "")

            # Skip if we've already processed this resource ID
            if element_id and element_id in processed_ids:
                continue

            # Add to processed IDs if not empty
            if element_id:
                processed_ids.add(element_id)

            # Skip dynamic content if configured
            if self.ignore_dynamic_content and element_text:
                if any(pattern in element_text.lower() for pattern in self.dynamic_content_patterns):
                    # Replace dynamic content with placeholder
                    element_text = "<dynamic_content>"

            # Create element signature
            element_signature = None
            if element_id:
                element_signature = f"id:{element_id}"
            elif element_text:
                element_signature = f"text:{element_text}:{element_class}"
            elif element_class:
                # When no better identifier is available, use class
                element_signature = f"class:{element_class}"

            if not element_signature:
                continue

            # Determine if this is an interactive element
            is_interactive = any(cls in element_class for cls in self.interactive_classes)

            # Add to appropriate list based on priority
            if self.prioritize_interactive_elements and is_interactive:
                priority_elements.append(element_signature)
            else:
                standard_elements.append(element_signature)

        # Combine and sort elements
        all_elements = priority_elements + standard_elements
        all_elements.sort()

        return all_elements

    def _create_hash_from_components(self, components: List[str]) -> str:
        """
        Create a hash from component strings.

        Args:
            components: List of component strings

        Returns:
            Hash string
        """
        # Join components and create hash
        combined = "|".join(components)
        return hashlib.md5(combined.encode()).hexdigest()

    def is_same_state(self, fingerprint1: str, fingerprint2: str) -> bool:
        """
        Check if two fingerprints represent the same state.

        Args:
            fingerprint1: First fingerprint
            fingerprint2: Second fingerprint

        Returns:
            True if same state, False otherwise
        """
        return fingerprint1 == fingerprint2
