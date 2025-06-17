"""
Unit tests for the AbstractTool base class.

This module contains comprehensive tests for the AbstractTool abstract base class
that defines the core contract for all testing tools in the RV-Android framework.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from abc import ABC

from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.app import App
from rv_android_core.commands.command import Command
from rv_android_core.commands.command_result import CommandResult


class ConcreteTestTool(AbstractTool):
    """Concrete implementation of AbstractTool for testing purposes."""

    def execute_tool_specific_logic(self, task, app):
        """Test implementation of abstract method."""
        self.test_execution_called = True
        self.test_task = task
        self.test_app = app


class TestAbstractToolInitialization:
    """Tests for AbstractTool initialization and setup."""

    def test_init_success(self):
        """Test successful initialization of AbstractTool."""
        # Arrange
        name = "test_tool"
        description = "Test tool description"
        process_pattern = "com.test.tool"

        # Act
        tool = ConcreteTestTool(name, description, process_pattern)

        # Assert
        assert tool.name == name
        assert tool.description == description
        assert tool.process_pattern == process_pattern
        # Logger and ErrorHandler are created by singletons, so we just check they exist
        assert tool.logger is not None
        assert tool.error_handler is not None

    def test_abstract_class_cannot_be_instantiated(self):
        """Test that AbstractTool cannot be instantiated directly."""
        # Act & Assert
        with pytest.raises(TypeError):
            AbstractTool("name", "description", "pattern")

    def test_concrete_class_requires_abstract_method_implementation(self):
        """Test that concrete classes must implement execute_tool_specific_logic."""

        class IncompleteTestTool(AbstractTool):
            pass  # Missing execute_tool_specific_logic implementation

        # Act & Assert
        with pytest.raises(TypeError):
            IncompleteTestTool("name", "description", "pattern")


class TestAbstractToolExecution:
    """Tests for AbstractTool execution workflow."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture providing mocked dependencies."""
        with patch('rv_android_core.util.logging.manager.LoggingManager') as mock_logging, \
                patch('rv_android_core.util.error.error_handler.ErrorHandler') as mock_error:
            mock_context_adapter = Mock()
            mock_logging_instance = Mock()
            mock_logging_instance.get_logger.return_value = mock_context_adapter
            mock_logging.get_instance.return_value = mock_logging_instance

            mock_error_instance = Mock()
            mock_error.get_instance.return_value = mock_error_instance

            yield {
                'logger': mock_context_adapter,
                'error_handler': mock_error_instance
            }

    @pytest.fixture
    def test_tool(self, mock_dependencies):
        """Fixture providing a concrete test tool instance."""
        return ConcreteTestTool("test_tool", "Test description", "com.test.tool")

    @pytest.fixture
    def mock_app(self):
        """Fixture providing a mock App instance."""
        app = Mock(spec=App)
        app.name = "test.apk"
        return app

    def test_execute_successful_workflow(self, test_tool, mock_app, mock_dependencies):
        """Test successful execution workflow."""
        # Arrange
        task = Mock()
        task.id = "123"  # Use object attribute instead of dict

        with patch.object(test_tool, 'kill_related_processes') as mock_kill, \
                patch.object(test_tool.logger, 'info') as mock_info, \
                patch.object(test_tool.logger, 'debug') as mock_debug:
            # Act
            test_tool.execute(task, mock_app)

            # Assert
            assert hasattr(test_tool, 'test_execution_called')
            assert test_tool.test_execution_called is True
            assert test_tool.test_task == task
            assert test_tool.test_app == mock_app

            # Verify process cleanup was called
            mock_kill.assert_called_once_with("com.test.tool")

            # Verify logging
            mock_info.assert_any_call("Executing monitored operations tool: test_tool")
            mock_debug.assert_any_call("Tool description: Test description")
            mock_info.assert_any_call("Tool test_tool execution completed successfully")

    def test_execute_handles_tool_specific_exception(self, test_tool, mock_app, mock_dependencies):
        """Test execution handles exceptions from tool-specific logic."""
        # Arrange
        task = Mock()
        task.id = "123"  # Use object attribute
        error = RuntimeError("Tool execution failed")

        # Override the tool-specific logic to raise an exception
        def failing_logic(task, app):
            raise error

        test_tool.execute_tool_specific_logic = failing_logic

        with patch.object(test_tool, 'kill_related_processes'), \
                patch.object(test_tool.logger, 'error') as mock_error_log, \
                patch.object(test_tool.error_handler, 'handle_error') as mock_handle_error:
            # Act & Assert
            with pytest.raises(RuntimeError):
                test_tool.execute(task, mock_app)

            # Verify error handling
            mock_handle_error.assert_called_once_with(
                error,
                context={
                    "tool_name": "test_tool",
                    "app_name": "test.apk",
                    "task_id": "123"
                }
            )

            # Verify error logging
            mock_error_log.assert_called_once()

    def test_execute_handles_missing_task_id(self, test_tool, mock_app, mock_dependencies):
        """Test execution handles task without ID gracefully."""
        # Arrange
        task = Mock(spec=[])  # Mock without 'id' attribute
        error = RuntimeError("Tool execution failed")

        def failing_logic(task, app):
            raise error

        test_tool.execute_tool_specific_logic = failing_logic

        with patch.object(test_tool, 'kill_related_processes'), \
                patch.object(test_tool.error_handler, 'handle_error') as mock_handle_error:
            # Act & Assert
            with pytest.raises(RuntimeError):
                test_tool.execute(task, mock_app)

            # Verify error context uses 'unknown' for missing task_id
            mock_handle_error.assert_called_once_with(
                error,
                context={
                    "tool_name": "test_tool",
                    "app_name": "test.apk",
                    "task_id": "unknown"
                }
            )


