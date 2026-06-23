# rv_platform/platform.py
"""
Main Platform class for rv-platform.

This module provides the primary interface for executing Android experiments
through the rv-platform system.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task, TaskConfiguration, TaskFactory
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_platform.components.coverage import CoverageComponent
from rv_platform.components.emulator import EmulatorComponent
from rv_platform.components.logcat import LogcatComponent
from rv_platform.components.result_processor import ResultProcessorComponent
from rv_platform.components.static_analysis import StaticAnalysisComponent
from rv_platform.components.tool_execution import ToolExecutionComponent
from rv_platform.config.platform_config import PlatformConfig
from rv_platform.execution.executor import TaskExecutor
from rv_platform.storage.task_storage import ExperimentMetadata, TaskStorage
from rv_tools import ToolFactory


class Platform:
    """
    Main entry point for rv-platform execution.

    ### Architectural Decisions:
    - Provides simple, clean interface for standalone usage
    - Manages task generation and execution coordination
    - Integrates with existing rv-android-core infrastructure
    ### Role in the System:
    - Discovers APKs and generates tasks based on configuration
    - Orchestrates task execution with proper resource management
    - Collects and aggregates basic task-level results
    - Provides progress reporting through logging
    """

    def __init__(self, config: PlatformConfig):
        """
        Initialize the platform with configuration.

        Validate dependencies, set up logging and error handling, initialize
        task storage for persistent tracking, and prepare the tool factory.

        Args:
            config: Platform configuration defining APKs, tools, timeouts, and
                output directories.

        State:
            config: Validated PlatformConfig instance.
            task_storage: TaskStorage loaded from results_dir/tasks.json for
                experiment continuation support.
            tasks: In-memory list of Task objects for current execution.
            tool_factory: ToolFactory for creating configured tool instances.
            _skipped_count: Number of tasks skipped during resume (from
                previous completed runs).

        Raises:
            ValueError: If configuration dependencies are invalid (no APKs,
                empty tool names).
        """
        self.config = config

        # Validate early, before any resources are allocated. This catches
        # misconfigurations (empty APK dir, invalid tool names) before we
        # create loggers, storage files, or factory instances.
        self.config.validate_dependencies()

        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_platform.platform", {CONTEXT_COMPONENT: "Platform"}
        )

        # Error handler
        self.error_handler = ErrorHandler.get_instance()

        # Task management with persistent storage
        self.task_factory = TaskFactory(Task)

        # TaskStorage is the persistence backbone for experiment resume. On first
        # run, load() finds no file and starts empty. On subsequent runs, load()
        # deserializes all previously completed tasks from tasks.json so that
        # _skip_completed_tasks() can identify which work units are already done.
        tasks_file = os.path.join(config.results_dir, "tasks.json")
        self.task_storage = TaskStorage(tasks_file, self.task_factory)
        self.task_storage.load()

        # In-memory task list for the CURRENT session only. After _skip_completed_tasks(),
        # this contains only pending tasks — previously completed tasks live only in
        # TaskStorage. This separation is intentional: self.tasks drives the execution
        # loop, while TaskStorage drives result processing (which needs ALL sessions).
        self.tasks: List[Task] = []
        self._skipped_count: int = 0

        # ToolFactory uses the ToolRegistry (populated at import time via __init__.py)
        # to create configured tool instances. Each task gets a fresh tool instance
        # because tools may hold per-execution state (process handles, temp files).
        self.tool_factory = ToolFactory()

        self.logger.info(f"Platform initialized with config: {self.config.apks_dir}")

    def run(self) -> Dict[str, Any]:
        """
        Execute the platform workflow.

        Generate tasks from APK/tool/timeout combinations, skip previously
        completed tasks (resume support), execute remaining tasks, process
        results into CSV/JSON, and return an execution summary.

        Returns:
            Summary dictionary with keys:
                - total_tasks: Number of tasks executed in this session.
                - successful_tasks: Count of successful tasks.
                - failed_tasks: Count of failed tasks.
                - skipped_tasks: Count of tasks skipped from previous runs.
                - success_rate: Ratio of successful to total tasks.
                - total_execution_time: Sum of all task execution times.
                - average_execution_time: Mean execution time per task.
                - results: List of per-task result dictionaries.

        Raises:
            Exception: Re-raised after logging if any phase of execution fails.
        """
        try:
            self.logger.info("Starting platform execution")

            # --- Phase 1: Task Generation ---
            # Build the full task matrix: APKs x tools x repetitions x timeouts.
            # All possible tasks are generated upfront so resume logic can diff
            # against previously completed tasks.
            self._generate_tasks()

            # Store experiment metadata for continuation support.
            # The config checksum enables detecting config changes between runs,
            # so we can warn if a resumed experiment has different parameters.
            config_dict = self.config.model_dump(mode="json")
            metadata = ExperimentMetadata.create_from_config(
                experiment_id=str(self.config.results_dir), config_dict=config_dict
            )
            self.task_storage.set_experiment_metadata(metadata)

            # --- Phase 2: Resume Check ---
            # Match generated tasks against completed tasks in TaskStorage by
            # identity tuple (apk, tool, variant, repetition, timeout). Matched
            # tasks are removed from self.tasks so they are not re-executed.
            self._skip_completed_tasks()

            # --- Phase 3: Execution ---
            results = self._execute_tasks()

            # --- Phase 4: Result Processing ---
            # Generate CSV/JSON from ALL completed tasks (previous + current).
            # Uses task_storage.get_completed_tasks() as the single source of truth,
            # which merges tasks from all sessions. Using self.tasks here would only
            # include tasks from the current session, producing incomplete output on
            # resume. Skippable for debugging or standalone result processing later.
            if not getattr(self.config, "skip_result_processing", False):
                self._process_results()

            # --- Phase 5: Summary ---
            summary = self._generate_summary(results, self._skipped_count)

            self.logger.info("Platform execution completed successfully")
            return summary

        except Exception as e:
            self.error_handler.handle_error(e, {"phase": "platform_execution"})
            self.logger.error(f"Platform execution failed: {e}")
            raise

    def _generate_tasks(self) -> None:
        """Generate tasks based on configuration."""
        self.logger.info("Generating tasks")

        # Discover APKs
        apks = self._discover_apks()
        self.logger.info(f"Discovered {len(apks)} APK files")

        # Cartesian product: every APK x tool x repetition x timeout produces one task.
        # This exhaustive generation is intentional: resume logic later filters out
        # tasks that were already completed, so the full matrix must be known upfront.
        task_count = 0
        for apk_path in apks:
            apk_name = apk_path.name

            # Create app instance
            app = App(str(apk_path))

            for tool_config in self.config.tools:
                for repetition in range(1, self.config.repetitions + 1):
                    for timeout in self.config.timeouts:
                        # device_serial is injected by ExecutionController when running
                        # in parallel containers. Each container gets a unique emulator
                        # port (5554, 5556, ...) to avoid port conflicts.
                        device_id = tool_config.parameters.get(
                            "device_serial", "emulator-5554"
                        )

                        task_config = TaskConfiguration(
                            apk_name=apk_name,
                            repetition=repetition,
                            timeout=timeout,
                            tool_config=tool_config,
                            no_window=self.config.no_window,
                            device_id=device_id,
                        )

                        # Create task
                        task = self.task_factory.create_task(task_config)
                        task.set_app(app)

                        # Initialize task
                        task.initialize(self.config.results_dir)

                        self.tasks.append(task)
                        task_count += 1

        self.logger.info(f"Generated {task_count} tasks")

    def _skip_completed_tasks(self) -> None:
        """
        Skip tasks already completed in a previous run (resume support).

        Match tasks by identity tuple (apk_name, tool_name, variant, repetition,
        timeout) against completed tasks in TaskStorage. Log a warning if the
        config checksum differs from the previous run. Update _skipped_count
        and filter self.tasks in place.
        """
        completed_tasks = self.task_storage.get_completed_tasks()
        if not completed_tasks:
            return

        # Validate configuration consistency via checksum
        config_dict = self.config.model_dump(mode="json")
        if not self.task_storage.check_continuation_compatibility(config_dict):
            stored = (
                self.task_storage.experiment_metadata.config_checksum[:8]
                if self.task_storage.experiment_metadata
                else "unknown"
            )
            current = hashlib.sha256(
                json.dumps(config_dict, sort_keys=True).encode()
            ).hexdigest()[:8]
            self.logger.warning(
                f"Config changed since last run (stored: {stored}, current: {current}) — resuming anyway"
            )

        # Identity tuple uniquely identifies a task across sessions. Two tasks
        # with the same identity are considered the "same work unit" regardless
        # of task_id (which is a UUID generated fresh each run).
        def task_identity(task):
            tc = task.config
            return (
                tc.apk_name,
                tc.tool_config.name,
                tc.tool_config.variant,
                tc.repetition,
                tc.timeout,
            )

        completed_ids = {task_identity(t) for t in completed_tasks}

        original_count = len(self.tasks)
        self.tasks = [t for t in self.tasks if task_identity(t) not in completed_ids]
        skipped = original_count - len(self.tasks)
        self._skipped_count = skipped

        if skipped > 0:
            self.logger.info(
                f"Resume: skipped {skipped} already-completed tasks "
                f"({len(self.tasks)} remaining)"
            )

    def _discover_apks(self) -> List[Path]:
        """
        Discover APK files in the configured directory.

        If apks_filter_file is set, only APKs whose filename appears in the
        filter file are included.

        Returns:
            List of APK file paths
        """
        apks_dir = Path(self.config.apks_dir)
        apk_files = list(apks_dir.glob("*.apk"))

        if not apk_files:
            raise ValueError(f"No APK files found in directory: {self.config.apks_dir}")

        if self.config.apks_filter_file:
            allowed = set(
                Path(self.config.apks_filter_file).read_text().strip().splitlines()
            )
            apk_files = [f for f in apk_files if f.name in allowed]
            if not apk_files:
                raise ValueError(
                    f"No APKs match filter: {self.config.apks_filter_file}"
                )
            self.logger.info(f"Filtered to {len(apk_files)} APKs from filter file")

        return sorted(apk_files)

    def _execute_tasks(self) -> List[Dict[str, Any]]:
        """
        Execute all generated tasks sequentially.

        For each task: load the tool, create a TaskExecutor with registered
        components (StaticAnalysis, Emulator, Logcat, Coverage, ToolExecution),
        execute, and persist the result to TaskStorage. Failed tasks are caught,
        marked as ERROR, and included in the results.

        Returns:
            List of per-task result dictionaries with keys: task_id, apk_name,
            tool_name, repetition, timeout, success, execution_time,
            error_message.
        """
        self.logger.info(f"Executing {len(self.tasks)} tasks")
        results = []

        for i, task in enumerate(self.tasks, 1):
            self.logger.info(f"Executing task {i}/{len(self.tasks)}: {task}")

            try:
                # Step 1: Create a fresh tool instance per task. Tools may hold
                # per-execution state (e.g., process handles), so sharing across
                # tasks would be unsafe.
                tool = self._load_tool(task.config.tool_config)

                # Step 2: Build the TaskExecutor with its component pipeline.
                # Components are registered in a specific order that determines
                # their initialization and execution sequence inside the executor.
                executor = TaskExecutor(task, tool, task_storage=self.task_storage)

                # Registration order matters: StaticAnalysis and Coverage run outside
                # the emulator session (phases 1-2), while Emulator/Logcat/ToolExecution
                # run inside the emulator context manager (phase 3).
                components = [
                    StaticAnalysisComponent(task, self.config.apks_dir),
                    EmulatorComponent(task),
                    LogcatComponent(task, self.config.logcat_diagnostics),
                    CoverageComponent(task),
                    ToolExecutionComponent(task, tool),
                ]

                for component in components:
                    executor.register_component(component)

                # Step 3: Execute the full component lifecycle (init -> execute -> cleanup).
                success = executor.execute()

                # Step 4: Persist task result immediately after completion.
                # Atomic write ensures crash recovery: if the process dies before
                # the next task, this task's result is already on disk.
                self.task_storage.update_task(task)

                # Collect result
                result = {
                    "task_id": task.id,
                    "apk_name": task.config.apk_name,
                    "tool_name": task.config.tool_config.get_full_tool_name(),
                    "repetition": task.config.repetition,
                    "timeout": task.config.timeout,
                    "success": success,
                    "execution_time": task.result.execution_time_seconds,
                    "error_message": task.result.error_message,
                }
                results.append(result)

                self.logger.info(f"Task completed: {success}")

            except Exception as e:
                # Walk the exception chain to find the most informative message.
                # RVToolTimeoutError is treated specially: timeouts are expected
                # behavior in bounded-time experiments, not failures.
                error_message = self._extract_meaningful_error_message(e)

                self.logger.error(f"Task execution failed: {error_message}")
                task.update_state(task.result.state.__class__.ERROR, error_message)

                # Persist failed tasks too so they are not re-executed on resume.
                # This is critical: without this, a crash-and-resume cycle would
                # re-run tasks that already failed, wasting experiment time. The
                # atomic write in TaskStorage.save() guarantees this survives crashes.
                self.task_storage.update_task(task)

                result = {
                    "task_id": task.id,
                    "apk_name": task.config.apk_name,
                    "tool_name": task.config.tool_config.get_full_tool_name(),
                    "repetition": task.config.repetition,
                    "timeout": task.config.timeout,
                    "success": False,
                    "execution_time": (
                        task.result.execution_time_seconds
                        if hasattr(task.result, "execution_time_seconds")
                        else 0
                    ),
                    "error_message": error_message,
                }
                results.append(result)

        return results

    def _extract_meaningful_error_message(self, exception: Exception) -> str:
        """
        Extract a meaningful error message from an exception chain.

        Args:
            exception: The exception to extract message from

        Returns:
            A clear, user-friendly error message
        """
        from rv_android_core.util.error.exceptions import (
            RVToolExecutionError,
            RVToolTimeoutError,
        )

        # Walk through the exception chain to find the root cause
        current = exception
        while current:
            # Check for timeout scenarios
            if isinstance(current, RVToolTimeoutError):
                tool_name = getattr(current, "tool_name", "unknown tool")
                timeout_seconds = getattr(current, "timeout_seconds", None)
                if timeout_seconds:
                    return f"{tool_name} execution timed out after {timeout_seconds} seconds (expected behavior)"
                else:
                    return f"{tool_name} execution timed out (expected behavior)"

            # Check for tool execution errors
            if isinstance(current, RVToolExecutionError):
                tool_name = getattr(current, "tool_name", "unknown tool")
                return f"{tool_name}: {current.message}"

            # Check for other specific RV exceptions with meaningful messages
            if hasattr(current, "message") and current.message:
                return current.message

            # Move to the cause of the current exception
            current = getattr(current, "cause", None) or getattr(
                current, "__cause__", None
            )

        # Fallback to the original exception message
        return str(exception)

    def _load_tool(self, tool_config):
        """
        Load and configure a tool using ToolConfig specification.

        Uses ToolFactory.create_tool() with the unified ToolConfig that contains
        name, variant, and parameters. The factory handles variant resolution,
        parameter merging, and tool configuration.

        Args:
            tool_config: ToolConfig instance with tool name, variant, and parameters

        Returns:
            Configured tool instance with variant-specific parameters

        Raises:
            ValueError: If tool loading or configuration fails
        """
        from rv_android_core.domain.task import ToolConfig

        try:
            if not isinstance(tool_config, ToolConfig):
                raise ValueError(
                    f"Expected ToolConfig instance, got {type(tool_config)}"
                )

            return self.tool_factory.create_tool(tool_config)

        except Exception as e:
            name = getattr(tool_config, "name", str(tool_config))
            variant = getattr(tool_config, "variant", "unknown")
            raise ValueError(f"Failed to load tool '{name}:{variant}': {e}")

    def _generate_summary(
        self, results: List[Dict[str, Any]], skipped_count: int = 0
    ) -> Dict[str, Any]:
        """
        Generate execution summary.

        Args:
            results: List of task results from this session
            skipped_count: Number of tasks skipped from previous runs (resume)

        Returns:
            Summary dictionary
        """
        total_tasks = len(results)
        successful_tasks = sum(1 for r in results if r["success"])
        failed_tasks = total_tasks - successful_tasks

        total_time = sum(r["execution_time"] for r in results)

        summary = {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "skipped_tasks": skipped_count,
            "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0,
            "total_execution_time": total_time,
            "average_execution_time": (
                total_time / total_tasks if total_tasks > 0 else 0
            ),
            "results": results,
        }

        self.logger.info(
            f"Execution summary: {successful_tasks}/{total_tasks} tasks successful"
            f" ({skipped_count} skipped from previous runs)"
        )
        return summary

    def get_tasks(self) -> List:
        """
        Get all task objects directly (no serialization).

        Returns:
            List of Task objects with static_data preserved
        """
        return self.tasks

    def get_tasks_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary of all tasks (serialized format).

        Returns:
            List of task summaries
        """
        return [task.to_dict() for task in self.tasks]

    @ErrorHandler.handle_errors(component="Platform", phase="result_processing")
    def _process_results(self) -> None:
        """
        Generate CSV/JSON files from completed experiment tasks.

        This method processes completed tasks to generate standardized output
        files for analysis and research purposes.
        """
        self.logger.info("Processing experiment results")

        # TaskStorage is the single source of truth for result processing.
        # It merges tasks from ALL sessions: previous runs (loaded from tasks.json
        # on startup) plus the current session. Using self.tasks instead would
        # only include tasks executed NOW, producing incomplete CSV/JSON when
        # resuming an experiment. This is the key invariant for resume correctness.
        all_completed = list(self.task_storage.get_completed_tasks())
        processor = ResultProcessorComponent(all_completed, self.config.results_dir)

        # Initialize and execute result processing
        processor.initialize({})
        processor.execute({})

        # Clean up
        processor.cleanup()

        self.logger.info("Experiment results processing completed")
