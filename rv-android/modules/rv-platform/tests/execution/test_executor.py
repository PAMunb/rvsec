# tests/execution/test_executor.py
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import rv_platform.execution.executor
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task, TaskConfiguration, TaskState
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import EmulatorError
from rv_platform.components.coverage import CoverageComponent
from rv_platform.components.emulator import EmulatorComponent
from rv_platform.components.logcat import LogcatComponent
from rv_platform.components.tool_execution import ToolExecutionComponent
from rv_platform.execution.executor import TaskExecutor


class TestTaskExecutor:
    """Tests for TaskExecutor class"""

    @pytest.fixture
    def basic_config(self):
        """Fixture providing a basic task configuration"""
        from rv_android_core.domain.task import ToolConfig

        tool_config = ToolConfig(name="monkey", variant="default", parameters={})

        return TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )

    @pytest.fixture
    def mock_app(self):
        """Fixture providing a mock App object"""
        app = MagicMock(spec=App)
        app.name = "test.apk"
        app.package_name = "com.test.app"
        return app

    @pytest.fixture
    def mock_tool(self):
        """Fixture providing a mock tool"""
        tool = MagicMock(spec=AbstractTool)
        tool.name = "monkey"
        tool.execute.return_value = True
        return tool

    @pytest.fixture
    def mock_error_handler(self):
        """Fixture providing a mock error handler"""
        return MagicMock(spec=ErrorHandler)

    @pytest.fixture
    def task_with_app(self, basic_config, mock_app):
        """Fixture providing a task with an app set"""
        task = Task(basic_config)
        task.set_app(mock_app)
        return task

    def test_executor_initialization(
        self, task_with_app, mock_tool, mock_error_handler
    ):
        """Test that TaskExecutor initializes correctly"""
        executor = TaskExecutor(task_with_app, mock_tool, None, mock_error_handler)

        assert executor.task == task_with_app
        assert executor.tool == mock_tool
        assert executor.error_handler == mock_error_handler
        assert isinstance(executor.components, list)
        assert len(executor.components) == 0

    def test_get_task_context(self, task_with_app, mock_tool):
        """Test getting task context"""
        executor = TaskExecutor(task_with_app, mock_tool)

        context = executor.get_task_context()

        assert context["task_id"] == task_with_app.id
        assert context["apk_name"] == "test.apk"
        assert (
            context["tool_name"] == "monkey"
        )  # This gets the full tool name from tool_config
        assert context["repetition"] == 1
        assert context["timeout"] == 60

    def test_register_component(self, task_with_app, mock_tool):
        """Test registering a component"""
        executor = TaskExecutor(task_with_app, mock_tool)
        mock_component = MagicMock()
        mock_component.name = "TestComponent"

        executor.register_component(mock_component)

        assert len(executor.components) == 1
        assert mock_component in executor.components

    def test_add_hooks(self, task_with_app, mock_tool):
        """Test adding pre and post execution hooks"""
        executor = TaskExecutor(task_with_app, mock_tool)

        def pre_hook(task):
            pass

        def post_hook(task, success):
            pass

        executor.add_pre_execution_hook(pre_hook)
        executor.add_post_execution_hook(post_hook)

        assert pre_hook in executor.pre_execution_hooks
        assert post_hook in executor.post_execution_hooks

    def test_execute_failure_no_app(self, basic_config, mock_tool):
        """Test execution failure when task has no app"""
        task = Task(basic_config)  # No app set
        executor = TaskExecutor(task, mock_tool)

        result = executor.execute()

        assert result is False
        assert task.result.state == TaskState.ERROR
        assert "no app instance" in task.result.error_message.lower()

    def test_execute_success_simple(self, task_with_app, mock_tool):
        """Test successful execution with simple components"""
        executor = TaskExecutor(task_with_app, mock_tool)

        # Add mock components with spec for isinstance() checks
        mock_emulator = MagicMock(spec=EmulatorComponent)
        mock_emulator.name = "EmulatorComponent"
        mock_emulator.execute.return_value = True

        # Mock the context manager for start_emulator
        mock_android = MagicMock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = MagicMock(return_value=mock_android)
        mock_context_manager.__exit__ = MagicMock(return_value=False)
        mock_emulator.start_emulator.return_value = mock_context_manager
        mock_emulator.install_app.return_value = True

        executor.register_component(mock_emulator)

        mock_tool_execution = MagicMock(spec=ToolExecutionComponent)
        mock_tool_execution.name = "ToolExecutionComponent"
        mock_tool_execution.execute.return_value = True
        executor.register_component(mock_tool_execution)

        result = executor.execute()

        assert result is True
        assert task_with_app.result.state == TaskState.COMPLETED

        # Verify emulator lifecycle methods were called
        mock_emulator.start_emulator.assert_called_once_with("RVSec")
        mock_emulator.install_app.assert_called_once_with(
            mock_android, task_with_app.app
        )
        mock_tool_execution.execute.assert_called_once()

    def test_execute_failure_component_error(self, task_with_app, mock_tool):
        """Test execution failure when component fails"""
        executor = TaskExecutor(task_with_app, mock_tool)

        # Add mock components with spec for isinstance() checks
        mock_emulator = MagicMock(spec=EmulatorComponent)
        mock_emulator.name = "EmulatorComponent"
        mock_emulator.execute.return_value = True

        # Mock the context manager for start_emulator
        mock_android = MagicMock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = MagicMock(return_value=mock_android)
        mock_context_manager.__exit__ = MagicMock(return_value=False)
        mock_emulator.start_emulator.return_value = mock_context_manager
        mock_emulator.install_app.return_value = True
        executor.register_component(mock_emulator)

        mock_tool_execution = MagicMock(spec=ToolExecutionComponent)
        mock_tool_execution.name = "ToolExecutionComponent"
        mock_tool_execution.execute.return_value = False  # This one fails
        executor.register_component(mock_tool_execution)

        result = executor.execute()

        assert result is False
        assert task_with_app.result.state == TaskState.ERROR

    def test_execute_with_hooks(self, task_with_app, mock_tool):
        """Test execution with pre and post hooks"""
        executor = TaskExecutor(task_with_app, mock_tool)

        pre_hook_called = []
        post_hook_called = []

        def pre_hook(task):
            pre_hook_called.append(task)

        def post_hook(task, success):
            post_hook_called.append((task, success))

        executor.add_pre_execution_hook(pre_hook)
        executor.add_post_execution_hook(post_hook)

        result = executor.execute()

        assert result is True

        # Verify hooks were called
        assert len(pre_hook_called) == 1
        assert pre_hook_called[0] == task_with_app
        assert len(post_hook_called) == 1
        assert post_hook_called[0] == (task_with_app, True)

    def test_execute_exception_handling(self, task_with_app, mock_tool):
        """Test exception handling during execution"""
        executor = TaskExecutor(task_with_app, mock_tool)

        # Add mock components with spec for isinstance() checks
        mock_emulator = MagicMock(spec=EmulatorComponent)
        mock_emulator.name = "EmulatorComponent"
        mock_emulator.execute.return_value = True

        # Mock the context manager for start_emulator
        mock_android = MagicMock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = MagicMock(return_value=mock_android)
        mock_context_manager.__exit__ = MagicMock(return_value=False)
        mock_emulator.start_emulator.return_value = mock_context_manager
        mock_emulator.install_app.return_value = True
        executor.register_component(mock_emulator)

        mock_tool_execution = MagicMock(spec=ToolExecutionComponent)
        mock_tool_execution.name = "ToolExecutionComponent"
        mock_tool_execution.execute.side_effect = Exception(
            "Test exception"
        )  # This one fails
        executor.register_component(mock_tool_execution)

        result = executor.execute()

        assert result is False
        assert task_with_app.result.state == TaskState.ERROR
        # The error message might contain the TaskExecutionError message
        assert task_with_app.result.error_message is not None

    def test_cleanup_components(self, task_with_app, mock_tool):
        """Test component cleanup"""
        executor = TaskExecutor(task_with_app, mock_tool)

        # Add mock components with cleanup methods
        mock_component1 = MagicMock()
        mock_component2 = MagicMock()

        executor.register_component(mock_component1)
        executor.register_component(mock_component2)

        context = executor.get_task_context()
        executor._cleanup_components(context)

        # Verify cleanup was called for both components
        mock_component1.cleanup.assert_called_once_with(context)
        mock_component2.cleanup.assert_called_once_with(context)

    def test_cleanup_components_with_error(self, task_with_app, mock_tool):
        """Test component cleanup when one component raises an error"""
        executor = TaskExecutor(task_with_app, mock_tool)

        # Add mock components - one that fails cleanup
        mock_component1 = MagicMock()
        mock_component1.cleanup.side_effect = Exception("Cleanup failed")
        mock_component2 = MagicMock()

        executor.register_component(mock_component1)
        executor.register_component(mock_component2)

        context = executor.get_task_context()

        # Should not raise exception, just log warning
        executor._cleanup_components(context)

        # Both should be called even if first fails
        mock_component1.cleanup.assert_called_once_with(context)
        mock_component2.cleanup.assert_called_once_with(context)

    def test_mark_tool_execution_start_called_before_coverage_start_tracking(
        self, task_with_app, mock_tool
    ):
        """
        Verify that mark_tool_execution_start() is called BEFORE coverage
        start_tracking() during emulator session execution.

        This ordering is critical: CoverageTracker needs the accurate
        tool_execution_start timestamp to calculate correct relative times
        in coverage.csv. If start_tracking() runs first, the tracker uses
        the task creation time as fallback, causing a ~60s offset in times.
        """
        executor = TaskExecutor(task_with_app, mock_tool)

        # Track call order
        call_order = []

        # Mock emulator component
        mock_emulator = MagicMock(spec=EmulatorComponent)
        mock_emulator.name = "EmulatorComponent"
        mock_android = MagicMock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = MagicMock(return_value=mock_android)
        mock_context_manager.__exit__ = MagicMock(return_value=False)
        mock_emulator.start_emulator.return_value = mock_context_manager
        mock_emulator.install_app.return_value = True
        executor.register_component(mock_emulator)

        # Mock coverage component that records call order
        mock_coverage = MagicMock(spec=CoverageComponent)
        mock_coverage.name = "CoverageComponent"
        mock_coverage.execute.return_value = True
        mock_coverage.start_tracking.side_effect = lambda: call_order.append(
            "start_tracking"
        )
        mock_coverage.stop_tracking.return_value = True
        mock_coverage.process_results.return_value = True
        executor.register_component(mock_coverage)

        # Mock tool component
        mock_tool_execution = MagicMock(spec=ToolExecutionComponent)
        mock_tool_execution.name = "ToolExecutionComponent"
        mock_tool_execution.execute.return_value = True
        executor.register_component(mock_tool_execution)

        # Patch mark_tool_execution_start to record call order
        original_mark = task_with_app.mark_tool_execution_start

        def tracked_mark():
            call_order.append("mark_tool_execution_start")
            original_mark()

        task_with_app.mark_tool_execution_start = tracked_mark

        executor.execute()

        # Verify both were called
        assert "mark_tool_execution_start" in call_order
        assert "start_tracking" in call_order

        # Verify ordering: mark_tool_execution_start BEFORE start_tracking
        mark_idx = call_order.index("mark_tool_execution_start")
        tracking_idx = call_order.index("start_tracking")
        assert mark_idx < tracking_idx, (
            f"mark_tool_execution_start (index {mark_idx}) must be called "
            f"before start_tracking (index {tracking_idx}). "
            f"Actual order: {call_order}"
        )


