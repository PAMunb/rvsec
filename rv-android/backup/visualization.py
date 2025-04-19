"""
Visualization module for generating charts and reports from analysis results.

This module provides utilities for creating visualizations from both standard
and integrated analysis results, focusing on coverage, security, and performance
metrics.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Union

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

from rvandroid.analysis.results.analysis import AnalysisResult, CoverageMetrics
from rvandroid.analysis.results.integrated_metrics import IntegratedAnalysisResult


class ResultVisualizer:
    """
    Visualizer for experiment results.
    
    Creates charts and visualizations from analysis results,
    supporting both standard and integrated result formats.
    
    ### Architectural Decisions:
    - Separates visualization logic from data processing
    - Provides modular, reusable chart generation
    - Supports both interactive and file output
    - Handles both standard and integrated result formats
    
    ### Role in the System:
    - Generates visual representations of results
    - Creates standardized charts for reporting
    - Facilitates result interpretation and analysis
    - Enables comparison across tools and applications
    """
    
    def __init__(self, output_dir: str):
        """
        Initialize the visualizer.
        
        Args:
            output_dir: Directory to save visualizations
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Configure visualization style
        sns.set_style("whitegrid")
        sns.set_context("paper")
        
    def visualize_standard_results(self, result: AnalysisResult) -> Dict[str, str]:
        """
        Generate visualizations for standard analysis results.
        
        Args:
            result: Standard analysis result
            
        Returns:
            Dictionary mapping chart names to file paths
        """
        chart_files = {}
        
        # Generate coverage chart
        coverage_chart = os.path.join(self.output_dir, "coverage_chart.png")
        self._create_coverage_chart(result, coverage_chart)
        chart_files["coverage"] = coverage_chart
        
        # Generate tools comparison chart
        tools_chart = os.path.join(self.output_dir, "tools_comparison.png")
        self._create_tools_comparison(result, tools_chart)
        chart_files["tools"] = tools_chart
        
        # Generate error chart if errors exist
        if result.errors.total_errors > 0:
            error_chart = os.path.join(self.output_dir, "error_chart.png")
            self._create_error_chart(result, error_chart)
            chart_files["errors"] = error_chart
        
        return chart_files
    
    def visualize_integrated_results(self, results_file: str) -> Dict[str, str]:
        """
        Generate visualizations for integrated analysis results.
        
        Args:
            results_file: Path to integrated results JSON file
            
        Returns:
            Dictionary mapping chart names to file paths
        """
        # Load integrated results
        with open(results_file, 'r') as f:
            data = json.load(f)
        
        chart_files = {}
        
        # Extract app data
        apps_data = data.get("apps", {})
        
        if not apps_data:
            self.logger.warning("No app data found in integrated results")
            return chart_files
        
        # Generate static metrics chart
        static_chart = os.path.join(self.output_dir, "static_metrics_chart.png")
        self._create_static_metrics_chart(apps_data, static_chart)
        chart_files["static"] = static_chart
        
        # Generate integrated coverage chart
        coverage_chart = os.path.join(self.output_dir, "integrated_coverage_chart.png")
        self._create_integrated_coverage_chart(apps_data, coverage_chart)
        chart_files["coverage"] = coverage_chart
        
        # Generate security metrics chart
        security_chart = os.path.join(self.output_dir, "security_metrics_chart.png")
        self._create_security_metrics_chart(apps_data, security_chart)
        chart_files["security"] = security_chart
        
        # Generate comparison dashboard
        dashboard_chart = os.path.join(self.output_dir, "metrics_dashboard.png")
        self._create_metrics_dashboard(apps_data, dashboard_chart)
        chart_files["dashboard"] = dashboard_chart
        
        return chart_files
    
    def generate_report(self, 
                        results_file: str, 
                        output_file: Optional[str] = None, 
                        report_type: str = "integrated") -> str:
        """
        Generate an HTML report from analysis results.
        
        Args:
            results_file: Path to results JSON file
            output_file: Path for output HTML file (optional)
            report_type: Type of report to generate ("standard" or "integrated")
            
        Returns:
            Path to the generated HTML report
        """
        # Load results
        with open(results_file, 'r') as f:
            data = json.load(f)
        
        # Determine output file
        if output_file is None:
            file_base = os.path.splitext(os.path.basename(results_file))[0]
            output_file = os.path.join(self.output_dir, f"{file_base}_report.html")
        
        # Generate visualizations
        chart_files = {}
        if report_type == "integrated":
            chart_files = self.visualize_integrated_results(results_file)
        else:
            # For standard results, convert to AnalysisResult first
            if "experiment_id" in data:
                from rvandroid.analysis.results.analysis import AnalysisResult
                result = AnalysisResult.from_dict(data)
                chart_files = self.visualize_standard_results(result)
        
        # Generate HTML report
        self._generate_html_report(data, chart_files, output_file, report_type)
        
        return output_file
    
    def _create_coverage_chart(self, result: AnalysisResult, output_file: str) -> None:
        """
        Create a coverage chart for standard analysis results.
        
        Args:
            result: Analysis result
            output_file: Output file path
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Extract coverage metrics
        coverage = result.coverage
        
        # Create bar data
        categories = ['Method', 'Activity', 'MOP Method']
        values = [
            coverage.method_coverage,
            coverage.activity_coverage,
            coverage.mop_method_coverage
        ]
        
        # Create bar chart
        bars = ax.bar(categories, values, color=sns.color_palette("muted"))
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height + 1,
                f'{height:.1f}%',
                ha='center',
                va='bottom'
            )
        
        # Set chart properties
        ax.set_ylim(0, 100)
        ax.set_ylabel('Coverage (%)')
        ax.set_title('Coverage Metrics')
        
        # Add counts as annotations
        ax.annotate(
            f'Methods: {coverage.called_methods}/{coverage.total_methods}',
            xy=(0, 5),
            xytext=(0, -15),
            textcoords='offset points',
            ha='center'
        )
        ax.annotate(
            f'Activities: {coverage.visited_activities}/{coverage.total_activities}',
            xy=(1, 5),
            xytext=(0, -15),
            textcoords='offset points',
            ha='center'
        )
        ax.annotate(
            f'MOP Methods: {coverage.called_mop_methods}/{coverage.total_mop_methods}',
            xy=(2, 5),
            xytext=(0, -15),
            textcoords='offset points',
            ha='center'
        )
        
        # Save chart
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_tools_comparison(self, result: AnalysisResult, output_file: str) -> None:
        """
        Create a tools comparison chart.
        
        Args:
            result: Analysis result
            output_file: Output file path
        """
        # Extract tools data
        tools_data = result.tools_metrics
        
        if not tools_data:
            self.logger.warning("No tools data found for comparison chart")
            return
        
        # Prepare data for chart
        tool_names = list(tools_data.keys())
        method_coverage = []
        activity_coverage = []
        mop_coverage = []
        error_counts = []
        
        for tool, data in tools_data.items():
            coverage_data = data.get('coverage', {})
            method_coverage.append(coverage_data.get('method_coverage', 0))
            activity_coverage.append(coverage_data.get('activity_coverage', 0))
            mop_coverage.append(coverage_data.get('mop_coverage', 0))
            error_counts.append(data.get('errors', 0))
        
        # Create the figure with multiple subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Coverage comparison chart
        x = np.arange(len(tool_names))
        width = 0.25
        
        ax1.bar(x - width, method_coverage, width, label='Method Coverage')
        ax1.bar(x, activity_coverage, width, label='Activity Coverage')
        ax1.bar(x + width, mop_coverage, width, label='MOP Coverage')
        
        ax1.set_ylabel('Coverage (%)')
        ax1.set_title('Coverage by Tool')
        ax1.set_xticks(x)
        ax1.set_xticklabels(tool_names, rotation=45, ha="right")
        ax1.set_ylim(0, 100)
        ax1.legend()
        
        # Error counts chart
        ax2.bar(tool_names, error_counts, color='salmon')
        ax2.set_ylabel('Error Count')
        ax2.set_title('Errors by Tool')
        ax2.set_xticklabels(tool_names, rotation=45, ha="right")
        
        # Add values on top of bars
        for i, v in enumerate(error_counts):
            ax2.text(i, v + 0.5, str(v), ha='center')
        
        # Save chart
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_error_chart(self, result: AnalysisResult, output_file: str) -> None:
        """
        Create an error distribution chart.
        
        Args:
            result: Analysis result
            output_file: Output file path
        """
        # Extract error data
        error_categories = result.errors.error_categories
        
        if not error_categories:
            self.logger.warning("No error categories found for error chart")
            return
        
        # Prepare data for chart
        categories = list(error_categories.keys())
        counts = list(error_categories.values())
        
        # Sort by count
        sorted_indices = np.argsort(counts)[::-1]  # Descending order
        categories = [categories[i] for i in sorted_indices]
        counts = [counts[i] for i in sorted_indices]
        
        # Create the chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create horizontal bar chart for better readability with many categories
        bars = ax.barh(categories, counts, color='salmon')
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.text(
                width + 0.5,
                bar.get_y() + bar.get_height() / 2.,
                f'{width}',
                ha='left',
                va='center'
            )
        
        # Set chart properties
        ax.set_xlabel('Count')
        ax.set_title('Error Distribution by Category')
        
        # Add total errors annotation
        ax.annotate(
            f'Total Errors: {result.errors.total_errors}',
            xy=(0.95, 0.05),
            xycoords='axes fraction',
            ha='right',
            va='bottom',
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8)
        )
        
        # Save chart
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_static_metrics_chart(self, apps_data: Dict[str, Any], output_file: str) -> None:
        """
        Create a static metrics comparison chart for multiple apps.
        
        Args:
            apps_data: Dictionary of app data from integrated results
            output_file: Output file path
        """
        # Prepare data for chart
        app_names = []
        classes = []
        methods = []
        activities = []
        mop_methods = []
        
        for app_id, app_data in apps_data.items():
            static = app_data.get('static_metrics', {})
            
            app_names.append(app_id)
            classes.append(static.get('total_classes', 0))
            methods.append(static.get('total_methods', 0) / 10)  # Scale down for better visualization
            activities.append(static.get('total_activities', 0))
            mop_methods.append(static.get('total_mop_methods', 0))
        
        # Create the chart
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Create grouped bar chart
        x = np.arange(len(app_names))
        width = 0.2
        
        ax.bar(x - 1.5*width, classes, width, label='Classes')
        ax.bar(x - 0.5*width, methods, width, label='Methods (x10)')
        ax.bar(x + 0.5*width, activities, width, label='Activities')
        ax.bar(x + 1.5*width, mop_methods, width, label='MOP Methods')
        
        # Set chart properties
        ax.set_ylabel('Count')
        ax.set_title('Static Metrics by Application')
        ax.set_xticks(x)
        ax.set_xticklabels(app_names, rotation=45, ha='right')
        ax.legend()
        
        # Save chart
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_integrated_coverage_chart(self, apps_data: Dict[str, Any], output_file: str) -> None:
        """
        Create an integrated coverage chart for multiple apps.
        
        Args:
            apps_data: Dictionary of app data from integrated results
            output_file: Output file path
        """
        # Prepare data for chart
        app_names = []
        method_coverage = []
        activity_coverage = []
        mop_coverage = []
        security_coverage = []
        
        for app_id, app_data in apps_data.items():
            coverage = app_data.get('coverage', {})
            
            app_names.append(app_id)
            method_coverage.append(coverage.get('method_coverage', 0))
            activity_coverage.append(coverage.get('activity_coverage', 0))
            mop_coverage.append(coverage.get('mop_method_coverage', 0))
            security_coverage.append(coverage.get('security_method_coverage', 0))
        
        # Create the chart
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Create grouped bar chart
        x = np.arange(len(app_names))
        width = 0.2
        
        ax.bar(x - 1.5*width, method_coverage, width, label='Method Coverage')
        ax.bar(x - 0.5*width, activity_coverage, width, label='Activity Coverage')
        ax.bar(x + 0.5*width, mop_coverage, width, label='MOP Method Coverage')
        ax.bar(x + 1.5*width, security_coverage, width, label='Security Method Coverage')
        
        # Set chart properties
        ax.set_ylabel('Coverage (%)')
        ax.set_title('Coverage Metrics by Application')
        ax.set_xticks(x)
        ax.set_xticklabels(app_names, rotation=45, ha='right')
        ax.set_ylim(0, 100)
        ax.legend()
        
        # Save chart
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_security_metrics_chart(self, apps_data: Dict[str, Any], output_file: str) -> None:
        """
        Create a security metrics chart for multiple apps.
        
        Args:
            apps_data: Dictionary of app data from integrated results
            output_file: Output file path
        """
        # Prepare data for chart
        app_names = []
        mop_specs = []
        mop_triggers = []
        potential_vulnerabilities = []
        detected_vulnerabilities = []
        
        for app_id, app_data in apps_data.items():
            security = app_data.get('security', {})
            
            app_names.append(app_id)
            mop_specs.append(security.get('mop_specifications', 0))
            mop_triggers.append(security.get('mop_triggers', 0))
            potential_vulnerabilities.append(security.get('potential_vulnerabilities', 0))
            detected_vulnerabilities.append(security.get('detected_vulnerabilities', 0))
        
        # Create the chart
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Create grouped bar chart
        x = np.arange(len(app_names))
        width = 0.2
        
        ax.bar(x - 1.5*width, mop_specs, width, label='MOP Specifications')
        ax.bar(x - 0.5*width, potential_vulnerabilities, width, label='Potential Vulnerabilities')
        ax.bar(x + 0.5*width, mop_triggers, width, label='MOP Triggers')
        ax.bar(x + 1.5*width, detected_vulnerabilities, width, label='Detected Vulnerabilities')
        
        # Set chart properties
        ax.set_ylabel('Count')
        ax.set_title('Security Metrics by Application')
        ax.set_xticks(x)
        ax.set_xticklabels(app_names, rotation=45, ha='right')
        ax.legend()
        
        # Save chart
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_metrics_dashboard(self, apps_data: Dict[str, Any], output_file: str) -> None:
        """
        Create a comprehensive metrics dashboard for multiple apps.
        
        Args:
            apps_data: Dictionary of app data from integrated results
            output_file: Output file path
        """
        # Create a dashboard with multiple charts
        fig, axes = plt.subplots(2, 2, figsize=(18, 14))
        
        # App selection
        # For simplicity, limit to first 5 apps if there are many
        app_ids = list(apps_data.keys())
        if len(app_ids) > 5:
            app_ids = app_ids[:5]
            
        app_data_subset = {app_id: apps_data[app_id] for app_id in app_ids}
        
        # 1. Static metrics (top left)
        ax1 = axes[0, 0]
        self._plot_static_metrics(app_data_subset, ax1)
        
        # 2. Coverage metrics (top right)
        ax2 = axes[0, 1]
        self._plot_coverage_metrics(app_data_subset, ax2)
        
        # 3. Security metrics (bottom left)
        ax3 = axes[1, 0]
        self._plot_security_metrics(app_data_subset, ax3)
        
        # 4. Vulnerability chart (bottom right)
        ax4 = axes[1, 1]
        self._plot_vulnerability_chart(app_data_subset, ax4)
        
        # Set overall title
        fig.suptitle('Application Analysis Dashboard', fontsize=16)
        
        # Save dashboard
        plt.tight_layout(rect=[0, 0, 1, 0.97])  # Adjust for suptitle
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _plot_static_metrics(self, apps_data: Dict[str, Any], ax: plt.Axes) -> None:
        """Plot static metrics on the given axes."""
        # Prepare data
        app_names = []
        classes = []
        methods = []
        activities = []
        
        for app_id, app_data in apps_data.items():
            static = app_data.get('static_metrics', {})
            
            app_names.append(app_id)
            classes.append(static.get('total_classes', 0))
            methods.append(static.get('total_methods', 0) / 10)  # Scale down
            activities.append(static.get('total_activities', 0))
        
        # Create chart
        x = np.arange(len(app_names))
        width = 0.25
        
        ax.bar(x - width, classes, width, label='Classes')
        ax.bar(x, methods, width, label='Methods (x10)')
        ax.bar(x + width, activities, width, label='Activities')
        
        # Set properties
        ax.set_ylabel('Count')
        ax.set_title('Static Metrics')
        ax.set_xticks(x)
        ax.set_xticklabels(app_names, rotation=45, ha='right')
        ax.legend()
    
    def _plot_coverage_metrics(self, apps_data: Dict[str, Any], ax: plt.Axes) -> None:
        """Plot coverage metrics on the given axes."""
        # Prepare data
        app_names = []
        method_coverage = []
        activity_coverage = []
        mop_coverage = []
        
        for app_id, app_data in apps_data.items():
            coverage = app_data.get('coverage', {})
            
            app_names.append(app_id)
            method_coverage.append(coverage.get('method_coverage', 0))
            activity_coverage.append(coverage.get('activity_coverage', 0))
            mop_coverage.append(coverage.get('mop_method_coverage', 0))
        
        # Create chart
        x = np.arange(len(app_names))
        width = 0.25
        
        ax.bar(x - width, method_coverage, width, label='Method')
        ax.bar(x, activity_coverage, width, label='Activity')
        ax.bar(x + width, mop_coverage, width, label='MOP Method')
        
        # Set properties
        ax.set_ylabel('Coverage (%)')
        ax.set_title('Coverage Metrics')
        ax.set_xticks(x)
        ax.set_xticklabels(app_names, rotation=45, ha='right')
        ax.set_ylim(0, 100)
        ax.legend()
    
    def _plot_security_metrics(self, apps_data: Dict[str, Any], ax: plt.Axes) -> None:
        """Plot security metrics on the given axes."""
        # Prepare data
        app_names = []
        mop_specs = []
        mop_triggers = []
        vulnerabilities = []
        
        for app_id, app_data in apps_data.items():
            security = app_data.get('security', {})
            
            app_names.append(app_id)
            mop_specs.append(security.get('mop_specifications', 0))
            mop_triggers.append(security.get('mop_triggers', 0))
            vulnerabilities.append(security.get('detected_vulnerabilities', 0))
        
        # Create chart
        x = np.arange(len(app_names))
        width = 0.25
        
        ax.bar(x - width, mop_specs, width, label='MOP Specs')
        ax.bar(x, mop_triggers, width, label='MOP Triggers')
        ax.bar(x + width, vulnerabilities, width, label='Vulnerabilities')
        
        # Set properties
        ax.set_ylabel('Count')
        ax.set_title('Security Metrics')
        ax.set_xticks(x)
        ax.set_xticklabels(app_names, rotation=45, ha='right')
        ax.legend()
    
    def _plot_vulnerability_chart(self, apps_data: Dict[str, Any], ax: plt.Axes) -> None:
        """Plot vulnerability categories on the given axes."""
        # Collect all vulnerability categories
        all_categories = {}
        
        for app_id, app_data in apps_data.items():
            security = app_data.get('security', {})
            categories = security.get('vulnerability_categories', {})
            
            for category, count in categories.items():
                if category in all_categories:
                    all_categories[category] += count
                else:
                    all_categories[category] = count
        
        # If no categories found, show message
        if not all_categories:
            ax.text(0.5, 0.5, 'No vulnerability data available',
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=ax.transAxes)
            ax.set_title('Vulnerability Categories')
            return
        
        # Sort categories by count
        categories = sorted(all_categories.items(), key=lambda x: x[1], reverse=True)
        labels = [c[0] for c in categories]
        sizes = [c[1] for c in categories]
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=labels, 
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 9}
        )
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.axis('equal')
        ax.set_title('Vulnerability Categories')
    
    def _generate_html_report(self, 
                              data: Dict[str, Any], 
                              chart_files: Dict[str, str], 
                              output_file: str,
                              report_type: str) -> None:
        """
        Generate an HTML report with charts and tables.
        
        Args:
            data: Results data
            chart_files: Dictionary of chart files
            output_file: Output file path
            report_type: Type of report ("standard" or "integrated")
        """
        # Prepare HTML content
        html_content = []
        
        # Add header
        html_content.append("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Analysis Results Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }
                h1, h2, h3 { color: #2c3e50; }
                .container { max-width: 1200px; margin: 0 auto; }
                .chart-container { margin: 20px 0; text-align: center; }
                .chart { max-width: 100%; height: auto; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background-color: #f2f2f2; }
                tr:hover { background-color: #f5f5f5; }
                .summary-card { background-color: #f8f9fa; border-radius: 5px; padding: 15px; margin: 10px 0; }
                .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 20px 0; }
                .metric-item { background-color: #f0f7ff; padding: 15px; border-radius: 5px; text-align: center; }
                .metric-value { font-size: 24px; font-weight: bold; color: #0066cc; }
                .metric-label { font-size: 14px; color: #666; }
                .section { margin: 30px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Analysis Results Report</h1>
        """)
        
        # Add timestamp
        timestamp = data.get("timestamp", "")
        html_content.append(f"<p>Generated on: {timestamp}</p>")
        
        # Add summary section
        html_content.append("""
                <div class="section">
                    <h2>Summary</h2>
                    <div class="summary-card">
        """)
        
        # Generate summary based on report type
        if report_type == "integrated":
            app_count = len(data.get("apps", {}))
            html_content.append(f"""
                        <div class="metric-grid">
                            <div class="metric-item">
                                <div class="metric-value">{app_count}</div>
                                <div class="metric-label">Applications</div>
                            </div>
            """)
            
            # Add additional summary metrics if available
            html_content.append("""
                        </div>
            """)
        else:
            # Standard report summary
            if "summary" in data:
                summary = data["summary"]
                html_content.append(f"""
                        <div class="metric-grid">
                            <div class="metric-item">
                                <div class="metric-value">{summary.get('total_apps', 0)}</div>
                                <div class="metric-label">Applications</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-value">{summary.get('total_tasks', 0)}</div>
                                <div class="metric-label">Tasks</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-value">{summary.get('avg_method_coverage', 0):.1f}%</div>
                                <div class="metric-label">Avg Method Coverage</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-value">{summary.get('total_errors', 0)}</div>
                                <div class="metric-label">Errors</div>
                            </div>
                        </div>
                """)
        
        html_content.append("""
                    </div>
                </div>
        """)
        
        # Add charts section
        html_content.append("""
                <div class="section">
                    <h2>Visualizations</h2>
        """)
        
        # Add each chart
        for chart_name, chart_file in chart_files.items():
            # Convert to relative path for HTML
            rel_path = os.path.relpath(chart_file, os.path.dirname(output_file))
            
            # Format chart title
            title = chart_name.replace('_', ' ').title()
            
            html_content.append(f"""
                    <div class="chart-container">
                        <h3>{title} Chart</h3>
                        <img class="chart" src="{rel_path}" alt="{title} Chart">
                    </div>
            """)
        
        html_content.append("""
                </div>
        """)
        
        # Add detailed results section for integrated report
        if report_type == "integrated":
            html_content.append("""
                <div class="section">
                    <h2>Detailed Results</h2>
            """)
            
            # Add table for each app
            for app_id, app_data in data.get("apps", {}).items():
                html_content.append(f"""
                    <h3>Application: {app_id}</h3>
                    
                    <h4>Static Metrics</h4>
                    <table>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                """)
                
                # Add static metrics rows
                static = app_data.get("static_metrics", {})
                for metric, value in static.items():
                    if metric != "security_methods":  # Skip complex nested data
                        html_content.append(f"""
                        <tr>
                            <td>{metric.replace('_', ' ').title()}</td>
                            <td>{value}</td>
                        </tr>
                        """)
                
                html_content.append("""
                    </table>
                    
                    <h4>Coverage Metrics</h4>
                    <table>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                """)
                
                # Add coverage metrics rows
                coverage = app_data.get("coverage", {})
                for metric, value in coverage.items():
                    if not isinstance(value, list):  # Skip list fields
                        formatted_value = f"{value:.2f}%" if "coverage" in metric.lower() else value
                        html_content.append(f"""
                        <tr>
                            <td>{metric.replace('_', ' ').title()}</td>
                            <td>{formatted_value}</td>
                        </tr>
                        """)
                
                html_content.append("""
                    </table>
                    
                    <h4>Security Metrics</h4>
                    <table>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                """)
                
                # Add security metrics rows
                security = app_data.get("security", {})
                for metric, value in security.items():
                    if not isinstance(value, (list, dict, set)):  # Skip complex data
                        html_content.append(f"""
                        <tr>
                            <td>{metric.replace('_', ' ').title()}</td>
                            <td>{value}</td>
                        </tr>
                        """)
                
                html_content.append("""
                    </table>
                """)
            
            html_content.append("""
                </div>
            """)
        
        # Close the HTML
        html_content.append("""
            </div>
        </body>
        </html>
        """)
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write("".join(html_content))


# Convenience function for creating visualizations
def create_visualizations(results_file: str, output_dir: str, report_type: str = "integrated") -> str:
    """
    Create visualizations and report from results file.
    
    Args:
        results_file: Path to results JSON file
        output_dir: Directory to save visualizations
        report_type: Type of report to generate ("standard" or "integrated")
        
    Returns:
        Path to the generated HTML report
    """
    visualizer = ResultVisualizer(output_dir)
    report_path = visualizer.generate_report(results_file, report_type=report_type)
    return report_path