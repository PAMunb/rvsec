# rvandroid/analysis/results/processor.py
"""
Results processing module for experiment outcomes.
"""
import json
import os
from typing import Dict, Any

from rvandroid.domain.coverage import LogcatRepository
from rvandroid.parser.log.logcat_parser import parse_logcat_file
from rvandroid.util.logging.constants import CONTEXT_COMPONENT, CONTEXT_PHASE
from rvandroid.util.logging.manager import LoggingManager


class ResultsProcessor:
    """
    Processes experiment results to generate summary data.

    ### Architectural Decisions:
    - Separates results processing from analysis
    - Provides a focused API for results data extraction
    - Supports batch processing of experiment results

    ### Role in the System:
    - Aggregates results from multiple experiment tasks
    - Generates standardized result summaries
    - Provides consolidated metrics across experiments
    """

    def __init__(self):
        """Initialize the results processor."""
        self.logger = LoggingManager.get_instance().get_logger(
            'analysis.results.processor',
            {CONTEXT_COMPONENT: 'ResultsProcessor'}
        )

    def process_results(self, results_dir: str) -> Dict[str, Any]:
        """
        Process experiment results from a directory.

        Args:
            results_dir: Directory containing results

        Returns:
            Dictionary with processed results
        """
        self.logger.info(f"Processing results from {results_dir}")

        # Results structure
        results = {
            "apps": {},
            "tools": {},
            "summary": {
                "total_apps": 0,
                "total_tasks": 0,
                "total_errors": 0,
                "avg_method_coverage": 0,
                "avg_activity_coverage": 0,
                "avg_mop_coverage": 0
            }
        }

        try:
            # Process app directories
            app_dirs = [d for d in os.listdir(results_dir)
                        if os.path.isdir(os.path.join(results_dir, d)) and d != "logs" and d != "charts"]

            results["summary"]["total_apps"] = len(app_dirs)
            total_method_coverage = 0
            total_activity_coverage = 0
            total_mop_coverage = 0
            total_tasks = 0
            total_errors = 0

            # Process each app directory
            for app_dir in app_dirs:
                app_path = os.path.join(results_dir, app_dir)
                app_results = self.process_app_results(app_path)

                results["apps"][app_dir] = app_results

                # Update tool statistics
                for tool, tool_data in app_results.get("tools", {}).items():
                    if tool not in results["tools"]:
                        results["tools"][tool] = {
                            "tasks": 0,
                            "method_coverage": 0,
                            "activity_coverage": 0,
                            "mop_coverage": 0,
                            "errors": 0
                        }

                    results["tools"][tool]["tasks"] += tool_data.get("tasks", 0)
                    results["tools"][tool]["method_coverage"] += tool_data.get("method_coverage", 0) * tool_data.get(
                        "tasks", 0)
                    results["tools"][tool]["activity_coverage"] += tool_data.get("activity_coverage",
                                                                                 0) * tool_data.get(
                        "tasks", 0)
                    results["tools"][tool]["mop_coverage"] += tool_data.get("mop_coverage", 0) * tool_data.get("tasks",
                                                                                                               0)
                    results["tools"][tool]["errors"] += tool_data.get("errors", 0)

                # Update summary statistics
                task_count = app_results.get("summary", {}).get("tasks", 0)
                total_tasks += task_count
                total_method_coverage += app_results.get("summary", {}).get("method_coverage", 0) * task_count
                total_activity_coverage += app_results.get("summary", {}).get("activity_coverage", 0) * task_count
                total_mop_coverage += app_results.get("summary", {}).get("mop_coverage", 0) * task_count
                total_errors += app_results.get("summary", {}).get("errors", 0)

            # Calculate averages for tools
            for tool, tool_data in results["tools"].items():
                tool_tasks = tool_data["tasks"]
                if tool_tasks > 0:
                    tool_data["method_coverage"] /= tool_tasks
                    tool_data["activity_coverage"] /= tool_tasks
                    tool_data["mop_coverage"] /= tool_tasks

            # Update summary
            results["summary"]["total_tasks"] = total_tasks
            results["summary"]["total_errors"] = total_errors

            if total_tasks > 0:
                results["summary"]["avg_method_coverage"] = total_method_coverage / total_tasks
                results["summary"]["avg_activity_coverage"] = total_activity_coverage / total_tasks
                results["summary"]["avg_mop_coverage"] = total_mop_coverage / total_tasks

            # Save results to file
            results_file = os.path.join(results_dir, "results_analysis.json")
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)

            self.logger.info(f"Results analysis saved to {results_file}")

            return results

        except Exception as e:
            self.logger.error(f"Error processing results: {e}", exc_info=True)
            return results

    def process_app_results(self, app_dir: str) -> Dict[str, Any]:
        """
        Process results for a single app.

        Args:
            app_dir: Directory containing app results

        Returns:
            Dictionary with app results
        """
        logger = LoggingManager.get_instance().get_logger(
            'analysis.results.processor',
            {
                CONTEXT_COMPONENT: 'ResultsProcessor',
                CONTEXT_PHASE: 'process_app_results',
                'app_dir': app_dir
            }
        )

        app_results = {
            "tools": {},
            "summary": {
                "tasks": 0,
                "method_coverage": 0,
                "activity_coverage": 0,
                "mop_coverage": 0,
                "errors": 0
            }
        }

        try:
            # Find logcat files
            logcat_files = [f for f in os.listdir(app_dir) if f.endswith(".logcat")]

            if not logcat_files:
                logger.warning(f"No logcat files found in {app_dir}")
                return app_results

            app_results["summary"]["tasks"] = len(logcat_files)
            total_method_coverage = 0
            total_activity_coverage = 0
            total_mop_coverage = 0
            total_errors = 0

            # Process each logcat file
            for logcat_file in logcat_files:
                # Parse tool name from filename (format: app__rep__timeout__tool.logcat)
                parts = logcat_file.split("__")
                tool_name = parts[-1].split(".")[0] if len(parts) >= 4 else "unknown"

                # Process logcat file using standardized repository
                repository = self._process_logcat_file(os.path.join(app_dir, logcat_file))

                # Calculate metrics directly from repository
                metrics = repository.calculate_metrics().to_dict()

                # Update tool statistics
                if tool_name not in app_results["tools"]:
                    app_results["tools"][tool_name] = {
                        "tasks": 0,
                        "method_coverage": 0,
                        "activity_coverage": 0,
                        "mop_coverage": 0,
                        "errors": 0
                    }

                app_results["tools"][tool_name]["tasks"] += 1
                app_results["tools"][tool_name]["method_coverage"] += metrics["method_coverage"]
                app_results["tools"][tool_name]["activity_coverage"] += metrics["activity_coverage"]
                app_results["tools"][tool_name]["mop_coverage"] += metrics["mop_method_coverage"]
                app_results["tools"][tool_name]["errors"] += metrics["unique_errors"]

                # Update totals
                total_method_coverage += metrics["method_coverage"]
                total_activity_coverage += metrics["activity_coverage"]
                total_mop_coverage += metrics["mop_method_coverage"]
                total_errors += metrics["unique_errors"]

            # Calculate averages for tools
            for tool, tool_data in app_results["tools"].items():
                tool_tasks = tool_data["tasks"]
                if tool_tasks > 0:
                    tool_data["method_coverage"] /= tool_tasks
                    tool_data["activity_coverage"] /= tool_tasks
                    tool_data["mop_coverage"] /= tool_tasks

            # Update summary
            task_count = app_results["summary"]["tasks"]
            if task_count > 0:
                app_results["summary"]["method_coverage"] = total_method_coverage / task_count
                app_results["summary"]["activity_coverage"] = total_activity_coverage / task_count
                app_results["summary"]["mop_coverage"] = total_mop_coverage / task_count
                app_results["summary"]["errors"] = total_errors

        except Exception as e:
            logger.error(f"Error processing app results: {e}", exc_info=True)

        return app_results

    def _process_logcat_file(self, logcat_file: str) -> LogcatRepository:
        """
        Process a logcat file and return a repository.

        Args:
            logcat_file: Path to logcat file

        Returns:
            LogcatRepository with parsed data
        """
        try:
            # Use the standard parser
            return parse_logcat_file(logcat_file)
        except Exception as e:
            self.logger.warning(f"Error parsing logcat file {logcat_file}: {e}")

            # Return empty repository
            return LogcatRepository()
