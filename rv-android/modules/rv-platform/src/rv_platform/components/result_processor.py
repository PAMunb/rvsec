# rv_platform/components/result_processor.py
"""
Result processor component for RV-Platform.

This component processes completed experiment tasks to generate CSV and JSON
output files for analysis and research purposes.
"""

import csv
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from rv_android_core.domain.task import TaskState
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import (
    CONTEXT_COMPONENT,
    LOG_COMPLETE,
    LOG_START,
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_coverage.parser.log.logcat_parser import parse_logcat_file
from rv_static_analysis.parser.static import static_analysis_parser


class ResultProcessorComponent:
    """
    Result processor component for generating CSV and JSON output files.

    This component processes completed experiment tasks to extract metrics,
    coverage data, and error information, then generates standardized output
    files for analysis and research.

    ### Architectural Role:
    - Processes completed experiment tasks to generate research output files
    - Creates standardized CSV files (coverage.csv, errors.csv, summary.csv)
    - Generates comprehensive JSON results files for structured data analysis
    - Operates independently of specific experiment frameworks
    - Provides consistent output format across different execution contexts

    ### Key Capabilities:
    - Process method coverage data with timing information
    - Extract and format monitored operations violations
    - Calculate aggregate metrics and coverage statistics
    - Generate experiment metadata and completion reports
    - Handle missing data gracefully with appropriate fallbacks

    ### Integration Points:
    - Uses ErrorHandler decorator for comprehensive error processing
    - Uses LoggingManager for consistent logging with context support
    - Processes tasks with repository data containing method calls and errors
    - Maintains compatibility with existing result analysis workflows
    """

    def __init__(self, tasks: List[Any], results_dir: str):
        """
        Initialize the result processor component.

        Args:
            tasks: List of completed tasks to process
            results_dir: Directory for storing generated result files
        """
        self.tasks = tasks
        self.results_dir = results_dir
        self.error_handler = ErrorHandler.get_instance()

        # Initialize logging with component context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_platform.components.result_processor",
            {CONTEXT_COMPONENT: "ResultProcessorComponent"},
        )

        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)

    @ErrorHandler.handle_errors(
        component="ResultProcessorComponent", phase="initialization"
    )
    def initialize(self, context: Dict[str, Any]) -> None:
        """
        Initialize the result processor component.

        Args:
            context: Initialization context (unused for this component)
        """
        self.logger.info(LOG_START.format(phase="result processor initialization"))
        # No specific initialization required
        self.logger.info(LOG_COMPLETE.format(phase="result processor initialization"))

    @ErrorHandler.handle_errors(
        component="ResultProcessorComponent", phase="result_processing"
    )
    def execute(self, context: Dict[str, Any]) -> None:
        """
        Execute result processing to generate CSV and JSON output files.

        Args:
            context: Execution context (unused for this component)
        """
        with self.logger.with_context(phase="result_processing"):
            self.logger.info(LOG_START.format(phase="experiment result processing"))

            # Filter for completed tasks. This includes tasks from ALL sessions
            # (previous runs loaded from tasks.json + current session), because
            # Platform._process_results() passes task_storage.get_completed_tasks().
            completed_tasks = self._filter_completed_tasks()
            if not completed_tasks:
                self.logger.warning("No completed tasks found for result processing")
                return

            # Generate all output files. Each generator handles the distinction
            # between tasks with in-memory repository (current session) and tasks
            # without repository (loaded from tasks.json on resume). For the
            # latter, MOP violations are reconstructed from persisted logcat files,
            # while coverage uses the serialized coverage_metrics fallback.
            self._generate_coverage_csv(completed_tasks)
            self._generate_errors_csv(completed_tasks)
            self._generate_summary_csv(completed_tasks)
            self._generate_results_json(completed_tasks)
            self._generate_performance_csv(completed_tasks)

            self.logger.info(LOG_COMPLETE.format(phase="experiment result processing"))

    def cleanup(self) -> None:
        """
        Clean up resources used by the result processor.
        """
        # No cleanup required for this component

    def _filter_completed_tasks(self) -> List[Any]:
        """
        Filter tasks to only include completed ones.

        Returns:
            List of completed tasks ready for processing
        """
        completed_tasks = [
            task
            for task in self.tasks
            if hasattr(task, "result")
            and getattr(task.result, "state", None) == TaskState.COMPLETED
        ]

        self.logger.info(
            f"Filtered {len(completed_tasks)} completed tasks out of {len(self.tasks)} total tasks"
        )
        return completed_tasks

    def _resolve_static_data(self, task: Any) -> Optional[Any]:
        """Return static-analysis data for a task, re-parsing the JSON on demand.

        Memoizes the result on ``task.static_data`` so repeated calls during a
        single CSV generation pass do not re-parse. INV-PLT-15 (gh58): the
        resume path obtains static data via re-parse rather than serializing
        it in tasks.json (which would inflate the persistence by MBs per task).
        """
        existing = getattr(task, "static_data", None)
        if existing is not None:
            return existing

        try:
            results_dir = getattr(task, "results_dir", None)
            apk_name = task.config.apk_name
            code_package = task.app.code_package if getattr(task, "app", None) else None
            static_data = static_analysis_parser.read_static_analysis_files(
                results_dir, apk_name, code_package
            )
            task.static_data = static_data
            return static_data
        except Exception as e:
            self.logger.warning(
                f"Failed to re-parse static analysis JSON for task {task.id}: {e} — "
                "per-method coverage will be zero, only MOP violations will be reliable"
            )
            return None

    def _reconstruct_repository_from_logcat(self, task: Any) -> Optional[Any]:
        """Reconstruct a LogcatRepository from the persisted logcat file.

        When a task is loaded from tasks.json on resume, ``task.repository`` is
        None because ``LogcatRepository`` is runtime-only (never serialized).
        This method re-reads the logcat file and re-parses the static-analysis
        JSON on demand (via ``_resolve_static_data``) so that the reconstructed
        repository has both MOP violation data AND per-method coverage data —
        equivalent to the runtime path. See INV-PLT-15 (gh58).

        Args:
            task: Task whose repository needs reconstruction

        Returns:
            LogcatRepository with MOP violations and (when static-analysis JSON
            is available) per-method coverage data. Returns ``None`` only when
            the logcat file itself is missing.
        """
        logcat_file = getattr(task.result, "logcat_file", None)
        if not logcat_file or not os.path.isfile(logcat_file):
            self.logger.warning(
                f"No logcat file available for task {task.id} — "
                "MOP violation details cannot be reconstructed"
            )
            return None

        try:
            static_data = self._resolve_static_data(task)
            repository = parse_logcat_file(logcat_file, static_data)
            error_count = len(repository.errors)
            coverage_note = (
                "with per-method coverage"
                if static_data is not None
                else "errors-only (static analysis JSON unavailable)"
            )
            self.logger.info(
                f"Reconstructed {error_count} MOP violations from logcat "
                f"for task {task.id} ({coverage_note})"
            )
            return repository
        except Exception as e:
            self.logger.warning(f"Failed to parse logcat file for task {task.id}: {e}")
            return None

    @ErrorHandler.handle_errors(
        component="ResultProcessorComponent", phase="coverage_csv_generation"
    )
    def _generate_coverage_csv(self, completed_tasks: List[Any]) -> None:
        """
        Generate detailed coverage CSV file with per-method coverage data.

        Args:
            completed_tasks: List of completed tasks to process
        """
        with self.logger.with_context(phase="coverage_csv_generation"):
            self.logger.info(LOG_START.format(phase="coverage CSV generation"))

            coverage_file = os.path.join(self.results_dir, "coverage.csv")

            with open(coverage_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # extended schema (gh58): 15 columns. The legacy
                # cov_method/cov_act/cov_rv_method remain cumulative-progressive.
                # cov_class and the three reachability-aware columns are
                # row-constant final values from CoverageMetrics.to_dict().
                writer.writerow(
                    [
                        "apk",
                        "rep",
                        "timeout",
                        "tool",
                        "time",
                        "class",
                        "method",
                        "signature",
                        "cov_class",
                        "cov_act",
                        "cov_method",
                        "cov_rv_method",
                        "cov_reachable",
                        "cov_reaches_target",
                        "cov_directly_reaches_target",
                    ]
                )

                # Process each completed task
                for task in completed_tasks:
                    self._write_task_coverage_data(writer, task)

            self.logger.info(f"Coverage CSV generated: {coverage_file}")

    def _write_task_coverage_data(self, writer: csv.writer, task: Any) -> None:
        """Write per-method coverage rows for a single task (gh58 unified path).

        On resume, ``task.repository`` may be None; this method calls
        ``_reconstruct_repository_from_logcat`` to obtain a populated
        ``LogcatRepository`` (re-parsing static-analysis JSON on demand).
        When the logcat file is missing entirely, the task is skipped — no
        fallback row from stale serialized metrics (INV-PLT-16).
        """
        try:
            config = task.config
            apk_name = config.apk_name
            repetition = config.repetition
            timeout = config.timeout
            tool_name = config.tool_config.get_full_tool_name()

            if not (hasattr(task, "repository") and task.repository):
                reconstructed = self._reconstruct_repository_from_logcat(task)
                if reconstructed is None:
                    return
                task.repository = reconstructed

            repository = task.repository

            # Final-state denominators from CoverageMetrics for the row-constant
            # columns (INV-PLT-17: cov_class = class_coverage, not method_coverage).
            metrics_dict = repository.calculate_metrics().to_dict()
            cov_class_final = round(metrics_dict.get("class_coverage", 0) or 0, 2)
            cov_reachable_final = round(
                metrics_dict.get("reachable_method_coverage", 0) or 0, 2
            )
            cov_reaches_target_final = round(
                metrics_dict.get("mop_method_coverage", 0) or 0, 2
            )
            cov_directly_reaches_target_final = round(
                metrics_dict.get("direct_mop_method_coverage", 0) or 0, 2
            )

            method_calls = repository.get_method_calls()

            # Progressive denominators for cov_method / cov_act / cov_rv_method.
            total_methods = (
                len(repository.get_static_methods())
                if hasattr(repository, "get_static_methods")
                else 0
            )
            total_activities = (
                len(repository.get_static_activities())
                if hasattr(repository, "get_static_activities")
                else 0
            )
            total_target_methods = (
                len(repository.get_target_methods())
                if hasattr(repository, "get_target_methods")
                else 1
            )

            called_methods: set = set()
            called_activities: set = set()
            called_target_methods: set = set()

            for i, call in enumerate(method_calls, 1):
                signature = call.get("signature", "")
                called_methods.add(signature)

                activity_name = call.get("activity")
                if activity_name:
                    called_activities.add(activity_name)

                if call.get("is_mop_method", False):
                    called_target_methods.add(signature)

                method_coverage = (
                    (len(called_methods) / total_methods * 100)
                    if total_methods > 0
                    else 0
                )
                activity_coverage = (
                    (len(called_activities) / total_activities * 100)
                    if total_activities > 0
                    else 0
                )
                mop_coverage = (
                    (len(called_target_methods) / total_target_methods * 100)
                    if total_target_methods > 0
                    else 0
                )

                writer.writerow(
                    [
                        apk_name,
                        repetition,
                        timeout,
                        tool_name,
                        call.get("time", i),
                        call.get("class_name", ""),
                        call.get("method_name", ""),
                        signature,
                        cov_class_final,
                        round(activity_coverage, 2),
                        round(method_coverage, 2),
                        round(mop_coverage, 2),
                        cov_reachable_final,
                        cov_reaches_target_final,
                        cov_directly_reaches_target_final,
                    ]
                )

        except Exception as e:
            self.logger.warning(
                f"Failed to write coverage data for task {task.id}: {e}"
            )

    @ErrorHandler.handle_errors(
        component="ResultProcessorComponent", phase="errors_csv_generation"
    )
    def _generate_errors_csv(self, completed_tasks: List[Any]) -> None:
        """
        Generate detailed errors CSV file with monitored operations violations.

        Args:
            completed_tasks: List of completed tasks to process
        """
        with self.logger.with_context(phase="errors_csv_generation"):
            self.logger.info(LOG_START.format(phase="errors CSV generation"))

            errors_file = os.path.join(self.results_dir, "errors.csv")

            with open(errors_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Write header for monitored operations violations
                writer.writerow(
                    [
                        "apk",
                        "rep",
                        "timeout",
                        "tool",
                        "time",
                        "spec",
                        "class",
                        "method",
                        "message",
                        "unique_msg",
                    ]
                )

                # Process each completed task
                for task in completed_tasks:
                    self._write_task_error_data(writer, task)

            self.logger.info(f"Errors CSV generated: {errors_file}")

    def _write_task_error_data(self, writer: csv.writer, task: Any) -> None:
        """
        Write error data for a single task to CSV.

        Args:
            writer: CSV writer instance
            task: Task to process for error data
        """
        try:
            # Extract task configuration
            config = task.config
            apk_name = config.apk_name
            repetition = config.repetition
            timeout = config.timeout
            tool_name = config.tool_config.get_full_tool_name()

            # For MOP violation data (errors.csv), we CAN reconstruct from logcat
            # because violations are standalone log entries that don't need static
            # analysis context. This is the key asymmetry with coverage.csv:
            # - errors.csv: reconstructible from logcat (RVSEC markers are self-contained)
            # - coverage.csv: NOT reconstructible (needs static analysis class list)
            repository = None
            if hasattr(task, "repository") and task.repository:
                repository = task.repository
            else:
                repository = self._reconstruct_repository_from_logcat(task)

            if repository:
                errors = repository.get_errors()

                # Process each monitored operations violation
                for i, error in enumerate(errors, 1):
                    # Extract fields from error data
                    class_full_name = error.get("class_full_name", "")
                    method = error.get("method", "")
                    spec = error.get("spec", "")
                    error_type = error.get("error_type", "")
                    message = error.get("message", "")

                    # Use existing unique_msg if available, otherwise construct it
                    unique_msg = error.get(
                        "unique_msg",
                        f"{class_full_name}:::{method}:::{spec}:::{error_type}:::{message}",
                    )

                    # Use timing data if available
                    time_value = error.get("time_since_task_start", i)
                    if time_value is None or time_value == 0:
                        time_value = i

                    writer.writerow(
                        [
                            apk_name,
                            repetition,
                            timeout,
                            tool_name,
                            time_value,
                            spec,
                            class_full_name,
                            method,
                            message,
                            unique_msg,
                        ]
                    )

        except Exception as e:
            self.logger.warning(f"Failed to write error data for task {task.id}: {e}")

    @ErrorHandler.handle_errors(
        component="ResultProcessorComponent", phase="summary_csv_generation"
    )
    def _generate_summary_csv(self, completed_tasks: List[Any]) -> None:
        """
        Generate summary CSV file with aggregate metrics per task.

        Args:
            completed_tasks: List of completed tasks to process
        """
        with self.logger.with_context(phase="summary_csv_generation"):
            self.logger.info(LOG_START.format(phase="summary CSV generation"))

            summary_file = os.path.join(self.results_dir, "summary.csv")

            with open(summary_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Extended schema (gh58): 12 columns, all values from
                # repository.calculate_metrics().to_dict() after reconstruct.
                # cov_rv_method is intentionally NOT included — in summary
                # (row-constant final values) it would alias cov_reaches_target.
                # It is retained in coverage.csv where it carries progressive
                # semantics distinct from cov_reaches_target.
                writer.writerow(
                    [
                        "apk",
                        "rep",
                        "timeout",
                        "tool",
                        "cov_act",
                        "cov_class",
                        "cov_method",
                        "cov_reachable",
                        "cov_reaches_target",
                        "cov_directly_reaches_target",
                        "mop_errors_total",
                        "mop_errors_unique",
                    ]
                )

                # Process each completed task
                for task in completed_tasks:
                    self._write_task_summary_data(writer, task)

            self.logger.info(f"Summary CSV generated: {summary_file}")

    def _write_task_summary_data(self, writer: csv.writer, task: Any) -> None:
        """Write one summary row per task (gh58 unified path).

        Reads exclusively from ``repository.calculate_metrics().to_dict()``
        after ``_reconstruct_repository_from_logcat`` ensures the repository
        is populated. The legacy 3-tier cascade (result.coverage_metrics →
        repository → zeros) is removed (INV-PLT-16); when the logcat is
        missing entirely, a zeroed row with explicit warning is emitted.
        """
        try:
            config = task.config
            apk_name = config.apk_name
            repetition = config.repetition
            timeout = config.timeout
            tool_name = config.tool_config.get_full_tool_name()

            if not (hasattr(task, "repository") and task.repository):
                reconstructed = self._reconstruct_repository_from_logcat(task)
                if reconstructed is not None:
                    task.repository = reconstructed

            if hasattr(task, "repository") and task.repository:
                metrics_dict = task.repository.calculate_metrics().to_dict()
            else:
                self.logger.warning(
                    f"No coverage metrics available for task {task.id} — "
                    "logcat missing, emitting zeroed summary row"
                )
                metrics_dict = {}

            def _val(key: str) -> float:
                return round(metrics_dict.get(key, 0) or 0, 2)

            writer.writerow(
                [
                    apk_name,
                    repetition,
                    timeout,
                    tool_name,
                    _val("activity_coverage"),
                    _val("class_coverage"),
                    _val("method_coverage"),
                    _val("reachable_method_coverage"),
                    _val("mop_method_coverage"),
                    _val("direct_mop_method_coverage"),
                    int(metrics_dict.get("total_errors", 0) or 0),
                    int(metrics_dict.get("unique_errors", 0) or 0),
                ]
            )

        except Exception as e:
            self.logger.warning(f"Failed to write summary data for task {task.id}: {e}")

    @ErrorHandler.handle_errors(
        component="ResultProcessorComponent", phase="results_json_generation"
    )
    def _generate_results_json(self, completed_tasks: List[Any]) -> None:
        """
        Generate comprehensive results JSON file with structured experiment data.

        Args:
            completed_tasks: List of completed tasks to process
        """
        with self.logger.with_context(phase="results_json_generation"):
            self.logger.info(LOG_START.format(phase="results JSON generation"))

            results_file = os.path.join(self.results_dir, "results.json")

            # Build hierarchical JSON: apk -> repetition -> timeout -> tool.
            # This nesting matches the experiment's Cartesian product structure
            # and makes it easy to compare tools for the same APK/timeout pair.
            results_data = {}
            for task in completed_tasks:
                apk_name = task.config.apk_name
                rep = task.config.repetition
                timeout = task.config.timeout
                tool_name = task.config.tool_config.get_full_tool_name()

                # Initialize nested structure
                if apk_name not in results_data:
                    results_data[apk_name] = {"repetitions": {}}

                if str(rep) not in results_data[apk_name]["repetitions"]:
                    results_data[apk_name]["repetitions"][str(rep)] = {"timeouts": {}}

                if (
                    str(timeout)
                    not in results_data[apk_name]["repetitions"][str(rep)]["timeouts"]
                ):
                    results_data[apk_name]["repetitions"][str(rep)]["timeouts"][
                        str(timeout)
                    ] = {"tools": {}}

                # Add tool-specific data
                tool_data = self._extract_task_data(task)
                results_data[apk_name]["repetitions"][str(rep)]["timeouts"][
                    str(timeout)
                ]["tools"][tool_name] = tool_data

            # Write JSON file
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Results JSON generated: {results_file}")

    def _extract_task_data(self, task: Any) -> Dict[str, Any]:
        """
        Extract comprehensive data for a single task.

        Args:
            task: Task to extract data from

        Returns:
            Dictionary with task data
        """
        try:
            # Base task information
            task_data = {
                "start_time": (
                    getattr(task.result, "start_time", datetime.now()).timestamp()
                    if hasattr(task, "result")
                    else None
                ),
                "summary": {},
                "monitored_operations_errors": {
                    "total": 0,
                    "messages": [],
                    "details": [],
                },
            }

            # Get metrics from repository or result
            if hasattr(task, "repository") and task.repository:
                metrics = task.repository.calculate_metrics()
                metrics_dict = metrics.to_dict()

                task_data["summary"] = {
                    "called_activities": metrics.called_activities,
                    "called_methods": metrics.called_methods,
                    "called_methods_mop_reachable": metrics.called_target_methods,
                    "activities_coverage": metrics_dict["activity_coverage"],
                    "method_coverage": metrics_dict["method_coverage"],
                    "methods_mop_reachable_coverage": metrics_dict[
                        "mop_method_coverage"
                    ],
                    "monitored_operations_errors_count": metrics.total_errors,
                }

                # Get error details
                errors = task.repository.get_errors()
                task_data["monitored_operations_errors"]["total"] = len(errors)

                # Create complete messages
                messages = []
                for error in errors:
                    if "unique_msg" in error and error["unique_msg"]:
                        messages.append(error["unique_msg"])
                    else:
                        # Construct using field names
                        class_full_name = error.get("class_full_name", "")
                        method = error.get("method", "")
                        spec = error.get("spec", "")
                        error_type = error.get("error_type", "")
                        message = error.get("message", "")
                        complete_msg = f"{class_full_name}:::{method}:::{spec}:::{error_type}:::{message}"
                        messages.append(complete_msg)

                task_data["monitored_operations_errors"]["messages"] = messages
                task_data["monitored_operations_errors"]["details"] = errors

            else:
                # Fallback to task result metrics for summary data
                metrics = getattr(task.result, "coverage_metrics", {})
                task_data["summary"] = {
                    "called_activities": metrics.get("called_activities", 0),
                    "called_methods": metrics.get("called_methods", 0),
                    "called_methods_mop_reachable": metrics.get(
                        "called_target_methods", 0
                    ),
                    "activities_coverage": metrics.get("activities_coverage", 0),
                    "method_coverage": metrics.get("method_coverage", 0),
                    "methods_mop_reachable_coverage": metrics.get(
                        "methods_mop_reachable_coverage", 0
                    ),
                    "monitored_operations_errors_count": metrics.get("total_errors", 0),
                }

                # Reconstruct MOP violation details from logcat
                reconstructed = self._reconstruct_repository_from_logcat(task)
                if reconstructed:
                    errors = reconstructed.get_errors()
                    task_data["monitored_operations_errors"]["total"] = len(errors)

                    messages = []
                    for error in errors:
                        if "unique_msg" in error and error["unique_msg"]:
                            messages.append(error["unique_msg"])
                        else:
                            class_full_name = error.get("class_full_name", "")
                            method = error.get("method", "")
                            spec = error.get("spec", "")
                            error_type = error.get("error_type", "")
                            message = error.get("message", "")
                            complete_msg = f"{class_full_name}:::{method}:::{spec}:::{error_type}:::{message}"
                            messages.append(complete_msg)

                    task_data["monitored_operations_errors"]["messages"] = messages
                    task_data["monitored_operations_errors"]["details"] = errors

            return task_data

        except Exception as e:
            self.logger.warning(f"Failed to extract data for task {task.id}: {e}")
            return {
                "summary": {},
                "monitored_operations_errors": {
                    "total": 0,
                    "messages": [],
                    "details": [],
                },
            }

    @ErrorHandler.handle_errors(
        component="ResultProcessorComponent", phase="performance_csv_generation"
    )
    def _generate_performance_csv(self, completed_tasks: List[Any]) -> None:
        """
        Generate performance CSV file using PerformanceProcessorComponent.

        Args:
            completed_tasks: List of completed tasks to process
        """
        with self.logger.with_context(phase="performance_csv_generation"):
            self.logger.info(LOG_START.format(phase="performance CSV generation"))

            try:
                # Import and use performance processor
                from rv_platform.components.performance_processor import (
                    PerformanceProcessorComponent,
                )

                performance_processor = PerformanceProcessorComponent(
                    completed_tasks, self.results_dir
                )
                performance_processor.generate()
                summary = performance_processor.get_performance_summary()
                self.logger.info(
                    f"Performance processing completed: {summary.get('summary', 'Unknown status')}"
                )

            except Exception as e:
                self.logger.warning(f"Performance CSV generation failed: {e}")
                # Create empty performance file as fallback
                self._create_empty_performance_csv()

            self.logger.info(LOG_COMPLETE.format(phase="performance CSV generation"))

    def _create_empty_performance_csv(self) -> None:
        """
        Create an empty performance CSV file as fallback.
        """
        try:
            performance_file = os.path.join(self.results_dir, "performance.csv")

            with open(performance_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "apk",
                        "rep",
                        "timeout",
                        "tool",
                        "execution_time_seconds",
                        "task_state",
                        "monitoring_enabled",
                        "timestamp",
                    ]
                )

                # Write basic data for each completed task
                for task in self.tasks:
                    try:
                        config = task.config
                        writer.writerow(
                            [
                                config.apk_name,
                                config.repetition,
                                config.timeout,
                                config.tool_config.get_full_tool_name(),
                                getattr(task.result, "execution_time_seconds", 0),
                                getattr(task.result, "state", "unknown"),
                                False,  # monitoring was disabled/failed
                                time.time(),
                            ]
                        )
                    except Exception:
                        pass  # Skip problematic tasks

            self.logger.info(f"Empty performance CSV created: {performance_file}")

        except Exception as e:
            self.logger.error(f"Failed to create empty performance CSV: {e}")
