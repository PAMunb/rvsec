# tests/tools/test_abstract_tool.py
import tempfile
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st
from rv_android_core.commands.command import Command
from rv_android_core.commands.command_result import CommandResult
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task, TaskConfiguration, ToolConfig
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.exceptions import (
    RVCommandTimeoutError,
    RVToolExecutionError,
    RVToolTimeoutError,
)


class ConcreteTestTool(AbstractTool):
    """Concrete implementation of AbstractTool for testing"""

    def __init__(self):
        super().__init__(
            name="testtool",
            description="Test tool for unit testing",
            process_pattern="testtool",
        )
        self._configured = False
        self._config = {}
        self.test_execution_called = False
        self.test_task = None
        self.test_app = None

    @classmethod
    def get_tool_spec(cls):
        return ToolSpec(
            name="testtool",
            description="Test tool for unit testing",
            url="https://example.com/testtool",
            version="1.0.0",
            process_pattern="testtool",
        )

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "default": {"mode": "normal", "timeout": 60},
            "fast": {"mode": "fast", "timeout": 30},
            "slow": {"mode": "slow", "timeout": 120},
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the test tool"""
        if config is None:
            raise ValueError("Configuration cannot be None")
        self._config = config
        self._configured = True

    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        """Execute test-specific logic"""
        if not self._configured:
            raise RVToolExecutionError("Tool not configured", tool_name=self.name)

        self.test_execution_called = True
        self.test_task = task
        self.test_app = app

        # Simulate some work
        self.logger.info(f"Executing {self.name} with config: {self._config}")


class TestAbstractToolInitialization:
    """Tests for AbstractTool initialization"""

    def test_init_success(self):
        """Test successful tool initialization"""
        tool = ConcreteTestTool()

        assert tool.name == "testtool"
        assert tool.description == "Test tool for unit testing"
        assert tool.process_pattern == "testtool"
        assert tool.logger is not None
        assert tool.error_handler is not None
        assert not tool._configured

    def test_get_variants(self):
        """Test getting tool variants"""
        variants = ConcreteTestTool.get_variants()

        assert "default" in variants
        assert "fast" in variants
        assert "slow" in variants

        assert variants["default"]["mode"] == "normal"
        assert variants["fast"]["timeout"] == 30
        assert variants["slow"]["timeout"] == 120

    def test_get_tool_spec(self):
        """Test getting tool specification"""
        spec = ConcreteTestTool.get_tool_spec()

        assert spec.name == "testtool"
        assert spec.description == "Test tool for unit testing"
        assert spec.version == "1.0.0"
        assert spec.process_pattern == "testtool"

    def test_configure_tool(self):
        """Test tool configuration"""
        tool = ConcreteTestTool()
        config = {"mode": "test", "debug": True}

        tool.configure(config)

        assert tool._configured
        assert tool._config == config


class TestAbstractToolExecution:
    """Tests for AbstractTool execution workflow"""

    def test_execute_successful_workflow(self):
        """Test successful execution workflow"""
        tool = ConcreteTestTool()
        tool.configure({"mode": "test"})

        # Create test task and app
        tool_config = ToolConfig(name="testtool")
        task_config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=task_config)

        app = MagicMock(spec=App)
        app.package_name = "com.example.test"

        # Execute the tool
        tool.execute(task, app)

        # Verify execution was called
        assert tool.test_execution_called
        assert tool.test_task == task
        assert tool.test_app == app

    def test_execute_handles_tool_specific_exception(self):
        """Test handling of tool-specific exceptions"""
        tool = ConcreteTestTool()
        tool.configure({"mode": "test"})

        tool_config = ToolConfig(name="testtool")
        task_config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=task_config)

        app = MagicMock(spec=App)

        # Override execute_tool_specific_logic to raise exception
        tool.execute_tool_specific_logic

        def failing_execute(task, app):
            raise RVToolExecutionError("Tool failed", tool_name="testtool")

        tool.execute_tool_specific_logic = failing_execute

        with pytest.raises(RVToolExecutionError):
            tool.execute(task, app)

    def test_execute_handles_missing_task_id(self):
        """Test handling of task without ID"""
        tool = ConcreteTestTool()
        tool.configure({"mode": "test"})

        # Create task without proper initialization
        tool_config = ToolConfig(name="testtool")
        task_config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=task_config)
        task.id = None  # Simulate missing ID

        app = MagicMock(spec=App)

        # Should handle gracefully since execute doesn't directly depend on task.id
        tool.execute(task, app)
        assert tool.test_execution_called


class TestAbstractToolProcessCleanup:
    """Tests for AbstractTool process cleanup functionality"""

    def test_kill_related_processes_success(self):
        """Test successful process cleanup"""
        tool = ConcreteTestTool()

        # Mock Command constructor and invoke methods
        with patch("rv_android_core.tools.abstract_tool.Command") as mock_command_class:
            mock_command = MagicMock()
            mock_result = MagicMock()
            mock_result.is_success.return_value = True
            mock_result.stdout = "1234\n5678\n"
            mock_command.invoke.return_value = mock_result
            mock_command_class.return_value = mock_command

            tool.kill_related_processes("testtool")

            # Verify commands were created and executed
            assert mock_command_class.call_count >= 1
            assert mock_command.invoke.call_count >= 1

    def test_kill_related_processes_no_processes_found(self):
        """Test process cleanup when no processes found"""
        tool = ConcreteTestTool()

        with patch("rv_android_core.commands.command.Command") as mock_command_class:
            mock_command = MagicMock()
            mock_result = MagicMock()
            mock_result.is_success.return_value = True
            mock_result.stdout = ""  # No processes found
            mock_command.invoke.return_value = mock_result
            mock_command_class.return_value = mock_command

            # Should not raise exception
            tool.kill_related_processes("testtool")

    def test_kill_related_processes_empty_pattern(self):
        """Test process cleanup with empty pattern"""
        tool = ConcreteTestTool()
        tool.process_pattern = ""

        # Should handle empty pattern gracefully
        tool.kill_related_processes("")

    def test_kill_related_processes_none_pattern(self):
        """Test process cleanup with None pattern"""
        tool = ConcreteTestTool()
        tool.process_pattern = None

        # Should handle None pattern gracefully
        tool.kill_related_processes(None)

    def test_kill_related_processes_command_exception(self):
        """Test process cleanup when command raises exception"""
        tool = ConcreteTestTool()

        with patch("rv_android_core.commands.command.Command") as mock_command_class:
            mock_command = MagicMock()
            mock_command.invoke.side_effect = Exception("Command failed")
            mock_command_class.return_value = mock_command

            # Should handle exception gracefully
            tool.kill_related_processes("testtool")

    def test_kill_related_processes_kill_command_fails(self):
        """Test process cleanup when kill command fails"""
        tool = ConcreteTestTool()

        with patch("rv_android_core.commands.command.Command") as mock_command_class:
            # First call (pgrep) succeeds
            mock_pgrep = MagicMock()
            mock_pgrep_result = MagicMock()
            mock_pgrep_result.is_success.return_value = True
            mock_pgrep_result.stdout = "1234\n5678\n"
            mock_pgrep.invoke.return_value = mock_pgrep_result

            # Second call (kill) fails
            mock_kill = MagicMock()
            mock_kill_result = MagicMock()
            mock_kill_result.is_success.return_value = False
            mock_kill.invoke.return_value = mock_kill_result

            # Return different mocks for different calls
            mock_command_class.side_effect = [mock_pgrep, mock_kill]

            # Should handle kill failure gracefully
            tool.kill_related_processes("testtool")


class TestAbstractToolUtilityMethods:
    """Tests for AbstractTool utility methods"""

    def test_get_tool_info(self):
        """Test getting tool information"""
        tool = ConcreteTestTool()

        info = tool.get_tool_info()

        assert info["name"] == "testtool"
        assert info["description"] == "Test tool for unit testing"
        assert info["process_pattern"] == "testtool"
        # AbstractTool base class doesn't include variants in tool info

    def test_str_representation(self):
        """Test string representation"""
        tool = ConcreteTestTool()

        result = str(tool)

        assert "testtool" in result.lower()

    def test_repr_representation(self):
        """Test repr representation"""
        tool = ConcreteTestTool()

        result = repr(tool)

        assert "Tool" in result


class TestAbstractToolCommandExecution:
    """Tests for AbstractTool command execution methods"""

    def test_execute_and_check_command_success(self):
        """Test successful command execution"""
        tool = ConcreteTestTool()

        mock_command = MagicMock(spec=Command)
        mock_result = MagicMock(spec=CommandResult)
        mock_result.is_success.return_value = True
        mock_result.is_failure.return_value = False
        mock_result.code = 0
        mock_command.invoke.return_value = mock_result

        result = tool._execute_and_check_command(mock_command)

        assert result == mock_result
        mock_command.invoke.assert_called_once_with(
            stdout=None, stderr=None, stdin=None
        )

    def test_execute_and_check_command_failure(self):
        """Test command execution failure"""
        tool = ConcreteTestTool()

        mock_command = MagicMock(spec=Command)
        mock_result = MagicMock(spec=CommandResult)
        mock_result.is_success.return_value = False
        mock_result.is_failure.return_value = True
        mock_result.code = 1
        mock_result.has_error_output.return_value = True
        mock_result.get_stderr_text.return_value = "Command failed"
        mock_command.command = "test_command"
        mock_command.args = ["arg1", "arg2"]
        mock_command.invoke.return_value = mock_result

        with pytest.raises(RVToolExecutionError) as exc_info:
            tool._execute_and_check_command(mock_command)

        assert "testtool" in str(exc_info.value)

    def test_execute_and_check_command_timeout(self):
        """Test command execution timeout"""
        tool = ConcreteTestTool()

        mock_command = MagicMock(spec=Command)
        mock_command.invoke.side_effect = RVCommandTimeoutError(
            "Command timed out", timeout_seconds=30
        )

        with pytest.raises(RVToolTimeoutError):
            tool._execute_and_check_command(mock_command)

    def test_execute_and_check_command_with_stdout_redirect(self):
        """Test command execution with stdout redirection"""
        tool = ConcreteTestTool()

        mock_command = MagicMock(spec=Command)
        mock_result = MagicMock(spec=CommandResult)
        mock_result.is_success.return_value = True
        mock_result.is_failure.return_value = False
        mock_command.invoke.return_value = mock_result

        with tempfile.NamedTemporaryFile() as temp_file:
            result = tool._execute_and_check_command(mock_command, stdout=temp_file)

            assert result == mock_result
            mock_command.invoke.assert_called_once_with(
                stdout=temp_file, stderr=None, stdin=None
            )

    def test_execute_and_check_command_failure_without_error_output(self):
        """Test command execution failure without stderr output"""
        tool = ConcreteTestTool()

        mock_command = MagicMock(spec=Command)
        mock_result = MagicMock(spec=CommandResult)
        mock_result.is_success.return_value = False
        mock_result.is_failure.return_value = True
        mock_result.code = 1
        mock_result.has_error_output.return_value = False
        mock_command.command = "test_command"
        mock_command.args = []
        mock_command.invoke.return_value = mock_result

        with pytest.raises(RVToolExecutionError) as exc_info:
            tool._execute_and_check_command(mock_command)

        assert "exit code 1" in str(exc_info.value)


class TestAbstractToolEdgeCases:
    """Tests for edge cases and error conditions"""

    def test_tool_with_invalid_configuration(self):
        """Test tool behavior with invalid configuration"""
        tool = ConcreteTestTool()

        # Test with None configuration
        with pytest.raises(ValueError):
            tool.configure(None)

    def test_tool_execution_without_configuration(self):
        """Test tool execution without prior configuration"""
        tool = ConcreteTestTool()

        tool_config = ToolConfig(name="testtool")
        task_config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=task_config)
        app = MagicMock(spec=App)

        with pytest.raises(RVToolExecutionError) as exc_info:
            tool.execute(task, app)

        assert "not configured" in str(exc_info.value)

    def test_empty_process_pattern_handling(self):
        """Test handling of empty process pattern"""
        tool = ConcreteTestTool()
        tool.process_pattern = ""

        # Should not raise exception
        tool.kill_related_processes("")

    @given(
        name=st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
        ),
        description=st.text(min_size=1, max_size=100),
        pattern=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd", "Pc")),
        ),
    )
    def test_abstract_tool_property_based(self, name, description, pattern):
        """Property-based test for AbstractTool initialization"""

        # Create a concrete tool with generated properties
        class PropertyBasedTool(AbstractTool):
            @classmethod
            def get_tool_spec(cls):
                return ToolSpec(
                    name=name,
                    description=description,
                    url="",
                    version="1.0.0",
                    process_pattern=pattern,
                )

            @classmethod
            def get_variants(cls):
                return {"default": {}}

            def configure(self, config):
                pass

            def execute_tool_specific_logic(self, task, app):
                pass

        # Use proper initialization
        tool = PropertyBasedTool(name, description, pattern)

        assert tool.name == name
        assert tool.description == description
        assert tool.process_pattern == pattern
        assert tool.logger is not None


class TestAbstractToolVariantSystem:
    """Tests for the variant system integration"""

    def test_variant_registration_through_get_variants(self):
        """Test that variants are properly exposed through get_variants"""
        variants = ConcreteTestTool.get_variants()

        assert isinstance(variants, dict)
        assert len(variants) >= 1
        assert "default" in variants

        # Check variant structure
        for variant_name, variant_config in variants.items():
            assert isinstance(variant_name, str)
            assert isinstance(variant_config, dict)

    def test_tool_spec_integration(self):
        """Test integration between tool spec and variants"""
        tool = ConcreteTestTool()
        spec = tool.get_tool_spec()
        variants = tool.get_variants()

        # Tool spec should match tool name
        assert spec.name == tool.name

        # Should have at least default variant
        assert "default" in variants

    def test_configure_with_variant_parameters(self):
        """Test configuration with variant-specific parameters"""
        tool = ConcreteTestTool()
        variants = tool.get_variants()

        # Configure with fast variant parameters
        fast_config = variants["fast"].copy()
        fast_config.update({"additional_param": "test"})

        tool.configure(fast_config)

        assert tool._configured
        assert tool._config["mode"] == "fast"
        assert tool._config["timeout"] == 30
        assert tool._config["additional_param"] == "test"

    def test_variant_parameter_validation(self):
        """Test validation of variant parameters"""
        tool = ConcreteTestTool()

        # Test with valid variant config
        valid_config = {"mode": "normal", "timeout": 60}
        tool.configure(valid_config)
        assert tool._configured

        # Test with empty config
        tool2 = ConcreteTestTool()
        tool2.configure({})
        assert tool2._configured
        assert tool2._config == {}

    @given(
        mode=st.sampled_from(["normal", "fast", "slow", "debug"]),
        timeout=st.integers(min_value=1, max_value=3600),
    )
    def test_variant_configuration_property_based(self, mode, timeout):
        """Property-based test for variant configuration"""
        tool = ConcreteTestTool()
        config = {"mode": mode, "timeout": timeout}

        tool.configure(config)

        assert tool._configured
        assert tool._config["mode"] == mode
        assert tool._config["timeout"] == timeout

        # Test that configuration is preserved
        assert tool._config == config


class TestAbstractToolLoggingAndErrorHandling:
    """Tests for logging and error handling functionality"""

    def test_logging_context_setup(self):
        """Test that logging context is properly set up"""
        tool = ConcreteTestTool()

        assert tool.logger is not None
        # Logger should have tool-specific name
        assert "testtool" in tool.logger.name.lower()

    def test_error_handler_integration(self):
        """Test error handler integration"""
        tool = ConcreteTestTool()

        assert tool.error_handler is not None

    def test_error_propagation(self):
        """Test that errors are properly propagated"""
        tool = ConcreteTestTool()
        tool.configure({"mode": "test"})

        tool_config = ToolConfig(name="testtool")
        task_config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=task_config)
        app = MagicMock(spec=App)

        # Mock execute_tool_specific_logic to raise an error
        def failing_execute(task, app):
            raise RVToolExecutionError("Simulated failure", tool_name=tool.name)

        tool.execute_tool_specific_logic = failing_execute

        with pytest.raises(RVToolExecutionError) as exc_info:
            tool.execute(task, app)

        assert "Simulated failure" in str(exc_info.value)
        assert exc_info.value.tool_name == "testtool"

    def test_execute_exception_no_duplicate_logging(self):
        """Test that execute() does not duplicate error logging.

        When execute_tool_specific_logic raises, execute() must re-raise
        without calling error_handler.handle_error() or logger.error(),
        because the caller (ToolExecutionComponent) handles logging.
        """
        tool = ConcreteTestTool()
        tool.configure({"mode": "test"})

        tool_config = ToolConfig(name="testtool")
        task_config = TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )
        task = Task(config=task_config)
        app = MagicMock(spec=App)

        def failing_execute(task, app):
            raise RuntimeError("something broke")

        tool.execute_tool_specific_logic = failing_execute

        with patch.object(
            tool.error_handler, "handle_error"
        ) as mock_handle, patch.object(tool.logger, "error") as mock_log_error:
            with pytest.raises(RuntimeError):
                tool.execute(task, app)

            # execute() must NOT call error_handler or logger.error
            mock_handle.assert_not_called()
            mock_log_error.assert_not_called()

    def test_logging_during_execution(self):
        """Test that logging works during execution"""
        tool = ConcreteTestTool()
        tool.configure({"mode": "test", "debug": True})

        # Mock logger to capture logs
        with patch.object(tool.logger, "info") as mock_log_info:
            tool_config = ToolConfig(name="testtool")
            task_config = TaskConfiguration(
                apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
            )
            task = Task(config=task_config)
            app = MagicMock(spec=App)

            tool.execute(task, app)

            # Should have logged execution
            mock_log_info.assert_called()
            # Check for either the execution start or completion message
            logged_messages = [call[0][0] for call in mock_log_info.call_args_list]
            assert any(
                "Executing monitored operations tool: testtool" in msg
                or "Tool testtool execution completed successfully" in msg
                for msg in logged_messages
            )
