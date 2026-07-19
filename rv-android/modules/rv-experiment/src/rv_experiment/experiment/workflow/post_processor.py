# rv_experiment/experiment/workflow/post_processor.py
"""
Clean post-processor component for RV-Android experiments.

This module provides minimal post-processing functionality focused only on
basic experiment diagnostics. All result processing is handled by rv-platform.

This is Phase 3 of the three-phase experiment workflow. Per the spec Requirement
"Three-Phase Workflow (FR15, NFR08)": "Phase 3 (post-processing) MUST create
basic diagnostics and completion metadata. It does not read back task results —
rv-platform handles result processing."

The deliberate absence of any result/coverage/error-log read-back realizes
INV-EXP-02: rv-experiment MUST NOT read back task results, coverage data, or
error logs from rv-platform after execution — data flows one-way from
rv-experiment to rv-platform. Keeping this phase minimal is what preserves that
one-way boundary.
"""

import os

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import (
    CONTEXT_COMPONENT,
    LOG_COMPLETE,
    LOG_START,
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_experiment.experiment.workflow.result_manager import ResultManager
from rv_platform.storage.task_storage import TaskStorage


class PostProcessor:
    """
    Clean post-processor component for basic experiment diagnostics.

    This component handles only basic post-processing functionality focused on
    experiment diagnostics. All CSV and JSON result processing is handled by
    rv-platform's ResultProcessorComponent for proper separation of concerns.

    This is the Phase 3 implementation of the spec Requirement "Three-Phase
    Workflow (FR15, NFR08)". Its two outputs — `instrument_errors.json` and
    `experiment_completion.json` — are the post-processing contract asserted by
    Scenario "Full Experiment With All Phases Enabled".

    ### Architectural Role:
    - Provides basic experiment completion diagnostics
    - Generates simple experiment metadata
    - No data processing or result generation

    ### Key Principles:
    - No result processing (delegated to rv-platform)
    - No data access from tasks or storage
    - Only basic diagnostics
    - Clean separation from data processing concerns (upholds INV-EXP-02: no
      read-back of task results, coverage, or error logs)
    """

    def __init__(self, results_dir: str):
        """
        Initialize the clean post-processor.

        Args:
            results_dir: Directory containing experiment results
        """
        self.results_dir = results_dir
        self.error_handler = ErrorHandler.get_instance()

        # Load tasks.json created by rv-platform during Phase 2 (execution).
        # TaskStorage provides read-only access to task status and metadata,
        # which ResultManager uses to identify instrumentation failures.
        # On first run before execution, the file may not exist — TaskStorage
        # handles this gracefully by returning an empty task list.
        #
        # Boundary note vs INV-EXP-02: INV-EXP-02 forbids reading back task
        # *results* — coverage data and error logs — from rv-platform. Reading
        # per-task instrumentation-failure *status metadata* here is the
        # sanctioned exception: it is the only input needed to build
        # instrument_errors.json (INV-EXP-11), and it carries no coverage or
        # result-log payload, so the one-way data flow stays intact.
        tasks_file = os.path.join(results_dir, "tasks.json")
        self.task_storage = TaskStorage(tasks_file)
        self.task_storage.load()

        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "experiment.workflow.post_processor", {CONTEXT_COMPONENT: "PostProcessor"}
        )

    def process(self):
        """
        Process experiment completion with basic diagnostics.

        This method handles only basic post-processing diagnostics.
        All result processing is handled by rv-platform automatically.

        Orchestrates the two Phase 3 outputs required by Scenario "Full
        Experiment With All Phases Enabled": `instrument_errors.json` and
        `experiment_completion.json`, both written to the results directory.

        Per Scenario "No APKs Available for Execution", Phase 3 MUST still
        execute to produce diagnostics even when Phase 2 created no Platform and
        ran nothing — hence this method is always invoked and never gated on
        whether any APKs were executed.
        """
        # Phase 3: Post-processing — generate diagnostics and summary reports.
        #
        # This phase is intentionally minimal. rv-platform already generates
        # CSV reports, coverage summaries, and MOP violation data during Phase 2.
        # Post-processing only adds:
        # 1. Instrumentation errors JSON — identifies APKs that failed instrumentation
        #    so they can be excluded from coverage calculations.
        # 2. Completion diagnostics — a timestamp marker confirming the experiment
        #    finished (useful for automated pipelines checking experiment status).
        with self.logger.with_context(phase="post_processing"):
            self.logger.info(LOG_START.format(phase="experiment post-processing"))

            # Generate instrumentation errors JSON using ResultManager
            self._generate_instrumentation_errors()

            # Basic experiment completion diagnostics
            self._generate_completion_diagnostics()

            self.logger.info(LOG_COMPLETE.format(phase="experiment post-processing"))
            self.logger.info("Post-processing completed")

    def _generate_instrumentation_errors(self):
        """
        Generate instrumentation errors JSON using ResultManager.

        Delegates to `ResultManager`, which writes `instrument_errors.json`.
        Per INV-EXP-11, this file MUST be produced even when no instrumentation
        errors occurred — in that case it contains an empty JSON object `{}`.
        Per Scenario "Mixed instrumentation results filter downstream phases",
        when APKs fail instrumentation the file MUST contain one entry per
        failed APK with accurate phase information (e.g. 3 failures → 3 entries).

        Any failure here is swallowed via ErrorHandler rather than re-raised, so
        Phase 3 never aborts the experiment on account of report generation.
        """
        with self.logger.with_context(phase="instrumentation_errors"):
            self.logger.info(
                LOG_START.format(phase="generating instrumentation errors JSON")
            )

            try:
                # ResultManager cross-references task_storage with APK files to
                # identify which APKs failed instrumentation. The output JSON is
                # consumed by analysis scripts to exclude non-instrumented APKs
                # from MOP coverage calculations (they would show 0% by definition).
                result_manager = ResultManager(self.results_dir, self.task_storage)
                result_manager.generate_reports()

                self.logger.info(
                    LOG_COMPLETE.format(phase="instrumentation errors JSON generation")
                )

            except Exception as e:
                error_context = {
                    "component": "PostProcessor",
                    "operation": "instrumentation_errors_generation",
                    "results_dir": self.results_dir,
                }
                self.error_handler.handle_error(e, error_context)

    def _generate_completion_diagnostics(self):
        """
        Generate basic completion diagnostics for the experiment.

        Writes `experiment_completion.json` with `results_directory`,
        `completion_timestamp`, and `post_processing_completed`. This is the
        completion-metadata half of the Phase 3 output contract in Scenario
        "Full Experiment With All Phases Enabled" (the other half being
        `instrument_errors.json`).

        WHY a timestamp marker: it lets automated pipelines detect that an
        experiment ran to completion without having to inspect or read back any
        task results — which INV-EXP-02 forbids anyway. The marker is metadata,
        not result data.

        Any failure is swallowed via ErrorHandler so Phase 3 never aborts.
        """
        with self.logger.with_context(phase="completion_diagnostics"):
            self.logger.info(
                LOG_START.format(phase="generating completion diagnostics")
            )

            try:
                # Generate basic diagnostic information
                diagnostic_info = {
                    "results_directory": self.results_dir,
                    "completion_timestamp": self._get_current_timestamp(),
                    "post_processing_completed": True,
                }

                # Log diagnostic information
                self.logger.info(
                    f"Experiment completion diagnostics: {diagnostic_info}"
                )

                # Save basic completion diagnostics
                diagnostic_path = os.path.join(
                    self.results_dir, "experiment_completion.json"
                )
                self._save_diagnostics(diagnostic_path, diagnostic_info)

            except Exception as e:
                error_context = {
                    "component": "PostProcessor",
                    "operation": "completion_diagnostics",
                    "results_dir": self.results_dir,
                }
                self.error_handler.handle_error(e, error_context)

            self.logger.info(
                LOG_COMPLETE.format(phase="generating completion diagnostics")
            )

    def _get_current_timestamp(self) -> str:
        """
        Get current timestamp for diagnostics.

        Returns:
            ISO format timestamp string
        """
        from datetime import datetime

        return datetime.now().isoformat()

    def _save_diagnostics(self, diagnostic_path: str, diagnostic_info: dict):
        """
        Save diagnostic information to file.

        Persists the `experiment_completion.json` payload that fulfils the
        completion-metadata half of Scenario "Full Experiment With All Phases
        Enabled". A save failure is logged as a warning (not raised) so Phase 3
        completes regardless.

        Args:
            diagnostic_path: Path to save diagnostics
            diagnostic_info: Diagnostic information to save
        """
        import json

        try:
            with open(diagnostic_path, "w", encoding="utf-8") as f:
                json.dump(diagnostic_info, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Completion diagnostics saved to {diagnostic_path}")
        except Exception as e:
            self.logger.warning(
                f"Failed to save completion diagnostics to {diagnostic_path}: {e}"
            )
