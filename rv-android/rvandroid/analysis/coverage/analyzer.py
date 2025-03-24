# rvandroid/analysis/coverage/analyzer.py
"""
Centralized coverage analyzer module.
"""
import logging
from typing import Dict, Optional, Any

from rvandroid.analysis.coverage.repository import CoverageRepository
from rvandroid.domain.log import RvCoverageLog, RvErrorLog
from rvandroid.domain.static import StaticAnalysisData


class CoverageAnalyzer:
    """
    Centralized analyzer for processing coverage data from various sources.

    ### Architectural Decisions:
    - Separates analysis logic from data collection
    - Provides a unified interface for coverage analysis
    - Supports both streaming and batch processing

    ### Role in the System:
    - Processes coverage data from experiment execution
    - Calculates metrics based on static analysis data
    - Tracks and aggregates errors during execution
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the analyzer.

        Args:
            static_data: Optional static analysis data
        """
        self.logger = logging.getLogger(__name__)
        self.static_data = static_data

        # Initialize repository
        self.repository = CoverageRepository()

        # Initialize repository from static_data if available
        if static_data and static_data.classes:
            self._initialize_from_static_data()

    def _initialize_from_static_data(self) -> None:
        """Initialize repository from static analysis data."""
        try:
            self.logger.info("Initializing analyzer from static analysis data")

            # Get underlying repository for direct operations
            core_repo = self.repository.get_underlying_repository()

            # Process classes from static data
            classes = self.static_data.classes

            for class_name, class_info in classes.classes.items():
                # Create class in repository
                from rvandroid.domain.coverage import ClassCoverageData
                class_data = ClassCoverageData(
                    name=class_name,
                    is_activity=class_info.is_activity,
                    is_main_activity=getattr(class_info, "is_main_activity", False)
                )

                # Add to repository
                core_repo.add_class(class_data)

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
                f"Initialized analyzer with {len(core_repo.classes)} classes and "
                f"{total_methods} methods from static data"
            )

        except Exception as e:
            self.logger.error(f"Error initializing from static data: {e}", exc_info=True)

    def process_logcat_file(self, logcat_file: str) -> Dict[str, Any]:
        """
        Process a logcat file for coverage and error data.

        Args:
            logcat_file: Path to logcat file

        Returns:
            Dictionary with coverage results
        """
        from rvandroid.parser.log.logcat_parser import parse_logcat_file

        # Parse logcat file
        parsed_repo = parse_logcat_file(logcat_file)

        # Get our repository's underlying core
        core_repo = self.repository.get_underlying_repository()

        # Transfer errors
        for error in parsed_repo.errors:
            core_repo.register_rv_error(error)

        # Calculate and return coverage
        return self.get_coverage_metrics()

    def add_method_call(self, coverage_log: RvCoverageLog) -> None:
        """
        Add a method call to the repository.

        Args:
            coverage_log: Coverage log entry
        """
        self.repository.register_method_call(coverage_log)

    def add_error(self, error_log: RvErrorLog) -> None:
        """
        Add an error to the repository.

        Args:
            error_log: Error log entry
        """
        self.repository.register_error(error_log)

    def get_coverage_metrics(self) -> Dict[str, Any]:
        """
        Get coverage metrics.

        Returns:
            Dictionary with metrics
        """
        metrics = self.repository.get_metrics()

        return {
            "SUMMARY": metrics,
            "method_coverage": metrics["method_coverage"],
            "activities_coverage": metrics["activity_coverage"],
            "methods_jca_reachable_coverage": metrics["mop_method_coverage"],
            "total_errors": metrics["unique_errors"],
            "total_method_calls": metrics["called_methods"]
        }
