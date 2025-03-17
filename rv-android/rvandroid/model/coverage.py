# rvandroid/model/coverage.py
"""
Unified model for method coverage tracking and analysis.
This module provides standardized data structures for tracking method coverage and coverage metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Any

from rvandroid.model.log import RvCoverageLog, RvErrorLog


@dataclass
class MethodCoverageData:
    """
    Standard data structure for method coverage information.
    Contains detailed data about a method, including its coverage status and properties.
    """
    class_name: str
    method_name: str
    signature: str
    parameters: List[str]
    reachable: bool = False
    reaches_mop: bool = False
    directly_reaches_mop: bool = False
    called: bool = False
    call_count: int = 0
    first_called_at: Optional[datetime] = None
    last_called_at: Optional[datetime] = None

    def register_call(self, timestamp: Optional[datetime] = None):
        """
        Register a call to this method.

        Args:
            timestamp: When the call occurred (defaults to now)
        """
        current_time = timestamp or datetime.now()
        self.called = True
        self.call_count += 1

        if not self.first_called_at:
            self.first_called_at = current_time

        self.last_called_at = current_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary representation."""
        return {
            "class_name": self.class_name,
            "method_name": self.method_name,
            "signature": self.signature,
            "parameters": self.parameters,
            "reachable": self.reachable,
            "reaches_mop": self.reaches_mop,
            "directly_reaches_mop": self.directly_reaches_mop,
            "called": self.called,
            "call_count": self.call_count,
            "first_called_at": self.first_called_at.isoformat() if self.first_called_at else None,
            "last_called_at": self.last_called_at.isoformat() if self.last_called_at else None
        }

    @classmethod
    def from_coverage_log(cls, coverage_log: RvCoverageLog) -> 'MethodCoverageData':
        """
        Create a MethodCoverageData instance from a RvCoverageLog.

        Args:
            coverage_log: Coverage log entry

        Returns:
            Method coverage data instance
        """
        return cls(
            class_name=coverage_log.clazz,
            method_name=coverage_log.method,
            signature=coverage_log.signature,
            parameters=coverage_log.params.split(";") if coverage_log.params else [],
            called=True,
            call_count=1,
            first_called_at=coverage_log.time_occurred,
            last_called_at=coverage_log.time_occurred
        )


