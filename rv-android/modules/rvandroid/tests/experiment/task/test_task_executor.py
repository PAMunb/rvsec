# tests/experiment/task/test_task_executor.py
"""
Test suite for TaskExecutor class.
Tests the component-based task execution system.
"""
import pytest
from unittest.mock import MagicMock, patch

from rvandroid.app import App
from rvandroid.domain.coverage import LogcatRepository
from rvandroid.experiment.event.bus import EventBus
from rvandroid.experiment.task.executor import TaskExecutor
from rvandroid.experiment.task.task_model import Task, TaskConfiguration
from rvandroid.experiment.task.interfaces import ITaskComponent, TaskState
from rvandroid.tools.tool_spec import AbstractTool

# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def mock_task():
    """Create a mock task for testing."""
    mock_task = MagicMock(spec=Task)
    mock_task.id = "test-task-123"
    mock_task.config = MagicMock(spec=TaskConfiguration)
    mock_task.config.apk_name = "test.apk"
    mock_task.config.tool_name = "test_tool"
    mock_task.config.repetition = 1
    mock_task.config.timeout = 60
    mock_task.app = MagicMock(spec=App)
    mock_task.app.name = "test.apk"
    mock_task.result = MagicMock()
    mock_task.result.state = TaskState.READY
    mock_task.result.execution_time_seconds = 10.5
    mock_task.update_state = MagicMock()
    return mock_task


@pytest.fixture
def mock_tool():
    """Create a mock tool for testing."""
    mock_tool = MagicMock(spec=AbstractTool)
    mock_tool.name = "test_tool"
    return mock_tool


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    return MagicMock(spec=EventBus)


@pytest.fixture
def mock_component():
    """Create a mock task component for testing."""
    component = MagicMock(spec=ITaskComponent)
    component.name = "TestComponent"
    component.initialize.return_value = True
    component.execute.return_value = True
    component.cleanup.return_value = True
    return component


