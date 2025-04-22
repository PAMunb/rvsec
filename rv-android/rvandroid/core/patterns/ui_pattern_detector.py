# rvandroid/core/patterns/ui_pattern_detector.py
"""
UI Pattern Detector base implementation.

This module provides the base classes for detecting UI patterns in application screens,
which is a core component of the Flow-Based Batch Action Strategy.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Set, Tuple, Type, ClassVar

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.llm.constants import StateEntry
from rvandroid.parser.screen.visitor.model import ItemAction, ScreenItem, ScreenDescription
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class PatternType(Enum):
    """Types of UI patterns."""
    FORM = "form"
    LIST = "list"
    TABS = "tabs"
    NAVIGATION = "navigation"
    DIALOG = "dialog"
    CAROUSEL = "carousel"
    UNKNOWN = "unknown"


@dataclass
class PatternElement:
    """Represents an element within a detected pattern."""
    id: str  # Element identifier (resource_id or generated id)
    role: str  # Role within the pattern (e.g., "input", "submit", "option")
    view: Dict[str, Any]  # Original view data
    actions: List[ItemAction] = field(default_factory=list)  # Available actions
    required: bool = False  # Whether this element is required for the pattern
    properties: Dict[str, Any] = field(default_factory=dict)  # Additional properties


@dataclass
class PatternResult:
    """Result of a pattern detection."""
    type: PatternType  # Type of pattern
    confidence: float  # Confidence score (0.0-1.0)
    elements: List[PatternElement] = field(default_factory=list)  # Elements in the pattern
    properties: Dict[str, Any] = field(default_factory=dict)  # Pattern-specific properties
    
    def is_valid(self) -> bool:
        """Check if this is a valid pattern with sufficient confidence."""
        return self.confidence >= 0.7 and len(self.elements) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "type": self.type.value,
            "confidence": self.confidence,
            "elements": [
                {
                    "id": elem.id,
                    "role": elem.role,
                    "required": elem.required,
                    "properties": elem.properties
                }
                for elem in self.elements
            ],
            "properties": self.properties
        }


class IPatternDetector(ABC):
    """Interface for pattern detectors."""
    
    @abstractmethod
    def detect(self, screen: ScreenDescription, state_data: Dict[str, Any]) -> PatternResult:
        """
        Detect patterns in a screen.
        
        Args:
            screen: Parsed screen description
            state_data: Additional state data
            
        Returns:
            PatternResult with detection results
        """
        pass
    
    @property
    @abstractmethod
    def pattern_type(self) -> PatternType:
        """Get the pattern type detected by this detector."""
        pass


class PatternDetectorFactory:
    """Factory for creating pattern detectors."""
    
    _detectors: ClassVar[Dict[PatternType, Type[IPatternDetector]]] = {}
    
    @classmethod
    def register(cls, detector_class: Type[IPatternDetector]) -> None:
        """
        Register a pattern detector.
        
        Args:
            detector_class: Detector class to register
        """
        pattern_type = detector_class().pattern_type
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
    Manages the pattern detection process by coordinating multiple specialized detectors.
    
    ### Architectural Decisions:
    - Implements a coordinated pattern detection system using a detector registry
    - Uses a strategy pattern for different pattern types
    - Provides aggregated detection results with confidence scoring
    - Supports pattern enrichment with MOP relevance information
    - Caches detection results to optimize performance
    
    ### Role in the System:
    - Serves as the central manager for pattern detection
    - Coordinates specialized pattern detectors
    - Provides aggregated pattern detection results
    - Enables pattern-specific action batch generation
    - Supports MOP-aware pattern evaluation
    """
    
    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the UI pattern detector manager.
        
        Args:
            static_data: Optional static analysis data
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "core.patterns.ui_pattern_detector",
            {CONTEXT_COMPONENT: "UIPatternDetector"}
        )
        
        # Initialize core parameters
        self.static_data = static_data
        
        # Cache for pattern detection results
        self.pattern_cache = {}
        
        # Get all detectors
        self.detectors = PatternDetectorFactory.get_all_detectors()
        
        self.logger.info(f"Initialized UI pattern detector with {len(self.detectors)} detectors")
    
    def detect_patterns(self, screen: ScreenDescription, 
                       state_data: Dict[str, Any]) -> Dict[PatternType, PatternResult]:
        """
        Detect all patterns in a screen.
        
        Args:
            screen: Parsed screen description
            state_data: Additional state data
            
        Returns:
            Dictionary mapping pattern types to detection results
        """
        # Check cache for this screen
        fingerprint = state_data.get(StateEntry.FINGERPRINT)
        if fingerprint and fingerprint in self.pattern_cache:
            self.logger.debug(f"Using cached pattern results for {fingerprint}")
            return self.pattern_cache[fingerprint]
        
        results = {}
        
        # Run all detectors
        for detector in self.detectors:
            try:
                pattern_result = detector.detect(screen, state_data)
                
                # Only include valid patterns
                if pattern_result.is_valid():
                    results[detector.pattern_type] = pattern_result
                    self.logger.debug(f"Detected {detector.pattern_type.value} "
                                      f"with confidence {pattern_result.confidence:.2f}")
                
            except Exception as e:
                self.logger.error(f"Error in pattern detector {detector.pattern_type.value}: {e}")
        
        # Cache results
        if fingerprint:
            self.pattern_cache[fingerprint] = results
        
        return results
    
    def get_dominant_pattern(self, screen: ScreenDescription, 
                            state_data: Dict[str, Any]) -> Optional[Tuple[PatternType, PatternResult]]:
        """
        Get the dominant pattern in a screen.
        
        Args:
            screen: Parsed screen description
            state_data: Additional state data
            
        Returns:
            Tuple of (pattern_type, pattern_result) or None if no patterns detected
        """
        patterns = self.detect_patterns(screen, state_data)
        
        if not patterns:
            return None
        
        # Find the pattern with highest confidence
        dominant_pattern = max(patterns.items(), key=lambda x: x[1].confidence)
        
        return dominant_pattern
    
    def enrich_patterns_with_mop_info(self, patterns: Dict[PatternType, PatternResult],
                                    state_data: Dict[str, Any]) -> Dict[PatternType, PatternResult]:
        """
        Enrich pattern results with monitored operations information.
        
        Args:
            patterns: Dictionary of pattern results
            state_data: State data with MOP information
            
        Returns:
            Enriched pattern results
        """
        for pattern_type, pattern_result in patterns.items():
            # Check each element in the pattern
            for element in pattern_result.elements:
                for action in element.actions:
                    # Check if action reaches or directly reaches MOP
                    if hasattr(action, 'reaches_mop') and action.reaches_mop:
                        element.properties["reaches_mop"] = True
                        pattern_result.properties["contains_mop_related_elements"] = True
                        
                    if hasattr(action, 'directly_reaches_mop') and action.directly_reaches_mop:
                        element.properties["directly_reaches_mop"] = True
                        pattern_result.properties["contains_direct_mop_elements"] = True
        
        return patterns
    
    def clear_cache(self) -> None:
        """Clear the pattern detection cache."""
        self.pattern_cache = {}
        self.logger.debug("Cleared pattern detection cache")