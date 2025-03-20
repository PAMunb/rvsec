# rvandroid/analysis/analyzer.py - Complete rewrite to use repository
"""
Unified analyzer module for processing coverage data.
Acts as a facade for different analysis functionalities.
"""

import logging
from typing import Dict

from rvandroid.model.coverage import LogcatRepository
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
        self.repository = LogcatRepository()

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

        # Parse logcat file
        errors, _, sorted_methods = parse_logcat_file(logcat_file)

        # Register all errors and method calls in the repository
        for error in errors:
            self.repository.register_error(error)

        for method in sorted_methods:
            self.repository.register_method_call(method)

        # Calculate and return coverage
        return self.get_coverage_metrics()

    def add_method_call(self, coverage_log: RvCoverageLog) -> None:
        """
        Add a method call to the analyzer's data using standardized model.

        Args:
            coverage_log: Coverage log entry to add
        """
        self.repository.register_method_call(coverage_log)

    def add_error(self, error_log: RvErrorLog) -> None:
        """
        Add an error to the analyzer's data using standardized model.

        Args:
            error_log: Error log entry to add
        """
        self.repository.register_error(error_log)

    def get_coverage_metrics(self) -> Dict:
        """
        Get coverage metrics from repository.

        Returns:
            Dictionary with metrics
        """
        metrics = self.repository.calculate_metrics().to_dict()

        return {
            "SUMMARY": metrics,
            "method_coverage": metrics["method_coverage"],
            "activities_coverage": metrics["activity_coverage"],
            "methods_jca_reachable_coverage": metrics["mop_method_coverage"],
            "total_errors": metrics["unique_errors"],
            "total_method_calls": metrics["called_methods"]
        }