class TestFinalizationOwnership:
    """Coverage and logcat are finalized once, in order, with the device alive.

    The finalization used to exist twice: inline at the end of the emulator
    session, and again in the components' own `cleanup()` reached from the
    error path after teardown had already killed the device. There is now one
    firing point, in a `finally` covering the body of the `with`.
    """

    @pytest.fixture
    def basic_config(self):
        from rv_android_core.domain.task import ToolConfig

        tool_config = ToolConfig(name="monkey", variant="default", parameters={})
        return TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )

    @pytest.fixture
    def task_with_app(self, basic_config):
        app = MagicMock(spec=App)
        app.name = "test.apk"
        app.package_name = "com.test.app"
        task = Task(basic_config)
        task.set_app(app)
        return task

    @pytest.fixture
    def mock_tool(self):
        tool = MagicMock(spec=AbstractTool)
        tool.name = "monkey"
        tool.execute.return_value = True
        return tool

    def _wire(self, executor, call_order, install_ok=True, tool_ok=True):
        """Register the four components, recording the order of every call.

        The emulator context manager appends "emu_kill" on `__exit__`, which
        stands in for the teardown the real one performs — the assertions
        below are about what happens before the device dies.
        """
        mock_emulator = MagicMock(spec=EmulatorComponent)
        mock_emulator.name = "EmulatorComponent"
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__ = MagicMock(return_value=MagicMock())
        mock_context_manager.__exit__ = MagicMock(
            side_effect=lambda *args: call_order.append("emu_kill") or False
        )
        mock_emulator.start_emulator.return_value = mock_context_manager
        mock_emulator.install_app.return_value = install_ok
        mock_emulator.last_install_error = None
        executor.register_component(mock_emulator)

        mock_logcat = MagicMock(spec=LogcatComponent)
        mock_logcat.name = "LogcatComponent"
        mock_logcat.execute.return_value = True
        mock_logcat.cleanup.side_effect = lambda ctx: call_order.append(
            "logcat_cleanup"
        )
        executor.register_component(mock_logcat)

        mock_coverage = MagicMock(spec=CoverageComponent)
        mock_coverage.name = "CoverageComponent"
        mock_coverage.execute.return_value = True
        mock_coverage.cleanup.side_effect = lambda ctx: call_order.append(
            "coverage_cleanup"
        )
        executor.register_component(mock_coverage)

        mock_tool_execution = MagicMock(spec=ToolExecutionComponent)
        mock_tool_execution.name = "ToolExecutionComponent"
        mock_tool_execution.execute.return_value = tool_ok
        executor.register_component(mock_tool_execution)

        return mock_emulator, mock_logcat, mock_coverage

    def test_success_path_finalizes_in_order_before_teardown(
        self, task_with_app, mock_tool
    ):
        executor = TaskExecutor(task_with_app, mock_tool)
        call_order = []
        self._wire(executor, call_order)

        executor.execute()

        assert "logcat_cleanup" in call_order
        assert "coverage_cleanup" in call_order
        assert call_order.index("logcat_cleanup") < call_order.index(
            "coverage_cleanup"
        ), f"producer must stop before consumer, got {call_order}"
        assert call_order.index("coverage_cleanup") < call_order.index(
            "emu_kill"
        ), f"finalization must run with the device alive, got {call_order}"

    def test_failure_path_finalizes_in_order_before_teardown(
        self, task_with_app, mock_tool
    ):
        """A failing tool must not skip finalization, nor reorder it."""
        executor = TaskExecutor(task_with_app, mock_tool)
        call_order = []
        self._wire(executor, call_order, tool_ok=False)

        executor.execute()

        assert task_with_app.result.state == TaskState.ERROR
        assert call_order.index("logcat_cleanup") < call_order.index("coverage_cleanup")
        assert call_order.index("coverage_cleanup") < call_order.index("emu_kill")

    def test_a_failing_cleanup_primitive_does_not_mask_the_original_failure(
        self, task_with_app, mock_tool
    ):
        """The `finally` is safe because `cleanup()` swallows its own errors.

        This drives the real components rather than mocks: a mock whose
        `cleanup` raises would be violating the contract under test, not
        exercising it. `CoverageTracker.stop()` is made to fail, which is the
        realistic way an internal error arises during finalization.
        """
        coverage_component = CoverageComponent(task_with_app)
        coverage_component.coverage_tracker = MagicMock()
        coverage_component.coverage_tracker.stop.side_effect = RuntimeError(
            "tracker thread wedged"
        )

        # Must not raise: an exception escaping here would replace the
        # exception being propagated out of the emulator session.
        coverage_component.cleanup({})

        logcat_component = LogcatComponent(task_with_app)
        logcat_component.logcat_manager = MagicMock()
        logcat_component.logcat_manager.stop_capture.side_effect = RuntimeError(
            "adb gone"
        )

        logcat_component.cleanup({})

    def test_repeat_cleanup_leaves_coverage_metrics_unchanged(
        self, task_with_app, mock_tool
    ):
        """`_cleanup_components()` still invokes both components afterwards;
        that second invocation must be inert."""
        executor = TaskExecutor(task_with_app, mock_tool)
        call_order = []
        _, mock_logcat, mock_coverage = self._wire(executor, call_order)

        executor.execute()
        metrics_after_execute = dict(task_with_app.result.coverage_metrics or {})

        executor._cleanup_components(executor.get_task_context())

        assert task_with_app.result.coverage_metrics == (metrics_after_execute or {})
        assert mock_logcat.cleanup.call_count >= 2
        assert mock_coverage.cleanup.call_count >= 2

    def test_no_install_is_attempted_when_the_boot_wait_times_out(
        self, task_with_app, mock_tool
    ):
        """INV-PLT-27: a device that never booted must not receive an install,
        and the failure must not be reported as an installation failure."""
        executor = TaskExecutor(task_with_app, mock_tool)
        call_order = []
        mock_emulator, _, _ = self._wire(executor, call_order)

        boot_failure = EmulatorError(
            "Failed to start emulator RVSec",
            cause=TimeoutError("emulator-5554 sys.boot_completed not set within 300s"),
        )
        mock_emulator.start_emulator.side_effect = boot_failure

        executor.execute()

        mock_emulator.install_app.assert_not_called()
        assert task_with_app.result.state == TaskState.ERROR
        assert "Failed to install application" not in task_with_app.result.error_message

    def test_executor_never_calls_the_finalization_primitives_directly(self):
        """Only one implementation of finalization exists: the components'.

        Comment lines are stripped before the search, so prose describing the
        behavior does not satisfy or break the assertion.
        """
        source_path = Path(rv_platform.execution.executor.__file__).resolve()
        code_lines = [
            line.split("#", 1)[0]
            for line in source_path.read_text(encoding="utf-8").splitlines()
        ]
        code = "\n".join(code_lines)

        for primitive in ("stop_tracking(", "process_results(", "stop_capture("):
            assert primitive not in code, (
                f"{primitive} is called directly in executor.py; finalization "
                f"must go through the components' cleanup()"
            )
