# rvandroid/model/coverage.py
"""
Unified model for method coverage tracking and analysis.
This module provides standardized data structures for tracking method coverage and coverage metrics.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Any

from rvandroid.domain.log import RvCoverageLog, RvErrorLog


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
    from_static_analysis: bool = False  # New field to track source
    time_since_task_start: int = 0  # Time in seconds when first called (from RvCoverageLog)

    def register_call(self, timestamp: Optional[datetime] = None, time_since_task_start: Optional[int] = None) -> None:
        """
        Register a call to this method.
        
        ### Critical Architecture Decision:
        This method preserves timing data from RvCoverageLog objects to maintain
        accurate timing information throughout the data flow. The time_since_task_start
        is essential for generating correct CSV reports with actual execution times.

        Args:
            timestamp: When the call occurred (defaults to now)
            time_since_task_start: Seconds since task execution started (from RvCoverageLog)
        """
        current_time = timestamp or datetime.now()
        self.called = True
        self.call_count += 1

        if not self.first_called_at:
            self.first_called_at = current_time
            # Store the time_since_task_start from the FIRST call for CSV export
            if time_since_task_start is not None:
                self.time_since_task_start = time_since_task_start

        self.last_called_at = current_time

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary representation.

        Returns:
            Dictionary with method coverage details
        """
        result = {
            "class_name": self.class_name,
            "method_name": self.method_name,
            "signature": self.signature,
            "parameters": self.parameters,
            "reachable": self.reachable,
            "reaches_mop": self.reaches_mop,
            "directly_reaches_mop": self.directly_reaches_mop,
            "called": self.called,
            "call_count": self.call_count,
            "from_static_analysis": self.from_static_analysis
        }

        # Convert datetime objects to ISO format strings if present
        if self.first_called_at:
            result["first_called_at"] = self.first_called_at.isoformat()
        else:
            result["first_called_at"] = None

        if self.last_called_at:
            result["last_called_at"] = self.last_called_at.isoformat()
        else:
            result["last_called_at"] = None

        return result

    @classmethod
    def from_coverage_log(cls, log: RvCoverageLog) -> 'MethodCoverageData':
        """
        Create a method coverage data instance from a coverage log entry.

        Args:
            log: Coverage log entry

        Returns:
            New MethodCoverageData instance initialized from the log
        """
        parameters = log.get_parameters_list()

        instance = cls(
            class_name=log.clazz,
            method_name=log.method,
            signature=log.signature,
            parameters=parameters,
            # Default values for other fields
            reachable=False,
            reaches_mop=False,
            directly_reaches_mop=False
        )

        # Register the call with the timestamp from the log
        instance.register_call(log.time_occurred)
        
        # Store the time since task start from the original log
        instance.time_since_task_start = log.time_since_task_start

        return instance


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

    def register_method_call(self, signature: str, timestamp: Optional[datetime] = None, time_since_task_start: Optional[int] = None) -> bool:
        """
        Register a call to a method in this class.
        
        ### Critical Architecture Decision:
        This method propagates timing data from RvCoverageLog through the coverage
        data structure to ensure accurate timing information in reports.

        Args:
            signature: Method signature
            timestamp: When the call occurred (optional)
            time_since_task_start: Seconds since task execution started (from RvCoverageLog)

        Returns:
            True if the method was found and updated, False otherwise
        """
        if signature in self.methods:
            self.methods[signature].register_call(timestamp, time_since_task_start)
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary representation.

        Returns:
            Dictionary with class coverage details
        """
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
            "methods": [method.to_dict() for method in self.methods.values()]
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


class LogcatRepository:
    """
    Central repository for coverage data.
    Provides a unified API for storing and retrieving coverage information.
    """

    def __init__(self):
        """Initialize the coverage repository."""
        self.logger = logging.getLogger(__name__)
        self.classes: Dict[str, ClassCoverageData] = {}
        self.errors: List[RvErrorLog] = []
        self.unique_errors: Set[str] = set()

        # Cache for static analysis totals - calculated once
        self._static_totals: Optional[Dict[str, int]] = None

    def add_class(self, class_data: ClassCoverageData) -> None:
        """
        Add a class to the repository.

        Args:
            class_data: Class coverage data
        """
        # We should only add a class once to maintain static analysis integrity
        if class_data.name not in self.classes:
            self.classes[class_data.name] = class_data

            # Mark methods from static analysis
            for signature, method in class_data.methods.items():
                method.from_static_analysis = True

            # Reset static totals cache when adding a class
            self._static_totals = None

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
        Only registers calls to methods that exist in static analysis data.
        
        ### Critical Architecture Decision:
        This method is the primary entry point for preserving timing data from
        RvCoverageLog objects into the coverage data structure. It ensures that
        the time_since_task_start calculated by CoverageTracker is preserved
        throughout the data flow to generate accurate CSV reports.

        Args:
            coverage_log: Coverage log entry with timing information
        """
        class_name = coverage_log.clazz
        signature = coverage_log.signature

        # Get the class if it exists
        class_data = self.get_class(class_name)
        if not class_data:
            self.logger.debug(f"Ignoring method call for unknown class: {class_name}")
            return

        # Only register calls to methods that exist in static analysis data
        # CRITICAL: Pass both timestamp AND time_since_task_start from RvCoverageLog
        if signature in class_data.methods:
            class_data.register_method_call(
                signature, 
                coverage_log.time_occurred, 
                coverage_log.time_since_task_start
            )
        else:
            self.logger.debug(f"Ignoring method call not found in static analysis: {signature}")

    def register_rv_error(self, error_log: RvErrorLog) -> None:
        """
        Register a formal property violation detected during runtime verification.

        IMPORTANT: This method is ONLY for registering formal property violations
        detected by runtime verification monitors, not for general system errors
        or exceptions.

        Args:
            error_log: Runtime verification error log entry
        """
        self.errors.append(error_log)
        self.unique_errors.add(error_log.unique_msg)

    def get_static_method_count(self) -> int:
        """Get the count of methods from static analysis."""
        if self._static_totals is None:
            self._calculate_static_totals()
        return self._static_totals.get("total_methods", 0) if self._static_totals else 0

    def calculate_metrics(self, restrict_to_static: bool = True) -> CoverageMetrics:
        """
        Calculate coverage metrics from the repository data.
        Returns 0% for all metrics if no static analysis data is available.

        Args:
            restrict_to_static: If True, only include methods found in static analysis

        Returns:
            Coverage metrics
        """
        metrics = CoverageMetrics()

        # Check if static analysis data is available
        if not self.classes:
            self.logger.warning("No static analysis data available, returning 0% for all metrics")
            return metrics

        # Calculate static analysis totals (only once)
        if self._static_totals is None:
            self._calculate_static_totals()

        # Use static totals for total counts
        if self._static_totals:
            metrics.total_classes = self._static_totals.get("total_classes", 0)
            metrics.total_activities = self._static_totals.get("total_activities", 0)
            metrics.total_methods = self._static_totals.get("total_methods", 0)
            metrics.total_reachable_methods = self._static_totals.get("total_reachable_methods", 0)
            metrics.total_mop_methods = self._static_totals.get("total_mop_methods", 0)
        else:
            self.logger.warning("Static totals not available, metrics may be inaccurate")

        # Count errors
        metrics.total_errors = len(self.errors)
        metrics.unique_errors = len(self.unique_errors)

        # Calculate called metrics
        for class_data in self.classes.values():
            if class_data.called:
                metrics.called_classes += 1
                if class_data.is_activity:
                    metrics.called_activities += 1

            # Count called methods
            for method in class_data.methods.values():
                # Only count methods from static analysis, which is now enforced
                if method.called:
                    metrics.called_methods += 1
                    if method.reachable:
                        metrics.called_reachable_methods += 1
                    if method.reaches_mop:
                        metrics.called_mop_methods += 1

        return metrics

    def _calculate_static_totals(self) -> None:
        """Calculate and cache totals from static analysis data."""
        totals = {
            "total_classes": 0,
            "total_activities": 0,
            "total_methods": 0,
            "total_reachable_methods": 0,
            "total_mop_methods": 0
        }

        # Count all classes and methods from static analysis
        for class_name, class_data in self.classes.items():
            totals["total_classes"] += 1

            if class_data.is_activity:
                totals["total_activities"] += 1

            # Count methods
            for signature, method in class_data.methods.items():
                totals["total_methods"] += 1

                if method.reachable:
                    totals["total_reachable_methods"] += 1

                if method.reaches_mop:
                    totals["total_mop_methods"] += 1

        # Cache the results
        self._static_totals = totals
        self.logger.debug(f"Calculated static analysis totals: {totals}")

    def diagnose(self) -> Dict[str, Any]:
        """
        Generate a diagnostic report about the current state of the repository.

        Returns:
            Dictionary with diagnostic information
        """
        # Collect diagnostic information
        diagnostics = {
            "class_count": len(self.classes),
            "activity_count": sum(1 for c in self.classes.values() if c.is_activity),
            "method_count": sum(len(c.methods) for c in self.classes.values()),
            "called_method_count": sum(sum(1 for m in c.methods.values() if m.called) for c in self.classes.values()),
            "error_count": len(self.errors),
            "unique_error_count": len(self.unique_errors),
            "static_totals": self._static_totals
        }

        # Check for common issues
        issues = []

        if diagnostics["method_count"] == 0:
            issues.append("No methods found in repository")

        if self._static_totals is None:
            issues.append("Static totals not calculated")
        elif self._static_totals.get("total_methods", 0) == 0:
            issues.append("Static totals shows zero methods")

        diagnostics["issues"] = issues
        return diagnostics

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert repository to dictionary format for serialization.

        Returns:
            Dictionary representation of the repository
        """
        metrics = self.calculate_metrics()

        return {
            "metrics": metrics.to_dict(),
            "classes": {name: class_data.to_dict() for name, class_data in self.classes.items()},
            "errors": {
                "count": len(self.errors),
                "unique_count": len(self.unique_errors),
                "items": [error.to_dict() for error in self.errors]
            }
        }

    def get_method_calls(self) -> List[Dict[str, Any]]:
        """
        Get all method calls as a list of dictionaries for export/reporting.
        
        ### Critical Architecture Decision:
        This method provides the final data structure used by ResultManager to generate
        CSV reports. It returns ONE entry per method (based on first call time) to avoid
        duplicates in coverage.csv. The time_since_task_start from RvCoverageLog objects
        is correctly propagated to maintain accurate timing data throughout the complete
        data flow: RvCoverageLog -> MethodCoverageData -> CSV.
        
        Returns:
            List of unique method call dictionaries sorted by first call time
        """
        method_calls = []
        
        for class_name, class_data in self.classes.items():
            for signature, method_data in class_data.methods.items():
                if method_data.called:
                    # CRITICAL: Use time_since_task_start preserved from RvCoverageLog
                    # Each method appears only ONCE based on its first call time
                    call_data = {
                        'time': method_data.time_since_task_start,  # Time of FIRST call from RvCoverageLog
                        'class_name': class_name,
                        'method_name': method_data.method_name,
                        'signature': signature,
                        'is_mop_method': method_data.reaches_mop,
                        'activity': class_name if class_data.is_activity else None,
                        'call_count': method_data.call_count,
                        'first_called_at': method_data.first_called_at.isoformat() if method_data.first_called_at else None,
                        'last_called_at': method_data.last_called_at.isoformat() if method_data.last_called_at else None
                    }
                    method_calls.append(call_data)
        
        # Sort method calls by time_since_task_start to maintain chronological order
        # This ensures progressive coverage calculation works correctly in CSV
        return sorted(method_calls, key=lambda x: x['time'])

    def get_errors(self) -> List[Dict[str, Any]]:
        """
        Get all monitored operations errors as a list of dictionaries for export/reporting.
        
        ### Critical Architecture Decision:
        This method returns errors sorted by time_since_task_start to maintain chronological
        order in the errors.csv output, enabling proper temporal analysis of security violations.
        
        Returns:
            List of error dictionaries sorted by occurrence time
        """
        error_dicts = [error.to_dict() for error in self.errors]
        # Sort by time_since_task_start to maintain chronological order in errors.csv
        return sorted(error_dicts, key=lambda x: x.get('time_since_task_start', 0))

    def get_static_methods(self) -> List[str]:
        """
        Get all method signatures from static analysis.
        
        Returns:
            List of method signatures
        """
        signatures = []
        for class_data in self.classes.values():
            signatures.extend(class_data.methods.keys())
        return signatures

    def get_static_activities(self) -> List[str]:
        """
        Get all activity class names from static analysis.
        
        Returns:
            List of activity class names
        """
        return [name for name, class_data in self.classes.items() if class_data.is_activity]

    def get_mop_methods(self) -> List[str]:
        """
        Get all MOP-reachable method signatures from static analysis.
        
        Returns:
            List of MOP-reachable method signatures
        """
        mop_signatures = []
        for class_data in self.classes.values():
            for signature, method_data in class_data.methods.items():
                if method_data.reaches_mop:
                    mop_signatures.append(signature)
        return mop_signatures
