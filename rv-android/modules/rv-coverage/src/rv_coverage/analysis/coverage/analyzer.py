"""
Coverage analysis module providing centralized analysis capabilities.

This module implements the CoverageAnalyzer class which serves as the main
entry point for coverage analysis operations in the RV-Android system.
"""
from typing import Dict, Optional, Any

from rv_android_core.analysis.base_analyzer import BaseAnalyzer
from rv_android_core.domain.coverage import LogcatRepository
from rv_android_core.domain.log import RvCoverageLog, RvErrorLog
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.error.error_handler import ErrorHandler


class CoverageAnalyzer(BaseAnalyzer[Dict[str, Any]]):
    """
    Centralized analyzer for processing coverage data from various sources.
    
    The CoverageAnalyzer serves as the main entry point for coverage analysis
    operations within the RV-Android system. It processes both real-time and
    batch coverage data, providing unified metrics and insights.

    ### Architectural Decisions:
    - **Direct Repository Integration**: Uses LogcatRepository directly without wrapper
      layers for performance and reduced complexity
    - **BaseAnalyzer Extension**: Implements the standard analyzer interface for
      consistent integration with the experiment framework
    - **Multi-Source Processing**: Supports analysis from logcat files, direct log
      entries, and streaming data sources
    - **Unified Metrics**: Provides coverage metrics across all analysis modes
    - **Event-Free Design**: Unlike CoverageTracker, focuses purely on analysis without
      event publishing, maintaining clear separation of concerns

    ### Role in the System:
    - **Primary Analysis Engine**: Main component for coverage data processing
    - **Metrics Calculator**: Computes coverage metrics from raw data
    - **Data Aggregator**: Combines coverage information with static analysis results
    - **Batch Processor**: Handles offline analysis of logcat files and historical data
    - **Integration Point**: Bridges coverage data with the broader analysis pipeline

    ### Integration Points:
    - **LogcatRepository**: Direct repository access for performance optimization
    - **StaticAnalysisData**: Initialization from static analysis results
    - **LoggingManager**: Standardized logging infrastructure integration
    - **ErrorHandler**: Centralized error handling patterns (inherited from BaseAnalyzer)

    ### Performance Considerations:
    - Direct repository usage eliminates unnecessary abstraction overhead
    - Batch processing optimizations for large logcat files
    - Memory-efficient processing of coverage data streams
    - Cached metrics calculation to avoid redundant computations

    ### Usage Patterns:
    ```python
    # Initialize with static data
    analyzer = CoverageAnalyzer(static_data=static_analysis_result)
    
    # Process logcat file
    metrics = analyzer.analyze("/path/to/logcat.txt")
    
    # Process individual entries
    analyzer.add_method_call(coverage_log)
    analyzer.add_error(error_log)
    
    # Get current metrics
    current_metrics = analyzer.get_coverage_metrics()
    ```
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the analyzer.

        Args:
            static_data: Optional static analysis data
        """
        super().__init__(analyzer_name="coverage", static_data=static_data)

        # Initialize repository directly for optimal performance
        # Direct repository usage provides better performance and simpler data flow
        self.repository = LogcatRepository()

        # Initialize repository from static_data if available
        if static_data and static_data.classes:
            self._initialize_from_static_data()

    @ErrorHandler.handle_errors(component="CoverageAnalyzer", phase="static_data_initialization")
    def _initialize_from_static_data(self) -> None:
        """Initialize repository from static analysis data."""
        # Example: Using decorator for cleaner error handling pattern
        self.logger.info("Initializing analyzer from static analysis data")

        # Repository is now direct LogcatRepository - no wrapper needed
        core_repo = self.repository

        # Process classes from static data
        classes = self.static_data.classes

        for class_name, class_info in classes.classes.items():
            # Create class in repository
            from rv_android_core.domain.coverage import ClassCoverageData
            class_data = ClassCoverageData(
                name=class_name,
                is_activity=class_info.is_activity,
                is_main_activity=getattr(class_info, "is_main_activity", False)
            )

            # Add to repository
            core_repo.add_class(class_data)

            # Add methods to class
            for method in class_info.methods:
                from rv_android_core.domain.coverage import MethodCoverageData
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
        self.log_processing_summary(
            "methods from static data",
            total_methods
        )
        self.logger.info(
            f"Initialized analyzer with {len(core_repo.classes)} classes and "
            f"{total_methods} methods from static data"
        )

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
        from rv_android_core.parser.log.logcat_parser import parse_logcat_file

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
            "total_method_calls": metrics["called_methods"]
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics from the analyzer.
        
        Returns:
            Dictionary containing metrics and their values
        """
        return self.get_coverage_metrics()
