"""
Integration module for connecting the new results analysis system with existing result processing.

This module provides adapters and integration components that allow the new analysis
system to work with the existing result processing infrastructure.
"""
import os
from typing import Dict, Any, Optional

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.analysis.results.analysis import ResultAnalyzer
from rv_android_core.analysis.results.processor import ResultsProcessor
from rv_android_core.analysis.results.report_generator import ReportGenerator, ReportConfig
from rv_android_core.experiment.task.storage import TaskStorage


class AnalysisAdapter:
    """
    Adapter that connects the new analysis system with the existing result processing.
    
    This class provides a bridge between the existing ResultProcessor and the new
    ResultAnalyzer/ReportGenerator, allowing for a gradual transition to the new system.
    """

    def __init__(self, results_dir: str, task_storage: Optional[TaskStorage] = None):
        """
        Initialize the analysis adapter.
        
        Args:
            results_dir: Directory containing experiment results
            task_storage: Optional task storage for accessing task information
        """
        self.results_dir = results_dir
        self.task_storage = task_storage

        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'analysis.results.adapter',
            {'component': 'AnalysisAdapter'}
        )

        # Create analyzer and report generator
        self.analyzer = ResultAnalyzer(results_dir, task_storage)

        # Configure report generation
        self.report_config = ReportConfig(
            include_visualizations=True,
            include_error_details=True,
            include_coverage_details=True,
            include_performance_metrics=True
        )

        self.report_generator = ReportGenerator(self.report_config)

        self.logger.info(f"AnalysisAdapter initialized for results directory: {results_dir}")

    def process_results(self) -> Dict[str, Any]:
        """
        Process results using the new analysis system.
        
        Returns:
            Dictionary containing analysis results summary
        """
        self.logger.info("Processing results with new analysis system")

        # Analyze results
        analysis_result = self.analyzer.analyze()

        # Generate report
        report_path = self.report_generator.generate_report(
            analysis_result=analysis_result,
            output_dir=os.path.join(self.results_dir, "reports"),
            report_name="advanced_analysis"
        )

        self.logger.info(f"Generated advanced analysis report at: {report_path}")

        # Return a summary of the analysis
        return {
            'summary': analysis_result.summary,
            'report_path': report_path,
            'metrics': analysis_result.metrics,
            'coverage': analysis_result.coverage_summary,
            'errors': analysis_result.error_summary
        }

    def get_legacy_processor(self) -> ResultsProcessor:
        """
        Get a legacy result processor that uses the new analysis system internally.
        
        This provides backward compatibility during the transition period.
        
        Returns:
            A result processor instance that delegates to the new analysis system
        """
        return EnhancedResultProcessor(self.results_dir, self.analyzer, self.report_generator)


class EnhancedResultProcessor(ResultsProcessor):
    """
    Enhanced version of the legacy ResultProcessor that uses the new analysis system.
    
    This class extends the existing ResultProcessor to use the new analysis capabilities
    while maintaining compatibility with code that expects the old interface.
    """

    def __init__(self, results_dir: str, analyzer: ResultAnalyzer, report_generator: ReportGenerator):
        """
        Initialize the enhanced result processor.
        
        Args:
            results_dir: Directory containing experiment results
            analyzer: Result analyzer to use for analysis
            report_generator: Report generator to use for report generation
        """
        # Initialize the parent class
        super().__init__(results_dir)

        # Store the new components
        self.analyzer = analyzer
        self.report_generator = report_generator

        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'analysis.results.enhanced_processor',
            {'component': 'EnhancedResultProcessor'}
        )

        self.logger.info("EnhancedResultProcessor initialized")

    def process(self) -> Dict[str, Any]:
        """
        Process experiment results, overriding the legacy method with enhanced capabilities.
        
        This method overrides the base class implementation to use the new analysis system
        while maintaining compatibility with the existing interface.
        
        Returns:
            Dictionary with processing results
        """
        self.logger.info("Processing results with enhanced processor")

        # Use the new analyzer to get advanced analysis
        analysis_result = self.analyzer.analyze()

        # Generate reports using the new report generator
        report_path = self.report_generator.generate_report(
            analysis_result=analysis_result,
            output_dir=os.path.join(self.results_dir, "reports"),
            report_name="enhanced_analysis"
        )

        # Call the legacy method to maintain compatibility
        legacy_results = super().process()

        # Enhance the legacy results with new analysis
        enhanced_results = {
            **legacy_results,
            'advanced_analysis': {
                'summary': analysis_result.summary,
                'report_path': report_path,
                'metrics': analysis_result.metrics
            }
        }

        self.logger.info("Enhanced result processing completed")
        return enhanced_results


