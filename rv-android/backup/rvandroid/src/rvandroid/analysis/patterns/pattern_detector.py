# rvandroid/analysis/patterns/pattern_detector.py
"""
Base interface for UI pattern detectors.

This module provides the base interface and abstract classes for UI
pattern detectors used in screen analysis.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type, ClassVar

from rv_android_core.analysis.patterns.pattern_data import PatternType, PatternData, PatternResult
from rv_android_core.analysis.patterns.ui_pattern_utils import UIPatternUtils
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ScreenItem
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class IPatternDetector(ABC):
    """
    Interface for pattern detectors.

    This interface defines the contract that all pattern detectors
    must implement to provide consistent behavior and integration
    with the UI pattern detection system.
    """

    @property
    @abstractmethod
    def pattern_type(self) -> PatternType:
        """Get the pattern type detected by this detector."""
        pass

    @abstractmethod
    def detect(self, screen: ScreenDescription) -> PatternResult:
        """
        Detect patterns in a screen.

        Args:
            screen: Parsed screen description

        Returns:
            PatternResult with detection results
        """
        pass


class BasePatternDetector(IPatternDetector, ABC):
    """
    Base implementation for pattern detectors.

    This class provides common functionality for all pattern detectors,
    including logging, utility methods, and standardized pattern detection.

    ### Architectural Decisions:
    - Provides a common base for all pattern detectors
    - Centralizes logging and utility functions
    - Standardizes pattern detection and result creation
    - Enables consistent behavior across different detector implementations

    ### Role in the System:
    - Serves as the foundation for specialized pattern detectors
    - Ensures consistent pattern detection behavior
    - Provides shared functionality to avoid code duplication
    - Standardizes pattern result creation and handling
    """

    def __init__(self):
        """Initialize the base pattern detector."""
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"analysis.patterns.{self.__class__.__name__.lower()}",
            {CONTEXT_COMPONENT: self.__class__.__name__}
        )

        # Utility functions
        self.utils = UIPatternUtils

    def create_pattern_data(self,
                            item: ScreenItem,
                            role: str,
                            confidence: float = 1.0,
                            properties: Optional[Dict[str, Any]] = None) -> PatternData:
        """
        Create pattern data for a screen item.

        Args:
            item: The screen item
            role: The role of the item in the pattern
            confidence: Confidence level for this assignment
            properties: Additional pattern-specific properties

        Returns:
            PatternData object
        """
        pattern_data = PatternData(
            type=self.pattern_type,
            role=role,
            confidence=confidence,
            properties=properties or {}
        )

        # Add common properties
        if "text" in item.view:
            pattern_data.properties["text"] = item.view["text"]

        if "content_description" in item.view:
            pattern_data.properties["content_description"] = item.view["content_description"]

        if "resource_id" in item.view:
            pattern_data.properties["resource_id"] = item.view["resource_id"]

        # Set bounds if available
        if "bounds" in item.view:
            pattern_data.properties["bounds"] = item.view["bounds"]

        # Store reference to actions
        pattern_data.properties["has_actions"] = len(item.actions) > 0

        return pattern_data

    def apply_pattern_to_item(self, item: ScreenItem, pattern_data: PatternData) -> None:
        """
        Apply pattern data to a screen item.

        Args:
            item: The screen item to update
            pattern_data: The pattern data to apply
        """
        # Initialize complement dictionary if needed
        if not hasattr(item, 'complement') or item.complement is None:
            item.complement = {}

        # Set pattern flag
        item.complement["has_pattern"] = True

        # Initialize patterns list if needed
        if "patterns" not in item.complement:
            item.complement["patterns"] = []

        # Add pattern data to the list
        item.complement["patterns"].append(pattern_data)

        # Add pattern type shorthand flag
        pattern_flag = f"in_{pattern_data.type.value}"
        item.complement[pattern_flag] = True

        # Add role shorthand
        role_flag = f"{pattern_data.type.value}_role"
        item.complement[role_flag] = pattern_data.role

    def create_base_result(self, pattern_type: PatternType) -> PatternResult:
        """
        Create a base pattern result.

        Args:
            pattern_type: Type of pattern

        Returns:
            Initialized PatternResult
        """
        return PatternResult(
            type=pattern_type,
            confidence=0.0,
            elements_count=0,
            properties={}
        )

    # Utility method wrappers for easier access

    def is_visible(self, item: ScreenItem) -> bool:
        """Check if an element is visible."""
        return self.utils.is_visible(item)

    def get_width_height(self, bounds: List[List[int]]) -> tuple:
        """Get width and height from bounds."""
        return self.utils.get_width_height(bounds)

    def get_center_coordinates(self, bounds: List[List[int]]) -> tuple:
        """Get center coordinates from bounds."""
        return self.utils.get_center_coordinates(bounds)

    def get_direct_children(self, container: ScreenItem, screen: ScreenDescription) -> List[ScreenItem]:
        """Get direct children of a container."""
        return self.utils.get_direct_children(container, screen)

    def is_horizontal_arrangement(self, items: List[ScreenItem]) -> bool:
        """Check if items are arranged horizontally."""
        return self.utils.is_horizontal_arrangement(items)

    def is_vertical_arrangement(self, items: List[ScreenItem]) -> bool:
        """Check if items are arranged vertically."""
        return self.utils.is_vertical_arrangement(items)

    def calculate_overlap_percentage(self, bounds1: List[List[int]], bounds2: List[List[int]]) -> float:
        """Calculate overlap percentage between two bounds."""
        return self.utils.calculate_overlap_percentage(bounds1, bounds2)

    def find_elements_by_property(self, screen: ScreenDescription, property_check_func) -> List[ScreenItem]:
        """Find elements by a property check function."""
        return self.utils.find_elements_by_property(screen, property_check_func)

    def estimate_screen_dimensions(self, screen: ScreenDescription) -> tuple:
        """Estimate screen dimensions."""
        return self.utils.estimate_screen_dimensions(screen)

    def get_resource_id(self, view:  Dict[str, Any]):
        return self.get_view_property("resource_id", view)

    def get_view_property(self, property_name: str, view: Dict[str, Any]):
        property = view.get(property_name, "")
        if property is None:
            property = ""
        return property.lower()


class PatternDetectorRegistry:
    """
    Registry for pattern detectors.

    This class manages the registration and retrieval of pattern detectors,
    providing a central point of access for all available detectors.

    ### Architectural Decisions:
    - Implements a registry pattern for detector discovery
    - Manages detector initialization and lifecycle
    - Provides type-safe detector registration and retrieval
    - Enables dynamic detector discovery and configuration

    ### Role in the System:
    - Centralizes detector management
    - Facilitates detector discovery and instantiation
    - Provides a consistent interface for detector access
    - Supports extensibility through dynamic registration
    """

    _detectors: ClassVar[Dict[PatternType, Type[IPatternDetector]]] = {}

    @classmethod
    def register(cls, detector_class: Type[IPatternDetector]) -> None:
        """
        Register a pattern detector.

        Args:
            detector_class: Detector class to register
        """
        detector = detector_class()
        pattern_type = detector.pattern_type
        cls._detectors[pattern_type] = detector_class

    @classmethod
    def create(cls, pattern_type: PatternType) -> Optional[IPatternDetector]:
        """
        Create a pattern detector for the specified type.

        Args:
            pattern_type: Type of pattern to detect

        Returns:
            Pattern detector or None if not found
        """
        detector_class = cls._detectors.get(pattern_type)
        if not detector_class:
            return None

        return detector_class()

    @classmethod
    def get_all_detectors(cls) -> List[IPatternDetector]:
        """
        Get all registered pattern detectors.

        Returns:
            List of pattern detector instances
        """
        return [detector_class() for detector_class in cls._detectors.values()]


class UIPatternDetectorManager:
    """
    Manages the pattern detection process across multiple detectors.

    This class coordinates the detection of UI patterns using registered
    specialized detectors, providing a unified interface for pattern detection.

    ### Architectural Decisions:
    - Implements a centralized manager for pattern detection
    - Coordinates multiple specialized detectors
    - Provides aggregated pattern detection results
    - Enables enrichment of screen items with pattern data

    ### Role in the System:
    - Serves as the entry point for pattern detection
    - Coordinates specialized pattern detectors
    - Aggregates and prioritizes pattern detection results
    - Enriches screen descriptions with pattern information
    """

    def __init__(self):
        """Initialize the UI pattern detector manager."""
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "analysis.patterns.detector_manager",
            {CONTEXT_COMPONENT: "UIPatternDetectorManager"}
        )

        # Initialize detectors
        self._load_detectors()

        self.logger.info(f"Initialized UI pattern detector manager with {len(self.detectors)} detectors")

    def _load_detectors(self) -> None:
        """Load and initialize all available detectors."""
        # Import detectors here to avoid circular imports
        from rv_android_core.analysis.patterns.form_detector import FormDetector
        from rv_android_core.analysis.patterns.list_detector import ListDetector
        from rv_android_core.analysis.patterns.tab_detector import TabDetector
        from rv_android_core.analysis.patterns.navigation_detector import NavigationDetector
        from rv_android_core.analysis.patterns.dialog_detector import DialogDetector

        # Register detectors
        PatternDetectorRegistry.register(FormDetector)
        PatternDetectorRegistry.register(ListDetector)
        PatternDetectorRegistry.register(TabDetector)
        PatternDetectorRegistry.register(NavigationDetector)
        PatternDetectorRegistry.register(DialogDetector)

        # Get all detectors
        self.detectors = PatternDetectorRegistry.get_all_detectors()

    def detect_patterns(self, screen: ScreenDescription) -> Dict[PatternType, PatternResult]:
        """
        Detect all patterns in a screen.

        Args:
            screen: Parsed screen description

        Returns:
            Dictionary mapping pattern types to detection results
        """
        results = {}

        # Run all detectors
        for detector in self.detectors:
            try:
                pattern_result = detector.detect(screen)

                # Only include valid patterns
                if pattern_result.is_valid():
                    results[detector.pattern_type] = pattern_result
                    self.logger.debug(
                        f"Detected {detector.pattern_type.value} "
                        f"with confidence {pattern_result.confidence:.2f}"
                    )

            except Exception as e:
                self.logger.error(f"Error in pattern detector {detector.pattern_type.value}: {e}")
                import traceback
                traceback.print_exc()

        return results

    def get_dominant_pattern(self, screen: ScreenDescription) -> Optional[tuple]:
        """
        Get the dominant pattern in a screen.

        Args:
            screen: Parsed screen description

        Returns:
            Tuple of (pattern_type, pattern_result) or None if no patterns detected
        """
        patterns = self.detect_patterns(screen)

        if not patterns:
            return None

        # Find the pattern with highest confidence
        dominant_pattern = max(patterns.items(), key=lambda x: x[1].confidence)

        return dominant_pattern

    def enrich_screen_with_patterns(self, screen: ScreenDescription) -> ScreenDescription:
        """
        Enrich screen description with detected patterns.

        Args:
            screen: Original screen description

        Returns:
            Enriched screen description
        """
        # Detect patterns
        patterns = self.detect_patterns(screen)

        # Mark the screen as pattern-enriched at the global level
        if not hasattr(screen, 'complement') or screen.complement is None:
            screen.complement = {}

        screen.complement["has_patterns"] = len(patterns) > 0

        # We'll add pattern types at screen level for easy filtering
        detected_pattern_types = []

        # Each detector already applies its patterns to the individual items
        # Here we just collect information about which patterns were detected
        for pattern_type, pattern_result in patterns.items():
            self.logger.debug(f"Adding {pattern_type.value} pattern information")
            detected_pattern_types.append(pattern_type.value)

        # Store detected pattern types for screen-level queries
        screen.complement["detected_patterns"] = detected_pattern_types

        return screen