class TestAbstractToolProcessCleanup:
    """Tests for AbstractTool process cleanup functionality."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture providing mocked dependencies."""
        with patch('rv_android_core.util.logging.manager.LoggingManager') as mock_logging, \
                patch('rv_android_core.util.error.error_handler.ErrorHandler') as mock_error:
            mock_context_adapter = Mock()
            mock_logging_instance = Mock()
            mock_logging_instance.get_logger.return_value = mock_context_adapter
            mock_logging.get_instance.return_value = mock_logging_instance

            mock_error_instance = Mock()
            mock_error.get_instance.return_value = mock_error_instance

            yield {
                'logger': mock_context_adapter,
                'error_handler': mock_error_instance
            }

    @pytest.fixture
    def test_tool(self, mock_dependencies):
        """Fixture providing a concrete test tool instance."""
        return ConcreteTestTool("test_tool", "Test description", "com.test.tool")

    @patch('rv_android_core.tools.abstract_tool.Command')
    def test_kill_related_processes_success(self, mock_command_class, test_tool, mock_dependencies):
        """Test successful process cleanup."""
        # Arrange
        process_pattern = "com.test.tool"

        # Mock process listing
        mock_get_processes_cmd = Mock()
        mock_get_processes_result = Mock()
        mock_get_processes_result.stdout = b"user 1234 0 com.test.tool.process\nuser 5678 0 com.test.tool.service\n"
        mock_get_processes_cmd.invoke.return_value = mock_get_processes_result

        # Mock process killing
        mock_kill_cmd = Mock()
        mock_kill_result = Mock()
        mock_kill_cmd.invoke.return_value = mock_kill_result

        # Configure command creation
        def command_side_effect(*args, **kwargs):
            if 'ps' in args[1]:
                return mock_get_processes_cmd
            elif 'kill' in args[1]:
                return mock_kill_cmd
            return Mock()

        mock_command_class.side_effect = command_side_effect

        with patch.object(test_tool.logger, 'debug') as mock_debug, \
                patch.object(test_tool.logger, 'info') as mock_info:

            # Act
            test_tool.kill_related_processes(process_pattern)

            # Assert
            # Verify get processes command
            mock_command_class.assert_any_call('adb', [
                'shell', 'ps', '|', 'grep', process_pattern
            ])

            # Verify kill commands for both processes
            mock_command_class.assert_any_call('adb', ['shell', 'kill', '1234'])
            mock_command_class.assert_any_call('adb', ['shell', 'kill', '5678'])

            # Verify logging
            mock_debug.assert_any_call(f"Cleaning up processes matching pattern: {process_pattern}")
            mock_debug.assert_any_call("Killed process 1234")
            mock_debug.assert_any_call("Killed process 5678")
            mock_info.assert_any_call("Cleaned up 2 related processes")

    @patch('rv_android_core.tools.abstract_tool.Command')
    def test_kill_related_processes_no_processes_found(self, mock_command_class, test_tool, mock_dependencies):
        """Test process cleanup when no processes match pattern."""
        # Arrange
        process_pattern = "com.nonexistent.tool"

        mock_get_processes_cmd = Mock()
        mock_get_processes_result = Mock()
        mock_get_processes_result.stdout = b""  # No processes found
        mock_get_processes_cmd.invoke.return_value = mock_get_processes_result

        mock_command_class.return_value = mock_get_processes_cmd

        with patch.object(test_tool.logger, 'debug') as mock_debug:
            # Act
            test_tool.kill_related_processes(process_pattern)

            # Assert
            mock_debug.assert_any_call("No matching processes found for cleanup")

    @patch('rv_android_core.tools.abstract_tool.Command')
    def test_kill_related_processes_empty_pattern(self, mock_command_class, test_tool, mock_dependencies):
        """Test process cleanup with empty pattern."""

        with patch.object(test_tool.logger, 'debug') as mock_debug:
            # Act
            test_tool.kill_related_processes("")

            # Assert
            mock_command_class.assert_not_called()
            mock_debug.assert_called_with("No process pattern specified, skipping process cleanup")

    @patch('rv_android_core.tools.abstract_tool.Command')
    def test_kill_related_processes_none_pattern(self, mock_command_class, test_tool, mock_dependencies):
        """Test process cleanup with None pattern."""
        with patch.object(test_tool.logger, 'debug') as mock_debug:
            # Act
            test_tool.kill_related_processes(None)

            # Assert
            mock_command_class.assert_not_called()
            mock_debug.assert_called_with("No process pattern specified, skipping process cleanup")

    @patch('rv_android_core.tools.abstract_tool.Command')
    def test_kill_related_processes_command_exception(self, mock_command_class, test_tool, mock_dependencies):
        """Test process cleanup handles command exceptions gracefully."""
        # Arrange
        process_pattern = "com.test.tool"

        mock_get_processes_cmd = Mock()
        mock_get_processes_cmd.invoke.side_effect = OSError("ADB not found")
        mock_command_class.return_value = mock_get_processes_cmd

        with patch.object(test_tool.logger, 'warning') as mock_warning:
            # Act
            test_tool.kill_related_processes(process_pattern)

            # Assert - Should not raise exception
            mock_warning.assert_called_with("Error during process cleanup: ADB not found")

    @patch('rv_android_core.tools.abstract_tool.Command')
    def test_kill_related_processes_kill_command_fails(self, mock_command_class, test_tool, mock_dependencies):
        """Test process cleanup handles individual kill command failures."""
        # Arrange
        process_pattern = "com.test.tool"

        # Mock process listing
        mock_get_processes_cmd = Mock()
        mock_get_processes_result = Mock()
        mock_get_processes_result.stdout = b"user 1234 0 com.test.tool.process\n"
        mock_get_processes_cmd.invoke.return_value = mock_get_processes_result

        # Mock failing kill command
        mock_kill_cmd = Mock()
        mock_kill_cmd.invoke.side_effect = Exception("Process already dead")

        def command_side_effect(*args, **kwargs):
            if 'ps' in args[1]:
                return mock_get_processes_cmd
            elif 'kill' in args[1]:
                return mock_kill_cmd
            return Mock()

        mock_command_class.side_effect = command_side_effect

        with patch.object(test_tool.logger, 'warning') as mock_warning:
            # Act
            test_tool.kill_related_processes(process_pattern)

            # Assert
            mock_warning.assert_called_with("Failed to kill process 1234: Process already dead")


