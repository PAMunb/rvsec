"""
Coverage tracker for calculating method coverage metrics.

Processes coverage entries from logcat against static analysis data from .methods files.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from rv_agent_validation.coverage.logcat_parser import CoverageEntry, ErrorEntry
from rv_agent_validation.coverage.methods_parser import MethodsParser


@dataclass
class CoverageResult:
    """Coverage calculation results."""

    # Percentages (0-100)
    activity_coverage: float = 0.0
    class_coverage: float = 0.0
    method_coverage: float = 0.0
    reachable_coverage: float = 0.0
    reaches_mop_coverage: float = 0.0
    directly_reaches_mop_coverage: float = 0.0

    # Counts
    called_activities: int = 0
    total_activities: int = 0
    called_classes: int = 0
    total_classes: int = 0
    called_methods: int = 0
    total_methods: int = 0
    called_reachable: int = 0
    total_reachable: int = 0
    called_reaches_mop: int = 0
    total_reaches_mop: int = 0
    called_directly_reaches_mop: int = 0
    total_directly_reaches_mop: int = 0

    # Errors
    unique_errors: int = 0
    total_errors: int = 0
    error_specs: List[str] = field(default_factory=list)

    # Diagnostics
    mismatched_signatures: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "activity_coverage": self.activity_coverage,
            "class_coverage": self.class_coverage,
            "method_coverage": self.method_coverage,
            "reachable_coverage": self.reachable_coverage,
            "reaches_mop_coverage": self.reaches_mop_coverage,
            "directly_reaches_mop_coverage": self.directly_reaches_mop_coverage,
            "called_activities": self.called_activities,
            "total_activities": self.total_activities,
            "called_classes": self.called_classes,
            "total_classes": self.total_classes,
            "called_methods": self.called_methods,
            "total_methods": self.total_methods,
            "called_reachable": self.called_reachable,
            "total_reachable": self.total_reachable,
            "called_reaches_mop": self.called_reaches_mop,
            "total_reaches_mop": self.total_reaches_mop,
            "called_directly_reaches_mop": self.called_directly_reaches_mop,
            "total_directly_reaches_mop": self.total_directly_reaches_mop,
            "unique_errors": self.unique_errors,
            "total_errors": self.total_errors,
            "error_specs": self.error_specs,
            "mismatched_signatures": self.mismatched_signatures,
        }


class CoverageTracker:
    """
    Tracks method coverage by matching logcat entries against static analysis data.

    Calculates coverage percentages for:
    - Activities visited
    - Classes touched
    - Methods called
    - Reachable methods called
    - Methods that reach MOP (transitive)
    - Methods that directly reach MOP
    """

    def __init__(self, methods_parser: MethodsParser):
        """
        Initialize tracker with static analysis data.

        Args:
            methods_parser: Parser with .methods file data
        """
        self.methods = methods_parser

        # Tracking sets
        self._called_activities: Set[str] = set()
        self._called_classes: Set[str] = set()
        self._called_methods: Set[str] = set()
        self._called_reachable: Set[str] = set()
        self._called_reaches_mop: Set[str] = set()
        self._called_directly_reaches_mop: Set[str] = set()

        # Mismatch tracking
        self._mismatched: Set[str] = set()

        # Error tracking
        self._unique_errors: Set[str] = set()
        self._error_specs: Set[str] = set()
        self._total_errors: int = 0

    def process_coverage(self, entries: List[CoverageEntry]) -> None:
        """
        Process coverage entries from logcat.

        Args:
            entries: List of coverage entries from LogcatCoverageParser
        """
        for entry in entries:
            self._process_entry(entry)

    def process_errors(self, errors: List[ErrorEntry]) -> None:
        """
        Process error entries from logcat.

        Args:
            errors: List of error entries from LogcatCoverageParser
        """
        for error in errors:
            self._total_errors += 1
            if error.unique_key not in self._unique_errors:
                self._unique_errors.add(error.unique_key)
                self._error_specs.add(error.spec)

    def _process_entry(self, entry: CoverageEntry) -> bool:
        """
        Process a single coverage entry.

        Returns:
            True if signature was found in static data, False otherwise
        """
        signature = entry.signature

        if signature in self._called_methods:
            return True  # Already processed

        if not self.methods.has_signature(signature):
            self._mismatched.add(signature)
            return False

        method = self.methods.get_method(signature)
        if not method:
            return False

        # Update tracking sets
        self._called_methods.add(signature)
        self._called_classes.add(method.class_name)

        if method.is_activity:
            self._called_activities.add(method.class_name)

        if method.reachable:
            self._called_reachable.add(signature)

        if method.reaches_mop:
            self._called_reaches_mop.add(signature)

        if method.directly_reaches_mop:
            self._called_directly_reaches_mop.add(signature)

        return True

    def get_result(self) -> CoverageResult:
        """
        Calculate and return coverage results.

        Returns:
            CoverageResult with all metrics
        """
        result = CoverageResult()

        # Totals from static analysis
        result.total_activities = len(self.methods.activities)
        result.total_classes = len(self.methods.classes)
        result.total_methods = self.methods.total_methods
        result.total_reachable = self.methods.reachable_count
        result.total_reaches_mop = self.methods.reaches_mop_count
        result.total_directly_reaches_mop = self.methods.directly_reaches_mop_count

        # Called counts
        result.called_activities = len(self._called_activities)
        result.called_classes = len(self._called_classes)
        result.called_methods = len(self._called_methods)
        result.called_reachable = len(self._called_reachable)
        result.called_reaches_mop = len(self._called_reaches_mop)
        result.called_directly_reaches_mop = len(self._called_directly_reaches_mop)

        # Calculate percentages
        result.activity_coverage = self._percentage(
            result.called_activities, result.total_activities
        )
        result.class_coverage = self._percentage(
            result.called_classes, result.total_classes
        )
        result.method_coverage = self._percentage(
            result.called_methods, result.total_methods
        )
        result.reachable_coverage = self._percentage(
            result.called_reachable, result.total_reachable
        )
        result.reaches_mop_coverage = self._percentage(
            result.called_reaches_mop, result.total_reaches_mop
        )
        result.directly_reaches_mop_coverage = self._percentage(
            result.called_directly_reaches_mop, result.total_directly_reaches_mop
        )

        # Errors
        result.unique_errors = len(self._unique_errors)
        result.total_errors = self._total_errors
        result.error_specs = sorted(self._error_specs)

        # Diagnostics
        result.mismatched_signatures = len(self._mismatched)

        return result

    def _percentage(self, part: int, total: int) -> float:
        """Calculate percentage, returning 0 if total is 0."""
        if total == 0:
            return 0.0
        return (part / total) * 100.0

    @property
    def mismatched_signatures(self) -> Set[str]:
        """Get signatures that were not found in static data."""
        return self._mismatched.copy()


def calculate_coverage(
    methods_file: Path,
    coverage_entries: List[CoverageEntry],
    error_entries: Optional[List[ErrorEntry]] = None,
) -> CoverageResult:
    """
    Convenience function to calculate coverage.

    Args:
        methods_file: Path to .methods file
        coverage_entries: Coverage entries from logcat parser
        error_entries: Error entries from logcat parser (optional)

    Returns:
        CoverageResult with all metrics
    """
    methods_parser = MethodsParser(methods_file)
    tracker = CoverageTracker(methods_parser)

    tracker.process_coverage(coverage_entries)

    if error_entries:
        tracker.process_errors(error_entries)

    return tracker.get_result()
