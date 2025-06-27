# rvandroid/analysis/results/processor.py
"""
Results processing module for experiment outcomes.

Processes experiment data and generates standardized result objects.
Integrates with the unified result system for consistent result handling.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from rv_android_core.domain.log import RvErrorLog
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, CONTEXT_PHASE
from rv_android_core.util.logging.manager import LoggingManager
from rv_experiment.analysis.results.analysis import AnalysisResult, CoverageMetrics, PerformanceMetrics, ErrorMetrics
from rv_experiment.analysis.results.base_result import (
    CoverageResult, ErrorResult
)
from rv_experiment.experiment.workflow.result_manager import ResultManager
from rv_coverage.parser.log.logcat_parser import parse_logcat_file


class ResultsProcessor:
    """
    Processes experiment results to generate standardized result objects.

    ### Architectural Decisions:
    - Separates results processing from analysis
    - Integrates with the unified result system
    - Provides a focused API for results data extraction
    - Supports batch processing of experiment results

    ### Role in the System:
    - Aggregates results from multiple experiment tasks
    - Generates standardized result objects
    - Integrates with ResultManager for result storage
    - Provides consolidated metrics across experiments
    """

    def __init__(self, result_manager: Optional[ResultManager] = None):
        """
        Initialize the results processor.
        
        Args:
            result_manager: Optional result manager instance
        """
        self.logger = LoggingManager.get_instance().get_logger(
            'analysis.results.processor',
            {CONTEXT_COMPONENT: 'ResultsProcessor'}
        )

        # Initialize or use provided result manager
        if result_manager:
            self.result_manager = result_manager
        else:
            # If no result manager provided, we can't create one without proper TaskStorage
            # This should not happen in normal workflow - log a warning
            self.logger.warning("No ResultManager provided - some functionality may be limited")
            self.result_manager = None

        # Store static analysis data for each app
        self.static_data_map = {}

    def set_static_data(self, app_id: str, static_data) -> None:
        """
        Set static analysis data for an app.
        
        Args:
            app_id: App identifier
            static_data: Static analysis data
        """
        self.static_data_map[app_id] = static_data
        self.logger.debug(f"Added static analysis data for {app_id}")

    def process_results(self, results_dir: str, legacy_compat: bool = True) -> Dict[str, Any]:
        """
        Process experiment results from a directory.

        Args:
            results_dir: Directory containing results
            legacy_compat: Whether to generate legacy compatibility outputs

        Returns:
            Dictionary with processed results (legacy format if legacy_compat=True)
        """
        self.logger.info(f"Processing results from {results_dir}")

        # Ensure directory exists
        if not os.path.exists(results_dir):
            self.logger.error(f"Results directory not found: {results_dir}")
            return {}

        try:
            # Process app directories
            app_dirs = [d for d in os.listdir(results_dir)
                        if os.path.isdir(os.path.join(results_dir, d)) and d != "logs" and d != "charts"]

            # First, try to load static data for each app
            self._load_static_data_for_apps(results_dir, app_dirs)

            # Process each app directory and create result objects
            for app_dir in app_dirs:
                app_path = os.path.join(results_dir, app_dir)
                app_id = app_dir

                # Process app results
                self._process_app_directory(app_path, app_id)

            # Generate advanced analysis using the new system
            analysis_results = self._generate_advanced_analysis(results_dir)

            # Save advanced analysis to file
            advanced_results_file = os.path.join(results_dir, "advanced_analysis.json")
            analysis_results.save_to_file(advanced_results_file)
            self.logger.info(f"Advanced analysis saved to {advanced_results_file}")

            # Generate legacy compatibility output if requested
            if legacy_compat:
                legacy_data = self._generate_legacy_output()

                # Save legacy results to file
                results_file = os.path.join(results_dir, "results_analysis.json")
                with open(results_file, 'w') as f:
                    json.dump(legacy_data, f, indent=2)

                self.logger.info(f"Legacy results analysis saved to {results_file}")

                return legacy_data

            # Export result manager data
            export_path = self.result_manager.export_results(
                output_file=os.path.join(results_dir, f"results_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            )

            self.logger.info(f"Results exported to {export_path}")

            # Return manager results with advanced analysis information
            return {
                "export_path": export_path,
                "advanced_analysis_path": advanced_results_file,
                "result_count": sum(
                    len(results)
                    for app_results in self.result_manager.results.values()
                    for results in app_results.values()
                )
            }

        except Exception as e:
            self.logger.error(f"Error processing results: {e}", exc_info=True)
            return {}

    def _load_static_data_for_apps(self, results_dir: str, app_dirs: list) -> None:
        """
        Attempt to load static analysis data for each app from task storage.
        
        Args:
            results_dir: Results directory
            app_dirs: List of app directories
        """
        # Try multiple approaches to load static data
        self._load_from_task_storage(app_dirs)

        # If we don't have static data for any app yet, try loading from static analysis files
        if not self.static_data_map:
            self._load_from_static_files(results_dir, app_dirs)

        # Log status of static data loading
        if self.static_data_map:
            self.logger.info(f"Successfully loaded static data for {len(self.static_data_map)} apps")
        else:
            self.logger.warning("Could not load static analysis data for any app - coverage metrics may be inaccurate")

    def _load_from_task_storage(self, app_dirs: list) -> None:
        """
        Load static data from task storage.
        
        Args:
            app_dirs: List of app directories
        """
        try:
            # If we have a result manager, we can access task storage through it
            if hasattr(self, 'result_manager') and self.result_manager and hasattr(self.result_manager, 'task_storage'):
                task_storage = self.result_manager.task_storage

                # Look for tasks related to this experiment
                for app_id in app_dirs:
                    if hasattr(task_storage, 'get_tasks_by_app_id'):
                        tasks = task_storage.get_tasks_by_app_id(app_id)
                        if tasks:
                            # Get static data from the first task for this app (all tasks should share the same static data)
                            first_task = tasks[0]
                            if hasattr(first_task, 'static_data') and first_task.static_data:
                                self.set_static_data(app_id, first_task.static_data)
                                self.logger.info(f"Loaded static analysis data for {app_id} from task storage")
            else:
                self.logger.debug("No task storage available for loading static data")

        except (ImportError, AttributeError, Exception) as e:
            self.logger.warning(f"Could not load static data from task storage: {e}")

    def _load_from_static_files(self, results_dir: str, app_dirs: list) -> None:
        """
        Try to load static data from static analysis files in the results directory.
        
        Args:
            results_dir: Results directory
            app_dirs: List of app directories
        """
        try:
            from rv_android_core.domain.static import StaticAnalysisData
            from rv_android_core.analysis.static.static_analysis import StaticAnalysisService

            for app_id in app_dirs:
                # Try to find the static analysis file
                app_dir = os.path.join(results_dir, app_id)
                static_file = os.path.join(app_dir, f"{app_id}_static_analysis.json")

                if os.path.exists(static_file):
                    try:
                        service = StaticAnalysisService()
                        static_data = service.load_from_file(static_file)

                        if static_data and hasattr(static_data, 'classes'):
                            self.set_static_data(app_id, static_data)
                            self.logger.info(f"Loaded static analysis data for {app_id} from file: {static_file}")
                    except Exception as e:
                        self.logger.warning(f"Error loading static data from file for {app_id}: {e}")

        except (ImportError, Exception) as e:
            self.logger.warning(f"Could not load static data from files: {e}")

    def _process_app_directory(self, app_dir: str, app_id: str) -> None:
        """
        Process a single app directory.
        
        Args:
            app_dir: App directory path
            app_id: App identifier
        """
        logger = LoggingManager.get_instance().get_logger(
            'analysis.results.processor',
            {
                CONTEXT_COMPONENT: 'ResultsProcessor',
                CONTEXT_PHASE: 'process_app_directory',
                'app_dir': app_dir
            }
        )

        try:
            # Find logcat files
            logcat_files = [f for f in os.listdir(app_dir) if f.endswith(".logcat")]

            if not logcat_files:
                logger.warning(f"No logcat files found in {app_dir}")
                return

            # Process each logcat file and create result objects
            for logcat_file in logcat_files:
                # Parse tool name from filename (format: app__rep__timeout__tool.logcat)
                parts = logcat_file.split("__")
                tool_name = parts[-1].split(".")[0] if len(parts) >= 4 else "unknown"

                # Process logcat file
                self._process_logcat_file(
                    os.path.join(app_dir, logcat_file),
                    app_id=app_id,
                    analyzer_name=tool_name
                )

        except Exception as e:
            logger.error(f"Error processing app directory {app_dir}: {e}", exc_info=True)

    def _process_logcat_file(self, logcat_file: str, app_id: str, analyzer_name: str) -> None:
        """
        Process a logcat file and create result objects.
        
        Args:
            logcat_file: Path to logcat file
            app_id: App identifier
            analyzer_name: Name of the analyzer/tool
        """
        try:
            # Get static analysis data for this app if available
            static_data = self.static_data_map.get(app_id)

            # Try to load static data from app files if we don't have it yet
            if not static_data:
                # Try to find common static analysis file locations
                app_dir = os.path.dirname(logcat_file)
                possible_static_files = [
                    os.path.join(app_dir, f"{app_id}_static_analysis.json"),
                    os.path.join(app_dir, "static_analysis.json"),
                    os.path.join(app_dir, "static_data.json")
                ]

                for static_file in possible_static_files:
                    if os.path.exists(static_file):
                        try:
                            from rv_android_core.analysis.static.static_analysis import StaticAnalysisService
                            service = StaticAnalysisService()
                            static_data = service.load_from_file(static_file)

                            if static_data and hasattr(static_data, 'classes'):
                                self.set_static_data(app_id, static_data)
                                self.logger.info(
                                    f"Loaded static analysis data from file during processing: {static_file}")
                                break
                        except Exception as e:
                            self.logger.debug(f"Failed to load static file {static_file}: {e}")

            # Parse logcat file with static data if available
            repository = parse_logcat_file(logcat_file, static_data)

            # Check if we have valid static data
            if repository.classes:
                self.logger.info(f"Successfully loaded repository with {len(repository.classes)} classes for {app_id}")
            else:
                self.logger.warning(f"No classes found in repository for {app_id} - metrics may be inaccurate")

            # Create coverage result
            metrics = repository.calculate_metrics()
            coverage_result = self._create_coverage_result(metrics, analyzer_name)

            # Add to result manager
            self.result_manager.add_result(coverage_result, app_id)

            # Create error result if errors exist
            if repository.errors:
                error_result = self._create_error_result(repository.errors, analyzer_name)

                # Add to result manager
                self.result_manager.add_result(error_result, app_id)

        except Exception as e:
            self.logger.warning(f"Error processing logcat file {logcat_file}: {e}", exc_info=True)

    def _create_coverage_result(self, metrics, analyzer_name: str) -> CoverageResult:
        """
        Create a coverage result from metrics.
        
        Args:
            metrics: Metrics object or dictionary
            analyzer_name: Name of the analyzer/tool
            
        Returns:
            CoverageResult instance
        """
        # Convert metrics to dictionary if it's not already
        metrics_dict = metrics.to_dict() if hasattr(metrics, "to_dict") else metrics

        # Process methods for detailed result data
        covered_methods = []
        covered_activities = []
        covered_mop_methods = []

        # Extract method lists if possible
        if hasattr(metrics, "repository"):
            repo = metrics.repository

            # Extract methods
            for class_name, class_obj in repo.classes.items():
                is_activity = class_obj.is_activity

                for method_name, method_obj in class_obj.methods.items():
                    if method_obj.called:
                        # Format: class.method
                        method_id = f"{class_name}.{method_name}"
                        covered_methods.append(method_id)

                        # Check if it's an activity method
                        if is_activity:
                            covered_activities.append(method_id)

                        # Check if it's a MOP-related method
                        if method_obj.reaches_mop:
                            covered_mop_methods.append(method_id)

        # Create result with all available data
        result = CoverageResult(
            analyzer_name=analyzer_name,
            timestamp=datetime.now(),

            # Coverage metrics
            method_coverage=metrics_dict.get("method_coverage", 0.0),
            activity_coverage=metrics_dict.get("activity_coverage", 0.0),
            mop_method_coverage=metrics_dict.get("mop_method_coverage", 0.0),

            # Detailed counts
            total_methods=metrics_dict.get("total_methods", 0),
            called_methods=metrics_dict.get("called_methods", 0),
            total_activities=metrics_dict.get("total_activities", 0),
            visited_activities=metrics_dict.get("visited_activities", 0),
            total_mop_methods=metrics_dict.get("total_mop_methods", 0),
            called_mop_methods=metrics_dict.get("called_mop_methods", 0),

            # Lists of covered elements
            covered_methods=covered_methods,
            covered_activities=covered_activities,
            covered_mop_methods=covered_mop_methods
        )

        return result

    def _create_error_result(self, errors: List[RvErrorLog], analyzer_name: str) -> ErrorResult:
        """
        Create an error result from error logs.
        
        Args:
            errors: List of error logs
            analyzer_name: Name of the analyzer/tool
            
        Returns:
            ErrorResult instance
        """
        # Convert errors to dictionaries
        error_dicts = []
        error_types = {}
        error_locations = {}
        unique_messages = set()

        for error in errors:
            # Skip if error is None
            if error is None:
                continue

            # Get basic error info - safely handle different attribute names
            # First try to get error_type (RvErrorLog class uses this)
            error_type = None
            if hasattr(error, 'error_type'):
                error_type = error.error_type
            # Fallback to 'type' attribute if error_type doesn't exist
            elif hasattr(error, 'type'):
                error_type = error.type
            # Final fallback
            if error_type is None:
                error_type = "unknown"

            # Get class and method names - handle different attribute naming conventions
            class_name = None
            if hasattr(error, 'class_full_name'):
                class_name = error.class_full_name
            elif hasattr(error, 'class_name'):
                class_name = error.class_name

            method_name = None
            if hasattr(error, 'method'):
                method_name = error.method
            elif hasattr(error, 'method_name'):
                method_name = error.method_name

            # Construct error location string
            if class_name and method_name:
                error_location = f"{class_name}.{method_name}"
            else:
                error_location = "unknown"

            # Get error message
            error_message = getattr(error, 'message', "") or ""

            # Create error dictionary
            error_dict = {
                "type": error_type,
                "location": error_location,
                "message": error_message,
                "timestamp": error.timestamp.isoformat() if hasattr(error, "timestamp") and error.timestamp else None
            }

            # Add to result
            error_dicts.append(error_dict)
            unique_messages.add(error_message)

            # Update type and location counts
            error_types[error_type] = error_types.get(error_type, 0) + 1
            error_locations[error_location] = error_locations.get(error_location, 0) + 1

        # Create result
        result = ErrorResult(
            analyzer_name=analyzer_name,
            timestamp=datetime.now(),

            # Error metrics
            total_errors=len(error_dicts),
            unique_errors=len(unique_messages),

            # Detailed error information
            error_types=error_types,
            error_locations=error_locations,

            # List of detailed errors
            errors=error_dicts
        )

        return result

    def _generate_advanced_analysis(self, results_dir: str) -> AnalysisResult:
        """
        Generate advanced analysis using the new analysis system.
        
        Args:
            results_dir: Directory containing results
            
        Returns:
            AnalysisResult instance
        """
        # Extract experiment ID from directory name
        experiment_id = os.path.basename(results_dir)

        # Initialize metrics
        coverage_metrics = CoverageMetrics()
        performance_metrics = PerformanceMetrics()
        error_metrics = ErrorMetrics()

        # Initialize tool and app metrics
        tools_metrics = {}
        apps_metrics = {}

        # Note: We directly use self.result_manager.results rather than get_results()

        # Process coverage results
        coverage_results = [
            r for app_results in self.result_manager.results.values()
            for r in app_results.get("coverage", [])
        ]

        # Calculate coverage metrics
        if coverage_results:
            # Initialize totals
            total_methods = 0
            called_methods = 0
            total_activities = 0
            visited_activities = 0
            total_mop_methods = 0
            called_mop_methods = 0

            # Process each result
            for result in coverage_results:
                total_methods += result.total_methods
                called_methods += result.called_methods
                total_activities += result.total_activities
                visited_activities += result.visited_activities
                total_mop_methods += result.total_mop_methods
                called_mop_methods += result.called_mop_methods

                # Process by tool
                tool_name = result.analyzer_name
                # Initialize tool metrics if not present
                if tool_name not in tools_metrics:
                    tools_metrics[tool_name] = {
                        "coverage": {
                            "method_coverage": 0,
                            "activity_coverage": 0,
                            "mop_coverage": 0,
                            "total_methods": 0,
                            "called_methods": 0
                        },
                        "performance": {},
                        "errors": {},
                        "task_count": 0
                    }

                tools_metrics[tool_name]["task_count"] += 1

                # Update tool coverage - ensure all required fields exist
                tool_coverage = tools_metrics[tool_name]["coverage"]

                # Safely access attributes with defaults
                method_coverage = getattr(result, 'method_coverage', 0)
                activity_coverage = getattr(result, 'activity_coverage', 0)
                mop_method_coverage = getattr(result, 'mop_method_coverage', 0)
                total_methods = getattr(result, 'total_methods', 0)
                called_methods = getattr(result, 'called_methods', 0)

                # Update metrics
                tool_coverage["method_coverage"] += method_coverage
                tool_coverage["activity_coverage"] += activity_coverage
                tool_coverage["mop_coverage"] += mop_method_coverage
                tool_coverage["total_methods"] += total_methods
                tool_coverage["called_methods"] += called_methods

                # Process by app
                app_id = next(
                    (app_id for app_id, app_results in self.result_manager.results.items()
                     if "coverage" in app_results and result in app_results["coverage"]),
                    "unknown"
                )

                # Initialize app metrics if not present
                if app_id not in apps_metrics:
                    apps_metrics[app_id] = {
                        "coverage": {
                            "method_coverage": 0,
                            "activity_coverage": 0,
                            "mop_coverage": 0,
                            "total_methods": 0,
                            "called_methods": 0
                        },
                        "performance": {},
                        "errors": {},
                        "task_count": 0
                    }

                apps_metrics[app_id]["task_count"] += 1

                # Update app coverage - use same safety measures as for tools
                app_coverage = apps_metrics[app_id]["coverage"]

                # Reuse values from earlier - already safely accessed with defaults
                app_coverage["method_coverage"] += method_coverage
                app_coverage["activity_coverage"] += activity_coverage
                app_coverage["mop_coverage"] += mop_method_coverage
                app_coverage["total_methods"] += total_methods
                app_coverage["called_methods"] += called_methods

            # Set coverage metrics
            coverage_metrics.total_methods = total_methods
            coverage_metrics.called_methods = called_methods
            coverage_metrics.total_activities = total_activities
            coverage_metrics.visited_activities = visited_activities
            coverage_metrics.total_mop_methods = total_mop_methods
            coverage_metrics.called_mop_methods = called_mop_methods

            # Calculate coverage percentages
            if total_methods > 0:
                coverage_metrics.method_coverage = (called_methods / total_methods) * 100

            if total_activities > 0:
                coverage_metrics.activity_coverage = (visited_activities / total_activities) * 100

            if total_mop_methods > 0:
                coverage_metrics.mop_method_coverage = (called_mop_methods / total_mop_methods) * 100

            # Calculate average tool coverage
            for tool_name, tool_data in tools_metrics.items():
                if tool_data["task_count"] > 0:
                    tool_data["coverage"]["method_coverage"] /= tool_data["task_count"]
                    tool_data["coverage"]["activity_coverage"] /= tool_data["task_count"]
                    tool_data["coverage"]["mop_coverage"] /= tool_data["task_count"]

            # Calculate average app coverage
            for app_id, app_data in apps_metrics.items():
                if app_data["task_count"] > 0:
                    app_data["coverage"]["method_coverage"] /= app_data["task_count"]
                    app_data["coverage"]["activity_coverage"] /= app_data["task_count"]
                    app_data["coverage"]["mop_coverage"] /= app_data["task_count"]

        # Process error results
        error_results = [
            r for app_results in self.result_manager.results.values()
            for r in app_results.get("error", [])
        ]

        # Calculate error metrics
        if error_results:
            # Initialize totals
            overall_total_errors = 0
            unique_error_messages = set()
            error_categories = {}

            # Process each result
            for result in error_results:
                # Make sure we have all needed attributes - doing this before we use them
                result_total_errors = 0
                result_unique_errors = 0
                result_errors = []

                # Safely get attributes from the result object
                if hasattr(result, 'total_errors'):
                    result_total_errors = result.total_errors
                if hasattr(result, 'unique_errors'):
                    result_unique_errors = result.unique_errors
                if hasattr(result, 'errors'):
                    result_errors = result.errors

                # Update overall counts
                overall_total_errors += result_total_errors

                # Add unique errors
                for error in result_errors:
                    error_message = error.get("message", "")
                    unique_error_messages.add(error_message)

                    # Categorize error
                    error_type = error.get("type", "unknown")
                    error_categories[error_type] = error_categories.get(error_type, 0) + 1

                # Process by tool
                tool_name = getattr(result, 'analyzer_name', 'unknown')
                self.logger.debug(f"Processing error metrics for tool: {tool_name}")

                # Make sure the tool exists in the metrics dictionary
                if tool_name not in tools_metrics:
                    # Initialize a complete tool metrics structure with all required fields
                    tools_metrics[tool_name] = {
                        "coverage": {
                            "method_coverage": 0,
                            "activity_coverage": 0,
                            "mop_coverage": 0,
                            "total_methods": 0,
                            "called_methods": 0
                        },
                        "performance": {
                            "execution_time": 0,
                            "cpu_usage": 0,
                            "memory_usage": 0
                        },
                        "errors": {
                            "total_errors": 0,
                            "unique_errors": 0
                        },
                        "task_count": 0
                    }

                # Make triple sure errors dictionary exists and has the right keys
                if "errors" not in tools_metrics[tool_name]:
                    tools_metrics[tool_name]["errors"] = {}

                if "total_errors" not in tools_metrics[tool_name]["errors"]:
                    tools_metrics[tool_name]["errors"]["total_errors"] = 0

                if "unique_errors" not in tools_metrics[tool_name]["errors"]:
                    tools_metrics[tool_name]["errors"]["unique_errors"] = 0

                # Update error metrics - using the values we extracted earlier
                tools_metrics[tool_name]["errors"]["total_errors"] += result_total_errors
                tools_metrics[tool_name]["errors"]["unique_errors"] += result_unique_errors

                # Process by app
                app_id = next(
                    (app_id for app_id, app_results in self.result_manager.results.items()
                     if "error" in app_results and result in app_results["error"]),
                    "unknown"
                )

                self.logger.debug(f"Processing error metrics for app: {app_id}")

                # Make sure the app exists in the metrics dictionary
                if app_id not in apps_metrics:
                    # Initialize a complete app metrics structure with all required fields
                    apps_metrics[app_id] = {
                        "coverage": {
                            "method_coverage": 0,
                            "activity_coverage": 0,
                            "mop_coverage": 0,
                            "total_methods": 0,
                            "called_methods": 0
                        },
                        "performance": {
                            "execution_time": 0,
                            "cpu_usage": 0,
                            "memory_usage": 0
                        },
                        "errors": {
                            "total_errors": 0,
                            "unique_errors": 0
                        },
                        "task_count": 0
                    }

                # Make triple sure errors dictionary exists and has the right keys
                if "errors" not in apps_metrics[app_id]:
                    apps_metrics[app_id]["errors"] = {}

                if "total_errors" not in apps_metrics[app_id]["errors"]:
                    apps_metrics[app_id]["errors"]["total_errors"] = 0

                if "unique_errors" not in apps_metrics[app_id]["errors"]:
                    apps_metrics[app_id]["errors"]["unique_errors"] = 0

                # Update app error metrics using the values we extracted earlier
                apps_metrics[app_id]["errors"]["total_errors"] += result_total_errors
                apps_metrics[app_id]["errors"]["unique_errors"] += result_unique_errors

            # Set error metrics using the overall totals
            error_metrics.total_errors = overall_total_errors
            error_metrics.unique_errors = len(unique_error_messages)
            error_metrics.error_categories = error_categories

            # Count crash types
            error_metrics.app_crash_count = error_categories.get("app_crash", 0)
            error_metrics.tool_crash_count = error_categories.get("tool_crash", 0)
            error_metrics.system_crash_count = error_categories.get("system_crash", 0)

        # Calculate task counts
        task_count = sum(
            1 for app_results in self.result_manager.results.values()
            for result_type in app_results.values()
            for _ in result_type
        )

        completed_task_count = sum(
            1 for app_results in self.result_manager.results.values()
            if "coverage" in app_results
            for _ in app_results["coverage"]
        )

        failed_task_count = sum(
            1 for app_results in self.result_manager.results.values()
            if "error" in app_results
            for _ in app_results["error"]
        )

        # Create analysis result
        analysis_result = AnalysisResult(
            experiment_id=experiment_id,
            coverage=coverage_metrics,
            performance=performance_metrics,
            errors=error_metrics,
            tools_metrics=tools_metrics,
            apps_metrics=apps_metrics,
            task_count=task_count,
            completed_task_count=completed_task_count,
            failed_task_count=failed_task_count
        )

        return analysis_result

    def _generate_legacy_output(self) -> Dict[str, Any]:
        """
        Generate legacy output format for backward compatibility.
        
        Returns:
            Dictionary in legacy format
        """
        legacy_output = {
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

        # Track totals for summary
        app_count = 0
        task_count = 0
        total_method_coverage = 0
        total_activity_coverage = 0
        total_mop_coverage = 0
        total_errors = 0

        # Process each app
        for app_id, app_results in self.result_manager.results.items():
            app_count += 1
            app_data = {
                "tools": {},
                "summary": {
                    "tasks": 0,
                    "method_coverage": 0,
                    "activity_coverage": 0,
                    "mop_coverage": 0,
                    "errors": 0
                }
            }

            # Group results by analyzer/tool
            tools_data = {}

            # Process coverage results
            coverage_results = app_results.get("coverage", [])
            for result in coverage_results:
                analyzer = result.analyzer_name

                # Initialize tool data if needed
                if analyzer not in tools_data:
                    tools_data[analyzer] = {
                        "tasks": 0,
                        "method_coverage": 0,
                        "activity_coverage": 0,
                        "mop_coverage": 0,
                        "errors": 0
                    }

                # Update tool data
                tools_data[analyzer]["tasks"] += 1
                tools_data[analyzer]["method_coverage"] += result.method_coverage
                tools_data[analyzer]["activity_coverage"] += result.activity_coverage
                tools_data[analyzer]["mop_coverage"] += result.mop_method_coverage

                # Update task count
                task_count += 1
                app_data["summary"]["tasks"] += 1

                # Update coverage totals
                total_method_coverage += result.method_coverage
                total_activity_coverage += result.activity_coverage
                total_mop_coverage += result.mop_method_coverage

            # Process error results
            error_results = app_results.get("error", [])
            for result in error_results:
                analyzer = result.analyzer_name

                # Initialize tool data if needed
                if analyzer not in tools_data:
                    tools_data[analyzer] = {
                        "tasks": 0,
                        "method_coverage": 0,
                        "activity_coverage": 0,
                        "mop_coverage": 0,
                        "errors": 0
                    }

                # Update tool data
                tools_data[analyzer]["errors"] += result.unique_errors

                # Update error totals
                total_errors += result.unique_errors
                app_data["summary"]["errors"] += result.unique_errors

            # Calculate averages for tools
            for tool, tool_data in tools_data.items():
                tool_tasks = tool_data["tasks"]
                if tool_tasks > 0:
                    tool_data["method_coverage"] /= tool_tasks
                    tool_data["activity_coverage"] /= tool_tasks
                    tool_data["mop_coverage"] /= tool_tasks

                # Add to app data
                app_data["tools"][tool] = tool_data

                # Add to global tools data
                if tool not in legacy_output["tools"]:
                    legacy_output["tools"][tool] = {
                        "tasks": 0,
                        "method_coverage": 0,
                        "activity_coverage": 0,
                        "mop_coverage": 0,
                        "errors": 0
                    }

                # Update global tool data
                legacy_output["tools"][tool]["tasks"] += tool_data["tasks"]
                legacy_output["tools"][tool]["method_coverage"] += tool_data["method_coverage"] * tool_data["tasks"]
                legacy_output["tools"][tool]["activity_coverage"] += tool_data["activity_coverage"] * tool_data["tasks"]
                legacy_output["tools"][tool]["mop_coverage"] += tool_data["mop_coverage"] * tool_data["tasks"]
                legacy_output["tools"][tool]["errors"] += tool_data["errors"]

            # Calculate app summary averages
            app_task_count = app_data["summary"]["tasks"]
            if app_task_count > 0:
                app_data["summary"]["method_coverage"] = sum(
                    r.method_coverage for r in coverage_results
                ) / app_task_count

                app_data["summary"]["activity_coverage"] = sum(
                    r.activity_coverage for r in coverage_results
                ) / app_task_count

                app_data["summary"]["mop_coverage"] = sum(
                    r.mop_method_coverage for r in coverage_results
                ) / app_task_count

            # Add app data to legacy output
            legacy_output["apps"][app_id] = app_data

        # Calculate global tool averages
        for tool, tool_data in legacy_output["tools"].items():
            tool_tasks = tool_data["tasks"]
            if tool_tasks > 0:
                tool_data["method_coverage"] /= tool_tasks
                tool_data["activity_coverage"] /= tool_tasks
                tool_data["mop_coverage"] /= tool_tasks

        # Update legacy summary
        legacy_output["summary"]["total_apps"] = app_count
        legacy_output["summary"]["total_tasks"] = task_count
        legacy_output["summary"]["total_errors"] = total_errors

        if task_count > 0:
            legacy_output["summary"]["avg_method_coverage"] = total_method_coverage / task_count
            legacy_output["summary"]["avg_activity_coverage"] = total_activity_coverage / task_count
            legacy_output["summary"]["avg_mop_coverage"] = total_mop_coverage / task_count

        return legacy_output


def process_results(results_dir: str, legacy_compat: bool = True) -> Dict[str, Any]:
    """
    Process experiment results from a directory.

    This is a convenience function that creates a ResultsProcessor instance
    and calls its process_results method.

    Args:
        results_dir: Directory containing results
        legacy_compat: Whether to generate legacy compatibility outputs

    Returns:
        Dictionary with processed results
    """
    processor = ResultsProcessor()
    return processor.process_results(results_dir, legacy_compat=legacy_compat)
