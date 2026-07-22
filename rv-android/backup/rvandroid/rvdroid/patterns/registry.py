# rvandroid/rvdroid/patterns/registry.py

"""
Pattern registry module for RVDroid.

This module provides a centralized registry that uses the core pattern detectors from 
rvandroid.core.patterns to identify UI patterns during application exploration.
"""

from typing import Dict, Any, List, Optional, Set
import time
from enum import Enum

from rvandroid.analysis.patterns import (
    PatternType as CorePatternType,
    UIPatternDetectorManager,
    PatternResult
)
from rvandroid.parser.screen.visitor.model import ScreenDescription
from rvandroid.rvdroid.core.component import Component
from rvandroid.util.error.decorators import handle_error


class PatternType(Enum):
    """Pattern type constants matching core pattern types."""
    FORM = "form"
    LIST = "list" 
    NAVIGATION = "navigation"
    TABS = "tabs"
    DIALOG = "dialog"
    CAROUSEL = "carousel"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_core_type(cls, core_type: CorePatternType) -> 'PatternType':
        """Convert core pattern type to local enum."""
        return cls(core_type.value)


class UIPattern:
    """
    Adapter class that wraps the core pattern results in a RVDroid-compatible interface.
    
    ### Architectural Decisions:
    - Implements a lightweight wrapper around core pattern detection results
    - Provides compatibility with existing exploration components
    - Maintains consistent interface while delegating to core implementation
    - Supports serialization for persistent storage
    
    ### Role in the System:
    - Represents recognized UI patterns in a standardized format
    - Enables pattern-based testing strategies and heuristics
    - Facilitates intelligent exploration based on UI patterns
    """
    
    def __init__(self, pattern_id: str, pattern_type: PatternType, confidence: float = 1.0):
        """
        Initialize a UI pattern instance.
        
        Args:
            pattern_id: Unique pattern identifier
            pattern_type: Type of pattern
            confidence: Pattern detection confidence (0.0 to 1.0)
        """
        self.id = pattern_id
        self.type = pattern_type.value
        self.confidence = confidence
        self.detection_time = time.time()
        self.occurrence_count = 1
        self.last_seen = self.detection_time
        self.associated_states: Set[str] = set()
        self.properties: Dict[str, Any] = {}
        
    @classmethod
    def from_core_result(cls, pattern_result: PatternResult, pattern_id: str) -> 'UIPattern':
        """
        Create a UIPattern from a core PatternResult.
        
        Args:
            pattern_result: Core pattern detection result
            pattern_id: Unique identifier for the pattern
            
        Returns:
            UIPattern instance
        """
        pattern = cls(
            pattern_id=pattern_id,
            pattern_type=PatternType.from_core_type(pattern_result.type),
            confidence=pattern_result.confidence
        )
        
        # Copy properties
        for key, value in pattern_result.properties.items():
            pattern.add_property(key, value)
            
        # Add elements information
        pattern.add_property("elements", [
            {
                "id": element.id,
                "role": element.role,
                "required": element.required,
                "properties": element.properties
            }
            for element in pattern_result.elements
        ])
        
        return pattern
        
    def update_occurrence(self, state_fingerprint: Optional[str] = None) -> None:
        """
        Update occurrence information for this pattern.
        
        Args:
            state_fingerprint: Optional state fingerprint where pattern was detected
        """
        self.occurrence_count += 1
        self.last_seen = time.time()
        
        if state_fingerprint:
            self.associated_states.add(state_fingerprint)
            
    def add_property(self, key: str, value: Any) -> None:
        """
        Add a property to this pattern.
        
        Args:
            key: Property key
            value: Property value
        """
        self.properties[key] = value
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert pattern to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "type": self.type,
            "confidence": self.confidence,
            "detection_time": self.detection_time,
            "occurrence_count": self.occurrence_count,
            "last_seen": self.last_seen,
            "associated_states": list(self.associated_states),
            "properties": self.properties
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UIPattern':
        """
        Create a pattern from dictionary representation.
        
        Args:
            data: Dictionary representation
            
        Returns:
            UIPattern instance
        """
        pattern = cls(
            pattern_id=data["id"],
            pattern_type=PatternType(data["type"]),
            confidence=data["confidence"]
        )
        
        pattern.detection_time = data["detection_time"]
        pattern.occurrence_count = data["occurrence_count"]
        pattern.last_seen = data["last_seen"]
        pattern.associated_states = set(data["associated_states"])
        pattern.properties = data["properties"]
        
        return pattern


