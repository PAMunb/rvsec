# rvandroid/analysis/results/report_generator.py
"""
Advanced report generation for experiment results.

This module provides comprehensive report generation capabilities for
experiment results, including detailed metrics, visualizations, and comparisons.
"""

import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rvandroid.analysis.results.analysis import (
    AnalysisResult,
    CoverageMetrics,
    PerformanceMetrics,
    ErrorMetrics
)


@dataclass
class ReportConfig:
    """
    Configuration for report generation.
    
    ### Architectural Decisions:
    - Uses dataclass for type safety and serialization
    - Provides comprehensive report configuration options
    - Enables flexible report customization
    - Supports fine-grained control over report content
    
    ### Role in the System:
    - Serves as a container for report settings
    - Enables consistent configuration across report generators
    - Facilitates configuration-based report customization
    - Provides a unified interface for report configuration
    """
    generate_html: bool = True
    generate_json: bool = True
    generate_visualizations: bool = True
    include_coverage: bool = True
    include_performance: bool = True
    include_errors: bool = True
    include_tool_comparison: bool = True
    include_app_comparison: bool = True
    chart_type: str = "bar"  # bar, line, scatter
    theme: str = "light"  # light, dark
    output_format: str = "html"  # html, markdown, text
    include_raw_data: bool = False
    custom_title: Optional[str] = None
    custom_description: Optional[str] = None
    comparison_metrics: List[str] = field(default_factory=lambda: [
        "method_coverage",
        "activity_coverage",
        "mop_method_coverage",
        "total_errors"
    ])