class TestTaskExecutor:
    """Test cases for the TaskExecutor class."""

    def test_task_executor_initialization(self, mock_task, mock_tool, mock_event_bus):
        """Test that TaskExecutor initializes correctly."""
        executor = TaskExecutor(mock_task, mock_tool, mock_event_bus)
        
        assert executor.task == mock_task
        assert executor.tool == mock_tool
        assert executor.event_bus == mock_event_bus
        assert len(executor.get_components()) == 0

    def test_register_component(self, mock_task, mock_tool, mock_component):
        """Test component registration."""
        executor = TaskExecutor(mock_task, mock_tool)
        
        executor.register_component(mock_component)
        
        components = executor.get_components()
        assert len(components) == 1
        assert mock_component in components

    def test_get_task_context(self, mock_task, mock_tool):
        """Test task context generation."""
        executor = TaskExecutor(mock_task, mock_tool)
        
        context = executor.get_task_context()
        
        assert context["task_id"] == "test-task-123"
        assert context["apk_name"] == "test.apk"
        assert context["tool_name"] == "test_tool"
        assert context["repetition"] == 1
        assert context["timeout"] == 60

    def test_execute_no_app(self, mock_tool):
        """Test execution with no app set."""
        mock_task = MagicMock(spec=Task)
        mock_task.id = "test-task"
        mock_task.app = None
        mock_task.config = MagicMock(spec=TaskConfiguration)
        mock_task.config.apk_name = "test.apk"
        mock_task.config.tool_name = "test_tool"
        mock_task.config.repetition = 1
        mock_task.config.timeout = 60
        mock_task.update_state = MagicMock()
        
        executor = TaskExecutor(mock_task, mock_tool)
        
        result = executor.execute()
        
        assert result is False
        mock_task.update_state.assert_called_with(TaskState.ERROR, "Task has no app instance set")

    def test_execute_success(self, mock_task, mock_tool, mock_component):
        """Test successful task execution."""
        executor = TaskExecutor(mock_task, mock_tool)
        executor.register_component(mock_component)
        
        with patch.object(executor, '_publish_task_started_event') as mock_start_event, \
             patch.object(executor, '_publish_task_completed_event') as mock_complete_event, \
             patch.object(executor.performance_monitor, 'measure_time') as mock_measure, \
             patch.object(executor.performance_monitor, 'record_metric') as mock_record, \
             patch.object(executor, '_execute_coordinated_components') as mock_coordinated:
            
            # Mock the context manager
            mock_measure.return_value.__enter__ = MagicMock()
            mock_measure.return_value.__exit__ = MagicMock()
            
            result = executor.execute()
            
            assert result is True
            mock_task.update_state.assert_called_with(TaskState.COMPLETED)
            mock_start_event.assert_called_once()
            mock_complete_event.assert_called_once()
            mock_coordinated.assert_called_once()

    def test_execute_component_failure(self, mock_task, mock_tool, mock_component):
        """Test execution when component fails."""
        executor = TaskExecutor(mock_task, mock_tool)
        executor.register_component(mock_component)
        
        with patch.object(executor, '_publish_task_started_event') as mock_start_event, \
             patch.object(executor, '_publish_task_failed_event') as mock_failed_event, \
             patch.object(executor, '_cleanup_resources') as mock_cleanup, \
             patch.object(executor.performance_monitor, 'measure_time') as mock_measure, \
             patch.object(executor.performance_monitor, 'record_metric') as mock_record, \
             patch.object(executor.error_handler, 'handle_error') as mock_error_handler, \
             patch.object(executor, '_execute_coordinated_components') as mock_coordinated:
            
            # Mock coordinated components to raise an exception
            mock_coordinated.side_effect = Exception("Component execution failed")
            
            # Mock the context manager properly to not suppress exceptions
            class MockContextManager:
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc_val, exc_tb):
                    return False  # Don't suppress exceptions
            
            mock_measure.return_value = MockContextManager()
            
            result = executor.execute()
            
            assert result is False
            # Verify that update_state was called with ERROR
            mock_task.update_state.assert_called()
            call_args = mock_task.update_state.call_args[0]
            assert call_args[0] == TaskState.ERROR
            assert "Component execution failed" in call_args[1]
            mock_failed_event.assert_called_once()

    def test_hooks_execution(self, mock_task, mock_tool):
        """Test pre and post execution hooks."""
        pre_hook = MagicMock()
        pre_hook.__name__ = "pre_hook"  # Fix AttributeError: __name__
        post_hook = MagicMock()
        post_hook.__name__ = "post_hook"
        
        executor = TaskExecutor(mock_task, mock_tool)
        executor.add_pre_execution_hook(pre_hook)
        executor.add_post_execution_hook(post_hook)
        
        with patch.object(executor, '_publish_task_started_event'), \
             patch.object(executor, '_publish_task_completed_event'), \
             patch.object(executor.performance_monitor, 'measure_time') as mock_measure:
            
            # Mock the context manager
            mock_measure.return_value.__enter__ = MagicMock()
            mock_measure.return_value.__exit__ = MagicMock()
            
            result = executor.execute()
            
            assert result is True
            pre_hook.assert_called_once_with(mock_task)
            post_hook.assert_called_once_with(mock_task, True)

    def test_cleanup_on_error(self, mock_task, mock_tool, mock_component):
        """Test cleanup when error occurs during execution."""
        executor = TaskExecutor(mock_task, mock_tool)
        executor.register_component(mock_component)
        
        with patch.object(executor, '_cleanup_resources') as mock_cleanup, \
             patch.object(executor, '_publish_task_started_event') as mock_start_event, \
             patch.object(executor, '_publish_task_failed_event') as mock_failed_event, \
             patch.object(executor.performance_monitor, 'measure_time') as mock_measure, \
             patch.object(executor.performance_monitor, 'record_metric') as mock_record, \
             patch.object(executor.error_handler, 'handle_error') as mock_error_handler, \
             patch.object(executor, '_execute_coordinated_components') as mock_coordinated:
            
            # Mock coordinated components to raise an exception
            mock_coordinated.side_effect = Exception("Component error")
            
            # Mock the context manager properly to not suppress exceptions
            class MockContextManager:
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc_val, exc_tb):
                    return False  # Don't suppress exceptions
            
            mock_measure.return_value = MockContextManager()
            
            result = executor.execute()
            
            assert result is False
            mock_cleanup.assert_called_once()

    def test_set_error_handler(self, mock_task, mock_tool):
        """Test setting custom error handler."""
        from rvandroid.util.error.error_handler import ErrorHandler
        custom_handler = MagicMock(spec=ErrorHandler)
        
        executor = TaskExecutor(mock_task, mock_tool)
        executor.set_error_handler(custom_handler)
        
        assert executor.error_handler == custom_handler