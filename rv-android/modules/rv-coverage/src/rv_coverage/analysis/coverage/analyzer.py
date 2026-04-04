"""
Coverage analysis module with fallback capabilities.

This module implements the CoverageAnalyzer class which serves as the main
entry point for coverage analysis operations in the RV-Android system,
with support for graceful degradation when static analysis data is not available.
"""

from enum import Enum
from typing import Any, Dict, Optional

from rv_android_core.analysis.base_analyzer import BaseAnalyzer
from rv_android_core.domain.coverage import LogcatRepository
from rv_android_core.domain.log import RvCoverageLog, RvErrorLog
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.android.repository_initializer import (
    initialize_repository_from_static_data,
)
from rv_android_core.util.error.error_handler import ErrorHandler


class CoverageCalculationMode(Enum):
    """Enumeration of coverage calculation modes."""

    FULL_STATIC_ANALYSIS = "full_static_analysis"
    PARTIAL_STATIC_ANALYSIS = "partial_static_analysis"
    RUNTIME_ONLY = "runtime_only"
    FALLBACK_MODE = "fallback_mode"


class CoverageAnalyzer(BaseAnalyzer[Dict[str, Any]]):
    """
    Coverage analyzer with fallback capabilities for graceful degradation.

    The CoverageAnalyzer serves as the main entry point for coverage analysis
    operations within the RV-Android system. It processes both real-time and
    batch coverage data, with fallback support when static analysis is unavailable.

    ### Architectural Features:
    - **Direct Repository Integration**: Uses LogcatRepository directly without wrapper
      layers for performance and reduced complexity
    - **Fallback Support**: Graceful degradation when static analysis data is unavailable
    - **Multi-Mode Operation**: Supports full, partial, runtime-only, and fallback modes
    - **Unified Metrics**: Provides coverage metrics across all analysis modes
    - **Event-Free Design**: Focuses purely on analysis without event publishing

    ### Fallback Capabilities:
    - **FULL_STATIC_ANALYSIS**: Complete static analysis data available
    - **PARTIAL_STATIC_ANALYSIS**: Limited static analysis data available
    - **RUNTIME_ONLY**: Only runtime data available, no static analysis
    - **FALLBACK_MODE**: Minimal functionality with basic runtime coverage

    ### Role in the System:
    - **Primary Analysis Engine**: Main component for coverage data processing
    - **Resilient Analyzer**: Continues operation despite missing dependencies
    - **Data Aggregator**: Combines coverage information with available static results
    - **Batch Processor**: Handles offline analysis of logcat files and historical data
    - **Integration Point**: Bridges coverage data with the broader analysis pipeline

    ### Usage Patterns:
    ```python
    # Initialize with static data (full mode)
    analyzer = CoverageAnalyzer(static_data=static_analysis_result)

    # Initialize in fallback mode
    analyzer = CoverageAnalyzer()
    analyzer.initialize_fallback_mode()

    # Process logcat file
    metrics = analyzer.analyze("/path/to/logcat.txt")

    # Get metrics with fallback information
    metrics = analyzer.get_coverage_metrics_with_fallback()
    ```
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the analyzer with fallback support.

        Args:
            static_data: Optional static analysis data
        """
        super().__init__(analyzer_name="coverage", static_data=static_data)

        # Initialize repository directly for optimal performance
        self.repository = LogcatRepository()

        # Initialize calculation mode based on available data
        self.calculation_mode = self._determine_calculation_mode(static_data)

        # Fallback state tracking
        self.fallback_reason: Optional[str] = None
        self.static_analysis_available = bool(static_data and static_data.classes)

        # Initialize repository from static_data if available
        if static_data and static_data.classes:
            self._initialize_from_static_data()
        else:
            self._initialize_fallback_mode_if_needed()

    @ErrorHandler.handle_errors(
        component="CoverageAnalyzer", phase="static_data_initialization"
    )
    def _initialize_from_static_data(self) -> None:
        """Initialize repository from static analysis data."""
        self.logger.info("Initializing analyzer from static analysis data")

        # Use centralized repository initializer to eliminate code duplication
        initialize_repository_from_static_data(
            self.repository, self.static_data, self.__class__.__name__
        )

        # Log summary
        total_methods = sum(
            len(class_info.methods)
            for class_info in self.static_data.classes.classes.values()
        )
        self.log_processing_summary("methods from static data", total_methods)
        self.logger.info(
            f"Initialized analyzer with {len(self.repository.classes)} classes and "
            f"{total_methods} methods from static data"
        )

    def _determine_calculation_mode(
        self, static_data: Optional[StaticAnalysisData]
    ) -> CoverageCalculationMode:
        """
        Determine the appropriate calculation mode based on available data.

        Args:
            static_data: Available static analysis data

        Returns:
            Appropriate calculation mode
        """
        if not static_data:
            return CoverageCalculationMode.RUNTIME_ONLY

        if not static_data.classes:
            return CoverageCalculationMode.RUNTIME_ONLY

        # Check completeness of static data
        total_classes = len(static_data.classes.classes)
        total_methods = sum(
            len(class_info.methods)
            for class_info in static_data.classes.classes.values()
        )

        if total_classes == 0 or total_methods == 0:
            return CoverageCalculationMode.RUNTIME_ONLY
        elif total_methods < 10:  # Threshold for partial analysis
            return CoverageCalculationMode.PARTIAL_STATIC_ANALYSIS
        else:
            return CoverageCalculationMode.FULL_STATIC_ANALYSIS

    def _initialize_fallback_mode_if_needed(self) -> None:
        """Initialize fallback mode if static data is not available."""
        if self.calculation_mode in [
            CoverageCalculationMode.RUNTIME_ONLY,
            CoverageCalculationMode.FALLBACK_MODE,
        ]:
            self.initialize_fallback_mode()

    @ErrorHandler.handle_errors(
        component="CoverageAnalyzer", phase="fallback_initialization"
    )
    def initialize_fallback_mode(self) -> None:
        """
        Initialize analyzer in fallback mode without static analysis.

        This method enables the analyzer to operate with limited functionality
        when static analysis data is not available, focusing on runtime coverage
        data collection and basic metrics calculation.
        """
        self.calculation_mode = CoverageCalculationMode.FALLBACK_MODE
        self.fallback_reason = (
            "Static analysis data not available - operating with runtime data only"
        )
        self.static_analysis_available = False

        self.logger.warning(
            "CoverageAnalyzer operating in fallback mode - limited static analysis"
        )
        self.logger.info("Fallback mode: Basic runtime coverage tracking enabled")

    @ErrorHandler.handle_errors(component="CoverageAnalyzer", phase="fallback_metrics")
    def get_coverage_metrics_with_fallback(self) -> Dict[str, Any]:
        """
        Get coverage metrics with fallback calculation strategies.

        This method provides coverage metrics regardless of the calculation mode,
        with additional metadata about the analysis capabilities and limitations.

        Returns:
            Dictionary with coverage metrics and mode information
        """
        # Get base metrics
        base_metrics = self.get_coverage_metrics()

        # Add fallback metadata
        base_metrics.update(
            {
                "calculation_mode": self.calculation_mode.value,
                "static_analysis_available": self.static_analysis_available,
                "fallback_reason": self.fallback_reason,
                "is_degraded_mode": self.calculation_mode
                in [
                    CoverageCalculationMode.FALLBACK_MODE,
                    CoverageCalculationMode.RUNTIME_ONLY,
                ],
            }
        )

        # Adjust metrics based on calculation mode
        if self.calculation_mode == CoverageCalculationMode.FALLBACK_MODE:
            base_metrics = self._calculate_fallback_metrics(base_metrics)
        elif self.calculation_mode == CoverageCalculationMode.PARTIAL_STATIC_ANALYSIS:
            base_metrics = self._calculate_partial_metrics(base_metrics)

        return base_metrics

    def _calculate_fallback_metrics(
        self, base_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate fallback metrics using only runtime data.

        Args:
            base_metrics: Base metrics from standard calculation

        Returns:
            Adjusted metrics for fallback mode
        """
        # Use repository directly for runtime data
        called_methods = (
            len(self.repository.get_called_methods())
            if hasattr(self.repository, "get_called_methods")
            else 0
        )
        unique_errors = (
            len(self.repository.get_unique_errors())
            if hasattr(self.repository, "get_unique_errors")
            else 0
        )

        # Create fallback metrics focusing on runtime data
        fallback_metrics = {
            "runtime_method_calls": called_methods,
            "runtime_unique_errors": unique_errors,
            "runtime_coverage_percentage": 0.0,  # Cannot calculate without static data
            "static_analysis_coverage": "unavailable",
            "reachability_analysis": "unavailable",
            "mop_analysis": "unavailable",
        }

        # Merge with base metrics, prioritizing runtime data
        base_metrics.update(fallback_metrics)
        base_metrics["total_method_calls"] = called_methods
        base_metrics["total_errors"] = unique_errors

        return base_metrics

    def _calculate_partial_metrics(
        self, base_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate metrics for partial static analysis mode.

        Args:
            base_metrics: Base metrics from standard calculation

        Returns:
            Adjusted metrics for partial analysis mode
        """
        # Add partial analysis indicators
        base_metrics.update(
            {
                "partial_analysis_warning": "Limited static analysis data available",
                "static_coverage_confidence": "low",
                "reachability_analysis": "partial",
            }
        )

        return base_metrics

    def get_fallback_status(self) -> Dict[str, Any]:
        """
        Get detailed status of fallback capabilities.

        Returns:
            Dictionary with fallback status information
        """
        return {
            "mode": self.calculation_mode.value,
            "static_analysis_available": self.static_analysis_available,
            "fallback_active": self.calculation_mode
            == CoverageCalculationMode.FALLBACK_MODE,
            "fallback_reason": self.fallback_reason,
            "can_provide_basic_metrics": True,
            "can_provide_static_coverage": self.static_analysis_available,
            "can_provide_reachability": self.static_analysis_available,
            "capabilities": self._get_available_capabilities(),
        }

    def _get_available_capabilities(self) -> Dict[str, bool]:
        """Get dictionary of available analysis capabilities."""
        return {
            "runtime_coverage": True,
            "error_tracking": True,
            "method_call_tracking": True,
            "static_coverage": self.static_analysis_available,
            "reachability_analysis": self.static_analysis_available,
            "mop_analysis": self.static_analysis_available,
            "activity_coverage": self.static_analysis_available,
        }

    def analyze(self, data: Any) -> Dict[str, Any]:
        """
        Analyze data and return results.

        Can handle:
        - RvCoverageLog: for method call registration
        - RvErrorLog: for error registration
        - str: assumes it's a logcat file path
        - List[RvCoverageLog] or List[RvErrorLog]: batch processing

        Args:
            data: The data to analyze

        Returns:
            Dictionary with coverage metrics
        """
        if isinstance(data, str):
            return self.process_logcat_file(data)
        elif isinstance(data, RvCoverageLog):
            self.add_method_call(data)
            return self.get_coverage_metrics()
        elif isinstance(data, RvErrorLog):
            self.add_error(data)
            return self.get_coverage_metrics()
        elif isinstance(data, list):
            # Process each item in the list
            for item in data:
                if isinstance(item, RvCoverageLog):
                    self.add_method_call(item)
                elif isinstance(item, RvErrorLog):
                    self.add_error(item)
            return self.get_coverage_metrics()
        else:
            self.logger.warning(f"Unsupported data type for analysis: {type(data)}")
            return self.get_coverage_metrics()

    def process_logcat_file(self, logcat_file: str) -> Dict[str, Any]:
        """
        Process a logcat file for coverage and error data.

        Args:
            logcat_file: Path to logcat file

        Returns:
            Dictionary with coverage results
        """
        from rv_coverage.parser.log.logcat_parser import parse_logcat_file

        # Parse logcat file
        parsed_repo = parse_logcat_file(logcat_file)

        # Repository is now direct LogcatRepository - no wrapper needed
        core_repo = self.repository

        # Transfer errors
        for error in parsed_repo.errors:
            core_repo.register_rv_error(error)

        # Log processing
        self.log_processing_summary("errors from logcat", len(parsed_repo.errors))

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
        self.repository.register_rv_error(error_log)

    def get_coverage_metrics(self) -> Dict[str, Any]:
        """
        Get coverage metrics.

        Returns:
            Dictionary with metrics
        """
        metrics_obj = self.repository.calculate_metrics()
        metrics = metrics_obj.to_dict()

        return {
            "SUMMARY": metrics,
            "method_coverage": metrics["method_coverage"],
            "activities_coverage": metrics["activity_coverage"],
            "methods_jca_reachable_coverage": metrics["mop_method_coverage"],
            "total_errors": metrics["unique_errors"],
            "total_method_calls": metrics["called_methods"],
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics from the analyzer.

        Returns:
            Dictionary containing metrics and their values
        """
        return self.get_coverage_metrics()