class PatternRegistry(Component):
    """
    Central registry for UI pattern detection that uses core pattern detectors.
    
    ### Architectural Decisions:
    - Delegates pattern detection to core UIPatternDetectorManager
    - Provides consistent interface for pattern detection and retrieval
    - Leverages the core pattern detection system for efficiency
    - Maintains state tracking and pattern statistics
    - Integrates with the component-based architecture for lifecycle management
    
    ### Role in the System:
    - Coordinates pattern detection across the testing process
    - Maintains a record of detected UI patterns and their occurrences
    - Provides access to pattern information for guided exploration
    - Enables analysis of UI pattern prevalence and distribution
    - Supports pattern-based testing strategies
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the pattern registry.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__("PatternRegistry", config)
        
        # Pattern catalog for tracking pattern instances
        self.patterns: Dict[str, UIPattern] = {}
        
        # Pattern type tracking
        self.pattern_types: Dict[str, int] = {}
        
        # Static data extracted from config
        static_data = self.config.get("static_data")
        
        # Create core pattern detector manager
        self.pattern_detector_manager = UIPatternDetectorManager(static_data)
        
        # Pattern cache for quick lookup
        self.pattern_cache = {}
        
    @handle_error(level="ERROR")
    def initialize(self) -> bool:
        """
        Initialize the pattern registry.
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        self.logger.info("Initializing pattern registry with core pattern detectors")
        
        # Clear any existing patterns
        self.patterns = {}
        self.pattern_types = {}
        self.pattern_cache = {}
        
        self.initialized = True
        return True
        
    @handle_error(level="ERROR")
    def start(self) -> bool:
        """
        Start the pattern registry.
        
        Returns:
            True if start succeeded, False otherwise
        """
        if not self.initialized:
            self.logger.error("Cannot start: registry not initialized")
            return False
            
        self.logger.info("Starting pattern registry")
        
        self.running = True
        return True
        
    @handle_error(level="ERROR")
    def stop(self) -> bool:
        """
        Stop the pattern registry.
        
        Returns:
            True if stop succeeded, False otherwise
        """
        if not self.running:
            self.logger.warning("Pattern registry is not running")
            return True
            
        self.logger.info("Stopping pattern registry")
        
        self.running = False
        return True
        
    @handle_error(level="ERROR")
    def cleanup(self) -> None:
        """
        Clean up registry resources.
        """
        self.logger.info("Cleaning up pattern registry")
        
        # Clear patterns
        self.patterns = {}
        self.pattern_types = {}
        
        # Clear cache
        self.pattern_cache = {}
        
        # Clear core detector's cache
        self.pattern_detector_manager.clear_cache()
        
        self.initialized = False
        self.running = False
        
    @handle_error(level="WARN")
    def detect_patterns(self, screen: ScreenDescription, 
                        state_data: Dict[str, Any]) -> List[UIPattern]:
        """
        Detect patterns in a UI screen using core pattern detectors.
        
        Args:
            screen: Parsed screen description
            state_data: Raw state data
            
        Returns:
            List of detected patterns
        """
        if not self.running:
            self.logger.warning("Pattern registry is not running")
            return []
            
        # Get fingerprint for caching
        fingerprint = state_data.get("fingerprint")
        
        # Check cache
        if fingerprint and fingerprint in self.pattern_cache:
            return self.pattern_cache[fingerprint]
            
        # Detect patterns using core detector
        core_pattern_results = self.pattern_detector_manager.detect_patterns(screen, state_data)
        
        # Enrich with MOP information if available
        if hasattr(self.pattern_detector_manager, 'enrich_patterns_with_mop_info'):
            core_pattern_results = self.pattern_detector_manager.enrich_patterns_with_mop_info(core_pattern_results)
        
        # Convert to RVDroid patterns
        all_patterns = []
        
        for pattern_type, pattern_result in core_pattern_results.items():
            # Generate a unique ID for the pattern
            pattern_id = f"{pattern_type.value}_{fingerprint}" if fingerprint else f"{pattern_type.value}_{int(time.time())}"
            
            # Create a UIPattern from the core result
            pattern = UIPattern.from_core_result(pattern_result, pattern_id)
            
            # Track state association
            if fingerprint:
                pattern.associated_states.add(fingerprint)
            
            # Update existing pattern or add new one
            if pattern.id in self.patterns:
                # Update existing pattern
                existing_pattern = self.patterns[pattern.id]
                existing_pattern.update_occurrence(fingerprint)
                
                # Use highest confidence
                if pattern.confidence > existing_pattern.confidence:
                    existing_pattern.confidence = pattern.confidence
                    
                # Add additional properties
                for key, value in pattern.properties.items():
                    existing_pattern.add_property(key, value)
                    
                all_patterns.append(existing_pattern)
            else:
                # Add new pattern
                self.patterns[pattern.id] = pattern
                
                # Update pattern type count
                if pattern.type not in self.pattern_types:
                    self.pattern_types[pattern.type] = 0
                self.pattern_types[pattern.type] += 1
                
                all_patterns.append(pattern)
        
        # Cache result
        if fingerprint:
            self.pattern_cache[fingerprint] = all_patterns
        
        self.logger.debug(f"Detected {len(all_patterns)} patterns")
        return all_patterns
        
    @handle_error(level="WARN")
    def get_pattern_by_id(self, pattern_id: str) -> Optional[UIPattern]:
        """
        Get a pattern by ID.
        
        Args:
            pattern_id: Pattern ID
            
        Returns:
            UIPattern or None if not found
        """
        return self.patterns.get(pattern_id)
        
    @handle_error(level="WARN")
    def get_patterns_by_type(self, pattern_type: str) -> List[UIPattern]:
        """
        Get patterns by type.
        
        Args:
            pattern_type: Pattern type
            
        Returns:
            List of patterns
        """
        return [p for p in self.patterns.values() if p.type == pattern_type]
        
    @handle_error(level="WARN")
    def get_patterns_by_state(self, state_fingerprint: str) -> List[UIPattern]:
        """
        Get patterns by state.
        
        Args:
            state_fingerprint: State fingerprint
            
        Returns:
            List of patterns
        """
        return [p for p in self.patterns.values() if state_fingerprint in p.associated_states]
        
    def get_pattern_stats(self) -> Dict[str, Any]:
        """
        Get pattern statistics.
        
        Returns:
            Dictionary with pattern statistics
        """
        total_patterns = len(self.patterns)
        
        # Calculate pattern type distribution
        type_distribution = {}
        for pattern_type, count in self.pattern_types.items():
            if total_patterns > 0:
                type_distribution[pattern_type] = round(count / total_patterns, 2)
            else:
                type_distribution[pattern_type] = 0
                
        return {
            "total_patterns": total_patterns,
            "pattern_types": dict(self.pattern_types),
            "type_distribution": type_distribution,
            "pattern_cache_size": len(self.pattern_cache)
        }
        
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        Get a summary of pattern detection progress.
        
        Returns:
            Dictionary with progress information
        """
        # Calculate pattern occurrence metrics
        avg_occurrence = 0
        max_occurrence = 0
        
        if self.patterns:
            occurrences = [p.occurrence_count for p in self.patterns.values()]
            avg_occurrence = sum(occurrences) / len(occurrences)
            max_occurrence = max(occurrences)
            
        # Determine pattern coverage
        state_coverage = set()
        for pattern in self.patterns.values():
            state_coverage.update(pattern.associated_states)
            
        return {
            "total_patterns": len(self.patterns),
            "pattern_types": dict(self.pattern_types),
            "avg_occurrence": avg_occurrence,
            "max_occurrence": max_occurrence,
            "covered_states": len(state_coverage)
        }