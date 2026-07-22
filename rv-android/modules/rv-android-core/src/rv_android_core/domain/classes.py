"""
Domain models for class and method representation in RV-Android Core.

This module provides validated models for representing Java classes and methods
with their properties, relationships, and monitored operations tracking.
"""

from typing import Dict, List, Optional, Set

from pydantic import ConfigDict, Field
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation.base import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


@validated_model(
    [
        "class_name",
        "name",
        "params",
        "signature",
        "reachable",
        "reaches_target",
        "directly_reaches_target",
    ]
)
class Method(BaseValidatedModel):
    """
    Represents a method in a Java class with properties and relationships to monitored operations.

    ### Architectural Decisions:
    - Inherits from BaseValidatedModel for comprehensive validation
    - Supports both positional and named parameter construction for compatibility
    - Tracks method reachability and monitored operations relationships
    - Provides comprehensive serialization for analysis and debugging

    ### Role in the System:
    - Represents individual methods in static analysis data structures
    - Tracks relationships between methods and monitored operations
    - Enables reachability analysis and coverage tracking
    - Supports method signature-based identification and comparison

    ### Monitored Operations Context:
    - reaches_target: Indicates if method can reach any monitored operation
    - directly_reaches_target: Indicates if method directly calls monitored operations
    - Used for tracking both cryptographic API usage and generic specification violations
    """

    class_name: str = Field(
        ..., description="Name of the class containing this method", min_length=1
    )

    name: str = Field(..., description="Method name", min_length=1)

    params: List[str] = Field(
        default_factory=list, description="List of parameter type names"
    )

    signature: str = Field(
        ..., description="Full method signature for unique identification", min_length=1
    )

    reachable: bool = Field(
        default=False,
        description="Whether the method is reachable from application entry points",
    )

    reaches_target: bool = Field(
        default=False,
        description="Whether the method can reach any monitored operation",
    )

    directly_reaches_target: bool = Field(
        default=False,
        description="Whether the method directly calls monitored operations",
    )

    reached: bool = Field(
        default=False,
        description="Runtime flag indicating if method was actually reached during execution",
    )

    def to_json(self) -> Dict[str, any]:
        """
        Convert the method to JSON-compatible dictionary format.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "class": self.class_name,
            "name": self.name,
            "params": self.params,
            "signature": self.signature,
            "reachable": self.reachable,
            "reaches_target": self.reaches_target,
            "directly_reaches_target": self.directly_reaches_target,
        }

    def is_monitored_operation_related(self) -> bool:
        """
        Check if this method is related to monitored operations.

        Returns:
            True if method reaches or directly reaches monitored operations
        """
        return self.reaches_target or self.directly_reaches_target

    def get_analysis_summary(self) -> Dict[str, any]:
        """
        Get analysis summary for this method.

        Returns:
            Dictionary with method analysis information
        """
        return {
            "signature": self.signature,
            "reachable": self.reachable,
            "monitored_operations": {
                "reaches": self.reaches_target,
                "directly_reaches": self.directly_reaches_target,
                "is_related": self.is_monitored_operation_related(),
            },
            "runtime_reached": self.reached,
        }

    def __eq__(self, other: object) -> bool:
        """
        Compare methods for equality based on signature.

        Args:
            other: Object to compare with

        Returns:
            True if signatures are equal, False otherwise
        """
        if isinstance(other, Method):
            return self.signature == other.signature
        return False

    def __hash__(self) -> int:
        """
        Generate hash value based on method signature.

        Returns:
            Hash value for use in sets and dictionaries
        """
        return hash(self.signature)

    def __str__(self) -> str:
        """
        Get detailed string representation.

        Returns:
            Comprehensive string representation for debugging
        """
        return (
            f"Method(name={self.name}, signature={self.signature}, "
            f"reachable={self.reachable}, reaches_target={self.reaches_target}, "
            f"directly_reaches_target={self.directly_reaches_target})"
        )

    def __repr__(self) -> str:
        """
        Get concise representation based on signature.

        Returns:
            Method signature for compact representation
        """
        return self.signature


@validated_model(["name", "component_type", "is_main"])
class Clazz(BaseValidatedModel):
    """
    Represents a Java class with its components, methods, and fields.

    ### Architectural Decisions:
    - Inherits from BaseValidatedModel for type safety and validation
    - Maintains collections of methods and fields with proper typing
    - Supports Android-specific properties (component classification)
    - Provides comprehensive serialization and analysis capabilities

    ### Role in the System:
    - Represents individual Java classes in static analysis structures
    - Manages collections of methods and fields within classes
    - Tracks Android component types (activity, service, receiver, provider)
    - Enables class-level analysis and relationship tracking

    ### Android Context:
    - component_type: Android component type ("activity", "service", "receiver",
      "provider") or None for plain classes
    - is_main: Indicates if class is the application's main entry point
    """

    name: str = Field(..., description="Fully qualified class name", min_length=1)

    component_type: Optional[str] = Field(
        default=None,
        description="Android component type: 'activity', 'service', 'receiver', 'provider', or None",
    )

    is_main: bool = Field(
        default=False,
        description="Whether the class is the main component (application entry point)",
    )

    # Note: Using factory functions to avoid mutable defaults
    methods: Set[Method] = Field(
        default_factory=set, description="Set of methods defined in this class"
    )

    fields: Set[str] = Field(
        default_factory=set, description="Set of field names defined in this class"
    )

    def add_method(self, method: Method) -> bool:
        """
        Add a method to the class if not already present.

        Args:
            method: Method instance to add

        Returns:
            True if method was added, False if already exists
        """
        if method in self.methods:
            return False
        self.methods.add(method)
        return True

    def add_field(self, field: str) -> None:
        """
        Add a field name to the class's field collection.

        Args:
            field: Field name to add
        """
        self.fields.add(field)

    def get_monitored_operation_methods(self) -> List[Method]:
        """
        Get methods that are related to monitored operations.

        Returns:
            List of methods that reach or directly reach monitored operations
        """
        return [
            method for method in self.methods if method.is_monitored_operation_related()
        ]

    def get_reachable_methods(self) -> List[Method]:
        """
        Get methods that are marked as reachable.

        Returns:
            List of reachable methods in this class
        """
        return [method for method in self.methods if method.reachable]

    def to_json(self) -> Dict[str, any]:
        """
        Convert class to JSON-compatible dictionary format.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "name": self.name,
            "component_type": self.component_type,
            "is_main": self.is_main,
            "methods": [method.to_json() for method in self.methods],
            "fields": list(self.fields),
        }

    def get_analysis_summary(self) -> Dict[str, any]:
        """
        Get comprehensive analysis summary for this class.

        Returns:
            Dictionary with class analysis information
        """
        monitored_methods = self.get_monitored_operation_methods()
        reachable_methods = self.get_reachable_methods()

        return {
            "name": self.name,
            "type": {
                "component_type": self.component_type,
                "is_main": self.is_main,
            },
            "methods": {
                "total": len(self.methods),
                "reachable": len(reachable_methods),
                "monitored_operations_related": len(monitored_methods),
            },
            "fields": {"total": len(self.fields)},
        }

    def __str__(self) -> str:
        """
        Get detailed string representation.

        Returns:
            Comprehensive string representation for debugging
        """
        return (
            f"Clazz(name={self.name}, component_type={self.component_type}, "
            f"is_main={self.is_main}, methods={len(self.methods)}, "
            f"fields={len(self.fields)})"
        )

    def __repr__(self) -> str:
        """
        Get concise representation.

        Returns:
            Compact representation with essential information
        """
        return f"[{self.name},{self.component_type},{self.is_main}]"


