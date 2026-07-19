# rv_experiment/experiment/workflow/result_manager.py
"""
Simplified result manager for RV-Android experiments.

This module provides minimal result management functionality focused
on experiment metadata and instrumentation error tracking.

Delegate for the Phase 3 (post-processing) outputs of Requirement
"Three-Phase Workflow (FR15, NFR08)": PostProcessor calls this manager to
emit `instrument_errors.json` (INV-EXP-11) plus an in-memory experiment
metadata summary. CSV/JSON result processing is intentionally NOT done here
-- it is owned by rv-platform -- which upholds INV-EXP-02: rv-experiment
never reads back task results, coverage data, or error logs. Data flows
one-way from rv-experiment to rv-platform.
"""

import json
import os
from typing import Any, Dict, List

from rv_android_core.domain.task import TaskState
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import (
    CONTEXT_COMPONENT,
    LOG_COMPLETE,
    LOG_START,
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_platform.storage.task_storage import TaskStorage


class ResultManager:
    """
    Simplified result manager for RV-Android experiments.

    This module provides minimal result management functionality focused
    on experiment metadata and instrumentation error tracking. CSV and JSON
    result processing is owned by rv-platform, keeping a clean separation
    of concerns and upholding INV-EXP-02 (rv-experiment does not read task
    results, coverage, or error logs back from rv-platform -- data flows
    one-way).

    This class is the Phase 3 (post-processing) delegate of Requirement
    "Three-Phase Workflow (FR15, NFR08)": `PostProcessor` invokes it to
    produce `instrument_errors.json` (INV-EXP-11 enforcement lives in
    `_generate_instrument_errors_json`) plus an in-memory metadata summary
    used only for logging.

    ### Architectural Role:
    - Generates `instrument_errors.json` per-APK for downstream filtering (INV-EXP-11)
    - Provides basic experiment metadata tracking for logging
    - Maintains minimal orchestration responsibilities
    - Delegates complex data processing to rv-platform (INV-EXP-02)

    ### Key Capabilities:
    - Generate instrumentation errors JSON file if errors occurred
    - Create basic experiment metadata for logging and tracking
    - Integrate with experiment workflow for error reporting
    - Provide simple result summary for experiment completion

    ### Integration Points:
    - Uses ErrorHandler decorator for error processing
    - Uses LoggingManager for consistent logging with context support
    - Works with TaskStorage for accessing completed experiment tasks
    """

    def __init__(self, results_dir: str, task_storage: TaskStorage):
        """
        Initialize the simplified result manager.

        Args:
            results_dir: Directory for storing experiment results
            task_storage: Task storage containing completed tasks
        """
        self.results_dir = results_dir
        self.task_storage = task_storage
        self.error_handler = ErrorHandler.get_instance()

        # Initialize logging with context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "experiment.workflow.result_manager", {CONTEXT_COMPONENT: "ResultManager"}
        )

        # Result processing state
        self.experiment_metadata: Dict[str, Any] = {}

        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)

    @ErrorHandler.handle_errors(component="ResultManager", phase="result_generation")
    def generate_reports(self) -> None:
        """
        Generate basic experiment reports focused on instrumentation errors.

        Orchestrates the two Phase 3 products of Requirement "Three-Phase
        Workflow (FR15, NFR08)": `instrument_errors.json` (via
        `_generate_instrument_errors_json`, the INV-EXP-11 enforcement site)
        and the in-memory experiment metadata summary. CSV and JSON result
        processing is handled by rv-platform's ResultProcessorComponent, not
        here (INV-EXP-02).

        Current-state caveat about INV-EXP-11: INV-EXP-11 requires that
        `instrument_errors.json` be generated even when no instrumentation
        errors occurred (empty `{}`). The always-write guarantee is provided
        by `_generate_instrument_errors_json`, but ONLY along the path where
        this method calls it. When zero tasks reached COMPLETED state, this
        method early-returns below BEFORE that call, so no
        `instrument_errors.json` is written at all in that case. The empty-`{}`
        guarantee is therefore conditional on at least one completed task
        existing -- it is not unconditional.
        """
        with self.logger.with_context(phase="result_generation"):
            self.logger.info(LOG_START.format(phase="experiment result generation"))

            # Load completed tasks (per-task STATUS metadata only; see INV-EXP-02
            # boundary note in _load_completed_tasks).
            completed_tasks = self._load_completed_tasks()
            if not completed_tasks:
                # Early return: with no completed tasks, neither product is
                # produced. This path skips instrument_errors.json entirely, so
                # the INV-EXP-11 empty-{} write does not happen here.
                #
                # TODO(INV-EXP-11): this early return violates INV-EXP-11, which
                # requires instrument_errors.json to ALWAYS be written (an empty
                # `{}` when there are no errors). When zero tasks reach COMPLETED
                # state the file is never created, so the empty-{} guarantee is
                # only conditional today. Fix (pending a separate OpenSpec change)
                # would write the empty file before returning, or move the write
                # out of the completed-tasks branch.
                self.logger.warning("No completed tasks found for result generation")
                return

            # Generate instrumentation errors JSON
            self._generate_instrument_errors_json(completed_tasks)

            # Create basic experiment metadata
            self._generate_experiment_metadata(completed_tasks)

            self.logger.info(LOG_COMPLETE.format(phase="experiment result generation"))

    @ErrorHandler.handle_errors(component="ResultManager", phase="task_loading")
    def _load_completed_tasks(self) -> List[Any]:
        """
        Load completed tasks from storage.

        Filters `TaskStorage` for tasks whose `result.state` is
        `TaskState.COMPLETED`. This reads only per-task STATUS metadata (the
        task's state field), not coverage or error-log result payloads --
        which is the sanctioned exception to INV-EXP-02: rv-experiment may
        inspect task status without violating the one-way data-flow rule that
        keeps result payloads owned by rv-platform.

        Returns:
            List of completed tasks ready for processing
        """
        # Get all tasks and filter for completed ones (status field only,
        # per the INV-EXP-02 boundary note above).
        all_tasks = self.task_storage.get_tasks()
        completed_tasks = [
            task
            for task in all_tasks
            if hasattr(task, "result")
            and getattr(task.result, "state", None) == TaskState.COMPLETED
        ]

        self.logger.info(
            f"Loaded {len(completed_tasks)} completed tasks out of {len(all_tasks)} total tasks"
        )
        return completed_tasks

    @ErrorHandler.handle_errors(
        component="ResultManager", phase="instrument_errors_json_generation"
    )
    def _generate_instrument_errors_json(self, completed_tasks: List[Any]) -> None:
        """
        Generate the instrumentation errors JSON file.

        INV-EXP-11 enforcement site: this method ALWAYS writes
        `instrument_errors.json` to the results directory when it runs --
        populated with one entry per APK that carries
        `task.result.instrument_errors`, or an empty JSON object `{}` when no
        task reported any error. This realizes Scenario "Mixed instrumentation
        results filter downstream phases": given N APKs that failed
        instrumentation, the file contains N entries with accurate phase
        information.

        WHY the empty `{}` still matters: downstream analysis scripts read
        this file to exclude non-instrumented APKs from MOP coverage
        denominators. A present-but-empty file signals "every completed APK
        was instrumented cleanly" and is distinct from a missing file. (Note:
        `generate_reports` only reaches this method when at least one task
        completed -- see its early-return caveat.)

        Args:
            completed_tasks: List of completed tasks to process
        """
        with self.logger.with_context(phase="instrument_errors_json_generation"):
            self.logger.info(
                LOG_START.format(phase="instrumentation errors JSON generation")
            )

            # Collect instrumentation errors, keyed by APK name -- one entry
            # per APK that reported errors (Scenario "Mixed instrumentation
            # results filter downstream phases": N failed APKs -> N entries).
            instrument_errors = {}

            for task in completed_tasks:
                if (
                    hasattr(task.result, "instrument_errors")
                    and task.result.instrument_errors
                ):
                    apk_name = task.config.apk_name
                    instrument_errors[apk_name] = task.result.instrument_errors

            # Always write the file, with errors or as an empty {} object
            # (INV-EXP-11: PostProcessor MUST produce instrument_errors.json
            # even when no errors occurred).
            errors_file = os.path.join(self.results_dir, "instrument_errors.json")

            with open(errors_file, "w", encoding="utf-8") as f:
                json.dump(instrument_errors, f, indent=2, ensure_ascii=False)

            if instrument_errors:
                self.logger.info(
                    f"Instrumentation errors JSON generated: {errors_file}"
                )
            else:
                self.logger.info("No instrumentation errors found - empty file created")

    def _generate_experiment_metadata(self, completed_tasks: List[Any]) -> None:
        """
        Create basic experiment metadata for logging and tracking.

        Builds an in-memory summary (total_tasks, unique_apks, unique_tools,
        completion_time) used only for logging and the
        `get_experiment_metadata()` accessor. It is never persisted as result
        data: persisted experiment results are owned by rv-platform, so
        keeping this in memory is consistent with INV-EXP-02. Failure here is
        non-fatal -- it is caught and logged as a warning so it cannot abort
        post-processing.

        Args:
            completed_tasks: List of completed tasks to summarize
        """
        try:
            from datetime import datetime

            # Calculate basic statistics
            total_tasks = len(completed_tasks)
            unique_apks = len(set(task.config.apk_name for task in completed_tasks))
            unique_tools = len(
                set(
                    task.config.tool_config.get_full_tool_name()
                    for task in completed_tasks
                )
            )

            # Store metadata for logging
            self.experiment_metadata = {
                "total_tasks": total_tasks,
                "unique_apks": unique_apks,
                "unique_tools": unique_tools,
                "completion_time": datetime.now().isoformat(),
            }

            self.logger.info(
                f"Experiment metadata: {total_tasks} tasks, {unique_apks} APKs, {unique_tools} tools"
            )

        except Exception as e:
            self.logger.warning(f"Failed to create experiment metadata: {e}")

    def get_experiment_metadata(self) -> Dict[str, Any]:
        """
        Get the current experiment metadata.

        Returns a copy of the in-memory summary built by
        `_generate_experiment_metadata`. This is logging/diagnostic data only
        and is not persisted result data (INV-EXP-02: rv-platform owns
        persisted results).

        Returns:
            Dictionary with keys:
            - "total_tasks" (int): Number of completed tasks summarized
            - "unique_apks" (int): Distinct APK names across completed tasks
            - "unique_tools" (int): Distinct full tool names across completed tasks
            - "completion_time" (str): ISO-8601 timestamp when metadata was built
            Empty dict if metadata has not been generated yet.
        """
        return self.experiment_metadata.copy()
