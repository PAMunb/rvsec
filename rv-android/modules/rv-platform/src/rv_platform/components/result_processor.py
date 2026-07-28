# rv_platform/components/result_processor.py
"""
Result processor component for RV-Platform.

This component processes completed experiment tasks and writes the experiment's
output files. It implements platform Requirement "Result Generation (FR14)":
only tasks in ``TaskState.COMPLETED`` are processed, and it produces six files —
the five FR14 files (``coverage.csv``, ``errors.csv``, ``summary.csv``,
``results.json``, ``performance.csv``) plus ``app_events.csv`` from Requirement
"Diagnostic Events CSV Generation (FR14)". Result processing can be skipped
during execution and run standalone later via ``rv-platform run
--process-results`` (Scenario "Standalone Result Processing").

On resume it also implements Requirement "Result Consolidation on Resume
(FR10-ext)": tasks loaded from ``tasks.json`` arrive with ``repository=None`` /
``results_dir=""`` / ``app=None``, so both MOP violations and per-method
coverage are reconstructed on demand from the persisted logcat and the
co-located static-analysis JSON.
"""

import csv
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.task import TaskState
from rv_android_core.domain.window import Windows
from rv_android_core.domain.wtg import WindowTransitionGraph
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
    Generate the experiment output files from completed tasks.

    Implements platform Requirement "Result Generation (FR14)": processes only
    tasks in ``TaskState.COMPLETED`` and writes six files — the five FR14 files
    (``coverage.csv``, ``errors.csv``, ``summary.csv``, ``results.json``,
    ``performance.csv``) plus ``app_events.csv`` from Requirement "Diagnostic
    Events CSV Generation (FR14)".

    ### Architectural Role:
    - Writes coverage.csv, errors.csv, summary.csv, results.json,
      performance.csv (FR14) and app_events.csv (diagnostic FR14).
    - Reconstructs resumed tasks (Requirement "Result Consolidation on Resume
      (FR10-ext)"): for tasks loaded from tasks.json with no in-memory
      repository, both MOP violations and per-method coverage are rebuilt from
      the persisted logcat plus co-located static-analysis JSON.
    - Runs from Platform._process_results() after execution, or standalone via
      --process-results (Scenario "Standalone Result Processing").

    ### Key Features:
    - Per-method coverage rows with progressive and row-constant metrics.
    - Monitored-operations violation rows (reconstructible from logcat alone).
    - Aggregate per-task summary and hierarchical JSON.

    ### Integration Points:
    - ErrorHandler decorators isolate per-file generation failures.
    - LoggingManager provides context-scoped logging.
    - Reads repository data (method calls and errors) or reconstructs it from
      logcat when the in-memory repository is absent (resume).
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

        # IDs of tasks whose static-analysis JSON could not be resolved during
        # reconstruction (D-3a). Membership-guarded so a task is counted at most
        # once regardless of how many CSV writers trigger reconstruction; len()
        # is the aggregate N surfaced by the resume health-check WARNING
        # (INV-PLT-18). This component-level counter is one of the two disjoint
        # fields of INV-PLT-15 — it counts tasks, distinct from the per-task
        # task.static_data parse-memo. (Re)initialized at the start of execute()
        # so each pass reports only its own tasks (Scenario "Resume Coverage
        # Health Check Warning").
        self._unresolved_task_ids: set = set()

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

            # Re-initialize the unresolved-static-data counter for this pass so a
            # second consolidation pass (e.g. --process-results) reports only its
            # own tasks (D-3a; protects G3 reprocessing idempotency). Per-pass
            # re-init is Scenario "Resume Coverage Health Check Warning".
            self._unresolved_task_ids = set()

            # Filter for completed tasks. This includes tasks from ALL sessions
            # (previous runs loaded from tasks.json + current session), because
            # Platform._process_results() passes task_storage.get_completed_tasks()
            # (Requirement "Result Consolidation on Resume (FR10-ext)", Scenario
            # "Result Processing After Resume Includes All Sessions").
            completed_tasks = self._filter_completed_tasks()
            if not completed_tasks:
                # Requirement "Result Generation (FR14)", Scenario "No Completed
                # Tasks": log a warning and generate no files.
                self.logger.warning("No completed tasks found for result processing")
                return

            # Generate all output files. Each generator handles the distinction
            # between tasks with in-memory repository (current session) and tasks
            # without repository (loaded from tasks.json on resume). For the
            # latter, BOTH MOP violations AND per-method coverage are reconstructed
            # from the persisted logcat + co-located static-analysis JSON
            # (re-parsed on demand). There is NO fallback to serialized
            # coverage_metrics (INV-PLT-16): when the JSON is genuinely absent,
            # coverage is zeroed by construction while MOP errors survive.
            # The first five files are Requirement "Result Generation (FR14)";
            # app_events.csv is Requirement "Diagnostic Events CSV Generation
            # (FR14)".
            self._generate_coverage_csv(completed_tasks)
            self._generate_errors_csv(completed_tasks)
            self._generate_app_events_csv(completed_tasks)
            self._generate_summary_csv(completed_tasks)
            self._generate_results_json(completed_tasks)
            self._generate_performance_csv(completed_tasks)

            # Resume health check (INV-PLT-18 / G4): if any processed task
            # reconstructed to zero coverage because its static-analysis JSON
            # could not be resolved, surface one prominent aggregate WARNING with
            # the exact N/M count. Silent when N == 0. Exactly one WARNING per
            # pass over a set re-initialized above (Scenario "Resume Coverage
            # Health Check Warning").
            unresolved = len(self._unresolved_task_ids)
            if unresolved:
                self.logger.warning(
                    f"Resume coverage health: {unresolved}/{len(completed_tasks)} "
                    "resumed tasks had unresolved static data — coverage zeroed for "
                    "those tasks (MOP errors preserved). Verify the static-analysis "
                    "JSON is co-located with each logcat if non-zero coverage was "
                    "expected."
                )

            self.logger.info(LOG_COMPLETE.format(phase="experiment result processing"))

    def cleanup(self) -> None:
        """
        Clean up resources used by the result processor.
        """
        # No cleanup required for this component

    def _filter_completed_tasks(self) -> List[Any]:
        """
        Filter tasks to only include completed ones.

        Requirement "Result Generation (FR14)": the component processes only
        tasks with ``TaskState.COMPLETED``; any other state is excluded. When
        none qualify, ``execute()`` skips all file generation (Scenario "No
        Completed Tasks").

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

        INV-PLT-15 (gh58 + gh65): the resume path obtains static data via an
        on-demand re-parse rather than serializing it in tasks.json (which would
        inflate the persistence by MBs per task). On resume, ``task.results_dir``
        is empty — it is not serialized — so the per-APK directory is derived
        from ``os.path.dirname(task.result.logcat_file)``: at runtime
        ``task.results_dir == os.path.dirname(logcat_file)`` and the
        static-analysis JSON is co-located with the logcat (ADR 0003).

        D-3a — two fields with disjoint roles keep the unresolved count robust:

        - ``task.static_data`` is the **parse memo**. A valid ``StaticAnalysisData``
          is assigned on EVERY path (an empty one when the JSON is absent or the
          parser raises), so a non-``None`` value short-circuits re-entry WITHOUT
          re-parsing and is always a legal argument to ``parse_logcat_file``.
          Consequently ``read_static_analysis_files`` runs at most once per task
          across all CSV writers, independent of writer ordering.
        - ``self._unresolved_task_ids`` **counts** tasks whose static data could
          not be resolved (empty ``classes``), membership-guarded so the count is
          idempotent across writers; ``len(...)`` is the aggregate N reported by
          the resume health-check WARNING (INV-PLT-18 / G4).

        Returns the populated ``StaticAnalysisData`` when ``<dir>/<apk>.json``
        resolves to non-empty classes; ``None`` otherwise (so downstream coverage
        is zeroed by construction), with ``task.id`` recorded once.

        Scenarios (Requirement "Result Consolidation on Resume (FR10-ext)"):
        "Resume After tasks.json Round-Trip Resolves results_dir from Logcat"
        (empty ``results_dir`` derived from the logcat dirname), "Static Analysis
        JSON Missing on Resume" (absent JSON → ``None``, task recorded once), and
        "Orchestrated Resume Skips Static Analysis but Reuses Persisted JSON"
        (locate the co-located JSON without re-running GATOR). In the degraded
        JSON-absent case, MOP errors — including ``total_errors``/``unique_errors``
        — stay reliable per analysis INV-ANA-25; only per-method coverage zeroes.
        """
        memo = getattr(task, "static_data", None)
        if memo is not None:
            # Parse memo holds — never re-parse. Empty classes => unresolved.
            return memo if memo.classes.classes else None

        static_data = None
        try:
            results_dir = getattr(task, "results_dir", None)
            if not results_dir:
                logcat_file = getattr(task.result, "logcat_file", None)
                results_dir = os.path.dirname(logcat_file) if logcat_file else ""
            apk_name = task.config.apk_name
            code_package = task.app.code_package if getattr(task, "app", None) else None
            static_data = static_analysis_parser.read_static_analysis_files(
                results_dir, apk_name, code_package
            )
        except Exception as e:
            self.logger.warning(
                f"Failed to re-parse static analysis JSON for task {task.id}: {e} — "
                "per-method coverage will be zero, only MOP violations will be reliable"
            )
            static_data = None

        # Memoize a VALID StaticAnalysisData on every path (empty when the JSON
        # is absent or the parser raised). The empty instance is non-None, so it
        # short-circuits re-entry without re-parsing/re-counting, and it is a
        # legal (zero-coverage) argument to parse_logcat_file.
        if static_data is None:
            static_data = StaticAnalysisData(
                Classes(), Windows(), WindowTransitionGraph()
            )
        task.static_data = static_data

        if not static_data.classes.classes:
            # Unresolved: count once per task (membership-guarded, order-independent).
            if task.id not in self._unresolved_task_ids:
                self._unresolved_task_ids.add(task.id)
                self.logger.warning(
                    f"Static analysis JSON unresolved for task {task.id} "
                    f"(apk={task.config.apk_name}) — per-method coverage zeroed, "
                    "MOP violations preserved"
                )
            return None

        return static_data

    def _reconstruct_repository_from_logcat(self, task: Any) -> Optional[Any]:
        """Reconstruct a LogcatRepository from the persisted logcat file.

        When a task is loaded from tasks.json on resume, ``task.repository`` is
        None because ``LogcatRepository`` is runtime-only (never serialized).
        This method re-reads the logcat file and re-parses the static-analysis
        JSON on demand (via ``_resolve_static_data``) so that the reconstructed
        repository has both MOP violation data AND per-method coverage data —
        equivalent to the runtime path. See INV-PLT-15 (gh58).

        The persisted ``task.result.tool_execution_start`` epoch is forwarded to
        ``parse_logcat_file`` so reconstructed entries carry the same
        ``time_since_task_start`` values the live tracker would have produced
        (INV-PLT-23). When the epoch is absent (legacy tasks.json), a WARNING is
        logged and timing stays 0 — an explicit degraded state, never fabricated.

        Scenarios (Requirement "Result Consolidation on Resume (FR10-ext)"):
        "Logcat Re-Reading with On-Demand Static Data Re-Parse" (re-parse JSON,
        cache on ``task.static_data``, re-read the logcat) and "Logcat File
        Missing on Resume" (return ``None`` only when the logcat file itself is
        missing).

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

        tool_execution_start = getattr(task.result, "tool_execution_start", None)
        if tool_execution_start is None:
            self.logger.warning(
                f"No tool execution start persisted for task {task.id} — "
                "reconstructed time values remain 0 (INV-PLT-23)"
            )

        try:
            static_data = self._resolve_static_data(task)
            repository = parse_logcat_file(
                logcat_file, static_data, tool_execution_start=tool_execution_start
            )
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

        Requirement "Result Generation (FR14)", Scenario "Coverage CSV Format".
        The 15-column header below is byte-identical to baseline (INV-PLT-19).

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

        Requirement "Result Generation (FR14)", Scenario "Coverage CSV Format".
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

        Requirement "Result Generation (FR14)", Scenario "Errors CSV Format".

        The header carries 11 columns: `source` sits after `method` so the row reads
        identity first, then evidence — `spec, class, method, source, message`. It
        records where the violation happened without letting the position into any
        key, which is the whole point of gh89: a source line inside `class`/`method`
        makes one misuse count once per line. Every known consumer (`rvsec-dataset`
        `unittests/report.py` and `unittests/classify.py`, the `ase-journal` analysis
        scripts) addresses columns by name, so appending a column is compatible; that
        was verified, not assumed.

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
                        "source",
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
            # Requirement "Result Consolidation on Resume (FR10-ext)": errors stay
            # reliable even when the static JSON is absent (analysis INV-ANA-25).
            repository = None
            if hasattr(task, "repository") and task.repository:
                repository = task.repository
            else:
                repository = self._reconstruct_repository_from_logcat(task)

            if repository:
                errors = repository.get_errors()

                # Process each monitored operations violation
                for error in errors:
                    # Extract fields from error data
                    class_full_name = error.get("class_full_name", "")
                    method = error.get("method", "")
                    # Empty only for a record serialized before `source` entered the
                    # schema; the field itself has always existed on RvErrorLog.
                    source = error.get("source", "")
                    spec = error.get("spec", "")
                    error_type = error.get("error_type", "")
                    message = error.get("message", "")

                    # Use existing unique_msg if available, otherwise construct it
                    unique_msg = error.get(
                        "unique_msg",
                        f"{class_full_name}:::{method}:::{spec}:::{error_type}:::{message}",
                    )

                    # time is written as-is (INV-PLT-24): 0 means "within the
                    # first second of tool execution", never a fabricated value.
                    time_value = error.get("time_since_task_start", 0)

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
                            source,
                            message,
                            unique_msg,
                        ]
                    )

        except Exception as e:
            self.logger.warning(f"Failed to write error data for task {task.id}: {e}")

    @ErrorHandler.handle_errors(
        component="ResultProcessorComponent", phase="app_events_csv_generation"
    )
    def _generate_app_events_csv(self, completed_tasks: List[Any]) -> None:
        """
        Generate the per-run app_events.csv with one row per diagnostic event
        (crash / VerifyError / ANR). Only the ``stack_head`` summary is written;
        the full multi-line trace stays in the ``.logcat`` (decision D3). The
        existing coverage/errors/summary CSV schemas are untouched (INV-PLT-19).

        Requirement "Diagnostic Events CSV Generation (FR14)", Scenarios "One
        row per diagnostic event with stack_head only" and "Existing CSV schemas
        unchanged".

        Args:
            completed_tasks: List of completed tasks to process
        """
        with self.logger.with_context(phase="app_events_csv_generation"):
            self.logger.info(LOG_START.format(phase="app events CSV generation"))

            app_events_file = os.path.join(self.results_dir, "app_events.csv")

            with open(app_events_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Header for diagnostic events (full trace stays in the .logcat).
                writer.writerow(
                    [
                        "apk",
                        "rep",
                        "timeout",
                        "tool",
                        "time",
                        "category",
                        "exception_class",
                        "method",
                        "source",
                        "message",
                        "process",
                        "pid",
                        "fatal",
                        "n_frames",
                        "stack_head",
                    ]
                )

                for task in completed_tasks:
                    self._write_task_app_events(writer, task)

            self.logger.info(f"App events CSV generated: {app_events_file}")

    def _write_task_app_events(self, writer: csv.writer, task: Any) -> None:
        """
        Write diagnostic-event rows for a single task to app_events.csv.

        Like errors.csv, diagnostic events are reconstructible from the logcat
        (the diagnostic parser runs inside ``parse_logcat_file``), so resumed
        tasks repopulate their rows from the persisted logcat (INV-PLT-20;
        Requirement "Diagnostic Events CSV Generation (FR14)", Scenario
        "app_events survives resume reconstruction").

        Args:
            writer: CSV writer instance
            task: Task to process for diagnostic-event data
        """
        try:
            config = task.config
            apk_name = config.apk_name
            repetition = config.repetition
            timeout = config.timeout
            tool_name = config.tool_config.get_full_tool_name()

            repository = None
            if hasattr(task, "repository") and task.repository:
                repository = task.repository
            else:
                repository = self._reconstruct_repository_from_logcat(task)

            if repository:
                for event in repository.get_diagnostic_events():
                    # time is written as-is (INV-PLT-24): 0 means "within the
                    # first second of tool execution", never a fabricated value.
                    time_value = event.get("time_since_task_start", 0)

                    writer.writerow(
                        [
                            apk_name,
                            repetition,
                            timeout,
                            tool_name,
                            time_value,
                            event.get("category", ""),
                            event.get("class_full_name", ""),
                            event.get("method", ""),
                            event.get("source", ""),
                            event.get("message", ""),
                            event.get("process", ""),
                            event.get("pid", ""),
                            event.get("fatal", False),
                            event.get("n_frames", 0),
                            event.get("stack_head", ""),
                        ]
                    )

        except Exception as e:
            self.logger.warning(
                f"Failed to write app event data for task {task.id}: {e}"
            )

    @ErrorHandler.handle_errors(
        component="ResultProcessorComponent", phase="summary_csv_generation"
    )
    def _generate_summary_csv(self, completed_tasks: List[Any]) -> None:
        """
        Generate summary CSV file with aggregate metrics per task.

        Requirement "Result Generation (FR14)", Scenario "Summary CSV Format".
        The 12-column header below is byte-identical to baseline (INV-PLT-19).

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

        Requirement "Result Generation (FR14)", Scenario "Summary CSV Format".
        Reads exclusively from ``repository.calculate_metrics().to_dict()``
        after ``_reconstruct_repository_from_logcat`` ensures the repository
        is populated. The legacy 3-tier cascade (result.coverage_metrics →
        repository → zeros) is removed (INV-PLT-16); when the logcat is
        missing entirely, a zeroed row with explicit warning is emitted
        (Scenario "Logcat File Missing on Resume" and Scenario "No Fallback to
        Serialized Coverage Metrics When JSON Is Absent").
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
        Generate the results JSON file with structured experiment data.

        Requirement "Result Generation (FR14)", Scenario "Results JSON
        Hierarchical Structure": keyed apk -> repetitions -> rep -> timeouts ->
        timeout -> tools -> tool_name, each entry carrying ``summary`` and
        ``monitored_operations_errors``.

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
        Extract the per-task entry for results.json.

        Requirement "Result Consolidation on Resume (FR10-ext)". The
        ``if task.repository:`` branch produces summary metrics plus MOP
        violation details from the populated repository (Scenario "Result
        Processing After Resume Includes All Sessions"). The ``else`` branch is
        reached only when ``task.repository`` was never populated (the logcat
        genuinely missing): ``execute()`` runs the coverage and summary writers
        first, and on resume those writers mutate ``task.repository`` via
        ``_reconstruct_repository_from_logcat``. In the ``else`` branch, summary
        values are read from the serialized ``task.result.coverage_metrics`` and
        MOP violation details are reconstructed independently from the logcat.

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

        Requirement "Result Generation (FR14)": ``performance.csv`` is one of the
        five FR14 files. Generation is delegated to
        ``PerformanceProcessorComponent``; ``_create_empty_performance_csv`` is
        the fallback path when that delegation fails.

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

        Requirement "Result Generation (FR14)": fallback for ``performance.csv``
        when ``PerformanceProcessorComponent`` delegation raises, so the file
        still exists with basic per-task timing rows.
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
