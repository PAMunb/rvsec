# rvandroid/experiment/processor/reporting.py
"""
Reporting processor for the unified execution framework.

This module provides the ReportingProcessor class, which handles the
reporting phase of experiment execution, including visualization creation,
report generation, and data export.
"""

import json
import os
from typing import Optional, Dict, Any

from rvandroid.experiment.core.interfaces import (
    IExecutionContext,
    ExecutionPhase
)
from rvandroid.experiment.event import EventBus, get_event_bus
from rvandroid.experiment.processor.base import BasePhaseProcessor
from rvandroid.util.logging.constants import LOG_START, LOG_COMPLETE, LOG_ERROR


class ReportingProcessor(BasePhaseProcessor):
    """
    Processor for experiment reporting phase.
    
    ### Architectural Decisions:
    - Implements a focused processor for reporting tasks
    - Provides clean separation of reporting concerns
    - Enables flexible report generation strategies
    - Supports comprehensive error handling
    
    ### Role in the System:
    - Generates visualizations of experiment results
    - Creates comprehensive reports for analysis
    - Exports data in various formats for sharing
    - Provides insights into experiment outcomes
    """
    
    def __init__(self, context: IExecutionContext, event_bus: Optional[EventBus] = None):
        """
        Initialize the reporting processor.
        
        Args:
            context: Execution context
            event_bus: Optional event bus for event publishing
        """
        super().__init__(
            processor_name="ReportingProcessor",
            supported_phases=[ExecutionPhase.REPORTING],
            context=context,
            event_bus=event_bus or get_event_bus()
        )
        
    def _process_phase(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Process the reporting phase.
        
        Args:
            phase: Phase to process
            context: Execution context
            
        Returns:
            True if processing was successful, False otherwise
        """
        if phase != ExecutionPhase.REPORTING:
            self.logger.warning(f"Unsupported phase: {phase.name}")
            return False
            
        return self._generate_reports(context)
        
    def _generate_reports(self, context: IExecutionContext) -> bool:
        """
        Generate reports for the experiment.
        
        Args:
            context: Execution context
            
        Returns:
            True if report generation was successful, False otherwise
        """
        with self.logger.with_context(phase="report_generation"):
            self.logger.info(LOG_START.format(operation="report generation"))
            
            success = True
            
            # Generate different report types
            dashboard_success = self._generate_performance_dashboard(context)
            if not dashboard_success:
                self.logger.error("Performance dashboard generation failed")
                success = False
                
            chart_success = self._generate_coverage_charts(context)
            if not chart_success:
                self.logger.error("Coverage chart generation failed")
                success = False
                
            summary_success = self._generate_summary_report(context)
            if not summary_success:
                self.logger.error("Summary report generation failed")
                success = False
                
            if success:
                self.logger.info(LOG_COMPLETE.format(operation="report generation"))
            else:
                self.logger.error(LOG_ERROR.format(
                    operation="report generation",
                    error="One or more report generation steps failed"
                ))
                
            return success
            
    def _generate_performance_dashboard(self, context: IExecutionContext) -> bool:
        """
        Generate performance dashboard.
        
        Args:
            context: Execution context
            
        Returns:
            True if dashboard generation was successful, False otherwise
        """
        with self.logger.with_context(phase="performance_dashboard"):
            self.logger.info(LOG_START.format(operation="performance dashboard generation"))
            
            try:
                # Import visualizer here to avoid circular imports
                from rvandroid.util.performance_visualizer import PerformanceVisualizer
                
                # Get reports directory
                reports_dir = context.get("directories.reports", os.path.join(context.results_dir, "reports"))
                dashboard_dir = os.path.join(reports_dir, "dashboard")
                os.makedirs(dashboard_dir, exist_ok=True)
                
                # Create visualizer
                visualizer = PerformanceVisualizer()
                
                # Generate dashboard
                visualizer.generate_performance_dashboard(context.results_dir, dashboard_dir)
                
                # Log dashboard URL
                dashboard_index = os.path.join(dashboard_dir, "index.html")
                if os.path.exists(dashboard_index):
                    self.logger.info(f"Dashboard available at: file://{os.path.abspath(dashboard_index)}")
                    
                self.logger.info(LOG_COMPLETE.format(operation="performance dashboard generation"))
                return True
                
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="performance dashboard generation",
                    error=str(e)
                ))
                return False
                
    def _generate_coverage_charts(self, context: IExecutionContext) -> bool:
        """
        Generate coverage charts.
        
        Args:
            context: Execution context
            
        Returns:
            True if chart generation was successful, False otherwise
        """
        with self.logger.with_context(phase="coverage_charts"):
            self.logger.info(LOG_START.format(operation="coverage chart generation"))
            
            try:
                # Import visualizer here to avoid circular imports
                from rvandroid.util.performance_visualizer import PerformanceVisualizer
                
                # Get coverage data
                coverage_data = context.get("analysis.coverage", None)
                
                if coverage_data is None:
                    # Try to load from file
                    coverage_file = os.path.join(context.results_dir, "coverage_report.json")
                    if os.path.exists(coverage_file):
                        with open(coverage_file, 'r') as f:
                            coverage_data = json.load(f)
                    else:
                        self.logger.warning("No coverage data found for chart generation")
                        return True
                        
                # Get reports directory
                reports_dir = context.get("directories.reports", os.path.join(context.results_dir, "reports"))
                charts_dir = os.path.join(reports_dir, "charts")
                os.makedirs(charts_dir, exist_ok=True)
                
                # Create visualizer
                visualizer = PerformanceVisualizer()
                
                # Generate charts
                visualizer.generate_coverage_comparison_chart(coverage_data, charts_dir)
                
                self.logger.info(LOG_COMPLETE.format(operation="coverage chart generation"))
                return True
                
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="coverage chart generation",
                    error=str(e)
                ))
                return False
                
    def _generate_summary_report(self, context: IExecutionContext) -> bool:
        """
        Generate summary report.
        
        Args:
            context: Execution context
            
        Returns:
            True if summary generation was successful, False otherwise
        """
        with self.logger.with_context(phase="summary_report"):
            self.logger.info(LOG_START.format(operation="summary report generation"))
            
            try:
                # Get summary data
                summary = context.get("analysis.summary", None)
                
                if summary is None:
                    # Try to load from file
                    summary_file = os.path.join(context.results_dir, "summary.json")
                    if os.path.exists(summary_file):
                        with open(summary_file, 'r') as f:
                            summary = json.load(f)
                    else:
                        self.logger.warning("No summary data found for report generation")
                        return True
                        
                # Get reports directory
                reports_dir = context.get("directories.reports", os.path.join(context.results_dir, "reports"))
                os.makedirs(reports_dir, exist_ok=True)
                
                # Generate HTML report
                html_report = self._generate_html_report(summary)
                
                # Save to file
                report_file = os.path.join(reports_dir, "summary.html")
                with open(report_file, 'w') as f:
                    f.write(html_report)
                    
                self.logger.info(f"Summary report saved to {report_file}")
                self.logger.info(LOG_COMPLETE.format(operation="summary report generation"))
                return True
                
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="summary report generation",
                    error=str(e)
                ))
                return False
                
    def _generate_html_report(self, summary: Dict[str, Any]) -> str:
        """
        Generate HTML report from summary data.
        
        Args:
            summary: Summary data
            
        Returns:
            HTML report
        """
        tasks = summary.get("tasks", {})
        coverage = summary.get("coverage", {})
        errors = summary.get("errors", {})
        
        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Experiment Summary: {summary.get("experiment_id", "Unknown")}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                .section {{ margin-bottom: 30px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .metric {{ font-weight: bold; }}
                .chart {{ margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>Experiment Summary: {summary.get("experiment_id", "Unknown")}</h1>
            
            <div class="section">
                <h2>Task Execution</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td class="metric">Total Tasks</td>
                        <td>{tasks.get("total", 0)}</td>
                    </tr>
                    <tr>
                        <td class="metric">Completed Tasks</td>
                        <td>{tasks.get("completed", 0)}</td>
                    </tr>
                    <tr>
                        <td class="metric">Failed Tasks</td>
                        <td>{tasks.get("failed", 0)}</td>
                    </tr>
                    <tr>
                        <td class="metric">Pending Tasks</td>
                        <td>{tasks.get("pending", 0)}</td>
                    </tr>
                    <tr>
                        <td class="metric">Success Rate</td>
                        <td>{tasks.get("completed", 0) / tasks.get("total", 1) * 100:.2f}%</td>
                    </tr>
                </table>
            </div>
            
            <div class="section">
                <h2>Coverage Results</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td class="metric">Method Coverage</td>
                        <td>{coverage.get("method_coverage", 0):.2f}%</td>
                    </tr>
                    <tr>
                        <td class="metric">Activity Coverage</td>
                        <td>{coverage.get("activity_coverage", 0):.2f}%</td>
                    </tr>
                    <tr>
                        <td class="metric">MOP Method Coverage</td>
                        <td>{coverage.get("mop_coverage", 0):.2f}%</td>
                    </tr>
                    <tr>
                        <td class="metric">Total Method Calls</td>
                        <td>{coverage.get("method_calls", 0)}</td>
                    </tr>
                    <tr>
                        <td class="metric">Unique Methods Called</td>
                        <td>{coverage.get("unique_methods", 0)}</td>
                    </tr>
                </table>
            </div>
            
            <div class="section">
                <h2>Error Summary</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td class="metric">Total Errors</td>
                        <td>{errors.get("total_errors", 0)}</td>
                    </tr>
                </table>
                
                <h3>Error Types</h3>
                <table>
                    <tr>
                        <th>Error Type</th>
                        <th>Count</th>
                    </tr>
        """
        
        # Add error types
        error_types = errors.get("error_types", {})
        for error_type, count in error_types.items():
            html += f"""
                    <tr>
                        <td>{error_type}</td>
                        <td>{count}</td>
                    </tr>
            """
            
        html += f"""
                </table>
            </div>
            
            <div class="section">
                <h2>Experiment Details</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td class="metric">Experiment ID</td>
                        <td>{summary.get("experiment_id", "Unknown")}</td>
                    </tr>
                    <tr>
                        <td class="metric">Results Directory</td>
                        <td>{summary.get("results_dir", "Unknown")}</td>
                    </tr>
                    <tr>
                        <td class="metric">Applications</td>
                        <td>{", ".join(summary.get("apps", []))}</td>
                    </tr>
                    <tr>
                        <td class="metric">Tools</td>
                        <td>{", ".join(summary.get("tools", []))}</td>
                    </tr>
                </table>
            </div>
            
            <div class="section">
                <h2>Charts and Visualizations</h2>
                <p>See the charts directory for detailed visualizations of coverage and performance data.</p>
            </div>
        </body>
        </html>
        """
        
        return html