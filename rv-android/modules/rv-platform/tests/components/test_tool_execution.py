# tests/components/test_tool_execution.py
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task, TaskConfiguration
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_platform.components.tool_execution import ToolExecutionComponent


class TestToolExecutionComponent:
    """Tests for ToolExecutionComponent class"""

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
    def task_with_app(self, basic_config, mock_app):
        """Fixture providing a task with an app set"""
        task = Task(basic_config)
        task.set_app(mock_app)
        return task

    def test_component_initialization(self, task_with_app, mock_tool):
        """Test that ToolExecutionComponent initializes correctly"""
        component = ToolExecutionComponent(task_with_app, mock_tool)

        assert component.name == "ToolExecutionComponent"
        assert component.task == task_with_app
        assert component.tool == mock_tool

    def test_initialize(self, task_with_app, mock_tool):
        """Test component initialization"""
        component = ToolExecutionComponent(task_with_app, mock_tool)
        context = {"test": "context"}

        result = component.initialize(context)

        assert result is True

    def test_execute_calls_run_tool(self, task_with_app, mock_tool):
        """Test that execute method calls run_tool"""
        component = ToolExecutionComponent(task_with_app, mock_tool)
        context = {"test": "context"}

        with patch.object(component, "run_tool", return_value=True) as mock_run_tool:
            result = component.execute(context)

            assert result is True
            mock_run_tool.assert_called_once()

    def test_successful_tool_execution(self, task_with_app, mock_tool):
        """Test successful tool execution"""
        component = ToolExecutionComponent(task_with_app, mock_tool)

        result = component.run_tool()

        assert result is True

        # Verify tool was executed
        mock_tool.execute.assert_called_once_with(task_with_app, task_with_app.app)

    def test_tool_execution_failure(self, task_with_app, mock_tool):
        """Test tool execution failure handling"""
        # Make tool execution fail
        mock_tool.execute.side_effect = Exception("Tool execution failed")

        component = ToolExecutionComponent(task_with_app, mock_tool)

        result = component.run_tool()

        assert result is False

        # Verify tool was attempted
        mock_tool.execute.assert_called_once_with(task_with_app, task_with_app.app)

    def test_cleanup_calls_cleanup_processes(self, task_with_app, mock_tool):
        """Test that cleanup method calls cleanup_processes"""
        component = ToolExecutionComponent(task_with_app, mock_tool)
        context = {"test": "context"}

        with patch.object(component, "cleanup_processes") as mock_cleanup:
            component.cleanup(context)

            mock_cleanup.assert_called_once()

    def test_cleanup_processes_success(self, task_with_app, mock_tool):
        """Test successful process cleanup"""
        mock_tool.process_pattern = "test_pattern"
        mock_tool.kill_related_processes = MagicMock()

        component = ToolExecutionComponent(task_with_app, mock_tool)

        component.cleanup_processes()

        mock_tool.kill_related_processes.assert_called_once_with("test_pattern")

    def test_cleanup_processes_no_pattern(self, task_with_app, mock_tool):
        """Test cleanup when tool has no process pattern"""
        # Tool without process_pattern attribute
        del mock_tool.process_pattern

        component = ToolExecutionComponent(task_with_app, mock_tool)

        # Should not raise an exception
        component.cleanup_processes()

    def test_cleanup_processes_failure(self, task_with_app, mock_tool):
        """Test cleanup process failure handling"""
        mock_tool.process_pattern = "test_pattern"
        mock_tool.kill_related_processes = MagicMock()
        mock_tool.kill_related_processes.side_effect = Exception("Cleanup failed")

        component = ToolExecutionComponent(task_with_app, mock_tool)

        # Should not raise an exception, just log warning
        component.cleanup_processes()

        mock_tool.kill_related_processes.assert_called_once_with("test_pattern")

    def test_error_handler_integration(self, task_with_app, mock_tool):
        """Test integration with error handler"""
        # Make tool execution fail
        mock_tool.execute.side_effect = Exception("Tool failed")

        component = ToolExecutionComponent(task_with_app, mock_tool)

        result = component.run_tool()

        assert result is False

        # Verify error handler exists (it's initialized in __init__)
        assert component.error_handler is not None
