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
        self.repository = CoverageRepository()
        self.class_methods = {}
        self.errors = []

    def process_logcat_file(self, logcat_file: str) -> Dict:
        """
        Process a logcat file to extract coverage and error information.

        Args:
            logcat_file: Path to the logcat file

        Returns:
            Dictionary with coverage results
        """
        from rvandroid.parser.log.logcat_parser import parse_logcat_file

        errors, called_methods, _ = parse_logcat_file(logcat_file)
        self.errors = errors
        self.class_methods = called_methods

        # Calculate coverage
        return self.calculate_coverage()

    def add_method_call(self, coverage_log: RvCoverageLog) -> None:
        """
        Add a method call to the analyzer's data.

        Args:
            coverage_log: Coverage log entry to add
        """
        # Add to repository
        self.repository.register_method_call(coverage_log)

        # Add to class_methods for backward compatibility
        if coverage_log.clazz not in self.class_methods:
            self.class_methods[coverage_log.clazz] = []

        self.class_methods[coverage_log.clazz].append(coverage_log)

    def add_error(self, error_log: RvErrorLog) -> None:
        """
        Add an error to the analyzer's data.

        Args:
            error_log: Error log entry to add
        """
        self.repository.register_error(error_log)
        self.errors.append(error_log)

    def calculate_coverage(self) -> Dict:
        """
        Calculate coverage metrics based on collected data.

        Returns:
            Dictionary with coverage results
        """
        if not self.static_data or not hasattr(self.static_data, "classes"):
            self.logger.warning("No static data available for coverage calculation")
            return {"SUMMARY": {}}

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

        # Process coverage
        return process_coverage(formatted_methods, all_methods)

    def get_metrics(self) -> Dict:
        """
        Get coverage metrics from repository.

        Returns:
            Dictionary with metrics
        """
        metrics = self.repository.calculate_metrics().to_dict()

        # For backward compatibility
        # TODO rever uso a linha abaixo para poder remover
        summary = self.calculate_coverage().get("SUMMARY", {})

        return {
            "method_coverage": metrics["method_coverage"],
            "activities_coverage": metrics["activity_coverage"],
            "methods_jca_reachable_coverage": metrics["mop_method_coverage"],
            "total_errors": len(self.errors),
            "total_method_calls": sum(len(methods) for methods in self.class_methods.values())
        }
