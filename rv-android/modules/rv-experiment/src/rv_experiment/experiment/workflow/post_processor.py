# rvandroid/experiment_workflow/post_processor.py
"""
Post-processor component for RV-Android experiments.
Handles analysis of experiment results.
"""
import os

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.event import EventBus, EventType


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

    def __init__(self, results_dir: str, event_bus: EventBus, execution_controller=None, result_manager=None):
        """
        Initialize the post-processor.

        Args:
            results_dir: Directory containing experiment results
            event_bus: Event bus for publishing events
            execution_controller: Reference to the execution controller
            result_manager: Result manager for processing results
        """
        self.results_dir = results_dir
        self.event_bus = event_bus
        self.execution_controller = execution_controller
        self.result_manager = result_manager
        self.error_handler = ErrorHandler.get_instance()

        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'experiment_workflow.post_processor',
            {
                CONTEXT_COMPONENT: 'PostProcessor'
            }
        )

    def process(self):
        """
        Process experiment results after execution.
        Performs standardized analysis on collected data.
        """
        with self.logger.with_context(phase="post_processing"):
            self.logger.info(LOG_START.format(phase="results processing"))

            # Process the results
            self._process_coverage_data()
            self._analyze_results()

            self.logger.info(LOG_COMPLETE.format(phase="results processing"))

            # Notify that post-processing is complete
            self.event_bus.publish_experiment_event(
                EventType.EXPERIMENT_COMPLETED,
                experiment_id="post_processing",
                message="Post-processing completed",
                source="PostProcessor"
            )

    def _process_coverage_data(self):
        """
        Delegate coverage data processing to ResultManager.
        Focuses on experiment-level coordination only.
        """
        with self.logger.with_context(phase="process_coverage"):
            self.logger.info(LOG_START.format(phase="coverage processing delegation"))

            # Delegate to ResultManager instead of duplicating logic
            if self.result_manager:
                self.logger.info("Delegating coverage processing to ResultManager")
                # ResultManager will handle all coverage processing in generate_reports()
                # No duplicated logic here
            else:
                self.logger.warning("No ResultManager available - coverage processing skipped")

            self.logger.info(LOG_COMPLETE.format(phase="coverage processing delegation"))

            # Publish delegation complete event
            self.event_bus.publish_analysis_event(
                EventType.COVERAGE_UPDATED,
                data={"delegated_to": "ResultManager"},
                source="PostProcessor"
            )

    def _analyze_results(self):
        """
        Perform detailed analysis of experiment results.
        Uses the configured ResultManager for result processing.
        """
        with self.logger.with_context(phase="results_analysis"):
            self.logger.info(LOG_START.format(phase="results analysis"))

            try:
                # Use the configured ResultManager instead of creating a new one
                if self.result_manager:
                    self.logger.info("Generating comprehensive experiment reports")
                    self.result_manager.generate_reports()
                    self.logger.info("Results generated successfully by ResultManager")
                else:
                    self.logger.warning("No ResultManager available - skipping detailed analysis")

                # Generate performance and error diagnostics
                self._generate_diagnostics()

            except Exception as e:
                error_context = {
                    "component": "PostProcessor",
                    "operation": "results_analysis",
                    "results_dir": self.results_dir,
                    "has_result_manager": self.result_manager is not None
                }
                self.error_handler.handle_error(e, error_context)

            self.logger.info(LOG_COMPLETE.format(phase="results analysis"))

    def _generate_diagnostics(self):
        """
        Generate diagnostic information about the experiment execution.
        Includes performance metrics and error summaries.
        """
        with self.logger.with_context(phase="diagnostics"):
            self.logger.info(LOG_START.format(phase="generating diagnostics"))

            try:
                # Generate diagnostic report
                from rv_android_core.util.diagnostics import DiagnosticTool
                diagnostic_tool = DiagnosticTool()
                report = diagnostic_tool.generate_report()
                report_path = os.path.join(self.results_dir, "diagnostic_report.json")
                report.save_to_file(report_path)
                self.logger.info(f"Diagnostic report saved to {report_path}")

            except Exception as e:
                error_context = {
                    "component": "PostProcessor",
                    "operation": "generating_diagnostics",
                    "results_dir": self.results_dir
                }
                self.error_handler.handle_error(e, error_context)

            self.logger.info(LOG_COMPLETE.format(phase="generating diagnostics"))
