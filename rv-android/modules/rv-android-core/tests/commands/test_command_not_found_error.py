# tests/commands/test_command_not_found_error.py
import pytest
from rv_android_core.commands.command_exception import CommandException
from rv_android_core.commands.command_not_found_error import CommandNotFoundError


class TestCommandNotFoundError:
    """Tests for CommandNotFoundError class"""

    def test_initialization_with_default_message(self):
        """Test CommandNotFoundError initialization with default message"""
        error = CommandNotFoundError()

        assert error.tool == "unknown"
        assert error.code == -1
        assert error.message == "Command not found"
        assert isinstance(error, CommandException)

    def test_initialization_with_custom_message(self):
        """Test CommandNotFoundError initialization with custom message"""
        custom_message = "The binary 'xyz' was not found in PATH"
        error = CommandNotFoundError(custom_message)

        assert error.tool == "unknown"  # Default tool name
        assert error.code == -1  # Default error code
        assert error.message == custom_message

    def test_explicit_tool_specification(self):
        """Test setting tool explicitly after initialization"""
        error = CommandNotFoundError("Command not found")
        # Manually set the tool name to simulate what the class might do internally
        error.tool = "adb"

        assert error.tool == "adb"
        assert error.code == -1
        assert error.message == "Command not found"

    def test_inheritance_from_command_exception(self):
        """Test that CommandNotFoundError is a subclass of CommandException"""
        error = CommandNotFoundError()

        assert isinstance(error, CommandException)
        assert issubclass(CommandNotFoundError, CommandException)

    def test_raising_and_catching_as_command_exception(self):
        """Test CommandNotFoundError can be caught as CommandException"""
        try:
            raise CommandNotFoundError("Command not found")
        except CommandException as e:
            assert e.tool == "unknown"
            assert e.code == -1
            assert e.message == "Command not found"
        except Exception:
            pytest.fail("CommandNotFoundError was not caught as CommandException")

    def test_raising_and_catching_as_specific_error(self):
        """Test CommandNotFoundError can be caught specifically"""
        try:
            raise CommandNotFoundError("Command not found")
        except CommandNotFoundError as e:
            assert e.tool == "unknown"
            assert e.code == -1
            assert e.message == "Command not found"
        except Exception:
            pytest.fail("CommandNotFoundError was not caught as expected")

    def test_string_representation_matches_parent(self):
        """Test string representation follows parent class format"""
        error = CommandNotFoundError("Command not found")
        # Ensure string representation follows CommandException format
        expected_format = f"CommandException[tool={error.tool} ::: code={error.code} ::: message={error.message}]"

        assert str(error) == expected_format