class ReportGenerator:
    """
    Advanced generator for experiment reports.
    
    ### Architectural Decisions:
    - Implements a comprehensive reporting system
    - Provides modular, extensible report generation
    - Generates standardized reports with rich visualization
    - Facilitates detailed experiment result communication
    
    ### Role in the System:
    - Generates detailed reports from experiment analysis
    - Provides visualizations of experiment results
    - Enables comparison between different tools and apps
    - Facilitates experiment evaluation and communication
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        """
        Initialize the report generator.
        
        Args:
            config: Optional report configuration
        """
        self.config = config or ReportConfig()
        self.logger = LoggingManager.get_instance().get_logger(
            'analysis.results.report_generator',
            {CONTEXT_COMPONENT: 'ReportGenerator'}
        )

    def generate_report(self,
                        analysis_result: AnalysisResult,
                        output_dir: str,
                        report_name: Optional[str] = None) -> str:
        """
        Generate a comprehensive report from analysis results.
        
        Args:
            analysis_result: Analysis result to report on
            output_dir: Directory to write report to
            report_name: Optional name for the report
            
        Returns:
            Path to the generated report
        """
        self.logger.info(f"Generating report in {output_dir}")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Generate report name if not provided
        if not report_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_name = f"experiment_report_{timestamp}"

        # Generate data files
        data_dir = os.path.join(output_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        # Save analysis result to JSON file
        json_path = os.path.join(data_dir, f"{report_name}.json")
        analysis_result.save_to_file(json_path)

        # Generate visualizations if requested
        if self.config.generate_visualizations:
            self._generate_visualizations(analysis_result, output_dir, report_name)

        # Generate HTML report if requested
        if self.config.generate_html:
            html_path = self._generate_html_report(analysis_result, output_dir, report_name)
            return html_path

        return json_path

    def _generate_visualizations(self,
                                 analysis_result: AnalysisResult,
                                 output_dir: str,
                                 report_name: str) -> Dict[str, str]:
        """
        Generate visualizations for analysis results.
        
        Args:
            analysis_result: Analysis result to visualize
            output_dir: Directory to write visualizations to
            report_name: Base name for visualization files
            
        Returns:
            Dictionary mapping visualization types to file paths
        """
        vis_dir = os.path.join(output_dir, "visualizations")
        os.makedirs(vis_dir, exist_ok=True)

        visualization_paths = {}

        try:
            # Import visualization libraries
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            import matplotlib.pyplot as plt
            import numpy as np

            # Coverage visualization
            if self.config.include_coverage:
                # Generate method coverage by tool chart
                tool_names = list(analysis_result.tools_metrics.keys())

                if tool_names:
                    # Method coverage by tool
                    method_coverage_values = [
                        analysis_result.tools_metrics[tool]["coverage"].get("method_coverage", 0)
                        for tool in tool_names
                    ]

                    plt.figure(figsize=(10, 6))
                    bars = plt.bar(tool_names, method_coverage_values)
                    plt.title('Method Coverage by Tool')
                    plt.xlabel('Tool')
                    plt.ylabel('Method Coverage (%)')
                    plt.ylim(0, 100)

                    # Add value labels
                    for bar in bars:
                        height = bar.get_height()
                        plt.text(
                            bar.get_x() + bar.get_width() / 2.,
                            height,
                            f'{height:.1f}%',
                            ha='center',
                            va='bottom'
                        )

                    # Save figure
                    method_coverage_path = os.path.join(vis_dir, f"{report_name}_method_coverage_by_tool.png")
                    plt.savefig(method_coverage_path, dpi=300, bbox_inches='tight')
                    plt.close()

                    visualization_paths["method_coverage_by_tool"] = method_coverage_path

                # Coverage metrics comparison
                plt.figure(figsize=(10, 6))
                metrics = ["Method Coverage", "Activity Coverage", "MOP Coverage"]
                values = [
                    analysis_result.coverage.method_coverage,
                    analysis_result.coverage.activity_coverage,
                    analysis_result.coverage.mop_method_coverage
                ]

                bars = plt.bar(metrics, values)
                plt.title('Coverage Metrics Comparison')
                plt.ylabel('Coverage (%)')
                plt.ylim(0, 100)

                # Add value labels
                for bar in bars:
                    height = bar.get_height()
                    plt.text(
                        bar.get_x() + bar.get_width() / 2.,
                        height,
                        f'{height:.1f}%',
                        ha='center',
                        va='bottom'
                    )

                # Save figure
                coverage_comparison_path = os.path.join(vis_dir, f"{report_name}_coverage_comparison.png")
                plt.savefig(coverage_comparison_path, dpi=300, bbox_inches='tight')
                plt.close()

                visualization_paths["coverage_comparison"] = coverage_comparison_path

            # Error visualization
            if self.config.include_errors and analysis_result.errors.total_errors > 0:
                # Error categories pie chart
                plt.figure(figsize=(10, 8))

                # Get categories and counts
                categories = list(analysis_result.errors.error_categories.keys())
                counts = list(analysis_result.errors.error_categories.values())

                if categories and counts:
                    # Sort by count
                    sorted_data = sorted(zip(categories, counts), key=lambda x: x[1], reverse=True)
                    categories, counts = zip(*sorted_data)

                    # Generate pie chart
                    plt.pie(
                        counts,
                        labels=categories,
                        autopct='%1.1f%%',
                        startangle=90
                    )
                    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
                    plt.title('Error Categories')

                    # Save figure
                    error_categories_path = os.path.join(vis_dir, f"{report_name}_error_categories.png")
                    plt.savefig(error_categories_path, dpi=300, bbox_inches='tight')
                    plt.close()

                    visualization_paths["error_categories"] = error_categories_path

                # Errors by tool bar chart
                if tool_names:
                    # Errors by tool
                    error_counts = [
                        analysis_result.tools_metrics[tool]["errors"].get("total_errors", 0)
                        if "errors" in analysis_result.tools_metrics[tool] else 0
                        for tool in tool_names
                    ]

                    plt.figure(figsize=(10, 6))
                    bars = plt.bar(tool_names, error_counts)
                    plt.title('Errors by Tool')
                    plt.xlabel('Tool')
                    plt.ylabel('Error Count')

                    # Add value labels
                    for bar in bars:
                        height = bar.get_height()
                        plt.text(
                            bar.get_x() + bar.get_width() / 2.,
                            height,
                            f'{int(height)}',
                            ha='center',
                            va='bottom'
                        )

                    # Save figure
                    errors_by_tool_path = os.path.join(vis_dir, f"{report_name}_errors_by_tool.png")
                    plt.savefig(errors_by_tool_path, dpi=300, bbox_inches='tight')
                    plt.close()

                    visualization_paths["errors_by_tool"] = errors_by_tool_path

            # Tool comparison
            if self.config.include_tool_comparison and len(analysis_result.tools_metrics) > 1:
                # Tool comparison radar chart
                plt.figure(figsize=(10, 10))

                # Get tool names
                tool_names = list(analysis_result.tools_metrics.keys())

                # Get metrics to compare
                metrics = [
                    "Method Coverage",
                    "Activity Coverage",
                    "MOP Coverage",
                    "Error Rate"
                ]

                # Set up radar chart
                angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
                angles += angles[:1]  # Close the loop

                # Create subplot with polar projection
                ax = plt.subplot(111, polar=True)

                # Set chart properties
                plt.xticks(angles[:-1], metrics)
                ax.set_rlabel_position(0)
                plt.yticks([20, 40, 60, 80, 100], ["20%", "40%", "60%", "80%", "100%"], color="grey", size=8)
                plt.ylim(0, 100)

                # Plot each tool
                for tool in tool_names:
                    tool_data = analysis_result.tools_metrics[tool]

                    # Get coverage values
                    method_coverage = tool_data["coverage"].get("method_coverage", 0)
                    activity_coverage = tool_data["coverage"].get("activity_coverage", 0)
                    mop_coverage = tool_data["coverage"].get("mop_coverage", 0)

                    # Get error rate (invert for radar chart)
                    error_count = tool_data["errors"].get("total_errors", 0) if "errors" in tool_data else 0
                    total_methods = tool_data["coverage"].get("total_methods", 1)
                    error_rate = (error_count / total_methods) * 100 if total_methods > 0 else 0
                    error_rate_inverted = max(0, 100 - min(error_rate * 10, 100))  # Invert and scale

                    # Create values list
                    values = [
                        method_coverage,
                        activity_coverage,
                        mop_coverage,
                        error_rate_inverted
                    ]
                    values += values[:1]  # Close the loop

                    # Plot values
                    ax.plot(angles, values, label=tool, linewidth=2)
                    ax.fill(angles, values, alpha=0.1)

                # Add legend
                plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
                plt.title('Tool Comparison')

                # Save figure
                tool_comparison_path = os.path.join(vis_dir, f"{report_name}_tool_comparison.png")
                plt.savefig(tool_comparison_path, dpi=300, bbox_inches='tight')
                plt.close()

                visualization_paths["tool_comparison"] = tool_comparison_path

        except ImportError:
            self.logger.warning("Matplotlib not available, skipping visualizations")
        except Exception as e:
            self.logger.error(f"Error generating visualizations: {e}")

        return visualization_paths

    def _generate_html_report(self,
                              analysis_result: AnalysisResult,
                              output_dir: str,
                              report_name: str) -> str:
        """
        Generate HTML report for analysis results.
        
        Args:
            analysis_result: Analysis result to report on
            output_dir: Directory to write report to
            report_name: Base name for report files
            
        Returns:
            Path to the generated HTML report
        """
        html_path = os.path.join(output_dir, f"{report_name}.html")

        # Generate report title
        title = self.config.custom_title or f"Experiment Report: {analysis_result.experiment_id}"

        # Generate report content
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3, h4 {{
                    color: #2c3e50;
                }}
                .summary-box {{
                    background-color: #f8f9fa;
                    border-radius: 5px;
                    padding: 15px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .summary-box h3 {{
                    margin-top: 0;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 8px;
                }}
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                }}
                .metric-card {{
                    background-color: white;
                    border-radius: 5px;
                    padding: 15px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .metric-card h4 {{
                    margin-top: 0;
                    color: #3498db;
                }}
                .metric-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .visualization {{
                    margin: 20px 0;
                    text-align: center;
                }}
                .visualization img {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 5px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 10px;
                    border-top: 1px solid #ddd;
                    font-size: 0.9em;
                    color: #777;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <p>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            
            <!-- Summary Section -->
            <div class="summary-box">
                <h3>Experiment Summary</h3>
                <p><strong>Experiment ID:</strong> {analysis_result.experiment_id}</p>
                <p><strong>Total Tasks:</strong> {analysis_result.task_count}</p>
                <p><strong>Completed Tasks:</strong> {analysis_result.completed_task_count}</p>
                <p><strong>Failed Tasks:</strong> {analysis_result.failed_task_count}</p>
                <p><strong>Timestamp:</strong> {analysis_result.timestamp}</p>
            </div>
            
            <!-- Key Metrics Section -->
            <h2>Key Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <h4>Method Coverage</h4>
                    <div class="metric-value">{analysis_result.coverage.method_coverage:.2f}%</div>
                    <p>{analysis_result.coverage.called_methods} / {analysis_result.coverage.total_methods} methods</p>
                </div>
                <div class="metric-card">
                    <h4>Activity Coverage</h4>
                    <div class="metric-value">{analysis_result.coverage.activity_coverage:.2f}%</div>
                    <p>{analysis_result.coverage.visited_activities} / {analysis_result.coverage.total_activities} activities</p>
                </div>
                <div class="metric-card">
                    <h4>MOP Method Coverage</h4>
                    <div class="metric-value">{analysis_result.coverage.mop_method_coverage:.2f}%</div>
                    <p>{analysis_result.coverage.called_mop_methods} / {analysis_result.coverage.total_mop_methods} MOP methods</p>
                </div>
                <div class="metric-card">
                    <h4>Total Errors</h4>
                    <div class="metric-value">{analysis_result.errors.total_errors}</div>
                    <p>{analysis_result.errors.unique_errors} unique errors</p>
                </div>
            </div>
        """

        # Add visualizations if available
        vis_dir = os.path.join(output_dir, "visualizations")
        if os.path.exists(vis_dir):
            vis_files = [
                f for f in os.listdir(vis_dir)
                if f.startswith(report_name) and f.endswith(".png")
            ]

            if vis_files:
                html_content += """
                <h2>Visualizations</h2>
                <div class="visualizations">
                """

                for vis_file in vis_files:
                    vis_path = f"visualizations/{vis_file}"
                    vis_title = vis_file.replace(f"{report_name}_", "").replace(".png", "").replace("_", " ").title()

                    html_content += f"""
                    <div class="visualization">
                        <h3>{vis_title}</h3>
                        <img src="{vis_path}" alt="{vis_title}">
                    </div>
                    """

                html_content += "</div>"

        # Add tool comparison section
        if analysis_result.tools_metrics:
            html_content += """
            <h2>Tool Comparison</h2>
            <table>
                <tr>
                    <th>Tool</th>
                    <th>Tasks</th>
                    <th>Method Coverage</th>
                    <th>Activity Coverage</th>
                    <th>MOP Coverage</th>
                    <th>Errors</th>
                </tr>
            """

            for tool_name, tool_data in analysis_result.tools_metrics.items():
                method_coverage = tool_data["coverage"].get("method_coverage", 0)
                activity_coverage = tool_data["coverage"].get("activity_coverage", 0)
                mop_coverage = tool_data["coverage"].get("mop_coverage", 0)
                errors = tool_data["errors"].get("total_errors", 0) if "errors" in tool_data else 0
                task_count = tool_data.get("task_count", 0)

                html_content += f"""
                <tr>
                    <td>{tool_name}</td>
                    <td>{task_count}</td>
                    <td>{method_coverage:.2f}%</td>
                    <td>{activity_coverage:.2f}%</td>
                    <td>{mop_coverage:.2f}%</td>
                    <td>{errors}</td>
                </tr>
                """

            html_content += "</table>"

        # Add app comparison section
        if analysis_result.apps_metrics:
            html_content += """
            <h2>App Comparison</h2>
            <table>
                <tr>
                    <th>App</th>
                    <th>Tasks</th>
                    <th>Method Coverage</th>
                    <th>Activity Coverage</th>
                    <th>MOP Coverage</th>
                    <th>Errors</th>
                </tr>
            """

            for app_name, app_data in analysis_result.apps_metrics.items():
                method_coverage = app_data["coverage"].get("method_coverage", 0)
                activity_coverage = app_data["coverage"].get("activity_coverage", 0)
                mop_coverage = app_data["coverage"].get("mop_coverage", 0)
                errors = app_data["errors"].get("total_errors", 0) if "errors" in app_data else 0
                task_count = app_data.get("task_count", 0)

                html_content += f"""
                <tr>
                    <td>{app_name}</td>
                    <td>{task_count}</td>
                    <td>{method_coverage:.2f}%</td>
                    <td>{activity_coverage:.2f}%</td>
                    <td>{mop_coverage:.2f}%</td>
                    <td>{errors}</td>
                </tr>
                """

            html_content += "</table>"

        # Add error details section
        if analysis_result.errors.total_errors > 0:
            html_content += """
            <h2>Error Details</h2>
            <div class="summary-box">
                <h3>Error Summary</h3>
                <p><strong>Total Errors:</strong> {0}</p>
                <p><strong>Unique Errors:</strong> {1}</p>
                <p><strong>App Crashes:</strong> {2}</p>
                <p><strong>Tool Crashes:</strong> {3}</p>
                <p><strong>System Crashes:</strong> {4}</p>
            </div>
            """.format(
                analysis_result.errors.total_errors,
                analysis_result.errors.unique_errors,
                analysis_result.errors.app_crash_count,
                analysis_result.errors.tool_crash_count,
                analysis_result.errors.system_crash_count
            )

            # Add error categories table
            if analysis_result.errors.error_categories:
                html_content += """
                <h3>Error Categories</h3>
                <table>
                    <tr>
                        <th>Category</th>
                        <th>Count</th>
                    </tr>
                """

                for category, count in sorted(
                        analysis_result.errors.error_categories.items(),
                        key=lambda x: x[1],
                        reverse=True
                ):
                    html_content += f"""
                    <tr>
                        <td>{category}</td>
                        <td>{count}</td>
                    </tr>
                    """

                html_content += "</table>"

        # Add footer
        html_content += """
            <div class="footer">
                <p>Report generated by RVAndroid Results Analysis System</p>
            </div>
        </body>
        </html>
        """

        # Write HTML to file
        with open(html_path, 'w') as f:
            f.write(html_content)

        self.logger.info(f"HTML report generated at {html_path}")

        return html_path


