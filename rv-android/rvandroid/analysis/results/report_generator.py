# rvandroid/analysis/results/report_generator.py
"""
Report generation module for experiment results.
"""
import json
import os
from typing import Dict, Any, Optional

import matplotlib.pyplot as plt
import numpy as np

from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ReportGenerator:
    """
    Generates reports and visualizations from experiment results.

    ### Architectural Decisions:
    - Separates report generation from results processing
    - Provides focused visualization capabilities
    - Supports multiple output formats

    ### Role in the System:
    - Creates visual representations of experiment results
    - Generates summary reports for analysis
    - Provides insights into experiment outcomes
    """

    def __init__(self):
        """Initialize the report generator."""
        self.logger = LoggingManager.get_instance().get_logger(
            'analysis.results.report_generator',
            {CONTEXT_COMPONENT: 'ReportGenerator'}
        )

    def generate_reports(self, results_dir: str, results_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Generate reports from experiment results.

        Args:
            results_dir: Directory containing results
            results_data: Optional pre-loaded results data

        Returns:
            Success status
        """
        try:
            self.logger.info(f"Generating reports for {results_dir}")

            # Load results data if not provided
            if results_data is None:
                results_file = os.path.join(results_dir, "results_analysis.json")
                if not os.path.exists(results_file):
                    self.logger.warning(f"Results file not found: {results_file}")
                    return False

                with open(results_file, 'r') as f:
                    results_data = json.load(f)

            # Create charts directory
            charts_dir = os.path.join(results_dir, "charts")
            os.makedirs(charts_dir, exist_ok=True)

            # Generate tool comparison chart
            self._generate_tool_comparison(results_data, charts_dir)

            # Generate app coverage chart
            self._generate_app_coverage(results_data, charts_dir)

            # Generate error summary
            self._generate_error_summary(results_data, charts_dir)

            self.logger.info(f"Reports generated in {charts_dir}")
            return True

        except Exception as e:
            self.logger.error(f"Error generating reports: {e}", exc_info=True)
            return False

    def _generate_tool_comparison(self, results: Dict[str, Any], charts_dir: str) -> None:
        """
        Generate tool comparison chart.

        Args:
            results: Results data
            charts_dir: Output directory
        """
        try:
            tools_data = results.get("tools", {})

            if not tools_data:
                return

            tool_names = list(tools_data.keys())
            method_coverage = [tools_data[t]["method_coverage"] for t in tool_names]
            activity_coverage = [tools_data[t]["activity_coverage"] for t in tool_names]
            mop_coverage = [tools_data[t]["mop_coverage"] for t in tool_names]

            x = np.arange(len(tool_names))
            width = 0.25

            fig, ax = plt.figure(figsize=(12, 8)), plt.axes()

            ax.bar(x - width, method_coverage, width, label='Method Coverage (%)')
            ax.bar(x, activity_coverage, width, label='Activity Coverage (%)')
            ax.bar(x + width, mop_coverage, width, label='MOP Coverage (%)')

            ax.set_ylabel('Coverage (%)')
            ax.set_title('Coverage by Tool')
            ax.set_xticks(x)
            ax.set_xticklabels(tool_names)
            ax.legend()

            plt.savefig(os.path.join(charts_dir, "tool_comparison.png"))
            plt.close()

        except Exception as e:
            self.logger.error(f"Error generating tool comparison chart: {e}", exc_info=True)

    def _generate_app_coverage(self, results: Dict[str, Any], charts_dir: str) -> None:
        """
        Generate app coverage chart.

        Args:
            results: Results data
            charts_dir: Output directory
        """
        try:
            apps_data = results.get("apps", {})

            if not apps_data:
                return

            app_names = list(apps_data.keys())
            method_coverage = [apps_data[a]["summary"]["method_coverage"] for a in app_names]
            activity_coverage = [apps_data[a]["summary"]["activity_coverage"] for a in app_names]
            mop_coverage = [apps_data[a]["summary"]["mop_coverage"] for a in app_names]

            # Truncate long app names
            app_names = [a[:15] + '...' if len(a) > 15 else a for a in app_names]

            fig, ax = plt.figure(figsize=(14, 8)), plt.axes()

            ax.barh(np.arange(len(app_names)) - 0.3, method_coverage, 0.2, label='Method Coverage (%)')
            ax.barh(np.arange(len(app_names)), activity_coverage, 0.2, label='Activity Coverage (%)')
            ax.barh(np.arange(len(app_names)) + 0.3, mop_coverage, 0.2, label='MOP Coverage (%)')

            ax.set_xlabel('Coverage (%)')
            ax.set_title('Coverage by App')
            ax.set_yticks(np.arange(len(app_names)))
            ax.set_yticklabels(app_names)
            ax.legend()

            plt.savefig(os.path.join(charts_dir, "app_coverage.png"))
            plt.close()

        except Exception as e:
            self.logger.error(f"Error generating app coverage chart: {e}", exc_info=True)

    def _generate_error_summary(self, results: Dict[str, Any], charts_dir: str) -> None:
        """
        Generate error summary chart.

        Args:
            results: Results data
            charts_dir: Output directory
        """
        try:
            tools_data = results.get("tools", {})

            if not tools_data:
                return

            tool_names = list(tools_data.keys())
            errors = [tools_data[t]["errors"] for t in tool_names]
            tasks = [tools_data[t]["tasks"] for t in tool_names]

            fig, ax = plt.figure(figsize=(10, 6)), plt.axes()

            ax.bar(tool_names, errors)

            ax.set_ylabel('Error Count')
            ax.set_title('Errors by Tool')
            plt.xticks(rotation=45)

            # Add error rate labels
            for i, (e, t) in enumerate(zip(errors, tasks)):
                if t > 0:
                    rate = (e / t)
                    ax.text(i, e + 0.5, f"{rate:.2f}/task", ha='center')

            plt.tight_layout()
            plt.savefig(os.path.join(charts_dir, "error_summary.png"))
            plt.close()

        except Exception as e:
            self.logger.error(f"Error generating error summary chart: {e}", exc_info=True)
