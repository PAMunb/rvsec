import json
import os
import time
from datetime import datetime
from typing import Dict

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np


class PerformanceVisualizer:
    """
    Tool for visualizing performance metrics from rv-android.
    Creates charts and reports based on metrics data.
    """

    def __init__(self):
        """Initialize the visualizer."""
        # Import here to avoid circular imports
        from rvandroid.util.logging_manager import LoggingManager
        self.logger = LoggingManager.get_instance().get_logger('performance_visualizer')

    def generate_timing_summary(self, output_dir: str, file_prefix: str = "timing_summary"):
        """
        Generate a summary chart of timing metrics.

        Args:
            output_dir: Directory to save the chart
            file_prefix: Prefix for the output file

        Returns:
            Path to the generated chart
        """
        from rvandroid.util.performance_monitor import PerformanceMonitor
        performance_monitor = PerformanceMonitor.get_instance()

        # Get metrics related to timing
        timing_metrics = [m for m in performance_monitor.metrics if m.unit == "s"]

        if not timing_metrics:
            self.logger.warning("No timing metrics available for visualization")
            return None

        # Group metrics by name
        grouped_metrics = {}
        for metric in timing_metrics:
            if metric.name not in grouped_metrics:
                grouped_metrics[metric.name] = []
            grouped_metrics[metric.name].append(metric.value)

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Create box plot for timing metrics
        fig, ax = plt.subplots(figsize=(12, 8))
        data = []
        labels = []

        for name, values in grouped_metrics.items():
            if len(values) > 1:  # Only include metrics with multiple values
                data.append(values)
                # Format name for readability
                readable_name = name.replace("_", " ").title()
                labels.append(f"{readable_name} (n={len(values)})")

        if not data:
            self.logger.warning("Not enough data for visualization")
            return None

        # Sort by median value
        medians = [np.median(d) for d in data]
        sorted_indices = np.argsort(medians)
        data = [data[i] for i in sorted_indices]
        labels = [labels[i] for i in sorted_indices]

        # Create box plot
        ax.boxplot(data, vert=False, patch_artist=True)
        ax.set_yticklabels(labels)
        ax.set_xlabel('Time (seconds)')
        ax.set_title('Timing Metrics Summary')
        ax.grid(axis='x', linestyle='--', alpha=0.7)

        # Format x-axis with better time units
        ax.xaxis.set_major_formatter(lambda x, pos: f"{x:.2f}s")

        # Tight layout
        plt.tight_layout()

        # Save figure
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_file = os.path.join(output_dir, f"{file_prefix}_{timestamp}.png")
        plt.savefig(output_file, dpi=100)
        plt.close(fig)

        self.logger.info(f"Timing summary chart saved to {output_file}")
        return output_file

    def generate_llm_performance_chart(self, output_dir: str, file_prefix: str = "llm_performance"):
        """
        Generate a chart showing LLM performance metrics.

        Args:
            output_dir: Directory to save the chart
            file_prefix: Prefix for the output file

        Returns:
            Path to the generated chart
        """
        from rvandroid.util.performance_monitor import PerformanceMonitor
        performance_monitor = PerformanceMonitor.get_instance()

        # Get LLM-related metrics
        llm_call_metrics = [m for m in performance_monitor.metrics if m.name == "llm_call"]
        prompt_length_metrics = [m for m in performance_monitor.metrics if m.name == "prompt_length_user"]
        response_length_metrics = [m for m in performance_monitor.metrics if m.name == "llm_response_length"]

        if not llm_call_metrics or not prompt_length_metrics or not response_length_metrics:
            self.logger.warning("Not enough LLM metrics for visualization")
            return None

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Create figure with multiple subplots
        fig, axes = plt.subplots(3, 1, figsize=(12, 12), sharex=True)

        # Sort metrics by timestamp
        llm_call_metrics.sort(key=lambda m: m.timestamp)
        prompt_length_metrics.sort(key=lambda m: m.timestamp)
        response_length_metrics.sort(key=lambda m: m.timestamp)

        # Extract data
        timestamps = [datetime.fromtimestamp(m.timestamp) for m in llm_call_metrics]
        call_times = [m.value for m in llm_call_metrics]
        prompt_lengths = [m.value / 1000 for m in prompt_length_metrics]  # Convert to KB
        response_lengths = [m.value / 1000 for m in response_length_metrics]  # Convert to KB

        # Plot LLM call times
        axes[0].plot(timestamps, call_times, 'o-', markersize=4)
        axes[0].set_ylabel('Time (seconds)')
        axes[0].set_title('LLM Call Time')
        axes[0].grid(True, linestyle='--', alpha=0.7)

        # Plot prompt lengths
        axes[1].plot(timestamps, prompt_lengths, 'o-', markersize=4, color='green')
        axes[1].set_ylabel('Length (KB)')
        axes[1].set_title('User Prompt Length')
        axes[1].grid(True, linestyle='--', alpha=0.7)

        # Plot response lengths
        axes[2].plot(timestamps, response_lengths, 'o-', markersize=4, color='red')
        axes[2].set_ylabel('Length (KB)')
        axes[2].set_title('LLM Response Length')
        axes[2].grid(True, linestyle='--', alpha=0.7)

        # Format x-axis
        axes[2].set_xlabel('Time')
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())

        # Add correlation annotation
        correlation = np.corrcoef(prompt_lengths, call_times)[0, 1]
        axes[0].annotate(f"Correlation with prompt length: {correlation:.2f}",
                         xy=(0.05, 0.95), xycoords='axes fraction',
                         fontsize=10, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))

        # Tight layout
        plt.tight_layout()
        fig.autofmt_xdate()

        # Save figure
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_file = os.path.join(output_dir, f"{file_prefix}_{timestamp}.png")
        plt.savefig(output_file, dpi=100)
        plt.close(fig)

        self.logger.info(f"LLM performance chart saved to {output_file}")
        return output_file

    def generate_coverage_report(self, coverage_data: Dict, output_dir: str, file_prefix: str = "coverage_report"):
        """
        Generate a coverage report visualization.

        Args:
            coverage_data: Coverage data from results analysis
            output_dir: Directory to save the chart
            file_prefix: Prefix for the output file

        Returns:
            Path to the generated chart
        """
        if not coverage_data:
            self.logger.warning("No coverage data available for visualization")
            return None

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Extract APK names and coverage metrics
        apks = []
        activity_coverage = []
        method_coverage = []
        jca_method_coverage = []

        for apk_name, data in coverage_data.items():
            if 'SUMMARY' in data:
                summary = data['SUMMARY']
                apks.append(apk_name)
                activity_coverage.append(summary.get('activities_coverage', 0))
                method_coverage.append(summary.get('method_coverage', 0))
                jca_method_coverage.append(summary.get('methods_jca_reachable_coverage', 0))

        if not apks:
            self.logger.warning("No valid coverage data for visualization")
            return None

        # Create figure with bar chart
        fig, ax = plt.subplots(figsize=(12, 8))

        # Set width of bars
        barWidth = 0.25

        # Set positions of bars on X axis
        r1 = np.arange(len(apks))
        r2 = [x + barWidth for x in r1]
        r3 = [x + barWidth for x in r2]

        # Create bars
        ax.bar(r1, activity_coverage, width=barWidth, edgecolor='grey', label='Activity Coverage')
        ax.bar(r2, method_coverage, width=barWidth, edgecolor='grey', label='Method Coverage')
        ax.bar(r3, jca_method_coverage, width=barWidth, edgecolor='grey', label='JCA Method Coverage')

        # Add labels
        ax.set_xlabel('Applications', fontweight='bold')
        ax.set_ylabel('Coverage (%)', fontweight='bold')
        ax.set_title('Coverage Metrics by Application')
        ax.set_xticks([r + barWidth for r in range(len(apks))])

        # Shorten long APK names
        short_names = [name[:20] + '...' if len(name) > 20 else name for name in apks]
        ax.set_xticklabels(short_names, rotation=45, ha='right')

        # Create legend
        ax.legend()

        # Add grid
        ax.grid(axis='y', linestyle='--', alpha=0.7)

        # Add values on top of bars
        for i, v in enumerate(activity_coverage):
            ax.text(r1[i], v + 1, f"{v:.1f}%", ha='center')
        for i, v in enumerate(method_coverage):
            ax.text(r2[i], v + 1, f"{v:.1f}%", ha='center')
        for i, v in enumerate(jca_method_coverage):
            ax.text(r3[i], v + 1, f"{v:.1f}%", ha='center')

        # Tight layout
        plt.tight_layout()

        # Save figure
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_file = os.path.join(output_dir, f"{file_prefix}_{timestamp}.png")
        plt.savefig(output_file, dpi=100)
        plt.close(fig)

        self.logger.info(f"Coverage report chart saved to {output_file}")
        return output_file

    def generate_errors_report(self, results_data: Dict, output_dir: str, file_prefix: str = "errors_report"):
        """
        Generate an errors report visualization.

        Args:
            results_data: Results data from results analysis
            output_dir: Directory to save the chart
            file_prefix: Prefix for the output file

        Returns:
            Path to the generated chart
        """
        if not results_data:
            self.logger.warning("No results data available for visualization")
            return None

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Extract error counts by APK and tool
        error_data = {}
        for apk_name, apk_data in results_data.items():
            if 'REPETITIONS' in apk_data:
                for rep_id, rep_data in apk_data['REPETITIONS'].items():
                    if 'TIMEOUTS' in rep_data:
                        for timeout_id, timeout_data in rep_data['TIMEOUTS'].items():
                            if 'TOOLS' in timeout_data:
                                for tool_name, tool_data in timeout_data['TOOLS'].items():
                                    if 'SUMMARY' in tool_data and 'RVSEC_ERRORS_COUNT' in tool_data['SUMMARY']:
                                        key = f"{apk_name}/{tool_name}"
                                        if key not in error_data:
                                            error_data[key] = []
                                        error_data[key].append(tool_data['SUMMARY']['RVSEC_ERRORS_COUNT'])

        if not error_data:
            self.logger.warning("No error data found for visualization")
            return None

        # Calculate average error count for each APK/tool combination
        avg_errors = {}
        for key, counts in error_data.items():
            avg_errors[key] = sum(counts) / len(counts)

        # Sort by average error count
        sorted_items = sorted(avg_errors.items(), key=lambda x: x[1], reverse=True)

        # Extract labels and values
        labels = [item[0] for item in sorted_items[:15]]  # Show top 15
        values = [item[1] for item in sorted_items[:15]]

        # Create figure with bar chart
        fig, ax = plt.subplots(figsize=(12, 8))

        # Create bars
        bars = ax.barh(labels, values, color='red', alpha=0.7)

        # Add labels
        ax.set_xlabel('Average Number of Errors', fontweight='bold')
        ax.set_ylabel('Application/Tool', fontweight='bold')
        ax.set_title('Average Number of RVSEC Errors by Application/Tool')

        # Add grid
        ax.grid(axis='x', linestyle='--', alpha=0.7)

        # Add values on bars
        for i, bar in enumerate(bars):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                    f"{values[i]:.1f}", va='center')

        # Tight layout
        plt.tight_layout()

        # Save figure
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_file = os.path.join(output_dir, f"{file_prefix}_{timestamp}.png")
        plt.savefig(output_file, dpi=100)
        plt.close(fig)

        self.logger.info(f"Errors report chart saved to {output_file}")
        return output_file

    def generate_performance_dashboard(self, results_dir: str):
        """
        Generate a complete performance dashboard with multiple charts.

        Args:
            results_dir: Path to results directory

        Returns:
            Path to dashboard directory
        """
        # Create dashboard directory
        dashboard_dir = os.path.join(results_dir, "dashboard")
        os.makedirs(dashboard_dir, exist_ok=True)

        # Generate performance metrics charts
        self.generate_timing_summary(dashboard_dir)
        self.generate_llm_performance_chart(dashboard_dir)

        # Load results data if available
        results_file = os.path.join(results_dir, "results_analysis.json")
        if os.path.exists(results_file):
            try:
                with open(results_file, 'r') as f:
                    results_data = json.load(f)

                # Generate coverage and errors reports
                self.generate_coverage_report(results_data, dashboard_dir)
                self.generate_errors_report(results_data, dashboard_dir)
            except Exception as e:
                self.logger.error(f"Error loading or processing results data: {e}")

        # Generate diagnostic report
        try:
            from rvandroid.util.diagnostics import DiagnosticTool
            diagnostic_tool = DiagnosticTool()
            report = diagnostic_tool.generate_report()
            report_path = os.path.join(dashboard_dir, "diagnostic_report.json")
            report.save_to_file(report_path)
            self.logger.info(f"Diagnostic report saved to {report_path}")
        except Exception as e:
            self.logger.error(f"Error generating diagnostic report: {e}")

        # Generate HTML index
        self.generate_dashboard_index(dashboard_dir)

        return dashboard_dir

    def generate_dashboard_index(self, dashboard_dir: str):
        """
        Generate an HTML index for the dashboard.

        Args:
            dashboard_dir: Dashboard directory

        Returns:
            Path to index file
        """
        # Get list of generated charts
        chart_files = [f for f in os.listdir(dashboard_dir) if f.endswith('.png')]

        # Create HTML content
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>RV-Android Performance Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #2c3e50; }
                .chart-container { margin-bottom: 30px; }
                img { max-width: 100%; border: 1px solid #ddd; }
                .timestamp { color: #7f8c8d; font-size: 0.8em; }
            </style>
        </head>
        <body>
            <h1>RV-Android Performance Dashboard</h1>
            <p class="timestamp">Generated on: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        """

        # Add each chart
        for chart_file in sorted(chart_files):
            chart_name = chart_file.split('_')[0].title()
            timestamp = chart_file.split('_')[-1].split('.')[0]
            timestamp_formatted = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[9:11]}:{timestamp[11:13]}:{timestamp[13:15]}"

            html_content += f"""
            <div class="chart-container">
                <h2>{chart_name} Report</h2>
                <p class="timestamp">Generated: {timestamp_formatted}</p>
                <img src="{chart_file}" alt="{chart_name} Chart">
            </div>
            """

        # Check for diagnostic report
        diagnostic_report_path = os.path.join(dashboard_dir, "diagnostic_report.json")
        if os.path.exists(diagnostic_report_path):
            try:
                with open(diagnostic_report_path, 'r') as f:
                    report_data = json.load(f)

                # Add system info section
                html_content += """
                <div class="chart-container">
                    <h2>System Information</h2>
                    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
                        <tr><th>Property</th><th>Value</th></tr>
                """

                for key, value in report_data.get("system_info", {}).items():
                    html_content += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"

                html_content += """
                    </table>
                </div>
                """

                # Add component status section
                html_content += """
                <div class="chart-container">
                    <h2>Component Status</h2>
                    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
                        <tr><th>Component</th><th>Status</th></tr>
                """

                for key, value in report_data.get("components_status", {}).items():
                    status = "OK" if value else "Failed"
                    color = "green" if value else "red"
                    html_content += f'<tr><td>{key.replace("_", " ").title()}</td><td style="color: {color};">{status}</td></tr>'

                html_content += """
                    </table>
                </div>
                """

                # Add errors section if any
                errors = report_data.get("errors", [])
                if errors:
                    html_content += """
                    <div class="chart-container">
                        <h2>Errors</h2>
                        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
                            <tr><th>Component</th><th>Error</th></tr>
                    """

                    for error in errors:
                        html_content += f'<tr><td>{error.get("component", "unknown")}</td><td>{error.get("error", "unknown")}</td></tr>'

                    html_content += """
                        </table>
                    </div>
                    """

            except Exception as e:
                html_content += f"<p>Error loading diagnostic report: {e}</p>"

        # Close HTML
        html_content += """
        </body>
        </html>
        """

        # Write HTML file
        index_path = os.path.join(dashboard_dir, "index.html")
        with open(index_path, 'w') as f:
            f.write(html_content)

        self.logger.info(f"Dashboard index generated at {index_path}")
        return index_path

    def generate_coverage_comparison_chart(self, coverage_report: Dict, output_dir: str,
                                           file_prefix: str = "coverage_comparison"):
        """
        Generate a comparative chart for coverage metrics across tools and apps.

        Args:
            coverage_report: Coverage report from ExecutionManager.get_coverage_report()
            output_dir: Directory to save the chart
            file_prefix: Prefix for the output file

        Returns:
            Path to the generated chart
        """
        if not coverage_report or "tasks" not in coverage_report:
            self.logger.warning("No coverage report data available for visualization")
            return None

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Group data by app and tool
        app_tool_data = {}
        for task_key, task_data in coverage_report["tasks"].items():
            app_name = task_data["apk_name"]
            tool_name = task_data["tool_name"]

            if app_name not in app_tool_data:
                app_tool_data[app_name] = {}

            if tool_name not in app_tool_data[app_name]:
                app_tool_data[app_name][tool_name] = []

            app_tool_data[app_name][tool_name].append(task_data)

        # Calculate averages for each app/tool combination
        avg_data = []
        for app_name, tools in app_tool_data.items():
            for tool_name, tasks in tools.items():
                if not tasks:
                    continue

                avg_method = sum(t["method_coverage"] for t in tasks) / len(tasks)
                avg_activity = sum(t["activities_coverage"] for t in tasks) / len(tasks)
                avg_mop = sum(t["mop_coverage"] for t in tasks) / len(tasks)
                total_errors = sum(t["errors"] for t in tasks)

                avg_data.append({
                    "app_name": app_name,
                    "tool_name": tool_name,
                    "avg_method_coverage": avg_method,
                    "avg_activities_coverage": avg_activity,
                    "avg_mop_coverage": avg_mop,
                    "total_errors": total_errors
                })

        if not avg_data:
            self.logger.warning("No data available to visualize")
            return None

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        axes = axes.flatten()

        # List of tools and apps for grouping
        all_tools = sorted(set(d["tool_name"] for d in avg_data))
        all_apps = sorted(set(d["app_name"] for d in avg_data))

        # Colors for tools
        tool_colors = plt.cm.tab10(np.linspace(0, 1, len(all_tools)))

        # 1. Method coverage by tool for each app
        ax = axes[0]
        x = np.arange(len(all_apps))
        width = 0.8 / len(all_tools)

        for i, tool in enumerate(all_tools):
            tool_data = [d for d in avg_data if d["tool_name"] == tool]
            # Map to ensure all apps are represented
            values = []
            for app in all_apps:
                app_data = next((d for d in tool_data if d["app_name"] == app), None)
                values.append(app_data["avg_method_coverage"] if app_data else 0)

            ax.bar(x + i * width - width * len(all_tools) / 2 + width / 2, values, width,
                   label=tool, color=tool_colors[i], alpha=0.7)

        ax.set_ylabel("Method Coverage (%)")
        ax.set_title("Method Coverage by Tool")
        ax.set_xticks(x)
        ax.set_xticklabels([name[:15] + '...' if len(name) > 15 else name for name in all_apps], rotation=45,
                           ha='right')
        ax.legend(title="Tool")
        ax.grid(axis='y', linestyle='--', alpha=0.7)

        # 2. Activity coverage by tool for each app
        ax = axes[1]
        for i, tool in enumerate(all_tools):
            tool_data = [d for d in avg_data if d["tool_name"] == tool]
            values = []
            for app in all_apps:
                app_data = next((d for d in tool_data if d["app_name"] == app), None)
                values.append(app_data["avg_activities_coverage"] if app_data else 0)

            ax.bar(x + i * width - width * len(all_tools) / 2 + width / 2, values, width,
                   label=tool, color=tool_colors[i], alpha=0.7)

        ax.set_ylabel("Activity Coverage (%)")
        ax.set_title("Activity Coverage by Tool")
        ax.set_xticks(x)
        ax.set_xticklabels([name[:15] + '...' if len(name) > 15 else name for name in all_apps], rotation=45,
                           ha='right')
        ax.legend(title="Tool")
        ax.grid(axis='y', linestyle='--', alpha=0.7)

        # 3. MOP methods coverage by tool for each app
        ax = axes[2]
        for i, tool in enumerate(all_tools):
            tool_data = [d for d in avg_data if d["tool_name"] == tool]
            values = []
            for app in all_apps:
                app_data = next((d for d in tool_data if d["app_name"] == app), None)
                values.append(app_data["avg_mop_coverage"] if app_data else 0)

            ax.bar(x + i * width - width * len(all_tools) / 2 + width / 2, values, width,
                   label=tool, color=tool_colors[i], alpha=0.7)

        ax.set_ylabel("MOP Methods Coverage (%)")
        ax.set_title("MOP Methods Coverage by Tool")
        ax.set_xticks(x)
        ax.set_xticklabels([name[:15] + '...' if len(name) > 15 else name for name in all_apps], rotation=45,
                           ha='right')
        ax.legend(title="Tool")
        ax.grid(axis='y', linestyle='--', alpha=0.7)

        # 4. Total errors detected by tool for each app
        ax = axes[3]
        for i, tool in enumerate(all_tools):
            tool_data = [d for d in avg_data if d["tool_name"] == tool]
            values = []
            for app in all_apps:
                app_data = next((d for d in tool_data if d["app_name"] == app), None)
                values.append(app_data["total_errors"] if app_data else 0)

            ax.bar(x + i * width - width * len(all_tools) / 2 + width / 2, values, width,
                   label=tool, color=tool_colors[i], alpha=0.7)

        ax.set_ylabel("Total Errors Detected")
        ax.set_title("Errors Detected by Tool")
        ax.set_xticks(x)
        ax.set_xticklabels([name[:15] + '...' if len(name) > 15 else name for name in all_apps], rotation=45,
                           ha='right')
        ax.legend(title="Tool")
        ax.grid(axis='y', linestyle='--', alpha=0.7)

        # Tight layout
        plt.tight_layout()

        # Save figure
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_file = os.path.join(output_dir, f"{file_prefix}_{timestamp}.png")
        plt.savefig(output_file, dpi=100)
        plt.close(fig)

        self.logger.info(f"Coverage comparison chart saved to {output_file}")
        return output_file