@dataclass
class ClassCoverageData:
    """
    Standard data structure for class coverage information.
    Tracks methods within a class and provides class-level metrics.
    """
    name: str
    is_activity: bool = False
    is_main_activity: bool = False
    methods: Dict[str, MethodCoverageData] = field(default_factory=dict)

    @property
    def called(self) -> bool:
        """Check if any method in this class has been called."""
        return any(method.called for method in self.methods.values())

    @property
    def method_count(self) -> int:
        """Get the total number of methods in this class."""
        return len(self.methods)

    @property
    def called_method_count(self) -> int:
        """Get the number of methods that have been called."""
        return sum(1 for method in self.methods.values() if method.called)

    @property
    def reachable_method_count(self) -> int:
        """Get the number of reachable methods."""
        return sum(1 for method in self.methods.values() if method.reachable)

    @property
    def called_reachable_method_count(self) -> int:
        """Get the number of reachable methods that have been called."""
        return sum(1 for method in self.methods.values()
                   if method.reachable and method.called)

    @property
    def mop_reaching_method_count(self) -> int:
        """Get the number of methods that can reach MOP operations."""
        return sum(1 for method in self.methods.values() if method.reaches_mop)

    @property
    def called_mop_reaching_method_count(self) -> int:
        """Get the number of MOP-reaching methods that have been called."""
        return sum(1 for method in self.methods.values()
                   if method.reaches_mop and method.called)

    def add_method(self, method: MethodCoverageData) -> None:
        """
        Add a method to this class.

        Args:
            method: Method data to add
        """
        self.methods[method.signature] = method

    def register_method_call(self, signature: str, timestamp: Optional[datetime] = None) -> bool:
        """
        Register a call to a method in this class.

        Args:
            signature: Method signature
            timestamp: When the call occurred

        Returns:
            True if the method was found and updated, False otherwise
        """
        if signature in self.methods:
            self.methods[signature].register_call(timestamp)
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary representation."""
        return {
            "name": self.name,
            "is_activity": self.is_activity,
            "is_main_activity": self.is_main_activity,
            "method_count": self.method_count,
            "called_method_count": self.called_method_count,
            "reachable_method_count": self.reachable_method_count,
            "called_reachable_method_count": self.called_reachable_method_count,
            "mop_reaching_method_count": self.mop_reaching_method_count,
            "called_mop_reaching_method_count": self.called_mop_reaching_method_count,
            "methods": {signature: method.to_dict() for signature, method in self.methods.items()}
        }


@dataclass
class CoverageMetrics:
    """
    Standard container for coverage metrics.
    Provides a consistent structure for storing and reporting coverage metrics.
    """
    # Basic counts
    total_classes: int = 0
    total_activities: int = 0
    total_methods: int = 0
    total_reachable_methods: int = 0
    total_mop_methods: int = 0

    # Called counts
    called_classes: int = 0
    called_activities: int = 0
    called_methods: int = 0
    called_reachable_methods: int = 0
    called_mop_methods: int = 0

    # Error counts
    total_errors: int = 0
    unique_errors: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a dictionary with calculated percentages."""
        return {
            # Raw counts
            "total_classes": self.total_classes,
            "total_activities": self.total_activities,
            "total_methods": self.total_methods,
            "total_reachable_methods": self.total_reachable_methods,
            "total_mop_methods": self.total_mop_methods,

            "called_classes": self.called_classes,
            "called_activities": self.called_activities,
            "called_methods": self.called_methods,
            "called_reachable_methods": self.called_reachable_methods,
            "called_mop_methods": self.called_mop_methods,

            "total_errors": self.total_errors,
            "unique_errors": self.unique_errors,

            # Percentages
            "class_coverage": self._percentage(self.called_classes, self.total_classes),
            "activity_coverage": self._percentage(self.called_activities, self.total_activities),
            "method_coverage": self._percentage(self.called_methods, self.total_methods),
            "reachable_method_coverage": self._percentage(
                self.called_reachable_methods, self.total_reachable_methods),
            "mop_method_coverage": self._percentage(
                self.called_mop_methods, self.total_mop_methods)
        }

    @staticmethod
    def _percentage(part: int, total: int) -> float:
        """Calculate percentage safely."""
        return (part / total * 100) if total > 0 else 0.0


