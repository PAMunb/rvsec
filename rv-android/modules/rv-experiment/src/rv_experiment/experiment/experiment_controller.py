"""
Experiment controller for RV-Android experiments.

Orchestrate three-phase experiment workflow (pre-processing, execution,
post-processing) with clean separation of concerns. rv-experiment handles
orchestration only; rv-platform handles all task execution and result processing.
"""

import os
from datetime import datetime
from typing import List

import rv_experiment.constants as rv_cte
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVExperimentExecutionError
from rv_android_core.util.logging.constants import (
    CONTEXT_COMPONENT,
    LOG_COMPLETE,
    LOG_ERROR,
    LOG_START,
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_experiment.config import ExperimentConfig
from rv_experiment.experiment.workflow.execution_controller import ExecutionController
from rv_experiment.experiment.workflow.post_processor import PostProcessor
from rv_experiment.experiment.workflow.pre_processor import PreProcessor


class ExperimentController:
    """Orchestrate three-phase experiment workflow for Android testing.

    Implements the "Three-Phase Workflow" requirement (FR15, NFR08): this is
    the sole facade over pre-processing, execution, and post-processing, and it
    is where the experiment domain's core invariants are enforced.

    ### Role in the System:
    Central orchestrator that coordinates experiment lifecycle without
    performing task execution itself. Delegates pre-processing to PreProcessor,
    execution to ExecutionController (which wraps rv-platform), and
    post-processing to PostProcessor.

    ### Architectural Decisions (spec-anchored):
    - Enforces INV-EXP-02: no data transfer from rv-platform back to
      rv-experiment. Results stay in rv-platform; this controller reads only
      the aggregate success/failure status returned by ExecutionController.
    - Enforces INV-EXP-01: pre-processing (monitor generation, APK
      instrumentation, static analysis) runs to completion before execution
      begins, and execution completes before post-processing starts.
    - Enforces INV-EXP-11 (via PostProcessor): post-processing is limited to
      basic diagnostics (instrument_errors.json + completion metadata). CSV/JSON
      result generation is handled entirely by rv-platform.

    ### Key Features:
    - Three-phase workflow: pre-processing, execution, post-processing (FR15)
    - Experiment configuration persistence for reproducibility (NFR08;
      Scenario: "JSON config auto-save on experiment run")
    - Tool creation via ToolFactory with variant support
    - Resume support through rv-platform task tracking (FR16-ext)

    ### Integration Points:
    - PreProcessor: Monitor generation, APK instrumentation, static analysis
    - ExecutionController: rv-platform coordination for task execution
    - PostProcessor: Completion diagnostics and error tracking
    - ToolFactory: Tool instance creation from ToolConfig specifications
    """

    # =========================================================================
    # Lifecycle: __init__ -> run() -> [Phase 1 -> Phase 2 -> Phase 3]
    #
    # Phase 1: Pre-processing — generate monitors, instrument APKs, run static analysis
    # Phase 2: Execution — delegate to rv-platform for task execution
    # Phase 3: Post-processing — generate diagnostics and summary reports
    #
    # INV-EXP-01: this strict pre->exec->post order is mandatory — Phase 2 never
    # starts before Phase 1 completes, Phase 3 never before Phase 2 completes.
    # Within Phase 1, each step is independently skippable via ExperimentConfig
    # flags (INV-EXP-07). On resume, all Phase 1 steps are auto-skipped because
    # the CLI forces the three flags to False (INV-EXP-13 — artifacts already exist).
    # =========================================================================

    @ErrorHandler.handle_errors(
        component="ExperimentController", phase="initialization"
    )
    def __init__(self, config: ExperimentConfig, experiment_id: str = None):
        """Initialize experiment controller with workflow components.

        Args:
            config: Experiment configuration defining tools, APKs, timeouts,
                and processing flags
            experiment_id: Unique experiment identifier. Defaults to
                current timestamp in YYYYMMDD_HHMMSS format.

        State:
            config: Experiment configuration instance
            experiment_id: Unique identifier for this experiment run
            results_dir: Directory path for experiment results
            pre_processor: PreProcessor for monitor generation and instrumentation
            execution_controller: ExecutionController wrapping rv-platform
            post_processor: PostProcessor for completion diagnostics
        """
        self.config = config
        self.experiment_id = experiment_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        # INV-EXP-14 (flat results dir): use config.results_dir verbatim — never
        # append config.name or any subdirectory. config.results_dir already
        # contains the full experiment path (e.g., "results/smoke_exp" or
        # "results/cli_experiment_20260212_...") built by __main__.py before it
        # calls execute_with_config(). Appending here would produce the doubled
        # "results/my_experiment/my_experiment" path that breaks resume detection.
        self.results_dir = config.results_dir or f"./{rv_cte.RESULTS_DIR}"
        os.makedirs(self.results_dir, exist_ok=True)

        # Initialize logging and error handling
        self.logging_manager = LoggingManager.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.experiment.controller",
            {CONTEXT_COMPONENT: "ExperimentController"},
        )

        # Initialize the three workflow components — one per phase (FR15 facade).
        # PreProcessor handles Phase 1 (monitor gen, instrumentation, static analysis).
        # ExecutionController wraps rv-platform for Phase 2 (task execution).
        # PostProcessor generates Phase 3 diagnostics (instrumentation errors, completion).
        # Each component is stateless across phases — no data flows between them,
        # reinforcing the one-way experiment->platform contract of INV-EXP-02.
        self.pre_processor = PreProcessor(config)
        self.execution_controller = ExecutionController(config)
        self.post_processor = PostProcessor(self.results_dir)

        self.logger.info(
            f"Experiment '{self.config.name}' initialized: {self.results_dir}"
        )

    @ErrorHandler.handle_errors(component="ExperimentController", phase="execution")
    def run(self) -> bool:
        """Execute the complete three-phase experiment workflow.

        Realizes FR15 and enforces INV-EXP-01 (strict pre->exec->post ordering):
        Phase 1 (pre-processing) runs monitor generation, APK instrumentation,
        and static analysis based on config flags; Phase 2 (execution) delegates
        to rv-platform via ExecutionController; Phase 3 (post-processing)
        generates completion diagnostics. The phases run in this fixed order and
        Phase 3 executes even when Phase 2 reports failure (see below).

        Failure handling maps to the spec scenarios: an execution failure sets
        the return to False (Scenario: "Execution Phase Failure Propagation" —
        the exception surfaces from ExecutionController and is caught here), while
        pre-processing failures do not abort (INV-EXP-08; Scenario: "Pre-Processing
        Failure Does Not Abort Experiment").

        Returns:
            True if all phases completed successfully, False if execution
            had failures (pre-processing errors raise exceptions instead)
        """
        with self.logger.with_context(
            experiment_id=self.experiment_id, phase="complete_experiment"
        ):
            self.logger.info(LOG_START.format(phase=f"experiment {self.experiment_id}"))

            # Save experiment configuration to results directory for reproducibility
            # (NFR08; Scenario: "JSON config auto-save on experiment run"). The JSON
            # snapshot captures the exact config used, is written in the unified
            # ToolConfig format, and is re-loadable via `rv-experiment run --config`,
            # enabling identical re-runs and audit trails for published results.
            self.save_experiment_config()

            try:
                success = True

                # Phase 1 of INV-EXP-01: Pre-processing — generate monitors,
                # instrument APKs, run static analysis. Each step is controlled by a
                # separate flag in ExperimentConfig and respected per INV-EXP-07.
                # When resuming, all three flags are forced to False by the CLI layer
                # (INV-EXP-13) because artifacts (monitors, instrumented APKs, static
                # analysis JSON) already exist from the first run — re-running would
                # overwrite them and could desync the coverage denominator.
                self.logger.info("Starting pre-processing phase")
                self._run_pre_processing()

                # Phase 2 of INV-EXP-01: Execution — delegate to rv-platform via
                # ExecutionController. rv-platform handles the full task lifecycle:
                # emulator management, tool execution, logcat capture, coverage
                # tracking, and CSV/JSON result generation. Per INV-EXP-02 no result
                # data transfers back — only the aggregate success/failure status.
                # The run_execution flag (CLI --skip-execution) lets Phase 2 be
                # bypassed while still producing Phase 3 diagnostics.
                if self.config.run_execution:
                    self.logger.info("Starting execution phase")
                    execution_success = self._run_execution()

                    if not execution_success:
                        self.logger.warning("Execution phase completed with issues")
                        success = False
                else:
                    self.logger.info("Execution phase skipped (--skip-execution)")

                # Phase 3 of INV-EXP-01: Post-processing — generate diagnostics and
                # summary reports. Intentionally lightweight: only produces the
                # instrument_errors.json (always written, even if empty — INV-EXP-11)
                # and a completion timestamp. All heavy result processing (CSV,
                # coverage reports, MOP violation summaries) happens in rv-platform
                # during Phase 2. Phase 3 runs unconditionally — even when Phase 2 was
                # skipped or produced no APKs (Scenario: "No APKs Available for Execution").
                self.logger.info("Starting post-processing phase")
                self.post_processor.process()

                self.logger.info(f"Experiment completed: {self.experiment_id}")
                self.logger.info(
                    LOG_COMPLETE.format(phase=f"experiment {self.experiment_id}")
                )
                return success

            except Exception as e:
                self.logger.error(
                    LOG_ERROR.format(
                        phase=f"experiment {self.experiment_id}", error=str(e)
                    )
                )
                self.logger.error(f"Experiment failed: {self.experiment_id}")

                return False

    def _run_pre_processing(self):
        """Execute pre-processing phase with instrumentation error tracking.

        Passes the three per-step flags straight through so PreProcessor can
        honor INV-EXP-07 (skip the corresponding step and log a warning).
        """
        # Delegate to PreProcessor with per-step flags from ExperimentConfig.
        # Each flag can be individually disabled via CLI (--skip-monitors, etc.)
        # per INV-EXP-07, or automatically disabled on resume (INV-EXP-13 forces
        # all three to False).
        self.pre_processor.process(
            generate_monitors=self.config.generate_monitors,
            instrument=self.config.instrument_apks,
            static_analysis=self.config.run_static_analysis,
        )

    def _run_execution(self) -> bool:
        """Execute tasks through rv-platform coordination.

        Retrieve instrumented APKs from pre-processor, create tool instances
        via ToolFactory, configure ExecutionController, and delegate execution
        to rv-platform. This is Phase 2 of INV-EXP-01 and the site of two spec
        scenarios: the empty-APK guard (Scenario: "No APKs Available for
        Execution") and the failure wrap (Scenario: "Execution Phase Failure
        Propagation").

        Returns:
            True if all tasks completed successfully, False if no APKs are
            available for execution

        Raises:
            RVExperimentExecutionError: If execution setup or platform
                coordination fails. Per Scenario "Execution Phase Failure
                Propagation", any exception from ExecutionController.run() is
                caught and re-raised as this typed error; run() then catches it,
                logs it, and returns False.
        """
        try:
            # Get instrumented APKs from the pre-processing output directory.
            # If instrumentation was skipped (resume or --skip-instrument), this
            # falls back to original APKs from apks_dir. Either way, these APKs
            # are what rv-platform will install on emulators for task execution.
            apks = self.pre_processor.get_instrumented_apks()

            # Scenario: "No APKs Available for Execution" — when get_instrumented_apks()
            # returns an empty list (no instrumented APKs found and no original APKs
            # available), log and return False WITHOUT creating a Platform instance.
            # Phase 3 still runs afterward (run() calls post_processor.process()
            # unconditionally), so diagnostics are produced even on this early return.
            if not apks:
                self.logger.error("No APKs available for execution")
                return False

            # Get configured tools
            tools = self._get_configured_tools()
            if not tools:
                self.logger.error("No valid tools found for execution")
                return False

            # Two-step lifecycle: setup() translates ExperimentConfig into PlatformConfig,
            # then run() delegates to Platform.run() which handles everything from here.
            # tool_configs is passed separately because it carries variant info that
            # would be lost if we derived configs from the tool instances alone.
            self.execution_controller.setup(
                apks=apks,
                repetitions=self.config.repetitions,
                timeouts=self.config.timeouts,
                tools=tools,
                tool_configs=self.config.tool_configs,
                no_window=getattr(self.config, "no_window", False),
                results_dir=self.results_dir,
            )

            # Execute through rv-platform. Platform.run() handles emulator lifecycle,
            # tool execution, logcat capture, and result processing (CSV/JSON).
            # On resume, rv-platform loads tasks.json and skips completed tasks.
            success = self.execution_controller.run()
            return success

        except Exception as e:
            # Scenario: "Execution Phase Failure Propagation" — wrap any platform
            # failure in the domain-typed RVExperimentExecutionError so run()'s
            # handler can distinguish execution faults, log them, and return False
            # (never re-raising past run()). The `from e` chain preserves the
            # original cause for debugging.
            self.logger.error(f"Execution phase failed: {e}")
            raise RVExperimentExecutionError(f"Execution failed: {e}") from e

    def _get_configured_tools(self) -> List[AbstractTool]:
        """Create tool instances from configured ToolConfig specifications.

        Iterate over tool_configs and use ToolFactory to instantiate each tool.
        Tools that fail to instantiate are logged as warnings and skipped.

        Returns:
            List of successfully created AbstractTool instances
        """
        tools = []

        try:
            # Lazy import: ToolFactory is only needed when we actually create tools.
            # This avoids import-time side effects when rv-tools is not installed
            # (e.g., during unit testing or pre-processing-only runs).
            from rv_tools import ToolFactory

            # Create ToolFactory instance
            tool_factory = ToolFactory()

            for tool_config in self.config.tool_configs:
                try:
                    # ToolConfig from rv-android-core is used directly by ToolFactory
                    tool = tool_factory.create_tool(tool_config)
                    tools.append(tool)
                    self.logger.debug(f"Configured tool: {tool_config.name}")

                except Exception as e:
                    self.logger.warning(
                        f"Failed to configure tool {tool_config.name}: {e}"
                    )

        except ImportError:
            self.logger.error("Tool factory not available")

        return tools

    def get_experiment_status(self) -> dict:
        """Get the current status of the experiment.

        Returns:
            Dictionary with keys:
                - experiment_id: Unique experiment identifier
                - results_dir: Path to results directory
                - execution_method: Workflow type identifier
        """
        return {
            "experiment_id": self.experiment_id,
            "results_dir": self.results_dir,
            "execution_method": "clean_three_phase_workflow",
        }

    def save_experiment_config(self) -> None:
        """Save the experiment configuration to the results directory.

        Realizes NFR08 (reproducibility) and the Scenario "JSON config auto-save
        on experiment run": writes the full ExperimentConfig as
        experiment_config.json in the results directory using the unified
        ToolConfig format (variant: str, not variants: List[str]). The saved file
        is re-loadable via `rv-experiment run --config <path>`, enabling identical
        re-runs and audit trails. A save failure is logged as a warning and does
        not abort the experiment — the config snapshot is a diagnostic aid, not a
        precondition for execution.
        """
        config_file = os.path.join(self.results_dir, "experiment_config.json")

        try:
            self.config.save_to_file(config_file)
            self.logger.info(f"Experiment configuration saved to {config_file}")
        except Exception as e:
            self.logger.warning(f"Failed to save experiment configuration: {e}")


def execute_with_config(config: ExperimentConfig) -> bool:
    """Execute experiment with provided configuration.

    Create an ExperimentController and run the three-phase workflow.
    This is the primary entry point used by the CLI and programmatic callers.

    Args:
        config: Validated ExperimentConfig with tools, APKs, timeouts,
            and processing flags

    Returns:
        True if experiment completed successfully, False otherwise
    """
    controller = ExperimentController(config)
    return controller.run()