def generate_reports(analysis_results: Union[AnalysisResult, Dict[str, Any]],
                     output_dir: str,
                     experiment_id: Optional[str] = None,
                     config: Optional[ReportConfig] = None) -> Dict[str, str]:
    """
    Generate reports from analysis results.
    
    This is a convenience function that creates a ReportGenerator instance
    and calls its generate_report method.
    
    Args:
        analysis_results: Analysis results or dictionary data
        output_dir: Directory to write reports to
        experiment_id: Optional experiment ID
        config: Optional report configuration
        
    Returns:
        Dictionary mapping report types to file paths
    """
    generator = ReportGenerator(config)

    # Convert dictionary to AnalysisResult if needed
    if isinstance(analysis_results, dict):
        # Check if this is a proper analysis result dictionary
        if "experiment_id" in analysis_results:
            analysis_result = AnalysisResult.from_dict(analysis_results)
        else:
            # Create a new AnalysisResult
            experiment_id = experiment_id or f"experiment_{int(time.time())}"
            analysis_result = AnalysisResult(
                experiment_id=experiment_id,
                coverage=CoverageMetrics(),
                performance=PerformanceMetrics(),
                errors=ErrorMetrics()
            )
    else:
        analysis_result = analysis_results

    # Generate reports
    report_path = generator.generate_report(analysis_result, output_dir)

    return {"html": report_path}
