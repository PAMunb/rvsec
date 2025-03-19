# rvandroid/analysis/analyzer.py
"""
Unified analyzer module for processing coverage data.
Acts as a facade for different analysis functionalities.
"""

import logging
from typing import Dict

from rvandroid.analysis.coverage import process_coverage
from rvandroid.model.coverage import CoverageRepository
from rvandroid.model.log import RvCoverageLog, RvErrorLog


class CoverageAnalyzer:
    """
    Centralized analyzer for processing coverage data from various sources.

    This class provides a unified interface for coverage analysis, separating
    the analysis logic from data collection to improve modularity and testability.

    ### Architectural Decisions:
    - Acts as a facade for different analysis approaches
    - Separates analysis logic from data collection
    - Provides both streaming and batch processing capabilities

    ### Role in the System:
    - Processes coverage data captured during experiment execution
    - Calculates coverage metrics based on static analysis data
    - Tracks and aggregates errors discovered during execution
    """

    def __init__(self, static_data=None):
        """
        Initialize the analyzer with optional static data.

        Args:
            static_data: Optional static analysis data for the app
        """
        self.logger = logging.getLogger(__name__)
        self.static_data = static_data

        # Primary model: standardized repository
        self.repository = CoverageRepository()

        # Legacy structures for backward compatibility
        self.class_methods = {}
        self.errors = []

    def process_logcat_file(self, logcat_file: str) -> Dict:
        """
        Process a logcat file to extract coverage and error information.
        Uses standardized parsing and data models.

        Args:
            logcat_file: Path to the logcat file

        Returns:
            Dictionary with coverage results
        """
        from rvandroid.parser.log.logcat_parser import parse_logcat_file

        # Parse logcat file using standardized parser
        errors, called_methods, sorted_methods = parse_logcat_file(logcat_file)

        # Store parsed data in both repository and legacy structures
        self.errors = errors
        self.class_methods = {
            class_name: [
                method for method in methods.values()
            ] for class_name, methods in {
                class_name: class_data["methods"]
                for class_name, class_data in called_methods.items()
            }.items()
        }

        # Register all errors and method calls in the repository
        for error in errors:
            self.repository.register_error(error)

        for method in sorted_methods:
            self.repository.register_method_call(method)

        # Calculate coverage using the repository
        return self.calculate_coverage()

    def add_method_call(self, coverage_log: RvCoverageLog) -> None:
        """
        Add a method call to the analyzer's data using standardized model.

        Args:
            coverage_log: Coverage log entry to add
        """
        # First update repository (primary model)
        self.repository.register_method_call(coverage_log)

        # Then update legacy structures for backward compatibility
        if coverage_log.clazz not in self.class_methods:
            self.class_methods[coverage_log.clazz] = []

        self.class_methods[coverage_log.clazz].append(coverage_log)

    def add_error(self, error_log: RvErrorLog) -> None:
        """
        Add an error to the analyzer's data using standardized model.

        Args:
            error_log: Error log entry to add
        """
        # First update repository (primary model)
        self.repository.register_error(error_log)

        # Then update legacy structures for backward compatibility
        self.errors.append(error_log)

    def calculate_coverage(self) -> Dict:
        """
        Calculate coverage metrics based on collected data.
        Prefers repository-based metrics when available.

        Returns:
            Dictionary with coverage results
        """
        # First get metrics from repository
        repository_metrics = self.repository.calculate_metrics().to_dict()

        # For backward compatibility, also calculate using legacy approach
        if self.static_data and hasattr(self.static_data, "classes"):
            legacy_coverage = self._calculate_legacy_coverage()

            # Merge metrics, preferring repository metrics where available
            result = legacy_coverage

            # Update summary with repository metrics
            if "SUMMARY" in result:
                result["SUMMARY"].update({
                    "method_coverage": repository_metrics["method_coverage"],
                    "activity_coverage": repository_metrics["activity_coverage"],
                    "mop_method_coverage": repository_metrics["mop_method_coverage"]
                })

            return result
        else:
            # If static data not available, just return repository metrics
            return {"SUMMARY": repository_metrics}

    def _calculate_legacy_coverage(self) -> Dict:
        """
        Calculate coverage using legacy approach for backward compatibility.

        Returns:
            Dictionary with coverage results in legacy format
        """
        # Convert class_methods to compatible format
        formatted_methods = {}
        for class_name, methods in self.class_methods.items():
            formatted_methods[class_name] = {"methods": {}}
            for method in methods:
                formatted_methods[class_name]["methods"][method.signature] = method

        # Create all_methods from static data
        all_methods = {}
        for class_name, class_info in self.static_data.classes.classes.items():
            all_methods[class_name] = {
                "is_activity": class_info.is_activity,
                "methods": {}
            }

            for method in class_info.methods:
                all_methods[class_name]["methods"][method.signature] = {
                    "reachable": method.reachable,
                    "reaches_mop": method.reaches_mop,
                    "directly_reaches_mop": method.directly_reaches_mop,
                    "called": False
                }

        # Process coverage using legacy function
        return process_coverage(formatted_methods, all_methods)

    def get_metrics(self) -> Dict:
        """
        Get coverage metrics, preferring repository-based metrics.

        Returns:
            Dictionary with metrics
        """
        # Get metrics from repository (primary model)
        metrics = self.repository.calculate_metrics().to_dict()

        # For backward compatibility
        summary = self.calculate_coverage().get("SUMMARY", {})

        return {
            "method_coverage": metrics["method_coverage"],
            "activities_coverage": metrics["activity_coverage"],
            "methods_jca_reachable_coverage": metrics["mop_method_coverage"],
            "total_errors": len(self.errors),
            "total_method_calls": sum(len(methods) for methods in self.class_methods.values())
        }