class LegacyResultAdapter:
    """
    Adapter that transforms legacy result formats to the format expected by the new analysis system.
    
    This class provides utility methods for converting between the old and new result formats,
    making it easier to integrate the existing and new systems.
    """

    @staticmethod
    def convert_to_new_format(legacy_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert legacy results to the format expected by the new analysis system.
        
        Args:
            legacy_results: Results in the legacy format
        
        Returns:
            Results in the new format
        """
        # Create logger for this method
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            'analysis.results.legacy_adapter',
            {'method': 'convert_to_new_format'}
        )

        logger.info("Converting legacy results to new format")

        # Extract key information from legacy results
        task_results = legacy_results.get('task_results', {})
        coverage_data = legacy_results.get('coverage', {})
        error_data = legacy_results.get('errors', {})

        # Transform into new format
        new_format = {
            'tasks': {},
            'coverage': {
                'overall': coverage_data.get('overall', 0),
                'by_app': coverage_data.get('by_app', {}),
                'by_tool': coverage_data.get('by_tool', {})
            },
            'errors': {
                'count': len(error_data),
                'by_type': {},
                'details': error_data
            },
            'metrics': {
                'execution_time': legacy_results.get('execution_time', 0),
                'task_count': len(task_results)
            }
        }

        # Transform task results
        for task_id, task_data in task_results.items():
            new_format['tasks'][task_id] = {
                'id': task_id,
                'app': task_data.get('app_name', ''),
                'tool': task_data.get('tool_name', ''),
                'status': 'completed' if task_data.get('success', False) else 'failed',
                'execution_time': task_data.get('execution_time', 0),
                'coverage': task_data.get('coverage', 0),
                'error': task_data.get('error', None)
            }

        # Count errors by type
        for error in error_data.values():
            error_type = error.get('type', 'unknown')
            if error_type not in new_format['errors']['by_type']:
                new_format['errors']['by_type'][error_type] = 0
            new_format['errors']['by_type'][error_type] += 1

        logger.info("Legacy result conversion completed")
        return new_format

    @staticmethod
    def convert_to_legacy_format(new_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert results from the new format back to the legacy format.
        
        Args:
            new_results: Results in the new format
        
        Returns:
            Results in the legacy format
        """
        # Create logger for this method
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            'analysis.results.legacy_adapter',
            {'method': 'convert_to_legacy_format'}
        )

        logger.info("Converting new results to legacy format")

        # Extract key information from new results
        tasks = new_results.get('tasks', {})
        coverage = new_results.get('coverage', {})
        errors = new_results.get('errors', {}).get('details', {})
        metrics = new_results.get('metrics', {})

        # Transform into legacy format
        legacy_format = {
            'task_results': {},
            'coverage': {
                'overall': coverage.get('overall', 0),
                'by_app': coverage.get('by_app', {}),
                'by_tool': coverage.get('by_tool', {})
            },
            'errors': errors,
            'execution_time': metrics.get('execution_time', 0)
        }

        # Transform task results
        for task_id, task_data in tasks.items():
            legacy_format['task_results'][task_id] = {
                'app_name': task_data.get('app', ''),
                'tool_name': task_data.get('tool', ''),
                'success': task_data.get('status') == 'completed',
                'execution_time': task_data.get('execution_time', 0),
                'coverage': task_data.get('coverage', 0),
                'error': task_data.get('error', None)
            }

        logger.info("New result conversion to legacy format completed")
        return legacy_format