class TestAbstractToolUtilityMethods:
    """Tests for AbstractTool utility methods."""

    @pytest.fixture
    def mock_dependencies(self):
        """Fixture providing mocked dependencies."""
        with patch('rv_android_core.util.logging.manager.LoggingManager') as mock_logging, \
                patch('rv_android_core.util.error.error_handler.ErrorHandler') as mock_error:
            mock_context_adapter = Mock()
            mock_logging_instance = Mock()
            mock_logging_instance.get_logger.return_value = mock_context_adapter
            mock_logging.get_instance.return_value = mock_logging_instance

            mock_error_instance = Mock()
            mock_error.get_instance.return_value = mock_error_instance

            yield {
                'logger': mock_context_adapter,
                'error_handler': mock_error_instance
            }

    @pytest.fixture
    def test_tool(self, mock_dependencies):
        """Fixture providing a concrete test tool instance."""
        return ConcreteTestTool("test_tool", "Test description", "com.test.tool")

    def test_get_tool_info(self, test_tool):
        """Test get_tool_info returns correct metadata."""
        # Act
        info = test_tool.get_tool_info()

        # Assert
        assert info == {
            "name": "test_tool",
            "description": "Test description",
            "process_pattern": "com.test.tool"
        }

    def test_str_representation(self, test_tool):
        """Test string representation of tool."""
        # Act
        str_repr = str(test_tool)

        # Assert
        assert str_repr == "ConcreteTestTool(name='test_tool', description='Test description')"

    def test_repr_representation(self, test_tool):
        """Test detailed string representation of tool."""
        # Act
        repr_str = repr(test_tool)

        # Assert
        expected = ("ConcreteTestTool(name='test_tool', "
                    "description='Test description', process_pattern='com.test.tool')")
        assert repr_str == expected
