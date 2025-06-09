# rvandroid/analysis/patterns/pattern_data.py
"""
Pattern data structures for UI pattern detection.

This module provides data classes to represent UI patterns detected
in Android application screens. These data structures are used to
enrich the screen description with pattern information.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any


class PatternType(Enum):
    """Types of UI patterns that can be detected."""
    FORM = "form"
    LIST = "list"
    TABS = "tabs"
    NAVIGATION = "navigation"
    DIALOG = "dialog"
    CAROUSEL = "carousel"
    UNKNOWN = "unknown"


@dataclass
class PatternData:
    """
    Represents a UI pattern detected in the screen.

    This class encapsulates all information about a detected UI pattern,
    including its type, role within the pattern, and specific properties.
    It is used to enrich ScreenItems with pattern information.

    ### Architectural Decisions:
    - Uses dataclass for clean serialization and property access
    - Maintains a standardized structure for all pattern types
    - Supports rich property sets for specialized pattern characteristics
    - Enables pattern relationship tracking across UI elements

    ### Role in the System:
    - Provides structured pattern data for LLM prompt enhancement
    - Enables advanced UI analysis for testing strategy selection
    - Facilitates pattern-based batch action generation
    - Supports comprehensive pattern-aware UI exploration
    """

    type: PatternType
    role: str
    confidence: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate the pattern data after initialization."""
        if not isinstance(self.type, PatternType):
            raise ValueError(f"type must be a PatternType enum, got {type(self.type)}")

        if not self.role:
            raise ValueError("role cannot be empty")

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the pattern data to a dictionary representation.

        Returns:
            Dictionary representation of the pattern data
        """
        return {
            "type": self.type.value,
            "role": self.role,
            "confidence": self.confidence,
            "properties": self.properties.copy()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PatternData':
        """
        Create a PatternData instance from a dictionary.

        Args:
            data: Dictionary containing pattern data

        Returns:
            PatternData instance
        """
        pattern_type = PatternType(data["type"]) if "type" in data else PatternType.UNKNOWN
        role = data.get("role", "unknown")
        confidence = data.get("confidence", 0.0)
        properties = data.get("properties", {})

        return cls(
            type=pattern_type,
            role=role,
            confidence=confidence,
            properties=properties
        )


@dataclass
class PatternResult:
    """
    Result of a pattern detection operation.

    This class contains the overall result of a pattern detection,
    including the pattern type, confidence score, and other metadata.

    ### Role in the System:
    - Provides pattern detection results for UI analysis
    - Enables confidence-based decision making for pattern application
    - Supports pattern metadata for downstream processing
    """

    type: PatternType
    confidence: float = 0.0
    elements_count: int = 0
    properties: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """
        Check if this is a valid pattern with sufficient confidence.

        Returns:
            True if the pattern is valid, False otherwise
        """
        return self.confidence >= 0.7 and self.elements_count > 0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary representation of the pattern result
        """
        return {
            "type": self.type.value,
            "confidence": self.confidence,
            "elements_count": self.elements_count,
            "properties": self.properties.copy()
        }
   