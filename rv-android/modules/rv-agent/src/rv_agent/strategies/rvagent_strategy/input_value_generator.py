"""
Input Value Generator - Generates test values for input fields.

Provides value variations for EditText elements to increase coverage.
Distinguishes between regular fields and MOP-reaching fields for
specialized test values.
"""

import logging
from collections import defaultdict
from typing import List, Optional, Dict


logger = logging.getLogger(__name__)


class InputValueGenerator:
    """
    Generates test values for input fields with variation tracking.

    Strategy:
    - Regular fields: Generic test values (empty, short text, longer text)
    - MOP fields: Security-focused values (boundary, injection attempts)

    Tracks which values have been tested per element to avoid repetition.

    Example:
        generator = InputValueGenerator(max_variations=3)

        # First call for email field
        value1 = generator.get_next_value("email_input", is_mop=False)
        # Returns: ""

        # Second call
        value2 = generator.get_next_value("email_input", is_mop=False)
        # Returns: "test"

        # Third call
        value3 = generator.get_next_value("email_input", is_mop=False)
        # Returns: "longer test input value"

        # Fourth call
        value4 = generator.get_next_value("email_input", is_mop=False)
        # Returns: None (all variations exhausted)
    """

    def __init__(self, max_variations: int = 3):
        """
        Initialize input value generator.

        Args:
            max_variations: Maximum number of values to test per element (default: 3)
        """
        if max_variations < 1:
            raise ValueError(f"max_variations must be >= 1, got {max_variations}")

        self.max_variations = max_variations

        # Maps element_id → list of values already tested
        self.tested_values: Dict[str, List[str]] = defaultdict(list)

        logger.info(f"InputValueGenerator initialized with max_variations={max_variations}")

    def get_next_value(
        self,
        element_id: str,
        is_mop: bool = False
    ) -> Optional[str]:
        """
        Get next untested value for an input element.

        Args:
            element_id: Unique identifier for the element (widget_id or coordinate)
            is_mop: True if element reaches MOP (uses security-focused values)

        Returns:
            Next test value, or None if all variations exhausted
        """
        tested = self.tested_values[element_id]

        # Check if exhausted
        if len(tested) >= self.max_variations:
            logger.debug(f"Element {element_id}: all {self.max_variations} variations tested")
            return None

        # Get candidate values based on MOP status
        if is_mop:
            candidates = self._get_mop_values()
        else:
            candidates = self._get_regular_values()

        # Find first untested value
        for value in candidates:
            if value not in tested:
                self.tested_values[element_id].append(value)
                logger.debug(
                    f"Element {element_id}: testing value #{len(tested) + 1}: "
                    f"'{value[:20]}{'...' if len(value) > 20 else ''}'"
                )
                return value

        # Shouldn't reach here if max_variations is correct, but handle gracefully
        logger.warning(
            f"Element {element_id}: ran out of candidate values "
            f"(tested={len(tested)}, candidates={len(candidates)})"
        )
        return None

    def _get_regular_values(self) -> List[str]:
        """
        Get test values for regular input fields.

        Returns:
            List of generic test values
        """
        return [
            "",                              # Empty (test required field validation)
            "test",                          # Short text
            "longer test input value",       # Longer text (test field capacity)
        ]

    def _get_mop_values(self) -> List[str]:
        """
        Get test values for MOP-reaching input fields.

        These values target security-relevant scenarios:
        - Boundary values (empty, zero, negative, max)
        - Injection attempts (path traversal, SQL, XSS)
        - Special characters

        Returns:
            List of security-focused test values
        """
        return [
            "",                              # Empty
            "0",                             # Zero
            "-1",                            # Negative
            "2147483647",                    # MAX_INT
            "../../../etc/passwd",           # Path traversal
            "' OR '1'='1",                  # SQL injection
        ]

    def get_tested_count(self, element_id: str) -> int:
        """
        Get number of values already tested for an element.

        Args:
            element_id: Element to check

        Returns:
            Number of values tested
        """
        return len(self.tested_values.get(element_id, []))

    def has_remaining_values(self, element_id: str) -> bool:
        """
        Check if element has untested values remaining.

        Args:
            element_id: Element to check

        Returns:
            True if more values can be tested
        """
        return self.get_tested_count(element_id) < self.max_variations

    def get_statistics(self) -> Dict[str, int]:
        """
        Get generator statistics.

        Returns:
            Dictionary with tracking statistics
        """
        total_elements = len(self.tested_values)
        exhausted_elements = sum(
            1 for tested in self.tested_values.values()
            if len(tested) >= self.max_variations
        )

        total_values_tested = sum(
            len(tested) for tested in self.tested_values.values()
        )

        return {
            "total_elements_tested": total_elements,
            "exhausted_elements": exhausted_elements,
            "active_elements": total_elements - exhausted_elements,
            "total_values_tested": total_values_tested,
        }

    def reset(self):
        """Reset generator state (clear all tested values)."""
        self.tested_values.clear()
        logger.info("InputValueGenerator reset")

    def __repr__(self) -> str:
        """String representation for debugging."""
        stats = self.get_statistics()
        return (
            f"InputValueGenerator(max_variations={self.max_variations}, "
            f"elements={stats['total_elements_tested']}, "
            f"values={stats['total_values_tested']})"
        )