class Classes(BaseValidatedModel):
    """
    Container and manager for all classes and methods in an application.

    ### Architectural Decisions:
    - Inherits from BaseValidatedModel for consistent validation behavior
    - Maintains separate indexes for classes and methods for efficient lookup
    - Integrates with logging infrastructure for debugging and analysis
    - Provides comprehensive analysis and reporting capabilities

    ### Role in the System:
    - Central repository for all class and method information
    - Provides efficient lookup and management of class relationships
    - Enables application-wide analysis of class and method structures
    - Supports serialization for persistence and inter-process communication

    ### Data Management:
    - classes: Dictionary mapping class names to Clazz instances
    - methods: Dictionary mapping method signatures to Method instances
    - Maintains consistency between class-method relationships
    """

    model_config = ConfigDict(
        # Allow extra attributes for logger
        extra="allow"
    )

    classes: Dict[str, Clazz] = Field(
        default_factory=dict,
        description="Dictionary mapping class names to Clazz instances",
    )

    methods: Dict[str, Method] = Field(
        default_factory=dict,
        description="Dictionary mapping method signatures to Method instances",
    )

    def __init__(self, **data):
        """Initialize with logging support."""
        super().__init__(**data)

        # Set up logging - use object.__setattr__ to bypass Pydantic validation
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rvandroid_core.domain.classes.Classes", {CONTEXT_COMPONENT: "Classes"}
        )
        object.__setattr__(self, "logger", logger)

    def get_classes(self) -> List[Clazz]:
        """
        Get list of all classes in the application.

        Returns:
            List of all Clazz instances
        """
        return list(self.classes.values())

    def add_clazz(self, name: str, component_type: str | None, is_main: bool) -> Clazz:
        """
        Add a new class or return existing one.

        Args:
            name: Fully qualified class name
            component_type: Android component type ("activity", "service",
                "receiver", "provider") or None for plain classes
            is_main: Whether class is the main component

        Returns:
            The Clazz instance (existing or newly created)
        """
        if name not in self.classes:
            self.logger.debug(f"Adding new class: {name}")
            self.classes[name] = Clazz(
                name=name, component_type=component_type, is_main=is_main
            )
        return self.classes[name]

    def get_clazz(self, name: str) -> Optional[Clazz]:
        """
        Retrieve a class by name.

        Args:
            name: Class name to look up

        Returns:
            Clazz instance or None if not found
        """
        return self.classes.get(name)

    def get_main_activity(self) -> Optional[Clazz]:
        """
        Find and return the main activity class.

        Returns:
            Main activity Clazz instance or None if not found
        """
        for clazz in self.classes.values():
            if clazz.is_main:
                return clazz
        return None

    def add_method(self, method: Method) -> bool:
        """
        Add a method to both class and global method collections.

        Args:
            method: Method instance to add

        Returns:
            True if method was added successfully, False otherwise
        """
        if method.signature not in self.methods:
            clazz = self.get_clazz(method.class_name)
            if clazz and clazz.add_method(method):
                self.methods[method.signature] = method
                self.logger.debug(f"Added method: {method.signature}")
                return True
        return False

    def get_method(self, signature: str) -> Optional[Method]:
        """
        Retrieve a method by its signature.

        Args:
            signature: Method signature to look up

        Returns:
            Method instance or None if not found
        """
        return self.methods.get(signature)

    def get_monitored_operation_methods(self) -> List[Method]:
        """
        Get all methods related to monitored operations.

        Returns:
            List of methods that reach or directly reach monitored operations
        """
        return [
            method
            for method in self.methods.values()
            if method.is_monitored_operation_related()
        ]

    def get_analysis_summary(self) -> Dict[str, any]:
        """
        Generate comprehensive analysis summary for all classes and methods.

        Returns:
            Dictionary with detailed analysis information
        """
        total_methods = len(self.methods)
        reachable_methods = sum(1 for m in self.methods.values() if m.reachable)
        monitored_methods = len(self.get_monitored_operation_methods())
        activities = sum(
            1 for c in self.classes.values() if c.component_type == "activity"
        )
        main_activity = self.get_main_activity()

        return {
            "classes": {
                "total": len(self.classes),
                "activities": activities,
                "main_activity": main_activity.name if main_activity else None,
            },
            "methods": {
                "total": total_methods,
                "reachable": reachable_methods,
                "monitored_operations_related": monitored_methods,
                "reachability_percentage": (
                    (reachable_methods / total_methods * 100)
                    if total_methods > 0
                    else 0
                ),
            },
        }

    def to_json(self) -> Dict[str, any]:
        """
        Convert all classes to JSON-compatible format.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {"classes": [clazz.to_json() for clazz in self.classes.values()]}
