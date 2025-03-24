# rvandroid/experiment_workflow/result_manager.py
"""
Result manager component for RV-Android experiments.
Handles result visualization and report generation.
"""
import json
import os

from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rvandroid.util.logging.manager import LoggingManager


class ResultManager:
    """
    A specialized component for managing experiment results and generating reports.

    ### Architectural Decisions:
    - Separates result management concerns from the main experiment controller
    - Provides a clean interface for report generation and visualization
    - Encapsulates the logic for creating different report formats
    - Enables independent testing and reuse of reporting functionality

    ### Role in the System:
    - Generates comprehensive reports from experiment data
    - Creates visualizations of experiment results
    - Provides dashboards for result analysis and interpretation
    - Formats results in a standardized, accessible manner
    """

    def __init__(self, results_dir: str, event_bus: EventBus):
        """
        Initialize the result manager.

        Args:
            results_dir: Directory containing experiment results
            event_bus: Event bus for publishing events
        """
        self.results_dir = results_dir
        self.event_bus = event_bus

        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'experiment_workflow.result_manager',
            {
                CONTEXT_COMPONENT: 'ResultManager'
            }
        )

    def generate_reports(self):
        """
        Generate all reports and visualizations for the experiment.
        """
        with self.logger.with_context(phase="report_generation"):
            self.logger.info(LOG_START.format(operation="report generation"))

            # Generate different report types
            self._generate_performance_dashboard()
            self._generate_coverage_charts()
            self._generate_error_summary()

            self.logger.info(LOG_COMPLETE.format(operation="report generation"))

            # Notify that reports are complete
            self.event_bus.publish_experiment_event(
                EventType.EXPERIMENT_STARTED,
                experiment_id="report_generation",
                message="Report generation completed",
                source="ResultManager"
            )

    def _generate_performance_dashboard(self):
        """
        Generate a performance dashboard for the experiment.
        """
        with self.logger.with_context(phase="performance_visualization"):
            self.logger.info(LOG_START.format(operation="generating performance dashboard"))

            try:
                # Generate performance dashboard
                from rvandroid.util.performance_visualizer import PerformanceVisualizer
                visualizer = PerformanceVisualizer()

                # Generate complete dashboard
                dashboard_dir = visualizer.generate_performance_dashboard(self.results_dir)
                self.logger.info(f"Performance dashboard generated at {dashboard_dir}")

                # Log dashboard URL for easy access
                dashboard_index = os.path.join(dashboard_dir, "index.html")
                if os.path.exists(dashboard_index):
                    self.logger.info(f"Dashboard available at: file://{os.path.abspath(dashboard_index)}")

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="generating performance dashboard",
                    error=str(e)
                ))

            self.logger.info(LOG_COMPLETE.format(operation="generating performance dashboard"))

    def _generate_coverage_charts(self):
        """
        Generate coverage charts for the experiment.
        """
        with self.logger.with_context(phase="coverage_visualization"):
            self.logger.info(LOG_START.format(operation="generating coverage charts"))

            try:
                # Get coverage report
                coverage_report_path = os.path.join(self.results_dir, "coverage_report.json")
                if not os.path.exists(coverage_report_path):
                    self.logger.warning(f"Coverage report not found at {coverage_report_path}")
                    return

                with open(coverage_report_path, 'r') as f:
                    coverage_report = json.load(f)

                # Generate coverage charts
                from rvandroid.util.performance_visualizer import PerformanceVisualizer
                visualizer = PerformanceVisualizer()

                charts_dir = os.path.join(self.results_dir, "charts")
                os.makedirs(charts_dir, exist_ok=True)

                # Generate comparison chart
                visualizer.generate_coverage_comparison_chart(
                    coverage_report=coverage_report,
                    output_dir=charts_dir
                )

                self.logger.info(f"Coverage charts generated in {charts_dir}")

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="generating coverage charts",
                    error=str(e)
                ))

            self.logger.info(LOG_COMPLETE.format(operation="generating coverage charts"))

    def _generate_error_summary(self):
        """
        Generate error summary for the experiment.
        """
        with self.logger.with_context(phase="error_summary"):
            self.logger.info(LOG_START.format(operation="generating error summary"))

            try:
                # Get analysis results
                analysis_path = os.path.join(self.results_dir, "analysis_results.json")
                if not os.path.exists(analysis_path):
                    self.logger.warning(f"Analysis results not found at {analysis_path}")
                    return

                with open(analysis_path, 'r') as f:
                    analysis_results = json.load(f)

                # Extract error information
                error_summary = {
                    "total_errors": 0,
                    "errors_by_app": {},
                    "errors_by_tool": {},
                    "common_errors": []
                }

                # Process app data
                if "apps" in analysis_results:
                    for app_name, app_data in analysis_results["apps"].items():
                        errors = app_data.get("summary", {}).get("errors", 0)
                        error_summary["total_errors"] += errors
                        error_summary["errors_by_app"][app_name] = errors

                # Process tool data
                if "tools" in analysis_results:
                    for tool_name, tool_data in analysis_results["tools"].items():
                        errors = tool_data.get("errors", 0)
                        error_summary["errors_by_tool"][tool_name] = errors

                # Save error summary
                summary_path = os.path.join(self.results_dir, "error_summary.json")
                with open(summary_path, 'w') as f:
                    json.dump(error_summary, f, indent=2)

                self.logger.info(f"Error summary saved to {summary_path}")

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="generating error summary",
                    error=str(e)
                ))

            self.logger.info(LOG_COMPLETE.format(operation="generating error summary"))
