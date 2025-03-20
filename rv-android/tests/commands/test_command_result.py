import pytest
from rvandroid.commands.command_result import CommandResult


class TestCommandResult:
    """Tests for CommandResult class"""

    def test_command_result_initialization(self):
        """Test CommandResult constructor"""
        stdout = b"Command output"
        stderr = b"Error output"
        result = CommandResult(0, stdout, stderr)

        assert result.code == 0
        assert result.stdout == stdout
        assert result.stderr == stderr

    def test_command_result_properties(self):
        """Test property setters and getters"""
        result = CommandResult(0, b"", b"")

        # Test setters
        result.code = 1
        result.stdout = b"New output"
        result.stderr = b"New error"

        # Test getters
        assert result.code == 1
        assert result.stdout == b"New output"
        assert result.stderr == b"New error"

    def test_command_result_with_string_output(self):
        """Test with string output instead of bytes"""
        # Note: In real scenarios, subprocess returns bytes, but we want
        # to ensure the class handles string values for robustness
        result = CommandResult(0, "String output", "String error")

        assert result.code == 0
        assert result.stdout == "String output"
        assert result.stderr == "String error"

    def test_command_result_with_none_values(self):
        """Test with None values"""
        result = CommandResult(None, None, None)

        assert result.code is None
        assert result.stdout is None
        assert result.stderr is None
       