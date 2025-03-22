# rvandroid/experiment_workflow/post_processor.py
"""
Post-processor component for RV-Android experiments.
Handles analysis of experiment results.
"""
import json
import os

from rvandroid.experiment.event_system import EventBus, EventType
from rvandroid.util.logging_manager import LoggingManager


class PostProcessor:
    """
    A specialized component for handling the post-processing phase of experiments.

    ### Architectural Decisions:
    - Separates result processing concerns from the main experiment controller
    - Provides a clean interface for post-experiment analysis
    - Encapsulates the logic for results processing and analysis
    - Enables independent testing and reuse of post-processing functionality

    ### Role in the System:
    - Processes raw experimental results after execution
    - Performs standardized analysis of coverage and error data
    - Prepares data for reporting and visualization
    - Generates experiment summaries and metrics
    """

    def __init__(self, results_dir: str, event_bus: EventBus, execution_controller=None):
        """
        Initialize the post-processor.

        Args:
            results_dir: Directory containing experiment results
            event_bus: Event bus for publishing events
            execution_controller: Reference to the execution controller
        """
        self.results_dir = results_dir
        self.event_bus = event_bus
        self.execution_controller = execution_controller

        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'experiment_workflow.post_processor',
            {
                LoggingManager.CONTEXT_COMPONENT: 'PostProcessor'
            }
        )

    def process(self):
        """
        Process experiment results after execution.
        Performs standardized analysis on collected data.
        """
        with self.logger.with_context(phase="post_processing"):
            self.logger.info(LoggingManager.LOG_START.format(operation="results processing"))

            # Process the results
            self._process_coverage_data()
            self._analyze_results()

            self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="results processing"))

            # Notify that post-processing is complete
            self.event_bus.publish_experiment_event(
                EventType.EXPERIMENT_STARTED,
                experiment_id="post_processing",
                message="Post-processing completed",
                source="PostProcessor"
            )

    def _process_coverage_data(self):
        """
        Process coverage data from experiment execution.
        Generates a standardized coverage report.
        """
        with self.logger.with_context(phase="process_coverage"):
            self.logger.info(LoggingManager.LOG_START.format(operation="coverage processing"))

            # Get coverage report from execution controller
            if self.execution_controller:
                coverage_report = self.execution_controller.get_coverage_report()
            else:
                # Fall back to creating an empty report structure
                coverage_report = {
                    "tasks": {},
                    "summary": {
                        "total_tasks": 0,
                        "completed_tasks": 0,
                        "avg_method_coverage": 0,
                        "avg_activities_coverage": 0,
                        "avg_mop_coverage": 0,
                        "total_errors": 0
                    }
                }

            # Save coverage report to file
            report_path = os.path.join(self.results_dir, "coverage_report.json")
            with open(report_path, 'w') as f:
                json.dump(coverage_report, f, indent=2)

            self.logger.info(f"Coverage report saved to {report_path}")
            self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="coverage processing"))

            # Publish coverage report generated event
            self.event_bus.publish_analysis_event(
                EventType.COVERAGE_UPDATED,
                data={"report_path": report_path},
                source="PostProcessor"
            )

    def _analyze_results(self):
        """
        Perform detailed analysis of experiment results.
        Uses standardized models for result processing.
        """
        with self.logger.with_context(phase="results_analysis"):
            self.logger.info(LoggingManager.LOG_START.format(operation="results analysis"))

            try:
                # Import here to avoid circular imports
                from rvandroid.analysis.results_analysis import process_results

                # Process results using standardized analysis
                results = process_results(self.results_dir)

                # Save analysis results
                analysis_path = os.path.join(self.results_dir, "analysis_results.json")
                with open(analysis_path, 'w') as f:
                    json.dump(results, f, indent=2)

                self.logger.info(f"Analysis results saved to {analysis_path}")

                # Generate performance and error diagnostics
                self._generate_diagnostics()

            except Exception as e:
                self.logger.error(LoggingManager.LOG_ERROR.format(
                    operation="results analysis",
                    error=str(e)
                ))

            self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="results analysis"))

    def _generate_diagnostics(self):
        """
        Generate diagnostic information about the experiment execution.
        Includes performance metrics and error summaries.
        """
        with self.logger.with_context(phase="diagnostics"):
            self.logger.info(LoggingManager.LOG_START.format(operation="generating diagnostics"))

            try:
                # Generate diagnostic report
                from rvandroid.util.diagnostics import DiagnosticTool
                diagnostic_tool = DiagnosticTool()
                report = diagnostic_tool.generate_report()
                report_path = os.path.join(self.results_dir, "diagnostic_report.json")
                report.save_to_file(report_path)
                self.logger.info(f"Diagnostic report saved to {report_path}")

            except Exception as e:
                self.logger.error(LoggingManager.LOG_ERROR.format(
                    operation="generating diagnostics",
                    error=str(e)
                ))

            self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="generating diagnostics"))
           