class CoverageRepository:
    """
    Central repository for coverage data.
    Provides a unified API for storing and retrieving coverage information.
    """

    def __init__(self):
        """Initialize the coverage repository."""
        self.classes: Dict[str, ClassCoverageData] = {}
        self.errors: List[RvErrorLog] = []
        self.unique_errors: Set[str] = set()

    def add_class(self, class_data: ClassCoverageData) -> None:
        """
        Add a class to the repository.

        Args:
            class_data: Class coverage data
        """
        self.classes[class_data.name] = class_data

    def get_class(self, class_name: str) -> Optional[ClassCoverageData]:
        """
        Get a class by name.

        Args:
            class_name: Class name

        Returns:
            Class coverage data or None if not found
        """
        return self.classes.get(class_name)

    def register_method_call(self, coverage_log: RvCoverageLog) -> None:
        """
        Register a method call from a coverage log entry.

        Args:
            coverage_log: Coverage log entry
        """
        class_name = coverage_log.clazz
        signature = coverage_log.signature

        # Get or create the class
        class_data = self.get_class(class_name)
        if not class_data:
            class_data = ClassCoverageData(name=class_name)
            self.add_class(class_data)

        # Register the method call
        if signature in class_data.methods:
            class_data.register_method_call(signature, coverage_log.time_occurred)
        else:
            # Create and add the method
            method_data = MethodCoverageData.from_coverage_log(coverage_log)
            class_data.add_method(method_data)

    def register_error(self, error_log: RvErrorLog) -> None:
        """
        Register an error log entry.

        Args:
            error_log: Error log entry
        """
        self.errors.append(error_log)
        self.unique_errors.add(error_log.unique_msg)

    def calculate_metrics(self) -> CoverageMetrics:
        """
        Calculate coverage metrics from the repository data.

        Returns:
            Coverage metrics
        """
        metrics = CoverageMetrics()

        # Count totals
        metrics.total_classes = len(self.classes)
        metrics.total_errors = len(self.errors)
        metrics.unique_errors = len(self.unique_errors)

        # Calculate class and method counts
        for class_data in self.classes.values():
            if class_data.is_activity:
                metrics.total_activities += 1
                if class_data.called:
                    metrics.called_activities += 1

            if class_data.called:
                metrics.called_classes += 1

            # Add method counts
            metrics.total_methods += class_data.method_count
            metrics.called_methods += class_data.called_method_count
            metrics.total_reachable_methods += class_data.reachable_method_count
            metrics.called_reachable_methods += class_data.called_reachable_method_count
            metrics.total_mop_methods += class_data.mop_reaching_method_count
            metrics.called_mop_methods += class_data.called_mop_reaching_method_count

        return metrics

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary representation."""
        return {
            "metrics": self.calculate_metrics().to_dict(),
            "classes": {name: cls.to_dict() for name, cls in self.classes.items()},
            "errors": {
                "count": len(self.errors),
                "unique_count": len(self.unique_errors)
            }
        }


def process_coverage_data(
        called_methods: Dict[str, Dict[str, Dict[str, RvCoverageLog]]],
        all_methods: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Process coverage data using the new unified model.
    This is a compatibility function to ease transition to the new model.

    Args:
        called_methods: Old format dictionary of called methods
        all_methods: Old format dictionary of all methods

    Returns:
        Dictionary with coverage results in the old format for compatibility
    """
    # Create a repository
    repository = CoverageRepository()

    # First add all methods from static analysis
    for class_name, class_info in all_methods.items():
        class_data = ClassCoverageData(
            name=class_name,
            is_activity=class_info.get("is_activity", False)
        )

        for signature, method_info in class_info.get("methods", {}).items():
            method_data = MethodCoverageData(
                class_name=class_name,
                method_name=signature.split("(")[0] if "(" in signature else signature,
                signature=signature,
                parameters=[],  # We don't have this info in the old format
                reachable=method_info.get("reachable", False),
                reaches_mop=method_info.get("reaches_mop", False),
                directly_reaches_mop=method_info.get("directly_reaches_mop", False),
                called=method_info.get("called", False)
            )
            class_data.add_method(method_data)

        repository.add_class(class_data)

    # Now add called methods
    for class_name, class_info in called_methods.items():
        class_data = repository.get_class(class_name)
        if not class_data:
            class_data = ClassCoverageData(name=class_name)
            repository.add_class(class_data)

        for signature, method_log in class_info.get("methods", {}).items():
            if isinstance(method_log, RvCoverageLog):
                if signature in class_data.methods:
                    class_data.register_method_call(signature, method_log.time_occurred)
                else:
                    method_data = MethodCoverageData.from_coverage_log(method_log)
                    class_data.add_method(method_data)

    # Calculate metrics
    metrics = repository.calculate_metrics()

    # Convert to old format for compatibility
    result = all_methods.copy()
    result["SUMMARY"] = metrics.to_dict()

    # Mark called methods
    for class_name, class_info in called_methods.items():
        if class_name in result:
            for signature in class_info.get("methods", {}):
                if signature in result[class_name]["methods"]:
                    result[class_name]["methods"][signature]["called"] = True

    return result
