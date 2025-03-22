# rvandroid/analysis/analyzer.py
"""
Unified analyzer module for processing coverage data.
Acts as a facade for different analysis functionalities.
"""

import logging
from typing import Dict

from rvandroid.domain.coverage import LogcatRepository
from rvandroid.domain.log import RvCoverageLog, RvErrorLog


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

        # Initialize repository from static_data if available
        if static_data and static_data.classes:
            self._initialize_from_static_data()
        else:
            self.logger.warning("No static analysis data provided. Coverage metrics will be set to 0%.")

    def _initialize_from_static_data(self):
        """Initialize repository from static analysis data."""
        try:
            self.logger.info("Initializing analyzer from static analysis data")

            # Initialize classes and methods from static data
            classes = self.static_data.classes

            for class_name, class_info in classes.classes.items():
                # Create class data in repository
                from rvandroid.domain.coverage import ClassCoverageData
                class_data = ClassCoverageData(
                    name=class_name,
                    is_activity=class_info.is_activity,
                    is_main_activity=getattr(class_info, "is_main_activity", False)
                )
                self.repository.add_class(class_data)

                # Add methods to class
                for method in class_info.methods:
                    from rvandroid.domain.coverage import MethodCoverageData
                    method_data = MethodCoverageData(
                        class_name=class_name,
                        method_name=method.name,
                        signature=method.signature,
                        parameters=getattr(method, "params", []),
                        reachable=method.reachable,
                        reaches_mop=method.reaches_mop,
                        directly_reaches_mop=method.directly_reaches_mop,
                        from_static_analysis=True
                    )
                    class_data.add_method(method_data)

            # Log summary
            total_methods = sum(len(class_info.methods) for class_info in classes.classes.values())
            self.logger.info(
                f"Initialized analyzer with {len(self.repository.classes)} classes and {total_methods} methods from static data")

        except Exception as e:
            self.logger.error(f"Error initializing from static data: {e}", exc_info=True)

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

        # Parse logcat file - returns a repository with parsed data
        repository = parse_logcat_file(logcat_file)

        # Add data to our own repository (which respects static analysis constraints)
        # Only methods from static analysis will be registered
        for error in repository.errors:
            self.repository.register_rv_error(error)

        # Calculate and return coverage
        return self.get_coverage_metrics()

    def add_method_call(self, coverage_log: RvCoverageLog) -> None:
        """
        Add a method call to the analyzer's data using standardized model.
        Only methods from static analysis will be registered.

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
        self.repository.register_rv_error(error_log)

    def get_coverage_metrics(self) -> Dict:
        """
        Get coverage metrics from repository.
        Returns 0% metrics if no static analysis data is available.

        Returns:
            Dictionary with metrics
        """
        metrics = self.repository.calculate_metrics()
        metrics_dict = metrics.to_dict()

        return {
            "SUMMARY": metrics_dict,
            "method_coverage": metrics_dict["method_coverage"],
            "activities_coverage": metrics_dict["activity_coverage"],
            "methods_jca_reachable_coverage": metrics_dict["mop_method_coverage"],
            "total_errors": metrics_dict["unique_errors"],
            "total_method_calls": metrics_dict["called_methods"]
        }
