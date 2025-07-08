# tests/execution/test_executor.py
from unittest.mock import MagicMock, patch

import pytest

from rv_android_core.domain.app import App
from rv_android_core.event import EventBus
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.domain.task import Task, TaskConfiguration, TaskState
from rv_platform.execution.executor import TaskExecutor


class TestTaskExecutor:
    """Tests for TaskExecutor class"""

    @pytest.fixture
    def basic_config(self):
        """Fixture providing a basic task configuration"""
        return TaskConfiguration(
            apk_name="test.apk",
            repetition=1,
            timeout=60,
            tool_name="monkey"
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
    def mock_event_bus(self):
        """Fixture providing a mock event bus"""
        return MagicMock(spec=EventBus)

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

    def test_executor_initialization(self, task_with_app, mock_tool, mock_event_bus, mock_error_handler):
        """Test that TaskExecutor initializes correctly"""
        # Updated signature: task, tool, event_bus, task_storage, error_handler
        executor = TaskExecutor(task_with_app, mock_tool, mock_event_bus, None, mock_error_handler)

        assert executor.task == task_with_app
        assert executor.tool == mock_tool
        assert executor.event_bus == mock_event_bus
        assert executor.error_handler == mock_error_handler
        assert isinstance(executor.components, list)
        assert len(executor.components) == 0

    def test_get_task_context(self, task_with_app, mock_tool):
        """Test getting task context"""
        executor = TaskExecutor(task_with_app, mock_tool)
        
        context = executor.get_task_context()
        
        assert context["task_id"] == task_with_app.id
        assert context["apk_name"] == "test.apk"
        assert context["tool_name"] == "monkey"
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

    @patch('rv_platform.execution.executor.PerformanceMonitor')
    def test_execute_success_simple(self, mock_perf_monitor, task_with_app, mock_tool):
        """Test successful execution with simple components"""
        # Mock performance monitor
        mock_perf_instance = MagicMock()
        mock_perf_monitor.get_instance.return_value = mock_perf_instance
        mock_perf_instance.measure_time.return_value.__enter__ = MagicMock()
        mock_perf_instance.measure_time.return_value.__exit__ = MagicMock()
        
        executor = TaskExecutor(task_with_app, mock_tool)
        
        # Add mock components that executor expects
        mock_emulator = MagicMock()
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
        
        mock_tool_execution = MagicMock()
        mock_tool_execution.name = "ToolExecutionComponent"  
        mock_tool_execution.execute.return_value = True
        executor.register_component(mock_tool_execution)
        
        # Debug: check registered components
        print(f"Registered components: {len(executor.components)}")
        for comp in executor.components:
            print(f"  - {comp.name}")
        
        result = executor.execute()
        
        print(f"Execution result: {result}")
        print(f"Task state: {task_with_app.result.state}")
        print(f"Emulator execute called: {mock_emulator.execute.call_count}")
        print(f"Tool execute called: {mock_tool_execution.execute.call_count}")
        
        assert result is True
        assert task_with_app.result.state == TaskState.COMPLETED
        
        # Verify components were called
        # Note: EmulatorComponent's execute method is not called in the current implementation
        # The emulator works through start_emulator and install_app methods
        mock_emulator.start_emulator.assert_called_once_with("RVSec")
        mock_emulator.install_app.assert_called_once_with(mock_android, task_with_app.app)
        mock_tool_execution.execute.assert_called_once()

    def test_execute_failure_component_error(self, task_with_app, mock_tool):
        """Test execution failure when component fails"""
        executor = TaskExecutor(task_with_app, mock_tool)
        
        # Add mock components with one that fails
        mock_emulator = MagicMock()
        mock_emulator.name = "EmulatorComponent"
        mock_emulator.execute.return_value = True
        executor.register_component(mock_emulator)
        
        mock_tool_execution = MagicMock()
        mock_tool_execution.name = "ToolExecutionComponent"
        mock_tool_execution.execute.return_value = False  # This one fails
        executor.register_component(mock_tool_execution)
        
        result = executor.execute()
        
        assert result is False
        assert task_with_app.result.state == TaskState.ERROR

    @patch('rv_platform.execution.executor.PerformanceMonitor')
    def test_execute_with_hooks(self, mock_perf_monitor, task_with_app, mock_tool):
        """Test execution with pre and post hooks"""
        # Mock performance monitor
        mock_perf_instance = MagicMock()
        mock_perf_monitor.get_instance.return_value = mock_perf_instance
        mock_perf_instance.measure_time.return_value.__enter__ = MagicMock()
        mock_perf_instance.measure_time.return_value.__exit__ = MagicMock()
        
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
        
        # Add mock components with one that raises an exception
        mock_emulator = MagicMock()
        mock_emulator.name = "EmulatorComponent"
        mock_emulator.execute.return_value = True
        executor.register_component(mock_emulator)
        
        mock_tool_execution = MagicMock()
        mock_tool_execution.name = "ToolExecutionComponent"
        mock_tool_execution.execute.side_effect = Exception("Test exception")  # This one fails
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