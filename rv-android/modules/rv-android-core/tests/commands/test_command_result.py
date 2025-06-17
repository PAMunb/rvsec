from rv_android_core.commands.command_result import CommandResult


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

    def test_command_result_with_bytes_output(self):
        """Test with bytes output (actual subprocess behavior)"""
        # subprocess.communicate() returns bytes, this is the correct scenario
        result = CommandResult(0, b"Bytes output", b"Bytes error")

        assert result.code == 0
        assert result.stdout == b"Bytes output"
        assert result.stderr == b"Bytes error"

    def test_command_result_with_empty_values(self):
        """Test with empty values (using proper types)"""
        result = CommandResult(0, b"", b"")

        assert result.code == 0
        assert result.stdout == b""
        assert result.stderr == b""
