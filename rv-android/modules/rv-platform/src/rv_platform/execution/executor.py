# rv_platform/execution/executor.py
"""
Task executor for RV-Platform.

Manages individual task execution through a component-based architecture
with proper lifecycle management.
"""

from typing import Any, Callable, Dict, List, Optional

from rv_android_core.domain.task import Task, TaskState
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.decorators import log_execution
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import TaskExecutionError
from rv_android_core.util.logging.constants import (
    CONTEXT_APP_NAME,
    CONTEXT_COMPONENT,
    CONTEXT_TASK_ID,
    CONTEXT_TOOL_NAME,
    LOG_COMPLETE,
    LOG_ERROR,
    LOG_START,
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_platform.components.coverage import CoverageComponent
from rv_platform.components.emulator import EmulatorComponent
from rv_platform.components.logcat import LogcatComponent
from rv_platform.components.static_analysis import StaticAnalysisComponent
from rv_platform.components.tool_execution import ToolExecutionComponent
from rv_platform.storage.task_storage import TaskStorage


@log_execution(
    logger_prefix="rv_platform.execution.executor", component_name="TaskExecutor"
)
class TaskExecutor:
    """
    Manages the execution of individual tasks within a platform workflow
    using a component-based architecture.

    ### Architectural Decisions:
    - Implements a component-based approach to task execution
    - Uses dependency injection for component management
    - Supports comprehensive error handling and performance tracking
    - Provides flexible task lifecycle management

    ### Role in the System:
    - Coordinates the detailed execution flow of individual platform tasks
    - Manages emulator interactions, app installation, and tool execution
    - Tracks and collects coverage data during task execution
    - Ensures proper resource management and cleanup
    """

    def __init__(
        self,
        task: Task,
        tool: AbstractTool,
        task_storage: Optional[TaskStorage] = None,
        error_handler: Optional[ErrorHandler] = None,
    ):
        """
        Initialize with a task and tool.

        Args:
            task: Task to execute, must have an App instance set before
                calling execute().
            tool: Tool implementation (e.g., MonkeyTool, DroidbotTool,
                RVAgentTool) to run against the APK.
            task_storage: Persistent storage for task state. When provided,
                task results survive process restarts.
            error_handler: Error handler for consistent error management.
                Defaults to the singleton ErrorHandler instance.

        State:
            components: Ordered list of registered execution components.
                Components execute in registration order during the
                coordinated execution phase.
            pre_execution_hooks: Callables invoked with the Task before
                component execution begins.
            post_execution_hooks: Callables invoked with (Task, success_bool)
                after execution completes or fails.
        """
        self.task = task
        self.tool = tool
        self.task_storage = task_storage
        self.error_handler = error_handler or ErrorHandler.get_instance()

        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_platform.execution.executor",
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: task.config.apk_name,
                CONTEXT_TOOL_NAME: tool.name,
                CONTEXT_COMPONENT: "TaskExecutor",
            },
        )

        # Component registry for coordinated task execution.
        # Registration order determines initialization order. During execution,
        # components are dispatched to phases by type (see _execute_coordinated_components),
        # not by registration order — but initialization still follows registration order.
        self.components: List[Any] = []

        # Execution hooks for extension points.
        # Pre-hooks run after task validation but before component initialization.
        # Post-hooks run after cleanup, receiving (task, success_bool) for both
        # success and failure paths. rv-experiment uses these for cross-task coordination.
        self.pre_execution_hooks: List[Callable[[Task], None]] = []
        self.post_execution_hooks: List[Callable[[Task, bool], None]] = []

    def get_task_context(self) -> Dict[str, Any]:
        """
        Build the standard context dictionary for this task execution.

        Returns:
            Dictionary with keys: task_id, apk_name, tool_name, repetition,
            timeout. Used by components and error handlers for contextual
            logging and error reporting.
        """
        return {
            "task_id": self.task.id,
            "apk_name": self.task.config.apk_name,
            "tool_name": self.task.config.tool_config.get_full_tool_name(),
            "repetition": self.task.config.repetition,
            "timeout": self.task.config.timeout,
        }

    def register_component(self, component: Any) -> None:
        """
        Register a component with the executor.

        Args:
            component: Component to register
        """
        self.components.append(component)
        self.logger.debug(
            f"Registered component: {getattr(component, 'name', type(component).__name__)}"
        )

    def get_components(self) -> List[Any]:
        """
        Get all registered components.

        Returns:
            List of registered components
        """
        return self.components

    def set_error_handler(self, handler: ErrorHandler) -> None:
        """
        Set the error handler for the executor.

        Args:
            handler: Error handler to use
        """
        self.error_handler = handler

    def add_pre_execution_hook(self, hook: Callable[[Task], None]) -> None:
        """
        Add a hook to be called before task execution.

        Args:
            hook: Function to call with the task
        """
        self.pre_execution_hooks.append(hook)
        self.logger.debug(f"Added pre-execution hook: {hook.__name__}")

    def add_post_execution_hook(self, hook: Callable[[Task, bool], None]) -> None:
        """
        Add a hook to be called after task execution.

        Args:
            hook: Function to call with the task and success flag
        """
        self.post_execution_hooks.append(hook)
        self.logger.debug(f"Added post-execution hook: {hook.__name__}")

    def execute(self) -> bool:
        """
        Execute the task through the full component lifecycle.

        Run pre-execution hooks, initialize all registered components,
        execute them in coordinated phases (static analysis -> coverage init
        -> emulator session with tool), clean up components, and run
        post-execution hooks. On failure, clean up resources and mark the
        task as ERROR.

        Returns:
            True if task execution completed successfully, False if the task
            had no App instance set or if any component raised an exception.

        Raises:
            No exceptions are raised; all errors are caught, logged via
            ErrorHandler, and reflected in the return value and task state.
        """
        self.logger.info(LOG_START.format(phase=f"execution of task {self.task}"))

        # Validate task has required app instance for execution
        # App instance contains APK path, package info, and static analysis data
        if not self.task.app:
            error_msg = "Task has no app instance set"
            self.task.update_state(TaskState.ERROR, error_msg)
            self.logger.error(
                LOG_ERROR.format(phase="task execution", error="app instance not set")
            )
            self._publish_task_failed_event(error_msg)
            return False

        try:
            # Step 1: Pre-execution hooks (e.g., rv-experiment cross-task coordination)
            for hook in self.pre_execution_hooks:
                hook(self.task)

            # Step 2: State transition — marks the task as actively running
            self.task.update_state(TaskState.RUNNING)
            self._publish_task_started_event()

            # Step 3: Initialize all components in registration order.
            # Each component gets the task context for configuration. Components
            # that need the Android device (emulator, logcat) defer their real work
            # to the execution phase — initialization only prepares internal state.
            context = self.get_task_context()
            self._initialize_components(context)

            # Step 4: Execute components in three coordinated phases.
            # Phase 1 (static analysis) and Phase 2 (coverage init) run OUTSIDE
            # the emulator — no device needed. Phase 3 runs INSIDE the emulator
            # context manager, which handles boot, app install, and teardown.
            # This separation avoids holding an emulator idle during analysis.
            self._execute_coordinated_components(context)

            # Step 5: Clean up all components (release file handles, stop threads)
            self._cleanup_components(context)

            # Step 6: Mark task as completed — persisted by Platform._execute_tasks()
            self.task.update_state(TaskState.COMPLETED)

            # Publish completed event
            self._publish_task_completed_event()
            self.logger.info(LOG_COMPLETE.format(phase=f"Task {self.task.id}"))

            # Run post-execution hooks
            for hook in self.post_execution_hooks:
                hook(self.task, True)

            return True

        except Exception as e:
            # Error path: mark task as failed, clean up resources, notify hooks.
            # Cleanup runs even on failure to release emulator/logcat resources;
            # _cleanup_resources() catches its own exceptions to avoid masking
            # the original error.
            self.error_handler.handle_error(e, self.get_task_context())

            error_message = str(e)
            self.task.update_state(TaskState.ERROR, error_message)

            self._publish_task_failed_event(error_message)

            self._cleanup_resources()

            # Post-execution hooks receive success=False so they can perform
            # failure-specific actions (e.g., notification, retry scheduling).
            for hook in self.post_execution_hooks:
                hook(self.task, False)

            return False

    def _initialize_components(self, context: Dict[str, Any]) -> None:
        """
        Initialize all registered components.

        Args:
            context: Task execution context
        """
        for component in self.components:
            if hasattr(component, "initialize"):
                self.logger.debug(
                    f"Initializing component: {getattr(component, 'name', type(component).__name__)}"
                )
                component.initialize(context)

    def _execute_coordinated_components(self, context: Dict[str, Any]) -> None:
        """
        Execute components in three coordinated phases.

        Phase 1: Static analysis data loading (outside emulator).
        Phase 2: Coverage tracker initialization (outside emulator).
        Phase 3: Emulator session with logcat capture, coverage tracking,
        and tool execution (inside emulator context manager).

        Args:
            context: Task execution context, enriched with 'android' and
                'device_id' keys during the emulator session phase.

        Raises:
            TaskExecutionError: If any component's execute() returns False.
        """
        # Classify components by type for phase-based execution.
        # Components are dispatched to three phases based on their resource needs:
        # - Phases 1-2 run WITHOUT an emulator (no Android device needed)
        # - Phase 3 runs INSIDE the emulator context manager (device is booted)
        # This separation avoids holding an emulator idle during static analysis
        # and coverage initialization, which can take significant time.
        static_component = None
        coverage_component = None
        emulator_component = None
        logcat_component = None
        tool_component = None

        for component in self.components:
            if isinstance(component, StaticAnalysisComponent):
                static_component = component
            elif isinstance(component, CoverageComponent):
                coverage_component = component
            elif isinstance(component, EmulatorComponent):
                emulator_component = component
            elif isinstance(component, LogcatComponent):
                logcat_component = component
            elif isinstance(component, ToolExecutionComponent):
                tool_component = component

        # Phase 1: Static analysis data loading (outside emulator).
        # Loads GATOR/GESDA/REACH data into the task's static_data field.
        # This data is needed by CoverageTracker to know which methods belong
        # to the app (vs library code) for accurate coverage calculation.
        if static_component:
            self.logger.info(f"Executing component: {static_component.name}")
            if not static_component.execute(context):
                raise TaskExecutionError(
                    f"Component {static_component.name} execution failed", self.task.id
                )

        # Phase 2: Coverage tracker initialization (outside emulator).
        # Creates the CoverageTracker with static_data and logcat_file path,
        # but does NOT start the monitoring thread yet. Tracking starts inside
        # the emulator session after the APK is installed and tool begins.
        if coverage_component:
            self.logger.info(f"Executing component: {coverage_component.name}")
            if not coverage_component.execute(context):
                raise TaskExecutionError(
                    f"Component {coverage_component.name} execution failed",
                    self.task.id,
                )

        # Phase 3: Emulator session (emulator boot -> app install -> tool run).
        # Everything inside this phase runs within the emulator context manager,
        # which handles startup, boot-wait, and teardown automatically.
        if emulator_component and tool_component:
            self._run_emulator_session(
                emulator_component,
                logcat_component,
                coverage_component,
                tool_component,
                context,
            )
        else:
            self.logger.warning(
                "Missing emulator or tool component - skipping emulator session"
            )

    def _run_emulator_session(
        self,
        emulator_component,
        logcat_component,
        coverage_component,
        tool_component,
        context: Dict[str, Any],
    ) -> None:
        """
        Run emulator session with proper lifecycle management.

        Args:
            emulator_component: Emulator component
            logcat_component: Logcat component
            coverage_component: Coverage component
            tool_component: Tool execution component
            context: Task execution context
        """
        # The context manager boots the emulator, waits for it to be ready,
        # and tears it down when the block exits (even on exception).
        # "RVSec" is the AVD name shared by all experiment containers.
        # The emulator gets a unique port via device_port in tool_config.parameters,
        # enabling parallel execution across Docker containers without port conflicts.
        with emulator_component.start_emulator("RVSec") as android:
            try:
                # Inject the Android interface into context so downstream components
                # (especially ToolExecutionComponent) can interact with the device.
                # Tools receive this via context["android"] in their execute() call.
                context["android"] = android
                context["device_id"] = self.task.config.device_id

                # Install app if needed. On failure the component holds the
                # reason ADB gave, which is what makes an INSTALL_FAILED_* code
                # reach the stored error_message instead of a bare "Failed to
                # install application" that names no cause (INV-CORE-51).
                if not self.task.config.skip_installation:
                    self.logger.info("Installing application")
                    if not emulator_component.install_app(android, self.task.app):
                        raise TaskExecutionError(
                            emulator_component.last_install_error
                            or "Failed to install application",
                            self.task.id,
                        )

                # Start logcat capture BEFORE the tool runs. Logcat captures all
                # Android system log output to a file, including RVSEC MOP violation
                # markers emitted by the instrumented APK. This file is persisted in
                # tasks.json and used for MOP violation reconstruction on resume.
                if logcat_component:
                    logcat_component.start_capture()

                # Record the precise tool execution start timestamp BEFORE starting
                # coverage tracking. CoverageTracker uses this timestamp to calculate
                # time-relative coverage metrics (e.g., "method first seen at T+30s").
                # The task start_time includes emulator boot time, which would skew
                # coverage timing if used instead.
                self.task.mark_tool_execution_start()
                self._publish_tool_execution_started_event()

                # Start real-time coverage tracking. The tracker reads the logcat
                # file in a background thread, parsing RVSEC log entries as they
                # appear. CoverageTracker uses static_data (loaded in Phase 1) to
                # distinguish app methods from library code for accurate coverage
                # calculation.
                if coverage_component:
                    coverage_component.start_tracking()

                # Execute the testing tool (Monkey, DroidBot, RVAgent, etc.).
                # The tool interacts with the emulator for the configured timeout
                # duration. RVToolTimeoutError is caught inside ToolExecutionComponent
                # and treated as successful completion (bounded-time experiments).
                self.logger.info(f"Executing component: {tool_component.name}")
                if not tool_component.execute(context):
                    raise TaskExecutionError(
                        f"Component {tool_component.name} execution failed",
                        self.task.id,
                    )

            finally:
                # The single point at which coverage and logcat are finalized.
                # It sits inside the `with`, so it runs while the device is
                # still alive on both the success and the failure path: a
                # COMPLETED task's .logcat is the reconstruction source for
                # resume, and finalizing after teardown would damage exactly
                # that artifact.
                #
                # Logcat first, then coverage. `adb logcat` is the producer
                # writing the file; CoverageTracker is the consumer reading the
                # same file through its own handle, obtained by path. Stopping
                # the producer first freezes the file, so the consumer's final
                # drain sees a complete input. Stopping the consumer first
                # would leave the producer appending lines that are present in
                # the file and absent from the in-memory repository, which is
                # what process_results() reads.
                #
                # These call the components' own cleanup(), which both catch
                # and log their own exceptions — required here, because an
                # exception escaping this `finally` would replace the exception
                # being propagated. _cleanup_components() still invokes both
                # afterwards; that second invocation is inert.
                if logcat_component:
                    logcat_component.cleanup(context)
                if coverage_component:
                    coverage_component.cleanup(context)

    def _cleanup_components(self, context: Dict[str, Any]) -> None:
        """
        Clean up all registered components.

        Args:
            context: Task execution context
        """
        for component in self.components:
            if hasattr(component, "cleanup"):
                try:
                    component_name = getattr(
                        component, "name", type(component).__name__
                    )
                    self.logger.debug(f"Cleaning up component: {component_name}")
                    component.cleanup(context)
                except Exception as e:
                    self.logger.warning(
                        f"Error cleaning up component {component_name}: {e}"
                    )

    def _cleanup_resources(self) -> None:
        """Clean up resources in case of error."""
        context = self.get_task_context()
        with self.logger.with_context(phase="resource_cleanup"):
            try:
                # Clean up all components
                self._cleanup_components(context)
            except Exception as e:
                # Create error context for cleanup failure
                cleanup_context = self.get_task_context()
                cleanup_context["phase"] = "component_cleanup"
                cleanup_context["component_count"] = len(self.components)

                # Use ErrorHandler for proper exception handling
                self.error_handler.handle_error(e, cleanup_context)

                # Log cleanup warning
                self.logger.warning(
                    LOG_ERROR.format(phase="cleaning up components", error=str(e))
                )

    # Task lifecycle logging methods

    def _publish_task_started_event(self) -> None:
        """Log task started."""
        self.logger.info(
            f"Task started: {self.task.id} tool={self.tool.name} apk={self.task.config.apk_name}"
        )

    def _publish_task_completed_event(self) -> None:
        """Log task completed."""
        self.logger.info(f"Task completed: {self.task.id}")

    def _publish_task_failed_event(self, error_message: str) -> None:
        """Log task failed."""
        self.logger.error(f"Task failed: {self.task.id} error={error_message}")

    def _publish_tool_execution_started_event(self) -> None:
        """Log tool execution started for timing coordination."""
        self.logger.info(
            f"Tool execution started: {self.tool.name} for task {self.task.id}"
        )
